"""
APEX INDIA — Constants & Market Reference Data
================================================
Centralized source of truth for all market constants, exchange symbols,
Nifty constituent lists, lot sizes, and trading session definitions.

All values are immutable at runtime. Configuration-level parameters
that may change between environments belong in config.yaml instead.
"""

from enum import Enum, unique
from typing import Dict, FrozenSet, List, Tuple
from datetime import time


# ═══════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════

@unique
class Exchange(str, Enum):
    """Supported Indian stock exchanges."""
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NFO = "NFO"    # NSE F&O segment
    BFO = "BFO"    # BSE F&O segment
    CDS = "CDS"    # Currency Derivatives


@unique
class Segment(str, Enum):
    """Market segments."""
    EQUITY = "EQUITY"
    FNO = "FNO"
    CURRENCY = "CURRENCY"
    COMMODITY = "COMMODITY"


@unique
class OrderSide(str, Enum):
    """Trade direction."""
    BUY = "BUY"
    SELL = "SELL"


@unique
class OrderType(str, Enum):
    """Broker order types."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"           # Stop-Loss Limit
    SL_M = "SL-M"       # Stop-Loss Market


@unique
class ProductType(str, Enum):
    """Broker product types (Zerodha nomenclature)."""
    CNC = "CNC"          # Cash & Carry (delivery)
    MIS = "MIS"          # Margin Intraday Settlement
    NRML = "NRML"        # Normal (F&O overnight)


@unique
class MarketRegime(str, Enum):
    """Market regime classifications for strategy selection."""
    TRENDING_BULLISH = "TRENDING_BULLISH"
    TRENDING_BEARISH = "TRENDING_BEARISH"
    MEAN_REVERTING = "MEAN_REVERTING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    BREAKOUT_PENDING = "BREAKOUT_PENDING"
    DISTRIBUTION = "DISTRIBUTION"
    ACCUMULATION = "ACCUMULATION"


@unique
class SignalGrade(str, Enum):
    """Trade signal quality grades."""
    A_PLUS = "A+"    # Act immediately — highest conviction
    A = "A"          # Strong signal — enter on confirmation
    B_PLUS = "B+"    # Decent signal — smaller position
    B = "B"          # Marginal — only if portfolio has room


@unique
class TradeAction(str, Enum):
    """Trade actions for signal output."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@unique
class StrategyName(str, Enum):
    """Registered strategy identifiers."""
    TREND_MOMENTUM_RIDER = "trend_momentum_rider"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    VWAP_MEAN_REVERSION = "vwap_mean_reversion"
    OPENING_RANGE_BREAKOUT = "opening_range_breakout"
    EARNINGS_MOMENTUM = "earnings_momentum"
    SECTOR_ROTATION = "sector_rotation"
    OPTIONS_THETA_HARVEST = "options_theta_harvest"
    SMC_REVERSAL = "smc_reversal"
    GAP_TRADE = "gap_trade"
    SWING_POSITIONAL = "swing_positional"


@unique
class Timeframe(str, Enum):
    """Supported OHLCV timeframes."""
    M1 = "minute"
    M3 = "3minute"
    M5 = "5minute"
    M15 = "15minute"
    M30 = "30minute"
    M60 = "60minute"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# ═══════════════════════════════════════════════════════════════
# TRADING SESSION TIMES (IST)
# ═══════════════════════════════════════════════════════════════

