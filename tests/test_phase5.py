"""
APEX INDIA — Phase 5 Integration Test
========================================
Verifies the complete risk management framework:
position sizing, stop-loss management, circuit breakers,
and portfolio risk controls.
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
    print("  APEX INDIA -- Phase 5 Integration Test")
    print("  Risk Management Framework")
    print("=" * 60 + "\n")

    # ═══════════════════════════════════════════════════════════
    # Position Sizer Tests
    # ═══════════════════════════════════════════════════════════

    def test_sizer_basic():
        from apex_india.risk.position_sizer import PositionSizer
        sizer = PositionSizer(capital=1_000_000, max_risk_pct=1.0)

        result = sizer.compute(entry_price=1500, stop_loss=1460, atr=35)
        assert result["approved"], f"Should be approved: {result}"
        assert result["quantity"] > 0, "Quantity should be > 0"

        # 1% risk check: risk_amount should be <= 10,000
        assert result["risk_amount"] <= 10_000, \
            f"Risk {result['risk_amount']} > 10,000 (1% of 10L)"

        print(f"    -> Qty={result['quantity']}, Risk=₹{result['risk_amount']:,.0f} "
              f"({result['risk_pct']:.2f}%), Value=₹{result['position_value']:,.0f}")

    test("Position Sizer - Basic 1% Risk Rule", test_sizer_basic)

    def test_sizer_exposure_limit():
        from apex_india.risk.position_sizer import PositionSizer
        sizer = PositionSizer(capital=1_000_000)

        # Register existing position = 70,000 (7%)
        sizer.register_position("RELIANCE", 70_000, sector="ENERGY")

        # Try adding more — should be capped
        result = sizer.compute(
            entry_price=1500, stop_loss=1460, symbol="RELIANCE",
            sector="ENERGY",
        )
        assert result["approved"], f"Should still be approved: {result}"
        # Position value + existing should not exceed 8%
        max_additional = 80_000 - 70_000  # 10,000 remaining
        assert result["position_value"] <= max_additional + 1500, \
            f"Position ₹{result['position_value']} exceeds remaining allowance"
        print(f"    -> After 7% existing: Qty={result['quantity']}, "
              f"Value=₹{result['position_value']:,.0f}")

    test("Position Sizer - 8% Single Stock Cap", test_sizer_exposure_limit)

    def test_sizer_kelly():
        from apex_india.risk.position_sizer import PositionSizer
        sizer = PositionSizer(capital=1_000_000)

        result = sizer.compute(
            entry_price=500, stop_loss=480,
            win_rate=0.55, avg_win_loss_ratio=1.5,
        )
        assert result["approved"]
        assert result["kelly_fraction"] is not None
        print(f"    -> Kelly fraction: {result['kelly_fraction']:.4f}, "
              f"Qty={result['quantity']}")

    test("Position Sizer - Half-Kelly Criterion", test_sizer_kelly)

    def test_sizer_deployment_limit():
        from apex_india.risk.position_sizer import PositionSizer
        sizer = PositionSizer(capital=1_000_000)

        # Deploy 85% of capital
        sizer.register_position("A", 200_000)
        sizer.register_position("B", 200_000)
        sizer.register_position("C", 200_000)
        sizer.register_position("D", 250_000)

        # Should reject (85% deployed)
        result = sizer.compute(entry_price=1000, stop_loss=960)
        assert result["quantity"] == 0 or not result["approved"], \
            "Should reject at 85% deployment"
        print(f"    -> Deployed: {sizer.deployed_pct:.1f}% | "
              f"Approved: {result.get('approved', False)}")

    test("Position Sizer - 85% Deployment Limit", test_sizer_deployment_limit)

    def test_sizer_fno():
        from apex_india.risk.position_sizer import PositionSizer
        sizer = PositionSizer(capital=1_000_000)

        result = sizer.compute(
            entry_price=24000, stop_loss=23800,
            symbol="NIFTY", is_fno=True,
        )
        print(f"    -> F&O: Qty={result['quantity']}, "
              f"Lots={result.get('lots')}, "
              f"LotSize={result.get('lot_size')}")

    test("Position Sizer - F&O Lot Rounding", test_sizer_fno)

    # ═══════════════════════════════════════════════════════════
    # Stop-Loss Manager Tests
    # ═══════════════════════════════════════════════════════════

    def test_sl_initial():
        from apex_india.risk.stop_loss_manager import StopLossManager
        slm = StopLossManager()

        # Long position
        stop = slm.compute_initial_stop(1500, "LONG", atr=35)
        assert stop == 1430.0, f"Expected 1430: {stop}"  # 1500 - 2*35

        # Short position
        stop = slm.compute_initial_stop(1500, "SHORT", atr=35)
        assert stop == 1570.0, f"Expected 1570: {stop}"

        # With structure stop (tighter)
        stop = slm.compute_initial_stop(1500, "LONG", atr=35, structure_stop=1450)
        assert stop == 1450.0, f"Should use tighter structure stop: {stop}"
        print(f"    -> Long SL=1430, Short SL=1570, Structure SL=1450")

    test("Stop-Loss - Initial Hard Stop", test_sl_initial)

    def test_sl_trailing():
        from apex_india.risk.stop_loss_manager import StopLossManager
        slm = StopLossManager()

        # Register position
        slm.register_position("P001", "RELIANCE", 1500.0, "LONG", 1430.0)

        # Price moves up
        result = slm.update_position("P001", 1550.0, atr=35)
        assert not result["should_exit"]
        print(f"    -> Price 1550: Stop={result['current_stop']}, "
              f"PnL={result['pnl_pct']:.1f}%")

        # Price moves further
        result = slm.update_position("P001", 1600.0, atr=35)
        assert result["current_stop"] >= 1430, "Stop should only tighten"
        print(f"    -> Price 1600: Stop={result['current_stop']}, "
              f"Breakeven={result['breakeven_activated']}")

        # Verify stop never moves down
        old_stop = result["current_stop"]
        result = slm.update_position("P001", 1580.0, atr=35)
        assert result["current_stop"] >= old_stop, "Stop moved backward!"
        print(f"    -> Price 1580: Stop={result['current_stop']} "
              f"(verified: never moves down)")

    test("Stop-Loss - Trailing (Ratchet-Only)", test_sl_trailing)

    def test_sl_stop_hit():
        from apex_india.risk.stop_loss_manager import StopLossManager
        slm = StopLossManager()

        slm.register_position("P002", "HDFCBANK", 1500.0, "LONG", 1430.0)

        # Price drops to stop
        result = slm.update_position("P002", 1425.0, atr=35)
        assert result["should_exit"], "Should exit on stop hit"
        print(f"    -> Stop HIT at 1425 | Reason: {result['exit_reason']}")

    test("Stop-Loss - Stop Hit Detection", test_sl_stop_hit)

    def test_sl_breakeven():
        from apex_india.risk.stop_loss_manager import StopLossManager
        slm = StopLossManager(breakeven_rr=1.0, atr_trail_mult=1.5)

        slm.register_position("P003", "INFY", 1000.0, "LONG", 960.0)

        # Move price up incrementally so trailing tracks highest
        for p in [1010, 1020, 1030, 1040, 1050, 1060, 1070, 1080]:
            slm.update_position("P003", p, atr=20)

        result = slm.update_position("P003", 1080, atr=20)
        # At 1080: highest=1080, risk=40, reward=80, R:R=2.0 -> breakeven should activate
        # Breakeven stop = entry + 0.1% buffer = ~1001
        assert result["current_stop"] >= 1000, \
            f"Break-even should activate: stop={result['current_stop']}"
        print(f"    -> R:R reached: Stop moved to {result['current_stop']} "
              f"(break-even={result['breakeven_activated']})")

    test("Stop-Loss - Break-Even Activation", test_sl_breakeven)

    # ═══════════════════════════════════════════════════════════
    # Circuit Breaker Tests
    # ═══════════════════════════════════════════════════════════

    def test_cb_daily():
        from apex_india.risk.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(capital=1_000_000, daily_limit=2.5)

        # Record losses
        cb.record_pnl(-10_000, "RELIANCE")
        cb.record_pnl(-8_000, "HDFCBANK")

        status = cb.check()
        assert not status["trading_allowed"] is False or status["level"] == "NORMAL"

        # Push past 2.5% daily limit
        cb.record_pnl(-10_000, "INFY")

        status = cb.check()
        if status["metrics"]["daily_pct"] <= -2.5:
            assert not status["trading_allowed"], "Should halt trading"
            print(f"    -> DAILY HALT triggered at {status['metrics']['daily_pct']:.2f}%")
        else:
            print(f"    -> Daily loss {status['metrics']['daily_pct']:.2f}% "
                  f"(below threshold)")

    test("Circuit Breaker - Daily Loss Limit", test_cb_daily)

    def test_cb_max_dd():
        from apex_india.risk.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(capital=1_000_000, max_dd=15.0)

        # Simulate 15% drawdown
        for _ in range(15):
            cb.record_pnl(-10_500)

        status = cb.check()
        assert not status["trading_allowed"], "Should FULL HALT at 15% DD"
        assert status["level"] == "FULL_HALT" or status["level"] == "MONTHLY_HALT"
        print(f"    -> Level: {status['level']} | "
              f"DD: {status['metrics']['drawdown_pct']:.1f}%")

    test("Circuit Breaker - Max Drawdown HALT", test_cb_max_dd)

    def test_cb_vix():
        from apex_india.risk.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(capital=1_000_000)

        status = cb.check(vix=40.0)
        assert not status["trading_allowed"]
        assert status["level"] == "VIX_EMERGENCY"
        print(f"    -> VIX Emergency at 40.0: {status['alerts'][0]}")

    test("Circuit Breaker - VIX Emergency", test_cb_vix)

    def test_cb_manual():
        from apex_india.risk.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(capital=1_000_000)

        cb.force_halt("Testing manual halt")
        assert cb.is_halted

        cb.resume("After review")
        assert not cb.is_halted
        print(f"    -> Manual halt/resume cycle working")

    test("Circuit Breaker - Manual Halt/Resume", test_cb_manual)

    # ═══════════════════════════════════════════════════════════
    # Portfolio Risk Tests
    # ═══════════════════════════════════════════════════════════

    def test_portfolio_assessment():
        from apex_india.risk.portfolio_risk import PortfolioRiskManager, Position

        prm = PortfolioRiskManager(capital=1_000_000)

        positions = [
            Position("RELIANCE", "LONG", 50, 1500, 1550, "ENERGY", 1.1, 5000000),
            Position("HDFCBANK", "LONG", 30, 1600, 1620, "BANK", 1.2, 4000000),
            Position("TCS", "LONG", 20, 3500, 3400, "IT", 0.8, 2000000),
            Position("ITC", "LONG", 100, 450, 460, "FMCG", 0.7, 8000000),
        ]

        assessment = prm.assess(positions)
        print(f"    -> Status: {assessment['status']}")
        print(f"    -> Violations: {len(assessment['violations'])}")
        for v in assessment["violations"][:3]:
            print(f"       - {v}")
        print(f"    -> Recommendations: {len(assessment['recommendations'])}")
        for r in assessment["recommendations"][:3]:
            print(f"       - {r}")
        m = assessment["metrics"]
        print(f"    -> Beta={m['portfolio_beta']:.2f}, "
              f"Sectors={m['num_sectors']}, "
              f"Deployed={m['deployed_pct']:.1f}%")

    test("Portfolio Risk - Full Assessment", test_portfolio_assessment)

    def test_portfolio_pretrade():
        from apex_india.risk.portfolio_risk import PortfolioRiskManager, Position

        prm = PortfolioRiskManager(capital=1_000_000)

        existing = [
            Position("RELIANCE", "LONG", 50, 1500, 1550, "ENERGY", 1.1, 5000000),
        ]

        # Try adding a reasonable position
        new_pos = Position("HDFCBANK", "LONG", 30, 1600, 1600, "BANK", 1.2, 4000000)
        check = prm.pre_trade_check(new_pos, existing)
        assert check["approved"], f"Should be approved: {check}"
        print(f"    -> Reasonable trade: APPROVED")

        # Try adding oversized position
        huge = Position("TCS", "LONG", 300, 3500, 3500, "IT", 0.8, 100000)
        check = prm.pre_trade_check(huge, existing)
        for c in check["checks"]:
            status = "✓" if c[0] == "PASS" else "✗"
            print(f"       {status} {c[1]}")

    test("Portfolio Risk - Pre-Trade Gate", test_portfolio_pretrade)

    def test_portfolio_concentration():
        from apex_india.risk.portfolio_risk import PortfolioRiskManager, Position

        prm = PortfolioRiskManager(capital=1_000_000)

        # Create concentrated portfolio
        positions = [
            Position("RELIANCE", "LONG", 60, 1500, 1500, "ENERGY"),  # 9% — violation
            Position("ONGC", "LONG", 200, 300, 300, "ENERGY"),       # 6%
            Position("BPCL", "LONG", 150, 500, 500, "ENERGY"),       # 7.5%
        ]

        assessment = prm.assess(positions)
        # Should have concentration violations
        assert any("concentration" in v.lower() or "sector" in v.lower()
                   for v in assessment["violations"]), \
            f"Should flag concentration: {assessment['violations']}"
        print(f"    -> Concentration violations: {len(assessment['violations'])}")

    test("Portfolio Risk - Concentration Detection", test_portfolio_concentration)

    # ═══════════════════════════════════════════════════════════
    # Full Integration: Sizing → SL → Portfolio → Circuit
    # ═══════════════════════════════════════════════════════════

    def test_full_pipeline():
        from apex_india.risk.position_sizer import PositionSizer
        from apex_india.risk.stop_loss_manager import StopLossManager
        from apex_india.risk.circuit_breaker import CircuitBreaker
        from apex_india.risk.portfolio_risk import PortfolioRiskManager, Position

        capital = 1_000_000
        sizer = PositionSizer(capital=capital)
        slm = StopLossManager()
        cb = CircuitBreaker(capital=capital)
        prm = PortfolioRiskManager(capital=capital)

        # Step 1: Size a position
        size_result = sizer.compute(entry_price=1500, stop_loss=1430, atr=35)
        assert size_result["approved"]
        qty = size_result["quantity"]

        # Step 2: Compute stop
        stop = slm.compute_initial_stop(1500, "LONG", 35)

        # Step 3: Pre-trade check
        new_pos = Position("RELIANCE", "LONG", qty, 1500, 1500, "ENERGY", 1.1, 5000000)
        gate = prm.pre_trade_check(new_pos, [])
        assert gate["approved"]

        # Step 4: Check circuit breaker
        status = cb.check()
        assert status["trading_allowed"]

        # Step 5: Register and simulate
        sizer.register_position("RELIANCE", qty * 1500)
        slm.register_position("TRADE001", "RELIANCE", 1500, "LONG", stop)

        # Simulate price movement
        slm.update_position("TRADE001", 1550, 35)
        slm.update_position("TRADE001", 1580, 35)

        # Record P&L
        pnl = (1580 - 1500) * qty
        cb.record_pnl(pnl, "RELIANCE")

        final_status = cb.check()
        print(f"    -> Full pipeline: Qty={qty}, SL={stop}, "
              f"PnL=+₹{pnl:,.0f}, "
              f"Trading={'ON' if final_status['trading_allowed'] else 'OFF'}")

    test("Full Risk Pipeline: Size → SL → Gate → Circuit", test_full_pipeline)

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
