"""
APEX INDIA — Daily Report Generator
======================================
Generates end-of-day performance reports in text format.

Reports include:
- Day's P&L summary
- Trade log with reasoning
- Risk metrics snapshot
- Strategy performance attribution
- Next-day market outlook

Usage:
    gen = ReportGenerator()
    report = gen.daily_report(trades, pnl_tracker, circuit_breaker)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("dashboard.reports")

IST = pytz.timezone(MARKET_TIMEZONE)


class ReportGenerator:
    """
    End-of-day report generation.
    """

    def daily_report(
        self,
        trades: List[Dict],
        equity: float = 0,
        initial_capital: float = 1_000_000,
        circuit_breaker_status: Optional[Dict] = None,
        strategy_weights: Optional[Dict] = None,
    ) -> str:
        """
        Generate full daily text report.
        """
        now = datetime.now(IST)
        lines = [
            "=" * 65,
            f"  APEX INDIA — DAILY PERFORMANCE REPORT",
            f"  {now.strftime('%d %B %Y, %A')}",
            "=" * 65,
            "",
        ]

        # P&L Summary
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        pnl_pct = (total_pnl / initial_capital * 100) if initial_capital else 0
        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        losses = sum(1 for t in trades if t.get("pnl", 0) < 0)

        lines.extend([
            "  P&L SUMMARY",
            "  " + "-" * 50,
            f"  Total P&L:      ₹{total_pnl:>12,.2f} ({pnl_pct:+.2f}%)",
            f"  Equity:          ₹{equity:>12,.2f}",
            f"  Trades:          {len(trades):>12d}",
            f"  Wins / Losses:   {wins:>5d} / {losses}",
            f"  Win Rate:        {(wins/max(len(trades),1)*100):>11.1f}%",
            "",
        ])

        # Trade Log
        if trades:
            lines.extend([
                "  TRADE LOG",
                "  " + "-" * 50,
            ])
            for i, t in enumerate(trades, 1):
                pnl = t.get("pnl", 0)
                symbol = t.get("symbol", "?")
                direction = t.get("direction", "?")
                strategy = t.get("strategy", "?")
                reason = t.get("exit_reason", "?")
                lines.append(
                    f"  {i:>2}. {direction:5s} {symbol:12s} "
                    f"{'+'if pnl>=0 else ''}{pnl:>8,.0f}  "
                    f"[{strategy}] ({reason})"
                )
            lines.append("")

        # Strategy Attribution
        if trades:
            strat_pnl: Dict[str, float] = {}
            strat_count: Dict[str, int] = {}
            for t in trades:
                s = t.get("strategy", "unknown")
                strat_pnl[s] = strat_pnl.get(s, 0) + t.get("pnl", 0)
                strat_count[s] = strat_count.get(s, 0) + 1

            lines.extend([
                "  STRATEGY ATTRIBUTION",
                "  " + "-" * 50,
            ])
            for strat in sorted(strat_pnl, key=lambda x: -strat_pnl[x]):
                pnl = strat_pnl[strat]
                cnt = strat_count[strat]
                lines.append(
                    f"  {strat:22s} {cnt:>3d} trades  "
                    f"₹{'+'if pnl>=0 else ''}{pnl:>10,.0f}"
                )
            lines.append("")

        # Risk Status
        if circuit_breaker_status:
            cb = circuit_breaker_status
            lines.extend([
                "  RISK STATUS",
                "  " + "-" * 50,
                f"  Circuit Breaker:  {cb.get('level', 'NORMAL')}",
                f"  Trading Allowed:  {'YES' if cb.get('trading_allowed') else 'NO'}",
            ])
            m = cb.get("metrics", {})
            if m:
                lines.extend([
                    f"  Daily Loss:       {m.get('daily_pct', 0):+.2f}% (limit: -2.5%)",
                    f"  Drawdown:         {m.get('drawdown_pct', 0):.2f}% (limit: 15%)",
                    f"  Consecutive Losses: {m.get('consecutive_losses', 0)}",
                ])
            lines.append("")

        # Strategy Weights
        if strategy_weights:
            lines.extend([
                "  ADAPTIVE WEIGHTS",
                "  " + "-" * 50,
            ])
            for strat, weight in sorted(strategy_weights.items(), key=lambda x: -x[1]):
                bar = "█" * int(weight * 40)
                lines.append(f"  {strat:22s} {weight*100:>5.1f}% {bar}")
            lines.append("")

        lines.extend([
            "=" * 65,
            f"  Generated: {now.strftime('%H:%M:%S IST')}",
            f"  APEX INDIA v3.0 — Built on discipline. Powered by intelligence.",
            "=" * 65,
        ])

        return "\n".join(lines)

    def weekly_summary(
        self,
        daily_reports: List[Dict],
    ) -> str:
        """Generate weekly summary from daily data."""
        total_pnl = sum(d.get("pnl", 0) for d in daily_reports)
        total_trades = sum(d.get("trades", 0) for d in daily_reports)
        wins = sum(d.get("wins", 0) for d in daily_reports)

        return f"""
{'='*65}
  APEX INDIA — WEEKLY SUMMARY
  {datetime.now(IST).strftime('%d %B %Y')}
{'='*65}

  Week P&L:     ₹{total_pnl:>12,.2f}
  Total Trades: {total_trades:>12d}
  Win Rate:     {(wins/max(total_trades,1)*100):>11.1f}%

{'='*65}
"""