class TradingSession:
    """Indian market trading session boundaries (all times IST)."""

    PRE_OPEN_START = time(9, 0)
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)
    POST_CLOSE = time(16, 0)

    # Observation & entry windows
    OPENING_OBSERVE_END = time(9, 30)     # No trades in first 15 min
    MORNING_WINDOW_END = time(11, 0)       # Best window for ORB/momentum
    MIDDAY_LULL_START = time(11, 0)
    MIDDAY_LULL_END = time(12, 30)
    LUNCH_REVERSAL_ZONE = time(13, 0)
    AFTERNOON_WINDOW_START = time(13, 0)
    AFTERNOON_WINDOW_END = time(14, 30)
    FINAL_HOUR_START = time(14, 30)
    NO_NEW_ENTRIES_AFTER = time(15, 0)
    INTRADAY_EXIT_BY = time(15, 15)       # Must close all intraday

    # Session labels for scheduling
    SESSIONS: List[Tuple[time, time, str]] = [
        (time(9, 0), time(9, 15), "PRE_OPEN"),
        (time(9, 15), time(9, 30), "OPENING_VOLATILITY"),
        (time(9, 30), time(11, 0), "MORNING_TREND"),
        (time(11, 0), time(12, 30), "MIDDAY_LULL"),
        (time(12, 30), time(13, 0), "LUNCH_REVERSAL"),
        (time(13, 0), time(14, 30), "AFTERNOON_MOMENTUM"),
        (time(14, 30), time(15, 0), "FINAL_HOUR"),
        (time(15, 0), time(15, 30), "CLOSING_WINDOW"),
    ]


# ═══════════════════════════════════════════════════════════════
# NIFTY 50 CONSTITUENTS (as of April 2026)
# ═══════════════════════════════════════════════════════════════
# NOTE: This list should be updated quarterly when SEBI/NSE
# revises the index composition. Use the NSE data feed to
# auto-update in production.

NIFTY_50_SYMBOLS: FrozenSet[str] = frozenset({
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BPCL",
    "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK",
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
    "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK",
    "LT", "M&M", "MARUTI", "NTPC", "NESTLEIND",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
})


# ═══════════════════════════════════════════════════════════════
# NIFTY BANK CONSTITUENTS
# ═══════════════════════════════════════════════════════════════

NIFTY_BANK_SYMBOLS: FrozenSet[str] = frozenset({
    "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
    "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB",
    "BANKBARODA", "AUBANK",
})


# ═══════════════════════════════════════════════════════════════
# NIFTY SECTOR INDEX SYMBOLS
# ═══════════════════════════════════════════════════════════════

NIFTY_SECTOR_INDICES: Dict[str, str] = {
    "IT": "NIFTY IT",
    "BANK": "NIFTY BANK",
    "AUTO": "NIFTY AUTO",
    "PHARMA": "NIFTY PHARMA",
    "FMCG": "NIFTY FMCG",
    "METAL": "NIFTY METAL",
    "REALTY": "NIFTY REALTY",
    "ENERGY": "NIFTY ENERGY",
    "INFRA": "NIFTY INFRA",
    "PSU_BANK": "NIFTY PSU BANK",
    "FINANCIAL": "NIFTY FINANCIAL SERVICES",
    "MEDIA": "NIFTY MEDIA",
}


# ═══════════════════════════════════════════════════════════════
# STOCK-TO-SECTOR MAPPING (Nifty 50)
# ═══════════════════════════════════════════════════════════════

