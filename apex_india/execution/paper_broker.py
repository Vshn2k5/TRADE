"""
APEX INDIA — Paper Trading Broker
====================================
Simulated broker for paper trading and strategy development.
Executes orders instantly with configurable slippage and costs.

Features:
- Instant fill at market price ± slippage
- Realistic transaction cost model
- Position & P&L tracking
- No real money at risk

Usage:
    broker = PaperBroker(initial_capital=1_000_000)
    broker.connect({})
    broker.place_order(order)
"""

import time
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

import pytz

from apex_india.execution.broker_base import BrokerBase
from apex_india.execution.order_manager import Order, OrderStatus
from apex_india.backtesting.engine import BacktestEngine
from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("execution.paper")

IST = pytz.timezone(MARKET_TIMEZONE)


class PaperBroker(BrokerBase):
    """
    Paper trading broker — simulates order execution
    without real money.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        slippage_pct: float = 0.05,
    ):
        super().__init__("paper")
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.slippage_pct = slippage_pct / 100
        self._cost_engine = BacktestEngine()

        # Simulated state
        self._positions: Dict[str, Dict] = {}
        self._holdings: Dict[str, Dict] = {}
        self._orders: Dict[str, Dict] = {}
        self._ltp_cache: Dict[str, float] = {}
        self._trade_log: List[Dict] = []

    # ───────────────────────────────────────────────
    # Connection
    # ───────────────────────────────────────────────

    def connect(self, credentials: Dict[str, str]) -> bool:
        """Paper broker always connects."""
        self._connected = True
        logger.info(
            f"Paper broker connected | Capital: ₹{self.capital:,.0f}"
        )
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Paper broker disconnected")

    # ───────────────────────────────────────────────
    # Order Operations
    # ───────────────────────────────────────────────

    def place_order(self, order: Order) -> Dict[str, Any]:
        """Instantly fill the order with simulated execution."""
        broker_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
        order.broker_order_id = broker_id
        order.update_status(OrderStatus.SUBMITTED)

        # Determine fill price
        base_price = self._ltp_cache.get(order.symbol, order.price)
        if order.order_type == "MARKET":
            fill_price = base_price
        else:
            fill_price = order.price

        # Apply slippage
        if order.side == "BUY":
            fill_price = round(fill_price * (1 + self.slippage_pct), 2)
        else:
            fill_price = round(fill_price * (1 - self.slippage_pct), 2)

        # Compute costs
        is_delivery = order.product == "CNC"
        cost = self._cost_engine.compute_costs(
            fill_price, order.quantity, order.side, is_delivery
        )

        # Check if enough capital
        if order.side == "BUY":
            required = fill_price * order.quantity + cost
            if required > self.capital:
                order.update_status(OrderStatus.REJECTED, "Insufficient capital")
                return {"success": False, "message": "Insufficient capital"}
            self.capital -= required
        else:
            proceeds = fill_price * order.quantity - cost
            self.capital += proceeds

        # Update fill
        order.update_fill(order.quantity, fill_price)

        # Track position
        self._update_position(order, fill_price, cost)

        # Store
        self._orders[broker_id] = {
            "order": order.to_dict(),
            "fill_price": fill_price,
            "cost": cost,
            "fill_time": datetime.now(IST).isoformat(),
        }

        self._trade_log.append({
            "time": datetime.now(IST).isoformat(),
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": fill_price,
            "cost": cost,
            "strategy": order.strategy,
        })

        logger.info(
            f"Paper fill: {order.side} {order.quantity}x{order.symbol} "
            f"@{fill_price} (cost=₹{cost:.2f}) | "
            f"Capital: ₹{self.capital:,.0f}"
        )

        return {
            "success": True,
            "broker_order_id": broker_id,
            "fill_price": fill_price,
            "cost": cost,
            "message": "Paper order filled",
        }

    def _update_position(self, order: Order, price: float, cost: float) -> None:
        """Update position tracking after fill."""
        sym = order.symbol

        if sym not in self._positions:
            self._positions[sym] = {
                "symbol": sym,
                "quantity": 0,
                "average_price": 0,
                "pnl": 0,
                "total_cost": 0,
            }

        pos = self._positions[sym]

        if order.side == "BUY":
            # Average up
            total_qty = pos["quantity"] + order.quantity
            if total_qty > 0:
                avg = ((pos["average_price"] * pos["quantity"]) +
                       (price * order.quantity)) / total_qty
                pos["average_price"] = round(avg, 2)
            pos["quantity"] = total_qty
        else:
            # Realize P&L
            pnl = (price - pos["average_price"]) * order.quantity - cost
            pos["pnl"] += pnl
            pos["quantity"] -= order.quantity

            if pos["quantity"] <= 0:
                pos["quantity"] = 0
                pos["average_price"] = 0

        pos["total_cost"] += cost

    def modify_order(self, broker_order_id, price=None, quantity=None, trigger_price=None):
        return {"success": True, "message": "Paper modify (no-op for filled orders)"}

    def cancel_order(self, broker_order_id: str):
        if broker_order_id in self._orders:
            return {"success": True, "message": "Paper order cancelled"}
        return {"success": False, "message": "Order not found"}

    def get_order_status(self, broker_order_id: str):
        entry = self._orders.get(broker_order_id, {})
        if entry:
            return {"status": "FILLED", "fill_price": entry.get("fill_price", 0)}
        return {"status": "UNKNOWN"}

    # ───────────────────────────────────────────────
    # Portfolio
    # ───────────────────────────────────────────────

    def get_positions(self) -> List[Dict[str, Any]]:
        return [
            p for p in self._positions.values() if p["quantity"] != 0
        ]

    def get_holdings(self) -> List[Dict[str, Any]]:
        return list(self._holdings.values())

    def set_ltp(self, symbol: str, price: float) -> None:
        """Set simulated LTP for paper trading."""
        self._ltp_cache[symbol] = price

    def get_ltp(self, symbols: List[str]) -> Dict[str, float]:
        return {s: self._ltp_cache.get(s, 0) for s in symbols}

    def get_margins(self) -> Dict[str, Any]:
        deployed = sum(
            p["quantity"] * p["average_price"]
            for p in self._positions.values()
        )
        return {
            "available_cash": round(self.capital, 2),
            "used_margin": round(deployed, 2),
            "total_balance": round(self.capital + deployed, 2),
            "initial_capital": self.initial_capital,
            "realized_pnl": round(
                sum(p["pnl"] for p in self._positions.values()), 2
            ),
        }

    @property
    def trade_log(self) -> List[Dict]:
        return list(self._trade_log)
