"""Chart specification -> Plotly figure. The analysis engine stays UI-agnostic."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .text import humanize


ACCENT = "#8b7cff"
ACCENT_2 = "#22d3ee"
GRID = "#1e293b"
PAPER = "rgba(0,0,0,0)"
FONT = "#cbd5e1"


def _style(fig: go.Figure, title: str | None = None, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=dict(family="Inter, sans-serif", color=FONT, size=12),
        title=dict(
            text=title or "",
            font=dict(size=14, color="#f8fafc", family="Inter, sans-serif"),
            x=0,
            xanchor="left",
            pad=dict(l=4, t=4, b=8),
        ),
        margin=dict(l=18, r=18, t=48 if title else 20, b=18),
        height=height,
        hoverlabel=dict(bgcolor="#111827", font_size=12, font_family="Inter"),
        colorway=[ACCENT, ACCENT_2, "#f472b6", "#fbbf24", "#34d399", "#60a5fa"],
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(size=11))
    return fig


def style_figure(fig: go.Figure, title: str | None = None, height: int = 380) -> go.Figure:
    return _style(fig, title=title, height=height)


def _short_labels(series: pd.Series, max_len: int = 26) -> pd.Series:
    return series.astype(str).map(lambda v: v if len(v) <= max_len else v[: max_len - 1] + "…")


def build_figure(
    chart: dict[str, Any] | None,
    table: pd.DataFrame | None,
    chart_override: str | None = None,
) -> go.Figure | None:
    if not chart:
        return None
    kind = chart_override or chart.get("type", "none")
    title = chart.get("title") or ""

    if kind in ("none", "kpi", "table"):
        return None

    if kind == "box":
        values = chart.get("values") or []
        if not values and table is not None and chart.get("y") in table.columns:
            values = table[chart["y"]].tolist()
        if not values:
            return None
        metric = chart.get("y", "Value")
        fig = go.Figure(go.Box(y=values, name=humanize(metric), marker_color=ACCENT, boxpoints="outliers"))
        fig.update_layout(yaxis_title=humanize(metric))
        return _style(fig, title)

    if chart.get("data"):
        try:
            table = pd.DataFrame(chart["data"])
        except Exception:
            pass

    if table is None or table.empty:
        return None

    if kind == "line":
        x, y = chart.get("x"), chart.get("y")
        if x not in table.columns or y not in table.columns:
            return None
        fig = px.line(table, x=x, y=y, markers=len(table) <= 60)
        fig.update_traces(line=dict(color=ACCENT, width=2.4), marker=dict(size=5, color=ACCENT_2))
        fig.update_layout(xaxis_title="", yaxis_title=humanize(y), hovermode="x unified")
        fig.update_yaxes(rangemode="tozero")
        return _style(fig, title)

    if kind in ("bar", "histogram"):
        x, y = chart.get("x"), chart.get("y")
        if x not in table.columns or y not in table.columns:
            return None
        plot_df = table.copy()
        orientation = chart.get("orientation", "v")
        if kind == "histogram":
            orientation = "v"
        if orientation == "h":
            plot_df = plot_df.iloc[::-1]
            fig = px.bar(plot_df, x=y, y=x, orientation="h")
            fig.update_traces(marker_color=ACCENT, marker_line_width=0, hovertemplate="%{y}<br>%{x:,.4s}<extra></extra>")
            fig.update_layout(xaxis_title=humanize(y), yaxis_title="")
            fig.update_xaxes(rangemode="tozero")
        else:
            label_col = x
            if plot_df[x].astype(str).str.len().max() > 24:
                plot_df[x] = _short_labels(plot_df[x])
            fig = px.bar(plot_df, x=x, y=y)
            fig.update_traces(
                marker_color=ACCENT,
                marker_line_width=0,
                hovertemplate=f"%{{x}}<br>{humanize(y)}: %{{y:,.4s}}<extra></extra>",
            )
            fig.update_layout(xaxis_title="", yaxis_title=humanize(y))
            fig.update_yaxes(rangemode="tozero")
            _ = label_col
        fig.update_xaxes(tickangle=-25 if orientation == "h" or len(table) > 8 else 0)
        return _style(fig, title)

    if kind == "pie":
        x, y = chart.get("x"), chart.get("y")
        if x not in table.columns or y not in table.columns:
            return None
        fig = px.pie(table.head(8), names=x, values=y, hole=0.55)
        fig.update_traces(textposition="inside", textinfo="percent", marker=dict(line=dict(color="#0b0f19", width=2)))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1, font=dict(size=10)))
        return _style(fig, title)

    if kind == "scatter":
        x, y = chart.get("x"), chart.get("y")
        if x not in table.columns or y not in table.columns:
            return None
        plot_df = table.rename(columns={x: chart.get("x_label", x), y: chart.get("y_label", y)})
        nx, ny = chart.get("x_label", x), chart.get("y_label", y)
        fig = px.scatter(plot_df, x=nx, y=ny, opacity=0.55)
        fig.update_traces(marker=dict(size=5, color=ACCENT_2, line=dict(width=0)))
        fig.update_layout(xaxis_title=nx, yaxis_title=ny)
        return _style(fig, title)

    return None


def alt_chart_types(chart: dict[str, Any] | None) -> list[str]:
    if not chart:
        return []
    kind = chart.get("type")
    if kind == "bar":
        return ["bar", "pie", "line"]
    if kind == "line":
        return ["line", "bar"]
    return []
