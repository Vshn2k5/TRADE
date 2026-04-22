"""
APEX INDIA — Circuit Breaker
===============================
Emergency risk controls that halt or reduce trading
when drawdown thresholds are breached.

Levels:
- Level 1: Daily loss > 2.5%  → halt all trading for today
- Level 2: Weekly loss > 5.0% → reduce size 50% for the week
- Level 3: Monthly loss > 8.0% → strategy recalibration required
- Level 4: Max DD > 15% from equity peak → COMPLETE HALT + audit
- VIX Emergency: VIX > 35 → exit all, hold 80%+ cash

Usage:
    breaker = CircuitBreaker(capital=1_000_000)
    breaker.record_pnl(-15000)  # Record a loss
    status = breaker.check()     # Check if any breaker is tripped
"""

from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("risk.circuit_breaker")

IST = pytz.timezone(MARKET_TIMEZONE)


class CircuitBreaker:
    """
    Multi-level circuit breaker system.

    Tracks P&L at daily/weekly/monthly granularity
    and triggers halts when limits are breached.
    """

    # Default thresholds
    DAILY_LOSS_LIMIT_PCT = 2.5
    WEEKLY_LOSS_LIMIT_PCT = 5.0
    MONTHLY_LOSS_LIMIT_PCT = 8.0
    MAX_DRAWDOWN_PCT = 15.0
    VIX_EMERGENCY_LEVEL = 35.0
    CONSECUTIVE_LOSS_LIMIT = 5

    def __init__(
        self,
        capital: float = 1_000_000,
        daily_limit: float = 2.5,
        weekly_limit: float = 5.0,
        monthly_limit: float = 8.0,
        max_dd: float = 15.0,
    ):
        self.initial_capital = capital
        self.capital = capital
        self.peak_capital = capital

        self.daily_limit = daily_limit
        self.weekly_limit = weekly_limit
        self.monthly_limit = monthly_limit
        self.max_dd = max_dd

        # P&L tracking
        self._daily_pnl: Dict[date, float] = defaultdict(float)
        self._trade_results: List[Dict] = []
        self._consecutive_losses = 0

        # Breaker states
        self._daily_halt = False
        self._size_reduction = 1.0  # Multiplier (1.0 = full, 0.5 = half)
        self._full_halt = False
        self._halt_reason = ""
        self._vix_emergency = False

    # ───────────────────────────────────────────────────────────
    # P&L Recording
    # ───────────────────────────────────────────────────────────

    def record_pnl(self, pnl: float, symbol: str = "") -> None:
        """Record a trade P&L and update breaker state."""
        today = datetime.now(IST).date()
        self._daily_pnl[today] += pnl
        self.capital += pnl
        self.peak_capital = max(self.peak_capital, self.capital)

        # Track consecutive losses
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        self._trade_results.append({
            "date": today,
            "symbol": symbol,
            "pnl": pnl,
            "capital_after": self.capital,
            "timestamp": datetime.now(IST),
        })

        logger.info(
            f"P&L recorded: {'+'if pnl>=0 else ''}{pnl:,.0f} ({symbol}) | "
            f"Capital: {self.capital:,.0f} | "
            f"Daily: {self._daily_pnl[today]:,.0f}"
        )

        # Auto-check after each P&L
        self.check()

    # ───────────────────────────────────────────────────────────
    # Breaker Checks
    # ───────────────────────────────────────────────────────────

    def check(self, vix: Optional[float] = None) -> Dict[str, Any]:
        """
        Run all circuit breaker checks.

        Returns status dict with breaker levels and trading permissions.
        """
        today = datetime.now(IST).date()

        status = {
            "trading_allowed": True,
            "size_multiplier": 1.0,
            "alerts": [],
            "level": "NORMAL",
        }

        # Manual / persistent halt check
        if self._full_halt:
            status["trading_allowed"] = False
            status["level"] = "FULL_HALT"
            status["alerts"].append(f"HALT ACTIVE: {self._halt_reason}")
            # Still compute metrics below but trading stays blocked

        # Level 1: Daily loss limit
        daily_pnl = self._daily_pnl.get(today, 0)
        daily_pct = (daily_pnl / self.initial_capital) * 100

        if daily_pct <= -self.daily_limit:
            self._daily_halt = True
            status["trading_allowed"] = False
            status["level"] = "DAILY_HALT"
            status["alerts"].append(
                f"DAILY CIRCUIT BREAKER: Loss {daily_pct:.2f}% "
                f"exceeds {self.daily_limit}% limit"
            )
            logger.warning(f"Circuit breaker LEVEL 1: Daily halt triggered ({daily_pct:.2f}%)")

        # Level 2: Weekly loss limit
        week_start = today - timedelta(days=today.weekday())
        weekly_pnl = sum(
            v for d, v in self._daily_pnl.items()
            if d >= week_start
        )
        weekly_pct = (weekly_pnl / self.initial_capital) * 100

        if weekly_pct <= -self.weekly_limit:
            self._size_reduction = 0.5
            status["size_multiplier"] = 0.5
            status["level"] = "WEEKLY_REDUCE"
            status["alerts"].append(
                f"WEEKLY BREAKER: Loss {weekly_pct:.2f}% — size reduced 50%"
            )
            logger.warning(f"Circuit breaker LEVEL 2: Size reduction ({weekly_pct:.2f}%)")

        # Level 3: Monthly loss limit
        month_start = today.replace(day=1)
        monthly_pnl = sum(
            v for d, v in self._daily_pnl.items()
            if d >= month_start
        )
        monthly_pct = (monthly_pnl / self.initial_capital) * 100

        if monthly_pct <= -self.monthly_limit:
            status["trading_allowed"] = False
            status["level"] = "MONTHLY_HALT"
            status["alerts"].append(
                f"MONTHLY CIRCUIT BREAKER: Loss {monthly_pct:.2f}% — "
                f"strategy recalibration required"
            )
            logger.error(f"Circuit breaker LEVEL 3: Monthly halt ({monthly_pct:.2f}%)")

        # Level 4: Max drawdown from equity peak
        drawdown = ((self.peak_capital - self.capital) / self.peak_capital) * 100

        if drawdown >= self.max_dd:
            self._full_halt = True
            self._halt_reason = f"Max drawdown {drawdown:.2f}% >= {self.max_dd}%"
            status["trading_allowed"] = False
            status["level"] = "FULL_HALT"
            status["alerts"].append(
                f"MAXIMUM DRAWDOWN BREAKER: {drawdown:.2f}% from peak — "
                f"COMPLETE HALT — manual audit required"
            )
            logger.critical(f"Circuit breaker LEVEL 4: FULL HALT ({drawdown:.2f}% DD)")

        # VIX Emergency
        if vix is not None and vix > self.VIX_EMERGENCY_LEVEL:
            self._vix_emergency = True
            status["trading_allowed"] = False
            status["level"] = "VIX_EMERGENCY"
            status["alerts"].append(
                f"VIX EMERGENCY: {vix:.1f} > {self.VIX_EMERGENCY_LEVEL} — "
                f"exit all positions, hold 80%+ cash"
            )
            logger.critical(f"VIX EMERGENCY: VIX={vix:.1f}")

        # Consecutive losses
        if self._consecutive_losses >= self.CONSECUTIVE_LOSS_LIMIT:
            status["size_multiplier"] = min(status["size_multiplier"], 0.5)
            status["alerts"].append(
                f"Consecutive losses: {self._consecutive_losses} — size reduced"
            )

        # Apply size reduction from weekly breaker
        if self._size_reduction < 1.0:
            status["size_multiplier"] = min(status["size_multiplier"], self._size_reduction)

        # Add metrics
        status["metrics"] = {
            "daily_pnl": round(daily_pnl, 2),
            "daily_pct": round(daily_pct, 3),
            "weekly_pnl": round(weekly_pnl, 2),
            "weekly_pct": round(weekly_pct, 3),
            "monthly_pnl": round(monthly_pnl, 2),
            "monthly_pct": round(monthly_pct, 3),
            "drawdown_pct": round(drawdown, 3),
            "peak_capital": round(self.peak_capital, 2),
            "current_capital": round(self.capital, 2),
            "consecutive_losses": self._consecutive_losses,
        }

        return status

    # ───────────────────────────────────────────────────────────
    # Manual Controls
    # ───────────────────────────────────────────────────────────

    def force_halt(self, reason: str = "Manual halt") -> None:
        """Manually halt all trading."""
        self._full_halt = True
        self._halt_reason = reason
        logger.critical(f"MANUAL HALT: {reason}")

    def resume(self, reason: str = "Manual resume") -> None:
        """Resume trading after manual review."""
        self._full_halt = False
        self._daily_halt = False
        self._vix_emergency = False
        self._size_reduction = 1.0
        self._halt_reason = ""
        logger.info(f"Trading RESUMED: {reason}")

    def reset_daily(self) -> None:
        """Reset daily breaker (called at start of each day)."""
        self._daily_halt = False
        logger.info("Daily circuit breaker reset")

    def reset_weekly(self) -> None:
        """Reset weekly breaker (called Monday morning)."""
        self._size_reduction = 1.0
        logger.info("Weekly circuit breaker reset")

    @property
    def is_halted(self) -> bool:
        return self._full_halt or self._daily_halt

    @property
    def halt_reason(self) -> str:
        return self._halt_reason
