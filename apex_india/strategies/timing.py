"""
APEX INDIA — Entry Timing Intelligence
=========================================
Time-of-day and calendar-based intelligence for optimizing
entry/exit timing in Indian markets.

Components:
- Session-based trading windows
- Calendar intelligence (expiry, RBI, budget)
- Scale-in timing logic
- Optimal entry window enforcement

Usage:
    timing = TimingIntelligence()
    window = timing.get_current_window()
    can_trade = timing.is_entry_allowed()
"""

from datetime import datetime, time, date, timedelta
from typing import Any, Dict, Optional, Tuple

import pytz

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import MARKET_TIMEZONE

logger = get_logger("strategies.timing")

IST = pytz.timezone(MARKET_TIMEZONE)


class TimingIntelligence:
    """
    Market session and calendar-aware entry timing.

    Session Windows (IST):
    - Pre-open:     09:00 - 09:15  (no trades)
    - Opening Rush:  09:15 - 09:30  (avoid new entries — high volatility)
    - Morning Prime: 09:30 - 11:30  (optimal for breakout strategies)
    - Midday Lull:  11:30 - 13:30  (reduced activity, mean reversion)
    - Afternoon:    13:30 - 14:30  (institutional activity picks up)
    - Power Hour:   14:30 - 15:15  (exit/position adjustment)
    - Close:        15:15 - 15:30  (square off intraday, no new entries)
    """

    # Session definitions
    SESSIONS = {
        "PRE_OPEN":      (time(9, 0), time(9, 15)),
        "OPENING_RUSH":  (time(9, 15), time(9, 30)),
        "MORNING_PRIME": (time(9, 30), time(11, 30)),
        "MIDDAY_LULL":   (time(11, 30), time(13, 30)),
        "AFTERNOON":     (time(13, 30), time(14, 30)),
        "POWER_HOUR":    (time(14, 30), time(15, 15)),
        "CLOSE":         (time(15, 15), time(15, 30)),
    }

    # Strategies allowed by session
    SESSION_STRATEGIES = {
        "PRE_OPEN": [],
        "OPENING_RUSH": ["orb", "gap_trade"],
        "MORNING_PRIME": [
            "trend_rider", "vol_breakout", "orb", "gap_trade",
            "sector_rotation", "swing_positional", "smc_reversal",
        ],
        "MIDDAY_LULL": ["vwap_mr", "theta_harvest"],
        "AFTERNOON": [
            "trend_rider", "vol_breakout", "vwap_mr",
            "swing_positional", "earnings",
        ],
        "POWER_HOUR": ["vwap_mr"],
        "CLOSE": [],
    }

    def __init__(self):
        # Known calendar events (static, update periodically)
        self._expiry_weekday = 3  # Thursday = 3

    # ───────────────────────────────────────────────────────────
    # Session Detection
    # ───────────────────────────────────────────────────────────

    def get_current_session(self) -> str:
        """Get the current market session name."""
        now = datetime.now(IST).time()

        for session_name, (start, end) in self.SESSIONS.items():
            if start <= now < end:
                return session_name

        return "CLOSED"

    def get_session_info(self) -> Dict[str, Any]:
        """Get detailed info about the current session."""
        session = self.get_current_session()
        now = datetime.now(IST)

        if session == "CLOSED":
            return {
                "session": "CLOSED",
                "market_open": False,
                "allowed_strategies": [],
                "note": "Market closed",
            }

        start, end = self.SESSIONS[session]
        remaining = datetime.combine(now.date(), end) - datetime.combine(now.date(), now.time())

        return {
            "session": session,
            "market_open": True,
            "start": str(start),
            "end": str(end),
            "remaining_minutes": int(remaining.total_seconds() / 60),
            "allowed_strategies": self.SESSION_STRATEGIES.get(session, []),
        }

    # ───────────────────────────────────────────────────────────
    # Entry Permission
    # ───────────────────────────────────────────────────────────

    def is_entry_allowed(
        self,
        strategy_name: str = "",
        is_intraday: bool = True,
    ) -> Tuple[bool, str]:
        """
        Check if a new entry is allowed right now.

        Rules:
        - Must be within market hours
        - Must be within allowed session for the strategy
        - No new entries after 15:00 for intraday
        - No new entries during pre-open or opening rush (except ORB/gap)
        """
        session = self.get_current_session()

        if session == "CLOSED":
            return False, "Market closed"

        if session == "PRE_OPEN":
            return False, "Pre-open session — no trading"

        # Strategy-specific session check
        allowed = self.SESSION_STRATEGIES.get(session, [])
        if strategy_name and strategy_name not in allowed:
            return False, f"Strategy '{strategy_name}' not active in {session}"

        # Intraday cutoff
        if is_intraday:
            now = datetime.now(IST).time()
            if now >= time(15, 0):
                return False, "Intraday entry cutoff (15:00)"

        return True, f"Entry allowed in {session}"

    # ───────────────────────────────────────────────────────────
    # Calendar Intelligence
    # ───────────────────────────────────────────────────────────

    def get_calendar_context(self) -> Dict[str, Any]:
        """
        Get calendar-based market context for today.

        Important dates:
        - F&O Expiry (last Thursday of month)
        - Weekly expiry (Thursday)
        - RBI policy dates
        - Budget day
        - Quarter-end
        """
        today = datetime.now(IST).date()
        weekday = today.weekday()

        context = {
            "date": str(today),
            "weekday": today.strftime("%A"),
            "is_weekly_expiry": weekday == self._expiry_weekday,
            "is_monthly_expiry": self._is_monthly_expiry(today),
            "is_quarter_end": today.month in [3, 6, 9, 12] and today.day >= 25,
            "days_to_monthly_expiry": self._days_to_monthly_expiry(today),
            "special_events": [],
            "risk_adjustment": 1.0,
        }

        # Risk adjustments
        if context["is_monthly_expiry"]:
            context["risk_adjustment"] = 0.7
            context["special_events"].append("Monthly F&O Expiry — reduce size 30%")
        elif context["is_weekly_expiry"]:
            context["risk_adjustment"] = 0.85
            context["special_events"].append("Weekly Expiry — reduce size 15%")

        if context["is_quarter_end"]:
            context["special_events"].append("Quarter-end — expect FII flows")

        # Avoid Monday morning (gap risk) and Friday afternoon (weekend risk)
        if weekday == 0:  # Monday
            now = datetime.now(IST).time()
            if now < time(10, 0):
                context["special_events"].append("Monday morning — wait for gap settlement")
                context["risk_adjustment"] *= 0.8
        elif weekday == 4:  # Friday
            now = datetime.now(IST).time()
            if now > time(14, 0):
                context["special_events"].append("Friday afternoon — reduce overnight risk")
                context["risk_adjustment"] *= 0.8

        return context

    def _is_monthly_expiry(self, d: date) -> bool:
        """Check if today is the last Thursday of the month."""
        if d.weekday() != self._expiry_weekday:
            return False
        # Check if next Thursday is in the next month
        next_week = d + timedelta(days=7)
        return next_week.month != d.month

    def _days_to_monthly_expiry(self, d: date) -> int:
        """Calculate days to the next monthly expiry."""
        # Find last Thursday of current month
        year, month = d.year, d.month

        # Get last day of month
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        # Find last Thursday
        while last_day.weekday() != self._expiry_weekday:
            last_day -= timedelta(days=1)

        if last_day >= d:
            return (last_day - d).days
        else:
            # Next month
            if month == 12:
                last_day = date(year + 1, 2, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 2, 1) - timedelta(days=1)
            while last_day.weekday() != self._expiry_weekday:
                last_day -= timedelta(days=1)
            return (last_day - d).days

    # ───────────────────────────────────────────────────────────
    # Scale-In Timing
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def scale_in_plan(
        total_quantity: int,
        tranches: int = 3,
    ) -> list:
        """
        Split an order into scale-in tranches.

        Default: 40% / 30% / 30% across 3 entries.
        """
        if tranches <= 1:
            return [total_quantity]

        splits = [0.4, 0.3, 0.3] if tranches == 3 else [1.0 / tranches] * tranches
        quantities = [max(1, int(total_quantity * s)) for s in splits]

        # Adjust for rounding
        diff = total_quantity - sum(quantities)
        quantities[0] += diff

        return quantities
