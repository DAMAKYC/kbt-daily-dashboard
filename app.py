import streamlit as st
import pandas as pd
import numpy as np
from utils.data_loader import load_data, validate_csv, append_csv
from utils.acwr import calc_all_acwr, acwr_trend
from utils.metrics import (
    get_today_summary, get_benchmarks, get_game_max,
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
/* ── 全体余白削減 ── */
[data-testid="stAppViewContainer"] { background:#111111; color:#ffffff; }
[data-testid="block-container"] { padding:0.2rem 0.8rem 0 !important; }
[data-testid="stSidebar"] { background:#0a0a0a; }
[data-testid="stSidebar"] * { color:#888 !important; }
div[data-testid="stVerticalBlock"] > div { gap:0 !important; }
div[data-testid="stHorizontalBlock"] { gap:5px !important; }
div[data-testid="stPlotlyChart"] { margin-bottom:-18px; margin-top:-6px; }
.element-container { margin-bottom:0 !important; }

/* ── カード ── */
.card {
  background:#1c1c1c; border-radius:5px;
  padding:6px 7px; margin-bottom:3px;
  border:1px solid #2a2a2a;
}
.card-title {
  font-size:0.58rem; color:#555;
  letter-spacing:0.2em; text-transform:uppercase;
  text-align:center; margin-bottom:3px;
}
.big-num { font-size:1.55rem; font-weight:600; line-height:1.05; text-align:center; color:#fff; }
.bench-row { display:flex; justify-content:space-around; margin:3px 0 1px; gap:2px; }
.bench-item { text-align:center; }
.bench-val { font-size:0.72rem; font-weight:400; color:#999; }
.bench-lbl { font-size:0.48rem; color:#4a4a4a; text-transform:uppercase; letter-spacing:0.08em; }
.pct-lbl { font-size:0.78rem; font-weight:600; text-align:center; margin:2px 0 1px; }
.pct-bar-bg { background:#252525; border-radius:2px; height:5px; overflow:hidden; }

/* ── セクションヘッダー ── */
.sec {
  font-size:0.6rem; color:#555; letter-spacing:0.22em;
  text-transform:uppercase; padding:1px 0;
  border-bottom:1px solid #252525; margin:4px 0 3px;
  font-weight:700;
}

/* ── ACWRカード ── */
.acwr-card {
  background:#1a1a1a; border-radius:6px;
  border:1px solid #2e2e2e; padding:8px 10px;
  height:100%;
}
.acwr-player { font-size:1.1rem; font-weight:600; color:#fff; line-height:1.2; }
.acwr-meta { font-size:0.72rem; color:#777; margin-bottom:6px; }
.density-wrap { background:#1c1c1c; border-radius:5px; border:1px solid #2a2a2a; padding:6px; }
.intensity-wrap { background:#1c1c1c; border-radius:5px; border:1px solid #2a2a2a; padding:6px; text-align:center; }
h1,h2,h3,h4 { color:#f0f0f0 !important; }
</style>
""", unsafe_allow_html=True)


def fmt(v, d=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if d == 0:
        return f"{int(round(v)):,}"
    return f"{v:,.{d}f}"


def pct_color(pct):
    if pct >= 80:
        return "#4ade80"
    if pct >= 60:
        return "#facc15"
    return "#f87171"


def pct_bar(pct):
    p = min(100, max(0, float(pct or 0)))
    c = pct_color(p)
    return (f'<div class="pct-bar-bg">'
            f'<div style="width:{p:.0f}%;background:{c};height:5px;border-radius:2px"></div>'
            f'</div>')


def volume_card(label, today_val, bench, color):
    pct = (today_val / bench["MAX"] * 100) if bench["MAX"] > 0 else 0
    pc = pct_color(pct)
    return f"""
<div class="card" style="border-top:2px solid {color}">
  <div class="card-title">{label}</div>
  <div class="big-num">{fmt(today_val)}</div>
  <div class="bench-row">
    <div class="bench-item"><div class="bench-val">{fmt(bench['MAX'])}</div><div class="bench-lbl">MAX</div></div>
    <div class="bench-item"><div class="bench-val">{fmt(bench['GAME'])}</div><div class="bench-lbl">GAME</div></div>
    <div class="bench-item"><div class="bench-val">{fmt(bench['PRAC'])}</div><div class="bench-lbl">PRAC</div></div>
  </div>
  <div class="pct-lbl" style="color:{pc}">{pct:.0f}%</div>
  {pct_bar(pct)}
</div>"""


def density_mini(label, today_val, bench, color):
    pct = (today_val / bench["MAX"] * 100) if bench["MAX"] > 0 else 0
    pc = pct_color(pct)
    return f"""
<div style="text-align:center;padding:0 4px">
  <div class="card-title" style="color:{color}">{label}</div>
  <div class="big-num" style="font-size:1.35rem">{fmt(today_val, 1)}</div>
  <div class="bench-row">
    <div class="bench-item"><div class="bench-val" style="font-size:0.65rem">{fmt(bench['MAX'],1)}</div><div class="bench-lbl">MAX</div></div>
    <div class="bench-item"><div class="bench-val" style="font-size:0.65rem">{fmt(bench['GAME'],1)}</div><div class="bench-lbl">GAME</div></div>
    <div class="bench-item"><div class="bench-val" style="font-size:0.65rem">{fmt(bench['PRAC'],1)}</div><div class="bench-lbl">PRAC</div></div>
  </div>
  <div class="pct-lbl" style="color:{pc};font-size:0.72rem">{pct:.0f}%</div>
  {pct_bar(pct)}
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

bench      = get_benchmarks(df, player)
acwr_all   = calc_all_acwr(df, player, date_str)
load_trend = acwr_trend(df, player, date_str, LOAD_COL, days=30)
daily_stack = get_daily_stacked(df, player, date_str, days=30)
weekly_load = get_weekly_metric(df, player, LOAD_COL)
load_m, load_w   = get_period_totals(df, player, date_str, LOAD_COL)
exe_m,  exe_w    = get_period_totals(df, player, date_str, EXE_COL)
chg_m,  chg_w    = get_period_totals(df, player, date_str, CHG_COL)
sprint_m, sprint_w = get_period_totals(df, player, date_str, SPRINT_COL)


# ── ROW 1: ACWR card │ Daily LOAD │ WEEK LOAD ────────────
c1, c2, c3 = st.columns([1, 2.2, 1.8])

with c1:
    load_acwr  = acwr_all["LOAD"]["acwr"] or 0
    load_acute = acwr_all["LOAD"]["acute"]
    cat_label  = today["primary_cat"]
    st.markdown(f"""
    <div class="acwr-card">
      <div class="acwr-player">{player}</div>
      <div class="acwr-meta">{date_str} &nbsp;·&nbsp;
        <span style="background:#85063B;color:#fff;padding:1px 6px;
              border-radius:3px;font-size:0.68rem">{cat_label}</span>
        &nbsp;vs {today['vs']}
      </div>
      <div style="font-size:0.58rem;color:#555;letter-spacing:0.18em;text-align:center;margin-bottom:-4px">ACWR</div>
    </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(acwr_gauge(load_acwr, height=95), use_container_width=True,
                    config={"displayModeBar": False})
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:-8px">
      <div style="background:#1a1a1a;border:1px solid #2e2e2e;border-radius:4px;
                  padding:5px;text-align:center">
        <div class="bench-lbl" style="font-size:0.5rem">MONTH</div>
        <div style="font-size:0.85rem;font-weight:500;color:#bbb">{fmt(load_m)}</div>
      </div>
      <div style="background:#1a1a1a;border:1px solid #c8a400;border-radius:4px;
                  padding:5px;text-align:center">
        <div class="bench-lbl" style="font-size:0.5rem">WEEK</div>
        <div style="font-size:0.85rem;font-weight:500;color:#c8a400">{fmt(load_w)}</div>
      </div>
    </div>
    <div style="text-align:center;margin-top:3px">
      <span style="font-size:0.52rem;color:#444;letter-spacing:0.15em">
        AVG {fmt(load_acute,1)} &nbsp;·&nbsp; MODIFY
      </span>
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
vol_hdr = f'<div class="sec">VOLUME &nbsp;<span style="color:#aaa;font-size:0.78rem;font-weight:400">{fmt(today["MIN"],1)}</span> <span style="color:#444;font-size:0.55rem">min</span></div>'
st.markdown(vol_hdr, unsafe_allow_html=True)

v1, v2, v3, v4, d_col, i_col = st.columns([1.3, 1.3, 1.3, 1.3, 2.0, 1.5])

with v1:
    st.markdown(volume_card("LOAD",     today["LOAD"],     bench["LOAD"],     "#cc3344"), unsafe_allow_html=True)
with v2:
    st.markdown(volume_card("EXERTION", today["EXERTION"], bench["EXERTION"], "#c8a400"), unsafe_allow_html=True)
with v3:
    st.markdown(volume_card("CHANGES",  today["CHANGE"],   bench["CHANGE"],   "#ff7722"), unsafe_allow_html=True)
with v4:
    st.markdown(volume_card("SPRINT",   today["SPRINT"],   bench["SPRINT"],   "#dd2200"), unsafe_allow_html=True)

with d_col:
    st.markdown('<div class="density-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">DENSITY</div>', unsafe_allow_html=True)
    dd1, dd2 = st.columns(2)
    with dd1:
        st.markdown(density_mini("EXE/MIN", today["EXE_MIN"], bench["EXE_MIN"], "#c8a400"), unsafe_allow_html=True)
    with dd2:
        st.markdown(density_mini("CHG/MIN", today["CHG_MIN"], bench["CHG_MIN"], "#ff7722"), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with i_col:
    exe_g = bench["EXE_MIN"]["GAME"]
    chg_g = bench["CHG_MIN"]["GAME"]
    load_g = bench["LOAD"]["GAME"]
    pcts = []
    if exe_g > 0: pcts.append(min(today["EXE_MIN"] / exe_g * 100, 100))
    if chg_g > 0: pcts.append(min(today["CHG_MIN"] / chg_g * 100, 100))
    intensity_pct = np.mean(pcts) if pcts else 0
    vol_pct = min((today["LOAD"] / load_g * 100) if load_g > 0 else 0, 999)

    st.markdown('<div class="intensity-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">INTENSITY</div>', unsafe_allow_html=True)
    st.plotly_chart(intensity_donut(intensity_pct), use_container_width=True,
                    config={"displayModeBar": False})
    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:2px;margin-top:-8px">
      <div style="text-align:center">
        <div class="bench-lbl">VOL</div>
        <div style="font-size:0.8rem;color:#ccc;font-weight:500">{vol_pct:.0f}%</div>
      </div>
      <div style="text-align:center">
        <div class="bench-lbl">DENS</div>
        <div style="font-size:0.8rem;color:#ccc;font-weight:500">{intensity_pct:.0f}%</div>
      </div>
      <div style="text-align:center">
        <div class="bench-lbl">min</div>
        <div style="font-size:0.8rem;color:#ccc;font-weight:500">{fmt(today['MIN'])}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── ROW 3: COMPARISON + GAME MAX ─────────────────────────
st.markdown('<div class="sec">COMPARISON</div>', unsafe_allow_html=True)

r3a, r3b = st.columns([1.8, 1])

comp_data = [
    ("LOAD", fmt(load_m),   fmt(today["LOAD"]),     fmt(bench["LOAD"]["MAX"]),     fmt(bench["LOAD"]["GAME"]),     fmt(bench["LOAD"]["PRAC"])),
    ("EXE",  fmt(exe_m),    fmt(today["EXERTION"]),  fmt(bench["EXERTION"]["MAX"]), fmt(bench["EXERTION"]["GAME"]), fmt(bench["EXERTION"]["PRAC"])),
    ("CHG",  fmt(chg_m),    fmt(today["CHANGE"]),    fmt(bench["CHANGE"]["MAX"]),   fmt(bench["CHANGE"]["GAME"]),   fmt(bench["CHANGE"]["PRAC"])),
    ("SPRT", fmt(sprint_m), fmt(today["SPRINT"]),    fmt(bench["SPRINT"]["MAX"]),   fmt(bench["SPRINT"]["GAME"]),   fmt(bench["SPRINT"]["PRAC"])),
]
th  = "font-size:0.62rem;color:#4a4a4a;letter-spacing:0.1em;text-align:center;padding:4px 6px;border-bottom:1px solid #2a2a2a"
tdl = "font-size:0.68rem;text-align:left;padding:4px 8px;color:#666;font-weight:600;letter-spacing:0.08em"
tdb = "font-size:0.82rem;text-align:center;padding:4px 6px;color:#aaa"
tdt = "font-size:0.9rem;text-align:center;padding:4px 6px;font-weight:600;color:#fff;background:#85063B"
rows_html = "".join(f"""<tr>
  <td style="{tdl}">{r[0]}</td><td style="{tdb}">{r[1]}</td>
  <td style="{tdt}">{r[2]}</td><td style="{tdb}">{r[3]}</td>
  <td style="{tdb}">{r[4]}</td><td style="{tdb}">{r[5]}</td>
</tr>""" for r in comp_data)

with r3a:
    st.markdown(f"""
    <div style="background:#1c1c1c;border-radius:5px;border:1px solid #2a2a2a;overflow:hidden">
    <table style="width:100%;border-collapse:collapse">
      <thead><tr>
        <th style="{th}"></th><th style="{th}">TOT</th>
        <th style="{th};color:#85063B">TODAY</th>
        <th style="{th}">MAX</th><th style="{th}">GAME</th><th style="{th}">PRAC</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

with r3b:
    game_max = get_game_max(df, player)
    if game_max:
        st.markdown('<div class="card-title" style="margin-bottom:2px">GAME MAX</div>', unsafe_allow_html=True)
        gm_rows = ""
        for row in game_max:
            gm_rows += f"""<tr>
              <td style="font-size:0.6rem;color:#555;padding:3px 6px;letter-spacing:0.1em">{row['metric']}</td>
              <td style="font-size:0.82rem;color:#fff;padding:3px 6px;text-align:right;font-weight:500">{row['value']}</td>
              <td style="font-size:0.6rem;color:#666;padding:3px 4px">{row['vs']}</td>
              <td style="font-size:0.6rem;color:#555;padding:3px 4px">{row['date']}</td>
            </tr>"""
        st.markdown(f"""
        <div style="background:#1c1c1c;border-radius:5px;border:1px solid #2a2a2a;overflow:hidden">
        <table style="width:100%;border-collapse:collapse">{gm_rows}</table>
        </div>""", unsafe_allow_html=True)


# ── PER-METRIC BLOCKS (下スクロール) ──────────────────────
def metric_block(label, daily_df, trend_df_, weekly_df, acwr_val, month_tot, week_tot, color, acute=None):
    st.markdown(f'<div class="sec">{label}</div>', unsafe_allow_html=True)
    m1, m2, m3 = st.columns([2, 2, 1])
    with m1:
        st.plotly_chart(daily_bar_acwr(daily_df, trend_df_, label, stacked=False, color=color),
                        use_container_width=True, config={"displayModeBar": False})
    with m2:
        st.plotly_chart(weekly_bar(weekly_df, label, color),
                        use_container_width=True, config={"displayModeBar": False})
    with m3:
        st.markdown('<div class="acwr-side-block" style="background:#1c1c1c;border-radius:5px;border:1px solid #2a2a2a;padding:7px">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">ACWR</div>', unsafe_allow_html=True)
        st.plotly_chart(acwr_gauge(acwr_val or 0, height=100), use_container_width=True,
                        config={"displayModeBar": False})
        avg_txt = f"AVG {fmt(acute,1)}" if acute is not None else ""
        st.markdown(f"""
        <div style="text-align:center;margin-top:-4px">
          <span style="font-size:0.5rem;color:#444;letter-spacing:0.12em">{avg_txt}</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;margin-top:4px">
          <div style="text-align:center"><div class="bench-lbl">MONTH</div>
            <div style="font-size:0.82rem;font-weight:500;color:#bbb">{fmt(month_tot)}</div></div>
          <div style="text-align:center;border:1px solid #c8a400;border-radius:3px;padding:2px">
            <div class="bench-lbl">WEEK</div>
            <div style="font-size:0.82rem;font-weight:500;color:#c8a400">{fmt(week_tot)}</div></div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


exe_trend    = acwr_trend(df, player, date_str, EXE_COL, days=30)
chg_trend    = acwr_trend(df, player, date_str, CHG_COL, days=30)
sprint_trend = acwr_trend(df, player, date_str, SPRINT_COL, days=30)
daily_exe    = get_daily_metric(df, player, EXE_COL, date_str, days=30)
daily_chg    = get_daily_metric(df, player, CHG_COL, date_str, days=30)
daily_sprint = get_daily_metric(df, player, SPRINT_COL, date_str, days=30)
daily_sc     = get_daily_metric(df, player, LOAD_COL, date_str, days=30, cat_filter=SC_CATS)
weekly_exe    = get_weekly_metric(df, player, EXE_COL)
weekly_chg    = get_weekly_metric(df, player, CHG_COL)
weekly_sprint = get_weekly_metric(df, player, SPRINT_COL)
weekly_sc     = get_weekly_metric(df, player, LOAD_COL, cat_filter=SC_CATS)

metric_block("EXERTION", daily_exe,    exe_trend,    weekly_exe,    acwr_all["EXERTION"]["acwr"], exe_m,    exe_w,    "#c8a400", acute=acwr_all["EXERTION"]["acute"])
metric_block("CHANGES",  daily_chg,    chg_trend,    weekly_chg,    acwr_all["CHANGE"]["acwr"],   chg_m,    chg_w,    "#ff7722", acute=acwr_all["CHANGE"]["acute"])
metric_block("SPRINT",   daily_sprint, sprint_trend, weekly_sprint, acwr_all["SPRINT"]["acwr"],   sprint_m, sprint_w, "#dd2200", acute=acwr_all["SPRINT"]["acute"])
metric_block("SC",       daily_sc,     None,         weekly_sc,     None,                         0,        0,        "#777777")
metric_block("LOAD",     get_daily_metric(df, player, LOAD_COL, date_str, days=30),
             load_trend, weekly_load, acwr_all["LOAD"]["acwr"], load_m, load_w, "#85063B", acute=acwr_all["LOAD"]["acute"])
