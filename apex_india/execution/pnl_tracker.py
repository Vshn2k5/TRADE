"""
APEX INDIA — Real-Time P&L Tracker
=====================================
Tracks live P&L across all positions, broken down by
strategy, symbol, and time period.

Features:
- Real-time MTM P&L
- Strategy-level attribution
- Daily/weekly/monthly aggregates
- Equity curve building
- P&L alerts and thresholds

Usage:
    tracker = PnLTracker(initial_capital=1_000_000)
    tracker.update_price("RELIANCE", 1550)
    report = tracker.get_report()
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional
from collections import defaultdict

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("execution.pnl")

IST = pytz.timezone(MARKET_TIMEZONE)


class PnLTracker:
    """
    Real-time P&L tracking and reporting.
    """

    def __init__(self, initial_capital: float = 1_000_000):
        self.initial_capital = initial_capital
        self.capital = initial_capital

        # Open positions for MTM
        self._positions: Dict[str, Dict] = {}

        # Realized P&L
        self._realized: List[Dict] = []
        self._daily_pnl: Dict[date, float] = defaultdict(float)

        # Strategy attribution
        self._strategy_pnl: Dict[str, float] = defaultdict(float)

        # Equity tracking
        self._equity_snapshots: List[Dict] = []

    # ───────────────────────────────────────────────────────────
    # Position Registration
    # ───────────────────────────────────────────────────────────

    def add_position(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        entry_price: float,
        strategy: str = "",
    ) -> None:
        """Register a new position for tracking."""
        self._positions[symbol] = {
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": entry_price,
            "unrealized_pnl": 0,
            "strategy": strategy,
            "entry_time": datetime.now(IST),
        }

    def close_position(
        self,
        symbol: str,
        exit_price: float,
    ) -> Dict[str, Any]:
        """Close a position and record realized P&L."""
        pos = self._positions.pop(symbol, None)
        if not pos:
            return {"error": f"Position {symbol} not found"}

        if pos["direction"] == "LONG":
            pnl = (exit_price - pos["entry_price"]) * pos["quantity"]
        else:
            pnl = (pos["entry_price"] - exit_price) * pos["quantity"]

        self.capital += pnl
        today = datetime.now(IST).date()
        self._daily_pnl[today] += pnl
        self._strategy_pnl[pos["strategy"]] += pnl

        record = {
            "symbol": symbol,
            "direction": pos["direction"],
            "quantity": pos["quantity"],
            "entry_price": pos["entry_price"],
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "strategy": pos["strategy"],
            "closed_at": datetime.now(IST).isoformat(),
        }
        self._realized.append(record)

        return record

    # ───────────────────────────────────────────────────────────
    # Price Updates
    # ───────────────────────────────────────────────────────────

    def update_price(self, symbol: str, price: float) -> None:
        """Update current price for a position."""
        pos = self._positions.get(symbol)
        if not pos:
            return

        pos["current_price"] = price

        if pos["direction"] == "LONG":
            pos["unrealized_pnl"] = (price - pos["entry_price"]) * pos["quantity"]
        else:
            pos["unrealized_pnl"] = (pos["entry_price"] - price) * pos["quantity"]

    def update_prices(self, prices: Dict[str, float]) -> None:
        """Bulk price update."""
        for symbol, price in prices.items():
            self.update_price(symbol, price)

    # ───────────────────────────────────────────────────────────
    # P&L Computation
    # ───────────────────────────────────────────────────────────

    @property
    def total_unrealized(self) -> float:
        """Total unrealized P&L across all open positions."""
        return sum(p["unrealized_pnl"] for p in self._positions.values())

    @property
    def total_realized(self) -> float:
        """Total realized P&L."""
        return sum(r["pnl"] for r in self._realized)

    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)."""
        return self.total_realized + self.total_unrealized

    @property
    def equity(self) -> float:
        """Current equity value."""
        return self.initial_capital + self.total_pnl

    # ───────────────────────────────────────────────────────────
    # Snapshots
    # ───────────────────────────────────────────────────────────

    def take_snapshot(self) -> None:
        """Record current equity state."""
        self._equity_snapshots.append({
            "time": datetime.now(IST).isoformat(),
            "equity": round(self.equity, 2),
            "realized": round(self.total_realized, 2),
            "unrealized": round(self.total_unrealized, 2),
            "positions": len(self._positions),
        })

    # ───────────────────────────────────────────────────────────
    # Reports
    # ───────────────────────────────────────────────────────────

    def get_report(self) -> Dict[str, Any]:
        """Full P&L report."""
        return {
            "equity": round(self.equity, 2),
            "initial_capital": self.initial_capital,
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl / self.initial_capital * 100, 3),
            "realized_pnl": round(self.total_realized, 2),
            "unrealized_pnl": round(self.total_unrealized, 2),
            "open_positions": len(self._positions),
            "closed_trades": len(self._realized),
            "positions": {
                sym: {
                    "direction": p["direction"],
                    "qty": p["quantity"],
                    "entry": p["entry_price"],
                    "current": p["current_price"],
                    "pnl": round(p["unrealized_pnl"], 2),
                    "strategy": p["strategy"],
                }
                for sym, p in self._positions.items()
            },
            "strategy_pnl": dict(self._strategy_pnl),
            "today_pnl": round(
                self._daily_pnl.get(datetime.now(IST).date(), 0), 2
            ),
        }

    def format_report(self) -> str:
        """Formatted P&L report."""
        r = self.get_report()
        lines = [
            "=" * 55,
            "  APEX INDIA — LIVE P&L DASHBOARD",
            "=" * 55,
            "",
            f"  Equity:       ₹{r['equity']:>12,.2f}",
            f"  Total P&L:    ₹{r['total_pnl']:>12,.2f} "
            f"({r['total_pnl_pct']:+.2f}%)",
            f"  Realized:     ₹{r['realized_pnl']:>12,.2f}",
            f"  Unrealized:   ₹{r['unrealized_pnl']:>12,.2f}",
            f"  Today's P&L:  ₹{r['today_pnl']:>12,.2f}",
            "",
            f"  Open Positions: {r['open_positions']}",
            f"  Closed Trades:  {r['closed_trades']}",
            "",
        ]

        if r["positions"]:
            lines.append("  OPEN POSITIONS:")
            for sym, p in r["positions"].items():
                lines.append(
                    f"    {p['direction']:5s} {sym:15s} "
                    f"x{p['qty']:>5d} "
                    f"Entry={p['entry']:>8.2f} "
                    f"Now={p['current']:>8.2f} "
                    f"P&L={'+'if p['pnl']>=0 else ''}{p['pnl']:>8,.0f}"
                )

        if r["strategy_pnl"]:
            lines.extend(["", "  STRATEGY P&L:"])
            for strat, pnl in sorted(
                r["strategy_pnl"].items(), key=lambda x: -x[1]
            ):
                lines.append(
                    f"    {strat:20s} ₹{'+'if pnl>=0 else ''}{pnl:>10,.0f}"
                )

        lines.extend(["", "=" * 55])
        return "\n".join(lines)
