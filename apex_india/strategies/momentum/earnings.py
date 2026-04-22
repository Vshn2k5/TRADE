"""
APEX INDIA — Strategy #5: Earnings Momentum
==============================================
Trades the post-earnings momentum after strong results.

Entry: Stock gaps up/down >3% post-earnings on high volume,
       RSI confirms direction, sector context is supportive.
Exit:  5-day maximum hold, or 2-ATR trailing stop.
Regime: Post-earnings (any regime)
"""

import pandas as pd
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.momentum import MomentumIndicators
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators


class EarningsMomentum(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="earnings",
            version="1.0",
            applicable_regimes=list(MarketRegime),  # Any regime
            min_bars=20,
        )
        self._momentum = MomentumIndicators()
        self._vol = VolatilityIndicators()
        self._volume = VolumeIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        df = self._compute(df)

        if len(df) < 5:
            return None

        # Detect earnings gap (>3% move on 2x+ volume)
        gap_pct = ((df["open"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]) * 100
        vol_ratio = df["volume"].iloc[-1] / df["volume"].tail(20).mean()

        if abs(gap_pct) < 3.0 or vol_ratio < 2.0:
            return None

        direction = SignalDirection.LONG if gap_pct > 0 else SignalDirection.SHORT

        # RSI confirmation
        rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50
        if direction == SignalDirection.LONG and rsi < 45:
            return None
        if direction == SignalDirection.SHORT and rsi > 55:
            return None

        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, direction)

        confidence = 70 + min(10, int(abs(gap_pct)))
        strength = SignalStrength.STRONG if abs(gap_pct) > 5 else SignalStrength.MODERATE

        return TradeSignal(
            symbol=symbol, direction=direction, strength=strength,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"Earnings gap {gap_pct:+.1f}%, "
                      f"Volume {vol_ratio:.1f}x avg, RSI={rsi:.1f}",
            metadata={"max_hold_days": 5},
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 2.0, 2.0, 3.0, 5.0)

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._momentum.rsi(df)
        df = self._vol.atr(df)
        return df
