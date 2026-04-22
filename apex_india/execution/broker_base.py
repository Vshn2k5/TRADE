"""
APEX INDIA — Abstract Broker Connector
=========================================
Base class for all broker integrations.
Defines the standard API that Zerodha, Upstox, and Paper
broker connectors must implement.

Usage:
    class ZerodhaBroker(BrokerBase):
        def place_order(self, order): ...
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from apex_india.execution.order_manager import Order, OrderStatus
from apex_india.utils.logger import get_logger

logger = get_logger("execution.broker")


class BrokerBase(ABC):
    """
    Abstract broker connector interface.

    All brokers must implement:
    - connect / disconnect
    - place_order / modify_order / cancel_order
    - get_positions / get_holdings
    - get_order_status
    - get_ltp (last traded price)
    - get_margins
    """

    def __init__(self, name: str):
        self.name = name
        self._connected = False

    # ───────────────────────────────────────────────
    # Connection
    # ───────────────────────────────────────────────

    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Establish connection to broker API."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from broker API."""
        pass

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ───────────────────────────────────────────────
    # Order Operations
    # ───────────────────────────────────────────────

    @abstractmethod
    def place_order(self, order: Order) -> Dict[str, Any]:
        """
        Place order with broker.

        Returns:
            {"success": bool, "broker_order_id": str, "message": str}
        """
        pass

    @abstractmethod
    def modify_order(
        self,
        broker_order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Modify an existing order."""
        pass

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        pass

    @abstractmethod
    def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        """Get current status of an order."""
        pass

    # ───────────────────────────────────────────────
    # Portfolio
    # ───────────────────────────────────────────────

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """Get portfolio holdings (delivery)."""
        pass

    # ───────────────────────────────────────────────
    # Market Data
    # ───────────────────────────────────────────────

    @abstractmethod
    def get_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """Get last traded price for symbols."""
        pass

    # ───────────────────────────────────────────────
    # Account
    # ───────────────────────────────────────────────

    @abstractmethod
    def get_margins(self) -> Dict[str, Any]:
        """Get account margin/fund details."""
        pass
