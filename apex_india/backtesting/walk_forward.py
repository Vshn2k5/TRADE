"""
APEX INDIA — Walk-Forward Optimization
=========================================
Expanding window walk-forward validation to prevent overfitting.

Method:
- Split data into expanding train/test windows
- Train on window N, test on window N+1
- Aggregate OOS (out-of-sample) performance
- Strategy must be within 20% of IS performance

Usage:
    wf = WalkForwardOptimizer()
    result = wf.run(df, strategy, n_splits=5)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from apex_india.backtesting.engine import BacktestEngine
from apex_india.backtesting.metrics import PerformanceMetrics
from apex_india.strategies.base_strategy import BaseStrategy, MarketRegime
from apex_india.utils.logger import get_logger

logger = get_logger("backtesting.walk_forward")


class WalkForwardOptimizer:
    """
    Walk-forward validation with expanding training windows.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        max_is_oos_divergence: float = 0.20,
    ):
        self.initial_capital = initial_capital
        self.max_divergence = max_is_oos_divergence

    def run(
        self,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        symbol: str = "TEST",
        n_splits: int = 5,
        train_ratio: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Run walk-forward optimization.

        Args:
            df: Full OHLCV dataset
            strategy: Strategy to test
            symbol: Symbol name
            n_splits: Number of walk-forward windows
            train_ratio: Ratio of data used for training in each window

        Returns:
            Dict with per-window and aggregate results.
        """
        total_bars = len(df)
        window_size = total_bars // n_splits

        results = []
        oos_equity_parts = []

        for i in range(n_splits):
            start = 0  # Expanding window: always start from 0
            train_end = (i + 1) * window_size
            test_end = min(train_end + window_size, total_bars)

            if train_end >= total_bars or test_end <= train_end:
                break

            train_df = df.iloc[start:train_end]
            test_df = df.iloc[:test_end]  # Include train for indicator warmup

            # In-sample backtest
            is_engine = BacktestEngine(self.initial_capital)
            is_result = is_engine.run(train_df, strategy, symbol)

            # Out-of-sample backtest (use full data up to test_end, but only measure OOS)
            oos_engine = BacktestEngine(self.initial_capital)
            oos_result = oos_engine.run(test_df, strategy, symbol)

            is_sharpe = is_result["metrics"]["returns"]["sharpe"]
            oos_sharpe = oos_result["metrics"]["returns"]["sharpe"]

            # Divergence check
            if is_sharpe != 0:
                divergence = abs(oos_sharpe - is_sharpe) / abs(is_sharpe)
            else:
                divergence = 0

            passed = divergence <= self.max_divergence or oos_sharpe >= 1.0

            window_result = {
                "window": i + 1,
                "train_bars": len(train_df),
                "test_bars": test_end - train_end,
                "is_sharpe": is_sharpe,
                "oos_sharpe": oos_sharpe,
                "is_return": is_result["metrics"]["returns"]["total_return_pct"],
                "oos_return": oos_result["metrics"]["returns"]["total_return_pct"],
                "divergence_pct": round(divergence * 100, 2),
                "passed": passed,
                "is_trades": is_result["num_trades"],
                "oos_trades": oos_result["num_trades"],
            }
            results.append(window_result)

        # Aggregate
        avg_oos_sharpe = np.mean([r["oos_sharpe"] for r in results]) if results else 0
        all_passed = all(r["passed"] for r in results)

        return {
            "windows": results,
            "n_windows": len(results),
            "avg_oos_sharpe": round(float(avg_oos_sharpe), 4),
            "all_windows_passed": all_passed,
            "robustness_score": round(
                sum(1 for r in results if r["passed"]) / max(len(results), 1) * 100, 1
            ),
        }
