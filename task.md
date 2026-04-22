# APEX INDIA — Task Tracker

## Phase 1: Project Foundation & Infrastructure

- [x] Project skeleton & package structure (25 sub-packages created)
- [x] `config.yaml` — Complete system configuration (13 sections, 300+ parameters)
- [x] `requirements.txt` — All dependencies pinned (40+ packages)
- [x] `.env.example` — Environment variable template
- [x] `.gitignore` — Version control exclusions
- [x] `apex_india/utils/constants.py` — Market constants, Nifty 50/Bank lists, sector maps, lot sizes, transaction costs, indicator defaults
- [x] `apex_india/utils/logger.py` — 5-sink logging (console, system, errors, trading audit, debug) with rotation
- [x] `apex_india/utils/config.py` — YAML loader with env var interpolation, dot-notation access, validation, singleton
- [x] `apex_india/data/storage/models.py` — 7 SQLAlchemy ORM models (OHLCV, Signals, Trades, Performance, Watchlist, Portfolio, News)
- [x] `apex_india/data/storage/database.py` — Connection manager (PostgreSQL + SQLite fallback, Redis, InfluxDB)
- [x] `scheduler.py` — Market calendar (NSE holidays), session detection, APScheduler integration
- [x] `main.py` — CLI entry point (--status, --mode, --init-db, --validate-config)
- [x] Verify: `python main.py --status` runs successfully
- [x] Verify: `python main.py --init-db` creates all database tables
- [x] Verify: `python main.py --validate-config` passes validation

## Phase 2: Data Acquisition Layer
- [ ] WebSocket handler (Zerodha Kite)
- [ ] Historical data fetcher
- [ ] NSE data scraper
- [ ] Macro data feeds
- [ ] News feed aggregator
- [ ] Data cleaner & feature engineer

## Phase 3: Technical Analysis & Signal Engine
- [ ] Trend indicators (EMA, ADX, Ichimoku, Supertrend)
- [ ] Momentum indicators (RSI, MACD, Stochastic RSI)
- [ ] Volatility indicators (BB, ATR, Keltner)
- [ ] Volume indicators (VWAP, OBV, CMF)
- [ ] Price action (patterns, S/R, SMC)
- [ ] Derivatives analysis (options, futures)
- [ ] Sector analysis
- [ ] Composite signal scorer

## Phase 4–8: Pending Phase 2–3 completion
