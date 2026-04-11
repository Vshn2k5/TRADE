"""
APEX INDIA — Structured Logging System
========================================
Production-grade logging with structured output, rotation, and
separate log files for trading activity, errors, and system events.

Usage:
    from apex_india.utils.logger import get_logger
    logger = get_logger("module_name")
    logger.info("Signal generated", symbol="RELIANCE", confidence=78.5)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from loguru import logger as _loguru_logger


# ═══════════════════════════════════════════════════════════════
# LOG DIRECTORY SETUP
# ═══════════════════════════════════════════════════════════════

# Resolve project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# LOG FORMAT DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# Console format — colorized, human-readable
_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[module]}</cyan> | "
    "<level>{message}</level>"
    "{exception}"
)

# File format — structured, parseable
_FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{extra[module]} | "
    "{message}"
    "{exception}"
)

# Trading log format — includes trade-specific metadata
_TRADE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "TRADE | "
    "{message}"
    "{exception}"
)


# ═══════════════════════════════════════════════════════════════
# LOGGER CONFIGURATION
# ═══════════════════════════════════════════════════════════════

def _configure_loguru(log_level: str = "INFO") -> None:
    """
    Configure loguru with multiple sinks:
    1. Console (colorized, level-filtered)
    2. system.log (all INFO+ messages, rotated daily)
    3. errors.log (ERROR+ only, rotated weekly)
    4. trading.log (trade-related messages, rotated daily)
    5. debug.log (DEBUG+ for troubleshooting, rotated daily)
    """
    # Remove default loguru handler
    _loguru_logger.remove()

    # ── Sink 1: Console Output ────────────────────────────────
    _loguru_logger.add(
        sys.stdout,
        format=_CONSOLE_FORMAT,
        level=log_level,
        colorize=True,
        filter=lambda record: record["extra"].get("module", "system") != "_silent",
    )

    # ── Sink 2: System Log (all INFO+ activity) ──────────────
    _loguru_logger.add(
        str(_LOG_DIR / "system_{time:YYYY-MM-DD}.log"),
        format=_FILE_FORMAT,
        level="INFO",
        rotation="00:00",        # New file at midnight
        retention="30 days",     # Keep 30 days of logs
        compression="gz",       # Compress old logs
        encoding="utf-8",
        enqueue=True,            # Thread-safe async writes
    )

    # ── Sink 3: Error Log (ERROR+ only) ──────────────────────
    _loguru_logger.add(
        str(_LOG_DIR / "errors_{time:YYYY-MM-DD}.log"),
        format=_FILE_FORMAT,
        level="ERROR",
        rotation="1 week",
        retention="90 days",
        compression="gz",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,          # Full exception traceback
        diagnose=True,           # Variable inspection on errors
    )

    # ── Sink 4: Trading Log (trade actions only) ─────────────
    _loguru_logger.add(
        str(_LOG_DIR / "trading_{time:YYYY-MM-DD}.log"),
        format=_TRADE_FORMAT,
        level="INFO",
        rotation="00:00",
        retention="365 days",    # Keep full year for audit
        compression="gz",
        encoding="utf-8",
        enqueue=True,
        filter=lambda record: record["extra"].get("category") == "trade",
    )

    # ── Sink 5: Debug Log (everything, for troubleshooting) ──
    _loguru_logger.add(
        str(_LOG_DIR / "debug_{time:YYYY-MM-DD}.log"),
        format=_FILE_FORMAT,
        level="DEBUG",
        rotation="00:00",
        retention="7 days",      # Short retention for debug
        compression="gz",
        encoding="utf-8",
        enqueue=True,
    )


# Initialize on module import
_is_configured = False


def _ensure_configured(log_level: str = "INFO") -> None:
    """Ensure loguru is configured exactly once."""
    global _is_configured
    if not _is_configured:
        _configure_loguru(log_level)
        _is_configured = True


# ═══════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════

def get_logger(module_name: str, log_level: str = "INFO"):
    """
    Get a logger instance bound to a specific module name.

    Args:
        module_name: Name of the calling module (e.g., 'data.feeds.websocket')
        log_level: Minimum log level for console output

    Returns:
        A loguru logger instance with the module name bound.

    Usage:
        logger = get_logger("execution.order_manager")
        logger.info("Order placed", symbol="RELIANCE", qty=100, price=2450.50)
        logger.error("Order rejected", order_id="ORD123", reason="Insufficient margin")
    """
    _ensure_configured(log_level)
    return _loguru_logger.bind(module=module_name)


def get_trade_logger():
    """
    Get a specialized logger for trade-related events.
    Messages from this logger are routed to trading.log.

    Usage:
        trade_log = get_trade_logger()
        trade_log.info("SIGNAL | BUY RELIANCE @ 2450.50 | Conf: 78% | RR: 1:3.2")
        trade_log.info("EXECUTED | Bought 100 RELIANCE @ 2451.00 | Slippage: 0.02%")
        trade_log.info("EXIT | Sold 100 RELIANCE @ 2530.00 | P&L: +₹7,900")
    """
    _ensure_configured()
    return _loguru_logger.bind(module="trading", category="trade")


def reconfigure(log_level: str) -> None:
    """
    Reconfigure the logging level at runtime.
    Useful for switching between DEBUG mode during development
    and INFO mode in production.
    """
    global _is_configured
    _is_configured = False
    _ensure_configured(log_level)


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE: Module-level logger for quick usage
# ═══════════════════════════════════════════════════════════════

# Pre-configured logger for ad-hoc use
system_logger = get_logger("system")
