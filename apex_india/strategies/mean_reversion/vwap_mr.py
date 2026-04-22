"""
APEX INDIA — Strategy #3: VWAP Mean Reversion
================================================
Fades overextended moves back toward VWAP in range-bound markets.

Entry: Price > 2 std devs from VWAP, RSI overbought/oversold,
       CMF diverging from price, low ADX.
Exit:  Price touches VWAP, or 1.5-ATR stop.
Regime: MEAN_REVERTING
"""

import pandas as pd
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.momentum import MomentumIndicators
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators
from apex_india.data.processors.feature_engineer import FeatureEngineer


class VWAPMeanReversion(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="vwap_mr",
            version="1.0",
            applicable_regimes=[MarketRegime.MEAN_REVERTING],
            min_bars=50,
        )
        self._momentum = MomentumIndicators()
        self._vol = VolatilityIndicators()
        self._volume = VolumeIndicators()
        self._fe = FeatureEngineer()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        df = self._compute(df)

        if "vwap_position" not in df.columns:
            return None

        vwap_pos = df["vwap_position"].iloc[-1]
        rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50

        # Short: price > 2 std devs above VWAP + RSI overbought
        if vwap_pos > 2.0 and rsi > 70:
            direction = SignalDirection.SHORT
        # Long: price > 2 std devs below VWAP + RSI oversold
        elif vwap_pos < -2.0 and rsi < 30:
            direction = SignalDirection.LONG
        else:
            return None

        # ADX filter: only trade MR in low-trend environments
        if "adx" in df.columns and df["adx"].iloc[-1] > 25:
            return None

        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, direction)

        cmf = df.get("cmf", pd.Series(0)).iloc[-1]
        confidence = 60
        if direction == SignalDirection.LONG and cmf > 0:
            confidence += 10
        elif direction == SignalDirection.SHORT and cmf < 0:
            confidence += 10

        return TradeSignal(
            symbol=symbol, direction=direction,
            strength=SignalStrength.MODERATE,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"VWAP position={vwap_pos:.1f} std devs, "
                      f"RSI={rsi:.1f}, CMF={cmf:.3f}",
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        # VWAP is the primary target
        vwap = df.get("vwap", pd.Series(entry)).iloc[-1]
        if direction == SignalDirection.LONG:
            t1 = round(vwap, 2)
        else:
            t1 = round(vwap, 2)

        sl, atr_targets = self.atr_stops(df, entry, direction, 1.5, 1.5, 2.5, 3.5)
        targets = [t1] + atr_targets[1:]
        return sl, targets

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._fe.compute_vwap(df)
        df = self._momentum.rsi(df)
        df = self._vol.atr(df)
        from apex_india.data.indicators.trend import TrendIndicators
        df = TrendIndicators.adx(df)
        df = self._volume.cmf(df)
        return df
