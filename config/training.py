"""Paths and defaults for training (`scripts/train.py`)."""

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

DATA_DIR: Path = PROJECT_ROOT / "data"
DEFAULT_DATA_PATH: Path = DATA_DIR / "pakistan_crime_dataset_1000.csv"
MODEL_DIR: Path = PROJECT_ROOT / "models"

PIPELINE_FILENAME: str = "crime_pipeline.joblib"
LABEL_ENCODER_FILENAME: str = "crime_label_encoder.joblib"
METRICS_FILENAME: str = "metrics.json"
CONFUSION_MATRIX_FILENAME: str = "confusion_matrix.png"

RANDOM_STATE: int = 42
TOP_N_CITIES: int = 30
TEST_SIZE: float = 0.2

FEATURE_COLUMNS: tuple[str, ...] = (
    "Province",
    "City",
    "Hour",
    "Month",
    "Weapon_Used",
)
TARGET_COLUMN: str = "Crime_Category"
