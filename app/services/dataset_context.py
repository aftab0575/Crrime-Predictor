"""Deterministic text summary of the active crime CSV for LLM context (no row-level RAG)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from flask import current_app, has_app_context

from config.training import DEFAULT_DATA_PATH

_DEFAULT_MAX_CHARS = 10_000


def get_active_csv_path() -> Path:
    if has_app_context():
        p = current_app.config.get("ACTIVE_DATA_PATH")
        if p is not None:
            return Path(p)
    return DEFAULT_DATA_PATH


def _top_counts_block(df: pd.DataFrame, column: str, n: int = 12) -> list[str]:
    if column not in df.columns:
        return []
    s = df[column].astype(str)
    vc = s.value_counts().head(n)
    total = len(df)
    lines = [f"\n### Top values: {column}"]
    for val, cnt in vc.items():
        pct = 100.0 * float(cnt) / total if total else 0.0
        lines.append(f"  - {val!r}: {int(cnt)} ({pct:.1f}%)")
    return lines


def build_dataset_summary(max_chars: int = _DEFAULT_MAX_CHARS) -> str:
    """
    Bounded markdown-like text: schema, row count, top category distributions.
    Falls back to a short message if the file is missing or unreadable.
    """
    path = get_active_csv_path()
    if not path.is_file():
        return (
            f"**Dataset unavailable.** No readable file at `{path}`. "
            "Do not invent statistics; say the project's table is not loaded."
        )

    try:
        df = pd.read_csv(path)
    except OSError as exc:
        return (
            f"**Dataset unavailable.** Could not read `{path}`: {exc}. "
            "Do not invent statistics."
        )

    parts: list[str] = [
        f"# Active dataset: {path.name}",
        f"- Resolved path: `{path.resolve()}`",
        f"- Row count: **{len(df)}**",
        "",
        "## Columns",
        ", ".join(str(c) for c in df.columns),
        "",
        "## Types",
    ]
    for col in df.columns:
        parts.append(f"- {col}: `{df[col].dtype}`")

    missing = df.isna().sum()
    nz = missing[missing > 0]
    if len(nz) > 0:
        parts.append("\n## Missing values (non-zero)")
        for col, n in nz.head(20).items():
            parts.append(f"- {col}: {int(n)}")

    parts.extend(_top_counts_block(df, "Crime_Category"))
    parts.extend(_top_counts_block(df, "Crime_Type"))
    parts.extend(_top_counts_block(df, "Province"))
    parts.extend(_top_counts_block(df, "Weapon_Used"))
    parts.extend(_top_counts_block(df, "City", n=15))

    if "Hour" in df.columns:
        try:
            h = pd.to_numeric(df["Hour"], errors="coerce").dropna().astype(int)
            if len(h):
                parts.append("\n### Hour (numeric)")
                parts.append(
                    f"  - Min / max: {int(h.min())} / {int(h.max())}; mean {float(h.mean()):.1f}"
                )
        except (TypeError, ValueError):
            pass

    text = "\n".join(parts)
    if len(text) > max_chars:
        head = text[: max_chars - 120]
        return (
            head
            + "\n\n...[Summary truncated]. Use only what appears above plus general knowledge."
        )
    return text
