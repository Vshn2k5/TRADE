"""
APEX INDIA — Monte Carlo Simulation
======================================
Bootstrap simulation to stress-test strategy robustness.

Method:
- Shuffle trade sequence 10,000 times
- Generate confidence intervals for key metrics
- Estimate worst-case scenarios

Usage:
    mc = MonteCarloSimulator()
    result = mc.simulate(trades, initial_capital=1_000_000)
"""

import numpy as np
from typing import Any, Dict, List

from apex_india.utils.logger import get_logger

logger = get_logger("backtesting.monte_carlo")


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy stress testing.
    """

    def __init__(self, n_simulations: int = 10_000, seed: int = 42):
        self.n_sims = n_simulations
        self.seed = seed

    def simulate(
        self,
        trades: List[Dict],
        initial_capital: float = 1_000_000,
        confidence_levels: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation on trade results.

        Args:
            trades: List of trade dicts with 'pnl' key
            initial_capital: Starting capital
            confidence_levels: Percentiles to compute [default: 5, 25, 50, 75, 95]

        Returns:
            Dict with statistics, drawdown distribution, final equity distribution
        """
        if not trades:
            return {"error": "No trades to simulate"}

        if confidence_levels is None:
            confidence_levels = [5, 25, 50, 75, 95]

        np.random.seed(self.seed)
        pnls = np.array([t.get("pnl", 0) for t in trades])
        n_trades = len(pnls)

        # Storage
        final_equities = np.zeros(self.n_sims)
        max_drawdowns = np.zeros(self.n_sims)
        max_run_ups = np.zeros(self.n_sims)

        for i in range(self.n_sims):
            # Shuffle trade sequence
            shuffled = np.random.permutation(pnls)
            equity = initial_capital + np.cumsum(shuffled)
            equity = np.insert(equity, 0, initial_capital)

            final_equities[i] = equity[-1]

            # Max drawdown
            peak = np.maximum.accumulate(equity)
            dd = (equity - peak) / peak
            max_drawdowns[i] = dd.min() * 100

            # Max run up
            max_run_ups[i] = ((equity.max() / initial_capital) - 1) * 100

        # Statistics
        final_returns = ((final_equities / initial_capital) - 1) * 100

        result = {
            "n_simulations": self.n_sims,
            "n_trades": n_trades,
            "initial_capital": initial_capital,

            "final_equity": {
                "mean": round(float(final_equities.mean()), 2),
                "std": round(float(final_equities.std()), 2),
                "min": round(float(final_equities.min()), 2),
                "max": round(float(final_equities.max()), 2),
                "percentiles": {
                    f"p{p}": round(float(np.percentile(final_equities, p)), 2)
                    for p in confidence_levels
                },
            },

            "returns_pct": {
                "mean": round(float(final_returns.mean()), 2),
                "std": round(float(final_returns.std()), 2),
                "percentiles": {
                    f"p{p}": round(float(np.percentile(final_returns, p)), 2)
                    for p in confidence_levels
                },
            },

            "max_drawdown_pct": {
                "mean": round(float(max_drawdowns.mean()), 2),
                "worst": round(float(max_drawdowns.min()), 2),
                "best": round(float(max_drawdowns.max()), 2),
                "percentiles": {
                    f"p{p}": round(float(np.percentile(max_drawdowns, p)), 2)
                    for p in confidence_levels
                },
            },

            "probability_of_profit": round(
                float((final_equities > initial_capital).mean() * 100), 2
            ),
            "probability_of_ruin": round(
                float((final_equities < initial_capital * 0.5).mean() * 100), 4
            ),

            "risk_of_ruin_10pct": round(
                float((max_drawdowns < -10).mean() * 100), 2
            ),
            "risk_of_ruin_15pct": round(
                float((max_drawdowns < -15).mean() * 100), 2
            ),
            "risk_of_ruin_20pct": round(
                float((max_drawdowns < -20).mean() * 100), 2
            ),
        }

        logger.info(
            f"Monte Carlo: {self.n_sims} sims | "
            f"Profit prob={result['probability_of_profit']:.1f}% | "
            f"Mean return={result['returns_pct']['mean']:.1f}% | "
            f"Mean DD={result['max_drawdown_pct']['mean']:.1f}%"
        )

        return result

    def format_report(self, result: Dict) -> str:
        """Format Monte Carlo results."""
        lines = [
            "=" * 60,
            "  MONTE CARLO STRESS TEST",
            f"  {result['n_simulations']:,} simulations × "
            f"{result['n_trades']} trades",
            "=" * 60,
            "",
            f"  Probability of Profit: {result['probability_of_profit']:.1f}%",
            f"  Probability of Ruin:   {result['probability_of_ruin']:.2f}%",
            "",
            "  Final Equity:",
            f"    Mean:   ₹{result['final_equity']['mean']:>12,.2f}",
            f"    P5:     ₹{result['final_equity']['percentiles']['p5']:>12,.2f}",
            f"    P50:    ₹{result['final_equity']['percentiles']['p50']:>12,.2f}",
            f"    P95:    ₹{result['final_equity']['percentiles']['p95']:>12,.2f}",
            "",
            "  Max Drawdown:",
            f"    Mean:   {result['max_drawdown_pct']['mean']:>8.2f}%",
            f"    Worst:  {result['max_drawdown_pct']['worst']:>8.2f}%",
            f"    P5:     {result['max_drawdown_pct']['percentiles']['p5']:>8.2f}%",
            "",
            f"  Risk >10% DD: {result['risk_of_ruin_10pct']:.1f}%",
            f"  Risk >15% DD: {result['risk_of_ruin_15pct']:.1f}%",
            f"  Risk >20% DD: {result['risk_of_ruin_20pct']:.1f}%",
            "",
            "=" * 60,
        ]
        return "\n".join(lines)
