"""Crime category prediction using saved sklearn Pipeline + LabelEncoder."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder


def predict_crime_category(
    *,
    pipeline: Pipeline,
    label_encoder: LabelEncoder,
    X_row: pd.DataFrame,
) -> tuple[str, list[dict[str, Any]] | None]:
    """
    Returns (decoded_label_str, optional list of {'label','prob'} top-5 descending).
    """
    pred_arr = pipeline.predict(X_row)
    idx = np.asarray(pred_arr).astype(int).ravel()[0]
    label_str = label_encoder.inverse_transform(np.array([idx]))[0]

    probas_kv: list[dict[str, Any]] | None = None
    clf = pipeline.named_steps.get("clf")
    if clf is not None and hasattr(clf, "predict_proba"):
        proba = pipeline.predict_proba(X_row)[0]
        classes = clf.classes_

        paired = [(float(proba[k]), int(classes[k])) for k in range(len(classes))]
        paired.sort(key=lambda z: z[0], reverse=True)

        ranked: list[dict[str, Any]] = []
        for p, cid in paired[:5]:
            lbl = label_encoder.inverse_transform(np.array([cid]))[0]
            ranked.append({"label": str(lbl), "prob": round(p * 100, 2)})

        probas_kv = ranked

    return str(label_str), probas_kv
