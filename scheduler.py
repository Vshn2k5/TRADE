"""
APEX INDIA — Main Orchestrator / Scheduler
=============================================
Central event loop that coordinates all system operations:
data ingestion, signal computation, position monitoring,
model updates, and report generation.

Uses APScheduler for cron-like task scheduling with
market-hours awareness and holiday detection.
"""

import signal
import threading
from datetime import datetime, time as dt_time
from typing import Callable, Dict, List, Optional

import pytz

from apex_india.utils.logger import get_logger, get_trade_logger
from apex_india.utils.config import get_config

logger = get_logger("scheduler")
trade_logger = get_trade_logger()


# ═══════════════════════════════════════════════════════════════
# MARKET CALENDAR
# ═══════════════════════════════════════════════════════════════

class MarketCalendar:
    """
    Indian market calendar with holiday awareness.
    Determines if the market is open and which session we're in.
    """

    IST = pytz.timezone("Asia/Kolkata")

    # NSE Holidays 2026 (must be updated annually)
    # Format: (month, day, description)
    NSE_HOLIDAYS_2026 = [
        (1, 26, "Republic Day"),
        (2, 26, "Maha Shivaratri"),
        (3, 10, "Holi"),
        (3, 31, "Id-Ul-Fitr (Ramadan)"),
        (4, 1, "Annual Bank Closing"),
        (4, 6, "Shri Ram Navami"),
        (4, 10, "Mahavir Jayanti"),
        (4, 14, "Dr. Ambedkar Jayanti"),
        (4, 18, "Good Friday"),
        (5, 1, "Maharashtra Day"),
        (5, 12, "Buddha Purnima"),
        (6, 7, "Bakri Id"),
        (7, 6, "Muharram"),
        (8, 15, "Independence Day"),
        (8, 16, "Janmashtami"),
        (9, 4, "Milad Un Nabi"),
        (10, 2, "Mahatma Gandhi Jayanti"),
        (10, 20, "Dussehra"),
        (10, 21, "Dussehra"),
        (11, 5, "Diwali (Laxmi Pujan)"),
        (11, 7, "Diwali (Balipratipada)"),
        (11, 24, "Guru Nanak Jayanti"),
        (12, 25, "Christmas"),
    ]

    def __init__(self):
        self._holidays = set()
        for month, day, _ in self.NSE_HOLIDAYS_2026:
            from datetime import date
            try:
                self._holidays.add(date(2026, month, day))
            except ValueError:
                pass

    def is_trading_day(self, check_date=None) -> bool:
        """Check if the given date is a trading day (not weekend/holiday)."""
        from datetime import date
        if check_date is None:
            check_date = datetime.now(self.IST).date()
        if isinstance(check_date, datetime):
            check_date = check_date.date()

        # Weekend check
        if check_date.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Holiday check
        if check_date in self._holidays:
            return False

        return True

    def is_market_open(self) -> bool:
        """Check if the market is currently open."""
        if not self.is_trading_day():
            return False

        now = datetime.now(self.IST).time()
        return dt_time(9, 15) <= now <= dt_time(15, 30)

    def is_pre_market(self) -> bool:
        """Check if we're in the pre-market window."""
        if not self.is_trading_day():
            return False

        now = datetime.now(self.IST).time()
        return dt_time(9, 0) <= now < dt_time(9, 15)

    def is_post_market(self) -> bool:
        """Check if we're in the post-market window."""
        if not self.is_trading_day():
            return False

        now = datetime.now(self.IST).time()
        return dt_time(15, 30) < now <= dt_time(16, 0)

    def current_session(self) -> str:
        """Get the current trading session label."""
        if not self.is_trading_day():
            return "CLOSED"

        now = datetime.now(self.IST).time()

        if now < dt_time(9, 0):
            return "PRE_HOURS"
        elif now < dt_time(9, 15):
            return "PRE_OPEN"
        elif now < dt_time(9, 30):
            return "OPENING_VOLATILITY"
        elif now < dt_time(11, 0):
            return "MORNING_TREND"
        elif now < dt_time(12, 30):
            return "MIDDAY_LULL"
        elif now < dt_time(13, 0):
            return "LUNCH_REVERSAL"
        elif now < dt_time(14, 30):
            return "AFTERNOON_MOMENTUM"
        elif now < dt_time(15, 0):
            return "FINAL_HOUR"
        elif now <= dt_time(15, 30):
            return "CLOSING_WINDOW"
        elif now <= dt_time(16, 0):
            return "POST_MARKET"
        else:
            return "AFTER_HOURS"

    def next_market_open(self) -> datetime:
        """Calculate when the market next opens."""
        from datetime import timedelta, date

        now = datetime.now(self.IST)
        check_date = now.date()

        # If market is already open or will open today
        if self.is_trading_day(check_date) and now.time() < dt_time(9, 15):
            return self.IST.localize(
                datetime.combine(check_date, dt_time(9, 15))
            )

        # Find next trading day
        check_date += timedelta(days=1)
        max_search = 10  # Safety: don't loop forever
        for _ in range(max_search):
            if self.is_trading_day(check_date):
                return self.IST.localize(
                    datetime.combine(check_date, dt_time(9, 15))
                )
            check_date += timedelta(days=1)

        return self.IST.localize(
            datetime.combine(check_date, dt_time(9, 15))
        )


