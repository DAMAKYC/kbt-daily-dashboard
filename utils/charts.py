import plotly.graph_objects as go
import numpy as np

BG = "#0e0e0e"
CARD = "#1c1c1c"
CARD2 = "#252525"
GRID = "#2a2a2a"

CAT_COLORS = {
    "SC": "#777777",
    "Individual": "#c8a400",
    "MAIN": "#85063B",
    "GAME": "#dd2200",
    "Reha": "#4488bb",
}


def _acwr_color(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "#888888"
    if v < 0.8:
        return "#facc15"
    if v <= 1.3:
        return "#4ade80"
    return "#f87171"


def acwr_gauge(value, height=150):
    v = value if (value is not None and not np.isnan(value)) else 0
    color = _acwr_color(v)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        number={"font": {"size": 28, "color": color, "family": "monospace"}, "valueformat": ".2f"},
        gauge={
            "axis": {
                "range": [0, 2],
                "tickvals": [0.3, 0.8, 1.3],
                "ticktext": ["0.3", "0.8", "1.3"],
                "tickfont": {"size": 9, "color": "#555"},
                "tickwidth": 1, "tickcolor": "#444",
            },
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": CARD,
            "borderwidth": 0,
            "steps": [
                {"range": [0, 0.8], "color": "#2a2400"},
                {"range": [0.8, 1.3], "color": "#0a2010"},
                {"range": [1.3, 2.0], "color": "#2a0808"},
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font={"color": "#ccc"},
        margin=dict(t=10, b=0, l=10, r=10),
        height=height,
    )
    return fig


def daily_bar_acwr(daily_df, acwr_df, title, stacked=False, color="#85063B"):
    fig = go.Figure()

    if stacked:
        cats_present = [c for c in CAT_COLORS if c in daily_df.columns and daily_df[c].sum() > 0]
        total = sum(daily_df[c] for c in cats_present) if cats_present else None
        for i, cat in enumerate(cats_present):
            is_top = (i == len(cats_present) - 1)
            fig.add_trace(go.Bar(
                x=daily_df["Date_norm"], y=daily_df[cat],
                name=cat, marker_color=CAT_COLORS[cat], yaxis="y1",
                text=[f"{int(v)}" if v > 0 else "" for v in (total if is_top else daily_df[cat])],
                textposition="outside" if is_top else "none",
                textfont=dict(size=7, color="#888"),
            ))
    else:
        fig.add_trace(go.Bar(
            x=daily_df["Date"], y=daily_df["value"],
            marker_color=color, name=title, yaxis="y1",
            showlegend=False,
            text=[f"{int(v)}" if v > 0 else "" for v in daily_df["value"]],
            textposition="outside",
            textfont=dict(size=7, color="#888"),
        ))

    if acwr_df is not None and len(acwr_df) > 0:
        fig.add_trace(go.Scatter(
            x=acwr_df["Date"], y=acwr_df["acwr"],
            mode="lines",
            line=dict(color="#ff8800", width=1.5),
            name="AC", yaxis="y2",
        ))

    fig.add_shape(type="line", x0=0, x1=1, xref="paper",
                  y0=1.3, y1=1.3, yref="y2",
                  line=dict(color="#f87171", width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=1, xref="paper",
                  y0=0.8, y1=0.8, yref="y2",
                  line=dict(color="#facc15", width=1, dash="dot"))
    fig.add_shape(type="line", x0=0, x1=1, xref="paper",
                  y0=0.3, y1=0.3, yref="y2",
                  line=dict(color="#4488bb", width=0.5, dash="dot"))

    fig.update_layout(
        barmode="stack",
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color="#777", size=9),
        xaxis=dict(showgrid=False, tickformat="%m/%d", tickfont=dict(size=8), tickcolor="#444"),
        yaxis=dict(showgrid=True, gridcolor=GRID, tickfont=dict(size=8), tickcolor="#444", autorange=True),
        yaxis2=dict(
            overlaying="y", side="right",
            range=[0, 2.2],
            tickvals=[0.8, 1.3],
            showgrid=False,
            tickfont=dict(size=8, color="#666"),
        ),
        legend=dict(orientation="h", x=0, y=1.08, font=dict(size=8), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=30, b=20, l=35, r=35),
        height=190,
        title=dict(text=f"<b>{title}</b>", font=dict(size=11, color="#aaa"), x=0.5),
    )
    return fig


def weekly_bar(weekly_df, title, color="#85063B"):
    if weekly_df.empty:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor=CARD, plot_bgcolor=CARD, height=190)
        return fig

    fig = go.Figure(go.Bar(
        x=weekly_df["Week"], y=weekly_df["value"],
        marker_color=color, showlegend=False,
    ))
    fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(color="#777", size=9),
        xaxis=dict(showgrid=False, title="Week", tickfont=dict(size=8)),
        yaxis=dict(showgrid=True, gridcolor=GRID, tickfont=dict(size=8)),
        margin=dict(t=30, b=20, l=35, r=10),
        height=190,
        title=dict(text=f"<b>WEEK {title}</b>", font=dict(size=11, color="#aaa"), x=0.5),
    )
    return fig


def intensity_donut(pct):
    p = min(100, max(0, pct or 0))
    color = "#facc15" if p < 60 else ("#4ade80" if p < 85 else "#f87171")
    fig = go.Figure(go.Pie(
        values=[p, 100 - p],
        hole=0.68,
        marker_colors=[color, CARD2],
        showlegend=False, textinfo="none", sort=False,
        direction="clockwise", rotation=90,
    ))
    fig.add_annotation(
        text=f"<b>{p:.0f}%</b>",
        x=0.5, y=0.5,
        font=dict(size=24, color=color),
        showarrow=False,
    )
    fig.update_layout(
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        margin=dict(t=5, b=5, l=5, r=5),
        height=130,
    )
    return fig
