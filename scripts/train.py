"""
Train sklearn pipelines for Crime_Category prediction (Step 2).
Run from project root: python scripts/train.py [--data CSV] [--random-state N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

# Project root on path for `config.training`
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import joblib
import matplotlib

matplotlib.use("Agg")  # non-GUI backend; safe when train.py runs in a background thread
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from config.training import (
    CONFUSION_MATRIX_FILENAME,
    DEFAULT_DATA_PATH,
    LABEL_ENCODER_FILENAME,
    METRICS_FILENAME,
    MODEL_DIR,
    PIPELINE_FILENAME,
    RANDOM_STATE,
    TEST_SIZE,
)

from app.utils.crime_data import load_xy_from_training_csv


def build_preprocessor_for_X() -> ColumnTransformer:
    cat_features = ["Province", "City", "Month", "Weapon_Used"]
    num_features = ["Hour"]

    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore", max_categories=50, sparse_output=False),
            ),
        ]
    )

    numerical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("cat", categorical, cat_features),
            ("num", numerical, num_features),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def pick_best(results_rf: dict, results_lr: dict) -> tuple[str, dict]:
    """Choose model by accuracy, then macro F1; tie prefers logistic_regression."""
    rf_acc, rf_f1 = results_rf["accuracy"], results_rf["f1_macro"]
    lr_acc, lr_f1 = results_lr["accuracy"], results_lr["f1_macro"]
    if rf_acc > lr_acc:
        return "random_forest", results_rf
    if lr_acc > rf_acc:
        return "logistic_regression", results_lr
    if rf_f1 > lr_f1:
        return "random_forest", results_rf
    if lr_f1 > rf_f1:
        return "logistic_regression", results_lr
    return "logistic_regression", results_lr


def run_training(
    csv_path: Path,
    random_state: int = RANDOM_STATE,
    *,
    progress: Callable[[int, str], Any] | None = None,
) -> dict[str, Any]:
    """
    Fit & compare RF vs LR, save best pipeline + metrics under models/.
    """
    rng = random_state

    def prog(pct: int, msg: str) -> None:
        if progress is not None:
            progress(pct, msg)

    prog(5, "Loading dataset…")
    X, y, meta = load_xy_from_training_csv(csv_path)

    label_encoder = LabelEncoder()
    y_enc = label_encoder.fit_transform(y)

    prog(15, "Splitting train / test…")
    X_train, X_test, y_train_enc, y_test_enc = train_test_split(
        X,
        y_enc,
        test_size=TEST_SIZE,
        random_state=rng,
        stratify=y_enc,
    )

    preprocessor = build_preprocessor_for_X()

    rf_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=200,
                    random_state=rng,
                    class_weight="balanced_subsample",
                    n_jobs=-1,
                ),
            ),
        ]
    )

    lr_prep = build_preprocessor_for_X()
    lr_pipeline = Pipeline(
        steps=[
            ("preprocessor", lr_prep),
            (
                "clf",
                LogisticRegression(
                    max_iter=8000,
                    solver="lbfgs",
                    class_weight="balanced",
                    random_state=rng,
                ),
            ),
        ]
    )

    prog(30, "Training Random Forest…")
    rf_pipeline.fit(X_train, y_train_enc)
    prog(50, "Training Logistic Regression…")
    lr_pipeline.fit(X_train, y_train_enc)

    rf_pred = rf_pipeline.predict(X_test)
    lr_pred = lr_pipeline.predict(X_test)

    results_rf = {
        "accuracy": float(accuracy_score(y_test_enc, rf_pred)),
        "f1_macro": float(f1_score(y_test_enc, rf_pred, average="macro", zero_division=0)),
        "pipeline": rf_pipeline,
    }
    results_lr = {
        "accuracy": float(accuracy_score(y_test_enc, lr_pred)),
        "f1_macro": float(f1_score(y_test_enc, lr_pred, average="macro", zero_division=0)),
        "pipeline": lr_pipeline,
    }

    prog(65, "Comparing models…")
    best_name, best_pack = pick_best(results_rf, results_lr)
    best_pipeline = best_pack["pipeline"]
    y_pred_best = best_pipeline.predict(X_test)

    cm = confusion_matrix(y_test_enc, y_pred_best)
    cm_list = cm.tolist()
    tie_acc_only = (
        abs(results_rf["accuracy"] - results_lr["accuracy"]) < 1e-12
    )

    prog(72, "Saving pipeline and artifacts…")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    pipeline_path = MODEL_DIR / PIPELINE_FILENAME
    encoder_path = MODEL_DIR / LABEL_ENCODER_FILENAME

    joblib.dump(best_pipeline, pipeline_path)
    joblib.dump(label_encoder, encoder_path)

    fig, ax = plt.subplots(figsize=(10, 8))
    ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=label_encoder.classes_,
    ).plot(ax=ax, xticks_rotation=45, colorbar=False)
    fig.tight_layout()
    png_path = MODEL_DIR / CONFUSION_MATRIX_FILENAME
    fig.savefig(png_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    saved_png = str(png_path)

    metrics: dict[str, Any] = {
        "csv_path": str(csv_path.resolve()),
        "random_state": rng,
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "dropped_na_hour_rows": meta["dropped_na_hour_rows"],
        "comparison": {
            "random_forest": {
                "test_accuracy": results_rf["accuracy"],
                "macro_f1": results_rf["f1_macro"],
            },
            "logistic_regression": {
                "test_accuracy": results_lr["accuracy"],
                "macro_f1": results_lr["f1_macro"],
            },
        },
        "selected_model": best_name,
        "test_accuracy": float(accuracy_score(y_test_enc, y_pred_best)),
        "macro_f1": float(f1_score(y_test_enc, y_pred_best, average="macro", zero_division=0)),
        "classification_report": classification_report(
            y_test_enc,
            y_pred_best,
            target_names=list(label_encoder.classes_),
            digits=4,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": cm_list,
        "label_order": list(label_encoder.classes_),
        "artifact_paths": {
            "pipeline": str(pipeline_path),
            "label_encoder": str(encoder_path),
            "confusion_matrix_png": saved_png,
        },
        "accuracy_tie_rf_lr": tie_acc_only,
    }

    prog(88, "Writing metrics…")
    metrics_path = MODEL_DIR / METRICS_FILENAME
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    verify = float(accuracy_score(y_test_enc, best_pipeline.predict(X_test)))
    metrics["_verify_accuracy"] = verify

    prog(100, "Done.")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Train crime category classifier.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"CSV path (default: {DEFAULT_DATA_PATH})",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=RANDOM_STATE,
        help=f"Seed (default: {RANDOM_STATE})",
    )
    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: CSV not found: {args.data}", file=sys.stderr)
        return 1

    print(f"Loading: {args.data}")
    metrics = run_training(args.data, args.random_state)

    verify = metrics.pop("_verify_accuracy", None)
    results_rf = metrics["comparison"]["random_forest"]
    results_lr = metrics["comparison"]["logistic_regression"]
    best_name = metrics["selected_model"]
    pipeline_path = Path(metrics["artifact_paths"]["pipeline"])
    encoder_path = Path(metrics["artifact_paths"]["label_encoder"])
    png_path = metrics["artifact_paths"]["confusion_matrix_png"]
    metrics_path = MODEL_DIR / METRICS_FILENAME

    print()
    print("-- Results " + "-" * 45)
    print(
        "  RandomForest       "
        f"acc={results_rf['test_accuracy']:.4f}  macro_F1={results_rf['macro_f1']:.4f}"
    )
    print(
        "  LogisticRegression acc="
        f"{results_lr['test_accuracy']:.4f} macro_F1={results_lr['macro_f1']:.4f}"
    )
    print(f"  Selected model: {best_name}")
    print(f"  Test accuracy : {metrics['test_accuracy']:.6f}")
    if verify is not None:
        print(f"  Sanity check    : {verify:.6f}")
    print()
    print(f"  Saved pipeline : {pipeline_path}")
    print(f"  Saved encoder  : {encoder_path}")
    print(f"  Saved metrics  : {metrics_path}")
    print(f"  Confusion PNG  : {png_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
