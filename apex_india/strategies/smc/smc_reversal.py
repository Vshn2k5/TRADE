"""
APEX INDIA — Strategy #8: SMC Reversal (Smart Money Concepts)
================================================================
Trades reversals at institutional order block levels using
Break of Structure (BOS), Change of Character (CHoCH), and
Fair Value Gaps (FVG).

Entry: CHoCH confirmed + price enters order block zone + FVG fill.
Exit:  Opposing BOS or 2-ATR stop.
Regime: DISTRIBUTION, ACCUMULATION
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators


class SMCReversal(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="smc_reversal",
            version="1.0",
            applicable_regimes=[MarketRegime.DISTRIBUTION, MarketRegime.ACCUMULATION],
            min_bars=50,
        )
        self._vol = VolatilityIndicators()
        self._volume = VolumeIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        df = self._compute(df)

        # Detect structure
        bos_bull, bos_bear = self._detect_bos(df)
        choch_bull, choch_bear = self._detect_choch(df)
        fvg_bull, fvg_bear = self._detect_fvg(df)
        ob_bull, ob_bear = self._detect_order_blocks(df)

        direction = None
        reasons = []

        # Bullish reversal: CHoCH bullish + order block + FVG
        if choch_bull:
            direction = SignalDirection.LONG
            reasons.append("CHoCH bullish")
            if ob_bull:
                reasons.append("demand OB")
            if fvg_bull:
                reasons.append("FVG fill")
        elif choch_bear:
            direction = SignalDirection.SHORT
            reasons.append("CHoCH bearish")
            if ob_bear:
                reasons.append("supply OB")
            if fvg_bear:
                reasons.append("FVG fill")

        if direction is None:
            return None

        entry = round(df["close"].iloc[-1], 2)
        sl, targets = self.compute_targets(df, entry, direction)
        confidence = 55 + len(reasons) * 10

        return TradeSignal(
            symbol=symbol, direction=direction,
            strength=SignalStrength.MODERATE if len(reasons) < 3 else SignalStrength.STRONG,
            strategy_name=self.name, entry_price=entry,
            stop_loss=sl, targets=targets, confidence=confidence,
            regime=regime,
            reasoning=f"SMC: {', '.join(reasons)}",
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 2.0, 3.0, 5.0, 7.0)

    # ── SMC Pattern Detection ──

    def _detect_bos(self, df: pd.DataFrame, lookback: int = 10) -> Tuple[bool, bool]:
        """Break of Structure: price breaks recent swing high/low."""
        if len(df) < lookback + 1:
            return False, False

        recent_high = df["high"].iloc[-lookback-1:-1].max()
        recent_low = df["low"].iloc[-lookback-1:-1].min()

        bos_bull = df["close"].iloc[-1] > recent_high
        bos_bear = df["close"].iloc[-1] < recent_low

        return bos_bull, bos_bear

    def _detect_choch(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[bool, bool]:
        """
        Change of Character: trend reversal signal.
        Downtrend making lower lows, then breaks a lower high = bullish CHoCH.
        """
        if len(df) < lookback + 5:
            return False, False

        subset = df.iloc[-lookback:]
        mid = len(subset) // 2

        first_half = subset.iloc[:mid]
        second_half = subset.iloc[mid:]

        # Bullish CHoCH: first half trending down, second half breaks up
        first_down = first_half["close"].iloc[-1] < first_half["close"].iloc[0]
        second_break_up = second_half["close"].iloc[-1] > first_half["high"].max()
        choch_bull = first_down and second_break_up

        # Bearish CHoCH
        first_up = first_half["close"].iloc[-1] > first_half["close"].iloc[0]
        second_break_down = second_half["close"].iloc[-1] < first_half["low"].min()
        choch_bear = first_up and second_break_down

        return choch_bull, choch_bear

    def _detect_fvg(self, df: pd.DataFrame) -> Tuple[bool, bool]:
        """
        Fair Value Gap: 3-candle pattern where there's a gap
        between candle 1's high and candle 3's low.
        """
        if len(df) < 3:
            return False, False

        c1_high = df["high"].iloc[-3]
        c3_low = df["low"].iloc[-1]
        c1_low = df["low"].iloc[-3]
        c3_high = df["high"].iloc[-1]

        fvg_bull = c3_low > c1_high  # Gap up
        fvg_bear = c3_high < c1_low  # Gap down

        return fvg_bull, fvg_bear

    def _detect_order_blocks(self, df: pd.DataFrame) -> Tuple[bool, bool]:
        """
        Order Block: last opposing candle before a strong move.
        Bullish OB: last red candle before a strong green candle.
        """
        if len(df) < 5:
            return False, False

        # Check if price is near a recent order block
        last_5 = df.tail(5)
        bodies = last_5["close"] - last_5["open"]

        # Bullish OB: find bearish candle followed by bullish
        ob_bull = False
        ob_bear = False
        for i in range(len(bodies) - 1):
            if bodies.iloc[i] < 0 and bodies.iloc[i+1] > 0:
                if abs(bodies.iloc[i+1]) > 2 * abs(bodies.iloc[i]):
                    ob_bull = True
            if bodies.iloc[i] > 0 and bodies.iloc[i+1] < 0:
                if abs(bodies.iloc[i+1]) > 2 * abs(bodies.iloc[i]):
                    ob_bear = True

        return ob_bull, ob_bear

    def _compute(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._vol.atr(df)
        return df
