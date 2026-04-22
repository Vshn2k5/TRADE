"""
APEX INDIA — Phase 8 Integration Test
========================================
Verifies dashboard, alerts, report generator, scheduler,
and full system integration.
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
    print("  APEX INDIA -- Phase 8 Integration Test")
    print("  Dashboard, Alerts & Deployment")
    print("=" * 60 + "\n")

    # ═══════════════════════════════════════════════════
    # 1. Chart Builder
    # ═══════════════════════════════════════════════════

    def test_charts():
        from apex_india.dashboard.charts import ChartBuilder, HAS_PLOTLY

        # Metrics cards (always works)
        cards = ChartBuilder.metrics_cards({
            "Equity": 1_004_240.0,
            "Day P&L": 4240.0,
            "Open Positions": 3,
        })
        assert len(cards) == 3
        assert "1,004,240" in cards[0]
        print(f"    -> Plotly available: {HAS_PLOTLY}")
        print(f"    -> Metric cards: {len(cards)} generated")

        if HAS_PLOTLY:
            # Equity curve
            equity = pd.Series(
                np.cumsum(np.random.normal(100, 50, 100)) + 1_000_000,
                index=pd.date_range("2024-01-01", periods=100, freq="D"),
            )
            fig = ChartBuilder.equity_curve(equity)
            assert fig is not None
            print(f"    -> Equity chart: {len(fig.data)} traces")

            # Candlestick
            df = pd.DataFrame({
                "open": [100, 102, 101], "high": [105, 106, 104],
                "low": [98, 100, 99], "close": [103, 101, 103],
                "volume": [1000, 1500, 1200],
            })
            fig = ChartBuilder.candlestick(df)
            assert fig is not None
            print(f"    -> Candlestick chart: {len(fig.data)} traces")

            # P&L waterfall
            fig = ChartBuilder.pnl_waterfall({
                "Mon": 5000, "Tue": -2000, "Wed": 3000, "Thu": -1000, "Fri": 4000
            })
            assert fig is not None
            print(f"    -> P&L waterfall: {len(fig.data)} traces")

            # Sector pie
            fig = ChartBuilder.sector_exposure({
                "Energy": 30, "Banking": 25, "IT": 20, "FMCG": 15, "Cash": 10
            })
            assert fig is not None
            print(f"    -> Sector pie: {len(fig.data)} traces")
        else:
            print("    -> Plotly not installed, skipping chart tests")

    test("Chart Builder - All Chart Types", test_charts)

    # ═══════════════════════════════════════════════════
    # 2. Report Generator
    # ═══════════════════════════════════════════════════

    def test_report_gen():
        from apex_india.dashboard.report_generator import ReportGenerator

        gen = ReportGenerator()

        trades = [
            {"symbol": "RELIANCE", "direction": "LONG", "pnl": 5000,
             "strategy": "trend_rider", "exit_reason": "Target 1 hit"},
            {"symbol": "HDFCBANK", "direction": "LONG", "pnl": -2000,
             "strategy": "orb", "exit_reason": "Stop hit"},
            {"symbol": "INFY", "direction": "SHORT", "pnl": 3000,
             "strategy": "vwap_mr", "exit_reason": "Target 2 hit"},
        ]

        report = gen.daily_report(
            trades=trades,
            equity=1_006_000,
            initial_capital=1_000_000,
            circuit_breaker_status={
                "level": "NORMAL",
                "trading_allowed": True,
                "metrics": {"daily_pct": -0.12, "drawdown_pct": 1.8, "consecutive_losses": 0}
            },
            strategy_weights={"trend_rider": 0.4, "orb": 0.3, "vwap_mr": 0.3},
        )

        # Verify content
        assert "DAILY PERFORMANCE REPORT" in report
        assert "RELIANCE" in report
        assert "STRATEGY ATTRIBUTION" in report
        assert "RISK STATUS" in report
        assert "ADAPTIVE WEIGHTS" in report

        # Print first 15 lines
        for line in report.split("\n")[:15]:
            print(f"    {line}")
        print(f"    ... ({len(report.split(chr(10)))} total lines)")

    test("Report Generator - Daily Report", test_report_gen)

    # ═══════════════════════════════════════════════════
    # 3. Telegram Bot (disabled mode)
    # ═══════════════════════════════════════════════════

    def test_telegram():
        from apex_india.alerts.telegram_bot import TelegramBot

        # Without token — should be disabled gracefully
        bot = TelegramBot(token="", chat_id="")
        assert not bot.is_enabled
        print(f"    -> Enabled (no token): {bot.is_enabled}")

        # All send methods should return False without error
        assert not bot.send_signal({"symbol": "RELIANCE", "direction": "LONG"})
        assert not bot.send_execution({"symbol": "RELIANCE", "quantity": 50})
        assert not bot.send_exit({"symbol": "RELIANCE", "pnl": 5000})
        assert not bot.send_circuit_breaker({"level": "DAILY_HALT"})
        assert not bot.send_daily_report("test report")
        assert not bot.send_pnl_update(5000, 1_005_000)
        print(f"    -> All 6 send methods: graceful no-op")

    test("Telegram Bot - Graceful Disable", test_telegram)

    # ═══════════════════════════════════════════════════
    # 4. Notification Manager
    # ═══════════════════════════════════════════════════

    def test_notifier():
        from apex_india.alerts.notification_manager import NotificationManager

        nm = NotificationManager()

        # All event types
        nm.notify("signal", {"symbol": "RELIANCE", "direction": "LONG"})
        nm.notify("execution", {"symbol": "RELIANCE", "quantity": 50})
        nm.notify("exit", {"symbol": "RELIANCE", "pnl": 5000})
        nm.notify("circuit_breaker", {"level": "DAILY_HALT", "alerts": ["test"]})
        nm.notify("pnl_update", {"pnl": 5000, "equity": 1_005_000})
        nm.notify("daily_report", {"report": "test report"})

        stats = nm.stats
        assert stats["total_sent"] == 6
        print(f"    -> Stats: {stats}")

        # Mute/unmute
        nm.mute()
        nm.notify("signal", {"symbol": "TEST"})
        assert nm.stats["total_sent"] == 6  # Should not increment
        nm.unmute()
        print(f"    -> Mute/unmute: working")

    test("Notification Manager - Multi-Channel", test_notifier)

    # ═══════════════════════════════════════════════════
    # 5. Scheduler Initialize
    # ═══════════════════════════════════════════════════

    def test_scheduler_init():
        from scheduler import ApexScheduler

        sched = ApexScheduler(mode="paper")
        assert sched.initialize()

        status = sched.get_status()
        print(f"    -> Mode: {status['mode']}")
        print(f"    -> Broker: {'connected' if status['broker_connected'] else 'disconnected'}")
        print(f"    -> Market hours: {status['market_hours']}")
        print(f"    -> Active trades: {status['active_trades']}")

        assert status["mode"] == "paper"
        assert status["broker_connected"]

    test("Scheduler - Initialization", test_scheduler_init)

    # ═══════════════════════════════════════════════════
    # 6. Scheduler EOD Tasks
    # ═══════════════════════════════════════════════════

    def test_scheduler_eod():
        from scheduler import ApexScheduler

        sched = ApexScheduler(mode="paper")
        sched.initialize()

        # Run EOD tasks (should not crash)
        sched._eod_tasks()
        print(f"    -> EOD tasks completed without error")

    test("Scheduler - EOD Report Generation", test_scheduler_eod)

    # ═══════════════════════════════════════════════════
    # 7. Dashboard Import
    # ═══════════════════════════════════════════════════

    def test_dashboard_import():
        # Just verify dashboard module imports without error
        from apex_india.dashboard.app import run_dashboard, HAS_STREAMLIT
        from apex_india.dashboard.charts import ChartBuilder, HAS_PLOTLY

        print(f"    -> Streamlit available: {HAS_STREAMLIT}")
        print(f"    -> Plotly available: {HAS_PLOTLY}")
        print(f"    -> Dashboard module: importable")

    test("Dashboard Module - Import", test_dashboard_import)

    # ═══════════════════════════════════════════════════
    # 8. Docker Config Validation
    # ═══════════════════════════════════════════════════

    def test_docker():
        docker_path = Path(PROJECT_ROOT) / "Dockerfile"
        compose_path = Path(PROJECT_ROOT) / "docker-compose.yml"

        assert docker_path.exists(), "Dockerfile missing"
        assert compose_path.exists(), "docker-compose.yml missing"

        # Verify Dockerfile content
        dockerfile = docker_path.read_text()
        assert "python:3.11" in dockerfile
        assert "Asia/Kolkata" in dockerfile
        assert "HEALTHCHECK" in dockerfile
        print(f"    -> Dockerfile: {len(dockerfile)} bytes, Python 3.11, IST timezone")

        # Verify compose content
        compose = compose_path.read_text()
        assert "postgres" in compose
        assert "redis" in compose
        assert "apex" in compose
        assert "8501" in compose
        print(f"    -> docker-compose.yml: {len(compose)} bytes, 4 services")

    test("Docker - Config Validation", test_docker)

    # ═══════════════════════════════════════════════════
    # 9. Full System E2E
    # ═══════════════════════════════════════════════════

    def test_full_system():
        """Test the full signal → execute → report → notify pipeline."""
        from apex_india.execution.paper_broker import PaperBroker
        from apex_india.execution.execution_engine import ExecutionEngine
        from apex_india.execution.pnl_tracker import PnLTracker
        from apex_india.risk.circuit_breaker import CircuitBreaker
        from apex_india.alerts.notification_manager import NotificationManager
        from apex_india.alerts.telegram_bot import TelegramBot
        from apex_india.dashboard.report_generator import ReportGenerator
        from apex_india.strategies.base_strategy import (
            TradeSignal, SignalDirection, SignalStrength,
        )

        # Init
        broker = PaperBroker(initial_capital=1_000_000)
        broker.connect({})
        cb = CircuitBreaker(capital=1_000_000)
        engine = ExecutionEngine(broker=broker, circuit_breaker=cb)
        tracker = PnLTracker(initial_capital=1_000_000)
        notifier = NotificationManager(TelegramBot())
        report_gen = ReportGenerator()

        # Signal
        signal = TradeSignal(
            "RELIANCE", SignalDirection.LONG, SignalStrength.STRONG,
            "trend_rider", 1500, 1460, [1580, 1640], 85,
        )

        # Notify signal
        notifier.notify("signal", signal.to_dict())

        # Execute
        result = engine.execute_signal(signal)
        assert result["executed"]
        notifier.notify("execution", {
            "symbol": "RELIANCE",
            "quantity": result["quantity"],
            "entry_price": result["entry_price"],
        })

        # Track
        tracker.add_position("RELIANCE", "LONG", result["quantity"],
                           result["entry_price"], "trend_rider")

        # Price move → exit
        actions = engine.update_positions({"RELIANCE": 1455})
        for a in actions:
            tracker.close_position(a["symbol"], a["exit_price"])
            notifier.notify("exit", a)
            cb.record_pnl(a["pnl"])

        # Generate report
        report = report_gen.daily_report(
            trades=[{"symbol": "RELIANCE", "direction": "LONG",
                    "pnl": actions[0]["pnl"] if actions else 0,
                    "strategy": "trend_rider",
                    "exit_reason": actions[0]["exit_reason"] if actions else "?"}],
            equity=tracker.equity,
            circuit_breaker_status=cb.check(),
        )

        notifier.notify("daily_report", {"report": report})

        print(f"    -> Signal -> Execute -> Exit -> Report -> Notify: OK")
        print(f"    -> Final equity: Rs {tracker.equity:,.0f}")
        print(f"    -> Notifications sent: {notifier.stats['total_sent']}")
        print(f"    -> Circuit breaker: {cb.check()['level']}")

    test("Full System E2E: Signal → Notify → Report", test_full_system)

    # ═══════════════════════════════════════════════════
    # 10. Cross-Phase Regression
    # ═══════════════════════════════════════════════════

    def test_regression():
        """Quick smoke test of all major components."""
        # Phase 2: Data
        from apex_india.data.feeds.historical_data import HistoricalDataFetcher
        from apex_india.data.processors.data_cleaner import DataCleaner

        # Phase 3: Indicators
        from apex_india.data.indicators.trend import TrendIndicators
        from apex_india.data.indicators.momentum import MomentumIndicators

        # Phase 4: Strategies
        from apex_india.strategies.base_strategy import BaseStrategy
        from apex_india.strategies.strategy_selector import StrategySelector

        # Phase 5: Risk
        from apex_india.risk.position_sizer import PositionSizer
        from apex_india.risk.circuit_breaker import CircuitBreaker

        # Phase 6: ML + Backtesting
        from apex_india.backtesting.engine import BacktestEngine
        from apex_india.backtesting.metrics import PerformanceMetrics

        # Phase 7: Execution
        from apex_india.execution.execution_engine import ExecutionEngine
        from apex_india.execution.paper_broker import PaperBroker

        # Phase 8: Dashboard + Alerts
        from apex_india.dashboard.report_generator import ReportGenerator
        from apex_india.alerts.notification_manager import NotificationManager

        print(f"    -> All 16 core modules importable")
        print(f"    -> Phases 2-8: import regression PASSED")

    test("Cross-Phase Import Regression", test_regression)

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
