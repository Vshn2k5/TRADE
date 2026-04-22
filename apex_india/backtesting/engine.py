"""
APEX INDIA — Backtesting Engine
==================================
Core backtesting loop with realistic Indian market assumptions:
brokerage, STT, SEBI charges, stamp duty, GST, slippage, latency.

Features:
- Event-driven bar-by-bar simulation
- Realistic transaction costs (Zerodha schedule)
- Slippage modeling (0.05-0.15%)
- Position tracking with P&L attribution
- Equity curve generation
- Integration with PerformanceMetrics

Usage:
    engine = BacktestEngine(initial_capital=1_000_000)
    result = engine.run(df, strategy)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from apex_india.strategies.base_strategy import (
    BaseStrategy, TradeSignal, SignalDirection, MarketRegime,
)
from apex_india.risk.position_sizer import PositionSizer
from apex_india.risk.stop_loss_manager import StopLossManager
from apex_india.backtesting.metrics import PerformanceMetrics
from apex_india.utils.logger import get_logger
from apex_india.utils.constants import TransactionCosts

logger = get_logger("backtesting.engine")


class BacktestEngine:
    """
    Event-driven backtesting engine with realistic costs.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        slippage_pct: float = 0.05,
        is_intraday: bool = False,
        max_positions: int = 5,
    ):
        self.initial_capital = initial_capital
        self.slippage_pct = slippage_pct / 100
        self.is_intraday = is_intraday
        self.max_positions = max_positions

        # State
        self.capital = initial_capital
        self.equity_curve: List[float] = []
        self.trades: List[Dict] = []
        self.positions: Dict[str, Dict] = {}

    # ───────────────────────────────────────────────────────────
    # Transaction Cost Model
    # ───────────────────────────────────────────────────────────

    def compute_costs(
        self,
        price: float,
        quantity: int,
        side: str,
        is_delivery: bool = True,
    ) -> float:
        """
        Compute realistic transaction costs for Indian markets.
        """
        turnover = price * quantity
        tc = TransactionCosts

        # Brokerage
        if is_delivery:
            brokerage = 0  # Zerodha zero delivery
        else:
            brokerage = min(turnover * tc.BROKERAGE_INTRADAY_PCT, 20)

        # STT
        if is_delivery:
            stt = turnover * tc.STT_DELIVERY_SELL_PCT if side == "SELL" else turnover * tc.STT_DELIVERY_BUY_PCT
        else:
            stt = turnover * tc.STT_INTRADAY_SELL_PCT if side == "SELL" else 0

        # Exchange charges
        exchange = turnover * tc.NSE_TXN_CHARGE_PCT

        # SEBI
        sebi = turnover * tc.SEBI_TURNOVER_CHARGE_PCT

        # Stamp duty (buy side only)
        if side == "BUY":
            stamp = turnover * (tc.STAMP_DUTY_DELIVERY_PCT if is_delivery else tc.STAMP_DUTY_INTRADAY_PCT)
        else:
            stamp = 0

        # GST on brokerage + exchange
        gst = (brokerage + exchange) * tc.GST_PCT

        total = brokerage + stt + exchange + sebi + stamp + gst
        return round(total, 2)

    def apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to fill price."""
        if side == "BUY":
            return round(price * (1 + self.slippage_pct), 2)
        else:
            return round(price * (1 - self.slippage_pct), 2)

    # ───────────────────────────────────────────────────────────
    # Core Backtest Loop
    # ───────────────────────────────────────────────────────────

    def run(
        self,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        symbol: str = "TEST",
        regime: MarketRegime = MarketRegime.UNKNOWN,
    ) -> Dict[str, Any]:
        """
        Run backtest on OHLCV data with a strategy.

        Args:
            df: OHLCV DataFrame (sorted by date)
            strategy: Strategy instance
            symbol: Symbol name
            regime: Market regime to apply

        Returns:
            Dict with equity_curve, trades, metrics
        """
        self._reset()
        min_bars = max(strategy.min_bars, 50)

        for i in range(min_bars, len(df)):
            # Slice data up to current bar (no look-ahead)
            window = df.iloc[:i+1].copy()
            current_bar = df.iloc[i]
            current_price = current_bar["close"]

            # 1. Check existing positions for stop hits
            self._check_stops(current_bar, df.iloc[:i+1])

            # 2. Generate new signals (only if we have room)
            if len(self.positions) < self.max_positions:
                signal = strategy.run(window, symbol, regime)
                if signal and signal.direction != SignalDirection.NEUTRAL:
                    self._execute_entry(signal, current_bar)

            # 3. Record equity
            equity = self._compute_equity(current_price)
            self.equity_curve.append(equity)

        # Close all remaining positions at last price
        last_price = df["close"].iloc[-1]
        for pid in list(self.positions.keys()):
            self._execute_exit(pid, last_price, "backtest_end")

        # Build results
        eq_series = pd.Series(self.equity_curve, index=df.index[min_bars:])
        metrics = PerformanceMetrics(eq_series, self.trades)

        result = {
            "equity_curve": eq_series,
            "trades": self.trades,
            "metrics": metrics.full_report(),
            "formatted_report": metrics.format_report(),
            "num_trades": len(self.trades),
            "final_capital": round(self.capital, 2),
        }

        logger.info(
            f"Backtest complete: {symbol} | "
            f"{len(self.trades)} trades | "
            f"Return={metrics.total_return():.1f}% | "
            f"Sharpe={metrics.sharpe_ratio():.2f}"
        )

        return result

    # ───────────────────────────────────────────────────────────
    # Execution
    # ───────────────────────────────────────────────────────────

    def _execute_entry(self, signal: TradeSignal, bar: pd.Series) -> None:
        """Execute entry for a signal."""
        side = "BUY" if signal.direction == SignalDirection.LONG else "SELL"
        fill_price = self.apply_slippage(signal.entry_price, side)

        # Position sizing: risk 1% max
        risk_per_share = abs(fill_price - signal.stop_loss)
        if risk_per_share <= 0:
            return

        max_risk = self.capital * 0.01
        quantity = min(
            int(max_risk / risk_per_share),
            int(self.capital * 0.08 / fill_price),  # 8% max per stock
        )

        if quantity <= 0:
            return

        # Costs
        cost = self.compute_costs(fill_price, quantity, side, not self.is_intraday)
        position_value = fill_price * quantity

        if position_value + cost > self.capital:
            return

        # Deduct
        self.capital -= (position_value + cost)

        pid = f"BT_{len(self.trades):04d}"
        self.positions[pid] = {
            "symbol": signal.symbol,
            "direction": signal.direction.value,
            "quantity": quantity,
            "entry_price": fill_price,
            "stop_loss": signal.stop_loss,
            "targets": signal.targets,
            "entry_cost": cost,
            "highest": fill_price,
            "lowest": fill_price,
            "entry_bar": bar.name if hasattr(bar, 'name') else None,
            "strategy": signal.strategy_name,
        }

    def _execute_exit(self, pid: str, price: float, reason: str) -> None:
        """Execute exit for a position."""
        pos = self.positions.pop(pid, None)
        if not pos:
            return

        side = "SELL" if pos["direction"] == "LONG" else "BUY"
        fill_price = self.apply_slippage(price, side)
        cost = self.compute_costs(fill_price, pos["quantity"], side, not self.is_intraday)

        # P&L
        if pos["direction"] == "LONG":
            gross_pnl = (fill_price - pos["entry_price"]) * pos["quantity"]
        else:
            gross_pnl = (pos["entry_price"] - fill_price) * pos["quantity"]

        net_pnl = gross_pnl - pos["entry_cost"] - cost

        # Return capital
        self.capital += pos["entry_price"] * pos["quantity"] + gross_pnl - cost

        self.trades.append({
            "symbol": pos["symbol"],
            "direction": pos["direction"],
            "strategy": pos["strategy"],
            "entry_price": pos["entry_price"],
            "exit_price": fill_price,
            "quantity": pos["quantity"],
            "gross_pnl": round(gross_pnl, 2),
            "costs": round(pos["entry_cost"] + cost, 2),
            "pnl": round(net_pnl, 2),
            "pnl_pct": round((net_pnl / (pos["entry_price"] * pos["quantity"])) * 100, 2),
            "exit_reason": reason,
        })

    def _check_stops(self, bar: pd.Series, window: pd.DataFrame) -> None:
        """Check stop-loss and target hits for all positions."""
        for pid in list(self.positions.keys()):
            pos = self.positions[pid]

            if pos["direction"] == "LONG":
                pos["highest"] = max(pos["highest"], bar["high"])
                # Stop hit
                if bar["low"] <= pos["stop_loss"]:
                    self._execute_exit(pid, pos["stop_loss"], "stop_loss")
                    continue
                # Target hit
                if pos["targets"] and bar["high"] >= pos["targets"][0]:
                    self._execute_exit(pid, pos["targets"][0], "target_1")
                    continue
            else:
                pos["lowest"] = min(pos["lowest"], bar["low"])
                if bar["high"] >= pos["stop_loss"]:
                    self._execute_exit(pid, pos["stop_loss"], "stop_loss")
                    continue
                if pos["targets"] and bar["low"] <= pos["targets"][0]:
                    self._execute_exit(pid, pos["targets"][0], "target_1")
                    continue

    def _compute_equity(self, current_price: float) -> float:
        """Compute total equity (cash + open positions MTM)."""
        open_value = 0
        for pos in self.positions.values():
            if pos["direction"] == "LONG":
                open_value += (current_price - pos["entry_price"]) * pos["quantity"]
            else:
                open_value += (pos["entry_price"] - current_price) * pos["quantity"]
            open_value += pos["entry_price"] * pos["quantity"]

        return round(self.capital + open_value, 2)

    def _reset(self) -> None:
        """Reset engine state for a fresh run."""
        self.capital = self.initial_capital
        self.equity_curve = []
        self.trades = []
        self.positions = {}
