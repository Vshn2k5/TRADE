"""
APEX INDIA — Phase 4 Integration Test
========================================
Verifies all strategy modules, regime detector, timing,
and the full selection pipeline.
"""

import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT_ROOT)

import traceback
import numpy as np
import pandas as pd

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []


def make_trending_data(n: int = 250, direction: str = "up") -> pd.DataFrame:
    """Generate trending OHLCV data."""
    np.random.seed(42)
    dates = pd.date_range("2024-06-01", periods=n, freq="D")
    drift = 0.001 if direction == "up" else -0.001
    price = 1000.0
    prices = []
    for _ in range(n):
        price *= (1 + drift + np.random.normal(0, 0.012))
        prices.append(price)
    close = pd.Series(prices, index=dates)
    return pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]) * (1 + np.random.normal(0, 0.003, n)),
        "high": close * (1 + np.abs(np.random.normal(0.005, 0.005, n))),
        "low": close * (1 - np.abs(np.random.normal(0.005, 0.005, n))),
        "close": close,
        "volume": np.random.randint(100000, 5000000, n),
    }, index=dates)


def make_range_data(n: int = 200) -> pd.DataFrame:
    """Generate range-bound OHLCV data."""
    np.random.seed(99)
    dates = pd.date_range("2024-06-01", periods=n, freq="D")
    price = 1000.0
    prices = []
    for _ in range(n):
        price = 1000 + np.random.normal(0, 15)
        prices.append(price)
    close = pd.Series(prices, index=dates)
    return pd.DataFrame({
        "open": close * (1 + np.random.normal(0, 0.002, n)),
        "high": close * (1 + np.abs(np.random.normal(0.003, 0.003, n))),
        "low": close * (1 - np.abs(np.random.normal(0.003, 0.003, n))),
        "close": close,
        "volume": np.random.randint(100000, 3000000, n),
    }, index=dates)


