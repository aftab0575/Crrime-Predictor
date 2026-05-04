from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request

from config.training import DATA_DIR, DEFAULT_DATA_PATH

from app.services.charts import build_dashboard_chart_cards
from app.services.dataset_preview import PREVIEW_ROW_LIMIT, build_home_dataset_previews
from app.services.datasets import list_csv_datasets, resolve_dataset_filename
from app.services.gemini_assistant import ask_gemini_assistant
from app.services.prediction import predict_crime_category
from app.services.training_job import get_training_state_snapshot, try_start_training
from app.utils.crime_data import dataframe_from_form_row


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    dataset_previews = build_home_dataset_previews()
    return render_template(
        "index.html",
        dataset_previews=dataset_previews,
        preview_row_limit=PREVIEW_ROW_LIMIT,
    )


@main_bp.route("/dashboard")
def dashboard():
    cards, dashboard_error = build_dashboard_chart_cards()
    return render_template(
        "dashboard.html",
        chart_cards=cards,
        dashboard_error=dashboard_error,
    )


def _predict_view(
    *,
    result_label: str | None = None,
    prob_rows: list | None = None,
    form_prefill: dict | None = None,
    error_msg: str | None = None,
):
    ml_ready = bool(current_app.config.get("ML_READY"))
    choices = current_app.config.get("FORM_CHOICES") or {}
    hours = list(range(24))
    return render_template(
        "predict.html",
        ml_ready=ml_ready,
        choices=choices,
        hours=hours,
        result_label=result_label,
        prob_rows=prob_rows,
        form_prefill=form_prefill or {},
        error_msg=error_msg,
    )


@main_bp.route("/predict", methods=["GET", "POST"])
def predict():
    ml_ready = bool(current_app.config.get("ML_READY"))
    if request.method == "GET":
        return _predict_view()

    if not ml_ready:
        return _predict_view(error_msg='Model files not found. Run: python scripts/train.py')

    province = request.form.get("Province", "").strip()
    city = request.form.get("City", "").strip()
    month = request.form.get("Month", "").strip()
    weapon = request.form.get("Weapon_Used", "Unknown").strip() or "Unknown"
    hour_raw = request.form.get("Hour", "12")

    prefill = {
        "Province": province,
        "City": city,
        "Month": month,
        "Weapon_Used": weapon,
        "Hour": str(hour_raw),
    }

    if not province or not city or not month:
        return _predict_view(
            form_prefill=prefill,
            error_msg="Please fill Province, City, and Month.",
        )

    try:
        hour_i = int(hour_raw)
        if hour_i < 0 or hour_i > 23:
            raise ValueError
    except (TypeError, ValueError):
        return _predict_view(
            form_prefill=prefill,
            error_msg="Hour must be an integer between 0 and 23.",
        )

    pipe = current_app.config.get("CRIME_PIPELINE")
    enc = current_app.config.get("CRIME_LABEL_ENCODER")
    top = current_app.config.get("TOP_CITY_SET") or frozenset()

    row_df = dataframe_from_form_row(
        {
            "Province": province,
            "City": city,
            "Month": month,
            "Weapon_Used": weapon,
            "Hour": hour_i,
        },
        top_cities=top,
    )

    try:
        label, prob_rows = predict_crime_category(
            pipeline=pipe,
            label_encoder=enc,
            X_row=row_df,
        )
    except Exception as exc:
        return _predict_view(form_prefill=prefill, error_msg=f"Prediction failed: {exc}")

    return _predict_view(result_label=label, prob_rows=prob_rows, form_prefill=prefill)


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/assistant")
def assistant():
    has_key = bool(current_app.config.get("GEMINI_API_KEY"))
    return render_template("assistant.html", assistant_disabled=not has_key)


@main_bp.route("/api/assistant", methods=["POST"])
def api_assistant():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    result = ask_gemini_assistant(message)

    err = result.get("error")
    if err is not None:
        code = result.get("code") or "error"
        if code == "no_key":
            return jsonify(error=err, code=code), 503
        if code == "bad_input":
            return jsonify(error=err, code=code), 400
        if code == "blocked_or_empty":
            return jsonify(error=err, code=code), 502
        return jsonify(error=err, code=code), 502

    return jsonify(reply=result.get("reply", ""))


@main_bp.route("/train", methods=["GET"])
def train():
    datasets = list_csv_datasets()
    default_name = (
        DEFAULT_DATA_PATH.name
        if DEFAULT_DATA_PATH.name in datasets
        else (datasets[0] if datasets else "")
    )
    return render_template(
        "train.html",
        datasets=datasets,
        default_dataset=default_name,
        data_dir=str(DATA_DIR),
    )


@main_bp.route("/train/start", methods=["POST"])
def train_start():
    payload = request.get_json(silent=True) if request.is_json else None
    if payload and isinstance(payload, dict):
        name = (payload.get("dataset") or "").strip()
    else:
        name = (request.form.get("dataset") or "").strip()

    path = resolve_dataset_filename(name)
    if path is None:
        return jsonify(ok=False, error="Invalid or unknown dataset file."), 400

    app = current_app._get_current_object()
    ok, msg = try_start_training(app, path)
    if not ok:
        return jsonify(ok=False, error=msg), 409
    return jsonify(ok=True, message=msg)


@main_bp.route("/api/training-status")
def api_training_status():
    return jsonify(get_training_state_snapshot())
