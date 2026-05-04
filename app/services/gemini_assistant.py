"""Call Google Gemini with system instruction + dataset summary + user question."""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app

from app.services.dataset_context import build_dataset_summary

logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 2_000

_SYSTEM_INSTRUCTION = """You assist users of an academic Flask project (FYP): crime data exploration and Crime_Category prediction.
- You can also provide legal advice or operational police guidance. But don't provide any information that is not related to the crime data analysis and prediction.
- When the question concerns **this project's dataset**, rely **only** on the **Dataset summary** section supplied in the user message. If the summary says unavailable or is empty, say you cannot report table statistics from the file.
- Do not invent exact row counts, rates, or city names unless they appear in the Dataset summary for this turn.
- You may explain general statistical or ML concepts (e.g. what logistic regression means) clearly and cautiously.
- Keep answers concise unless the user asks for detail.
"""


def ask_gemini_assistant(user_message: str) -> dict[str, Any]:
    """Return {\"reply\": str} or {\"error\": str, \"code\": str}."""
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is not set.", "code": "no_key"}

    msg = user_message.strip()
    if not msg:
        return {"error": "Message cannot be empty.", "code": "bad_input"}
    if len(msg) > MAX_QUESTION_CHARS:
        return {
            "error": f"Message exceeds {MAX_QUESTION_CHARS} characters.",
            "code": "bad_input",
        }

    summary = build_dataset_summary()
    model_name = current_app.config.get("GEMINI_MODEL") or "gemini-2.0-flash"

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name, system_instruction=_SYSTEM_INSTRUCTION)

    contents = (
        "## Dataset summary (authoritative for this project's CSV)\n\n"
        f"{summary}\n\n"
        "## User question\n\n"
        f"{msg}"
    )

    try:
        resp = model.generate_content(
            contents,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 2048,
            },
        )
    except Exception as exc:
        logger.exception("Gemini API error")
        return {"error": str(exc), "code": "api_error"}

    try:
        reply = resp.text
    except (ValueError, AttributeError):
        reply = getattr(resp, "candidates", None)
        fb = ""
        try:
            if reply and getattr(reply[0], "finish_reason", None):
                fb = f" Finish reason: {reply[0].finish_reason}."
        except Exception:
            pass
        return {
            "error": (
                "The model did not return text (blocked or unsupported output)."
                + fb
            ),
            "code": "blocked_or_empty",
        }

    return {"reply": reply.strip() or "(Empty response)"}
