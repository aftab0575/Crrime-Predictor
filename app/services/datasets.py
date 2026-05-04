"""Dataset listing and safe path resolution under `data/`."""

from __future__ import annotations

from pathlib import Path

from config.training import DATA_DIR


def list_csv_datasets(data_dir: Path | None = None) -> list[str]:
    root = data_dir or DATA_DIR
    if not root.is_dir():
        return []
    names = [p.name for p in root.iterdir() if p.is_file() and p.suffix.lower() == ".csv"]
    return sorted(names, key=str.casefold)


def resolve_dataset_filename(filename: str, data_dir: Path | None = None) -> Path | None:
    """
    Return resolved path to DATA_DIR / filename, or None if invalid (path traversal / not csv).
    """
    root = (data_dir or DATA_DIR).resolve()
    if not filename or Path(filename).name != filename:
        return None
    if not filename.lower().endswith(".csv"):
        return None
    candidate = (root / filename).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None
