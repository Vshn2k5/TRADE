"""
APEX INDIA — Phase 7 Integration Test
========================================
Verifies execution engine, order manager, paper broker,
P&L tracker, and the full signal-to-trade pipeline.
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
    print("  APEX INDIA -- Phase 7 Integration Test")
    print("  Execution Engine & Broker Integration")
    print("=" * 60 + "\n")

    # ═══════════════════════════════════════════════════
    # 1. Order Manager
    # ═══════════════════════════════════════════════════

    def test_order_manager():
        from apex_india.execution.order_manager import OrderManager, OrderStatus

        om = OrderManager(max_orders_per_day=50)

        # Create order
        order = om.create_order("RELIANCE", "BUY", 50, 1500, "LIMIT", "CNC",
                                strategy="trend_rider")
        assert order.status == OrderStatus.VALIDATED, f"Wrong status: {order.status}"
        print(f"    -> Order: {order}")

        # Modify
        om.modify_order(order.order_id, new_price=1495)
        assert order.price == 1495

        # Cancel
        om.cancel_order(order.order_id)
        assert order.status == OrderStatus.CANCELLED

        # Rejection
        bad_order = om.create_order("TEST", "BUY", -1, 100)
        assert bad_order.status == OrderStatus.REJECTED
        print(f"    -> Rejected: {bad_order.rejection_reason}")

        # Summary
        summary = om.get_summary()
        print(f"    -> Summary: {summary}")

    test("Order Manager - Lifecycle", test_order_manager)

    # ═══════════════════════════════════════════════════
    # 2. Paper Broker
    # ═══════════════════════════════════════════════════

    def test_paper_broker():
        from apex_india.execution.paper_broker import PaperBroker
        from apex_india.execution.order_manager import Order

        broker = PaperBroker(initial_capital=1_000_000, slippage_pct=0.05)
        assert broker.connect({})
        assert broker.is_connected

        # Set price
        broker.set_ltp("RELIANCE", 1500)

        # Buy order
        buy = Order("RELIANCE", "BUY", 50, 1500, "LIMIT", "CNC", strategy="test")
        result = broker.place_order(buy)
        assert result["success"], f"Buy failed: {result}"
        print(f"    -> Buy fill: {result['fill_price']} (cost=₹{result['cost']:.2f})")

        # Check position
        positions = broker.get_positions()
        assert len(positions) == 1
        print(f"    -> Position: {positions[0]}")

        # Sell order (close)
        broker.set_ltp("RELIANCE", 1550)
        sell = Order("RELIANCE", "SELL", 50, 1550, "LIMIT", "CNC", strategy="test")
        result = broker.place_order(sell)
        assert result["success"]
        print(f"    -> Sell fill: {result['fill_price']}")

        # Margins
        margins = broker.get_margins()
        print(f"    -> Margins: ₹{margins['available_cash']:,.0f} "
              f"(PnL=₹{margins['realized_pnl']:,.0f})")

    test("Paper Broker - Buy/Sell Cycle", test_paper_broker)

    # ═══════════════════════════════════════════════════
    # 3. Broker Base (interface check)
    # ═══════════════════════════════════════════════════

    def test_broker_base():
        from apex_india.execution.broker_base import BrokerBase

        # Verify abstract methods
        methods = [
            "connect", "disconnect", "place_order", "modify_order",
            "cancel_order", "get_order_status", "get_positions",
            "get_holdings", "get_ltp", "get_margins",
        ]
        for m in methods:
            assert hasattr(BrokerBase, m), f"Missing method: {m}"
        print(f"    -> All {len(methods)} abstract methods verified")

    test("Broker Base - Interface Contract", test_broker_base)

    # ═══════════════════════════════════════════════════
    # 4. Zerodha Broker (import check)
    # ═══════════════════════════════════════════════════

    def test_zerodha():
        from apex_india.execution.zerodha_broker import ZerodhaBroker, HAS_KITE

        broker = ZerodhaBroker()
        print(f"    -> KiteConnect available: {HAS_KITE}")
        print(f"    -> Broker name: {broker.name}")

        # Without credentials, connect should fail gracefully
        result = broker.connect({"api_key": "", "access_token": ""})
        print(f"    -> Connect (no creds): {result}")

    test("Zerodha Broker - Import & Graceful Fallback", test_zerodha)

    # ═══════════════════════════════════════════════════
    # 5. Upstox Broker (import check)
    # ═══════════════════════════════════════════════════

    def test_upstox():
        from apex_india.execution.upstox_broker import UpstoxBroker, HAS_UPSTOX

        broker = UpstoxBroker()
        print(f"    -> Upstox SDK available: {HAS_UPSTOX}")
        print(f"    -> Broker name: {broker.name}")

    test("Upstox Broker - Import & Graceful Fallback", test_upstox)

    # ═══════════════════════════════════════════════════
    # 6. P&L Tracker
    # ═══════════════════════════════════════════════════

    def test_pnl_tracker():
        from apex_india.execution.pnl_tracker import PnLTracker

        tracker = PnLTracker(initial_capital=1_000_000)

        # Add positions
        tracker.add_position("RELIANCE", "LONG", 50, 1500, "trend_rider")
        tracker.add_position("HDFCBANK", "LONG", 30, 1600, "orb")
        tracker.add_position("INFY", "SHORT", 20, 1800, "vwap_mr")

        # Update prices
        tracker.update_prices({
            "RELIANCE": 1550,
            "HDFCBANK": 1580,
            "INFY": 1780,
        })

        report = tracker.get_report()
        print(f"    -> Equity: ₹{report['equity']:,.0f}")
        print(f"    -> Unrealized: ₹{report['unrealized_pnl']:,.0f}")
        print(f"    -> Open: {report['open_positions']} positions")

        # Close one
        result = tracker.close_position("RELIANCE", 1555)
        print(f"    -> Closed RELIANCE: PnL=₹{result['pnl']:,.0f}")

        # Snapshot
        tracker.take_snapshot()

        # Format
        formatted = tracker.format_report()
        for line in formatted.split("\n")[:10]:
            print(f"    {line}")

    test("P&L Tracker - Real-Time Dashboard", test_pnl_tracker)

    # ═══════════════════════════════════════════════════
    # 7. Execution Engine
    # ═══════════════════════════════════════════════════

    def test_execution_engine():
        from apex_india.execution.execution_engine import ExecutionEngine
        from apex_india.execution.paper_broker import PaperBroker
        from apex_india.strategies.base_strategy import (
            TradeSignal, SignalDirection, SignalStrength, MarketRegime,
        )

        broker = PaperBroker(initial_capital=1_000_000)
        broker.connect({})

        engine = ExecutionEngine(broker=broker)

        # Create a signal
        signal = TradeSignal(
            symbol="RELIANCE",
            direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG,
            strategy_name="trend_rider",
            entry_price=1500,
            stop_loss=1460,
            targets=[1580, 1640, 1700],
            confidence=85,
            regime=MarketRegime.TRENDING_BULLISH,
            reasoning="Test signal",
        )

        # Execute
        result = engine.execute_signal(signal)
        assert result["executed"], f"Execution failed: {result}"
        print(f"    -> Executed: {result['quantity']}x{signal.symbol} "
              f"@{result['entry_price']}")

        # Check active trades
        assert len(engine.active_trades) == 1
        print(f"    -> Active trades: {len(engine.active_trades)}")

        # Get status
        status = engine.get_status()
        print(f"    -> Engine status: {status['active_trades']} active, "
              f"broker={status['broker']}")

    test("Execution Engine - Signal-to-Trade Pipeline", test_execution_engine)

    # ═══════════════════════════════════════════════════
    # 8. Execution with Risk Rejection
    # ═══════════════════════════════════════════════════

    def test_risk_rejection():
        from apex_india.execution.execution_engine import ExecutionEngine
        from apex_india.execution.paper_broker import PaperBroker
        from apex_india.risk.circuit_breaker import CircuitBreaker
        from apex_india.strategies.base_strategy import (
            TradeSignal, SignalDirection, SignalStrength, MarketRegime,
        )

        broker = PaperBroker(initial_capital=1_000_000)
        broker.connect({})

        # Tripped circuit breaker
        cb = CircuitBreaker(capital=1_000_000)
        cb.force_halt("Test halt")

        engine = ExecutionEngine(broker=broker, circuit_breaker=cb)

        signal = TradeSignal(
            symbol="TCS", direction=SignalDirection.LONG,
            strength=SignalStrength.MODERATE, strategy_name="orb",
            entry_price=3500, stop_loss=3400, targets=[3600],
            confidence=70,
        )

        result = engine.execute_signal(signal)
        assert not result["executed"], "Should be rejected"
        assert "Circuit breaker" in result["rejection_reason"]
        print(f"    -> Correctly rejected: {result['rejection_reason']}")

        # Resume and retry
        cb.resume("Test resume")
        result = engine.execute_signal(signal)
        assert result["executed"], f"Should execute after resume: {result}"
        print(f"    -> After resume: Executed {result['quantity']}xTCS")

    test("Execution - Risk Rejection & Resume", test_risk_rejection)

    # ═══════════════════════════════════════════════════
    # 9. Position Monitoring (stop exit)
    # ═══════════════════════════════════════════════════

    def test_position_monitoring():
        from apex_india.execution.execution_engine import ExecutionEngine
        from apex_india.execution.paper_broker import PaperBroker
        from apex_india.strategies.base_strategy import (
            TradeSignal, SignalDirection, SignalStrength, MarketRegime,
        )

        broker = PaperBroker(initial_capital=1_000_000)
        broker.connect({})

        engine = ExecutionEngine(broker=broker)

        signal = TradeSignal(
            symbol="INFY", direction=SignalDirection.LONG,
            strength=SignalStrength.STRONG, strategy_name="trend_rider",
            entry_price=1800, stop_loss=1760, targets=[1880],
            confidence=80,
        )

        engine.execute_signal(signal)
        assert len(engine.active_trades) == 1

        # Price drops to stop
        actions = engine.update_positions({"INFY": 1755})

        assert len(actions) == 1, f"Should have 1 exit: {actions}"
        assert len(engine.active_trades) == 0

        print(f"    -> Stop hit: PnL=₹{actions[0]['pnl']:,.0f} "
              f"({actions[0]['exit_reason']})")

    test("Position Monitoring - Stop Exit", test_position_monitoring)

    # ═══════════════════════════════════════════════════
    # 10. Full E2E: Signal → Execute → Monitor → Exit
    # ═══════════════════════════════════════════════════

    def test_full_e2e():
        from apex_india.execution.execution_engine import ExecutionEngine
        from apex_india.execution.paper_broker import PaperBroker
        from apex_india.execution.pnl_tracker import PnLTracker
        from apex_india.strategies.base_strategy import (
            TradeSignal, SignalDirection, SignalStrength, MarketRegime,
        )

        broker = PaperBroker(initial_capital=1_000_000)
        broker.connect({})

        engine = ExecutionEngine(broker=broker)
        tracker = PnLTracker(initial_capital=1_000_000)

        # Multiple signals
        signals = [
            TradeSignal("RELIANCE", SignalDirection.LONG, SignalStrength.STRONG,
                        "trend_rider", 1500, 1460, [1580, 1640], 85),
            TradeSignal("HDFCBANK", SignalDirection.LONG, SignalStrength.MODERATE,
                        "orb", 1600, 1560, [1680], 75),
            TradeSignal("INFY", SignalDirection.SHORT, SignalStrength.STRONG,
                        "vwap_mr", 1800, 1850, [1720], 80),
        ]

        for sig in signals:
            result = engine.execute_signal(sig)
            if result["executed"]:
                tracker.add_position(
                    sig.symbol, sig.direction.value,
                    result["quantity"], sig.entry_price, sig.strategy_name,
                )

        print(f"    -> Executed: {len(engine.active_trades)} trades")

        # Simulate price movement
        prices = {"RELIANCE": 1550, "HDFCBANK": 1620, "INFY": 1780}
        tracker.update_prices(prices)
        engine.update_positions(prices)

        report = tracker.get_report()
        print(f"    -> Equity: ₹{report['equity']:,.0f} "
              f"(PnL=₹{report['total_pnl']:+,.0f})")

        # Target hit
        prices = {"RELIANCE": 1585, "HDFCBANK": 1685, "INFY": 1715}
        actions = engine.update_positions(prices)
        for a in actions:
            tracker.close_position(a["symbol"], a["exit_price"])
            print(f"       Exit {a['symbol']}: PnL=₹{a['pnl']:+,.0f} ({a['exit_reason']})")

        final = tracker.get_report()
        print(f"    -> Final: {final['open_positions']} open, "
              f"{final['closed_trades']} closed, "
              f"P&L=₹{final['total_pnl']:+,.0f}")

    test("Full E2E: Signals → Execute → Monitor → Exit", test_full_e2e)

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
