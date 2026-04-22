"""
APEX INDIA — Market Regime Detector
=======================================
Multi-factor regime classification engine that identifies the
current market state to activate appropriate strategies.

7 Regimes:
- TRENDING_BULLISH:  ADX>25, +DI>-DI, price>EMA200, breadth>60%
- TRENDING_BEARISH:  ADX>25, -DI>+DI, price<EMA200, breadth<40%
- MEAN_REVERTING:    ADX<20, narrow BB width, low ATR
- HIGH_VOLATILITY:   VIX>25, ATR expanding, BB bandwidth high
- BREAKOUT_PENDING:  TTM squeeze on, narrow range, volume contraction
- DISTRIBUTION:      Price near highs but OBV diverging, smart money selling
- ACCUMULATION:      Price near lows but OBV rising, smart money buying

Updates every 15 minutes during market hours.

Usage:
    detector = RegimeDetector()
    regime = detector.detect(nifty_df, vix=15.2, breadth={"advance_pct": 62})
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from apex_india.strategies.base_strategy import MarketRegime
from apex_india.data.indicators.trend import TrendIndicators
from apex_india.data.indicators.momentum import MomentumIndicators
from apex_india.data.indicators.volatility import VolatilityIndicators
from apex_india.data.indicators.volume import VolumeIndicators
from apex_india.utils.logger import get_logger

logger = get_logger("models.regime")


class RegimeDetector:
    """
    Multi-factor market regime classification.

    Scoring approach: each regime has a probability score
    based on multiple confirming/denying factors. The regime
    with the highest score wins.
    """

    def __init__(self):
        self._trend = TrendIndicators()
        self._momentum = MomentumIndicators()
        self._volatility = VolatilityIndicators()
        self._volume = VolumeIndicators()

        self._current_regime = MarketRegime.UNKNOWN
        self._regime_history: List[MarketRegime] = []
        self._scores: Dict[str, float] = {}

    # ───────────────────────────────────────────────────────────
    # Main Detection
    # ───────────────────────────────────────────────────────────

    def detect(
        self,
        df: pd.DataFrame,
        vix: Optional[float] = None,
        breadth: Optional[Dict] = None,
        pcr: Optional[float] = None,
    ) -> MarketRegime:
        """
        Detect the current market regime.

        Args:
            df: Nifty 50 (or benchmark) OHLCV DataFrame (min 200 bars)
            vix: Current India VIX value (optional)
            breadth: Market breadth dict with advance_pct (optional)
            pcr: Put-Call Ratio (optional)

        Returns:
            MarketRegime enum value
        """
        if df is None or len(df) < 50:
            return MarketRegime.UNKNOWN

        # Compute indicators
        df_ind = self._compute_indicators(df)

        # Score each regime
        scores = {
            MarketRegime.TRENDING_BULLISH: self._score_trending_bullish(df_ind, vix, breadth),
            MarketRegime.TRENDING_BEARISH: self._score_trending_bearish(df_ind, vix, breadth),
            MarketRegime.MEAN_REVERTING: self._score_mean_reverting(df_ind, vix),
            MarketRegime.HIGH_VOLATILITY: self._score_high_volatility(df_ind, vix),
            MarketRegime.BREAKOUT_PENDING: self._score_breakout_pending(df_ind),
            MarketRegime.DISTRIBUTION: self._score_distribution(df_ind, breadth),
            MarketRegime.ACCUMULATION: self._score_accumulation(df_ind, breadth),
        }

        self._scores = {k.value: round(v, 1) for k, v in scores.items()}

        # Winner takes all
        best_regime = max(scores, key=scores.get)
        best_score = scores[best_regime]

        # Minimum confidence threshold
        if best_score < 30:
            best_regime = MarketRegime.UNKNOWN

        # Update history
        self._regime_history.append(best_regime)
        if len(self._regime_history) > 100:
            self._regime_history = self._regime_history[-100:]

        prev = self._current_regime
        self._current_regime = best_regime

        if best_regime != prev:
            logger.info(
                f"Regime change: {prev.value} -> {best_regime.value} "
                f"(score={best_score:.1f})"
            )

        return best_regime

    # ───────────────────────────────────────────────────────────
    # Indicator Computation
    # ───────────────────────────────────────────────────────────

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute required indicators for regime detection."""
        df = df.copy()
        df = self._trend.ema(df, periods=[21, 50, 200])
        df = self._trend.adx(df)
        df = self._trend.supertrend(df)
        df = self._momentum.rsi(df)
        df = self._volatility.atr(df)
        df = self._volatility.bollinger_bands(df)
        df = self._volume.obv(df)
        df = self._volume.cmf(df)
        return df

    # ───────────────────────────────────────────────────────────
    # Regime Scorers (0-100 each)
    # ───────────────────────────────────────────────────────────

    def _score_trending_bullish(
        self, df: pd.DataFrame, vix: Optional[float], breadth: Optional[Dict]
    ) -> float:
        score = 0.0

        # ADX > 25 and +DI > -DI
        if "adx" in df.columns:
            adx = df["adx"].iloc[-1]
            if adx > 25:
                score += 20
            if "plus_di" in df.columns and "minus_di" in df.columns:
                if df["plus_di"].iloc[-1] > df["minus_di"].iloc[-1]:
                    score += 15

        # Price above EMA 200
        if "ema_200" in df.columns:
            if df["close"].iloc[-1] > df["ema_200"].iloc[-1]:
                score += 15

        # EMA alignment (21 > 50 > 200)
        if all(f"ema_{p}" in df.columns for p in [21, 50, 200]):
            e21 = df["ema_21"].iloc[-1]
            e50 = df["ema_50"].iloc[-1]
            e200 = df["ema_200"].iloc[-1]
            if e21 > e50 > e200:
                score += 15

        # RSI > 50
        if "rsi" in df.columns and df["rsi"].iloc[-1] > 50:
            score += 10

        # OBV trending up
        if "obv_trend" in df.columns and df["obv_trend"].iloc[-1] > 0:
            score += 10

        # VIX < 20 (calm market favors trend)
        if vix is not None and vix < 20:
            score += 5

        # Breadth > 60%
        if breadth and breadth.get("advance_pct", 50) > 60:
            score += 10

        return min(100, score)

    def _score_trending_bearish(
        self, df: pd.DataFrame, vix: Optional[float], breadth: Optional[Dict]
    ) -> float:
        score = 0.0

        if "adx" in df.columns:
            if df["adx"].iloc[-1] > 25:
                score += 20
            if "plus_di" in df.columns and "minus_di" in df.columns:
                if df["minus_di"].iloc[-1] > df["plus_di"].iloc[-1]:
                    score += 15

        if "ema_200" in df.columns:
            if df["close"].iloc[-1] < df["ema_200"].iloc[-1]:
                score += 15

        if all(f"ema_{p}" in df.columns for p in [21, 50, 200]):
            e21 = df["ema_21"].iloc[-1]
            e50 = df["ema_50"].iloc[-1]
            e200 = df["ema_200"].iloc[-1]
            if e21 < e50 < e200:
                score += 15

        if "rsi" in df.columns and df["rsi"].iloc[-1] < 50:
            score += 10

        if "obv_trend" in df.columns and df["obv_trend"].iloc[-1] < 0:
            score += 10

        if vix is not None and vix > 20:
            score += 5

        if breadth and breadth.get("advance_pct", 50) < 40:
            score += 10

        return min(100, score)

    def _score_mean_reverting(
        self, df: pd.DataFrame, vix: Optional[float]
    ) -> float:
        score = 0.0

        # ADX < 20 (no trend)
        if "adx" in df.columns and df["adx"].iloc[-1] < 20:
            score += 25

        # Narrow BB width (squeeze)
        if "bb_bandwidth" in df.columns:
            bw = df["bb_bandwidth"].iloc[-1]
            avg_bw = df["bb_bandwidth"].tail(50).mean()
            if bw < avg_bw * 0.7:
                score += 20

        # RSI near 50 (neutral)
        if "rsi" in df.columns:
            rsi = df["rsi"].iloc[-1]
            if 40 < rsi < 60:
                score += 15

        # Low ATR ratio
        if "atr_ratio" in df.columns and df["atr_ratio"].iloc[-1] < 0.8:
            score += 15

        # Low VIX
        if vix is not None and vix < 15:
            score += 10

        # Supertrend flipping frequently
        if "supertrend_direction" in df.columns:
            flips = (df["supertrend_direction"].tail(20).diff().abs() > 0).sum()
            if flips > 4:
                score += 15

        return min(100, score)

    def _score_high_volatility(
        self, df: pd.DataFrame, vix: Optional[float]
    ) -> float:
        score = 0.0

        # VIX > 25
        if vix is not None:
            if vix > 35:
                score += 30
            elif vix > 25:
                score += 20

        # ATR expanding
        if "atr_expanding" in df.columns and df["atr_expanding"].iloc[-1]:
            score += 15

        if "atr_ratio" in df.columns and df["atr_ratio"].iloc[-1] > 1.5:
            score += 15

        # Wide BB bandwidth
        if "bb_bandwidth" in df.columns:
            bw = df["bb_bandwidth"].iloc[-1]
            avg_bw = df["bb_bandwidth"].tail(50).mean()
            if bw > avg_bw * 1.5:
                score += 15

        # Large daily ranges
        if len(df) >= 5:
            recent_range = ((df["high"] - df["low"]) / df["close"]).tail(5).mean()
            if recent_range > 0.03:  # 3% average daily range
                score += 15

        return min(100, score)

    def _score_breakout_pending(self, df: pd.DataFrame) -> float:
        score = 0.0

        # ADX low but rising
        if "adx" in df.columns:
            adx = df["adx"].iloc[-1]
            adx_prev = df["adx"].iloc[-5] if len(df) >= 5 else adx
            if adx < 20 and adx > adx_prev:
                score += 20

        # BB squeeze
        if "bb_squeeze" in df.columns and df["bb_squeeze"].iloc[-1]:
            score += 25

        # Narrow range (NR4/NR7)
        if len(df) >= 7:
            ranges = (df["high"] - df["low"]).tail(7)
            if ranges.iloc[-1] <= ranges.min():
                score += 20

        # Volume contraction
        if "volume" in df.columns and len(df) >= 20:
            vol_ratio = df["volume"].iloc[-1] / df["volume"].tail(20).mean()
            if vol_ratio < 0.6:
                score += 15

        # Price near EMA cluster (21, 50 within 1%)
        if all(f"ema_{p}" in df.columns for p in [21, 50]):
            e21 = df["ema_21"].iloc[-1]
            e50 = df["ema_50"].iloc[-1]
            spread = abs(e21 - e50) / e50
            if spread < 0.01:
                score += 15

        return min(100, score)

    def _score_distribution(
        self, df: pd.DataFrame, breadth: Optional[Dict]
    ) -> float:
        score = 0.0

        # Price near highs but OBV diverging (bearish divergence)
        if len(df) >= 20:
            price_near_high = df["close"].iloc[-1] >= df["close"].tail(20).quantile(0.9)
            if price_near_high:
                score += 15

            if "obv" in df.columns:
                obv_near_high = df["obv"].iloc[-1] >= df["obv"].tail(20).quantile(0.9)
                if price_near_high and not obv_near_high:
                    score += 25  # Bearish OBV divergence

        # CMF turning negative
        if "cmf" in df.columns and df["cmf"].iloc[-1] < -0.05:
            score += 15

        # RSI divergence
        if "rsi_bearish_div" in df.columns and df["rsi_bearish_div"].tail(5).sum() > 0:
            score += 15

        # Breadth deteriorating
        if breadth and breadth.get("advance_pct", 50) < 45:
            score += 10

        return min(100, score)

    def _score_accumulation(
        self, df: pd.DataFrame, breadth: Optional[Dict]
    ) -> float:
        score = 0.0

        # Price near lows but OBV rising (bullish divergence)
        if len(df) >= 20:
            price_near_low = df["close"].iloc[-1] <= df["close"].tail(20).quantile(0.1)
            if price_near_low:
                score += 15

            if "obv" in df.columns:
                obv_rising = df["obv"].iloc[-1] > df["obv"].tail(20).mean()
                if price_near_low and obv_rising:
                    score += 25  # Bullish OBV divergence

        # CMF turning positive
        if "cmf" in df.columns and df["cmf"].iloc[-1] > 0.05:
            score += 15

        # RSI divergence
        if "rsi_bullish_div" in df.columns and df["rsi_bullish_div"].tail(5).sum() > 0:
            score += 15

        # Breadth improving
        if breadth and breadth.get("advance_pct", 50) > 55:
            score += 10

        return min(100, score)

    # ───────────────────────────────────────────────────────────
    # API
    # ───────────────────────────────────────────────────────────

    @property
    def current_regime(self) -> MarketRegime:
        return self._current_regime

    @property
    def scores(self) -> Dict[str, float]:
        return dict(self._scores)

    @property
    def regime_history(self) -> List[str]:
        return [r.value for r in self._regime_history[-20:]]

    def get_report(self) -> Dict[str, Any]:
        """Full regime report."""
        return {
            "current_regime": self._current_regime.value,
            "scores": self._scores,
            "history_last_20": self.regime_history,
            "regime_stability": self._regime_stability(),
        }

    def _regime_stability(self) -> str:
        """How stable is the current regime?"""
        if len(self._regime_history) < 5:
            return "insufficient_data"
        last_5 = self._regime_history[-5:]
        if all(r == last_5[0] for r in last_5):
            return "stable"
        elif sum(1 for r in last_5 if r == self._current_regime) >= 3:
            return "mostly_stable"
        else:
            return "transitioning"
