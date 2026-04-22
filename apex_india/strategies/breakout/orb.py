"""
APEX INDIA — Strategy #4: Opening Range Breakout (ORB)
========================================================
Trades breakout of the first 15/30-minute opening range.

Entry: Price closes above/below the OR high/low on volume.
Exit:  Counter-OR level is stop, targets at 1x/2x OR range.
Regime: Any (except HIGH_VOLATILITY)
"""

import pandas as pd
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.volatility import VolatilityIndicators


class OpeningRangeBreakout(BaseStrategy):

    def __init__(self, or_minutes: int = 15):
        super().__init__(
            name="orb",
            version="1.0",
            applicable_regimes=[
                MarketRegime.TRENDING_BULLISH, MarketRegime.TRENDING_BEARISH,
                MarketRegime.BREAKOUT_PENDING, MarketRegime.MEAN_REVERTING,
                MarketRegime.ACCUMULATION, MarketRegime.DISTRIBUTION,
            ],
            min_bars=20,
            timeframe="15min",
        )
        self.or_minutes = or_minutes
        self._vol = VolatilityIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        if len(df) < 5:
            return None

        df = self._vol.atr(df)

        # For daily data, simulate OR using first candle
        or_high = df["high"].iloc[0]
        or_low = df["low"].iloc[0]
        or_range = or_high - or_low

        if or_range <= 0:
            return None

        current_close = df["close"].iloc[-1]

        # Breakout detection
        if current_close > or_high:
            direction = SignalDirection.LONG
        elif current_close < or_low:
            direction = SignalDirection.SHORT
        else:
            return None

        entry = round(current_close, 2)
        sl, targets = self.compute_targets(df, entry, direction)

        # Override targets with OR-based levels
        if direction == SignalDirection.LONG:
            sl = round(or_low, 2)
            targets = [
                round(or_high + or_range, 2),
                round(or_high + 2 * or_range, 2),
                round(or_high + 3 * or_range, 2),
            ]
        else:
            sl = round(or_high, 2)
            targets = [
                round(or_low - or_range, 2),
                round(or_low - 2 * or_range, 2),
                round(or_low - 3 * or_range, 2),
            ]

        confidence = 65
        vol_confirm = self.volume_confirmation(df)
        if vol_confirm:
            confidence += 10

        return TradeSignal(
            symbol=symbol, direction=direction,
            strength=SignalStrength.MODERATE,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime, timeframe=self.timeframe,
            reasoning=f"OR breakout {'above' if direction == SignalDirection.LONG else 'below'} "
                      f"({or_low:.2f}-{or_high:.2f}), range={or_range:.2f}",
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 1.5, 1.5, 2.5, 3.5)
