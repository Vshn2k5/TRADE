"""
APEX INDIA — Execution Engine
================================
Smart order routing and trade orchestration.
Connects signals from the strategy selector to the broker
through risk validation gates.

Pipeline:
  Signal → Risk Gate → Position Size → Order Create → Broker Submit
  → Fill Tracking → Stop Registration → P&L Update

Usage:
    engine = ExecutionEngine(broker, order_manager, sizer, slm, cb)
    engine.execute_signal(signal)
"""

from typing import Any, Dict, List, Optional

from apex_india.execution.order_manager import OrderManager, Order, OrderStatus
from apex_india.execution.broker_base import BrokerBase
from apex_india.risk.position_sizer import PositionSizer
from apex_india.risk.stop_loss_manager import StopLossManager
from apex_india.risk.circuit_breaker import CircuitBreaker
from apex_india.risk.portfolio_risk import PortfolioRiskManager, Position
from apex_india.strategies.base_strategy import TradeSignal, SignalDirection
from apex_india.utils.logger import get_logger

logger = get_logger("execution.engine")


class ExecutionEngine:
    """
    Smart trading execution engine.
    Orchestrates the full signal-to-trade pipeline with
    multi-layer risk validation.
    """

    def __init__(
        self,
        broker: BrokerBase,
        order_manager: Optional[OrderManager] = None,
        position_sizer: Optional[PositionSizer] = None,
        stop_loss_manager: Optional[StopLossManager] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        portfolio_risk: Optional[PortfolioRiskManager] = None,
    ):
        self.broker = broker
        self.om = order_manager or OrderManager()
        self.sizer = position_sizer or PositionSizer()
        self.slm = stop_loss_manager or StopLossManager()
        self.cb = circuit_breaker or CircuitBreaker()
        self.prm = portfolio_risk or PortfolioRiskManager()

        self._active_trades: Dict[str, Dict] = {}
        self._execution_log: List[Dict] = []

    # ───────────────────────────────────────────────────────────
    # Signal Execution
    # ───────────────────────────────────────────────────────────

    def execute_signal(self, signal: TradeSignal) -> Dict[str, Any]:
        """
        Full signal-to-trade execution pipeline.

        Steps:
        1. Circuit breaker check
        2. Position sizing
        3. Pre-trade risk gate
        4. Create order
        5. Submit to broker
        6. Register stop-loss
        7. Update tracking

        Returns:
            Execution result with order details or rejection reason.
        """
        result = {
            "signal": signal.to_dict(),
            "executed": False,
            "order_id": None,
            "rejection_reason": None,
        }

        # Step 1: Circuit breaker
        cb_status = self.cb.check()
        if not cb_status["trading_allowed"]:
            result["rejection_reason"] = f"Circuit breaker: {cb_status['level']}"
            logger.warning(f"Signal rejected: {result['rejection_reason']}")
            return result

        # Step 2: Position sizing
        atr = signal.risk  # Use risk as ATR proxy
        size_result = self.sizer.compute(
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            atr=atr,
            symbol=signal.symbol,
        )

        if not size_result["approved"]:
            result["rejection_reason"] = f"Sizing: {size_result.get('reason', 'rejected')}"
            logger.warning(f"Signal rejected: {result['rejection_reason']}")
            return result

        quantity = size_result["quantity"]

        # Apply circuit breaker size multiplier
        size_mult = cb_status.get("size_multiplier", 1.0)
        quantity = max(1, int(quantity * size_mult))

        # Step 3: Pre-trade risk gate
        new_pos = Position(
            symbol=signal.symbol,
            direction=signal.direction.value,
            quantity=quantity,
            entry_price=signal.entry_price,
            current_price=signal.entry_price,
        )
        existing = self._get_existing_positions()
        gate = self.prm.pre_trade_check(new_pos, existing)

        if not gate["approved"]:
            result["rejection_reason"] = f"Risk gate: {gate['rejection_reasons']}"
            logger.warning(f"Signal rejected: {result['rejection_reason']}")
            return result

        # Step 4: Create order
        side = "BUY" if signal.direction == SignalDirection.LONG else "SELL"
        order = self.om.create_order(
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            price=signal.entry_price,
            order_type="LIMIT",
            product="MIS" if signal.timeframe in ("15min", "5min") else "CNC",
            strategy=signal.strategy_name,
            signal_id=str(id(signal)),
        )

        if order.status == OrderStatus.REJECTED:
            result["rejection_reason"] = f"Order validation: {order.rejection_reason}"
            return result

        # Step 5: Submit to broker
        broker_result = self.broker.place_order(order)

        if not broker_result.get("success"):
            result["rejection_reason"] = f"Broker: {broker_result.get('message')}"
            return result

        # Step 6: Register stop-loss
        is_intraday = order.product == "MIS"
        self.slm.register_position(
            position_id=order.order_id,
            symbol=signal.symbol,
            entry_price=signal.entry_price,
            direction=signal.direction.value,
            initial_stop=signal.stop_loss,
            is_intraday=is_intraday,
            max_hold_days=signal.metadata.get("max_hold_days"),
        )

        # Step 7: Register with position sizer
        self.sizer.register_position(
            signal.symbol,
            quantity * signal.entry_price,
        )

        # Step 8: Track
        self._active_trades[order.order_id] = {
            "order": order,
            "signal": signal,
            "quantity": quantity,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "targets": signal.targets,
        }

        result["executed"] = True
        result["order_id"] = order.order_id
        result["broker_order_id"] = order.broker_order_id
        result["quantity"] = quantity
        result["entry_price"] = signal.entry_price

        self._execution_log.append(result)

        logger.info(
            f"EXECUTED: {signal.direction.value} {quantity}x{signal.symbol} "
            f"@{signal.entry_price} | SL={signal.stop_loss} | "
            f"Strategy={signal.strategy_name}"
        )

        return result

    # ───────────────────────────────────────────────────────────
    # Position Monitoring
    # ───────────────────────────────────────────────────────────

    def update_positions(self, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Update all active positions with current prices.
        Check stops and targets.

        Returns list of exit actions taken.
        """
        actions = []

        for trade_id, trade in list(self._active_trades.items()):
            symbol = trade["signal"].symbol
            price = current_prices.get(symbol, 0)
            if price <= 0:
                continue

            atr = trade["signal"].risk  # Proxy

            # Update stop-loss manager
            sl_result = self.slm.update_position(trade_id, price, atr)

            if sl_result.get("should_exit"):
                # Execute exit
                exit_action = self._exit_position(
                    trade_id, price, sl_result.get("exit_reason", "stop")
                )
                actions.append(exit_action)

        return actions

    def _exit_position(
        self,
        trade_id: str,
        exit_price: float,
        reason: str,
    ) -> Dict[str, Any]:
        """Exit a position."""
        trade = self._active_trades.pop(trade_id, None)
        if not trade:
            return {"error": f"Trade {trade_id} not found"}

        signal = trade["signal"]
        side = "SELL" if signal.direction == SignalDirection.LONG else "BUY"

        # Create exit order
        exit_order = self.om.create_order(
            symbol=signal.symbol,
            side=side,
            quantity=trade["quantity"],
            price=exit_price,
            order_type="MARKET",
            strategy=signal.strategy_name,
        )

        broker_result = self.broker.place_order(exit_order)

        # P&L
        if signal.direction == SignalDirection.LONG:
            pnl = (exit_price - trade["entry_price"]) * trade["quantity"]
        else:
            pnl = (trade["entry_price"] - exit_price) * trade["quantity"]

        # Record with circuit breaker
        self.cb.record_pnl(pnl, signal.symbol)

        # Release from sizer
        self.sizer.release_position(
            signal.symbol,
            trade["quantity"] * trade["entry_price"],
        )

        # Clean up stop
        self.slm.close_position(trade_id)

        result = {
            "trade_id": trade_id,
            "symbol": signal.symbol,
            "exit_price": exit_price,
            "exit_reason": reason,
            "pnl": round(pnl, 2),
            "strategy": signal.strategy_name,
        }

        logger.info(
            f"EXIT: {signal.symbol} @{exit_price} | "
            f"PnL={'+'if pnl>=0 else ''}{pnl:,.0f} | "
            f"Reason: {reason}"
        )

        return result

    # ───────────────────────────────────────────────────────────
    # Queries
    # ───────────────────────────────────────────────────────────

    def _get_existing_positions(self) -> List[Position]:
        """Get existing positions for risk checks."""
        positions = []
        for trade in self._active_trades.values():
            positions.append(Position(
                symbol=trade["signal"].symbol,
                direction=trade["signal"].direction.value,
                quantity=trade["quantity"],
                entry_price=trade["entry_price"],
                current_price=trade["entry_price"],
            ))
        return positions

    @property
    def active_trades(self) -> Dict[str, Dict]:
        return dict(self._active_trades)

    @property
    def execution_log(self) -> List[Dict]:
        return list(self._execution_log)

    def get_status(self) -> Dict[str, Any]:
        """Full engine status."""
        return {
            "broker": self.broker.name,
            "connected": self.broker.is_connected,
            "active_trades": len(self._active_trades),
            "total_executions": len(self._execution_log),
            "circuit_breaker": self.cb.check(),
            "capital": self.sizer.get_exposure_report(),
            "stops": self.slm.get_all_stops(),
        }
