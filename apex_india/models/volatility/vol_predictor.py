"""
APEX INDIA — Volatility Predictor
====================================
Forecasts future realized volatility for position sizing
and regime detection using statistical models.

Models:
- EWMA volatility (primary/fallback)
- GARCH(1,1) if arch library available
- Parkinson/Garman-Klass realized vol estimators

Usage:
    vp = VolatilityPredictor()
    forecast = vp.predict(df, horizon=5)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, Optional

from apex_india.utils.logger import get_logger

logger = get_logger("models.volatility")

# Optional GARCH import
try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False
    logger.info("arch library not installed — using EWMA fallback for vol prediction")


class VolatilityPredictor:
    """
    Multi-model volatility forecasting engine.
    """

    def __init__(self, trading_days: int = 252):
        self.trading_days = trading_days
        self._garch_model = None

    # ───────────────────────────────────────────────────────────
    # Realized Volatility Estimators
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def close_to_close_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Standard close-to-close realized volatility."""
        returns = np.log(df["close"] / df["close"].shift(1))
        return returns.rolling(window).std() * np.sqrt(252)

    @staticmethod
    def parkinson_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Parkinson volatility — uses high/low range."""
        hl = np.log(df["high"] / df["low"]) ** 2
        return np.sqrt(hl.rolling(window).mean() / (4 * np.log(2))) * np.sqrt(252)

    @staticmethod
    def garman_klass_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """Garman-Klass volatility — uses OHLC."""
        hl = 0.5 * np.log(df["high"] / df["low"]) ** 2
        co = (2 * np.log(2) - 1) * np.log(df["close"] / df["open"]) ** 2
        gk = hl - co
        return np.sqrt(gk.rolling(window).mean()) * np.sqrt(252)

    # ───────────────────────────────────────────────────────────
    # EWMA Forecast (always available)
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def ewma_vol(df: pd.DataFrame, decay: float = 0.94) -> float:
        """EWMA (RiskMetrics) volatility forecast."""
        returns = np.log(df["close"] / df["close"].shift(1)).dropna()
        if len(returns) < 10:
            return 0.0

        variance = returns.iloc[0] ** 2
        for r in returns.iloc[1:]:
            variance = decay * variance + (1 - decay) * r ** 2

        daily_vol = np.sqrt(variance)
        return round(float(daily_vol * np.sqrt(252)), 6)

    # ───────────────────────────────────────────────────────────
    # GARCH(1,1) Forecast
    # ───────────────────────────────────────────────────────────

    def garch_forecast(
        self,
        df: pd.DataFrame,
        horizon: int = 5,
    ) -> Dict[str, Any]:
        """
        Fit GARCH(1,1) and forecast volatility.

        Args:
            df: OHLCV DataFrame (min 100 bars)
            horizon: Forecast horizon in days

        Returns:
            Dict with forecast, annualized_vol, model_params
        """
        if not HAS_ARCH:
            # Fallback to EWMA
            ewma = self.ewma_vol(df)
            return {
                "model": "EWMA",
                "annualized_vol": ewma,
                "forecast_horizon": horizon,
                "daily_vol_forecast": round(ewma / np.sqrt(252), 6),
            }

        returns = np.log(df["close"] / df["close"].shift(1)).dropna() * 100

        if len(returns) < 100:
            ewma = self.ewma_vol(df)
            return {"model": "EWMA_fallback", "annualized_vol": ewma}

        try:
            model = arch_model(returns, vol="Garch", p=1, q=1, mean="Constant")
            result = model.fit(disp="off", show_warning=False)

            forecasts = result.forecast(horizon=horizon)
            variance_forecast = forecasts.variance.iloc[-1].values

            daily_vol = np.sqrt(variance_forecast) / 100  # Back from percentage
            annualized = daily_vol * np.sqrt(252)

            self._garch_model = result

            return {
                "model": "GARCH(1,1)",
                "annualized_vol": round(float(annualized[-1]), 6),
                "daily_vol_forecast": [round(float(v), 6) for v in daily_vol],
                "forecast_horizon": horizon,
                "params": {
                    "omega": round(float(result.params.get("omega", 0)), 8),
                    "alpha": round(float(result.params.get("alpha[1]", 0)), 6),
                    "beta": round(float(result.params.get("beta[1]", 0)), 6),
                },
                "aic": round(float(result.aic), 2),
                "bic": round(float(result.bic), 2),
            }

        except Exception as e:
            logger.warning(f"GARCH fit failed: {e} — falling back to EWMA")
            ewma = self.ewma_vol(df)
            return {"model": "EWMA_fallback", "annualized_vol": ewma, "error": str(e)}

    # ───────────────────────────────────────────────────────────
    # Composite Forecast
    # ───────────────────────────────────────────────────────────

    def predict(
        self,
        df: pd.DataFrame,
        horizon: int = 5,
    ) -> Dict[str, Any]:
        """
        Produce composite volatility forecast.
        Averages multiple estimators for robustness.
        """
        if len(df) < 20:
            return {"volatility": 0.0, "regime": "unknown"}

        # All estimators
        cc_vol = float(self.close_to_close_vol(df).iloc[-1]) if len(df) > 20 else 0
        pk_vol = float(self.parkinson_vol(df).iloc[-1]) if len(df) > 20 else 0
        gk_vol = float(self.garman_klass_vol(df).iloc[-1]) if len(df) > 20 else 0
        ewma = self.ewma_vol(df)

        # GARCH
        garch = self.garch_forecast(df, horizon)
        garch_vol = garch.get("annualized_vol", ewma)

        # Composite (weighted average)
        vols = [v for v in [cc_vol, pk_vol, gk_vol, ewma, garch_vol] if v > 0]
        composite = np.mean(vols) if vols else 0

        # Volatility regime
        if composite > 0.35:
            vol_regime = "extreme"
        elif composite > 0.25:
            vol_regime = "high"
        elif composite > 0.15:
            vol_regime = "normal"
        else:
            vol_regime = "low"

        return {
            "composite_vol": round(float(composite), 6),
            "vol_regime": vol_regime,
            "estimators": {
                "close_to_close": round(cc_vol, 6),
                "parkinson": round(pk_vol, 6),
                "garman_klass": round(gk_vol, 6),
                "ewma": round(ewma, 6),
                "garch": garch,
            },
            "horizon_days": horizon,
        }
