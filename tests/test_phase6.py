"""
APEX INDIA — Phase 6 Integration Test
========================================
Verifies ML models, backtesting engine, walk-forward,
Monte Carlo, and adaptive engine.
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


def make_data(n=300, seed=42):
    np.random.seed(seed)
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    price = 1000.0
    prices = []
    for _ in range(n):
        price *= (1 + np.random.normal(0.0003, 0.015))
        prices.append(price)
    close = pd.Series(prices, index=dates)
    return pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]) * (1 + np.random.normal(0, 0.003, n)),
        "high": close * (1 + np.abs(np.random.normal(0.005, 0.005, n))),
        "low": close * (1 - np.abs(np.random.normal(0.005, 0.005, n))),
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
    print("  APEX INDIA -- Phase 6 Integration Test")
    print("  ML Models & Backtesting Engine")
    print("=" * 60 + "\n")

    df = make_data(300)

    # ═══════════════════════════════════════════════════
    # 1. Performance Metrics
    # ═══════════════════════════════════════════════════

    def test_metrics():
        from apex_india.backtesting.metrics import PerformanceMetrics

        eq = pd.Series(
            np.cumsum(np.random.normal(100, 50, 250)) + 1_000_000,
            index=pd.date_range("2024-01-01", periods=250, freq="D"),
        )
        trades = [
            {"pnl": 5000}, {"pnl": -2000}, {"pnl": 3000},
            {"pnl": -1000}, {"pnl": 7000}, {"pnl": -3000},
            {"pnl": 4000}, {"pnl": 2000}, {"pnl": -500},
        ]

        pm = PerformanceMetrics(eq, trades)
        report = pm.full_report()

        print(f"    -> Sharpe:  {report['returns']['sharpe']}")
        print(f"    -> Sortino: {report['returns']['sortino']}")
        print(f"    -> Max DD:  {report['drawdown']['max_drawdown_pct']:.2f}%")
        print(f"    -> Win Rate: {report['trades']['win_rate']}%")
        print(f"    -> PF:      {report['trades']['profit_factor']}")

        assert "sharpe" in report["returns"]
        assert "max_drawdown_pct" in report["drawdown"]

    test("Performance Metrics - Full Report", test_metrics)

    # ═══════════════════════════════════════════════════
    # 2. Backtest Engine
    # ═══════════════════════════════════════════════════

    def test_backtest():
        from apex_india.backtesting.engine import BacktestEngine
        from apex_india.strategies.breakout.orb import OpeningRangeBreakout

        engine = BacktestEngine(initial_capital=1_000_000, slippage_pct=0.05)
        strategy = OpeningRangeBreakout()

        result = engine.run(df, strategy, symbol="TEST")

        print(f"    -> Trades: {result['num_trades']}")
        print(f"    -> Final:  ₹{result['final_capital']:,.0f}")
        print(f"    -> Return: {result['metrics']['returns']['total_return_pct']:.2f}%")
        print(f"    -> Sharpe: {result['metrics']['returns']['sharpe']}")

        assert "equity_curve" in result
        assert result["num_trades"] >= 0

    test("Backtest Engine - Full Run (ORB)", test_backtest)

    # ═══════════════════════════════════════════════════
    # 3. Transaction Costs
    # ═══════════════════════════════════════════════════

    def test_costs():
        from apex_india.backtesting.engine import BacktestEngine
        engine = BacktestEngine()

        cost_del = engine.compute_costs(1500, 100, "BUY", is_delivery=True)
        cost_int = engine.compute_costs(1500, 100, "SELL", is_delivery=False)

        print(f"    -> Delivery BUY 100x1500: ₹{cost_del:.2f}")
        print(f"    -> Intraday SELL 100x1500: ₹{cost_int:.2f}")

        assert cost_del > 0, "Costs should be > 0"
        assert cost_int > 0, "Costs should be > 0"

    test("Transaction Cost Model", test_costs)

    # ═══════════════════════════════════════════════════
    # 4. Walk-Forward
    # ═══════════════════════════════════════════════════

    def test_walkforward():
        from apex_india.backtesting.walk_forward import WalkForwardOptimizer
        from apex_india.strategies.breakout.orb import OpeningRangeBreakout

        wf = WalkForwardOptimizer(initial_capital=1_000_000)
        result = wf.run(make_data(500, seed=123), OpeningRangeBreakout(), n_splits=3)

        print(f"    -> Windows: {result['n_windows']}")
        print(f"    -> Avg OOS Sharpe: {result['avg_oos_sharpe']}")
        print(f"    -> Robustness: {result['robustness_score']}%")

        for w in result["windows"]:
            print(f"       W{w['window']}: IS={w['is_sharpe']:.2f} "
                  f"OOS={w['oos_sharpe']:.2f} "
                  f"Div={w['divergence_pct']:.1f}% "
                  f"{'PASS' if w['passed'] else 'FAIL'}")

    test("Walk-Forward Optimization", test_walkforward)

    # ═══════════════════════════════════════════════════
    # 5. Monte Carlo
    # ═══════════════════════════════════════════════════

    def test_montecarlo():
        from apex_india.backtesting.monte_carlo import MonteCarloSimulator

        trades = [{"pnl": np.random.normal(200, 1500)} for _ in range(100)]
        mc = MonteCarloSimulator(n_simulations=5000)
        result = mc.simulate(trades)

        print(f"    -> Profit probability: {result['probability_of_profit']:.1f}%")
        print(f"    -> Mean return: {result['returns_pct']['mean']:.1f}%")
        print(f"    -> Mean DD: {result['max_drawdown_pct']['mean']:.1f}%")
        print(f"    -> P5 equity: ₹{result['final_equity']['percentiles']['p5']:,.0f}")
        print(f"    -> P95 equity: ₹{result['final_equity']['percentiles']['p95']:,.0f}")

        assert result["n_simulations"] == 5000

    test("Monte Carlo Stress Test", test_montecarlo)

    # ═══════════════════════════════════════════════════
    # 6. Price Direction Classifier
    # ═══════════════════════════════════════════════════

    def test_classifier():
        from apex_india.models.direction.price_classifier import PriceDirectionClassifier

        clf = PriceDirectionClassifier(lookforward=1, n_estimators=50)
        train_data = make_data(500, seed=77)

        result = clf.fit(train_data)
        if "error" in result:
            print(f"    -> Skipped: {result['error']}")
            return

        print(f"    -> Accuracy: {result['accuracy']:.3f}")
        print(f"    -> Features: {result['n_features']}")
        print(f"    -> Top features: {list(result['top_features'].keys())[:5]}")

        pred = clf.predict(train_data)
        print(f"    -> Prediction: {pred['direction']} "
              f"(conf={pred['confidence']:.1f}%)")

    test("Price Direction Classifier (ML)", test_classifier)

    # ═══════════════════════════════════════════════════
    # 7. Volatility Predictor
    # ═══════════════════════════════════════════════════

    def test_vol_pred():
        from apex_india.models.volatility.vol_predictor import VolatilityPredictor

        vp = VolatilityPredictor()
        result = vp.predict(df, horizon=5)

        print(f"    -> Composite vol: {result['composite_vol']*100:.1f}%")
        print(f"    -> Vol regime: {result['vol_regime']}")
        print(f"    -> C2C: {result['estimators']['close_to_close']*100:.1f}%")
        print(f"    -> Parkinson: {result['estimators']['parkinson']*100:.1f}%")
        print(f"    -> EWMA: {result['estimators']['ewma']*100:.1f}%")
        print(f"    -> GARCH model: {result['estimators']['garch']['model']}")

    test("Volatility Predictor - Composite Forecast", test_vol_pred)

    # ═══════════════════════════════════════════════════
    # 8. HMM Regime Classifier
    # ═══════════════════════════════════════════════════

    def test_hmm():
        from apex_india.models.regime.hmm_regime import HMMRegimeClassifier

        hmm = HMMRegimeClassifier(n_states=4)
        fit_result = hmm.fit(df)

        if "error" in fit_result:
            print(f"    -> Skipped: {fit_result['error']}")
            return

        print(f"    -> Model: {fit_result['model']}")
        print(f"    -> States: {fit_result['state_distribution']}")

        pred = hmm.predict(df)
        print(f"    -> Current regime: {pred['regime']}")

    test("HMM Regime Classifier", test_hmm)

    # ═══════════════════════════════════════════════════
    # 9. DQN Entry Agent
    # ═══════════════════════════════════════════════════

    def test_dqn():
        from apex_india.models.timing.dqn_entry import DQNEntryAgent

        agent = DQNEntryAgent()
        print(f"    -> Mode: {agent.stats['mode']}")

        state = agent.build_state(rsi=55, adx=30, bb_pct_b=0.7, volume_ratio=1.5)
        action = agent.act(state)
        print(f"    -> State: RSI=55, ADX=30 -> Action: {agent.get_action_name(action)}")

        # Simulate a few transitions
        for _ in range(100):
            s = agent.build_state(
                rsi=np.random.uniform(20, 80),
                adx=np.random.uniform(10, 50),
                volume_ratio=np.random.uniform(0.5, 3),
            )
            a = agent.act(s)
            r = np.random.normal(0, 100)
            s2 = agent.build_state(rsi=np.random.uniform(20, 80))
            agent.remember(s, a, r, s2, False)

        loss = agent.learn()
        print(f"    -> Training loss: {loss if loss else 'N/A (batch not full)'}")
        print(f"    -> Memory: {agent.stats['memory_size']}, Epsilon: {agent.stats['epsilon']:.3f}")

    test("DQN Entry Agent", test_dqn)

    # ═══════════════════════════════════════════════════
    # 10. FinBERT Sentiment
    # ═══════════════════════════════════════════════════

    def test_sentiment():
        from apex_india.models.sentiment.finbert_india import FinBERTIndia

        analyzer = FinBERTIndia()

        headlines = [
            "HDFC Bank reports record quarterly profit, beats estimates",
            "Reliance Industries stock surges on strong earnings momentum",
            "FII selling intensifies amid global recession fears",
            "India GDP growth slows to 5.4%, below expectations",
            "Nifty hits all-time high as DII buying continues",
        ]

        result = analyzer.analyze_headlines(headlines)
        print(f"    -> Method: {analyzer.analyze('test')['method']}")
        print(f"    -> Aggregate: {result['aggregate_sentiment']} "
              f"(score={result['score']:.3f})")
        print(f"    -> Positive: {result['positive_pct']:.0f}%, "
              f"Negative: {result['negative_pct']:.0f}%")

    test("FinBERT Sentiment Analyzer", test_sentiment)

    # ═══════════════════════════════════════════════════
    # 11. Adaptive Engine
    # ═══════════════════════════════════════════════════

    def test_adaptive():
        from apex_india.models.adaptive_engine import AdaptiveEngine

        engine = AdaptiveEngine()

        # Simulate 5 days of trades
        for day in range(5):
            trades = [
                {"strategy": "trend_rider", "pnl": np.random.normal(500, 2000)},
                {"strategy": "orb", "pnl": np.random.normal(300, 1500)},
                {"strategy": "vwap_mr", "pnl": np.random.normal(-100, 1000)},
            ]
            engine.daily_update(trades, regime="TRENDING_BULLISH")

        report = engine.get_report()
        print(f"    -> Strategy weights: {report['strategy_weights']}")
        print(f"    -> Adaptations: {report['total_adaptations']}")
        print(f"    -> Days tracked: {report['daily_summaries_count']}")

    test("Adaptive Engine - Daily Learning Loop", test_adaptive)

    # ═══════════════════════════════════════════════════
    # 12. Real Data Pipeline
    # ═══════════════════════════════════════════════════

    def test_real_pipeline():
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        from apex_india.data.processors.data_cleaner import DataCleaner
        from apex_india.backtesting.engine import BacktestEngine
        from apex_india.strategies.momentum.trend_rider import TrendMomentumRider
        from datetime import datetime, timedelta
        import pytz

        IST = pytz.timezone("Asia/Kolkata")
        fetcher = HistoricalDataFetcher()
        raw = fetcher._fetch_from_yahoo(
            "RELIANCE", datetime.now(IST) - timedelta(days=500),
            datetime.now(IST),
        )
        if raw is None or len(raw) < 250:
            print("    -> Skipping: insufficient Yahoo data")
            return

        cleaner = DataCleaner()
        clean = cleaner.clean_ohlcv(raw, symbol="RELIANCE")

        engine = BacktestEngine(initial_capital=1_000_000)
        result = engine.run(clean, TrendMomentumRider(), symbol="RELIANCE")

        print(f"    -> RELIANCE: {result['num_trades']} trades")
        print(f"    -> Return: {result['metrics']['returns']['total_return_pct']:.2f}%")
        print(f"    -> Sharpe: {result['metrics']['returns']['sharpe']:.4f}")
        print(f"    -> Max DD: {result['metrics']['drawdown']['max_drawdown_pct']:.2f}%")

    test("Real Pipeline: Yahoo -> Backtest -> Report", test_real_pipeline)

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
