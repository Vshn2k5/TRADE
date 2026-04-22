"""
APEX INDIA — Performance Metrics
===================================
Comprehensive trading performance analysis with all standard
quantitative metrics used by institutional desks.

Metrics:
- Risk-adjusted: Sharpe, Sortino, Calmar, Recovery Factor
- Profitability: CAGR, Win Rate, Profit Factor, Expectancy
- Drawdown: Max DD, Avg DD, DD Duration, Underwater Equity
- Trade: Average Win/Loss, Largest Win/Loss, Consecutive W/L

Usage:
    metrics = PerformanceMetrics(equity_curve, trades)
    report = metrics.full_report()
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from apex_india.utils.logger import get_logger

logger = get_logger("backtesting.metrics")


class PerformanceMetrics:
    """
    Compute all performance metrics from equity curve and trade log.
    """

    RISK_FREE_RATE = 0.065  # India 10Y ~6.5%
    TRADING_DAYS_PER_YEAR = 252

    def __init__(
        self,
        equity_curve: pd.Series,
        trades: Optional[List[Dict]] = None,
        risk_free_rate: float = 0.065,
    ):
        self.equity = equity_curve
        self.trades = trades or []
        self.rf = risk_free_rate
        self._returns = equity_curve.pct_change().dropna()

    # ───────────────────────────────────────────────────────────
    # Risk-Adjusted Returns
    # ───────────────────────────────────────────────────────────

    def sharpe_ratio(self) -> float:
        """Annualized Sharpe Ratio."""
        if len(self._returns) < 2 or self._returns.std() == 0:
            return 0.0
        excess = self._returns.mean() - self.rf / self.TRADING_DAYS_PER_YEAR
        return round(float(excess / self._returns.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)), 4)

    def sortino_ratio(self) -> float:
        """Sortino Ratio — penalizes downside volatility only."""
        if len(self._returns) < 2:
            return 0.0
        downside = self._returns[self._returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return float("inf") if self._returns.mean() > 0 else 0.0
        excess = self._returns.mean() - self.rf / self.TRADING_DAYS_PER_YEAR
        return round(float(excess / downside.std() * np.sqrt(self.TRADING_DAYS_PER_YEAR)), 4)

    def calmar_ratio(self) -> float:
        """Calmar Ratio = CAGR / Max Drawdown."""
        cagr = self.cagr()
        mdd = self.max_drawdown()
        if mdd == 0:
            return 0.0
        return round(cagr / abs(mdd), 4)

    def recovery_factor(self) -> float:
        """Net Profit / Max Drawdown."""
        total_profit = self.equity.iloc[-1] - self.equity.iloc[0]
        mdd_abs = abs(self.max_drawdown_absolute())
        if mdd_abs == 0:
            return 0.0
        return round(total_profit / mdd_abs, 4)

    # ───────────────────────────────────────────────────────────
    # Profitability
    # ───────────────────────────────────────────────────────────

    def cagr(self) -> float:
        """Compound Annual Growth Rate."""
        if len(self.equity) < 2 or self.equity.iloc[0] <= 0:
            return 0.0
        total_return = self.equity.iloc[-1] / self.equity.iloc[0]
        n_years = len(self.equity) / self.TRADING_DAYS_PER_YEAR
        if n_years <= 0:
            return 0.0
        return round(float(total_return ** (1 / n_years) - 1), 6)

    def total_return(self) -> float:
        """Total return percentage."""
        if self.equity.iloc[0] == 0:
            return 0.0
        return round(float((self.equity.iloc[-1] / self.equity.iloc[0] - 1) * 100), 2)

    def win_rate(self) -> float:
        """Percentage of winning trades."""
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.get("pnl", 0) > 0)
        return round(wins / len(self.trades) * 100, 2)

    def profit_factor(self) -> float:
        """Gross Profit / Gross Loss."""
        if not self.trades:
            return 0.0
        gross_profit = sum(t["pnl"] for t in self.trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in self.trades if t.get("pnl", 0) < 0))
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return round(gross_profit / gross_loss, 4)

    def expectancy(self) -> float:
        """Average expected profit per trade."""
        if not self.trades:
            return 0.0
        return round(sum(t.get("pnl", 0) for t in self.trades) / len(self.trades), 2)

    # ───────────────────────────────────────────────────────────
    # Drawdown Analysis
    # ───────────────────────────────────────────────────────────

    def max_drawdown(self) -> float:
        """Maximum drawdown as percentage."""
        peak = self.equity.cummax()
        dd = (self.equity - peak) / peak
        return round(float(dd.min() * 100), 4)

    def max_drawdown_absolute(self) -> float:
        """Maximum drawdown in absolute terms."""
        peak = self.equity.cummax()
        dd = self.equity - peak
        return round(float(dd.min()), 2)

    def avg_drawdown(self) -> float:
        """Average drawdown depth."""
        peak = self.equity.cummax()
        dd = (self.equity - peak) / peak
        drawdowns = dd[dd < 0]
        if len(drawdowns) == 0:
            return 0.0
        return round(float(drawdowns.mean() * 100), 4)

    def max_drawdown_duration(self) -> int:
        """Longest drawdown duration in days."""
        peak = self.equity.cummax()
        underwater = self.equity < peak

        if not underwater.any():
            return 0

        max_duration = 0
        current_duration = 0
        for is_underwater in underwater:
            if is_underwater:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0

        return max_duration

    def drawdown_series(self) -> pd.Series:
        """Drawdown percentage series for charting."""
        peak = self.equity.cummax()
        return (self.equity - peak) / peak * 100

    # ───────────────────────────────────────────────────────────
    # Trade Statistics
    # ───────────────────────────────────────────────────────────

    def trade_stats(self) -> Dict[str, Any]:
        """Detailed trade-level statistics."""
        if not self.trades:
            return {}

        pnls = [t.get("pnl", 0) for t in self.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        # Consecutive tracking
        max_consec_wins = max_consec_losses = 0
        cur_wins = cur_losses = 0
        for p in pnls:
            if p > 0:
                cur_wins += 1
                cur_losses = 0
                max_consec_wins = max(max_consec_wins, cur_wins)
            elif p < 0:
                cur_losses += 1
                cur_wins = 0
                max_consec_losses = max(max_consec_losses, cur_losses)

        return {
            "total_trades": len(self.trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": self.win_rate(),
            "avg_win": round(np.mean(wins), 2) if wins else 0,
            "avg_loss": round(np.mean(losses), 2) if losses else 0,
            "largest_win": round(max(wins), 2) if wins else 0,
            "largest_loss": round(min(losses), 2) if losses else 0,
            "avg_win_loss_ratio": round(
                abs(np.mean(wins) / np.mean(losses)), 4
            ) if wins and losses else 0,
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "expectancy": self.expectancy(),
            "profit_factor": self.profit_factor(),
        }

    # ───────────────────────────────────────────────────────────
    # Monthly Returns
    # ───────────────────────────────────────────────────────────

    def monthly_returns(self) -> pd.DataFrame:
        """Monthly returns table (year x month)."""
        if len(self._returns) < 20:
            return pd.DataFrame()

        monthly = self._returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        if hasattr(monthly.index, 'month'):
            table = monthly.groupby([monthly.index.year, monthly.index.month]).first().unstack()
            table.columns = [f"M{m}" for m in range(1, 13)][:len(table.columns)]
            return (table * 100).round(2)
        return pd.DataFrame()

    # ───────────────────────────────────────────────────────────
    # Full Report
    # ───────────────────────────────────────────────────────────

    def full_report(self) -> Dict[str, Any]:
        """Complete performance report."""
        report = {
            "returns": {
                "total_return_pct": self.total_return(),
                "cagr": round(self.cagr() * 100, 2),
                "sharpe": self.sharpe_ratio(),
                "sortino": self.sortino_ratio(),
                "calmar": self.calmar_ratio(),
                "recovery_factor": self.recovery_factor(),
            },
            "drawdown": {
                "max_drawdown_pct": self.max_drawdown(),
                "max_drawdown_abs": self.max_drawdown_absolute(),
                "avg_drawdown_pct": self.avg_drawdown(),
                "max_dd_duration_days": self.max_drawdown_duration(),
            },
            "trades": self.trade_stats(),
            "equity": {
                "start": round(float(self.equity.iloc[0]), 2),
                "end": round(float(self.equity.iloc[-1]), 2),
                "peak": round(float(self.equity.max()), 2),
                "trough": round(float(self.equity.min()), 2),
                "days": len(self.equity),
            },
        }

        # Pass/Fail against targets
        report["targets"] = {
            "cagr_target_20pct": report["returns"]["cagr"] >= 20,
            "sharpe_target_1.5": report["returns"]["sharpe"] >= 1.5,
            "max_dd_target_15pct": abs(report["drawdown"]["max_drawdown_pct"]) <= 15,
            "profit_factor_1.8": report["trades"].get("profit_factor", 0) >= 1.8,
        }

        return report

    def format_report(self) -> str:
        """Formatted text report."""
        r = self.full_report()
        lines = [
            "=" * 60,
            "  APEX INDIA — BACKTEST PERFORMANCE REPORT",
            "=" * 60,
            "",
            f"  Total Return:  {r['returns']['total_return_pct']:>8.2f}%",
            f"  CAGR:          {r['returns']['cagr']:>8.2f}%",
            f"  Sharpe Ratio:  {r['returns']['sharpe']:>8.4f}",
            f"  Sortino Ratio: {r['returns']['sortino']:>8.4f}",
            f"  Calmar Ratio:  {r['returns']['calmar']:>8.4f}",
            f"  Recovery Fac:  {r['returns']['recovery_factor']:>8.4f}",
            "",
            f"  Max Drawdown:  {r['drawdown']['max_drawdown_pct']:>8.2f}%",
            f"  Max DD Abs:    ₹{r['drawdown']['max_drawdown_abs']:>10,.2f}",
            f"  Avg Drawdown:  {r['drawdown']['avg_drawdown_pct']:>8.2f}%",
            f"  Max DD Days:   {r['drawdown']['max_dd_duration_days']:>8d}",
            "",
        ]
        if r["trades"]:
            t = r["trades"]
            lines.extend([
                f"  Total Trades:  {t['total_trades']:>8d}",
                f"  Win Rate:      {t['win_rate']:>8.2f}%",
                f"  Profit Factor: {t['profit_factor']:>8.4f}",
                f"  Expectancy:    ₹{t['expectancy']:>10,.2f}",
                f"  Avg Win:       ₹{t['avg_win']:>10,.2f}",
                f"  Avg Loss:      ₹{t['avg_loss']:>10,.2f}",
                f"  W/L Ratio:     {t['avg_win_loss_ratio']:>8.4f}",
                f"  Max Consec W:  {t['max_consecutive_wins']:>8d}",
                f"  Max Consec L:  {t['max_consecutive_losses']:>8d}",
            ])

        lines.extend(["", "=" * 60])
        return "\n".join(lines)
