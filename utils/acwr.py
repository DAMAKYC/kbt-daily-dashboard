import pandas as pd
import numpy as np

LOAD_COL = "Accumulated Acceleration Load"
EXE_COL = "Exertions"
CHG_COL = "Changes of Orientation"
SPRINT_COL = "SPRINT"


def _daily_load(df, player, metric):
    pdf = df[df["Name"] == player].copy()
    pdf["Date"] = pd.to_datetime(pdf["Date"])
    pdf[metric] = pd.to_numeric(pdf[metric], errors="coerce").fillna(0)
    daily = pdf.groupby("Date")[metric].sum().sort_index()
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_idx, fill_value=0)


def calc_acwr(df, player, date_str, metric=LOAD_COL):
    target = pd.Timestamp(date_str)
    daily = _daily_load(df, player, metric)
    if target not in daily.index:
        return None, None, None
    window = daily[:target]
    acute = window.iloc[-7:].mean() if len(window) >= 1 else np.nan
    chronic = window.iloc[-28:].mean() if len(window) >= 1 else np.nan
    acwr = (acute / chronic) if (chronic and chronic > 0) else np.nan
    return round(acwr, 3), round(acute, 2), round(chronic, 2)


def calc_all_acwr(df, player, date_str):
    metrics = {
        "LOAD": LOAD_COL,
        "EXERTION": EXE_COL,
        "CHANGE": CHG_COL,
        "SPRINT": SPRINT_COL,
    }
    result = {}
    for key, col in metrics.items():
        acwr, acute, chronic = calc_acwr(df, player, date_str, col)
        result[key] = {"acwr": acwr, "acute": acute, "chronic": chronic}
    return result


def acwr_trend(df, player, end_date, metric=LOAD_COL, days=30):
    end = pd.Timestamp(end_date)
    start = end - pd.Timedelta(days=days - 1)
    daily = _daily_load(df, player, metric)

    rows = []
    for d in pd.date_range(start, end, freq="D"):
        if d not in daily.index:
            rows.append({"Date": d, "acwr": np.nan, "acute": np.nan})
            continue
        window = daily[:d]
        acute = window.iloc[-7:].mean() if len(window) >= 1 else np.nan
        chronic = window.iloc[-28:].mean() if len(window) >= 1 else np.nan
        acwr = (acute / chronic) if (chronic and chronic > 0) else np.nan
        rows.append({
            "Date": d,
            "acwr": round(acwr, 3) if not np.isnan(acwr) else np.nan,
            "acute": round(acute, 2) if not np.isnan(acute) else np.nan,
        })
    return pd.DataFrame(rows)
