import pandas as pd
import numpy as np

LOAD_COL = "Accumulated Acceleration Load"
EXE_COL = "Exertions"
CHG_COL = "Changes of Orientation"
EXE_MIN_COL = "Exertions / min"
CHG_MIN_COL = "Changes of Orientation / min"
LOAD_MIN_COL = "Accumulated Acceleration Load / min"
SPRINT_COL = "SPRINT"

GAME_CATS = {"試合"}
PRAC_CATS = {"練習", "2部練"}
SC_CATS = {"SC"}
INDY_CATS = {"individual", "individual0"}
REHA_CATS = {"Reha"}

CAT_COLORS = {
    "SC": "#777777",
    "Individual": "#c8a400",
    "MAIN": "#85063B",
    "GAME": "#dd2200",
    "Reha": "#4488bb",
}


def categorize(cat):
    if cat in SC_CATS:
        return "SC"
    if cat in INDY_CATS:
        return "Individual"
    if cat in GAME_CATS:
        return "GAME"
    if cat in REHA_CATS:
        return "Reha"
    return "MAIN"


def _prep(df, player, col):
    pdf = df[df["Name"] == player].copy()
    pdf["Date_norm"] = pd.to_datetime(pdf["Date"]).dt.normalize()
    pdf[col] = pd.to_numeric(pdf[col], errors="coerce").fillna(0)
    return pdf


def get_today_summary(df, player, date_str):
    day = pd.Timestamp(date_str)
    pdf = _prep(df, player, LOAD_COL)
    today = pdf[pdf["Date_norm"] == day].copy()
    if today.empty:
        return None

    for c in [EXE_COL, CHG_COL, SPRINT_COL]:
        today[c] = pd.to_numeric(today[c], errors="coerce").fillna(0)

    cats = [c for c in today["CATEGORY"].unique() if c != "OFF"]
    vs = today["VS"].iloc[0] if len(today) > 0 else "—"

    today["load_min"] = pd.to_numeric(today[LOAD_MIN_COL], errors="coerce")
    today["dur"] = today[LOAD_COL] / today["load_min"]
    total_min = today["dur"].replace([np.inf, -np.inf], np.nan).sum()

    active = today[~today["CATEGORY"].isin({"OFF"})]
    exe_min = pd.to_numeric(active[EXE_MIN_COL], errors="coerce").mean()
    chg_min = pd.to_numeric(active[CHG_MIN_COL], errors="coerce").mean()

    return {
        "LOAD": today[LOAD_COL].sum(),
        "EXERTION": today[EXE_COL].sum(),
        "CHANGE": today[CHG_COL].sum(),
        "SPRINT": today[SPRINT_COL].sum(),
        "EXE_MIN": exe_min if not np.isnan(exe_min) else 0,
        "CHG_MIN": chg_min if not np.isnan(chg_min) else 0,
        "MIN": total_min if not np.isnan(total_min) else 0,
        "cats": cats,
        "vs": vs,
        "primary_cat": cats[0] if cats else "—",
    }


def get_benchmarks(df, player):
    pdf = df[df["Name"] == player].copy()
    pdf["Date_norm"] = pd.to_datetime(pdf["Date"]).dt.normalize()
    for c in [LOAD_COL, EXE_COL, CHG_COL, SPRINT_COL, EXE_MIN_COL, CHG_MIN_COL]:
        pdf[c] = pd.to_numeric(pdf[c], errors="coerce").fillna(0)

    game_df = pdf[pdf["CATEGORY"].isin(GAME_CATS)]
    prac_df = pdf[pdf["CATEGORY"].isin(PRAC_CATS)]

    result = {}
    for key, col in [
        ("LOAD", LOAD_COL), ("EXERTION", EXE_COL),
        ("CHANGE", CHG_COL), ("SPRINT", SPRINT_COL),
        ("EXE_MIN", EXE_MIN_COL), ("CHG_MIN", CHG_MIN_COL),
    ]:
        all_d = pdf.groupby("Date_norm")[col].sum()
        game_d = game_df.groupby("Date_norm")[col].sum() if not game_df.empty else pd.Series(dtype=float)
        prac_d = prac_df.groupby("Date_norm")[col].sum() if not prac_df.empty else pd.Series(dtype=float)
        result[key] = {
            "MAX": round(all_d.max(), 1) if not all_d.empty else 0,
            "GAME": round(game_d.mean(), 1) if not game_d.empty else 0,
            "PRAC": round(prac_d.mean(), 1) if not prac_d.empty else 0,
        }
    return result


def get_daily_stacked(df, player, end_date, days=30):
    pdf = _prep(df, player, LOAD_COL)
    pdf["CatGroup"] = pdf["CATEGORY"].apply(categorize)
    end = pd.Timestamp(end_date)
    start = end - pd.Timedelta(days=days - 1)
    pdf = pdf[(pdf["Date_norm"] >= start) & (pdf["Date_norm"] <= end)]
    daily = (
        pdf.groupby(["Date_norm", "CatGroup"])[LOAD_COL]
        .sum().unstack(fill_value=0).reset_index()
    )
    for c in ["SC", "Individual", "MAIN", "GAME", "Reha"]:
        if c not in daily.columns:
            daily[c] = 0
    return daily


def get_daily_metric(df, player, col, end_date, days=30, cat_filter=None):
    pdf = _prep(df, player, col)
    if cat_filter:
        pdf = pdf[pdf["CATEGORY"].isin(cat_filter)]
    end = pd.Timestamp(end_date)
    start = end - pd.Timedelta(days=days - 1)
    pdf = pdf[(pdf["Date_norm"] >= start) & (pdf["Date_norm"] <= end)]
    daily = pdf.groupby("Date_norm")[col].sum().reset_index()
    daily.columns = ["Date", "value"]
    return daily


def get_weekly_metric(df, player, col, cat_filter=None):
    pdf = _prep(df, player, col)
    if cat_filter:
        pdf = pdf[pdf["CATEGORY"].isin(cat_filter)]
    if pdf.empty:
        return pd.DataFrame(columns=["Week", "value"])
    min_date = pdf["Date_norm"].min()
    pdf["Week"] = ((pdf["Date_norm"] - min_date).dt.days // 7) + 1
    weekly = pdf.groupby("Week")[col].sum().reset_index()
    weekly.columns = ["Week", "value"]
    return weekly


def get_period_totals(df, player, date_str, col):
    pdf = _prep(df, player, col)
    target = pd.Timestamp(date_str)
    month_mask = (
        (pdf["Date_norm"].dt.year == target.year) &
        (pdf["Date_norm"].dt.month == target.month) &
        (pdf["Date_norm"] <= target)
    )
    week_start = target - pd.Timedelta(days=target.dayofweek)
    week_mask = (pdf["Date_norm"] >= week_start) & (pdf["Date_norm"] <= target)
    return int(pdf[month_mask][col].sum()), int(pdf[week_mask][col].sum())
