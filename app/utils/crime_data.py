"""Shared crime CSV prep: must match scripts/train.py + inference (Step 4)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.training import FEATURE_COLUMNS, TARGET_COLUMN, TOP_N_CITIES


def compute_top_cities(csv_path: Path, top_n: int = TOP_N_CITIES) -> frozenset[str]:
    df = pd.read_csv(csv_path, usecols=["City"])
    s = df["City"].astype(str).str.strip().replace("", pd.NA).fillna("Unknown")
    top = s.value_counts().nlargest(top_n).index.astype(str).tolist()
    return frozenset(top)


def _sanitize_cats(series_like: pd.Series) -> pd.Series:
    return series_like.astype(str).str.strip().replace("", pd.NA).fillna("Unknown")


def bucket_city(raw_city: str, top_cities: frozenset[str]) -> str:
    c = raw_city.strip() if isinstance(raw_city, str) else str(raw_city).strip()
    if not c:
        c = "Unknown"
    return c if c in top_cities else "Other"


def load_xy_from_training_csv(csv_path: Path) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Same semantics as scripts/train.load_and_prepare_features (training)."""
    df = pd.read_csv(csv_path)
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Missing target column '{TARGET_COLUMN}'")

    df = df.dropna(subset=[TARGET_COLUMN])
    cats = ["Province", "City", "Month", "Weapon_Used"]
    for col in cats:
        if col not in df.columns:
            raise ValueError(f"Missing feature column '{col}'")
        df[col] = _sanitize_cats(df[col])

    df["Hour"] = pd.to_numeric(df["Hour"], errors="coerce")
    dropped_hour = int(df["Hour"].isna().sum())
    df = df.dropna(subset=["Hour"]).copy()
    df["Hour"] = df["Hour"].astype(int)

    top = df["City"].value_counts().nlargest(TOP_N_CITIES).index
    df["City"] = df["City"].where(df["City"].isin(top), "Other")

    missing_feat = set(FEATURE_COLUMNS) - set(df.columns)
    if missing_feat:
        raise ValueError(f"Missing columns: {missing_feat}")

    X = df[list(FEATURE_COLUMNS)].copy()
    y = df[TARGET_COLUMN].astype(str)
    meta = {"dropped_na_hour_rows": dropped_hour, "final_rows": len(df)}
    return X, y, meta


def form_choices_from_csv(csv_path: Path) -> dict[str, list]:
    """Unique sorted values per form field from raw CSV (before bucket)."""
    df = pd.read_csv(csv_path)
    out = {}
    for col in ["Province", "City", "Month", "Weapon_Used"]:
        if col not in df.columns:
            continue
        u = sorted(
            pd.Series(df[col].astype(str).str.strip().replace("", "Unknown")).dropna().unique().tolist(),
            key=lambda x: (x.casefold(), x),
        )
        out[col] = u if u else ["Unknown"]
    return out


def dataframe_from_form_row(
    row: dict,
    *,
    top_cities: frozenset[str],
) -> pd.DataFrame:
    """One row aligned with FEATURE_COLUMNS."""
    province = (row.get("Province") or "Unknown").strip() or "Unknown"
    raw_city = (row.get("City") or "Unknown").strip() or "Unknown"
    city = bucket_city(raw_city, top_cities)
    hour = row.get("Hour", 12)
    try:
        hour_i = int(hour)
    except (TypeError, ValueError):
        hour_i = 12
    hour_i = max(0, min(23, hour_i))
    month = (row.get("Month") or "Unknown").strip() or "Unknown"
    weapon = (row.get("Weapon_Used") or "Unknown").strip() or "Unknown"

    data = {
        "Province": province,
        "City": city,
        "Hour": hour_i,
        "Month": month,
        "Weapon_Used": weapon,
    }
    df = pd.DataFrame([data], columns=list(FEATURE_COLUMNS))
    return df
