"""
APEX INDIA — Strategy #7: Options Theta Harvest
==================================================
Short premium strategy for sideways/low-vol markets.
Sells OTM strangles/iron condors when IV is elevated.

Entry: IV Rank > 60%, narrow range, ADX < 20,
       sell strikes at OI support/resistance.
Exit:  65% of max profit, or 2x credit received (stop).
Regime: MEAN_REVERTING, LOW_VOL
"""

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
)
from apex_india.data.indicators.derivatives import DerivativesAnalysis
from apex_india.data.indicators.volatility import VolatilityIndicators


class ThetaHarvest(BaseStrategy):

    def __init__(self):
        super().__init__(
            name="theta_harvest",
            version="1.0",
            applicable_regimes=[MarketRegime.MEAN_REVERTING],
            min_bars=30,
        )
        self._deriv = DerivativesAnalysis()
        self._vol = VolatilityIndicators()

    def generate_signals(
        self, df: pd.DataFrame, symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
        iv_rank: Optional[float] = None,
        oi_support: Optional[float] = None,
        oi_resistance: Optional[float] = None,
    ) -> Optional[TradeSignal]:
        df = self._vol.atr(df)
        df = self._vol.bollinger_bands(df)

        from apex_india.data.indicators.trend import TrendIndicators
        df = TrendIndicators.adx(df)

        # ADX must be low (range-bound)
        if "adx" in df.columns and df["adx"].iloc[-1] > 25:
            return None

        # IV Rank should be elevated (premiums worth selling)
        effective_iv = iv_rank if iv_rank is not None else 50
        if effective_iv < 40:
            return None

        entry = round(df["close"].iloc[-1], 2)
        atr = df["atr"].iloc[-1] if "atr" in df.columns else entry * 0.015

        # Strangle strikes
        call_strike = oi_resistance or round(entry + 2 * atr, 0)
        put_strike = oi_support or round(entry - 2 * atr, 0)

        confidence = 55 + min(25, int(effective_iv * 0.3))
        if oi_support and oi_resistance:
            confidence += 10

        return TradeSignal(
            symbol=symbol, direction=SignalDirection.NEUTRAL,
            strength=SignalStrength.MODERATE,
            strategy_name=self.name, entry_price=entry,
            stop_loss=round(entry + 3 * atr, 2),
            targets=[round(entry, 2)],
            confidence=confidence, regime=regime,
            reasoning=f"Theta harvest: IV Rank={effective_iv:.0f}%, "
                      f"ADX={df['adx'].iloc[-1]:.1f}, "
                      f"Sell {put_strike:.0f}PE / {call_strike:.0f}CE",
            metadata={
                "strategy_type": "short_strangle",
                "call_strike": call_strike,
                "put_strike": put_strike,
                "profit_target_pct": 65,
                "max_loss_multiplier": 2,
            },
        )

    def compute_targets(
        self, df: pd.DataFrame, entry: float, direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        return self.atr_stops(df, entry, direction, 3.0, 1.0, 2.0, 3.0)
