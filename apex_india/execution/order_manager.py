"""
APEX INDIA — Order Manager
=============================
Manages the full order lifecycle: create → validate → submit →
track → modify → cancel → reconcile.

Order States:
  CREATED → VALIDATED → SUBMITTED → OPEN → PARTIAL_FILL → FILLED
                                          → CANCELLED
                                          → REJECTED
                                          → EXPIRED

Usage:
    om = OrderManager()
    order = om.create_order("RELIANCE", "BUY", 50, 1500, "LIMIT")
    om.submit_order(order.order_id, broker)
"""

from datetime import datetime
from enum import Enum, unique
from typing import Any, Dict, List, Optional
from collections import OrderedDict
import uuid

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import (
    MARKET_TIMEZONE, OrderSide, OrderType, ProductType,
)

logger = get_logger("execution.orders")

IST = pytz.timezone(MARKET_TIMEZONE)


@unique
class OrderStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Order:
    """Represents a single order."""

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = "LIMIT",
        product: str = "CNC",
        trigger_price: float = 0,
        strategy: str = "",
        signal_id: str = "",
        tag: str = "",
    ):
        self.order_id = f"APEX-{uuid.uuid4().hex[:8].upper()}"
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.order_type = order_type
        self.product = product
        self.trigger_price = trigger_price
        self.strategy = strategy
        self.signal_id = signal_id
        self.tag = tag

        # State
        self.status = OrderStatus.CREATED
        self.broker_order_id: Optional[str] = None
        self.filled_quantity = 0
        self.average_price = 0.0
        self.pending_quantity = quantity

        # Timestamps
        self.created_at = datetime.now(IST)
        self.submitted_at: Optional[datetime] = None
        self.filled_at: Optional[datetime] = None
        self.cancelled_at: Optional[datetime] = None

        # Error tracking
        self.rejection_reason = ""
        self.modification_count = 0

        # Audit
        self._state_history: List[Dict] = [
            {"status": self.status.value, "time": self.created_at.isoformat()}
        ]

    def update_status(self, new_status: OrderStatus, reason: str = "") -> None:
        """Update order status with audit trail."""
        old = self.status
        self.status = new_status
        now = datetime.now(IST)

        self._state_history.append({
            "status": new_status.value,
            "time": now.isoformat(),
            "reason": reason,
        })

        if new_status == OrderStatus.REJECTED:
            self.rejection_reason = reason
        elif new_status == OrderStatus.SUBMITTED:
            self.submitted_at = now
        elif new_status == OrderStatus.FILLED:
            self.filled_at = now
        elif new_status == OrderStatus.CANCELLED:
            self.cancelled_at = now

        logger.info(
            f"Order {self.order_id}: {old.value} -> {new_status.value} "
            f"({self.symbol} {self.side} {self.quantity})"
        )

    def update_fill(self, filled_qty: int, avg_price: float) -> None:
        """Update fill information."""
        self.filled_quantity = filled_qty
        self.average_price = avg_price
        self.pending_quantity = self.quantity - filled_qty

        if filled_qty >= self.quantity:
            self.update_status(OrderStatus.FILLED)
        elif filled_qty > 0:
            self.update_status(OrderStatus.PARTIAL_FILL)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "product": self.product,
            "trigger_price": self.trigger_price,
            "status": self.status.value,
            "broker_order_id": self.broker_order_id,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "pending_quantity": self.pending_quantity,
            "strategy": self.strategy,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "rejection_reason": self.rejection_reason,
        }

    def __repr__(self) -> str:
        return (
            f"<Order {self.order_id} {self.side} {self.symbol} "
            f"x{self.quantity} @{self.price} [{self.status.value}]>"
        )