def test(name, func):
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
    print("  APEX INDIA -- Phase 4 Integration Test")
    print("=" * 60 + "\n")

    trending = make_trending_data(250, "up")
    ranging = make_range_data(200)

    # ── Test 1: Base Strategy & Models ──
    def test_base():
        from apex_india.strategies.base_strategy import (
            BaseStrategy, TradeSignal, SignalDirection, SignalStrength, MarketRegime,
        )
        assert len(MarketRegime) == 8, f"Expected 8 regimes: {len(MarketRegime)}"
        sig = TradeSignal(
            symbol="TEST", direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG, strategy_name="test",
            entry_price=100.0, stop_loss=95.0, targets=[110, 115, 120],
            confidence=85.0, regime=MarketRegime.TRENDING_BULLISH,
        )
        assert sig.risk_reward == 2.0, f"R:R should be 2.0: {sig.risk_reward}"
        print(f"    -> Signal model: {sig}")

    test("Base Strategy & Signal Model", test_base)

    # ── Test 2: Regime Detector ──
    def test_regime():
        from apex_india.models.regime.regime_detector import RegimeDetector
        from apex_india.strategies.base_strategy import MarketRegime
        detector = RegimeDetector()

        regime = detector.detect(trending, vix=14.5, breadth={"advance_pct": 65})
        print(f"    -> Trending data regime: {regime.value}")
        print(f"    -> Scores: {detector.scores}")
        assert regime != MarketRegime.UNKNOWN, "Should detect a regime"

        regime2 = detector.detect(ranging, vix=12.0)
        print(f"    -> Ranging data regime: {regime2.value}")

    test("Regime Detector - Trending & Ranging", test_regime)

    # ── Test 3: Timing Intelligence ──
    def test_timing():
        from apex_india.strategies.timing import TimingIntelligence
        timing = TimingIntelligence()

        session = timing.get_session_info()
        print(f"    -> Session: {session['session']}")

        calendar = timing.get_calendar_context()
        print(f"    -> Calendar: {calendar['weekday']}, "
              f"Risk adj={calendar['risk_adjustment']}")
        for evt in calendar.get("special_events", []):
            print(f"       - {evt}")

        plan = timing.scale_in_plan(150, tranches=3)
        assert sum(plan) == 150, f"Scale-in plan doesn't sum: {plan}"
        print(f"    -> Scale-in plan: {plan}")

    test("Timing Intelligence - Session & Calendar", test_timing)

    # ── Test 4-13: Individual strategies ──
    strategies_to_test = [
        ("Strategy #1: Trend Rider", "apex_india.strategies.momentum.trend_rider", "TrendMomentumRider", trending),
        ("Strategy #2: Vol Breakout", "apex_india.strategies.breakout.vol_breakout", "VolatilityBreakout", trending),
        ("Strategy #3: VWAP Mean Reversion", "apex_india.strategies.mean_reversion.vwap_mr", "VWAPMeanReversion", ranging),
        ("Strategy #4: ORB", "apex_india.strategies.breakout.orb", "OpeningRangeBreakout", trending),
        ("Strategy #5: Earnings Momentum", "apex_india.strategies.momentum.earnings", "EarningsMomentum", trending),
        ("Strategy #6: Sector Rotation", "apex_india.strategies.momentum.sector_rotation", "SectorRotation", trending),
        ("Strategy #7: Theta Harvest", "apex_india.strategies.options.theta_harvest", "ThetaHarvest", ranging),
        ("Strategy #8: SMC Reversal", "apex_india.strategies.smc.smc_reversal", "SMCReversal", trending),
        ("Strategy #9: Gap Trade", "apex_india.strategies.momentum.gap_trade", "GapTrade", trending),
        ("Strategy #10: Swing Positional", "apex_india.strategies.momentum.swing_positional", "SwingPositional", trending),
    ]

    for test_name, module_path, class_name, data in strategies_to_test:
        def make_test(mp, cn, d):
            def _test():
                import importlib
                mod = importlib.import_module(mp)
                cls = getattr(mod, cn)
                strategy = cls()
                assert hasattr(strategy, "generate_signals"), "Missing generate_signals"
                assert hasattr(strategy, "compute_targets"), "Missing compute_targets"
                print(f"    -> {strategy.name} v{strategy.version}, "
                      f"regimes={[r.value for r in strategy.applicable_regimes[:2]]}...")

                # Try generating a signal
                from apex_india.strategies.base_strategy import MarketRegime
                regime = strategy.applicable_regimes[0] if strategy.applicable_regimes else MarketRegime.UNKNOWN
                signal = strategy.run(d, "TESTSTOCK", regime)
                if signal:
                    print(f"    -> Signal: {signal}")
                else:
                    print(f"    -> No signal (conditions not met — normal)")
            return _test
        test(test_name, make_test(module_path, class_name, data))

    # ── Test 14: Strategy Selector (full pipeline) ──
    def test_selector():
        from apex_india.strategies.strategy_selector import StrategySelector

        selector = StrategySelector()

        # Build a small universe
        universe = {
            "RELIANCE": make_trending_data(250, "up"),
            "HDFCBANK": make_trending_data(250, "up"),
            "INFY": make_range_data(200),
        }

        benchmark = make_trending_data(250, "up")

        candidates = selector.select(
            universe_data=universe,
            benchmark_df=benchmark,
            vix=14.5,
            breadth={"advance_pct": 65},
            min_confidence=50,
        )

        print(f"    -> Regime: {selector.current_regime.value}")
        print(f"    -> Candidates: {len(candidates)}/{len(universe)} stocks")
        for c in candidates:
            print(f"       {c}")

        # Print report
        report = selector.format_candidates_report(candidates)
        for line in report.split("\n")[:8]:
            print(f"    {line}")

    test("Strategy Selector - Full Pipeline", test_selector)

    # ── Test 15: Real Data Pipeline ──
    def test_real_pipeline():
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        from apex_india.data.processors.data_cleaner import DataCleaner
        from apex_india.strategies.strategy_selector import StrategySelector
        from datetime import datetime, timedelta
        import pytz

        IST = pytz.timezone("Asia/Kolkata")

        fetcher = HistoricalDataFetcher()
        raw = fetcher._fetch_from_yahoo(
            "TCS",
            datetime.now(IST) - timedelta(days=400),
            datetime.now(IST),
        )
        if raw is None or len(raw) < 200:
            print("    -> Skipping: insufficient Yahoo data")
            return

        cleaner = DataCleaner()
        clean = cleaner.clean_ohlcv(raw, symbol="TCS")

        selector = StrategySelector()
        candidates = selector.select(
            universe_data={"TCS": clean},
            vix=15.0,
            min_confidence=40,
        )
        print(f"    -> TCS: Regime={selector.current_regime.value}, "
              f"Candidates={len(candidates)}")
        for c in candidates:
            print(f"       -> {c}")

    test("Real Pipeline: Yahoo -> Clean -> Select (TCS)", test_real_pipeline)

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
