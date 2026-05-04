"""Optional Gemini API settings (read from environment)."""

from __future__ import annotations

import os

# Default model: override with GEMINI_MODEL if your project uses another ID.
DEFAULT_GEMINI_MODEL: str = "gemini-2.0-flash"


def apply_gemini_config(app) -> None:
    """Populate Flask config from env (no secrets in repo)."""
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    model = (os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
    app.config["GEMINI_API_KEY"] = key or None
    app.config["GEMINI_MODEL"] = model
