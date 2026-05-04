"""Build Plotly figures for the crime analytics dashboard (Step 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from flask import current_app, has_app_context

from config.training import DEFAULT_DATA_PATH


def _active_csv_path() -> Path:
    if has_app_context():
        p = current_app.config.get("ACTIVE_DATA_PATH")
        if p is not None:
            return Path(p)
    return DEFAULT_DATA_PATH

_LAYOUT_KW: dict[str, Any] = {
    "template": "plotly_white",
    "margin": dict(l=48, r=24, t=48, b=48),
    "height": 400,
}
_CONFIG = {"responsive": True, "displaylogo": False}


def _fig_to_div(fig: go.Figure) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=_CONFIG,
    )


def _load_dataframe(csv_path: Path) -> pd.DataFrame:
    return pd.read_csv(csv_path)


def _chart_crimes_by_hour(df: pd.DataFrame) -> go.Figure:
    hours = range(24)
    counts = (
        df.groupby("Hour")
        .size()
        .reindex(hours, fill_value=0)
        .rename("Crimes")
        .reset_index()
    )
    fig = px.bar(
        counts,
        x="Hour",
        y="Crimes",
        title="Recorded incidents by hour of day",
        labels={"Hour": "Hour (0–23)", "Crimes": "Count"},
    )
    fig.update_layout(**_LAYOUT_KW)
    fig.update_traces(marker_color="#1a2744")
    return fig


def _chart_top_crime_types(df: pd.DataFrame) -> go.Figure:
    vc = df["Crime_Type"].astype(str).value_counts().nlargest(10)
    data = vc.reset_index()
    data.columns = ["Crime_Type", "count"]
    fig = px.bar(
        data,
        x="count",
        y="Crime_Type",
        orientation="h",
        title="Top 10 crime types",
        labels={"count": "Count", "Crime_Type": ""},
    )
    fig.update_layout(**_LAYOUT_KW)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_traces(marker_color="#2563eb")
    return fig


def _chart_crime_category_share(df: pd.DataFrame) -> go.Figure:
    vc = df["Crime_Category"].astype(str).value_counts()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=vc.index.tolist(),
                values=vc.values.tolist(),
                hole=0.45,
                marker=dict(line=dict(color="#fff", width=1)),
            )
        ]
    )
    fig.update_layout(
        title="Share by crime category",
        **_LAYOUT_KW,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            x=0.5,
            xanchor="center",
        ),
    )
    return fig


def _chart_by_province(df: pd.DataFrame) -> go.Figure:
    vc = df["Province"].astype(str).value_counts().sort_values(ascending=True)
    data = vc.reset_index()
    data.columns = ["Province", "count"]
    fig = px.bar(
        data,
        x="count",
        y="Province",
        orientation="h",
        title="Incidents by province",
        labels={"count": "Count", "Province": ""},
    )
    fig.update_layout(**_LAYOUT_KW)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    fig.update_traces(marker_color="#0d9488")
    return fig


def _chart_lat_lon(df: pd.DataFrame) -> go.Figure:
    subset = df.dropna(subset=["Latitude", "Longitude"]).copy()
    if len(subset) > 2000:
        subset = subset.sample(2000, random_state=42)
    subset["Province"] = subset["Province"].astype(str)
    fig = px.scatter(
        subset,
        x="Longitude",
        y="Latitude",
        color="Province",
        title="Geographic scatter of incidents (sample)",
        labels={"Longitude": "", "Latitude": "", "Province": "Province"},
        opacity=0.65,
    )
    kw = dict(_LAYOUT_KW)
    kw["height"] = 420
    fig.update_layout(**kw)
    fig.update_traces(marker=dict(size=8, line=dict(width=0)))
    return fig


def build_dashboard_chart_cards(
    csv_path: Path | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Load CSV and produce a list of cards: dict with id, title, html fragments.
    Template should load Plotly.js once (CDN).
    Returns (cards, error_message).
    """
    path = Path(csv_path) if csv_path is not None else _active_csv_path()
    if not path.exists():
        return [], f"Dataset not found at: {path}"

    try:
        df = _load_dataframe(path)
    except OSError as exc:
        return [], f"Could not read dataset: {exc}"

    required = {"Hour", "Crime_Type", "Crime_Category", "Province", "Latitude", "Longitude"}
    missing = required - set(df.columns)
    if missing:
        return [], f"Dataset missing columns: {sorted(missing)}"

    figures: list[tuple[str, str, go.Figure]] = [
        ("hour", "Crimes by hour of day", _chart_crimes_by_hour(df)),
        ("top-types", "Top crime types", _chart_top_crime_types(df)),
        ("categories", "Crime category mix", _chart_crime_category_share(df)),
        ("province", "By province", _chart_by_province(df)),
        ("coords", "Location sample", _chart_lat_lon(df)),
    ]

    cards: list[dict[str, Any]] = []
    for fid, title, fig in figures:
        cards.append({"id": fid, "title": title, "html": _fig_to_div(fig)})
    return cards, None
