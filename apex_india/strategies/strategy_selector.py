"""
APEX INDIA — Autonomous Strategy Selector
============================================
Orchestrates regime detection → strategy activation → universe
screening → signal ranking → top trade candidates.

Called every 60 seconds during market hours.

Pipeline:
1. Detect current market regime
2. Activate strategies applicable to the regime
3. Score universe against each active strategy
4. Rank all signals by confidence
5. Apply risk gate filters
6. Return top N trade candidates

Usage:
    selector = StrategySelector()
    candidates = selector.select(universe_data, benchmark_df)
"""

from typing import Dict, List, Optional

import pandas as pd

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, MarketRegime,
)
from apex_india.models.regime.regime_detector import RegimeDetector
from apex_india.strategies.timing import TimingIntelligence
from apex_india.utils.logger import get_logger

# Strategy imports
from apex_india.strategies.momentum.trend_rider import TrendMomentumRider
from apex_india.strategies.breakout.vol_breakout import VolatilityBreakout
from apex_india.strategies.mean_reversion.vwap_mr import VWAPMeanReversion
from apex_india.strategies.breakout.orb import OpeningRangeBreakout
from apex_india.strategies.momentum.earnings import EarningsMomentum
from apex_india.strategies.momentum.sector_rotation import SectorRotation
from apex_india.strategies.options.theta_harvest import ThetaHarvest
from apex_india.strategies.smc.smc_reversal import SMCReversal
from apex_india.strategies.momentum.gap_trade import GapTrade
from apex_india.strategies.momentum.swing_positional import SwingPositional

logger = get_logger("strategies.selector")


class StrategySelector:
    """
    Autonomous strategy selector and trade candidate generator.

    Maintains all 10 strategies and the regime detector.
    Produces ranked, filtered trade signals ready for the
    risk layer and execution engine.
    """

    MAX_CANDIDATES = 5  # Max simultaneous new trades

    def __init__(self):
        self._regime_detector = RegimeDetector()
        self._timing = TimingIntelligence()

        # Initialize all strategies
        self._strategies: List[BaseStrategy] = [
            TrendMomentumRider(),     # #1
            VolatilityBreakout(),     # #2
            VWAPMeanReversion(),      # #3
            OpeningRangeBreakout(),   # #4
            EarningsMomentum(),       # #5
            SectorRotation(),         # #6
            ThetaHarvest(),           # #7
            SMCReversal(),            # #8
            GapTrade(),               # #9
            SwingPositional(),        # #10
        ]

        self._strategy_map = {s.name: s for s in self._strategies}

    # ───────────────────────────────────────────────────────────
    # Main Selection Pipeline
    # ───────────────────────────────────────────────────────────

    def select(
        self,
        universe_data: Dict[str, pd.DataFrame],
        benchmark_df: Optional[pd.DataFrame] = None,
        vix: Optional[float] = None,
        breadth: Optional[Dict] = None,
        min_confidence: float = 60,
    ) -> List[TradeSignal]:
        """
        Full selection pipeline.

        Args:
            universe_data: {symbol: OHLCV DataFrame}
            benchmark_df: Nifty 50 data for regime detection
            vix: India VIX value
            breadth: Market breadth data
            min_confidence: Minimum confidence score to include

        Returns:
            Ranked list of TradeSignal objects (top N candidates)
        """
        # Step 1: Detect regime
        regime_df = benchmark_df if benchmark_df is not None else next(iter(universe_data.values()), pd.DataFrame())
        regime = self._regime_detector.detect(regime_df, vix=vix, breadth=breadth)

        logger.info(
            f"Regime: {regime.value} | "
            f"Scores: {self._regime_detector.scores}"
        )

        # Step 2: Get active strategies for this regime
        active_strategies = [
            s for s in self._strategies
            if s.is_active_for_regime(regime)
        ]

        logger.info(
            f"Active strategies: {[s.name for s in active_strategies]} "
            f"({len(active_strategies)}/{len(self._strategies)})"
        )

        # Step 3: Check timing
        calendar = self._timing.get_calendar_context()
        risk_adj = calendar.get("risk_adjustment", 1.0)

        # Step 4: Run each active strategy on each symbol
        all_signals: List[TradeSignal] = []

        for symbol, df in universe_data.items():
            for strategy in active_strategies:
                try:
                    signal = strategy.run(df, symbol, regime)
                    if signal and signal.confidence >= min_confidence:
                        # Apply calendar risk adjustment
                        signal.confidence *= risk_adj
                        all_signals.append(signal)
                except Exception as e:
                    logger.error(
                        f"Strategy {strategy.name} failed on {symbol}: {e}"
                    )

        # Step 5: Deduplicate — keep best signal per symbol
        best_per_symbol: Dict[str, TradeSignal] = {}
        for signal in all_signals:
            key = signal.symbol
            if key not in best_per_symbol or signal.confidence > best_per_symbol[key].confidence:
                best_per_symbol[key] = signal

        # Step 6: Rank by confidence (descending)
        ranked = sorted(best_per_symbol.values(), key=lambda s: s.confidence, reverse=True)

        # Step 7: Limit to max candidates
        top_candidates = ranked[:self.MAX_CANDIDATES]

        logger.info(
            f"Selection complete: "
            f"{len(all_signals)} raw signals → "
            f"{len(best_per_symbol)} unique symbols → "
            f"{len(top_candidates)} top candidates"
        )

        return top_candidates

    # ───────────────────────────────────────────────────────────
    # API
    # ───────────────────────────────────────────────────────────

    @property
    def current_regime(self) -> MarketRegime:
        return self._regime_detector.current_regime

    @property
    def regime_report(self) -> dict:
        return self._regime_detector.get_report()

    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        return self._strategy_map.get(name)

    def get_all_stats(self) -> List[dict]:
        return [s.stats for s in self._strategies]

    def format_candidates_report(self, signals: List[TradeSignal]) -> str:
        """Format trade candidates into a readable report."""
        if not signals:
            return "No trade candidates at this time."

        lines = [
            "=" * 75,
            f"  APEX INDIA — TRADE CANDIDATES | Regime: {self.current_regime.value}",
            "=" * 75,
            "",
        ]

        for i, sig in enumerate(signals, 1):
            lines.append(
                f"  #{i} [{sig.strategy_name:15s}] "
                f"{sig.direction.value:5s} {sig.symbol:15s} "
                f"Conf={sig.confidence:.0f}% "
                f"Entry={sig.entry_price:>10.2f} "
                f"SL={sig.stop_loss:>10.2f} "
                f"R:R={sig.risk_reward:>4.1f}"
            )
            lines.append(f"     Reason: {sig.reasoning}")
            lines.append("")

        lines.append("=" * 75)
        return "\n".join(lines)
