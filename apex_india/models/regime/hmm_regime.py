"""
APEX INDIA — HMM Regime Classifier
=====================================
Hidden Markov Model for probabilistic market regime detection.
Falls back to K-Means clustering if hmmlearn is unavailable.

States: maps to MarketRegime enum via feature-based labeling.

Usage:
    hmm = HMMRegimeClassifier(n_states=4)
    hmm.fit(df)
    state = hmm.predict(df)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from apex_india.strategies.base_strategy import MarketRegime
from apex_india.utils.logger import get_logger

logger = get_logger("models.regime.hmm")

try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMM = True
except ImportError:
    HAS_HMM = False

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class HMMRegimeClassifier:
    """
    Probabilistic regime classification using HMM or K-Means fallback.
    """

    # Map cluster/state IDs to regimes by feature characteristics
    REGIME_LABELS = [
        MarketRegime.TRENDING_BULLISH,
        MarketRegime.TRENDING_BEARISH,
        MarketRegime.MEAN_REVERTING,
        MarketRegime.HIGH_VOLATILITY,
    ]

    def __init__(self, n_states: int = 4, seed: int = 42):
        self.n_states = min(n_states, len(self.REGIME_LABELS))
        self.seed = seed
        self._model = None
        self._scaler = None
        self._is_fitted = False
        self._state_map: Dict[int, MarketRegime] = {}

    # ───────────────────────────────────────────────────────────
    # Feature Engineering
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def build_features(df: pd.DataFrame) -> pd.DataFrame:
        """Build regime features from OHLCV."""
        feat = pd.DataFrame(index=df.index)

        returns = df["close"].pct_change()
        feat["return_5d"] = returns.rolling(5).mean()
        feat["return_20d"] = returns.rolling(20).mean()
        feat["volatility_10d"] = returns.rolling(10).std()
        feat["volatility_20d"] = returns.rolling(20).std()

        # Trend strength
        if len(df) >= 50:
            feat["trend"] = (df["close"] / df["close"].rolling(50).mean()) - 1

        # Range contraction
        feat["range_ratio"] = (df["high"] - df["low"]) / df["close"]

        # Volume trend
        if "volume" in df.columns:
            feat["volume_trend"] = (
                df["volume"].rolling(5).mean() / df["volume"].rolling(20).mean()
            )

        return feat.dropna()

    # ───────────────────────────────────────────────────────────
    # Training
    # ───────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit the regime model.
        """
        features = self.build_features(df)
        if len(features) < 50:
            return {"error": "Insufficient data for regime model"}

        if not HAS_SKLEARN:
            return {"error": "scikit-learn required"}

        self._scaler = StandardScaler()
        X = self._scaler.fit_transform(features.values)

        if HAS_HMM:
            logger.info("Fitting GaussianHMM regime model")
            self._model = GaussianHMM(
                n_components=self.n_states,
                covariance_type="full",
                n_iter=200,
                random_state=self.seed,
            )
            self._model.fit(X)
            states = self._model.predict(X)
        else:
            logger.info("Fitting K-Means regime model (HMM not available)")
            self._model = KMeans(
                n_clusters=self.n_states,
                random_state=self.seed,
                n_init=10,
            )
            states = self._model.fit_predict(X)

        # Label states by feature characteristics
        self._label_states(features, states)
        self._is_fitted = True

        # State distribution
        unique, counts = np.unique(states, return_counts=True)
        dist = {self._state_map.get(s, MarketRegime.UNKNOWN).value: int(c)
                for s, c in zip(unique, counts)}

        return {
            "model": "HMM" if HAS_HMM else "KMeans",
            "n_states": self.n_states,
            "samples": len(features),
            "state_distribution": dist,
        }

    def _label_states(self, features: pd.DataFrame, states: np.ndarray) -> None:
        """Map numeric states to MarketRegime by feature characteristics."""
        df_states = features.copy()
        df_states["state"] = states

        for state_id in range(self.n_states):
            mask = df_states["state"] == state_id
            if not mask.any():
                self._state_map[state_id] = MarketRegime.UNKNOWN
                continue

            cluster = df_states[mask]
            mean_return = cluster["return_20d"].mean() if "return_20d" in cluster else 0
            mean_vol = cluster["volatility_20d"].mean() if "volatility_20d" in cluster else 0

            # Label based on return + volatility
            if mean_vol > cluster["volatility_20d"].quantile(0.75):
                self._state_map[state_id] = MarketRegime.HIGH_VOLATILITY
            elif mean_return > 0.001:
                self._state_map[state_id] = MarketRegime.TRENDING_BULLISH
            elif mean_return < -0.001:
                self._state_map[state_id] = MarketRegime.TRENDING_BEARISH
            else:
                self._state_map[state_id] = MarketRegime.MEAN_REVERTING

    # ───────────────────────────────────────────────────────────
    # Prediction
    # ───────────────────────────────────────────────────────────

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict current regime.

        Returns:
            {regime: str, state_id: int, probabilities: dict}
        """
        if not self._is_fitted:
            return {"regime": MarketRegime.UNKNOWN.value, "reason": "Not fitted"}

        features = self.build_features(df)
        if len(features) == 0:
            return {"regime": MarketRegime.UNKNOWN.value, "reason": "No features"}

        X = self._scaler.transform(features.iloc[[-1]].values)

        if HAS_HMM and hasattr(self._model, 'predict_proba'):
            state = self._model.predict(X)[0]
            proba = self._model.predict_proba(X)[0]
            probabilities = {
                self._state_map.get(i, MarketRegime.UNKNOWN).value: round(float(p), 4)
                for i, p in enumerate(proba)
            }
        else:
            state = self._model.predict(X)[0]
            probabilities = {}

        regime = self._state_map.get(state, MarketRegime.UNKNOWN)

        return {
            "regime": regime.value,
            "state_id": int(state),
            "probabilities": probabilities,
        }
