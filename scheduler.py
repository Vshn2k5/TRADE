"""
APEX INDIA — Main Scheduler / Orchestrator (Refactored for Dual Mode & Free Tier)
================================================================================
APScheduler-based orchestrator that runs the complete trading pipeline.
Now supports the "Zero Cost" setup using yfinance and dual Paper/Real modes.
"""

import sys
import time
import signal
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import pytz

# Ensure project root in path
PROJECT_ROOT = str(Path(__file__).resolve().parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE, NIFTY_50_SYMBOLS
from apex_india.data.feeds.free_feed import FreeFeedManager
from apex_india.server.app import store  # Shared state store

logger = get_logger("scheduler")
IST = pytz.timezone(MARKET_TIMEZONE)

class ApexScheduler:
    """
    Main trading system orchestrator (Zero-Cost / Dual Mode Version).
    """

    def __init__(self, mode: str = "paper"):
        self.mode = mode
        self._running = False
        self._poll_interval = 60 # 1 minute for free tier

        # Core components
        self._broker = None
        self._engine = None
        self._pnl_tracker = None
        self._circuit_breaker = None
        self._notifier = None
        self._feed = None
        
        # Sync thread
        self._sync_thread = None

    def initialize(self) -> bool:
        """Initialize all system components."""
        logger.info(f"Initializing APEX INDIA (Setup: FREE | Mode: {self.mode.upper()})...")

        try:
            from apex_india.execution.paper_broker import PaperBroker
            from apex_india.execution.execution_engine import ExecutionEngine
            from apex_india.execution.pnl_tracker import PnLTracker
            from apex_india.risk.circuit_breaker import CircuitBreaker
            from apex_india.alerts.telegram_bot import TelegramBot
            from apex_india.alerts.notification_manager import NotificationManager

            # 1. Initialize Free Data Feed
            self._feed = FreeFeedManager(poll_interval=self._poll_interval)
            # Add Nifty Top 10 for the free watchlist
            self._feed.add_symbols(["RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK", "SBIN", "BHARTIARTL", "LT", "ITC", "KOTAKBANK"])
            self._feed.start()

            # 2. Initialize Broker (Dynamic)
            # Default to PaperBroker for Phase 1 Free Setup
            # If user eventually provides Shoonya/Zerodha keys, we swap here
            self._broker = PaperBroker(initial_capital=10000) # Starting small as per user request
            self._broker.connect({})

            # 3. Initialize Risk & Execution
            self._circuit_breaker = CircuitBreaker(capital=10000)
            self._engine = ExecutionEngine(
                broker=self._broker,
                circuit_breaker=self._circuit_breaker,
            )
            self._pnl_tracker = PnLTracker(initial_capital=10000)
            self._notifier = NotificationManager(TelegramBot())

            logger.info("APEX components initialized. Status: READY.")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def start(self):
        """Start the orchestrator loop."""
        if not self.initialize():
            return

        self._running = True
        
        # Start background sync with FastAPI server
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()

        # Handle signals
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

        logger.info("=" * 60)
        logger.info("  APEX INDIA — ZERO COST SYSTEM ACTIVE")
        logger.info(f"  Data: yfinance (polling {self._poll_interval}s)")
        logger.info(f"  Dashboard: http://localhost:8000")
        logger.info("=" * 60)

        try:
            while self._running:
                now = datetime.now(IST)
                
                # Update mode from dashboard toggle
                dashboard_mode = store.state.get("mode")
                if dashboard_mode != self.mode:
                    logger.info(f"Mode changed via Dashboard: {self.mode} -> {dashboard_mode}")
                    self.mode = dashboard_mode
                
                # Check for system halt from dashboard
                if not store.state.get("running") and self._running and now.hour > 0:
                    # (Initial running state is False, wait for first toggle or skip check at midnight)
                    pass

                # Main Logic
                if self._is_market_hours(now):
                    self._market_loop(now)
                
                time.sleep(10) # Small sleep, market loop handles its own timing
        except KeyboardInterrupt:
            self._handle_exit()

    def _market_loop(self, now: datetime):
        """Standard market-hours operations."""
        # 1. Get latest prices from Free Feed
        prices = {}
        for s, data in self._feed.get_all_data().items():
            clean_s = s.replace(".NS", "").replace(".BO", "")
            prices[clean_s] = data["price"]

        if not prices:
            return

        # 2. Update Position Monitor
        if self._engine:
            self._engine.update_positions(prices)

        # 3. Signal Scan (Every 15 mins)
        if now.minute % 15 == 0 and now.second < 10:
            self._scan_and_execute(prices)

    def _scan_and_execute(self, prices: Dict[str, float]):
        """Run signals and send to execution engine."""
        logger.info(f"Scanning for signals in {self.mode.upper()} mode...")
        # Placeholder for Strategy Selector logic
        # In this phase, we are waiting for user-specific strategy or using Phase 3 defaults
        pass

    def _sync_loop(self):
        """Background thread to push system state to the FastAPI server."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _sync():
            while self._running:
                try:
                    # Gather state
                    active_positions = []
                    if self._engine:
                        for tid, trade in self._engine.active_trades.items():
                            symbol = trade["signal"].symbol
                            ltp = self._feed.get_latest_price(symbol) or trade["entry_price"]
                            active_positions.append({
                                "symbol": symbol,
                                "direction": trade["signal"].direction.value,
                                "quantity": trade["quantity"],
                                "entry": trade["entry_price"],
                                "ltp": ltp,
                                "pnl": round((ltp - trade["entry_price"]) * trade["quantity"] if trade["signal"].direction.value == "LONG" else (trade["entry_price"] - ltp) * trade["quantity"], 2)
                            })

                    # Push to FastAPI state store
                    store.update({
                        "running": self._running,
                        "market_open": self._is_market_hours(datetime.now(IST)),
                        "equity": self._pnl_tracker.equity if self._pnl_tracker else 10000,
                        "day_pnl": self._pnl_tracker.total_pnl if self._pnl_tracker else 0,
                        "active_trades": len(active_positions),
                        "positions": active_positions,
                        "mode": self.mode
                    })
                    
                    # Broadcast to WebSocket clients
                    await store.broadcast()
                except Exception as e:
                    logger.debug(f"Sync error: {e}")
                
                await asyncio.sleep(2) # Sync every 2 seconds

        loop.run_until_complete(_sync())

    def _is_market_hours(self, now: datetime) -> bool:
        """Weekday 9:15-15:30 IST."""
        if now.weekday() >= 5: return False
        from datetime import time as dtime
        # Allow simulation if not in market hours for testing? No, keep it real as requested.
        return dtime(9, 15) <= now.time() <= dtime(15, 30)

    def _handle_exit(self, *args):
        self._running = False
        if self._feed: self._feed.stop()
        logger.info("APEX Schduler shutdown complete.")
        sys.exit(0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="paper")
    args = parser.parse_args()
    
    scheduler = ApexScheduler(mode=args.mode)
    scheduler.start()
