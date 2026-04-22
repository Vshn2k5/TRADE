"""
APEX INDIA — Strategy #2: Volatility Breakout
================================================
Enters when price breaks out of a low-volatility contraction
zone (TTM Squeeze or Bollinger Squeeze).

Entry: Squeeze fires (BB exits Keltner), momentum > 0 for long,
       confirmed by volume surge.
Exit:  Supertrend flip or 2-ATR trailing stop.
Regime: BREAKOUT_PENDING
"""

import pandas as pd
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.trend import TrendIndicators
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators


class VolatilityBreakout(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="vol_breakout",
            version="1.0",
            applicable_regimes=[MarketRegime.BREAKOUT_PENDING, MarketRegime.MEAN_REVERTING],
            min_bars=100,
        )
        self._trend = TrendIndicators()
        self._vol = VolatilityIndicators()
        self._volume = VolumeIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        df = self._compute(df)

        squeeze_fire = df.get("squeeze_fire", pd.Series(0)).iloc[-1]
        if not squeeze_fire:
            # Also check Donchian breakout
            dc_up = df.get("dc_breakout_up", pd.Series(0)).iloc[-1]
            dc_down = df.get("dc_breakout_down", pd.Series(0)).iloc[-1]
            if not dc_up and not dc_down:
                return None

            direction = SignalDirection.LONG if dc_up else SignalDirection.SHORT
        else:
            momentum = df.get("squeeze_momentum", pd.Series(0)).iloc[-1]
            direction = SignalDirection.LONG if momentum > 0 else SignalDirection.SHORT

        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, direction)

        vol_confirm = self.volume_confirmation(df, threshold=1.3)
        confidence = 65 + (15 if vol_confirm else 0) + (10 if squeeze_fire else 0)
        strength = SignalStrength.STRONG if squeeze_fire and vol_confirm else SignalStrength.MODERATE

        return TradeSignal(
            symbol=symbol, direction=direction, strength=strength,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"{'Squeeze fire' if squeeze_fire else 'Donchian breakout'}, "
                      f"Volume confirm={'Yes' if vol_confirm else 'No'}",
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 1.5, 2.5, 4.0, 6.0)

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._vol.atr(df)
        df = self._vol.bollinger_bands(df)
        df = self._vol.ttm_squeeze(df)
        df = self._vol.donchian(df)
        df = self._volume.volume_roc(df)
        return df
