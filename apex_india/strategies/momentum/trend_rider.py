"""
APEX INDIA — Strategy #1: Trend Momentum Rider
=================================================
Rides strong institutional trends using multi-timeframe
EMA alignment + ADX trend strength + Supertrend confirmation.

Entry: EMA aligned (21>50>200), ADX>25, Supertrend bullish,
       RSI>50, volume above average.
Exit:  Supertrend flip, or trailing 2-ATR stop.
Regime: TRENDING_BULLISH, TRENDING_BEARISH
"""

import pandas as pd
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.trend import TrendIndicators
from apex_india.data.indicators.momentum import MomentumIndicators
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators


class TrendMomentumRider(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="trend_rider",
            version="1.0",
            applicable_regimes=[
                MarketRegime.TRENDING_BULLISH,
                MarketRegime.TRENDING_BEARISH,
            ],
            min_bars=200,
            timeframe="day",
        )
        self._trend = TrendIndicators()
        self._momentum = MomentumIndicators()
        self._volatility = VolatilityIndicators()
        self._volume = VolumeIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        df = self._compute(df)

        # Long conditions
        long_cond = (
            df.get("ema_bullish_aligned", pd.Series(False)).iloc[-1] and
            df["adx"].iloc[-1] > 25 and
            df["supertrend_direction"].iloc[-1] == 1 and
            df["rsi"].iloc[-1] > 50 and
            df["rsi"].iloc[-1] < 75 and  # Not overbought
            df["obv_trend"].iloc[-1] > 0
        )

        # Short conditions
        short_cond = (
            df.get("ema_bearish_aligned", pd.Series(False)).iloc[-1] and
            df["adx"].iloc[-1] > 25 and
            df["supertrend_direction"].iloc[-1] == -1 and
            df["rsi"].iloc[-1] < 50 and
            df["rsi"].iloc[-1] > 25 and
            df["obv_trend"].iloc[-1] < 0
        )

        if not long_cond and not short_cond:
            return None

        direction = SignalDirection.LONG if long_cond else SignalDirection.SHORT
        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, direction)

        # Strength assessment
        adx = df["adx"].iloc[-1]
        strength = SignalStrength.STRONG if adx > 35 else SignalStrength.MODERATE

        vol_confirm = self.volume_confirmation(df)
        confidence = 70 + (10 if vol_confirm else 0) + (5 if adx > 35 else 0)

        return TradeSignal(
            symbol=symbol, direction=direction, strength=strength,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"Trend aligned, ADX={adx:.1f}, "
                      f"RSI={df['rsi'].iloc[-1]:.1f}, "
                      f"Supertrend={'Bull' if direction == SignalDirection.LONG else 'Bear'}",
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 2.0, 2.0, 3.5, 5.0)

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._trend.ema(df, periods=[21, 50, 200])
        df = self._trend.adx(df)
        df = self._trend.supertrend(df)
        df = self._momentum.rsi(df)
        df = self._volatility.atr(df)
        df = self._volume.obv(df)
        return df
