"""
APEX INDIA — Upstox Broker Connector
=======================================
Secondary broker connector for Upstox API v2.

Usage:
    broker = UpstoxBroker()
    broker.connect({"api_key": "xxx", "access_token": "yyy"})
"""

import time
from typing import Any, Dict, List, Optional

from apex_india.execution.broker_base import BrokerBase
from apex_india.execution.order_manager import Order, OrderStatus
from apex_india.utils.logger import get_logger

logger = get_logger("execution.upstox")

try:
    import upstox_client
    HAS_UPSTOX = True
except ImportError:
    HAS_UPSTOX = False
    logger.info("upstox_client not installed — Upstox broker unavailable")


class UpstoxBroker(BrokerBase):
    """
    Upstox API v2 broker implementation.
    """

    RATE_LIMIT_DELAY = 0.5

    def __init__(self):
        super().__init__("upstox")
        self._api_key = ""
        self._access_token = ""
        self._last_request_time = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def connect(self, credentials: Dict[str, str]) -> bool:
        if not HAS_UPSTOX:
            logger.error("upstox_client not installed")
            return False

        try:
            self._api_key = credentials.get("api_key", "")
            self._access_token = credentials.get("access_token", "")

            configuration = upstox_client.Configuration()
            configuration.access_token = self._access_token

            api = upstox_client.UserApi(upstox_client.ApiClient(configuration))
            profile = api.get_profile("2.0")

            self._connected = True
            logger.info(f"Connected to Upstox: {profile.data.user_name}")
            return True

        except Exception as e:
            logger.error(f"Upstox connection failed: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from Upstox")

    def place_order(self, order: Order) -> Dict[str, Any]:
        if not self._connected:
            return {"success": False, "message": "Not connected"}

        self._rate_limit()

        try:
            configuration = upstox_client.Configuration()
            configuration.access_token = self._access_token

            api = upstox_client.OrderApi(upstox_client.ApiClient(configuration))

            body = upstox_client.PlaceOrderRequest(
                quantity=order.quantity,
                product=order.product.upper(),
                validity="DAY",
                price=order.price if order.order_type == "LIMIT" else 0,
                tag=order.tag[:20] if order.tag else "",
                instrument_token=f"NSE_EQ|{order.symbol}",
                order_type=order.order_type,
                transaction_type=order.side,
                disclosed_quantity=0,
                trigger_price=order.trigger_price,
                is_amo=False,
            )

            result = api.place_order(body, "2.0")
            broker_id = result.data.order_id

            order.broker_order_id = broker_id
            order.update_status(OrderStatus.SUBMITTED)

            return {"success": True, "broker_order_id": broker_id}

        except Exception as e:
            order.update_status(OrderStatus.REJECTED, str(e))
            return {"success": False, "message": str(e)}

    def modify_order(self, broker_order_id: str, price=None, quantity=None, trigger_price=None):
        if not self._connected:
            return {"success": False, "message": "Not connected"}

        self._rate_limit()

        try:
            configuration = upstox_client.Configuration()
            configuration.access_token = self._access_token

            api = upstox_client.OrderApi(upstox_client.ApiClient(configuration))

            body = upstox_client.ModifyOrderRequest(
                order_id=broker_order_id,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price,
                validity="DAY",
                order_type="LIMIT",
            )

            api.modify_order(body, "2.0")
            return {"success": True}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def cancel_order(self, broker_order_id: str):
        if not self._connected:
            return {"success": False, "message": "Not connected"}

        self._rate_limit()

        try:
            configuration = upstox_client.Configuration()
            configuration.access_token = self._access_token

            api = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
            api.cancel_order(broker_order_id, "2.0")
            return {"success": True}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_order_status(self, broker_order_id: str):
        return {"status": "NOT_IMPLEMENTED", "message": "Use get_positions"}

    def get_positions(self):
        if not self._connected:
            return []
        return []

    def get_holdings(self):
        if not self._connected:
            return []
        return []

    def get_ltp(self, symbols: List[str]):
        return {}

    def get_margins(self):
        return {}
