"""
APEX INDIA — Portfolio Risk Manager
======================================
Portfolio-level risk controls including correlation monitoring,
beta management, hedging rules, diversification enforcement,
and liquidity risk management.

Rules:
- Reduce when 3+ positions have correlation > 0.7
- Portfolio beta between 0.8 and 1.4 vs Nifty
- Buy Nifty puts when > 80% deployed
- Min 4 sectors for diversification
- Max 3% of stock's ADV per position
- Min 15% cash buffer

Usage:
    prm = PortfolioRiskManager(capital=1_000_000)
    assessment = prm.assess(positions, market_data)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

from apex_india.utils.logger import get_logger

logger = get_logger("risk.portfolio")


class Position:
    """Represents an open position in the portfolio."""

    def __init__(
        self,
        symbol: str,
        direction: str,
        quantity: int,
        entry_price: float,
        current_price: float,
        sector: str = "UNKNOWN",
        beta: float = 1.0,
        avg_daily_volume: int = 0,
    ):
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.entry_price = entry_price
        self.current_price = current_price
        self.sector = sector
        self.beta = beta
        self.avg_daily_volume = avg_daily_volume

    @property
    def value(self) -> float:
        return abs(self.quantity * self.current_price)

    @property
    def pnl(self) -> float:
        if self.direction == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def pnl_pct(self) -> float:
        return (self.pnl / (self.entry_price * self.quantity)) * 100


class PortfolioRiskManager:
    """
    Portfolio-level risk assessment and enforcement.
    """

    # Limits
    MAX_CORRELATION_THRESHOLD = 0.7
    MAX_CORRELATED_POSITIONS = 3
    MIN_BETA = 0.8
    MAX_BETA = 1.4
    HEDGE_TRIGGER_DEPLOYED_PCT = 80.0
    MIN_SECTORS = 4
    MAX_ADV_PCT = 3.0       # Max 3% of average daily volume
    MIN_CASH_BUFFER_PCT = 15.0

    def __init__(self, capital: float = 1_000_000):
        self.capital = capital

    # ───────────────────────────────────────────────────────────
    # Full Portfolio Assessment
    # ───────────────────────────────────────────────────────────

    def assess(
        self,
        positions: List[Position],
        price_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Dict[str, Any]:
        """
        Run full portfolio risk assessment.

        Returns comprehensive risk report with violations and recommendations.
        """
        if not positions:
            return {
                "status": "CLEAR",
                "violations": [],
                "recommendations": [],
                "metrics": self._empty_metrics(),
            }

        violations = []
        recommendations = []

        # 1. Concentration check
        conc = self._check_concentration(positions)
        violations.extend(conc.get("violations", []))
        recommendations.extend(conc.get("recommendations", []))

        # 2. Sector diversification
        div = self._check_diversification(positions)
        violations.extend(div.get("violations", []))
        recommendations.extend(div.get("recommendations", []))

        # 3. Beta exposure
        beta = self._check_beta(positions)
        violations.extend(beta.get("violations", []))
        recommendations.extend(beta.get("recommendations", []))

        # 4. Correlation check
        if price_data:
            corr = self._check_correlation(positions, price_data)
            violations.extend(corr.get("violations", []))
            recommendations.extend(corr.get("recommendations", []))

        # 5. Liquidity check
        liq = self._check_liquidity(positions)
        violations.extend(liq.get("violations", []))

        # 6. Cash buffer
        cash = self._check_cash_buffer(positions)
        violations.extend(cash.get("violations", []))
        recommendations.extend(cash.get("recommendations", []))

        # 7. Hedging check
        hedge = self._check_hedging(positions)
        recommendations.extend(hedge.get("recommendations", []))

        # Status
        if any("CRITICAL" in v for v in violations):
            status = "CRITICAL"
        elif violations:
            status = "WARNING"
        else:
            status = "CLEAR"

        return {
            "status": status,
            "violations": violations,
            "recommendations": recommendations,
            "metrics": self._compute_metrics(positions),
        }

    # ───────────────────────────────────────────────────────────
    # Individual Checks
    # ───────────────────────────────────────────────────────────

    def _check_concentration(self, positions: List[Position]) -> Dict:
        """Check single-stock and sector concentration."""
        violations = []
        recommendations = []
        total_value = sum(p.value for p in positions)

        for p in positions:
            pct = (p.value / self.capital) * 100
            if pct > 8:
                violations.append(
                    f"CRITICAL: {p.symbol} concentration {pct:.1f}% > 8% limit"
                )
                recommendations.append(
                    f"Reduce {p.symbol} by ₹{(p.value - self.capital * 0.08):,.0f}"
                )

        # Sector concentration
        sector_values = {}
        for p in positions:
            sector_values[p.sector] = sector_values.get(p.sector, 0) + p.value

        for sector, val in sector_values.items():
            pct = (val / self.capital) * 100
            if pct > 25:
                violations.append(
                    f"Sector {sector} concentration {pct:.1f}% > 25% limit"
                )

        return {"violations": violations, "recommendations": recommendations}

    def _check_diversification(self, positions: List[Position]) -> Dict:
        """Ensure minimum sector diversification."""
        violations = []
        recommendations = []

        sectors = set(p.sector for p in positions)
        if len(sectors) < self.MIN_SECTORS and len(positions) >= 4:
            violations.append(
                f"Low diversification: {len(sectors)} sectors < {self.MIN_SECTORS} minimum"
            )
            recommendations.append("Add positions in underrepresented sectors")

        return {"violations": violations, "recommendations": recommendations}

    def _check_beta(self, positions: List[Position]) -> Dict:
        """Check portfolio beta vs Nifty."""
        violations = []
        recommendations = []

        total_value = sum(p.value for p in positions)
        if total_value == 0:
            return {"violations": [], "recommendations": []}

        weighted_beta = sum(p.beta * p.value for p in positions) / total_value

        if weighted_beta > self.MAX_BETA:
            violations.append(
                f"Portfolio beta {weighted_beta:.2f} > {self.MAX_BETA} — too aggressive"
            )
            recommendations.append("Add low-beta defensives (FMCG, Pharma) or reduce high-beta")
        elif weighted_beta < self.MIN_BETA:
            recommendations.append(
                f"Portfolio beta {weighted_beta:.2f} < {self.MIN_BETA} — may underperform in bull market"
            )

        return {"violations": violations, "recommendations": recommendations}

    def _check_correlation(
        self,
        positions: List[Position],
        price_data: Dict[str, pd.DataFrame],
    ) -> Dict:
        """Check inter-position correlation."""
        violations = []
        recommendations = []

        symbols = [p.symbol for p in positions if p.symbol in price_data]
        if len(symbols) < 2:
            return {"violations": [], "recommendations": []}

        # Compute pairwise correlation
        returns = {}
        for sym in symbols:
            df = price_data[sym]
            if len(df) >= 60:
                returns[sym] = df["close"].pct_change().tail(60)

        if len(returns) < 2:
            return {"violations": [], "recommendations": []}

        returns_df = pd.DataFrame(returns)
        corr_matrix = returns_df.corr()

        high_corr_pairs = []
        for i, s1 in enumerate(symbols):
            for j, s2 in enumerate(symbols):
                if i < j and s1 in corr_matrix.columns and s2 in corr_matrix.columns:
                    r = corr_matrix.loc[s1, s2]
                    if abs(r) > self.MAX_CORRELATION_THRESHOLD:
                        high_corr_pairs.append((s1, s2, round(r, 3)))

        if len(high_corr_pairs) >= self.MAX_CORRELATED_POSITIONS:
            violations.append(
                f"High correlation risk: {len(high_corr_pairs)} pairs above {self.MAX_CORRELATION_THRESHOLD}"
            )
            for s1, s2, r in high_corr_pairs[:3]:
                recommendations.append(
                    f"Reduce one of {s1}/{s2} (correlation={r})"
                )

        return {"violations": violations, "recommendations": recommendations}

    def _check_liquidity(self, positions: List[Position]) -> Dict:
        """Ensure positions are within ADV limits."""
        violations = []

        for p in positions:
            if p.avg_daily_volume > 0:
                pct_adv = (p.quantity / p.avg_daily_volume) * 100
                if pct_adv > self.MAX_ADV_PCT:
                    violations.append(
                        f"{p.symbol}: position is {pct_adv:.1f}% of ADV "
                        f"(>{self.MAX_ADV_PCT}%) — liquidity risk"
                    )

        return {"violations": violations}

    def _check_cash_buffer(self, positions: List[Position]) -> Dict:
        """Ensure minimum cash buffer."""
        violations = []
        recommendations = []

        deployed = sum(p.value for p in positions)
        deployed_pct = (deployed / self.capital) * 100
        cash_pct = 100 - deployed_pct

        if cash_pct < self.MIN_CASH_BUFFER_PCT:
            violations.append(
                f"Cash buffer {cash_pct:.1f}% < {self.MIN_CASH_BUFFER_PCT}% minimum"
            )
            excess = deployed - self.capital * (1 - self.MIN_CASH_BUFFER_PCT / 100)
            recommendations.append(
                f"Reduce positions by ₹{excess:,.0f} to restore cash buffer"
            )

        return {"violations": violations, "recommendations": recommendations}

    def _check_hedging(self, positions: List[Position]) -> Dict:
        """Check if hedging is needed."""
        recommendations = []

        deployed = sum(p.value for p in positions)
        deployed_pct = (deployed / self.capital) * 100

        if deployed_pct > self.HEDGE_TRIGGER_DEPLOYED_PCT:
            recommendations.append(
                f"Portfolio {deployed_pct:.0f}% deployed > {self.HEDGE_TRIGGER_DEPLOYED_PCT}% — "
                f"consider buying Nifty puts for downside protection"
            )

        # Net direction check
        long_value = sum(p.value for p in positions if p.direction == "LONG")
        short_value = sum(p.value for p in positions if p.direction == "SHORT")
        net_exposure_pct = ((long_value - short_value) / self.capital) * 100

        if abs(net_exposure_pct) > 70:
            recommendations.append(
                f"Net exposure {net_exposure_pct:+.0f}% — consider hedging with "
                f"{'puts' if net_exposure_pct > 0 else 'calls'}"
            )

        return {"recommendations": recommendations}

    # ───────────────────────────────────────────────────────────
    # Metrics
    # ───────────────────────────────────────────────────────────

    def _compute_metrics(self, positions: List[Position]) -> Dict[str, Any]:
        """Compute portfolio metrics."""
        total_value = sum(p.value for p in positions)
        total_pnl = sum(p.pnl for p in positions)
        sectors = set(p.sector for p in positions)

        weighted_beta = (
            sum(p.beta * p.value for p in positions) / total_value
            if total_value > 0 else 1.0
        )

        long_value = sum(p.value for p in positions if p.direction == "LONG")
        short_value = sum(p.value for p in positions if p.direction == "SHORT")

        return {
            "num_positions": len(positions),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "deployed_pct": round((total_value / self.capital) * 100, 2),
            "cash_buffer_pct": round((1 - total_value / self.capital) * 100, 2),
            "num_sectors": len(sectors),
            "sectors": list(sectors),
            "portfolio_beta": round(weighted_beta, 3),
            "long_exposure": round(long_value, 2),
            "short_exposure": round(short_value, 2),
            "net_exposure_pct": round(((long_value - short_value) / self.capital) * 100, 2),
            "winners": sum(1 for p in positions if p.pnl > 0),
            "losers": sum(1 for p in positions if p.pnl < 0),
        }

    def _empty_metrics(self) -> Dict:
        return {
            "num_positions": 0, "total_value": 0, "total_pnl": 0,
            "deployed_pct": 0, "cash_buffer_pct": 100,
            "num_sectors": 0, "sectors": [], "portfolio_beta": 0,
            "long_exposure": 0, "short_exposure": 0, "net_exposure_pct": 0,
            "winners": 0, "losers": 0,
        }

    # ───────────────────────────────────────────────────────────
    # Pre-Trade Gate
    # ───────────────────────────────────────────────────────────

    def pre_trade_check(
        self,
        new_position: Position,
        existing_positions: List[Position],
    ) -> Dict[str, Any]:
        """
        Pre-trade risk gate — checks if a new position is allowed.

        Must pass ALL checks to proceed.
        """
        checks = []

        # 1. Single stock limit
        existing_value = sum(
            p.value for p in existing_positions if p.symbol == new_position.symbol
        )
        new_total = existing_value + new_position.value
        if (new_total / self.capital) * 100 > 8:
            checks.append(("FAIL", f"{new_position.symbol}: total exposure "
                          f"₹{new_total:,.0f} would exceed 8% limit"))
        else:
            checks.append(("PASS", "Single stock limit"))

        # 2. Sector limit
        sector_value = sum(
            p.value for p in existing_positions
            if p.sector == new_position.sector
        ) + new_position.value
        if (sector_value / self.capital) * 100 > 25:
            checks.append(("FAIL", f"Sector {new_position.sector}: "
                          f"₹{sector_value:,.0f} would exceed 25% limit"))
        else:
            checks.append(("PASS", "Sector limit"))

        # 3. Total deployment
        total_deployed = sum(p.value for p in existing_positions) + new_position.value
        if (total_deployed / self.capital) * 100 > 85:
            checks.append(("FAIL", f"Portfolio deployment "
                          f"{(total_deployed/self.capital)*100:.0f}% would exceed 85%"))
        else:
            checks.append(("PASS", "Deployment limit"))

        # 4. Liquidity
        if new_position.avg_daily_volume > 0:
            pct_adv = (new_position.quantity / new_position.avg_daily_volume) * 100
            if pct_adv > 3:
                checks.append(("FAIL", f"Liquidity: {pct_adv:.1f}% ADV > 3% limit"))
            else:
                checks.append(("PASS", "Liquidity"))

        all_passed = all(c[0] == "PASS" for c in checks)

        return {
            "approved": all_passed,
            "checks": checks,
            "rejection_reasons": [c[1] for c in checks if c[0] == "FAIL"],
        }
