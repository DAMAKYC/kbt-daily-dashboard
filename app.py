import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data_loader import load_data, validate_csv, append_csv
from utils.acwr import calc_all_acwr, acwr_trend, session_summary

st.set_page_config(
    page_title="KBT Daily Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0e0e0e; color: #f0f0f0; }
  [data-testid="stSidebar"] { background: #1a1a1a; }
  .metric-card {
    background: #1e1e1e;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 20px 16px;
    text-align: center;
  }
  .metric-label { font-size: 0.75rem; color: #888; letter-spacing: 0.1em; text-transform: uppercase; }
  .metric-value { font-size: 2.2rem; font-weight: 700; margin: 6px 0 2px; }
  .metric-sub { font-size: 0.8rem; color: #aaa; }
  .acwr-green { color: #4ade80; }
  .acwr-yellow { color: #facc15; }
  .acwr-red { color: #f87171; }
  .session-badge {
    display: inline-block;
    background: #85063B;
    color: #fff;
    border-radius: 6px;
    padding: 3px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.05em;
  }
  h1, h2, h3 { color: #f0f0f0 !important; }
  .stSelectbox label, .stDateInput label { color: #ccc !important; }
</style>
""", unsafe_allow_html=True)


def acwr_color_class(v):
    if v is None or np.isnan(v):
        return "metric-sub"
    if v < 0.8:
        return "acwr-yellow"
    if v <= 1.3:
        return "acwr-green"
    return "acwr-red"


def acwr_zone_label(v):
    if v is None or np.isnan(v):
        return "—"
    if v < 0.8:
        return "⚠ Under"
    if v <= 1.3:
        return "✓ Optimal"
    return "⚠ Over"


@st.cache_data(ttl=60)
def get_data():
    return load_data()


df = get_data()

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏀 KBT Daily")
    st.divider()

    players = sorted(df["Name"].dropna().unique())
    player = st.selectbox("選手", players)

    player_df = df[df["Name"] == player]
    available_dates = sorted(
        pd.to_datetime(player_df["Date"]).dt.normalize().unique(), reverse=True
    )
    available_dates = [d for d in available_dates if d is not pd.NaT]

    date = st.selectbox(
        "日付",
        available_dates,
        format_func=lambda d: d.strftime("%Y-%m-%d"),
    )
    date_str = pd.Timestamp(date).strftime("%Y-%m-%d")

    st.divider()
    st.markdown("### CSVアップロード")
    uploaded = st.file_uploader("新データ追記（RAWDATA形式）", type=["csv"])
    if uploaded:
        try:
            new_df = pd.read_csv(uploaded)
            ok, err = validate_csv(new_df)
            if not ok:
                st.error(err)
            else:
                if st.button("追記する"):
                    added, skipped = append_csv(new_df)
                    st.success(f"追記: {added}行 / スキップ: {skipped}行")
                    st.cache_data.clear()
                    st.rerun()
        except Exception as e:
            st.error(f"読み込みエラー: {e}")

# ── Main ─────────────────────────────────────────────────
session = session_summary(df, player, date_str)

if session.empty:
    st.warning(f"{player} / {date_str} のデータがありません。")
    st.stop()

category = session["CATEGORY"].iloc[0] if "CATEGORY" in session.columns else "—"
vs = session["VS"].iloc[0] if "VS" in session.columns else "—"

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"# {player}")
    st.markdown(f"**{date_str}** &nbsp; <span class='session-badge'>{category}</span> &nbsp; vs {vs}", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<div style='text-align:right;color:#555;padding-top:24px;font-size:0.8rem;'>KBT Conditioning</div>", unsafe_allow_html=True)

st.divider()

# ── ACWR Cards ───────────────────────────────────────────
acwr_data = calc_all_acwr(df, player, date_str)

metrics = [
    ("LOAD", "Accumulated Acceleration Load", "au"),
    ("EXERTION", "Exertions", "reps"),
    ("CHANGE", "Changes of Orientation", "reps"),
    ("SPRINT", "SPRINT", "m"),
]

cols = st.columns(4)
for col, (key, raw_col, unit) in zip(cols, metrics):
    acwr_val = acwr_data[key]["acwr"]
    today_val = session[raw_col].sum() if raw_col in session.columns else None
    cls = acwr_color_class(acwr_val)
    zone = acwr_zone_label(acwr_val)
    acwr_str = f"{acwr_val:.2f}" if (acwr_val is not None and not np.isnan(acwr_val)) else "—"
    today_str = f"{today_val:,.0f}" if today_val is not None and not np.isnan(today_val) else "—"

    with col:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">{key}</div>
          <div class="metric-value {cls}">{acwr_str}</div>
          <div class="metric-sub">ACWR &nbsp;·&nbsp; {zone}</div>
          <hr style="border-color:#333;margin:10px 0">
          <div style="font-size:1.3rem;font-weight:600;color:#f0f0f0">{today_str}</div>
          <div class="metric-sub">Today ({unit})</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Per-minute metrics ────────────────────────────────────
col_e, col_c = st.columns(2)
exe_min = session["Exertions / min"].mean() if "Exertions / min" in session.columns else None
chg_min = session["Changes of Orientation / min"].mean() if "Changes of Orientation / min" in session.columns else None

with col_e:
    val = f"{exe_min:.2f}" if exe_min is not None and not np.isnan(exe_min) else "—"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">EXE / min</div>
      <div class="metric-value" style="color:#c084fc">{val}</div>
    </div>""", unsafe_allow_html=True)

with col_c:
    val = f"{chg_min:.2f}" if chg_min is not None and not np.isnan(chg_min) else "—"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">CHANGE / min</div>
      <div class="metric-value" style="color:#c084fc">{val}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── ACWR Trend Chart ──────────────────────────────────────
st.markdown("### ACWR Trend (Load · 28 days)")
trend_df = acwr_trend(df, player, date_str, days=28)

fig = go.Figure()

fig.add_hrect(y0=0.8, y1=1.3, fillcolor="rgba(74,222,128,0.07)", line_width=0, annotation_text="Optimal Zone", annotation_position="top left", annotation_font_color="#4ade80")
fig.add_hline(y=1.3, line_dash="dot", line_color="#f87171", line_width=1)
fig.add_hline(y=0.8, line_dash="dot", line_color="#facc15", line_width=1)

fig.add_trace(go.Scatter(
    x=trend_df["Date"],
    y=trend_df["acwr"],
    mode="lines+markers",
    line=dict(color="#85063B", width=2.5),
    marker=dict(size=6, color="#85063B"),
    name="ACWR",
    hovertemplate="%{x|%m/%d}<br>ACWR: %{y:.2f}<extra></extra>",
))

fig.update_layout(
    paper_bgcolor="#0e0e0e",
    plot_bgcolor="#0e0e0e",
    font=dict(color="#ccc"),
    xaxis=dict(showgrid=False, tickformat="%m/%d"),
    yaxis=dict(showgrid=True, gridcolor="#222", range=[0, max(2.0, trend_df["acwr"].max() + 0.2 if not trend_df["acwr"].isna().all() else 2.0)]),
    margin=dict(t=20, b=20, l=10, r=10),
    height=280,
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

# ── Session Table ─────────────────────────────────────────
with st.expander("セッション詳細"):
    show_cols = [c for c in ["VS", "CATEGORY", "Accumulated Acceleration Load",
                              "Exertions", "Exertions / min", "Changes of Orientation",
                              "Changes of Orientation / min", "SPRINT"] if c in session.columns]
    st.dataframe(session[show_cols].reset_index(drop=True), use_container_width=True)
