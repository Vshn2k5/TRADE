"""
APEX INDIA — Phase 3 Integration Test
========================================
Verifies all indicator modules compute correctly on real and
synthetic data, and the composite scorer produces valid signals.
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


def make_test_data(n: int = 200) -> pd.DataFrame:
    """Generate realistic synthetic OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=n, freq="D")

    # Trending price with random walks
    price = 1000.0
    prices = []
    for _ in range(n):
        price *= (1 + np.random.normal(0.0005, 0.015))
        prices.append(price)

    close = pd.Series(prices, index=dates)
    noise = lambda: np.random.uniform(0.005, 0.02, n)
    high = close * (1 + noise())
    low = close * (1 - noise())
    open_ = close.shift(1).fillna(close.iloc[0]) * (1 + np.random.normal(0, 0.005, n))

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(100000, 5000000, n),
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
    print("  APEX INDIA -- Phase 3 Integration Test")
    print("=" * 60 + "\n")

    df = make_test_data(200)

    # ── Test 1: Trend Indicators ──
    def test_trend():
        from apex_india.data.indicators.trend import TrendIndicators
        trend = TrendIndicators()
        result = trend.compute_all(df)
        assert "ema_9" in result.columns, "EMA 9 missing"
        assert "ema_200" in result.columns, "EMA 200 missing"
        assert "adx" in result.columns, "ADX missing"
        assert "supertrend_direction" in result.columns, "Supertrend missing"
        assert "ichi_tenkan" in result.columns, "Ichimoku missing"
        assert "ha_close" in result.columns, "Heikin-Ashi missing"
        assert "dema_21" in result.columns, "DEMA missing"
        assert "tema_21" in result.columns, "TEMA missing"
        print(f"    -> {len(result.columns)} columns | ADX={result['adx'].iloc[-1]:.1f}")

    test("Trend Indicators - Full Suite", test_trend)

    # ── Test 2: Momentum Indicators ──
    def test_momentum():
        from apex_india.data.indicators.momentum import MomentumIndicators
        mom = MomentumIndicators()
        result = mom.compute_all(df)
        assert "rsi" in result.columns, "RSI missing"
        assert "macd" in result.columns, "MACD missing"
        assert "stoch_rsi_k" in result.columns, "Stoch RSI missing"
        assert "roc_5" in result.columns, "ROC missing"
        assert "williams_r" in result.columns, "Williams %R missing"
        assert "cci" in result.columns, "CCI missing"
        assert "mfi" in result.columns, "MFI missing"
        rsi = result["rsi"].iloc[-1]
        assert 0 <= rsi <= 100, f"RSI out of range: {rsi}"
        print(f"    -> RSI={rsi:.1f} | MACD={result['macd'].iloc[-1]:.2f}")

    test("Momentum Indicators - Full Suite", test_momentum)

    # ── Test 3: Volatility Indicators ──
    def test_volatility():
        from apex_india.data.indicators.volatility import VolatilityIndicators
        vol = VolatilityIndicators()
        result = vol.compute_all(df)
        assert "atr" in result.columns, "ATR missing"
        assert "bb_upper" in result.columns, "BB missing"
        assert "kc_upper" in result.columns, "Keltner missing"
        assert "squeeze_on" in result.columns, "Squeeze missing"
        assert "dc_upper" in result.columns, "Donchian missing"
        assert "hv_20" in result.columns, "HV missing"
        print(f"    -> ATR={result['atr'].iloc[-1]:.2f} | BB Width={result['bb_bandwidth'].iloc[-1]:.2f}")

    test("Volatility Indicators - Full Suite", test_volatility)

    # ── Test 4: Volume Indicators ──
    def test_volume():
        from apex_india.data.indicators.volume import VolumeIndicators
        vol = VolumeIndicators()
        result = vol.compute_all(df)
        assert "obv" in result.columns, "OBV missing"
        assert "cmf" in result.columns, "CMF missing"
        assert "ad_line" in result.columns, "A/D Line missing"
        assert "rvol" in result.columns, "RVOL missing"
        assert "force_index" in result.columns, "Force Index missing"
        print(f"    -> CMF={result['cmf'].iloc[-1]:.3f} | RVOL={result['rvol'].iloc[-1]:.2f}")

    test("Volume Indicators - Full Suite", test_volume)

    # ── Test 5: Price Action ──
    def test_price_action():
        from apex_india.data.indicators.price_action import PriceActionIndicators
        pa = PriceActionIndicators()
        result = pa.compute_all(df)
        assert "pat_doji" in result.columns, "Doji pattern missing"
        assert "pat_hammer" in result.columns, "Hammer pattern missing"
        assert "pat_bull_engulf" in result.columns, "Engulfing missing"
        assert "pattern_score" in result.columns, "Pattern score missing"
        assert "fib_618" in result.columns, "Fibonacci missing"
        assert "swing_high" in result.columns, "Swing points missing"
        assert "gap_pct" in result.columns, "Gap analysis missing"

        # Count detected patterns
        patterns = ["pat_doji", "pat_hammer", "pat_bull_engulf",
                     "pat_bear_engulf", "pat_morning_star"]
        total = sum(result[p].sum() for p in patterns if p in result.columns)
        print(f"    -> {total} patterns detected | Fib 61.8%={result['fib_618'].iloc[-1]:.2f}")

    test("Price Action - Patterns & Fibonacci", test_price_action)

    # ── Test 6: Derivatives Analysis ──
    def test_derivatives():
        from apex_india.data.indicators.derivatives import DerivativesAnalysis
        deriv = DerivativesAnalysis()

        # PCR
        pcr_result = deriv.analyze_pcr([0.8, 0.9, 1.0, 1.2, 1.35])
        assert pcr_result["signal"] == "bullish", f"Expected bullish: {pcr_result}"
        print(f"    -> PCR={pcr_result['pcr']:.2f} | Signal={pcr_result['signal']}")

        # IV
        iv_result = deriv.iv_analysis(25.0, list(np.random.uniform(10, 30, 252)))
        assert "iv_rank" in iv_result, "IV Rank missing"
        print(f"    -> IV Rank={iv_result['iv_rank']:.1f}% | Strategy={iv_result['strategy']}")

        # Futures basis
        basis = deriv.futures_basis(24000, 24150, 15)
        assert basis["sentiment"] == "bullish", f"Expected bullish: {basis}"
        print(f"    -> Basis={basis['basis_pct']:.2f}% | Sentiment={basis['sentiment']}")

        # OI S/R from mock chain
        chain = pd.DataFrame({
            "strikePrice": [23500, 23600, 23700, 23800, 23900, 24000, 24100, 24200],
            "CE_OI": [10000, 20000, 50000, 80000, 120000, 200000, 150000, 100000],
            "PE_OI": [150000, 200000, 180000, 100000, 50000, 30000, 20000, 10000],
        })
        sr = deriv.oi_support_resistance(chain)
        assert sr["resistance"] == 24000, f"Expected 24000: {sr}"
        assert sr["support"] == 23600, f"Expected 23600: {sr}"
        print(f"    -> Support={sr['support']} | Resistance={sr['resistance']}")

    test("Derivatives Analysis - PCR, IV, Basis, OI S/R", test_derivatives)

    # ── Test 7: Sector Analysis ──
    def test_sector():
        from apex_india.data.indicators.sector import SectorAnalysis
        sector = SectorAnalysis()

        # Create mock sector data
        sector_data = {}
        for name in ["BANK", "IT", "PHARMA", "AUTO", "METAL"]:
            sector_data[name] = make_test_data(100)

        ranking = sector.relative_strength(sector_data)
        assert not ranking.empty, "Ranking empty"
        assert "return_20d_pct" in ranking.columns, "Return column missing"
        print(f"    -> {len(ranking)} sectors ranked")

        rotation = sector.sector_rotation(sector_data)
        assert "phase" in rotation, "Phase missing"
        print(f"    -> Rotation phase: {rotation['phase']}")

    test("Sector Analysis - RS Ranking & Rotation", test_sector)

    # ── Test 8: Composite Scorer (the main event) ──
    def test_scorer():
        from apex_india.data.indicators.composite_scorer import CompositeScorer, Signal

        scorer = CompositeScorer()

        # Score single stock
        signal = scorer.score(df, symbol="RELIANCE")
        assert isinstance(signal, Signal), "Not a Signal object"
        assert 0 <= signal.score <= 100, f"Score out of range: {signal.score}"
        assert signal.direction in ("BUY", "SELL", "NEUTRAL"), f"Bad direction: {signal.direction}"
        assert signal.entry_price > 0, "No entry price"
        print(f"    -> {signal}")
        print(f"    -> Components: {signal.components}")

    test("Composite Scorer - Single Stock Signal", test_scorer)

    # ── Test 9: Composite Scorer - Universe Batch ──
    def test_scorer_batch():
        from apex_india.data.indicators.composite_scorer import CompositeScorer

        scorer = CompositeScorer()

        # Create universe
        universe = {}
        for sym in ["RELIANCE", "HDFCBANK", "INFY", "TCS", "SBIN"]:
            universe[sym] = make_test_data(200)

        signals = scorer.score_universe(universe, min_score=55)
        print(f"    -> {len(signals)} actionable signals from {len(universe)} stocks")

        # Print formatted report
        report = CompositeScorer.format_signal_report(signals)
        for line in report.split("\n")[:10]:
            print(f"    {line}")

    test("Composite Scorer - Universe Batch Scoring", test_scorer_batch)

    # ── Test 10: Full Pipeline (Yahoo -> Indicators -> Score) ──
    def test_full_pipeline():
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        from apex_india.data.processors.data_cleaner import DataCleaner
        from apex_india.data.indicators.composite_scorer import CompositeScorer
        from datetime import datetime, timedelta
        import pytz

        IST = pytz.timezone("Asia/Kolkata")

        # Fetch real data
        fetcher = HistoricalDataFetcher()
        raw = fetcher._fetch_from_yahoo(
            "RELIANCE",
            datetime.now(IST) - timedelta(days=400),
            datetime.now(IST),
        )
        if raw is None or len(raw) < 50:
            print("    -> Skipping: insufficient Yahoo data")
            return

        # Clean
        cleaner = DataCleaner()
        clean = cleaner.clean_ohlcv(raw, symbol="RELIANCE")

        # Score
        scorer = CompositeScorer()
        signal = scorer.score(clean, symbol="RELIANCE")

        assert signal.entry_price > 0, "No entry price from real data"
        print(f"    -> RELIANCE Real Signal: {signal}")
        print(f"    -> Score={signal.score} | Direction={signal.direction} | "
              f"SL={signal.stop_loss} | R:R={signal.risk_reward}")

    test("Full Pipeline: Yahoo -> Clean -> Score (RELIANCE)", test_full_pipeline)

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