# ═══════════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════════

class ApexScheduler:
    """
    Main orchestrator for the APEX INDIA trading system.

    Manages the lifecycle of all scheduled tasks:
    - Market data ingestion (every tick / 1 second)
    - Signal computation (every 60 seconds)
    - Position monitoring (every 60 seconds)
    - Regime detection (every 15 minutes)
    - Model updates (daily after market close)
    - Report generation (daily/weekly/monthly)
    """

    def __init__(self):
        self.config = get_config()
        self.calendar = MarketCalendar()
        self._running = False
        self._shutdown_event = threading.Event()
        self._registered_tasks: Dict[str, dict] = {}

        # Scheduler will be initialized when we have APScheduler
        self._scheduler = None

    def register_task(
        self,
        name: str,
        func: Callable,
        trigger: str = "interval",
        market_hours_only: bool = True,
        **trigger_kwargs,
    ) -> None:
        """
        Register a task for scheduled execution.

        Args:
            name: Unique task identifier
            func: Callable to execute
            trigger: APScheduler trigger type ('interval', 'cron')
            market_hours_only: If True, only runs during market hours
            **trigger_kwargs: Additional trigger arguments
                (seconds, minutes, hour, minute, etc.)
        """
        self._registered_tasks[name] = {
            "func": func,
            "trigger": trigger,
            "market_hours_only": market_hours_only,
            "trigger_kwargs": trigger_kwargs,
        }
        logger.info(
            f"Registered task: {name} | trigger={trigger} | "
            f"market_hours_only={market_hours_only} | "
            f"kwargs={trigger_kwargs}"
        )

    def start(self) -> None:
        """Start the scheduler and all registered tasks."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from apscheduler.triggers.cron import CronTrigger

            self._scheduler = BackgroundScheduler(
                timezone=pytz.timezone("Asia/Kolkata"),
                job_defaults={
                    "coalesce": True,          # Merge missed executions
                    "max_instances": 1,         # No parallel runs of same job
                    "misfire_grace_time": 30,   # 30 sec grace for misfires
                },
            )

            for name, task in self._registered_tasks.items():
                func = task["func"]
                trigger = task["trigger"]
                market_only = task["market_hours_only"]
                kwargs = task["trigger_kwargs"]

                # Wrap function with market-hours check if needed
                if market_only:
                    wrapped_func = self._wrap_market_hours(func, name)
                else:
                    wrapped_func = func

                self._scheduler.add_job(
                    wrapped_func,
                    trigger=trigger,
                    id=name,
                    name=name,
                    **kwargs,
                )

            self._scheduler.start()
            self._running = True
            logger.info(
                f"Scheduler started with {len(self._registered_tasks)} tasks ✓"
            )

        except ImportError:
            logger.warning(
                "APScheduler not installed — running in manual mode. "
                "Install with: pip install APScheduler"
            )

    def _wrap_market_hours(self, func: Callable, task_name: str) -> Callable:
        """Wrap a function to only execute during market hours."""
        def wrapper():
            if self.calendar.is_market_open():
                try:
                    func()
                except Exception as e:
                    logger.error(f"Task '{task_name}' failed: {e}", exc_info=True)
            else:
                logger.debug(
                    f"Task '{task_name}' skipped — market closed "
                    f"(session: {self.calendar.current_session()})"
                )
        wrapper.__name__ = f"{func.__name__}_market_hours"
        return wrapper

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        logger.info("Stopping scheduler...")
        self._running = False
        self._shutdown_event.set()

        if self._scheduler:
            self._scheduler.shutdown(wait=True)

        logger.info("Scheduler stopped ✓")

    def run_forever(self) -> None:
        """
        Block the main thread and keep the scheduler running.
        Handles graceful shutdown on SIGINT/SIGTERM.
        """
        # Register signal handlers for graceful shutdown
        def _signal_handler(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info(f"Received {sig_name} — initiating graceful shutdown...")
            self.stop()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        logger.info("APEX INDIA scheduler running. Press Ctrl+C to stop.")

        try:
            self._shutdown_event.wait()
        except KeyboardInterrupt:
            self.stop()

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        """Get current scheduler status and job list."""
        status = {
            "running": self._running,
            "market_open": self.calendar.is_market_open(),
            "current_session": self.calendar.current_session(),
            "is_trading_day": self.calendar.is_trading_day(),
            "registered_tasks": list(self._registered_tasks.keys()),
            "next_market_open": str(self.calendar.next_market_open()),
        }

        if self._scheduler and self._running:
            jobs = self._scheduler.get_jobs()
            status["active_jobs"] = [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                }
                for job in jobs
            ]

        return status
