import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "rawdata.csv"

REQUIRED_COLS = {
    "Date", "VS", "Name",
    "Accumulated Acceleration Load",
    "Exertions", "Changes of Orientation", "SPRINT", "CATEGORY",
}


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    return df


def validate_csv(uploaded: pd.DataFrame) -> tuple[bool, str]:
    missing = REQUIRED_COLS - set(uploaded.columns)
    if missing:
        return False, f"必須カラムが不足: {', '.join(sorted(missing))}"
    return True, ""


def append_csv(uploaded: pd.DataFrame) -> tuple[int, int]:
    existing = load_data()
    uploaded["Date"] = pd.to_datetime(uploaded["Date"]).dt.normalize()

    merged = pd.concat([existing, uploaded], ignore_index=True)
    before = len(merged)
    merged = merged.drop_duplicates(subset=["Date", "Name", "VS"], keep="first")
    added = len(merged) - len(existing)
    skipped = before - len(existing) - max(added, 0)

    merged["Date"] = merged["Date"].dt.strftime("%Y-%m-%d")
    merged.to_csv(DATA_PATH, index=False)
    return max(added, 0), max(skipped, 0)
