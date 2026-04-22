<div align="center">

# APEX INDIA
### Autonomous Quantitative Trading Intelligence
**Zero-Cost Market Data &middot; Advanced ML Sentiment &middot; Precision Execution**

[![Version](https://img.shields.io/badge/version-3.1.0-blue?style=for-the-badge)](https://github.com/Vshn2k5/TRADE)
[![Python](https://img.shields.io/badge/python-3.11+-green?style=for-the-badge&logo=python&logoColor=white)](https://github.com/Vshn2k5/TRADE)
[![Status](https://img.shields.io/badge/status-Production_Ready-emerald?style=for-the-badge)](https://github.com/Vshn2k5/TRADE)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=for-the-badge)](https://github.com/Vshn2k5/TRADE)

*"The market rewards patience, punishes greed, and destroys those without a plan."*

---

![APEX INDIA Dashboard](docs/images/dashboard_preview.png)

</div>

## 🌌 System Identity
**APEX INDIA** is an elite, fully autonomous quantitative trading engine purpose-built for the **Indian Financial Markets** (NSE/BSE/MCX). Designed for high-reliability execution with zero recurring data costs, it bridges the gap between retail trading and institutional-grade algorithmic intelligence.

### 🎯 Core Objectives
- **Alpha Generation**: 10 distinct strategies optimized for different market regimes.
- **Risk Preservation**: 4-layer stop-loss architecture and hard capital constraints.
- **Zero-Cost Edge**: Uses `yfinance` and NSE-direct scapers for premium data without the premium price.
- **Glassmorphic UX**: A stunning Command Center dashboard for real-time monitoring and remote control.

---

## ⚡ Key Features

| Category | Highlights |
| :--- | :--- |
| **🧠 Intelligence** | 10+ Strategies, Market Regime Detection, Sentiment Analysis (FinBERT), ML Price Classifiers. |
| **🛡️ Risk** | 1% Max Risk/Trade, Daily/Weekly Circuit Breakers, 15% Drawdown Hard Halt, ATR-based Stop Sizing. |
| **🚀 Execution** | Zerodha Kite / Upstox Integration, Paper Trading Simulation, WebSocket Low-Latency Feeds. |
| **🖥️ Dashboard** | FastAPI + Glassmorphism Web Interface, Real-time P&L, Signal Lab, System Status Central. |

---

## 🏗️ Technical Architecture
APEX INDIA operates on a decoupled **7-Layer Infrastructure**:

1.  **Data Layer**: Multi-source ingestion (WebSockets, yfinance, NSE Scraping).
2.  **Intelligence Layer**: Feature engineering for 130+ technical indicators.
3.  **Regime Engine**: HMM-based classification of market states (Trending, Reverting, Volatile).
4.  **Strategy Lab**: Parallel execution of 10 proprietary trading models.
5.  **Decision Gate**: Composite scoring logic (Confidence 0-100) before any trade execution.
6.  **Risk Shield**: Real-time position sizing and stop-loss management.
7.  **Command Center**: Premium frontend for system oversight and manual override.

---

## 🧪 Strategy Lab: The 10 Proprietary Models
The system automatically toggles between these strategies based on the identified **Market Regime**.

| # | Strategy | Primary Regime | Logic |
| :-- | :-- | :-- | :-- |
| 01 | **Trend Rider** | Trending | EMA Ribbon Alignment (21/50/200) + ADX Trend Strength. |
| 02 | **Vol Breakout** | Breakout | BB Squeeze detection + sudden Volume/Volatility expansion. |
| 03 | **VWAP Reversion** | Reverting | Mean reversion from VWAP ±2.5σ with RSI exhaustion. |
| 04 | **ORB (15m)** | Opening | First 15-min range high/low breakout with volume confirmation. |
| 05 | **Earnings Drift** | Post-Event | EPS Surprise (>15%) followed by multi-day drift patterns. |
| 06 | **Sector Rotation** | Trending | Capital allocation into top 3 sectors with relative strength. |
| 07 | **Theta Harvest** | Low Vol | Delta-neutral Iron Condors/Strangles for time decay. |
| 08 | **SMC Reversal** | Distribution | Smart Money footprints: BOS, CHoCH, and Order Blocks. |
| 09 | **Gap Trade** | Trending | Gap-and-go patterns validated against pre-market global cues. |
| 10 | **Swing Positional** | Any | Institutional accumulation patterns (Cup & Handle, Bull Flags). |

---

## 🕹️ Command Center (Dashboard)
The **APEX INDIA Dashboard** is a high-performance web interface designed with **Glassmorphism** aesthetics.
- **Live Status**: Real-time IST clock, Market status (Open/Closed), and System Mode (Paper/Real).
- **Metric Grid**: Instant feedback on Equity, Day P&L, Active Trades, and Win Rate.
- **Equity Curve**: Dynamic Chart.js visualization of your account growth.
- **Signal Feed**: Direct stream of incoming alpha alerts before execution.
- **Safety Switch**: One-click **HALT TRADING** for emergency manual intervention.

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.11+**
- **Zerodha Kite Connect** or **Upstox API** credentials.
- Recommended RAM: **8GB+** for ML model inference.

### Quick Start
```bash
# 1. Clone the repository
git clone https://github.com/Vshn2k5/TRADE.git
cd TRADE

# 2. Setup environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# [!] Edit .env with your API keys and configuration

# 5. Initialize & Check
python main.py --init-db
python main.py --status
```

---

## ⚖️ Governance & Risk
APEX INDIA is governed by **Iron-Clad Constraints** to ensure capital survival:
- **Max Drawdown**: 15% (System completely halts until manual audit).
- **Daily Loss Limit**: 2.5% (Trading ceases for the remainder of the day).
- **Position Limit**: Max 10 concurrent intraday exposures.
- **Sector Limit**: No more than 25% exposure in any single sector.

---

<div align="center">

<div align="center">

# APEX INDIA
### Autonomous Quantitative Trading Intelligence
**Zero-Cost Market Data &middot; Advanced ML Sentiment &middot; Precision Execution**

[![Version](https://img.shields.io/badge/version-3.1.0-blue?style=for-the-badge)](https://github.com/Vshn2k5/TRADE)
[![Python](https://img.shields.io/badge/python-3.11+-green?style=for-the-badge&logo=python&logoColor=white)](https://github.com/Vshn2k5/TRADE)
[![Status](https://img.shields.io/badge/status-Production_Ready-emerald?style=for-the-badge)](https://github.com/Vshn2k5/TRADE)
[![License](https://img.shields.io/badge/license-Proprietary-red?style=for-the-badge)](https://github.com/Vshn2k5/TRADE)

*"The market rewards patience, punishes greed, and destroys those without a plan."*

---

![APEX INDIA Dashboard](docs/images/dashboard_preview.png)


## Table of Contents

- [System Identity](#system-identity)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
- [Usage](#usage)
  - [CLI Commands](#cli-commands)
  - [Operating Modes](#operating-modes)
- [Core Modules](#core-modules)
  - [Data Acquisition Layer](#1-data-acquisition-layer)
  - [Market Analysis Engine](#2-market-analysis-engine)
  - [Strategy Library](#3-strategy-library)
  - [Risk Management](#4-risk-management)
  - [Machine Learning Layer](#5-machine-learning--adaptive-intelligence)
  - [Execution Engine](#6-execution-engine)
  - [Dashboard & Monitoring](#7-dashboard--monitoring)
  - [Alerts & Notifications](#8-alerts--notifications)
- [Trading Strategies](#trading-strategies)
- [Risk Management Framework](#risk-management-framework)
- [Signal Output Format](#signal-output-format)
- [Performance Targets](#performance-targets)
- [Backtesting Protocol](#backtesting-protocol)
- [Deployment](#deployment)
- [Iron-Clad Constraints](#iron-clad-constraints--ethical-rules)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)

---

## System Identity

**APEX INDIA** is an elite, fully autonomous, production-grade quantitative trading intelligence system purpose-built for **Indian financial markets**. It is not a signal generator. It is not an assistant. It is a complete, self-contained trading organism that perceives markets, reasons about opportunities, manages capital, executes trades, and learns continuously.

Its prime directive is **consistent, risk-adjusted, long-term capital compounding** across:

| Market | Coverage |
|--------|----------|
| **NSE / BSE Equities** | Nifty 50, Nifty 200, Mid-Cap 150 |
| **Index Derivatives** | Nifty, Bank Nifty, Fin Nifty futures & options |
| **Stock F&O** | All F&O-permitted equities |
| **Currency** | NSE FX pairs (USD/INR, EUR/INR, GBP/INR) |
| **Commodities** | MCX Gold, Silver, Crude Oil |

> **APEX INDIA never trades on hope. It trades on edge.**

---

## Key Features

- **Fully Autonomous Operation** -- From data ingestion to order execution, the system operates independently during market hours with zero manual intervention required.
- **Multi-Strategy Engine** -- 10 distinct strategies, automatically selected based on real-time market regime detection.
- **Multi-Timeframe Analysis** -- Hierarchical approach: weekly/daily for trend, 15min/5min for entries, tick data for execution.
- **Composite Signal Scoring** -- Every trade scored 0-100 across technical (40%), fundamental (25%), derivatives (25%), and sentiment (10%) dimensions.
- **Zero-Compromise Risk Management** -- 1% max risk per trade, daily/weekly/monthly circuit breakers, 15% max drawdown hard halt.
- **5 ML Models** -- LightGBM/XGBoost ensemble, GARCH+LSTM volatility predictor, HMM regime classifier, DQN entry timing, FinBERT sentiment.
- **Paper Trading Mode** -- Full simulation with live data before any real capital is deployed.
- **Real-Time Dashboard** -- Streamlit-powered live P&L, positions, signals, risk exposure, and trade analytics.
- **Multi-Channel Alerts** -- Telegram (primary), Email (reports), SMS (emergency circuit breakers).
- **Broker Integration** -- Zerodha Kite Connect (primary) and Upstox (secondary), with order lifecycle management.
- **Complete Audit Trail** -- Every signal, every trade, every decision logged with reasoning for 365+ days.

---

## System Architecture

```
+-------------------------------------------------------------------+
|                        APEX INDIA v3.0                             |
+-------------------------------------------------------------------+
|                                                                   |
|  +------------------+    +------------------+    +-------------+  |
|  |  DATA LAYER      |    |  INTELLIGENCE    |    |  DECISION   |  |
|  |                  |    |  LAYER           |    |  LAYER      |  |
|  |  - WebSocket     |--->|  - Tech. Anal.   |--->|  - Strategy |  |
|  |  - Historical    |    |  - Fundamentals  |    |    Selector |  |
|  |  - NSE Feeds     |    |  - Sentiment NLP |    |  - Trade    |  |
|  |  - News RSS      |    |  - Derivatives   |    |    Gate     |  |
|  |  - Macro Data    |    |  - ML Models     |    |  - Position |  |
|  |                  |    |  - Composite     |    |    Sizer    |  |
|  |                  |    |    Scorer        |    |             |  |
|  +------------------+    +------------------+    +------+------+  |
|                                                         |         |
|  +------------------+    +------------------+    +------v------+  |
|  |  MONITORING      |    |  RISK LAYER      |    |  EXECUTION  |  |
|  |                  |    |                  |    |  LAYER      |  |
|  |  - Streamlit     |<---|  - Stop-Loss Mgr |<---|  - Order    |  |
|  |    Dashboard     |    |  - Circuit Break |    |    Manager  |  |
|  |  - Telegram Bot  |    |  - Portfolio Risk|    |  - Broker   |  |
|  |  - Daily Reports |    |  - Correlation   |    |    API      |  |
|  |  - Grafana       |    |    Monitor       |    |  - Position |  |
|  |                  |    |                  |    |    Monitor  |  |
|  +------------------+    +------------------+    +-------------+  |
|                                                                   |
|  +-------------------------------------------------------------+  |
|  |  PERSISTENCE: PostgreSQL | Redis | InfluxDB | SQLite (dev)  |  |
|  +-------------------------------------------------------------+  |
+-------------------------------------------------------------------+
```

---

## Technology Stack

### Core

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.11+ | Primary development language |
| **Config** | YAML + dotenv | Configuration management with env var interpolation |
| **Logging** | Loguru | Structured logging with 5 separate sinks |
| **Scheduling** | APScheduler | Cron-like task orchestration |

### Data & Storage

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Primary DB** | PostgreSQL (prod) / SQLite (dev) | OHLCV data, trade logs, strategy performance |
| **Cache** | Redis | Real-time tick data, position state, signal queue |
| **Time-Series** | InfluxDB | High-frequency tick data, system metrics |
| **ORM** | SQLAlchemy 2.0 | Database abstraction with declarative mapping |

### Analysis & Indicators

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Data Processing** | pandas, numpy, scipy | Numerical computing and data manipulation |
| **Technical Indicators** | pandas-ta | 130+ technical indicators |
| **Statistics** | statsmodels | GARCH models, regime detection |

### Machine Learning

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Classical ML** | scikit-learn | Feature preprocessing, evaluation |
| **Gradient Boosting** | LightGBM, XGBoost | Price direction classification |
| **Deep Learning** | PyTorch | LSTM volatility predictor, Transformer models |
| **Reinforcement Learning** | Stable-Baselines3 | DQN entry timing optimization |
| **NLP** | Transformers (FinBERT) | News & social sentiment analysis |
| **Hyperparameter Tuning** | Optuna | Bayesian optimization |

### Broker & Execution

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Primary Broker** | Zerodha Kite Connect | Order execution, WebSocket data feeds |
| **Secondary Broker** | Upstox Python SDK | Backup broker integration |
| **Async I/O** | asyncio, aiohttp, websockets | Non-blocking order management |

### Dashboard & Alerts

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Dashboard** | Streamlit | Real-time trading dashboard |
| **Charts** | Plotly | Interactive visualizations |
| **Alerts** | python-telegram-bot | Trade signals & P&L updates |
| **Monitoring** | Grafana + Prometheus | System health monitoring |

### Backtesting

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Vectorized Backtest** | VectorBT | Fast historical strategy validation |
| **Walk-Forward** | Custom engine | Rolling out-of-sample testing |
| **Monte Carlo** | Custom simulator | 10,000-run confidence analysis |

---

## Project Structure

```
TRADE/
|
|-- main.py                              # System entry point (CLI)
|-- scheduler.py                         # Market calendar + task orchestrator
|-- config.yaml                          # Master configuration (300+ params)
|-- requirements.txt                     # Pinned Python dependencies
|-- .env.example                         # Environment variable template
|-- .gitignore                           # Version control exclusions
|-- README.md                            # This file
|
|-- apex_india/                          # Core Python package
|   |-- __init__.py                      # Package metadata (v3.0.0)
|   |
|   |-- data/                            # DATA LAYER
|   |   |-- feeds/                       # Real-time data ingestion
|   |   |   |-- websocket_handler.py     #   Zerodha Kite WebSocket client
|   |   |   |-- historical_data.py       #   OHLCV backfill from Kite API
|   |   |   |-- nse_data.py              #   NSE scraper (OI, FII/DII, delivery)
|   |   |   |-- macro_data.py            #   RBI, global macro, economic calendar
|   |   |   +-- news_feed.py             #   RSS aggregator (ET, MC, BS, BQ)
|   |   |
|   |   |-- processors/                  # Data transformation
|   |   |   |-- data_cleaner.py          #   Gap fill, anomaly detection, corp actions
|   |   |   +-- feature_engineer.py      #   VWAP, volume profile, breadth, features
|   |   |
|   |   |-- storage/                     # Database layer
|   |   |   |-- models.py               #   7 SQLAlchemy ORM models
|   |   |   +-- database.py             #   Connection manager (PG + SQLite + Redis)
|   |   |
|   |   +-- indicators/                  # Technical indicator library
|   |       |-- trend.py                 #   EMA, ADX, Ichimoku, Supertrend
|   |       |-- momentum.py             #   RSI, MACD, Stochastic RSI, ROC
|   |       |-- volatility.py           #   Bollinger, ATR, Keltner, VIX
|   |       |-- volume.py               #   VWAP, OBV, CMF, Volume Profile
|   |       |-- price_action.py         #   Patterns, S/R, Fibonacci, SMC
|   |       |-- derivatives.py          #   Options chain, OI, PCR, Greeks
|   |       |-- sector.py               #   Sector rotation, RS analysis
|   |       +-- composite_scorer.py     #   Unified 0-100 signal scoring
|   |
|   |-- strategies/                      # STRATEGY LIBRARY (10 strategies)
|   |   |-- base_strategy.py             #   Abstract base class
|   |   |-- strategy_selector.py         #   Regime-based auto-selection
|   |   |-- timing.py                    #   Entry timing intelligence
|   |   |-- momentum/                    #   Trend-following strategies
|   |   |   |-- trend_rider.py           #     Strategy 01: Trend Momentum
|   |   |   |-- earnings.py              #     Strategy 05: Earnings Momentum
|   |   |   |-- sector_rotation.py       #     Strategy 06: Sector Rotation
|   |   |   |-- gap_trade.py             #     Strategy 09: Gap Trading
|   |   |   +-- swing_positional.py      #     Strategy 10: Swing (3-15 days)
|   |   |-- mean_reversion/
|   |   |   +-- vwap_mr.py              #     Strategy 03: VWAP Mean Reversion
|   |   |-- breakout/
|   |   |   |-- vol_breakout.py          #     Strategy 02: Volatility Breakout
|   |   |   +-- orb.py                   #     Strategy 04: Opening Range Breakout
|   |   |-- options/
|   |   |   +-- theta_harvest.py         #     Strategy 07: Theta Harvesting
|   |   +-- smc/
|   |       +-- smc_reversal.py          #     Strategy 08: Smart Money Reversal
|   |
|   |-- models/                          # ML & AI MODELS
|   |   |-- regime/
|   |   |   |-- regime_detector.py       #   Rule-based regime classification
|   |   |   +-- hmm_regime.py            #   HMM + Random Forest regime model
|   |   |-- direction/
|   |   |   +-- price_classifier.py      #   LightGBM/XGBoost ensemble
|   |   |-- volatility/
|   |   |   +-- vol_predictor.py         #   GARCH(1,1) + LSTM hybrid
|   |   |-- sentiment/
|   |   |   +-- finbert_india.py         #   FinBERT fine-tuned for India
|   |   |-- timing/
|   |   |   +-- dqn_entry.py             #   Deep Q-Network entry optimizer
|   |   +-- adaptive_engine.py           #   Continuous learning loop
|   |
|   |-- risk/                            # RISK MANAGEMENT
|   |   |-- position_sizer.py            #   ATR-based volatility sizing
|   |   |-- stop_loss_manager.py         #   4-layer stop architecture
|   |   |-- circuit_breaker.py           #   Daily/weekly/monthly loss limits
|   |   +-- portfolio_risk.py            #   Correlation, beta, hedging
|   |
|   |-- execution/                       # ORDER EXECUTION
|   |   |-- order_manager.py             #   Full order lifecycle
|   |   |-- broker_zerodha.py            #   Kite Connect API wrapper
|   |   |-- broker_upstox.py             #   Upstox API wrapper
|   |   |-- position_monitor.py          #   Real-time position tracking
|   |   |-- paper_trader.py              #   Simulated execution engine
|   |   +-- signal_formatter.py          #   Formatted signal output
|   |
|   |-- backtesting/                     # BACKTESTING ENGINE
|   |   |-- engine.py                    #   Core backtest loop
|   |   |-- walk_forward.py              #   Walk-forward validation
|   |   |-- monte_carlo.py              #   10,000-run Monte Carlo sim
|   |   +-- metrics.py                   #   Performance metrics calculator
|   |
|   |-- dashboard/                       # MONITORING DASHBOARD
|   |   |-- app.py                       #   Streamlit main application
|   |   |-- charts.py                    #   Plotly chart builders
|   |   +-- report_generator.py          #   Daily PDF reports
|   |
|   |-- alerts/                          # NOTIFICATION SYSTEM
|   |   |-- telegram_bot.py              #   Telegram bot integration
|   |   +-- notification_manager.py      #   Multi-channel dispatcher
|   |
|   +-- utils/                           # UTILITIES
|       |-- constants.py                 #   Market constants, Nifty lists, enums
|       |-- config.py                    #   YAML config loader with validation
|       +-- logger.py                    #   Structured 5-sink logging system
|
|-- data/                                # Local data storage (gitignored)
|   +-- apex_india.db                    #   SQLite database (dev mode)
|
|-- logs/                                # Log files (gitignored)
|   |-- system_YYYY-MM-DD.log           #   All INFO+ messages
|   |-- errors_YYYY-MM-DD.log           #   ERROR+ with full traceback
|   |-- trading_YYYY-MM-DD.log          #   Trade audit trail (365-day retention)
|   +-- debug_YYYY-MM-DD.log            #   DEBUG+ (7-day retention)
|
+-- tests/                               # Test suite
    |-- test_indicators/
    |-- test_strategies/
    |-- test_risk/
    |-- test_execution/
    +-- test_backtesting/
```

---

## Getting Started

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Python** | 3.11 | 3.11+ |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 10 GB | 50 GB (for historical data) |
| **OS** | Windows 10 / Ubuntu 20.04 | Ubuntu 22.04 LTS |
| **Network** | Stable broadband | Low-latency connection |
| **GPU** | Not required | CUDA-capable (for ML training) |

**External Services (Production):**

| Service | Purpose | Required? |
|---------|---------|-----------|
| Zerodha Kite Connect | Broker API (data + execution) | Yes |
| PostgreSQL 15+ | Primary database | Recommended (SQLite fallback available) |
| Redis 7+ | Real-time caching | Optional (in-memory fallback) |
| InfluxDB 2.x | Tick-level time-series | Optional |
| Telegram Bot | Trade alerts | Recommended |

### Installation

**1. Clone the repository:**

```bash
git clone https://github.com/your-org/apex-india.git
cd apex-india
```

**2. Create a virtual environment:**

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies:**

```bash
# Core dependencies only (minimal setup for development)
pip install PyYAML loguru sqlalchemy python-dotenv pytz colorama tabulate click APScheduler

# Full installation (all features including ML)
pip install -r requirements.txt
```

**4. Configure environment variables:**

```bash
# Copy the template
cp .env.example .env

# Edit .env with your actual API keys
# IMPORTANT: Never commit .env to version control
```

**5. Initialize the database:**

```bash
python main.py --init-db
```

**6. Verify the installation:**

```bash
python main.py --status
```

You should see output like:

```
+===============================================================+
|                                                               |
|          A P E X   I N D I A   v 3 . 0                       |
|                                                               |
|        Autonomous Quantitative Trading Intelligence           |
|        BSE Sensex - Nifty 50 - F&O - MCX                     |
|                                                               |
+===============================================================+

============================================================
  SYSTEM CONFIGURATION
============================================================
  Config File      : config.yaml
  System Mode      : PAPER
  Primary Broker   : zerodha
  Config Valid     : PASSED

------------------------------------------------------------
  MARKET STATUS
------------------------------------------------------------
  Current Time     : 2026-04-11 12:08:22 IST
  Trading Day      : Yes
  Market Open      : Yes
  Session          : MORNING_TREND

------------------------------------------------------------
  DATABASE STATUS
------------------------------------------------------------
  sql_database      : connected
  sql_backend       : sqlite
  redis             : disabled
  influxdb          : disabled
============================================================
```

### Configuration

All system parameters are centralized in **`config.yaml`** (300+ parameters across 13 sections):

| Section | Parameters | Description |
|---------|-----------|-------------|
| `system` | 4 | Name, version, mode (paper/live/backtest), log level |
| `broker` | 12 | Zerodha & Upstox API credentials, retry config |
| `database` | 15 | PostgreSQL, Redis, InfluxDB connection settings |
| `market` | 20 | Trading hours, entry windows, observation periods |
| `universe` | 10 | Stock screening filters (market cap, volume, RS) |
| `risk` | 25 | Position sizing, stop-loss layers, circuit breakers |
| `scoring` | 30 | Signal weight distribution across all 4 dimensions |
| `strategies` | 80+ | Per-strategy parameters (EMA periods, thresholds) |
| `models` | 20 | ML model types, training windows, thresholds |
| `backtesting` | 20 | Cost assumptions, performance thresholds |
| `dashboard` | 6 | Host, port, refresh interval, theme |
| `alerts` | 15 | Telegram, email, SMS configuration |
| `scheduler` | 8 | Task intervals and timing |

**Key configuration values:**

```yaml
system:
  mode: "paper"          # paper | live | backtest

risk:
  position:
    max_risk_per_trade_pct: 0.01    # 1% of portfolio
    max_single_stock_exposure: 0.08  # 8% max in one stock
    max_sector_exposure: 0.25        # 25% max per sector
    min_risk_reward: 2.0             # 1:2 minimum RR
    cash_buffer_min: 0.15            # Always keep 15% cash
  circuit_breakers:
    daily_loss_limit_pct: 0.025      # 2.5% -> halt trading
    max_drawdown_pct: 0.15           # 15% -> complete halt

scoring:
  trade_gates:
    min_confidence_standard: 65      # Minimum score for trades
    min_confidence_large: 75         # Minimum for large positions
```

### Environment Variables

Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

**Required variables:**

| Variable | Description | How to Obtain |
|----------|-------------|---------------|
| `ZERODHA_API_KEY` | Kite Connect API key | [Kite Developer Portal](https://developers.kite.trade/) |
| `ZERODHA_API_SECRET` | Kite Connect API secret | Same as above |
| `DB_USER` | PostgreSQL username | Your database setup |
| `DB_PASSWORD` | PostgreSQL password | Your database setup |

**Optional variables:**

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `REDIS_PASSWORD` | Redis authentication password |
| `INFLUXDB_TOKEN` | InfluxDB API token |

---

## Usage

### CLI Commands

```bash
# Check full system status (config, market, database, dependencies)
python main.py --status

# Start in paper trading mode (simulated execution)
python main.py --mode paper

# Start in live trading mode (REAL money - requires confirmation)
python main.py --mode live

# Run backtesting engine
python main.py --mode backtest

# Initialize / reset database tables
python main.py --init-db

# Validate configuration file
python main.py --validate-config

# Use a custom config file
python main.py --status --config /path/to/custom_config.yaml
```

### Operating Modes

| Mode | Description | Risk |
|------|-------------|------|
| **`paper`** | Full system with simulated execution. Uses live market data but no real orders. | Zero |
| **`backtest`** | Historical strategy validation with realistic cost assumptions. | Zero |
| **`live`** | Real order execution via broker APIs. Requires typing `CONFIRM LIVE`. | Real capital |

> **Safety Feature:** Starting in `live` mode requires you to type `CONFIRM LIVE` at the prompt. This prevents accidental real-money trading.

---

## Core Modules

### 1. Data Acquisition Layer

The system ingests, validates, and synchronizes data from multiple sources with sub-100ms latency targets:

**Real-Time Market Feeds:**
- NSE/BSE tick data via Zerodha Kite WebSocket API
- Full OHLCV across 9 timeframes (1min to weekly)
- Level-2 order book (bid/ask depth up to 20 levels)
- FII/DII daily activity, futures OI, option chain data
- India VIX, delivery percentage, block/bulk deals

**Derived Data Streams (computed in real-time):**
- Tick volume profile with POC, VAH, VAL
- Market microstructure (bid-ask spread, order flow imbalance)
- Rolling VWAP with standard deviation bands
- Cumulative delta (buying vs selling pressure)
- Market breadth (advance/decline, % above 50/200 DMA)

**Macroeconomic Intelligence:**
- RBI policy decisions, CPI, GDP, PMI, GST collections
- Global feeds: US Fed, DXY, US 10Y yield, Brent crude, gold
- Corporate fundamentals: earnings, margins, institutional flow
- Monsoon progress (IMD), trade deficit, forex reserves

**Sentiment & News Engine:**
- RSS feeds from Economic Times, Moneycontrol, Business Standard, BloombergQuint
- NLP pipeline: NER, event classification, sentiment scoring (-1.0 to +1.0)
- Social sentiment via FinBERT (India-fine-tuned)
- Analyst consensus aggregation and insider transaction tracking

### 2. Market Analysis Engine

**Technical Analysis (Multi-Timeframe Cascade):**

| Category | Indicators |
|----------|-----------|
| **Trend** | 200/50/21 EMA, ADX(14), Ichimoku Cloud, Supertrend(7,3), Heikin-Ashi |
| **Momentum** | RSI(14), Connors RSI, MACD(12,26,9), Stochastic RSI, ROC, Williams %R |
| **Volatility** | Bollinger Bands(20,2), ATR(14), Keltner Channels, India VIX, BB Squeeze |
| **Volume** | VWAP+bands, OBV, A/D Line, CMF(20), Volume Profile, Delivery Ratio |
| **Price Action** | Swing pivots, S/R levels, Fibonacci, 15+ candlestick patterns, 10+ chart patterns |
| **Smart Money** | Break of Structure, Change of Character, Order Blocks, FVG, Liquidity Sweeps |

**Derivatives Intelligence:**
- Option chain: PCR, max pain, OI buildup classification, IV Rank/Percentile
- Gamma Exposure (GEX), unusual options activity, put/call skew
- Futures basis, rollover data, FII positioning

**Sector & Relative Strength:**
- 12 sector index tracking with rotation model
- RS ranking vs Nifty 50 (only trade RS > 1.0 stocks)
- Inter-market correlation analysis
- Beta-adjusted sector exposure management

### 3. Strategy Library

See [Trading Strategies](#trading-strategies) section below for full details on all 10 strategies.

### 4. Risk Management

See [Risk Management Framework](#risk-management-framework) section below for the complete zero-compromise framework.

### 5. Machine Learning & Adaptive Intelligence

| Model | Architecture | Purpose | Update Frequency |
|-------|-------------|---------|-----------------|
| **Price Classifier** | LightGBM + XGBoost ensemble | 5-day return direction prediction | Weekly retrain |
| **Volatility Predictor** | GARCH(1,1) + LSTM hybrid | 5-day ATR forecast for position sizing | Daily |
| **Regime Classifier** | Hidden Markov Model + Random Forest | 4-state market regime detection | Daily (HMM every 15min) |
| **Entry Timing** | Deep Q-Network (RL) | Optimal entry timing optimization | Weekly |
| **Sentiment Analyzer** | FinBERT (India-fine-tuned) | News impact: direction + magnitude + duration | Continuous |

**Continuous Learning Loop:**
- **Daily:** Model performance evaluation on today's predictions
- **Weekly:** Strategy review -- live Sharpe vs backtest Sharpe comparison
- **Real-time (15min):** HMM regime probability updates
- **Monthly:** Full performance attribution and factor decomposition

### 6. Execution Engine

- **Order Types:** MARKET, LIMIT, SL (Stop-Loss Limit), SL-M (Stop-Loss Market)
- **Products:** CNC (delivery), MIS (intraday), NRML (F&O overnight)
- **Bracket Orders:** Automated SL and target placement
- **Smart Execution:** TWAP/VWAP for orders > Rs 5 lakh to minimize market impact
- **Retry Logic:** 3 attempts with exponential backoff
- **Position Monitoring:** Every 60 seconds -- trailing stops, partial profits, early exit detection

### 7. Dashboard & Monitoring

**Streamlit Dashboard Pages:**

| Page | Content |
|------|---------|
| **Live Trading** | Open positions with real-time mark-to-market, today's signals, P&L waterfall |
| **Portfolio** | Sector exposure, beta, correlation matrix, equity curve with drawdown overlay |
| **Signals** | Signal heatmap across watchlist, historical signal accuracy by strategy |
| **Backtesting** | Strategy comparison, walk-forward results, Monte Carlo distributions |
| **Settings** | Configuration editor, strategy enable/disable, risk parameter adjustment |

### 8. Alerts & Notifications

| Channel | Events | Priority |
|---------|--------|----------|
| **Telegram** | Trade signals, execution confirmations, hourly P&L, EOD summary | Primary |
| **Email** | Daily performance report, weekly strategy review | Reports |
| **SMS (Twilio)** | Circuit breaker alerts, emergency halts | Emergency |

**Telegram Bot Commands:**

```
/status     - Current system status
/positions  - Open positions with P&L
/pnl        - Today's profit/loss summary
/halt       - IMMEDIATELY stop all trading (human override)
/resume     - Resume trading after manual halt
```

---

## Trading Strategies

### Strategy Selection Flow

```
Market Regime Detection (every 15 min)
         |
         v
+--------------------+
| Regime Classified: |----> Select matching strategies
| - TRENDING_BULL    |      from the library
| - TRENDING_BEAR    |
| - MEAN_REVERTING   |         |
| - HIGH_VOLATILITY  |         v
| - BREAKOUT_PENDING |  Screen Universe
| - DISTRIBUTION     |  (1500+ -> ~50 candidates)
| - ACCUMULATION     |         |
+--------------------+         v
                        Score all candidates
                        (Composite 0-100)
                               |
                               v
                        Rank by Confidence
                        x RR x Regime Fit
                               |
                               v
                        Apply Timing Filters
                               |
                               v
                        TOP 3 per session
                               |
                               v
                        Final Risk Gate
                        (ALL must pass)
```

### All 10 Strategies

| # | Strategy | Regime | Timeframe | Hold Period | Description |
|---|----------|--------|-----------|-------------|-------------|
| 01 | **Trend Momentum Rider** | Trending | Daily/15min | Intraday-Swing | Pullback to 21 EMA with RSI bounce from 40-50 zone |
| 02 | **Volatility Breakout** | Breakout Pending | 15min/5min | Intraday | BB squeeze detection followed by volume breakout |
| 03 | **VWAP Mean Reversion** | Mean Reverting | 5min/15min | Intraday | Price deviation to VWAP +/-2 sigma with RSI extreme |
| 04 | **Opening Range Breakout** | Any | 15min/5min | Intraday | First 15-min high/low break on 2x volume |
| 05 | **Earnings Momentum** | Post-earnings | Daily | 3-7 days | EPS surprise >15% with guidance confirmation |
| 06 | **Sector Rotation** | Trending | Weekly | Monthly | Buy top 3 sector ETFs, avoid bottom 3 |
| 07 | **Options Theta Harvest** | Low Volatility | Weekly | 1 week | Sell iron condors/strangles at 1-2 SD strikes |
| 08 | **SMC Reversal** | Distribution/Accum. | 15min/1hr | Intraday-Swing | Liquidity sweep + BOS + order block retest |
| 09 | **Gap Trade** | Trending | 5min | Intraday | Gap >0.5% with global cue confirmation |
| 10 | **Swing Positional** | Any (ADX>20) | Daily/Weekly | 3-15 days | Cup & Handle / Bull Flag breakout with volume |

---

## Risk Management Framework

### Position Sizing (ATR-Based)

```
Risk Amount = Portfolio x 1% (max per trade)
Position Size = Risk Amount / ATR-adjusted Stop Distance
Final Size = min(Position Size, 8% of Portfolio / Entry Price)
```

### 4-Layer Stop-Loss Architecture

| Layer | Mechanism | Details |
|-------|-----------|---------|
| **L1: Hard Stop** | Structure / ATR-based | Placed immediately on entry. NEVER moved further from entry. |
| **L2: Trailing Stop** | 2x ATR from highest high | Activates at +1 ATR profit. Parabolic SAR secondary. |
| **L3: Time Stop** | Session / day-based | Intraday: close by 15:15 IST. Swing: exit if no +1% in 5 days. |
| **L4: Break-Even** | Auto at 1:1 RR | Capital protected once first target hit. |

### Portfolio Circuit Breakers

| Threshold | Action | Reset |
|-----------|--------|-------|
| **Daily loss > 2.5%** | HALT all trading | Next trading day |
| **Weekly loss > 5.0%** | Reduce size 50% | Next week |
| **Monthly loss > 8.0%** | Strategy recalibration mandatory | After review |
| **Drawdown > 15%** | COMPLETE HALT + audit | After full strategy audit |
| **VIX > 35** | Exit all positions, 80%+ cash | Daily review |

### Portfolio Controls

- Max 10 concurrent intraday positions, 8 swing positions
- Min 4 sectors in active portfolio (diversification)
- Portfolio beta maintained between 0.8-1.4 vs Nifty
- Hedge with Nifty puts when >80% capital deployed
- Max 3% of any stock's average daily volume held
- 15% minimum cash buffer at all times

---

## Signal Output Format

Every trade signal contains **all** of the following fields:

```
+==================================================================+
|               APEX INDIA -- TRADE SIGNAL                         |
+==================================================================+
| SIGNAL ID     : APEX-20260411-103045-001                         |
| TIMESTAMP     : 11/04/2026 10:30:45 IST                         |
| INSTRUMENT    : RELIANCE | NSE | EQUITY                         |
| STRATEGY      : Trend Momentum Rider -- v1.2                    |
| MARKET REGIME : TRENDING_BULLISH                                 |
+------------------------------------------------------------------+
| ACTION        : BUY                                              |
| ORDER TYPE    : LIMIT                                            |
| ENTRY PRICE   : Rs 2,450.50 (zone: Rs 2,440 -- Rs 2,460)       |
| STOP LOSS     : Rs 2,398.00 (2.1% | 1.5x ATR from entry)       |
| TARGET 1      : Rs 2,503.00 (1:1 RR -- partial exit 33%)       |
| TARGET 2      : Rs 2,555.50 (1:2 RR -- partial exit 33%)       |
| TARGET 3      : Rs 2,608.00 (1:3 RR -- trail remainder)        |
+------------------------------------------------------------------+
| POSITION SIZE : 100 shares                                       |
| CAPITAL USED  : Rs 2,45,050 (4.9% of portfolio)                |
| RISK AMOUNT   : Rs 5,250 (1.0% of portfolio)                   |
| RR RATIO      : 1 : 3.0                                         |
+------------------------------------------------------------------+
| CONFIDENCE    : 78% ########..                                   |
| SIGNAL GRADE  : A                                                |
+------------------------------------------------------------------+
| TECHNICAL: Trend Bullish | ADX: 32 | RSI: 52 | MACD: Bullish   |
| VOLUME: 1.8x avg | Above VWAP | Bull Flag breakout              |
| FUNDAMENTAL: Score 72/100 | EPS +18.5% | Sector: Energy (Top 3) |
| SENTIMENT: Positive 7.2/10 | F&O: Fresh longs | PCR: 1.15      |
+------------------------------------------------------------------+
| REASONING:                                                       |
| Reliance showing strong trend continuation with pullback to 21   |
| EMA respected on 1.8x volume. MACD bullish crossover on daily.  |
| FII fresh long buildup in futures supports upside. Invalidated   |
| if price closes below 2,398 (swing low + ATR buffer).           |
+==================================================================+
```

---

## Performance Targets

| Metric | Target | Hard Minimum |
|--------|--------|-------------|
| **Annual Return (CAGR)** | > 25% | > 20% |
| **Sharpe Ratio** | > 1.8 | > 1.5 |
| **Sortino Ratio** | > 2.5 | > 2.0 |
| **Maximum Drawdown** | < 12% | < 15% |
| **Win Rate (Momentum)** | > 48% | > 45% |
| **Win Rate (Mean Reversion)** | > 60% | > 55% |
| **Average Win/Loss Ratio** | > 2.0 | > 1.5 |
| **Profit Factor** | > 1.9 | > 1.8 |
| **Recovery Factor** | > 4.0 | > 3.0 |
| **Calmar Ratio** | > 2.0 | > 1.5 |
| **Monthly Consistency** | > 70% months profitable | > 60% |
| **Alpha vs Nifty 50** | > 8% annual | > 5% |
| **Slippage Impact** | < 0.5% of gross returns | < 1% |

---

## Backtesting Protocol

Every strategy must pass this protocol before live deployment:

| Requirement | Specification |
|-------------|--------------|
| **Historical Period** | Minimum 5 years (multiple market cycles) |
| **Market Regimes** | At least 1 full bull + 1 bear + 1 sideways |
| **Brokerage** | 0.03% per leg (Zerodha rates) |
| **STT** | Per SEBI schedule (0.1% delivery, 0.025% intraday) |
| **Slippage** | 0.05-0.15% depending on market cap |
| **Market Impact** | 0.02-0.1% for larger positions |
| **Latency** | 50-200ms execution delay simulation |
| **Minimum Trades** | 200+ for statistical significance |
| **Walk-Forward** | Expanding window, 3-month out-of-sample |
| **Monte Carlo** | 10,000 runs for confidence intervals |
| **Anti-Overfitting** | Train/test within 20% of each other |
| **Cross-Instrument** | Must work on at least 3 different instruments |

---

## Deployment

### Development (Local)

```bash
python main.py --mode paper    # Paper trading with SQLite
```

### Production (VPS)

**Recommended:** Mumbai-based VPS co-located with NSE data center for minimal latency.

```bash
# Docker Compose (recommended)
docker-compose up -d

# Or systemd service
sudo systemctl start apex-india
```

**Infrastructure Stack:**

| Component | Specification |
|-----------|--------------|
| **Server** | 4+ vCPU, 16GB RAM, SSD |
| **Location** | Mumbai (co-locate with NSE) |
| **OS** | Ubuntu 22.04 LTS (low-latency kernel) |
| **Container** | Docker + Docker Compose |
| **Process Manager** | systemd (auto-restart on failure) |
| **Scheduled Tasks** | Cron (data backup, model updates, reports) |
| **CI/CD** | GitHub Actions (strategy deployments) |
| **Monitoring** | Grafana + Prometheus (system health) |

---

## Iron-Clad Constraints & Ethical Rules

These rules are **non-negotiable** and hardcoded into every layer:

| # | Rule | Enforcement |
|---|------|-------------|
| 1 | **Capital Preservation First** | 15% drawdown triggers mandatory halt |
| 2 | **No Gambling** | Every trade requires documented thesis, predefined SL & target |
| 3 | **No FOMO Trades** | If entry missed by > 2 ATR, trade is abandoned |
| 4 | **Regulatory Compliance** | No circuit stocks, no F&O ban stocks, no insider info |
| 5 | **Explainability** | Every signal has human-readable reasoning summary |
| 6 | **Backtest Before Live** | Full protocol must pass before any strategy goes live |
| 7 | **Human Override** | Single command (`/halt`) stops everything instantly |
| 8 | **No Overfitting** | All models evaluated on out-of-sample data only |
| 9 | **Realistic Expectations** | Claims of >50% returns with <5% DD are auto-rejected |
| 10 | **Continuous Improvement** | Weekly review mandatory; 2-month underperformers suspended |

---

## Roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Completed | Project foundation, config, database, CLI |
| **Phase 2** | ✅ Completed (14/14 tests) | Data acquisition layer (WebSocket, NSE, news, historical) |
| **Phase 3** | ✅ Completed (10/10 tests) | Technical analysis engine (40+ indicators, composite scorer) |
| **Phase 4** | ✅ Completed (15/15 tests) | Strategy library (10 strategies + regime detection) |
| **Phase 5** | ✅ Completed (17/17 tests) | Risk management framework (sizing, stops, circuit breaker, portfolio) |
| **Phase 6** | ✅ Completed (12/12 tests) | ML models (5 models) + backtesting engine (walk-forward, Monte Carlo) |
| **Phase 7** | ✅ Completed (10/10 tests) | Execution engine + paper trading + broker integration |
| **Phase 8** | ✅ Completed (10/10 tests) | Dashboard, alerts, scheduler, Docker deployment |

---

## Contributing

This is a proprietary quantitative trading system. Contribution guidelines:

1. All code must pass the existing test suite
2. New strategies require full backtesting protocol compliance
3. Risk management parameters cannot be relaxed without explicit approval
4. Every PR must include updated documentation
5. No external API endpoints may be added without security review

---

## Disclaimer

> **This software is for educational and research purposes.** Trading in financial markets involves substantial risk of loss. Past performance, whether actual or backtested, does not guarantee future results. The developers of APEX INDIA are not responsible for any financial losses incurred through the use of this system. Always trade with capital you can afford to lose, and consult a qualified financial advisor before making investment decisions.

> **SEBI Compliance:** This system is designed to comply with all applicable SEBI regulations. Users are responsible for ensuring their trading activity complies with all applicable laws and regulations in their jurisdiction.

---

<div align="center">

**APEX INDIA -- Built on discipline. Powered by intelligence. Governed by risk.**

*v3.0.0 | April 2026*

</div>



**Built on discipline. Powered by intelligence. Governed by risk.**

*v3.1.0 | April 2026 | [APEX INDIA GitHub](https://github.com/Vshn2k5/TRADE)*

</div>

---

> **Disclaimer**: This software is for educational and research purposes. Trading in financial markets involves substantial risk. The developers are not responsible for any financial losses. Always trade with capital you can afford to lose.
