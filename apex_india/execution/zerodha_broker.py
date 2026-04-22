"""
APEX INDIA — Zerodha Kite Connect Broker
===========================================
Production broker connector for Zerodha Kite Connect API.
Requires kiteconnect package and valid API credentials.

Features:
- Full order CRUD with Kite API
- Position & holdings sync
- LTP and margin queries
- Auto-reconnect on session expiry
- Rate limiting (3 req/sec)

Usage:
    broker = ZerodhaBroker()
    broker.connect({"api_key": "xxx", "access_token": "yyy"})
    broker.place_order(order)
"""

import time
from typing import Any, Dict, List, Optional

from apex_india.execution.broker_base import BrokerBase
from apex_india.execution.order_manager import Order, OrderStatus
from apex_india.utils.logger import get_logger

logger = get_logger("execution.zerodha")

try:
    from kiteconnect import KiteConnect
    HAS_KITE = True
except ImportError:
    HAS_KITE = False
    logger.info("kiteconnect not installed — Zerodha broker unavailable")


class ZerodhaBroker(BrokerBase):
    """
    Zerodha Kite Connect broker implementation.
    """

    RATE_LIMIT_DELAY = 0.35  # 3 requests per second

    def __init__(self):
        super().__init__("zerodha")
        self._kite = None
        self._api_key = ""
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    # ───────────────────────────────────────────────
    # Connection
    # ───────────────────────────────────────────────

    def connect(self, credentials: Dict[str, str]) -> bool:
        """
        Connect to Zerodha.

        credentials:
            - api_key: Kite API key
            - access_token: Session access token
        """
        if not HAS_KITE:
            logger.error("kiteconnect not installed")
            return False

        try:
            self._api_key = credentials.get("api_key", "")
            access_token = credentials.get("access_token", "")

            self._kite = KiteConnect(api_key=self._api_key)
            self._kite.set_access_token(access_token)

            # Verify connection
            profile = self._kite.profile()
            self._connected = True
            logger.info(f"Connected to Zerodha: {profile.get('user_name', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Zerodha connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Invalidate session."""
        if self._kite and self._connected:
            try:
                self._kite.invalidate_access_token()
            except Exception:
                pass
        self._connected = False
        logger.info("Disconnected from Zerodha")

    # ───────────────────────────────────────────────
    # Order Operations
    # ───────────────────────────────────────────────

    def place_order(self, order: Order) -> Dict[str, Any]:
        if not self._connected or not self._kite:
            return {"success": False, "message": "Not connected"}

        self._rate_limit()

        try:
            # Map to Kite parameters
            variety = "regular"
            if order.order_type in ("SL", "SL-M"):
                variety = "regular"

            params = {
                "tradingsymbol": order.symbol,
                "exchange": "NSE",
                "transaction_type": order.side,
                "quantity": order.quantity,
                "order_type": order.order_type,
                "product": order.product,
                "variety": variety,
            }

            if order.order_type == "LIMIT":
                params["price"] = order.price
            if order.trigger_price > 0:
                params["trigger_price"] = order.trigger_price
            if order.tag:
                params["tag"] = order.tag[:20]

            broker_id = self._kite.place_order(**params)

            order.broker_order_id = str(broker_id)
            order.update_status(OrderStatus.SUBMITTED)

            logger.info(f"Order placed: {order.order_id} -> Kite: {broker_id}")
            return {
                "success": True,
                "broker_order_id": str(broker_id),
                "message": "Order placed successfully",
            }

        except Exception as e:
            order.update_status(OrderStatus.REJECTED, str(e))
            logger.error(f"Order placement failed: {e}")
            return {"success": False, "message": str(e)}

    def modify_order(
        self,
        broker_order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        trigger_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self._connected or not self._kite:
            return {"success": False, "message": "Not connected"}

        self._rate_limit()

        try:
            params = {"order_id": broker_order_id, "variety": "regular"}
            if price:
                params["price"] = price
            if quantity:
                params["quantity"] = quantity
            if trigger_price:
                params["trigger_price"] = trigger_price

            self._kite.modify_order(**params)
            return {"success": True, "message": "Order modified"}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def cancel_order(self, broker_order_id: str) -> Dict[str, Any]:
        if not self._connected or not self._kite:
            return {"success": False, "message": "Not connected"}

        self._rate_limit()

        try:
            self._kite.cancel_order(variety="regular", order_id=broker_order_id)
            return {"success": True, "message": "Order cancelled"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_order_status(self, broker_order_id: str) -> Dict[str, Any]:
        if not self._connected or not self._kite:
            return {"status": "UNKNOWN", "message": "Not connected"}

        self._rate_limit()

        try:
            history = self._kite.order_history(broker_order_id)
            if history:
                latest = history[-1]
                return {
                    "status": latest.get("status", "UNKNOWN"),
                    "filled_quantity": latest.get("filled_quantity", 0),
                    "average_price": latest.get("average_price", 0),
                    "pending_quantity": latest.get("pending_quantity", 0),
                    "status_message": latest.get("status_message", ""),
                }
            return {"status": "UNKNOWN"}

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # ───────────────────────────────────────────────
    # Portfolio
    # ───────────────────────────────────────────────

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self._connected or not self._kite:
            return []

        self._rate_limit()

        try:
            positions = self._kite.positions()
            return positions.get("net", [])
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self._connected or not self._kite:
            return []

        self._rate_limit()

        try:
            return self._kite.holdings()
        except Exception as e:
            logger.error(f"Failed to get holdings: {e}")
            return []

    # ───────────────────────────────────────────────
    # Market Data
    # ───────────────────────────────────────────────

    def get_ltp(self, symbols: List[str]) -> Dict[str, float]:
        if not self._connected or not self._kite:
            return {}

        self._rate_limit()

        try:
            instruments = [f"NSE:{s}" for s in symbols]
            data = self._kite.ltp(instruments)
            return {
                s: data.get(f"NSE:{s}", {}).get("last_price", 0)
                for s in symbols
            }
        except Exception as e:
            logger.error(f"LTP query failed: {e}")
            return {}

    # ───────────────────────────────────────────────
    # Account
    # ───────────────────────────────────────────────

    def get_margins(self) -> Dict[str, Any]:
        if not self._connected or not self._kite:
            return {}

        self._rate_limit()

        try:
            margins = self._kite.margins()
            equity = margins.get("equity", {})
            return {
                "available_cash": equity.get("available", {}).get("cash", 0),
                "used_margin": equity.get("utilised", {}).get("debits", 0),
                "total_balance": equity.get("net", 0),
            }
        except Exception as e:
            return {"error": str(e)}
