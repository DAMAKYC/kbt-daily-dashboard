import streamlit as st
import pandas as pd
import numpy as np
from utils.data_loader import load_data, validate_csv, append_csv
from utils.acwr import calc_all_acwr, acwr_trend
from utils.metrics import (
    get_today_summary, get_benchmarks,
    get_daily_stacked, get_daily_metric,
    get_weekly_metric, get_period_totals,
    LOAD_COL, EXE_COL, CHG_COL, SPRINT_COL,
    EXE_MIN_COL, CHG_MIN_COL, SC_CATS,
)
from utils.charts import acwr_gauge, daily_bar_acwr, weekly_bar, intensity_donut

st.set_page_config(
    page_title="KBT Daily Dashboard",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#111111; color:#ffffff; }
[data-testid="stSidebar"] { background:#0a0a0a; }
[data-testid="stSidebar"] * { color:#888 !important; }
.card {
  background:#1c1c1c; border-radius:6px;
  padding:12px 10px; margin-bottom:6px;
  border:1px solid #2e2e2e;
}
.card-title {
  font-size:0.62rem; color:#666;
  letter-spacing:0.18em; text-transform:uppercase;
  text-align:center; margin-bottom:6px;
}
.big-num { font-size:2rem; font-weight:800; line-height:1.1; text-align:center; }
.bench-row {
  display:flex; justify-content:space-around;
  margin:6px 0 2px; gap:4px;
}
.bench-item { text-align:center; }
.bench-val { font-size:0.82rem; font-weight:600; color:#dddddd; }
.bench-lbl { font-size:0.55rem; color:#555; text-transform:uppercase; letter-spacing:0.1em; }
.pct-num { font-size:0.78rem; color:#aaa; text-align:center; margin-top:2px; }
.pct-bar-bg {
  background:#333; border-radius:3px;
  height:7px; margin-top:4px; overflow:hidden;
}
.section-hdr {
  font-size:0.68rem; color:#777; letter-spacing:0.22em;
  text-transform:uppercase; padding:4px 0;
  border-bottom:1px solid #333; margin:14px 0 8px;
  font-weight:600;
}
.acwr-side-block { background:#1c1c1c; border-radius:6px; padding:10px; border:1px solid #2e2e2e; }
h1,h2,h3,h4 { color:#f0f0f0 !important; }
.stDataFrame { background:#1a1a1a !important; }
div[data-testid="stHorizontalBlock"] { gap:8px; }
</style>
""", unsafe_allow_html=True)


def fmt(v, d=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if d == 0:
        return f"{int(round(v)):,}"
    return f"{v:,.{d}f}"


def pct_bar(pct, color):
    p = min(100, max(0, float(pct or 0)))
    return (f'<div class="pct-bar-bg">'
            f'<div style="width:{p:.0f}%;background:{color};height:6px;border-radius:3px"></div>'
            f'</div>')


def volume_card(label, today_val, bench, color):
    pct = (today_val / bench["MAX"] * 100) if bench["MAX"] > 0 else 0
    return f"""
<div class="card">
  <div class="card-title">{label}</div>
  <div class="big-num" style="color:{color}">{fmt(today_val)}</div>
  <div class="bench-row">
    <div class="bench-item"><div class="bench-val">{fmt(bench['MAX'])}</div><div class="bench-lbl">MAX</div></div>
    <div class="bench-item"><div class="bench-val">{fmt(bench['GAME'])}</div><div class="bench-lbl">GAME</div></div>
    <div class="bench-item"><div class="bench-val">{fmt(bench['PRAC'])}</div><div class="bench-lbl">PRAC</div></div>
  </div>
  <div class="pct-num">{pct:.0f}%</div>
  {pct_bar(pct, color)}
</div>"""


def density_card(label, today_val, bench, color):
    pct = (today_val / bench["MAX"] * 100) if bench["MAX"] > 0 else 0
    return f"""
<div class="card">
  <div class="card-title">{label}</div>
  <div class="big-num" style="color:{color}">{fmt(today_val, 1)}</div>
  <div class="bench-row">
    <div class="bench-item"><div class="bench-val">{fmt(bench['MAX'],1)}</div><div class="bench-lbl">MAX</div></div>
    <div class="bench-item"><div class="bench-val">{fmt(bench['GAME'],1)}</div><div class="bench-lbl">GAME</div></div>
    <div class="bench-item"><div class="bench-val">{fmt(bench['PRAC'],1)}</div><div class="bench-lbl">PRAC</div></div>
  </div>
  <div class="pct-num">{pct:.0f}%</div>
  {pct_bar(pct, color)}
</div>"""


@st.cache_data(ttl=60)
def get_data():
    return load_data()


df = get_data()

# ── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏀 KBT Daily")
    st.divider()
    players = sorted(df["Name"].dropna().unique())
    player = st.selectbox("選手", players)

    avail = sorted(
        pd.to_datetime(df[df["Name"] == player]["Date"]).dt.normalize().unique(),
        reverse=True,
    )
    date = st.selectbox("日付", avail, format_func=lambda d: d.strftime("%Y-%m-%d"))
    date_str = pd.Timestamp(date).strftime("%Y-%m-%d")

    st.divider()
    st.markdown("**CSV追記**")
    f = st.file_uploader("RAWDATA形式", type=["csv"], label_visibility="collapsed")
    if f:
        new_df = pd.read_csv(f)
        ok, err = validate_csv(new_df)
        if not ok:
            st.error(err)
        elif st.button("追記する"):
            added, skipped = append_csv(new_df)
            st.success(f"追記 {added}行 / スキップ {skipped}行")
            st.cache_data.clear()
            st.rerun()


# ── Data ─────────────────────────────────────────────────
today = get_today_summary(df, player, date_str)
if today is None:
    st.warning("データがありません")
    st.stop()

bench = get_benchmarks(df, player)
acwr_all = calc_all_acwr(df, player, date_str)

load_trend   = acwr_trend(df, player, date_str, LOAD_COL, days=30)
exe_trend    = acwr_trend(df, player, date_str, EXE_COL, days=30)
chg_trend    = acwr_trend(df, player, date_str, CHG_COL, days=30)
sprint_trend = acwr_trend(df, player, date_str, SPRINT_COL, days=30)

daily_stack  = get_daily_stacked(df, player, date_str, days=30)
daily_exe    = get_daily_metric(df, player, EXE_COL, date_str, days=30)
daily_chg    = get_daily_metric(df, player, CHG_COL, date_str, days=30)
daily_sprint = get_daily_metric(df, player, SPRINT_COL, date_str, days=30)
daily_sc     = get_daily_metric(df, player, LOAD_COL, date_str, days=30, cat_filter=SC_CATS)

weekly_load   = get_weekly_metric(df, player, LOAD_COL)
weekly_exe    = get_weekly_metric(df, player, EXE_COL)
weekly_chg    = get_weekly_metric(df, player, CHG_COL)
weekly_sprint = get_weekly_metric(df, player, SPRINT_COL)
weekly_sc     = get_weekly_metric(df, player, LOAD_COL, cat_filter=SC_CATS)

load_m,   load_w   = get_period_totals(df, player, date_str, LOAD_COL)
exe_m,    exe_w    = get_period_totals(df, player, date_str, EXE_COL)
chg_m,    chg_w    = get_period_totals(df, player, date_str, CHG_COL)
sprint_m, sprint_w = get_period_totals(df, player, date_str, SPRINT_COL)


# ── HEADER ───────────────────────────────────────────────
st.markdown(f"""
<div style="background:#1a1a1a;border-radius:10px;padding:14px 20px;
            border-left:4px solid #85063B;margin-bottom:12px;
            display:flex;justify-content:space-between;align-items:center">
  <div>
    <div style="font-size:1.4rem;font-weight:800;color:#fff">{player}</div>
    <div style="font-size:0.85rem;color:#888;margin-top:2px">
      {date_str} &nbsp;·&nbsp;
      <span style="background:#85063B;color:#fff;padding:2px 8px;
                   border-radius:4px;font-size:0.75rem">{today['primary_cat']}</span>
      &nbsp; vs {today['vs']}
    </div>
  </div>
  <div style="text-align:right;color:#333;font-size:0.7rem;letter-spacing:0.15em">
    KAWASAKI BRAVE THUNDERS<br>KINEXON DATA
  </div>
</div>
""", unsafe_allow_html=True)


# ── ROW 1: ACWR gauge │ Daily LOAD │ Week LOAD ───────────
c1, c2, c3 = st.columns([1, 2, 2])

with c1:
    load_acwr = acwr_all["LOAD"]["acwr"] or 0
    st.markdown('<div class="card-title" style="margin-top:8px">ACWR (LOAD)</div>', unsafe_allow_html=True)
    st.plotly_chart(acwr_gauge(load_acwr, height=140), use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:4px">
      <div class="card" style="padding:8px;text-align:center">
        <div class="bench-lbl">MONTH</div>
        <div style="font-size:1rem;font-weight:700;color:#ccc">{fmt(load_m)}</div>
      </div>
      <div style="background:#1a1a1a;border:1px solid #85063B;border-radius:8px;
                  padding:8px;text-align:center">
        <div class="bench-lbl">WEEK</div>
        <div style="font-size:1rem;font-weight:700;color:#ccc">{fmt(load_w)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.plotly_chart(
        daily_bar_acwr(daily_stack, load_trend, "LOAD", stacked=True),
        use_container_width=True, config={"displayModeBar": False},
    )

with c3:
    st.plotly_chart(
        weekly_bar(weekly_load, "LOAD", "#85063B"),
        use_container_width=True, config={"displayModeBar": False},
    )


# ── ROW 2: VOLUME │ DENSITY │ INTENSITY ──────────────────
st.markdown('<div class="section-hdr">VOLUME &nbsp;<span style="color:#ccc;font-size:0.85rem">' + fmt(today["MIN"], 1) + '</span> min</div>', unsafe_allow_html=True)

v1, v2, v3, v4, gap, d1, d2, gap2, i1 = st.columns([1.4, 1.4, 1.4, 1.4, 0.1, 1.3, 1.3, 0.1, 1.4])

with v1:
    st.markdown(volume_card("LOAD", today["LOAD"], bench["LOAD"], "#cc3344"), unsafe_allow_html=True)
with v2:
    st.markdown(volume_card("EXERTION", today["EXERTION"], bench["EXERTION"], "#c8a400"), unsafe_allow_html=True)
with v3:
    st.markdown(volume_card("CHANGES", today["CHANGE"], bench["CHANGE"], "#ff7722"), unsafe_allow_html=True)
with v4:
    st.markdown(volume_card("SPRINT", today["SPRINT"], bench["SPRINT"], "#dd2200"), unsafe_allow_html=True)

with d1:
    st.markdown('<div class="card-title" style="margin-bottom:0">DENSITY</div>', unsafe_allow_html=True)
    st.markdown(density_card("EXE/MIN", today["EXE_MIN"], bench["EXE_MIN"], "#c8a400"), unsafe_allow_html=True)
with d2:
    st.markdown('<div style="margin-top:18px"></div>', unsafe_allow_html=True)
    st.markdown(density_card("CHG/MIN", today["CHG_MIN"], bench["CHG_MIN"], "#ff7722"), unsafe_allow_html=True)

with i1:
    st.markdown('<div class="card-title">INTENSITY</div>', unsafe_allow_html=True)
    exe_g = bench["EXE_MIN"]["GAME"]
    chg_g = bench["CHG_MIN"]["GAME"]
    load_g = bench["LOAD"]["GAME"]
    pcts = []
    if exe_g > 0:
        pcts.append(today["EXE_MIN"] / exe_g * 100)
    if chg_g > 0:
        pcts.append(today["CHG_MIN"] / chg_g * 100)
    intensity_pct = np.mean(pcts) if pcts else 0
    vol_pct = (today["LOAD"] / load_g * 100) if load_g > 0 else 0
    st.plotly_chart(intensity_donut(intensity_pct), use_container_width=True, config={"displayModeBar": False})
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;text-align:center;margin-top:2px">
      <div><div class="bench-lbl">VOL</div><div style="font-size:0.85rem;color:#ccc">{vol_pct:.0f}%</div></div>
      <div><div class="bench-lbl">DENS</div><div style="font-size:0.85rem;color:#ccc">{intensity_pct:.0f}%</div></div>
      <div><div class="bench-lbl">min</div><div style="font-size:0.85rem;color:#ccc">{fmt(today['MIN'])}</div></div>
    </div>
    """, unsafe_allow_html=True)


# ── ROW 3: TOT / TODAY / MAX / GAME / PRAC Table ─────────
st.markdown('<div class="section-hdr">COMPARISON</div>', unsafe_allow_html=True)

comp_cols = ["", "TOT (Month)", "TODAY", "MAX", "GAME", "PRAC"]
rows = [
    ["LOAD",   fmt(load_m),   fmt(today["LOAD"]),      fmt(bench["LOAD"]["MAX"]),      fmt(bench["LOAD"]["GAME"]),      fmt(bench["LOAD"]["PRAC"])],
    ["EXE",    fmt(exe_m),    fmt(today["EXERTION"]),   fmt(bench["EXERTION"]["MAX"]),  fmt(bench["EXERTION"]["GAME"]),  fmt(bench["EXERTION"]["PRAC"])],
    ["CHG",    fmt(chg_m),    fmt(today["CHANGE"]),     fmt(bench["CHANGE"]["MAX"]),    fmt(bench["CHANGE"]["GAME"]),    fmt(bench["CHANGE"]["PRAC"])],
    ["SPRT",   fmt(sprint_m), fmt(today["SPRINT"]),     fmt(bench["SPRINT"]["MAX"]),    fmt(bench["SPRINT"]["GAME"]),    fmt(bench["SPRINT"]["PRAC"])],
]
comp_df = pd.DataFrame(rows, columns=comp_cols).set_index("")
st.dataframe(
    comp_df.style.set_properties(**{"text-align": "center"})
           .set_table_styles([{"selector": "th", "props": [("color", "#666"), ("font-size", "0.75rem")]}]),
    use_container_width=True,
)


# ── PER-METRIC BLOCKS ─────────────────────────────────────
def metric_block(label, daily_df, trend_df_, weekly_df, acwr_val, month_tot, week_tot, color):
    st.markdown(f'<div class="section-hdr">{label}</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns([2, 2, 1])

    with m1:
        st.plotly_chart(
            daily_bar_acwr(daily_df, trend_df_, label, stacked=False, color=color),
            use_container_width=True, config={"displayModeBar": False},
        )
    with m2:
        st.plotly_chart(
            weekly_bar(weekly_df, label, color),
            use_container_width=True, config={"displayModeBar": False},
        )
    with m3:
        st.markdown('<div class="acwr-side-block">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-title">ACWR</div>', unsafe_allow_html=True)
        st.plotly_chart(acwr_gauge(acwr_val or 0, height=120), use_container_width=True, config={"displayModeBar": False})
        st.markdown(f"""
        <div style="text-align:center;margin-top:2px">
          <div class="bench-lbl">MONTH</div>
          <div style="font-size:1rem;font-weight:600;color:#ccc">{fmt(month_tot)}</div>
        </div>
        <div style="text-align:center;border:1px solid {color};border-radius:4px;
                    padding:4px;margin-top:6px">
          <div class="bench-lbl">WEEK</div>
          <div style="font-size:1rem;font-weight:600;color:#ccc">{fmt(week_tot)}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


metric_block("EXERTION", daily_exe,    exe_trend,    weekly_exe,    acwr_all["EXERTION"]["acwr"], exe_m,    exe_w,    "#c8a400")
metric_block("CHANGES",  daily_chg,    chg_trend,    weekly_chg,    acwr_all["CHANGE"]["acwr"],   chg_m,    chg_w,    "#ff7722")
metric_block("SPRINT",   daily_sprint, sprint_trend, weekly_sprint, acwr_all["SPRINT"]["acwr"],   sprint_m, sprint_w, "#dd2200")
metric_block("SC",       daily_sc,     None,         weekly_sc,     None,                         0,        0,        "#777777")
metric_block("LOAD",     get_daily_metric(df, player, LOAD_COL, date_str, days=30),
             load_trend, weekly_load, acwr_all["LOAD"]["acwr"], load_m, load_w, "#85063B")
