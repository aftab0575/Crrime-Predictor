"""Load small previews of CSV datasets for the home page."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from flask import current_app, has_app_context

from config.training import DEFAULT_DATA_PATH
from app.services.datasets import list_csv_datasets, resolve_dataset_filename

PREVIEW_ROW_LIMIT = 25


def _active_csv_path() -> Path:
    if has_app_context():
        p = current_app.config.get("ACTIVE_DATA_PATH")
        if p is not None:
            return Path(p)
    return DEFAULT_DATA_PATH


def build_home_dataset_previews(max_rows: int | None = None) -> list[dict]:
    """
    For each CSV in ``data/``, read at most ``max_rows`` rows (default 25).
    Active dataset (``ACTIVE_DATA_PATH`` / default) is listed first when present.

    Each item: ``filename``, ``is_active``, ``columns`` (str list), ``rows`` (list of dicts),
    ``error`` (optional str).
    """
    limit = PREVIEW_ROW_LIMIT if max_rows is None else max(1, min(max_rows, 100))
    names = list_csv_datasets()
    active = _active_csv_path()
    active_name = active.name if active.is_file() else None

    ordered: list[str] = []
    if active_name and active_name in names:
        ordered.append(active_name)
    for n in names:
        if n not in ordered:
            ordered.append(n)

    previews: list[dict] = []
    for name in ordered:
        path = resolve_dataset_filename(name)
        entry: dict = {
            "filename": name,
            "is_active": bool(active_name and name == active_name),
            "columns": [],
            "rows": [],
            "error": None,
        }
        if path is None:
            entry["error"] = "File not found."
            previews.append(entry)
            continue

        try:
            df = pd.read_csv(path, nrows=limit)
            df.columns = df.columns.map(str)
            df = df.fillna("")
            entry["columns"] = df.columns.tolist()
            entry["rows"] = df.astype(str).to_dict(orient="records")
        except Exception as exc:  # noqa: BLE001
            entry["error"] = f"Could not read CSV: {exc}"
        previews.append(entry)

    return previews
