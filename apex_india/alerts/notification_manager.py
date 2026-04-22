"""
APEX INDIA — Notification Manager
====================================
Multi-channel notification dispatcher.
Routes alerts to Telegram, email, and logging based on priority.

Channels:
- Telegram (primary): All trade signals, P&L updates
- Email: Daily/weekly reports
- Log: Everything (audit trail)

Usage:
    nm = NotificationManager(telegram_bot=bot)
    nm.notify("signal", signal_data)
"""

from typing import Any, Dict, Optional

from apex_india.alerts.telegram_bot import TelegramBot
from apex_india.utils.logger import get_logger

logger = get_logger("alerts.dispatcher")


class NotificationManager:
    """
    Multi-channel notification dispatcher.
    """

    def __init__(
        self,
        telegram: Optional[TelegramBot] = None,
    ):
        self.telegram = telegram or TelegramBot()
        self._enabled = True
        self._notification_count = 0

    def notify(self, event_type: str, data: Dict) -> bool:
        """
        Dispatch notification based on event type.

        Event types:
        - signal: New trade signal
        - execution: Order filled
        - exit: Position closed
        - circuit_breaker: Risk alert
        - pnl_update: Hourly P&L
        - daily_report: EOD summary
        """
        if not self._enabled:
            return False

        self._notification_count += 1

        # Always log
        logger.info(f"Notification [{event_type}]: {_summary(data)}")

        # Route to channels
        success = False

        if event_type == "signal":
            success = self.telegram.send_signal(data)

        elif event_type == "execution":
            success = self.telegram.send_execution(data)

        elif event_type == "exit":
            success = self.telegram.send_exit(data)

        elif event_type == "circuit_breaker":
            success = self.telegram.send_circuit_breaker(data)

        elif event_type == "pnl_update":
            success = self.telegram.send_pnl_update(
                data.get("pnl", 0), data.get("equity", 0)
            )

        elif event_type == "daily_report":
            success = self.telegram.send_daily_report(data.get("report", ""))

        return success

    def mute(self) -> None:
        """Mute all notifications."""
        self._enabled = False
        logger.info("Notifications MUTED")

    def unmute(self) -> None:
        """Unmute notifications."""
        self._enabled = True
        logger.info("Notifications UNMUTED")

    @property
    def stats(self) -> Dict:
        return {
            "enabled": self._enabled,
            "telegram_enabled": self.telegram.is_enabled,
            "total_sent": self._notification_count,
        }


def _summary(data: Dict) -> str:
    """Create brief summary from notification data."""
    if "symbol" in data:
        return f"{data.get('symbol', '?')} {data.get('direction', '')}"
    if "report" in data:
        return "Daily report"
    if "level" in data:
        return f"Circuit breaker: {data.get('level')}"
    return str(data)[:80]
