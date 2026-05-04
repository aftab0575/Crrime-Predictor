from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from config.gemini import apply_gemini_config
from config.training import DEFAULT_DATA_PATH

from app.routes.main_bp import main_bp
from app.services.training_job import reload_ml_into_app

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    load_dotenv(_PROJECT_ROOT / ".env")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.setdefault("SECRET_KEY", "dev-crime-predictor-change-me")

    apply_gemini_config(app)

    reload_ml_into_app(app, DEFAULT_DATA_PATH)

    app.register_blueprint(main_bp)

    return app