STOCK_SECTOR_MAP: Dict[str, str] = {
    # IT
    "INFY": "IT", "TCS": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT",
    # Banking & Financial
    "HDFCBANK": "BANK", "ICICIBANK": "BANK", "KOTAKBANK": "BANK",
    "AXISBANK": "BANK", "SBIN": "BANK", "INDUSINDBK": "BANK",
    "BAJFINANCE": "FINANCIAL", "BAJAJFINSV": "FINANCIAL",
    "HDFCLIFE": "FINANCIAL", "SBILIFE": "FINANCIAL",
    # Auto
    "BAJAJ-AUTO": "AUTO", "EICHERMOT": "AUTO", "HEROMOTOCO": "AUTO",
    "M&M": "AUTO", "MARUTI": "AUTO", "TATAMOTORS": "AUTO", "TRENT": "AUTO",
    # Pharma & Healthcare
    "CIPLA": "PHARMA", "DRREDDY": "PHARMA", "SUNPHARMA": "PHARMA",
    "APOLLOHOSP": "PHARMA",
    # FMCG
    "BRITANNIA": "FMCG", "HINDUNILVR": "FMCG", "ITC": "FMCG",
    "NESTLEIND": "FMCG", "TATACONSUM": "FMCG",
    # Metal & Mining
    "HINDALCO": "METAL", "JSWSTEEL": "METAL", "TATASTEEL": "METAL",
    "COALINDIA": "METAL",
    # Energy & Oil
    "ADANIENT": "ENERGY", "BPCL": "ENERGY", "NTPC": "ENERGY",
    "ONGC": "ENERGY", "POWERGRID": "ENERGY", "RELIANCE": "ENERGY",
    # Telecom
    "BHARTIARTL": "TELECOM",
    # Infrastructure & Construction
    "ADANIPORTS": "INFRA", "LT": "INFRA", "GRASIM": "INFRA",
    "ULTRACEMCO": "INFRA",
    # Consumer & Retail
    "ASIANPAINT": "CONSUMER", "TITAN": "CONSUMER",
    # Defence
    "BEL": "DEFENCE",
    # Hospitality / Food
    "ETERNAL": "CONSUMER",
}


# ═══════════════════════════════════════════════════════════════
# F&O LOT SIZES (updated periodically by NSE)
# ═══════════════════════════════════════════════════════════════
# NOTE: Lot sizes change quarterly. This should be fetched from
# NSE at startup in production. These are reference defaults.

FNO_LOT_SIZES: Dict[str, int] = {
    "NIFTY": 25,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "MIDCPNIFTY": 50,
    "RELIANCE": 250,
    "HDFCBANK": 550,
    "ICICIBANK": 1375,
    "INFY": 300,
    "TCS": 150,
    "SBIN": 750,
    "BAJFINANCE": 125,
    "TATAMOTORS": 1400,
    "AXISBANK": 600,
    "KOTAKBANK": 400,
    "ITC": 1600,
    "HINDUNILVR": 300,
    "LT": 150,
    "MARUTI": 50,
    "SUNPHARMA": 350,
    "BHARTIARTL": 475,
    "WIPRO": 1500,
    "HCLTECH": 350,
    "TATASTEEL": 1100,
    "M&M": 350,
    "NTPC": 1800,
    "HINDALCO": 1075,
    "ONGC": 1925,
    "COALINDIA": 1200,
    "ASIANPAINT": 200,
    "TITAN": 175,
    "ADANIENT": 250,
    "ULTRACEMCO": 50,
    "BAJAJ-AUTO": 75,
    "DRREDDY": 75,
    "CIPLA": 325,
    "TECHM": 300,
    "EICHERMOT": 100,
    "JSWSTEEL": 675,
    "POWERGRID": 2700,
    "BPCL": 1050,
    "GRASIM": 275,
    "BRITANNIA": 100,
    "NESTLEIND": 50,
    "APOLLOHOSP": 125,
    "TATACONSUM": 450,
    "HEROMOTOCO": 100,
    "ADANIPORTS": 500,
    "INDUSINDBK": 500,
}


# ═══════════════════════════════════════════════════════════════
# TRANSACTION COST CONSTANTS (SEBI schedule)
# ═══════════════════════════════════════════════════════════════

