"""
APEX INDIA — Strategy #10: Swing Positional
==============================================
Multi-day positional strategy for capturing larger swings.
Uses weekly structure + daily entry for holding 5-20 days.

Entry: ADX>20, EMA aligned, Supertrend confirms, weekly trend up,
       pullback into 21-EMA zone (value area).
Exit:  EMA 21 cross below 50, or trailing 2.5-ATR stop.
Regime: Any where ADX > 20
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


class SwingPositional(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="swing_positional",
            version="1.0",
            applicable_regimes=[
                MarketRegime.TRENDING_BULLISH, MarketRegime.TRENDING_BEARISH,
                MarketRegime.BREAKOUT_PENDING, MarketRegime.ACCUMULATION,
            ],
            min_bars=200,
            timeframe="day",
        )
        self._trend = TrendIndicators()
        self._momentum = MomentumIndicators()
        self._vol = VolatilityIndicators()
        self._volume = VolumeIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        df = self._compute(df)

        # Trend filter: ADX > 20
        adx = df["adx"].iloc[-1] if "adx" in df.columns else 0
        if adx < 20:
            return None

        # EMA structure
        ema_21 = df["ema_21"].iloc[-1] if "ema_21" in df.columns else 0
        ema_50 = df["ema_50"].iloc[-1] if "ema_50" in df.columns else 0
        ema_200 = df["ema_200"].iloc[-1] if "ema_200" in df.columns else 0

        close = df["close"].iloc[-1]
        direction = None

        # Bullish swing: price above 200 EMA, pullback to 21 EMA zone
        if close > ema_200 and ema_21 > ema_50:
            # Price near 21 EMA (within 1.5%)
            dist_to_21 = abs(close - ema_21) / ema_21 if ema_21 > 0 else 1
            if dist_to_21 < 0.015:
                # Bounce confirmation: current close > open (bullish candle)
                if close > df["open"].iloc[-1]:
                    direction = SignalDirection.LONG

        # Bearish swing: price below 200 EMA, pullback to 21 EMA zone
        elif close < ema_200 and ema_21 < ema_50:
            dist_to_21 = abs(close - ema_21) / ema_21 if ema_21 > 0 else 1
            if dist_to_21 < 0.015:
                if close < df["open"].iloc[-1]:
                    direction = SignalDirection.SHORT

        if direction is None:
            return None

        entry = round(close, 2)
        sl, targets = self.compute_targets(df, entry, direction)

        # Volume should be average or above
        vol_confirm = self.volume_confirmation(df, threshold=0.8)
        rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50

        confidence = 65
        if vol_confirm:
            confidence += 10
        if adx > 30:
            confidence += 5
        if df.get("supertrend_direction", pd.Series(0)).iloc[-1] == (1 if direction == SignalDirection.LONG else -1):
            confidence += 10

        return TradeSignal(
            symbol=symbol, direction=direction,
            strength=SignalStrength.STRONG if confidence >= 80 else SignalStrength.MODERATE,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"Swing {direction.value}: pullback to 21-EMA zone, "
                      f"ADX={adx:.1f}, RSI={rsi:.1f}",
            metadata={"max_hold_days": 20},
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 2.5, 3.0, 5.0, 8.0)

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._trend.ema(df, periods=[21, 50, 200])
        df = self._trend.adx(df)
        df = self._trend.supertrend(df)
        df = self._momentum.rsi(df)
        df = self._vol.atr(df)
        return df
