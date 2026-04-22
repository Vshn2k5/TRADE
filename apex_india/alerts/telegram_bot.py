"""
APEX INDIA — Telegram Bot
============================
Trade alerts and system control via Telegram.

Commands:
    /status     - System status
    /positions  - Open positions with P&L
    /pnl        - Today's P&L summary
    /halt       - Emergency halt
    /resume     - Resume trading
    /report     - Today's full report

Usage:
    bot = TelegramBot(token="...", chat_id="...")
    bot.send_signal(signal)
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("alerts.telegram")

IST = pytz.timezone(MARKET_TIMEZONE)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class TelegramBot:
    """
    Telegram bot for trade alerts and system control.
    """

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(
        self,
        token: str = "",
        chat_id: str = "",
    ):
        self.token = token
        self.chat_id = chat_id
        self._enabled = bool(token and chat_id and HAS_REQUESTS)

        if self._enabled:
            logger.info("Telegram bot initialized")
        else:
            logger.info("Telegram bot disabled (no token/chat_id or requests not installed)")

    def _send(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram."""
        if not self._enabled:
            logger.debug(f"Telegram (disabled): {text[:50]}...")
            return False

        try:
            url = f"{self.BASE_URL.format(token=self.token)}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False

    # ───────────────────────────────────────────────────────────
    # Alert Types
    # ───────────────────────────────────────────────────────────

    def send_signal(self, signal_data: Dict) -> bool:
        """Send trade signal alert."""
        direction = signal_data.get("direction", "?")
        symbol = signal_data.get("symbol", "?")
        entry = signal_data.get("entry_price", 0)
        sl = signal_data.get("stop_loss", 0)
        targets = signal_data.get("targets", [])
        conf = signal_data.get("confidence", 0)
        strategy = signal_data.get("strategy", "?")

        emoji = "🟢" if direction == "LONG" else "🔴"

        text = f"""
{emoji} <b>APEX SIGNAL — {direction}</b>

📌 <b>{symbol}</b>
💰 Entry: ₹{entry:,.2f}
🛑 Stop: ₹{sl:,.2f}
🎯 Targets: {', '.join(f'₹{t:,.0f}' for t in targets[:3])}

📊 Strategy: {strategy}
🔒 Confidence: {conf:.0f}%
⏰ {datetime.now(IST).strftime('%H:%M IST')}
"""
        return self._send(text.strip())

    def send_execution(self, exec_data: Dict) -> bool:
        """Send execution confirmation."""
        symbol = exec_data.get("symbol", "?")
        qty = exec_data.get("quantity", 0)
        price = exec_data.get("entry_price", 0)

        text = f"""
✅ <b>ORDER EXECUTED</b>

📌 {symbol} x{qty} @ ₹{price:,.2f}
⏰ {datetime.now(IST).strftime('%H:%M IST')}
"""
        return self._send(text.strip())

    def send_exit(self, exit_data: Dict) -> bool:
        """Send exit alert."""
        symbol = exit_data.get("symbol", "?")
        pnl = exit_data.get("pnl", 0)
        reason = exit_data.get("exit_reason", "?")
        emoji = "💚" if pnl >= 0 else "💔"

        text = f"""
{emoji} <b>POSITION CLOSED</b>

📌 {symbol}
💰 P&L: ₹{pnl:+,.0f}
📝 Reason: {reason}
⏰ {datetime.now(IST).strftime('%H:%M IST')}
"""
        return self._send(text.strip())

    def send_circuit_breaker(self, status: Dict) -> bool:
        """Send circuit breaker alert."""
        level = status.get("level", "UNKNOWN")
        alerts = status.get("alerts", [])

        text = f"""
🚨 <b>CIRCUIT BREAKER — {level}</b>

{''.join(f'⚠️ {a}' + chr(10) for a in alerts)}
⏰ {datetime.now(IST).strftime('%H:%M IST')}
"""
        return self._send(text.strip())

    def send_daily_report(self, report: str) -> bool:
        """Send daily summary report."""
        # Telegram has 4096 char limit, truncate if needed
        if len(report) > 4000:
            report = report[:3950] + "\n\n[... truncated ...]"
        return self._send(f"<pre>{report}</pre>")

    def send_pnl_update(self, pnl: float, equity: float) -> bool:
        """Hourly P&L update."""
        emoji = "📈" if pnl >= 0 else "📉"
        text = f"""
{emoji} <b>P&L Update</b>
💰 Today: ₹{pnl:+,.0f}
📊 Equity: ₹{equity:,.0f}
⏰ {datetime.now(IST).strftime('%H:%M IST')}
"""
        return self._send(text.strip())

    @property
    def is_enabled(self) -> bool:
        return self._enabled