class TransactionCosts:
    """Indian market transaction cost components."""

    # Brokerage (Zerodha Kite rates)
    BROKERAGE_DELIVERY_PCT = 0.0          # Zerodha: zero delivery brokerage
    BROKERAGE_INTRADAY_PCT = 0.0003       # 0.03% or ₹20 per order, whichever lower
    BROKERAGE_FNO_FLAT = 20.0             # ₹20 per executed order

    # Securities Transaction Tax (STT)
    STT_DELIVERY_BUY_PCT = 0.001          # 0.1% on buy side
    STT_DELIVERY_SELL_PCT = 0.001         # 0.1% on sell side
    STT_INTRADAY_SELL_PCT = 0.00025       # 0.025% on sell side only
    STT_FO_SELL_PCT = 0.000125            # 0.0125% on sell side of options premium
    STT_FUTURES_SELL_PCT = 0.000125       # 0.0125% on sell side

    # Exchange Transaction Charges
    NSE_TXN_CHARGE_PCT = 0.0000297        # NSE equity
    BSE_TXN_CHARGE_PCT = 0.0000297        # BSE equity
    NSE_FO_TXN_CHARGE_PCT = 0.0000495     # NSE F&O

    # SEBI Charges
    SEBI_TURNOVER_CHARGE_PCT = 0.000001   # ₹10 per crore

    # Stamp Duty (buy side only)
    STAMP_DUTY_DELIVERY_PCT = 0.00015     # 0.015%
    STAMP_DUTY_INTRADAY_PCT = 0.00003     # 0.003%
    STAMP_DUTY_FO_PCT = 0.00003           # 0.003%

    # GST on brokerage + exchange charges
    GST_PCT = 0.18                        # 18% GST


# ═══════════════════════════════════════════════════════════════
# INDICATOR DEFAULT PARAMETERS
# ═══════════════════════════════════════════════════════════════

class IndicatorDefaults:
    """Default parameters for all technical indicators."""

    # Trend
    EMA_FAST = 21
    EMA_MEDIUM = 50
    EMA_SLOW = 200
    ADX_PERIOD = 14
    ADX_TREND_THRESHOLD = 20
    ADX_STRONG_TREND = 25
    SUPERTREND_PERIOD = 7
    SUPERTREND_MULTIPLIER = 3.0
    ICHIMOKU_TENKAN = 9
    ICHIMOKU_KIJUN = 26
    ICHIMOKU_SENKOU = 52

    # Momentum
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    CONNORS_RSI = (3, 2, 100)
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    STOCH_RSI_PERIOD = 14
    STOCH_RSI_K = 3
    STOCH_RSI_D = 3
    ROC_SHORT = 10
    ROC_MEDIUM = 21
    WILLIAMS_R_PERIOD = 14

    # Volatility
    BB_PERIOD = 20
    BB_STD = 2.0
    BB_SQUEEZE_PERCENTILE = 20
    ATR_PERIOD = 14
    KELTNER_PERIOD = 20
    KELTNER_ATR_MULT = 2.0
    HV_WINDOWS = (10, 20, 30)

    # Volume
    VWAP_STD_BANDS = (1.0, 2.0)
    OBV_PERIOD = 20
    CMF_PERIOD = 20
    VOLUME_SPIKE_MULT = 2.0
    VOLUME_CONFIRM_MULT = 1.5

    # Price Action
    FIBONACCI_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786)
    FIBONACCI_EXTENSIONS = (1.0, 1.272, 1.618, 2.0, 2.618)
    PIVOT_LOOKBACK = 5


# ═══════════════════════════════════════════════════════════════
# SYSTEM CONSTANTS
# ═══════════════════════════════════════════════════════════════

# Timezone
MARKET_TIMEZONE = "Asia/Kolkata"

# Data refresh intervals (seconds)
TICK_DATA_INTERVAL = 1
INDICATOR_REFRESH_INTERVAL = 60
REGIME_CHECK_INTERVAL = 900       # 15 minutes
MODEL_UPDATE_INTERVAL = 86400     # Daily (after market close)

# Signal ID format
SIGNAL_ID_PREFIX = "APEX"
SIGNAL_ID_FORMAT = "{prefix}-{date}-{time}-{seq:03d}"

# Performance metric targets
TARGET_CAGR = 0.25
TARGET_SHARPE = 1.8
TARGET_SORTINO = 2.5
TARGET_MAX_DRAWDOWN = 0.12
TARGET_WIN_RATE_MOMENTUM = 0.48
TARGET_WIN_RATE_MEAN_REV = 0.60
TARGET_PROFIT_FACTOR = 1.9
TARGET_CALMAR = 2.0
TARGET_ALPHA_VS_NIFTY = 0.08
