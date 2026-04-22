"""
APEX INDIA — Stop-Loss Manager
=================================
4-layer stop-loss architecture that protects capital while
allowing winning trades room to run.

Layers:
- Layer 1: Initial Hard Stop (structure-based or ATR-based)
- Layer 2: Trailing Stop (ATR-based, ratchet-only)
- Layer 3: Time-Based Stop (intraday close by 15:15, swing 5-day rule)
- Layer 4: Break-Even Stop (activated at 1:1 R:R)

CRITICAL RULE: Stop-loss can NEVER move further from entry.

Usage:
    slm = StopLossManager()
    stop = slm.compute_initial_stop(entry=1500, direction="LONG", atr=35)
    new_stop = slm.update_trailing(current_price=1580, highest=1590, atr=35)
"""

from datetime import datetime, time, timedelta
from typing import Any, Dict, Optional, Tuple

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("risk.stop_loss")

IST = pytz.timezone(MARKET_TIMEZONE)


class StopLossManager:
    """
    Multi-layer stop-loss management for open positions.

    Each position tracked with:
    - entry_price, direction, initial_stop
    - current_stop (can only tighten)
    - highest_price (for longs) / lowest_price (for shorts)
    - entry_time (for time-based stops)
    """

    def __init__(
        self,
        atr_initial_mult: float = 2.0,
        atr_trail_mult: float = 2.0,
        breakeven_rr: float = 1.0,
        intraday_close_time: time = time(15, 15),
        swing_max_days: int = 5,
    ):
        self.atr_initial_mult = atr_initial_mult
        self.atr_trail_mult = atr_trail_mult
        self.breakeven_rr = breakeven_rr
        self.intraday_close_time = intraday_close_time
        self.swing_max_days = swing_max_days

        # Active positions
        self._positions: Dict[str, Dict] = {}

    # ───────────────────────────────────────────────────────────
    # Layer 1: Initial Hard Stop
    # ───────────────────────────────────────────────────────────

    def compute_initial_stop(
        self,
        entry_price: float,
        direction: str,
        atr: float,
        structure_stop: Optional[float] = None,
    ) -> float:
        """
        Compute initial stop-loss.

        Uses the tighter of:
        - ATR-based stop (entry ± atr_mult * ATR)
        - Structure-based stop (swing low/high, support/resistance)

        Args:
            entry_price: Entry price
            direction: "LONG" or "SHORT"
            atr: ATR value
            structure_stop: Optional structure-based stop level

        Returns:
            Stop-loss price
        """
        # ATR-based
        if direction == "LONG":
            atr_stop = entry_price - self.atr_initial_mult * atr
        else:
            atr_stop = entry_price + self.atr_initial_mult * atr

        # Use structure stop if provided and it's tighter
        if structure_stop is not None:
            if direction == "LONG":
                stop = max(atr_stop, structure_stop)  # Tighter = higher for long
            else:
                stop = min(atr_stop, structure_stop)  # Tighter = lower for short
        else:
            stop = atr_stop

        return round(stop, 2)

    # ───────────────────────────────────────────────────────────
    # Layer 2: Trailing Stop
    # ───────────────────────────────────────────────────────────

    def update_trailing_stop(
        self,
        current_stop: float,
        entry_price: float,
        direction: str,
        current_price: float,
        highest_since_entry: float,
        lowest_since_entry: float,
        atr: float,
    ) -> Tuple[float, str]:
        """
        Update trailing stop-loss.

        CRITICAL: Stop can ONLY move toward the price (tighten),
        NEVER away from it.

        Returns:
            (new_stop, reason) — reason explains any change
        """
        if direction == "LONG":
            # Trail from highest high
            trail_stop = highest_since_entry - self.atr_trail_mult * atr
            new_stop = max(current_stop, trail_stop)  # Only tighten (raise)

            # Layer 4: Break-even activation
            risk = abs(entry_price - current_stop)
            reward = highest_since_entry - entry_price
            if risk > 0 and reward / risk >= self.breakeven_rr:
                breakeven_stop = entry_price + (entry_price * 0.001)  # Tiny buffer above entry
                new_stop = max(new_stop, breakeven_stop)

        else:  # SHORT
            trail_stop = lowest_since_entry + self.atr_trail_mult * atr
            new_stop = min(current_stop, trail_stop)  # Only tighten (lower)

            risk = abs(entry_price - current_stop)
            reward = entry_price - lowest_since_entry
            if risk > 0 and reward / risk >= self.breakeven_rr:
                breakeven_stop = entry_price - (entry_price * 0.001)
                new_stop = min(new_stop, breakeven_stop)

        new_stop = round(new_stop, 2)

        if new_stop != current_stop:
            reason = "trailing" if new_stop != entry_price else "breakeven"
            logger.debug(
                f"Stop updated: {current_stop} -> {new_stop} ({reason})"
            )
            return new_stop, reason

        return current_stop, "unchanged"

    # ───────────────────────────────────────────────────────────
    # Layer 3: Time-Based Stops
    # ───────────────────────────────────────────────────────────

    def check_time_stop(
        self,
        entry_time: datetime,
        is_intraday: bool = True,
        max_hold_days: Optional[int] = None,
    ) -> Tuple[bool, str]:
        """
        Check if a time-based stop is triggered.

        - Intraday: must close by 15:15 IST
        - Swing: max hold period (default 5 days)

        Returns:
            (should_exit, reason)
        """
        now = datetime.now(IST)

        # Intraday time stop
        if is_intraday:
            if now.time() >= self.intraday_close_time:
                return True, f"Intraday time stop: {self.intraday_close_time}"

        # Swing holding period stop
        hold_days = max_hold_days or self.swing_max_days
        if not is_intraday:
            elapsed = (now - entry_time).days
            if elapsed >= hold_days:
                return True, f"Holding period exceeded: {elapsed} >= {hold_days} days"

        return False, "OK"

    # ───────────────────────────────────────────────────────────
    # Position Manager
    # ───────────────────────────────────────────────────────────

    def register_position(
        self,
        position_id: str,
        symbol: str,
        entry_price: float,
        direction: str,
        initial_stop: float,
        is_intraday: bool = True,
        max_hold_days: Optional[int] = None,
    ) -> None:
        """Register a new position for stop management."""
        self._positions[position_id] = {
            "symbol": symbol,
            "entry_price": entry_price,
            "direction": direction,
            "initial_stop": initial_stop,
            "current_stop": initial_stop,
            "highest_since_entry": entry_price,
            "lowest_since_entry": entry_price,
            "entry_time": datetime.now(IST),
            "is_intraday": is_intraday,
            "max_hold_days": max_hold_days,
            "breakeven_activated": False,
            "stop_updates": 0,
        }
        logger.info(
            f"Position registered: {position_id} | {direction} {symbol} "
            f"@ {entry_price} | SL={initial_stop}"
        )

    def update_position(
        self,
        position_id: str,
        current_price: float,
        atr: float,
    ) -> Dict[str, Any]:
        """
        Update a position's stop-loss given current market price.

        Returns dict with: should_exit, exit_reason, current_stop, etc.
        """
        pos = self._positions.get(position_id)
        if not pos:
            return {"should_exit": False, "error": "Position not found"}

        # Update price extremes
        if pos["direction"] == "LONG":
            pos["highest_since_entry"] = max(pos["highest_since_entry"], current_price)
        else:
            pos["lowest_since_entry"] = min(pos["lowest_since_entry"], current_price)

        # Check price stop
        if pos["direction"] == "LONG" and current_price <= pos["current_stop"]:
            return {
                "should_exit": True,
                "exit_reason": f"Stop hit: {current_price:.2f} <= {pos['current_stop']:.2f}",
                "current_stop": pos["current_stop"],
                "pnl_pct": round((current_price / pos["entry_price"] - 1) * 100, 2),
            }
        elif pos["direction"] == "SHORT" and current_price >= pos["current_stop"]:
            return {
                "should_exit": True,
                "exit_reason": f"Stop hit: {current_price:.2f} >= {pos['current_stop']:.2f}",
                "current_stop": pos["current_stop"],
                "pnl_pct": round((1 - current_price / pos["entry_price"]) * 100, 2),
            }

        # Update trailing stop
        new_stop, reason = self.update_trailing_stop(
            current_stop=pos["current_stop"],
            entry_price=pos["entry_price"],
            direction=pos["direction"],
            current_price=current_price,
            highest_since_entry=pos["highest_since_entry"],
            lowest_since_entry=pos["lowest_since_entry"],
            atr=atr,
        )
        if new_stop != pos["current_stop"]:
            pos["current_stop"] = new_stop
            pos["stop_updates"] += 1
            if reason == "breakeven":
                pos["breakeven_activated"] = True

        # Check time stop
        time_exit, time_reason = self.check_time_stop(
            entry_time=pos["entry_time"],
            is_intraday=pos["is_intraday"],
            max_hold_days=pos.get("max_hold_days"),
        )
        if time_exit:
            return {
                "should_exit": True,
                "exit_reason": time_reason,
                "current_stop": pos["current_stop"],
            }

        # P&L
        if pos["direction"] == "LONG":
            pnl_pct = (current_price / pos["entry_price"] - 1) * 100
        else:
            pnl_pct = (1 - current_price / pos["entry_price"]) * 100

        return {
            "should_exit": False,
            "current_stop": pos["current_stop"],
            "breakeven_activated": pos["breakeven_activated"],
            "stop_updates": pos["stop_updates"],
            "pnl_pct": round(pnl_pct, 2),
        }

    def close_position(self, position_id: str) -> None:
        """Remove a closed position."""
        if position_id in self._positions:
            del self._positions[position_id]

    @property
    def active_positions(self) -> Dict[str, Dict]:
        return dict(self._positions)

    def get_all_stops(self) -> Dict[str, float]:
        """Get current stop for all positions."""
        return {pid: pos["current_stop"] for pid, pos in self._positions.items()}
