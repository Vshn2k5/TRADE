"""
APEX INDIA — Plotly Chart Builders
====================================
Reusable chart components for the Streamlit dashboard.

Charts:
- Equity curve with drawdown overlay
- Candlestick with indicators
- P&L waterfall (daily)
- Sector exposure pie
- Signal heatmap
- Monte Carlo distribution

Usage:
    from apex_india.dashboard.charts import ChartBuilder
    fig = ChartBuilder.equity_curve(equity_series)
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


class ChartBuilder:
    """
    Production-grade Plotly chart builders for APEX INDIA dashboard.
    """

    # Color palette
    COLORS = {
        "bg": "#0E1117",
        "card": "#1A1F2E",
        "green": "#00D26A",
        "red": "#FF4444",
        "blue": "#4A9EFF",
        "yellow": "#FFD700",
        "text": "#E0E0E0",
        "grid": "#2A2F3E",
        "accent": "#7C3AED",
    }

    TEMPLATE = {
        "paper_bgcolor": "#0E1117",
        "plot_bgcolor": "#1A1F2E",
        "font": {"color": "#E0E0E0", "family": "Inter, sans-serif"},
    }

    @classmethod
    def equity_curve(
        cls,
        equity: pd.Series,
        title: str = "Equity Curve",
    ) -> "go.Figure":
        """Equity curve with drawdown overlay."""
        if not HAS_PLOTLY:
            return None

        peak = equity.cummax()
        dd = ((equity - peak) / peak) * 100

        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.03,
        )

        # Equity line
        fig.add_trace(go.Scatter(
            x=equity.index, y=equity.values,
            name="Equity", line=dict(color=cls.COLORS["blue"], width=2),
            fill="tozeroy", fillcolor="rgba(74,158,255,0.1)",
        ), row=1, col=1)

        # Peak line
        fig.add_trace(go.Scatter(
            x=peak.index, y=peak.values,
            name="Peak", line=dict(color=cls.COLORS["yellow"], width=1, dash="dot"),
        ), row=1, col=1)

        # Drawdown
        fig.add_trace(go.Scatter(
            x=dd.index, y=dd.values,
            name="Drawdown %", line=dict(color=cls.COLORS["red"], width=1),
            fill="tozeroy", fillcolor="rgba(255,68,68,0.2)",
        ), row=2, col=1)

        fig.update_layout(
            title=title, height=500, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            **cls.TEMPLATE,
        )
        fig.update_xaxes(gridcolor=cls.COLORS["grid"])
        fig.update_yaxes(gridcolor=cls.COLORS["grid"])

        return fig

    @classmethod
    def candlestick(
        cls,
        df: pd.DataFrame,
        title: str = "Price Chart",
        show_volume: bool = True,
    ) -> "go.Figure":
        """Candlestick chart with optional volume."""
        if not HAS_PLOTLY:
            return None

        rows = 2 if show_volume else 1
        heights = [0.75, 0.25] if show_volume else [1.0]

        fig = make_subplots(
            rows=rows, cols=1, shared_xaxes=True,
            row_heights=heights, vertical_spacing=0.03,
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            increasing_line_color=cls.COLORS["green"],
            decreasing_line_color=cls.COLORS["red"],
            name="OHLC",
        ), row=1, col=1)

        # Volume bars
        if show_volume and "volume" in df.columns:
            colors = [
                cls.COLORS["green"] if c >= o else cls.COLORS["red"]
                for c, o in zip(df["close"], df["open"])
            ]
            fig.add_trace(go.Bar(
                x=df.index, y=df["volume"],
                marker_color=colors, opacity=0.5, name="Volume",
            ), row=2, col=1)

        fig.update_layout(
            title=title, height=500,
            xaxis_rangeslider_visible=False,
            **cls.TEMPLATE,
        )
        fig.update_xaxes(gridcolor=cls.COLORS["grid"])
        fig.update_yaxes(gridcolor=cls.COLORS["grid"])

        return fig

    @classmethod
    def pnl_waterfall(
        cls,
        daily_pnl: Dict[str, float],
        title: str = "Daily P&L",
    ) -> "go.Figure":
        """Daily P&L waterfall chart."""
        if not HAS_PLOTLY:
            return None

        dates = list(daily_pnl.keys())
        values = list(daily_pnl.values())
        colors = [cls.COLORS["green"] if v >= 0 else cls.COLORS["red"] for v in values]

        fig = go.Figure(go.Bar(
            x=dates, y=values,
            marker_color=colors,
            text=[f"₹{v:+,.0f}" for v in values],
            textposition="outside",
        ))

        fig.update_layout(
            title=title, height=400,
            yaxis_title="P&L (₹)",
            **cls.TEMPLATE,
        )
        fig.update_xaxes(gridcolor=cls.COLORS["grid"])
        fig.update_yaxes(gridcolor=cls.COLORS["grid"])

        return fig

    @classmethod
    def sector_exposure(
        cls,
        sectors: Dict[str, float],
        title: str = "Sector Exposure",
    ) -> "go.Figure":
        """Sector allocation pie chart."""
        if not HAS_PLOTLY:
            return None

        palette = [
            "#4A9EFF", "#00D26A", "#FFD700", "#FF4444",
            "#7C3AED", "#FF6B35", "#00BCD4", "#E91E63",
            "#8BC34A", "#FF9800", "#9C27B0", "#607D8B",
        ]

        fig = go.Figure(go.Pie(
            labels=list(sectors.keys()),
            values=list(sectors.values()),
            marker=dict(colors=palette[:len(sectors)]),
            textinfo="label+percent",
            hole=0.4,
        ))

        fig.update_layout(
            title=title, height=400,
            **cls.TEMPLATE,
        )

        return fig

    @classmethod
    def metrics_cards(cls, metrics: Dict[str, Any]) -> str:
        """Generate HTML metrics cards for Streamlit."""
        cards = []
        for label, value in metrics.items():
            if isinstance(value, float):
                color = cls.COLORS["green"] if value >= 0 else cls.COLORS["red"]
                display = f"{value:+,.2f}"
            else:
                color = cls.COLORS["blue"]
                display = str(value)

            cards.append(f"""
            <div style="background:{cls.COLORS['card']};
                        padding:16px; border-radius:12px;
                        border-left:4px solid {color};
                        text-align:center;">
                <div style="color:{cls.COLORS['text']};
                            font-size:12px; opacity:0.7;">{label}</div>
                <div style="color:{color};
                            font-size:24px; font-weight:700;
                            margin-top:4px;">{display}</div>
            </div>
            """)

        return cards
