"""
APEX INDIA — Strategy #9: Gap Trade
======================================
Trades significant opening gaps (>0.5%) with institutional direction.

Entry: Gap > 0.5%, volume confirms, RSI not at extreme.
Exit:  Gap fill (mean reversion) or trailing ATR stop.
Regime: TRENDING (gap continuation), any (gap fill)
"""

import pandas as pd
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.momentum import MomentumIndicators
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators


class GapTrade(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="gap_trade",
            version="1.0",
            applicable_regimes=[
                MarketRegime.TRENDING_BULLISH, MarketRegime.TRENDING_BEARISH,
                MarketRegime.BREAKOUT_PENDING,
            ],
            min_bars=20,
        )
        self._momentum = MomentumIndicators()
        self._vol = VolatilityIndicators()
        self._volume = VolumeIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        if len(df) < 5:
            return None

        df = self._compute(df)

        # Gap detection
        prev_close = df["close"].iloc[-2]
        current_open = df["open"].iloc[-1]
        gap_pct = ((current_open - prev_close) / prev_close) * 100

        if abs(gap_pct) < 0.5:
            return None

        # Gap continuation (trade in gap direction)
        direction = SignalDirection.LONG if gap_pct > 0 else SignalDirection.SHORT

        # Volume check
        vol_confirm = self.volume_confirmation(df, threshold=1.2)

        # RSI filter (don't enter at extremes)
        rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50
        if direction == SignalDirection.LONG and rsi > 75:
            return None
        if direction == SignalDirection.SHORT and rsi < 25:
            return None

        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, direction)

        # Add gap fill as a potential exit target
        gap_fill = round(prev_close, 2)
        strength = SignalStrength.STRONG if abs(gap_pct) > 2 else SignalStrength.MODERATE
        confidence = 60 + min(15, int(abs(gap_pct) * 3)) + (10 if vol_confirm else 0)

        return TradeSignal(
            symbol=symbol, direction=direction, strength=strength,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"Gap {'up' if gap_pct > 0 else 'down'} {gap_pct:+.1f}%, "
                      f"RSI={rsi:.1f}, Vol confirm={'Yes' if vol_confirm else 'No'}",
            metadata={"gap_fill_level": gap_fill, "gap_pct": gap_pct},
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 1.5, 2.0, 3.0, 4.5)

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._momentum.rsi(df)
        df = self._vol.atr(df)
        return df
