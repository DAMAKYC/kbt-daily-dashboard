import pandas as pd
import numpy as np


LOAD_COL = "Accumulated Acceleration Load"
EXE_COL = "Exertions"
CHG_COL = "Changes of Orientation"
SPRINT_COL = "SPRINT"

ACTIVE_CATEGORIES = {"練習", "2部練", "individual", "individual0", "Reha", "SC", "試合"}


def _daily_load(df: pd.DataFrame, player: str, metric: str) -> pd.Series:
    pdf = df[df["Name"] == player].copy()
    pdf["Date"] = pd.to_datetime(pdf["Date"])
    pdf[metric] = pd.to_numeric(pdf[metric], errors="coerce").fillna(0)
    daily = pdf.groupby("Date")[metric].sum().sort_index()
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_idx, fill_value=0)


def calc_acwr(df: pd.DataFrame, player: str, date: str, metric: str = LOAD_COL):
    target = pd.Timestamp(date)
    daily = _daily_load(df, player, metric)

    if target not in daily.index:
        return None, None, None

    window = daily[:target]
    acute = window.iloc[-7:].mean() if len(window) >= 1 else np.nan
    chronic = window.iloc[-28:].mean() if len(window) >= 1 else np.nan
    acwr = (acute / chronic) if (chronic and chronic > 0) else np.nan
    return round(acwr, 3), round(acute, 2), round(chronic, 2)


def calc_all_acwr(df: pd.DataFrame, player: str, date: str) -> dict:
    metrics = {
        "LOAD": LOAD_COL,
        "EXERTION": EXE_COL,
        "CHANGE": CHG_COL,
        "SPRINT": SPRINT_COL,
    }
    result = {}
    for key, col in metrics.items():
        acwr, acute, chronic = calc_acwr(df, player, date, col)
        result[key] = {"acwr": acwr, "acute": acute, "chronic": chronic}
    return result


def acwr_trend(df: pd.DataFrame, player: str, end_date: str, days: int = 28) -> pd.DataFrame:
    end = pd.Timestamp(end_date)
    start = end - pd.Timedelta(days=days - 1)
    daily = _daily_load(df, player, LOAD_COL)

    rows = []
    for d in pd.date_range(start, end, freq="D"):
        if d not in daily.index:
            rows.append({"Date": d, "acwr": np.nan})
            continue
        window = daily[:d]
        acute = window.iloc[-7:].mean() if len(window) >= 1 else np.nan
        chronic = window.iloc[-28:].mean() if len(window) >= 1 else np.nan
        acwr = (acute / chronic) if (chronic and chronic > 0) else np.nan
        rows.append({"Date": d, "acwr": round(acwr, 3) if not np.isnan(acwr) else np.nan})
    return pd.DataFrame(rows)


def session_summary(df: pd.DataFrame, player: str, date: str) -> pd.DataFrame:
    day = pd.Timestamp(date)
    mask = (df["Name"] == player) & (pd.to_datetime(df["Date"]) == day)
    rows = df[mask].copy()
    return rows
