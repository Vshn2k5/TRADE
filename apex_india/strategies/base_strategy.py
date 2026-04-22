"""
APEX INDIA — Base Strategy
============================
Abstract base class for all trading strategies.

Every strategy inherits from BaseStrategy and implements:
- generate_signals(): Core signal generation logic
- validate_entry(): Pre-trade validation rules
- compute_targets(): SL/target calculation
- should_exit(): Exit condition evaluation

Strategy Lifecycle:
    1. Regime check (is this strategy active for current regime?)
    2. Universe screening (filter symbols meeting prerequisites)
    3. Signal generation (core logic)
    4. Entry validation (volume, timing, risk checks)
    5. Target computation (SL, T1, T2, T3)
    6. Score + rank candidates

Usage:
    class MyStrategy(BaseStrategy):
        def generate_signals(self, df, symbol):
            ...
"""

from abc import ABC, abstractmethod
from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("strategies.base")

IST = pytz.timezone(MARKET_TIMEZONE)


# ═══════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════

class MarketRegime(Enum):
    """Market regime classification."""
    TRENDING_BULLISH = "TRENDING_BULLISH"
    TRENDING_BEARISH = "TRENDING_BEARISH"
    MEAN_REVERTING = "MEAN_REVERTING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    BREAKOUT_PENDING = "BREAKOUT_PENDING"
    DISTRIBUTION = "DISTRIBUTION"
    ACCUMULATION = "ACCUMULATION"
    UNKNOWN = "UNKNOWN"


class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalStrength(Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"


class TradeSignal:
    """
    Standardized trade signal output from any strategy.
    """

    def __init__(
        self,
        symbol: str,
        direction: SignalDirection,
        strength: SignalStrength,
        strategy_name: str,
        entry_price: float,
        stop_loss: float,
        targets: List[float],
        confidence: float = 0.0,
        timeframe: str = "day",
        regime: MarketRegime = MarketRegime.UNKNOWN,
        reasoning: str = "",
        metadata: Optional[Dict] = None,
    ):
        self.symbol = symbol
        self.direction = direction
        self.strength = strength
        self.strategy_name = strategy_name
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.targets = targets
        self.confidence = confidence
        self.timeframe = timeframe
        self.regime = regime
        self.reasoning = reasoning
        self.metadata = metadata or {}
        self.timestamp = datetime.now(IST)

        # Computed
        self.risk = abs(entry_price - stop_loss)
        self.reward = abs(targets[0] - entry_price) if targets else 0
        self.risk_reward = round(self.reward / self.risk, 2) if self.risk > 0 else 0

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "strategy": self.strategy_name,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "targets": self.targets,
            "risk_reward": self.risk_reward,
            "confidence": self.confidence,
            "timeframe": self.timeframe,
            "regime": self.regime.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<TradeSignal {self.direction.value} {self.symbol} "
            f"[{self.strategy_name}] "
            f"Entry={self.entry_price:.2f} SL={self.stop_loss:.2f} "
            f"R:R={self.risk_reward} Conf={self.confidence:.0f}%>"
        )


# ═══════════════════════════════════════════════════════════════
# BASE STRATEGY
# ═══════════════════════════════════════════════════════════════