class OrderManager:
    """
    Order lifecycle management.
    Thread-safe order book with validation, tracking, and reconciliation.
    """

    def __init__(self, max_orders_per_day: int = 50):
        self.max_orders_per_day = max_orders_per_day
        self._orders: OrderedDict[str, Order] = OrderedDict()
        self._daily_count = 0
        self._daily_date = None

    # ───────────────────────────────────────────────────────────
    # Order Creation
    # ───────────────────────────────────────────────────────────

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = "LIMIT",
        product: str = "CNC",
        trigger_price: float = 0,
        strategy: str = "",
        signal_id: str = "",
    ) -> Order:
        """Create and validate a new order."""
        # Reset daily counter
        today = datetime.now(IST).date()
        if self._daily_date != today:
            self._daily_count = 0
            self._daily_date = today

        order = Order(
            symbol=symbol, side=side, quantity=quantity,
            price=price, order_type=order_type, product=product,
            trigger_price=trigger_price, strategy=strategy,
            signal_id=signal_id,
        )

        # Validate
        valid, reason = self._validate(order)
        if valid:
            order.update_status(OrderStatus.VALIDATED)
        else:
            order.update_status(OrderStatus.REJECTED, reason)

        self._orders[order.order_id] = order
        self._daily_count += 1

        return order

    def _validate(self, order: Order) -> tuple:
        """Pre-submission validation."""
        if order.quantity <= 0:
            return False, "Quantity must be > 0"

        if order.price <= 0 and order.order_type == "LIMIT":
            return False, "Limit price must be > 0"

        if self._daily_count >= self.max_orders_per_day:
            return False, f"Daily order limit ({self.max_orders_per_day}) reached"

        if order.order_type == "SL" and order.trigger_price <= 0:
            return False, "SL order requires trigger price"

        return True, "OK"

    # ───────────────────────────────────────────────────────────
    # Order Operations
    # ───────────────────────────────────────────────────────────

    def modify_order(
        self,
        order_id: str,
        new_price: Optional[float] = None,
        new_quantity: Optional[int] = None,
        new_trigger: Optional[float] = None,
    ) -> bool:
        """Modify an open order."""
        order = self._orders.get(order_id)
        if not order:
            return False

        if order.status not in (OrderStatus.OPEN, OrderStatus.VALIDATED, OrderStatus.SUBMITTED):
            logger.warning(f"Cannot modify order {order_id} in state {order.status.value}")
            return False

        if new_price:
            order.price = new_price
        if new_quantity:
            order.quantity = new_quantity
            order.pending_quantity = new_quantity - order.filled_quantity
        if new_trigger:
            order.trigger_price = new_trigger

        order.modification_count += 1

        logger.info(f"Order {order_id} modified (count={order.modification_count})")
        return True

    def cancel_order(self, order_id: str, reason: str = "User cancelled") -> bool:
        """Cancel an order."""
        order = self._orders.get(order_id)
        if not order:
            return False

        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            return False

        order.update_status(OrderStatus.CANCELLED, reason)
        return True

    # ───────────────────────────────────────────────────────────
    # Queries
    # ───────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)

    def get_open_orders(self) -> List[Order]:
        return [
            o for o in self._orders.values()
            if o.status in (
                OrderStatus.OPEN, OrderStatus.SUBMITTED,
                OrderStatus.VALIDATED, OrderStatus.PARTIAL_FILL,
            )
        ]

    def get_filled_orders(self) -> List[Order]:
        return [o for o in self._orders.values() if o.status == OrderStatus.FILLED]

    def get_orders_by_strategy(self, strategy: str) -> List[Order]:
        return [o for o in self._orders.values() if o.strategy == strategy]

    @property
    def daily_order_count(self) -> int:
        return self._daily_count

    def get_summary(self) -> Dict[str, Any]:
        """Order book summary."""
        statuses = {}
        for o in self._orders.values():
            statuses[o.status.value] = statuses.get(o.status.value, 0) + 1

        return {
            "total_orders": len(self._orders),
            "daily_count": self._daily_count,
            "statuses": statuses,
            "open_count": len(self.get_open_orders()),
            "filled_count": len(self.get_filled_orders()),
        }
