"""Tema Plotly unificado e helpers de gráfico."""

from __future__ import annotations

import plotly.graph_objects as go

from ui.theme import BRAND, NEG, POS, WARN

# Paleta categórica: espresso, teal, âmbar, ardósia, argila, oliva.
CATEGORICAL = ["#A2764F", "#12907A", "#C79A3E", "#6C7F93", "#BE6A4A", "#7E9152"]

# Escalas contínuas derivadas da paleta (claro -> saturado).
SEQ_BRAND = ["#E8D6C4", "#D0AF8D", "#B58A63", "#96694A", "#7A5236"]
SEQ_POS = ["#A9DBCD", "#6FC5AE", "#3AAA8F", "#1B9077", "#0E7C66"]
SEQ_NEG = ["#F3B9B2", "#E58C82", "#D66658", "#C4463A", "#AE2E23"]

# Neutros de meio-tom: legíveis sobre fundo claro e escuro.
AXIS = "#8A93A0"
GRID = "rgba(138, 147, 160, 0.26)"
TRANSPARENT = "rgba(0,0,0,0)"

FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", '
    "Arial, sans-serif"
)


def style_fig(fig: go.Figure, height: int = 360, legend: bool = False) -> go.Figure:
    """Aplica o tema do ERP a uma figura Plotly."""
    fig.update_layout(
        height=height,
        showlegend=legend,
        margin=dict(l=8, r=8, t=34, b=8),
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=dict(family=FONT, size=12, color=AXIS),
        title=dict(
            font=dict(size=13, color=AXIS, family=FONT),
            x=0,
            xanchor="left",
            y=0.97,
        ),
        hoverlabel=dict(
            bgcolor="#22262E",
            bordercolor=GRID,
            font=dict(color="#F2F4F7", family=FONT, size=12),
        ),
        colorway=CATEGORICAL,
        separators=",.",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=GRID,
        ticks="outside",
        tickcolor=GRID,
        ticklen=4,
        zeroline=False,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        griddash="dot",
        linecolor=TRANSPARENT,
        zeroline=False,
    )
    fig.update_coloraxes(showscale=False)
    return fig


def area_line(x, y, name: str, title: str, color: str = "#A2764F") -> go.Figure:
    """Série temporal com preenchimento suave."""
    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            name=name,
            mode="lines+markers",
            line=dict(color=color, width=2.4, shape="spline", smoothing=0.5),
            marker=dict(size=6, color=color),
            fill="tozeroy",
            fillcolor="rgba(162, 118, 79, 0.14)",
        )
    )
    fig.update_layout(title=title)
    fig.update_xaxes(tickformat="%d/%m", hoverformat="%d/%m/%Y")
    return style_fig(fig)


def cashflow(x, entradas, saidas, acumulado, title: str) -> go.Figure:
    """Entradas x saídas em barras + saldo acumulado em linha secundária."""
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Entradas", x=x, y=entradas, marker_color=POS))
    fig.add_trace(go.Bar(name="Saídas", x=x, y=saidas, marker_color=NEG))
    fig.add_trace(
        go.Scatter(
            name="Saldo acumulado",
            x=x,
            y=acumulado,
            mode="lines+markers",
            line=dict(color="#A2764F", width=2.4),
            marker=dict(size=5),
            yaxis="y2",
        )
    )
    fig.update_layout(
        title=title,
        barmode="group",
        bargap=0.28,
        hovermode="x unified",
        yaxis2=dict(overlaying="y", side="right", showgrid=False, tickfont=dict(color="#A2764F")),
    )
    fig.update_xaxes(tickformat="%d/%m", hoverformat="%d/%m/%Y")
    return style_fig(fig, height=420, legend=True)


def donut(labels, values, title: str) -> go.Figure:
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.58,
            marker=dict(colors=CATEGORICAL, line=dict(color=GRID, width=1)),
            textposition="outside",
            textinfo="label+percent",
            sort=True,
        )
    )
    fig.update_layout(title=title)
    return style_fig(fig, height=380)


def hbar(labels, values, title: str, color: str = "#A2764F") -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=color,
            text=values,
            textposition="auto",
            textfont=dict(size=11),
        )
    )
    fig.update_layout(title=title, yaxis=dict(categoryorder="total ascending"))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, griddash="dot")
    fig.update_yaxes(showgrid=False)
    return style_fig(fig)


def vbar(labels, values, title: str, color: str = "#A2764F") -> go.Figure:
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=color))
    fig.update_layout(title=title, bargap=0.35)
    return style_fig(fig)


__all__ = [
    "CATEGORICAL", "SEQ_BRAND", "SEQ_POS", "SEQ_NEG", "AXIS", "GRID",
    "style_fig", "area_line", "cashflow", "donut", "hbar", "vbar",
    "BRAND", "POS", "NEG", "WARN",
]
