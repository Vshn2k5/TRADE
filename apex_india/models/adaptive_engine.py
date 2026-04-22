"""
APEX INDIA — Adaptive Engine
===============================
Continuous learning loop that monitors strategy performance,
adapts model weights, triggers retraining, and adjusts risk
parameters based on live performance feedback.

Loop (runs daily after market close):
1. Collect day's trade results
2. Update strategy performance scores
3. Retrain ML models if degradation detected
4. Adjust regime weights
5. Recalibrate position sizing parameters

Usage:
    engine = AdaptiveEngine()
    engine.daily_update(trades, market_data)
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("models.adaptive")

IST = pytz.timezone(MARKET_TIMEZONE)


class AdaptiveEngine:
    """
    Continuous learning and adaptation engine.

    Tracks per-strategy and per-regime performance,
    adjusts weights, and triggers model retraining.
    """

    # Performance windows
    SHORT_WINDOW = 20    # Last 20 trades
    MEDIUM_WINDOW = 50   # Last 50 trades
    LONG_WINDOW = 200    # Last 200 trades

    # Thresholds
    MIN_TRADES_FOR_EVAL = 10
    DEGRADATION_THRESHOLD = 0.20  # 20% decline in Sharpe
    RETRAINING_COOLDOWN_DAYS = 7

    def __init__(self):
        # Strategy performance tracking
        self._strategy_trades: Dict[str, List[Dict]] = defaultdict(list)
        self._strategy_scores: Dict[str, float] = {}
        self._strategy_weights: Dict[str, float] = {}

        # Regime performance
        self._regime_trades: Dict[str, List[Dict]] = defaultdict(list)
        self._regime_accuracy: Dict[str, float] = {}

        # Retraining tracker
        self._last_retrain: Dict[str, datetime] = {}
        self._retrain_queue: List[str] = []

        # History
        self._daily_summaries: List[Dict] = []
        self._adaptation_log: List[Dict] = []

    # ───────────────────────────────────────────────────────────
    # Daily Update Loop
    # ───────────────────────────────────────────────────────────

    def daily_update(
        self,
        trades: List[Dict],
        regime: str = "UNKNOWN",
    ) -> Dict[str, Any]:
        """
        End-of-day adaptation cycle.

        Args:
            trades: List of today's completed trade dicts
            regime: Current regime label

        Returns:
            Dict with adaptations made
        """
        if not trades:
            return {"status": "no_trades", "adaptations": []}

        now = datetime.now(IST)
        adaptations = []

        # 1. Record trades
        for trade in trades:
            strategy = trade.get("strategy", "unknown")
            self._strategy_trades[strategy].append(trade)
            self._regime_trades[regime].append(trade)

        # 2. Evaluate strategy performance
        strategy_evals = {}
        for strategy_name, strades in self._strategy_trades.items():
            if len(strades) < self.MIN_TRADES_FOR_EVAL:
                continue
            eval_result = self._evaluate_strategy(strategy_name, strades)
            strategy_evals[strategy_name] = eval_result

            # Check for degradation
            if eval_result.get("degradation_detected"):
                adaptations.append({
                    "type": "degradation",
                    "strategy": strategy_name,
                    "action": "reduce_weight",
                    "detail": eval_result,
                })

        # 3. Update strategy weights
        self._update_weights(strategy_evals)

        # 4. Check if retraining needed
        retrain_needed = self._check_retrain_triggers()
        if retrain_needed:
            adaptations.append({
                "type": "retrain_triggered",
                "models": retrain_needed,
            })

        # 5. Update regime accuracy
        self._update_regime_accuracy(regime, trades)

        # Store summary
        daily_summary = {
            "date": now.date().isoformat(),
            "n_trades": len(trades),
            "regime": regime,
            "pnl": sum(t.get("pnl", 0) for t in trades),
            "win_rate": round(
                sum(1 for t in trades if t.get("pnl", 0) > 0) / len(trades) * 100, 1
            ),
            "strategy_weights": dict(self._strategy_weights),
            "adaptations": len(adaptations),
        }
        self._daily_summaries.append(daily_summary)
        self._adaptation_log.extend(adaptations)

        logger.info(
            f"Daily update: {len(trades)} trades, "
            f"PnL={daily_summary['pnl']:+,.0f}, "
            f"Adaptations={len(adaptations)}"
        )

        return {
            "status": "updated",
            "summary": daily_summary,
            "strategy_weights": dict(self._strategy_weights),
            "adaptations": adaptations,
        }

    # ───────────────────────────────────────────────────────────
    # Strategy Evaluation
    # ───────────────────────────────────────────────────────────

    def _evaluate_strategy(
        self,
        strategy_name: str,
        trades: List[Dict],
    ) -> Dict[str, Any]:
        """Evaluate strategy performance over different windows."""
        pnls = [t.get("pnl", 0) for t in trades]

        # Short-term metrics
        short = pnls[-self.SHORT_WINDOW:]
        medium = pnls[-self.MEDIUM_WINDOW:]

        short_wr = sum(1 for p in short if p > 0) / max(len(short), 1)
        medium_wr = sum(1 for p in medium if p > 0) / max(len(medium), 1)

        short_sharpe = self._compute_sharpe(short)
        medium_sharpe = self._compute_sharpe(medium)

        # Degradation detection
        degradation = False
        if len(pnls) >= self.MEDIUM_WINDOW:
            if medium_sharpe > 0 and short_sharpe < medium_sharpe * (1 - self.DEGRADATION_THRESHOLD):
                degradation = True

        self._strategy_scores[strategy_name] = short_sharpe

        return {
            "strategy": strategy_name,
            "short_win_rate": round(short_wr * 100, 1),
            "medium_win_rate": round(medium_wr * 100, 1),
            "short_sharpe": round(short_sharpe, 4),
            "medium_sharpe": round(medium_sharpe, 4),
            "n_trades": len(trades),
            "total_pnl": round(sum(pnls), 2),
            "degradation_detected": degradation,
        }

    @staticmethod
    def _compute_sharpe(pnls: List[float]) -> float:
        """Compute Sharpe ratio from P&L series."""
        if len(pnls) < 2:
            return 0.0
        arr = np.array(pnls)
        std = arr.std()
        if std == 0:
            return 0.0
        return float(arr.mean() / std * np.sqrt(252))

    # ───────────────────────────────────────────────────────────
    # Weight Adjustment
    # ───────────────────────────────────────────────────────────

    def _update_weights(self, evals: Dict[str, Dict]) -> None:
        """Update strategy selection weights based on performance."""
        if not evals:
            return

        # Score-based weighting (softmax of Sharpe ratios)
        scores = {}
        for name, ev in evals.items():
            sharpe = max(ev.get("short_sharpe", 0), 0.01)
            scores[name] = sharpe

        if not scores:
            return

        total = sum(scores.values())
        for name, score in scores.items():
            self._strategy_weights[name] = round(score / total, 4)

    # ───────────────────────────────────────────────────────────
    # Retraining Triggers
    # ───────────────────────────────────────────────────────────

    def _check_retrain_triggers(self) -> List[str]:
        """Check if any ML models need retraining."""
        now = datetime.now(IST)
        models_to_retrain = []

        for strategy, score in self._strategy_scores.items():
            last_retrain = self._last_retrain.get(strategy)

            if last_retrain:
                days_since = (now - last_retrain).days
                if days_since < self.RETRAINING_COOLDOWN_DAYS:
                    continue

            # Retrain if Sharpe < 0.5 or significant degradation
            if score < 0.5:
                models_to_retrain.append(strategy)
                self._last_retrain[strategy] = now

        return models_to_retrain

    # ───────────────────────────────────────────────────────────
    # Regime Accuracy
    # ───────────────────────────────────────────────────────────

    def _update_regime_accuracy(self, regime: str, trades: List[Dict]) -> None:
        """Track how well the regime prediction matches trade outcomes."""
        if not trades:
            return

        win_rate = sum(1 for t in trades if t.get("pnl", 0) > 0) / len(trades)
        self._regime_accuracy[regime] = round(win_rate, 4)

    # ───────────────────────────────────────────────────────────
    # API
    # ───────────────────────────────────────────────────────────

    def get_strategy_weight(self, strategy_name: str) -> float:
        """Get current weight for a strategy."""
        return self._strategy_weights.get(strategy_name, 1.0 / max(len(self._strategy_weights), 1))

    def get_report(self) -> Dict[str, Any]:
        """Full adaptive engine report."""
        return {
            "strategy_weights": dict(self._strategy_weights),
            "strategy_scores": dict(self._strategy_scores),
            "regime_accuracy": dict(self._regime_accuracy),
            "retrain_queue": list(self._retrain_queue),
            "total_adaptations": len(self._adaptation_log),
            "daily_summaries_count": len(self._daily_summaries),
            "last_5_days": self._daily_summaries[-5:] if self._daily_summaries else [],
        }
