"""
APEX INDIA — Phase 2 Integration Test
========================================
Verifies all data acquisition modules load correctly,
core functionality works, and the pipeline is wired together.
"""

import sys
import os
import io

# Force UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT_ROOT)

import traceback

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def test(name, func):
    """Run a test and record result."""
    try:
        func()
        results.append((name, True, ""))
        print(f"  {PASS} {name}")
    except Exception as e:
        results.append((name, False, str(e)))
        print(f"  {FAIL} {name}: {e}")
        traceback.print_exc()


def main():
    print("\n" + "=" * 60)
    print("  APEX INDIA -- Phase 2 Integration Test")
    print("=" * 60 + "\n")

    # ── Test 1: WebSocket Handler imports ──
    def test_ws_import():
        from apex_india.data.feeds.websocket_handler import (
            WebSocketHandler, TickData, TickCache
        )
        cache = TickCache(max_history=100)
        tick = TickData(
            symbol="RELIANCE", exchange="NSE", ltp=2450.50,
            open=2440.0, high=2455.0, low=2435.0, close=2450.50,
            volume=1500000, timestamp=None,
        )
        cache.update(tick)
        latest = cache.get_latest("RELIANCE")
        assert latest is not None, "TickCache.get_latest failed"
        assert latest.ltp == 2450.50, f"LTP mismatch: {latest.ltp}"
        assert latest.to_json(), "TickData.to_json failed"
        assert "RELIANCE" in cache.symbols, "Symbol not in cache"

    test("WebSocket Handler - TickData & TickCache", test_ws_import)

    # ── Test 2: WebSocket simulation mode ──
    def test_ws_simulation():
        from apex_india.data.feeds.websocket_handler import WebSocketHandler
        handler = WebSocketHandler()
        handler.start(threaded=True)  # Should run simulation
        import time
        time.sleep(2)  # Let it generate some ticks
        stats = handler.get_stats()
        assert stats["ticks_received"] > 0, f"No ticks received: {stats}"
        handler.stop()

    test("WebSocket Handler - Simulation Mode", test_ws_simulation)

    # ── Test 3: Historical Data Fetcher imports ──
    def test_hist_import():
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        fetcher = HistoricalDataFetcher()
        assert fetcher is not None

    test("Historical Data Fetcher - Import", test_hist_import)

    # ── Test 4: Historical Data - Yahoo Finance fallback ──
    def test_hist_yahoo():
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        from datetime import datetime, timedelta
        import pytz

        fetcher = HistoricalDataFetcher()
        IST = pytz.timezone("Asia/Kolkata")
        end = datetime.now(IST)
        start = end - timedelta(days=30)

        df = fetcher._fetch_from_yahoo("RELIANCE", start, end)
        assert df is not None, "Yahoo Finance returned None"
        assert len(df) > 5, f"Too few candles: {len(df)}"
        assert "close" in df.columns, "Missing 'close' column"
        assert "volume" in df.columns, "Missing 'volume' column"
        print(f"    -> Fetched {len(df)} daily candles from Yahoo Finance")

    test("Historical Data - Yahoo Finance Fallback", test_hist_yahoo)

    # ── Test 5: NSE Data Scraper imports ──
    def test_nse_import():
        from apex_india.data.feeds.nse_data import NSEDataScraper
        nse = NSEDataScraper()
        assert nse is not None
        stats = nse.get_cache_stats()
        assert "total_cached" in stats

    test("NSE Data Scraper - Import & Init", test_nse_import)

    # ── Test 6: NSE All Indices (live data check) ──
    def test_nse_indices():
        from apex_india.data.feeds.nse_data import NSEDataScraper
        nse = NSEDataScraper()
        indices = nse.get_all_indices()
        if indices is not None:
            assert len(indices) > 0, "No indices returned"
            print(f"    -> Fetched {len(indices)} index values from NSE")
        else:
            print(f"    -> NSE unavailable (expected outside market hours)")

    test("NSE Data Scraper - All Indices", test_nse_indices)

    # ── Test 7: Macro Data Feed ──
    def test_macro():
        from apex_india.data.feeds.macro_data import MacroDataFeed
        macro = MacroDataFeed()

        # Indian macro (static)
        india = macro.get_india_macro()
        assert "rbi_repo_rate" in india, "Missing RBI repo rate"
        assert india["rbi_repo_rate"] > 0, "Invalid repo rate"

        # Economic calendar
        events = macro.get_upcoming_events()
        assert len(events) > 0, "No upcoming events"

    test("Macro Data Feed - Indian Macro & Calendar", test_macro)

    # ── Test 8: Macro - Global data (Yahoo Finance) ──
    def test_macro_global():
        from apex_india.data.feeds.macro_data import MacroDataFeed
        macro = MacroDataFeed()

        dxy = macro.get_dxy()
        if dxy and dxy.get("price"):
            print(f"    -> DXY: {dxy['price']}")
        else:
            print(f"    -> DXY unavailable (network issue)")

        # Global sentiment
        sentiment = macro.get_global_sentiment()
        assert sentiment in ("RISK_ON", "RISK_OFF", "NEUTRAL"), f"Bad sentiment: {sentiment}"
        print(f"    -> Global sentiment: {sentiment}")

    test("Macro Data Feed - Global Data", test_macro_global)

    # ── Test 9: News Feed Aggregator ──
    def test_news():
        from apex_india.data.feeds.news_feed import NewsFeedAggregator, NewsArticle

        feed = NewsFeedAggregator()

        # Test sentiment analysis
        article = NewsArticle(
            headline="Reliance Industries surges 5% on strong quarterly earnings beat",
            source="Test",
        )
        feed.analyze_all([article])

        assert article.sentiment_score is not None, "Sentiment not scored"
        assert article.sentiment_score > 0, f"Expected positive: {article.sentiment_score}"
        assert "RELIANCE" in article.related_symbols, f"NER missed RELIANCE: {article.related_symbols}"
        assert article.event_type == "EARNINGS", f"Wrong event type: {article.event_type}"
        print(f"    -> Sentiment: {article.sentiment_score:+.2f}, Event: {article.event_type}")

        # Negative article
        neg = NewsArticle(
            headline="HDFC Bank crashes as SEBI launches investigation into loan fraud",
            source="Test",
        )
        feed.analyze_all([neg])
        assert neg.sentiment_score < 0, f"Expected negative: {neg.sentiment_score}"
        assert "HDFCBANK" in neg.related_symbols, f"NER missed HDFCBANK: {neg.related_symbols}"
        print(f"    -> Sentiment: {neg.sentiment_score:+.2f}, Event: {neg.event_type}")

    test("News Feed - Sentiment & NER Analysis", test_news)

    # ── Test 10: News Feed - RSS Fetch ──
    def test_news_rss():
        from apex_india.data.feeds.news_feed import NewsFeedAggregator
        feed = NewsFeedAggregator()
        articles = feed.fetch_all(max_per_source=5)
        print(f"    -> Fetched {len(articles)} articles from RSS feeds")
        if articles:
            analyzed = feed.analyze_all(articles[:5])
            for a in analyzed[:3]:
                print(f"    -> [{a.source}] {a.headline[:50]}... Sent={a.sentiment_score:+.2f}")

    test("News Feed - RSS Live Fetch", test_news_rss)

    # ── Test 11: Data Cleaner ──
    def test_cleaner():
        from apex_india.data.processors.data_cleaner import DataCleaner
        import pandas as pd
        import numpy as np

        cleaner = DataCleaner()

        # Create dirty test data
        dates = pd.date_range("2026-01-01", periods=50, freq="D")
        df = pd.DataFrame({
            "open": np.random.uniform(100, 110, 50),
            "high": np.random.uniform(108, 115, 50),
            "low": np.random.uniform(95, 102, 50),
            "close": np.random.uniform(100, 110, 50),
            "volume": np.random.randint(100000, 1000000, 50),
        }, index=dates)

        # Inject anomalies
        df.iloc[10, df.columns.get_loc("close")] = 0           # Zero price
        df.iloc[20, df.columns.get_loc("high")] = 50           # High < Low
        df.iloc[30, df.columns.get_loc("volume")] = -100       # Negative volume
        df.iloc[40, df.columns.get_loc("close")] = np.nan      # Missing data

        # Clean
        clean = cleaner.clean_ohlcv(df, symbol="TEST")
        assert len(clean) > 0, "Cleaning produced empty DataFrame"
        assert (clean["volume"] >= 0).all(), "Negative volume not fixed"
        assert (clean["high"] >= clean["low"]).all(), "OHLC relationship broken"
        assert clean["close"].isna().sum() == 0, "NaN prices remain"

        # Quality
        quality = cleaner.assess_quality(clean, "TEST")
        assert quality["quality_score"] > 0, "Quality score is 0"
        print(f"    -> Quality: {quality['quality_score']}/100 (Grade {quality['grade']})")

    test("Data Cleaner - Full Pipeline", test_cleaner)

    # ── Test 12: Feature Engineer ──
    def test_features():
        from apex_india.data.processors.feature_engineer import FeatureEngineer
        import pandas as pd
        import numpy as np

        engineer = FeatureEngineer()

        dates = pd.date_range("2026-01-01", periods=100, freq="D")
        df = pd.DataFrame({
            "open": np.random.uniform(100, 110, 100),
            "high": np.random.uniform(110, 115, 100),
            "low": np.random.uniform(95, 100, 100),
            "close": np.random.uniform(100, 110, 100),
            "volume": np.random.randint(100000, 1000000, 100),
        }, index=dates)

        # Ensure OHLC consistency
        df["high"] = df[["open", "high", "close"]].max(axis=1) + 1
        df["low"] = df[["open", "low", "close"]].min(axis=1) - 1

        # VWAP
        vwap_df = engineer.compute_vwap(df)
        assert "vwap" in vwap_df.columns, "VWAP not computed"
        assert "vwap_upper_1" in vwap_df.columns, "VWAP bands missing"

        # Cumulative Delta
        delta_df = engineer.compute_cumulative_delta(df)
        assert "delta" in delta_df.columns, "Delta not computed"
        assert "cum_delta" in delta_df.columns, "Cumulative delta missing"

        # Volume profile
        vpd = engineer.compute_volume_profile(df)
        assert "poc" in vpd, "POC missing"
        assert "vah" in vpd, "VAH missing"
        assert "val" in vpd, "VAL missing"
        print(f"    -> Volume Profile: POC={vpd['poc']}, VAH={vpd['vah']}, VAL={vpd['val']}")

        # Rolling features
        roll_df = engineer.compute_rolling_features(df)
        assert "f5_return" in roll_df.columns, "Rolling return missing"
        assert "f20_volatility" in roll_df.columns, "Rolling vol missing"

        # Full pipeline
        full = engineer.compute_all(df)
        print(f"    -> Full features: {len(full.columns)} columns")

        # ML feature matrix
        X, y = engineer.build_ml_feature_matrix(df)
        assert len(X) > 0, "Empty feature matrix"
        print(f"    -> ML matrix: {X.shape[1]} features, {len(X)} samples")

    test("Feature Engineer - Full Pipeline", test_features)

    # ── Test 13: Database integration ──
    def test_db_integration():
        from apex_india.data.storage.database import get_database
        db = get_database()
        db.create_tables()
        health = db.health_check()
        assert health["sql_database"] == "connected", f"DB not connected: {health}"

    test("Database - Tables & Health Check", test_db_integration)

    # ── Test 14: Full pipeline (Yahoo -> Clean -> Features -> DB) ──
    def test_full_pipeline():
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        from apex_india.data.processors.data_cleaner import DataCleaner
        from apex_india.data.processors.feature_engineer import FeatureEngineer
        from apex_india.data.storage.database import get_database
        from datetime import datetime, timedelta
        import pytz

        IST = pytz.timezone("Asia/Kolkata")
        end = datetime.now(IST)
        start = end - timedelta(days=60)

        # 1. Fetch
        fetcher = HistoricalDataFetcher()
        raw = fetcher._fetch_from_yahoo("INFY", start, end)
        if raw is None:
            print("    -> Skipping: Yahoo unavailable")
            return
        print(f"    -> Fetched {len(raw)} raw candles")

        # 2. Clean
        cleaner = DataCleaner()
        clean = cleaner.clean_ohlcv(raw, symbol="INFY")
        quality = cleaner.assess_quality(clean, "INFY")
        print(f"    -> Cleaned: {len(clean)} candles, Quality={quality['quality_score']}/100")

        # 3. Features
        engineer = FeatureEngineer()
        featured = engineer.compute_all(clean)
        print(f"    -> Features: {len(featured.columns)} columns")

        # 4. Store (just the OHLCV part)
        db = get_database()
        db.create_tables()
        count = fetcher._store_ohlcv(clean, "INFY", "NSE", "day")
        # Retrieve
        from apex_india.data.storage.models import OHLCVData
        with db.get_session() as session:
            stored = session.query(OHLCVData).filter_by(symbol="INFY").count()
        print(f"    -> Stored in DB: {stored} rows")

    test("Full Pipeline: Fetch -> Clean -> Features -> DB", test_full_pipeline)

    # ── Summary ──
    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"  RESULTS: {passed} passed, {failed} failed, {len(results)} total")

    if failed > 0:
        print("\n  Failed tests:")
        for name, ok, err in results:
            if not ok:
                print(f"    - {name}: {err}")

    print("=" * 60 + "\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
