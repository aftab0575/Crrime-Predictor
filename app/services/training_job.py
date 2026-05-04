"""Background training job state, lock, and model reload into Flask config."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
from flask import Flask

from config.training import (
    DEFAULT_DATA_PATH,
    LABEL_ENCODER_FILENAME,
    MODEL_DIR,
    PIPELINE_FILENAME,
    RANDOM_STATE,
)
from app.utils.crime_data import compute_top_cities, form_choices_from_csv

TRAINING_LOCK = threading.Lock()

training_state: dict[str, Any] = {
    "status": "idle",
    "message": "",
    "pct": 0,
    "started_at": None,
    "finished_at": None,
    "last_metrics": None,
}


def get_training_state_snapshot() -> dict[str, Any]:
    with TRAINING_LOCK:
        return {k: v for k, v in training_state.items()}


def reload_ml_into_app(app: Flask, active_csv: Path) -> None:
    """Load joblib artifacts and refresh form choices / top cities from `active_csv`."""
    pipeline_path = MODEL_DIR / PIPELINE_FILENAME
    label_path = MODEL_DIR / LABEL_ENCODER_FILENAME
    ml_ready = pipeline_path.is_file() and label_path.is_file()
    app.config["ML_READY"] = ml_ready
    app.config["ACTIVE_DATA_PATH"] = active_csv

    if ml_ready:
        app.config["CRIME_PIPELINE"] = joblib.load(pipeline_path)
        app.config["CRIME_LABEL_ENCODER"] = joblib.load(label_path)
    else:
        app.config["CRIME_PIPELINE"] = None
        app.config["CRIME_LABEL_ENCODER"] = None

    app.config["TOP_CITY_SET"] = frozenset()
    app.config["FORM_CHOICES"] = {}
    if active_csv.is_file():
        try:
            app.config["TOP_CITY_SET"] = compute_top_cities(active_csv)
            app.config["FORM_CHOICES"] = form_choices_from_csv(active_csv)
        except OSError:
            pass


def _worker(app: Flask, csv_path: Path, rng: int) -> None:
    def prog(pct: int, msg: str) -> None:
        with TRAINING_LOCK:
            training_state["pct"] = pct
            training_state["message"] = msg

    try:
        from scripts.train import run_training

        metrics = run_training(csv_path, rng, progress=prog)
        metrics.pop("_verify_accuracy", None)
        with TRAINING_LOCK:
            training_state["status"] = "done"
            training_state["message"] = "Training finished."
            training_state["pct"] = 100
            training_state["last_metrics"] = {
                "selected_model": metrics.get("selected_model"),
                "test_accuracy": metrics.get("test_accuracy"),
                "macro_f1": metrics.get("macro_f1"),
                "csv_path": metrics.get("csv_path"),
            }
        with app.app_context():
            reload_ml_into_app(app, csv_path.resolve())
    except Exception as exc:  # noqa: BLE001
        with TRAINING_LOCK:
            training_state["status"] = "error"
            training_state["message"] = str(exc)
            training_state["pct"] = 0
    finally:
        fin = datetime.now(timezone.utc).isoformat()
        with TRAINING_LOCK:
            training_state["finished_at"] = fin


def try_start_training(app: Flask, csv_path: Path, rng: int = RANDOM_STATE) -> tuple[bool, str]:
    """
    Start a background training thread if idle. Returns (ok, message).
    When ok is False, caller may return HTTP 409.
    """
    with TRAINING_LOCK:
        if training_state["status"] == "running":
            return False, "Training is already in progress."
        training_state["status"] = "running"
        training_state["message"] = "Starting…"
        training_state["pct"] = 0
        training_state["started_at"] = datetime.now(timezone.utc).isoformat()
        training_state["finished_at"] = None
        training_state["last_metrics"] = None

    t = threading.Thread(
        target=_worker,
        args=(app, csv_path, rng),
        daemon=True,
    )
    t.start()
    return True, "Training started."
