"""
APEX INDIA — Position Sizer
==============================
ATR-based volatility-adjusted position sizing with hard risk limits.

Core Rules:
- Max 1% of capital risked per trade
- ATR-based distance determines quantity
- Half-Kelly criterion for optimal sizing
- Lot size rounding for F&O instruments
- Exposure limits: 8% single stock, 25% sector, 40% correlated

Usage:
    sizer = PositionSizer(capital=1_000_000)
    result = sizer.compute(entry=1500, stop_loss=1460, atr=35)
"""

from typing import Any, Dict, Optional

from apex_india.utils.logger import get_logger
from apex_india.utils.constants import FNO_LOT_SIZES as LOT_SIZES

logger = get_logger("risk.position_sizer")


class PositionSizer:
    """
    Volatility-adjusted position sizing engine.

    Determines the exact quantity and capital allocation
    for each trade based on account risk parameters.
    """

    # Hard limits
    MAX_RISK_PER_TRADE_PCT = 1.0      # 1% of capital
    MAX_SINGLE_STOCK_PCT = 8.0        # 8% of portfolio
    MAX_SECTOR_EXPOSURE_PCT = 25.0    # 25% of portfolio
    MAX_CORRELATED_PCT = 40.0         # 40% of portfolio
    MAX_PORTFOLIO_DEPLOYED_PCT = 85.0 # 85% max deployment
    MIN_CASH_BUFFER_PCT = 15.0        # 15% always in cash

    def __init__(
        self,
        capital: float = 1_000_000,
        max_risk_pct: float = 1.0,
        max_single_stock_pct: float = 8.0,
    ):
        self.capital = capital
        self.max_risk_pct = min(max_risk_pct, self.MAX_RISK_PER_TRADE_PCT)
        self.max_single_stock_pct = min(max_single_stock_pct, self.MAX_SINGLE_STOCK_PCT)

        # Tracking
        self._deployed_capital = 0.0
        self._positions: Dict[str, float] = {}  # symbol -> allocated capital
        self._sector_exposure: Dict[str, float] = {}

    # ───────────────────────────────────────────────────────────
    # Core Sizing
    # ───────────────────────────────────────────────────────────

    def compute(
        self,
        entry_price: float,
        stop_loss: float,
        atr: Optional[float] = None,
        symbol: Optional[str] = None,
        sector: Optional[str] = None,
        is_fno: bool = False,
        win_rate: Optional[float] = None,
        avg_win_loss_ratio: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Compute position size for a trade.

        Args:
            entry_price: Planned entry price
            stop_loss: Stop-loss price
            atr: Average True Range (for volatility adjustment)
            symbol: Stock symbol (for exposure checks)
            sector: Sector name (for sector limits)
            is_fno: If True, rounds to lot sizes
            win_rate: Historical win rate (0-1) for Kelly
            avg_win_loss_ratio: Avg win / avg loss for Kelly

        Returns:
            Dict with quantity, risk_amount, position_value, etc.
        """
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return self._reject("Invalid stop-loss: risk per share is zero")

        # Available capital (respecting cash buffer)
        available = self.capital - self._deployed_capital
        max_deployable = self.capital * (self.MAX_PORTFOLIO_DEPLOYED_PCT / 100)
        available = min(available, max_deployable - self._deployed_capital)

        if available <= 0:
            return self._reject("No capital available (deployment limit reached)")

        # Step 1: Risk-based sizing (1% rule)
        max_risk_amount = self.capital * (self.max_risk_pct / 100)
        quantity_by_risk = int(max_risk_amount / risk_per_share)

        # Step 2: ATR-based adjustment
        if atr and atr > 0:
            # If stop is wider than 2 ATR, reduce size proportionally
            atr_ratio = risk_per_share / atr
            if atr_ratio > 2.5:
                quantity_by_risk = int(quantity_by_risk * (2.0 / atr_ratio))

        # Step 3: Kelly Criterion (half-Kelly for safety)
        kelly_fraction = None
        if win_rate is not None and avg_win_loss_ratio is not None:
            kelly = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
            kelly = max(0, kelly)
            kelly_fraction = kelly / 2  # Half-Kelly

            kelly_max_capital = self.capital * kelly_fraction
            quantity_by_kelly = int(kelly_max_capital / entry_price)
            quantity_by_risk = min(quantity_by_risk, quantity_by_kelly)

        # Step 4: Single stock exposure limit
        max_position_value = self.capital * (self.max_single_stock_pct / 100)
        existing_exposure = self._positions.get(symbol, 0) if symbol else 0
        remaining_allowance = max_position_value - existing_exposure
        quantity_by_exposure = int(remaining_allowance / entry_price)

        # Step 5: Sector exposure check
        if sector:
            max_sector = self.capital * (self.MAX_SECTOR_EXPOSURE_PCT / 100)
            sector_used = self._sector_exposure.get(sector, 0)
            sector_remaining = max_sector - sector_used
            quantity_by_sector = int(sector_remaining / entry_price)
        else:
            quantity_by_sector = quantity_by_risk

        # Step 6: Take minimum of all limits
        final_quantity = max(0, min(
            quantity_by_risk,
            quantity_by_exposure,
            quantity_by_sector,
            int(available / entry_price),
        ))

        # Step 7: F&O lot size rounding
        lot_size = 1
        if is_fno and symbol:
            lot_size = LOT_SIZES.get(symbol, 1)
            if lot_size > 1:
                final_quantity = (final_quantity // lot_size) * lot_size

        # Reject if quantity is zero
        if final_quantity <= 0:
            return self._reject("Quantity zero after all limits applied")

        # Compute final values
        position_value = final_quantity * entry_price
        risk_amount = final_quantity * risk_per_share
        risk_pct = (risk_amount / self.capital) * 100
        position_pct = (position_value / self.capital) * 100

        return {
            "approved": True,
            "quantity": final_quantity,
            "lots": final_quantity // lot_size if lot_size > 1 else None,
            "lot_size": lot_size if is_fno else None,
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "risk_per_share": round(risk_per_share, 2),
            "risk_amount": round(risk_amount, 2),
            "risk_pct": round(risk_pct, 3),
            "position_value": round(position_value, 2),
            "position_pct": round(position_pct, 2),
            "kelly_fraction": round(kelly_fraction, 4) if kelly_fraction else None,
            "capital": self.capital,
            "available_capital": round(available, 2),
            "deployed_pct": round((self._deployed_capital / self.capital) * 100, 2),
        }

    # ───────────────────────────────────────────────────────────
    # Position Tracking
    # ───────────────────────────────────────────────────────────

    def register_position(
        self,
        symbol: str,
        value: float,
        sector: Optional[str] = None,
    ) -> None:
        """Register an open position for exposure tracking."""
        self._positions[symbol] = self._positions.get(symbol, 0) + value
        self._deployed_capital += value

        if sector:
            self._sector_exposure[sector] = self._sector_exposure.get(sector, 0) + value

        logger.info(
            f"Position registered: {symbol} +₹{value:,.0f} | "
            f"Deployed: {self._deployed_capital/self.capital*100:.1f}%"
        )

    def release_position(
        self,
        symbol: str,
        value: float,
        sector: Optional[str] = None,
    ) -> None:
        """Release a closed position."""
        self._positions[symbol] = max(0, self._positions.get(symbol, 0) - value)
        self._deployed_capital = max(0, self._deployed_capital - value)

        if sector:
            self._sector_exposure[sector] = max(0, self._sector_exposure.get(sector, 0) - value)

    def update_capital(self, new_capital: float) -> None:
        """Update capital (after P&L settlement)."""
        self.capital = new_capital
        logger.info(f"Capital updated: ₹{new_capital:,.0f}")

    # ───────────────────────────────────────────────────────────
    # Queries
    # ───────────────────────────────────────────────────────────

    @property
    def deployed_pct(self) -> float:
        return (self._deployed_capital / self.capital) * 100 if self.capital > 0 else 0

    @property
    def available_capital(self) -> float:
        max_deployable = self.capital * (self.MAX_PORTFOLIO_DEPLOYED_PCT / 100)
        return max(0, max_deployable - self._deployed_capital)

    def get_exposure_report(self) -> Dict[str, Any]:
        """Get current exposure breakdown."""
        return {
            "capital": self.capital,
            "deployed": round(self._deployed_capital, 2),
            "deployed_pct": round(self.deployed_pct, 2),
            "available": round(self.available_capital, 2),
            "positions": dict(self._positions),
            "sector_exposure": dict(self._sector_exposure),
            "cash_buffer_pct": round(100 - self.deployed_pct, 2),
        }

    @staticmethod
    def _reject(reason: str) -> Dict[str, Any]:
        return {"approved": False, "reason": reason, "quantity": 0}
