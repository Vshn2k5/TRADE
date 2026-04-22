"""
APEX INDIA — Strategy #6: Sector Rotation
============================================
Weekly rebalancing into leading sectors based on
relative strength momentum.

Entry: Top 3 sectors by 20-day RS, buy strongest stocks within.
Exit:  Sector drops out of top 3, or weekly rebalance.
Regime: TRENDING_BULLISH (best), any trending
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.sector import SectorAnalysis
from apex_india.data.indicators.volatility import VolatilityIndicators


class SectorRotation(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="sector_rotation",
            version="1.0",
            applicable_regimes=[
                MarketRegime.TRENDING_BULLISH, MarketRegime.TRENDING_BEARISH,
            ],
            min_bars=60,
            timeframe="week",
        )
        self._sector = SectorAnalysis()
        self._vol = VolatilityIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        """
        For sector rotation, df should be the individual stock data.
        This strategy is typically run at the portfolio level via
        generate_rotation_signals() instead.
        """
        df = VolatilityIndicators.atr(df)

        # Simple momentum check: 20-day return > 2%
        if len(df) < 20:
            return None

        ret_20 = (df["close"].iloc[-1] / df["close"].iloc[-21]) - 1

        if ret_20 < 0.02:
            return None

        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, SignalDirection.LONG)

        return TradeSignal(
            symbol=symbol, direction=SignalDirection.LONG,
            strength=SignalStrength.MODERATE,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets,
            confidence=60 + min(20, int(ret_20 * 100)),
            regime=regime, timeframe="week",
            reasoning=f"Sector momentum: 20d return={ret_20*100:.1f}%",
        )

    def generate_rotation_signals(
        self,
        sector_data: Dict[str, pd.DataFrame],
        stock_data: Dict[str, pd.DataFrame],
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> List[TradeSignal]:
        """
        Portfolio-level rotation signal generation.
        Identifies top sectors and best stocks within them.
        """
        rotation = self._sector.sector_rotation(sector_data)
        leaders = rotation.get("leaders", [])

        if not leaders:
            return []

        signals = []
        for symbol, df in stock_data.items():
            signal = self.generate_signals(df, symbol, regime)
            if signal:
                signals.append(signal)

        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals[:5]

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 2.5, 3.0, 5.0, 8.0)