class BaseStrategy(ABC):
    """
    Abstract base class for all APEX INDIA trading strategies.

    Subclasses must implement:
    - generate_signals(): Core signal logic
    - validate_entry(): Entry validation
    - compute_targets(): SL/target computation

    Built-in methods:
    - is_active_for_regime(): Regime applicability check
    - volume_confirmation(): Volume above threshold
    - is_market_hours(): Time-of-day filter
    - run(): Full signal generation pipeline
    """

    def __init__(
        self,
        name: str,
        version: str = "1.0",
        applicable_regimes: Optional[List[MarketRegime]] = None,
        min_bars: int = 50,
        timeframe: str = "day",
    ):
        self.name = name
        self.version = version
        self.applicable_regimes = applicable_regimes or list(MarketRegime)
        self.min_bars = min_bars
        self.timeframe = timeframe

        # Performance tracking
        self._signal_count = 0
        self._win_count = 0
        self._loss_count = 0

    # ───────────────────────────────────────────────────────────
    # Abstract Methods (must be implemented by subclass)
    # ───────────────────────────────────────────────────────────

    @abstractmethod
    def generate_signals(
        self,
        df: pd.DataFrame,
        symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        """
        Core signal generation logic.

        Args:
            df: OHLCV DataFrame with indicators computed
            symbol: Stock symbol
            regime: Current market regime

        Returns:
            TradeSignal if conditions met, None otherwise
        """
        pass

    @abstractmethod
    def compute_targets(
        self,
        df: pd.DataFrame,
        entry_price: float,
        direction: SignalDirection,
    ) -> Tuple[float, List[float]]:
        """
        Compute stop-loss and target levels.

        Returns:
            (stop_loss, [target_1, target_2, target_3])
        """
        pass

    # ───────────────────────────────────────────────────────────
    # Built-in Validation Methods
    # ───────────────────────────────────────────────────────────

    def validate_entry(
        self,
        df: pd.DataFrame,
        direction: SignalDirection,
    ) -> Tuple[bool, str]:
        """
        Default entry validation — can be overridden.
        Checks: data sufficiency, volume, spread reasonableness.
        """
        if len(df) < self.min_bars:
            return False, f"Insufficient data: {len(df)} < {self.min_bars} bars"

        # Volume check: current volume should be > 50% of 20-day average
        if "volume" in df.columns and len(df) >= 20:
            avg_vol = df["volume"].tail(20).mean()
            current_vol = df["volume"].iloc[-1]
            if current_vol < avg_vol * 0.5:
                return False, f"Low volume: {current_vol:,.0f} < 50% of avg {avg_vol:,.0f}"

        # Price > ₹50 (avoid penny stocks)
        if df["close"].iloc[-1] < 50:
            return False, f"Price too low: ₹{df['close'].iloc[-1]:.2f}"

        return True, "OK"

    def is_active_for_regime(self, regime: MarketRegime) -> bool:
        """Check if this strategy applies to the current regime."""
        return regime in self.applicable_regimes

    @staticmethod
    def volume_confirmation(
        df: pd.DataFrame,
        threshold: float = 1.2,
    ) -> bool:
        """Confirm volume is above threshold (relative to 20-day avg)."""
        if "volume" not in df.columns or len(df) < 20:
            return True  # Pass if no volume data

        avg_vol = df["volume"].tail(20).mean()
        current_vol = df["volume"].iloc[-1]
        return current_vol > avg_vol * threshold

    @staticmethod
    def is_market_hours() -> bool:
        """Check if we're within Indian market hours."""
        now = datetime.now(IST)
        market_open = time(9, 15)
        market_close = time(15, 30)
        return market_open <= now.time() <= market_close

    # ───────────────────────────────────────────────────────────
    # Helper: ATR-Based Stops & Targets
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def atr_stops(
        df: pd.DataFrame,
        entry_price: float,
        direction: SignalDirection,
        atr_sl_mult: float = 2.0,
        atr_t1_mult: float = 2.0,
        atr_t2_mult: float = 3.5,
        atr_t3_mult: float = 5.0,
    ) -> Tuple[float, List[float]]:
        """
        Standard ATR-based stop-loss and targets.
        Used as the default target computation.
        """
        if "atr" in df.columns:
            atr = df["atr"].iloc[-1]
        else:
            # Fallback: compute ATR inline
            tr = pd.concat([
                df["high"] - df["low"],
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ], axis=1).max(axis=1)
            atr = tr.tail(14).mean()

        if direction == SignalDirection.LONG:
            sl = round(entry_price - atr_sl_mult * atr, 2)
            targets = [
                round(entry_price + atr_t1_mult * atr, 2),
                round(entry_price + atr_t2_mult * atr, 2),
                round(entry_price + atr_t3_mult * atr, 2),
            ]
        else:
            sl = round(entry_price + atr_sl_mult * atr, 2)
            targets = [
                round(entry_price - atr_t1_mult * atr, 2),
                round(entry_price - atr_t2_mult * atr, 2),
                round(entry_price - atr_t3_mult * atr, 2),
            ]

        return sl, targets

    # ───────────────────────────────────────────────────────────
    # Main Pipeline
    # ───────────────────────────────────────────────────────────

    def run(
        self,
        df: pd.DataFrame,
        symbol: str,
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Optional[TradeSignal]:
        """
        Full signal generation pipeline.

        1. Check regime applicability
        2. Validate data / entry conditions
        3. Generate signal
        4. Return TradeSignal or None
        """
        # Regime check
        if not self.is_active_for_regime(regime):
            return None

        # Validation
        valid, reason = self.validate_entry(df, SignalDirection.NEUTRAL)
        if not valid:
            return None

        # Generate
        try:
            signal = self.generate_signals(df, symbol, regime)
            if signal:
                self._signal_count += 1
                logger.info(f"[{self.name}] Signal: {signal}")
            return signal
        except Exception as e:
            logger.error(f"[{self.name}] Signal generation failed for {symbol}: {e}")
            return None

    # ───────────────────────────────────────────────────────────
    # Performance Tracking
    # ───────────────────────────────────────────────────────────

    def record_outcome(self, win: bool) -> None:
        """Record trade outcome for win rate tracking."""
        if win:
            self._win_count += 1
        else:
            self._loss_count += 1

    @property
    def win_rate(self) -> float:
        total = self._win_count + self._loss_count
        return (self._win_count / total * 100) if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "signals_generated": self._signal_count,
            "wins": self._win_count,
            "losses": self._loss_count,
            "win_rate": f"{self.win_rate:.1f}%",
            "applicable_regimes": [r.value for r in self.applicable_regimes],
        }
