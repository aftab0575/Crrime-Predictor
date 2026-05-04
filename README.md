# Crime Predictor (FYP)

Flask app for Crime Data Analysis & Prediction. **Step 5:** thesis screenshots and report polish.

## Requirements

- Python 3.10+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2 — Train the model

Place CSV datasets under **`data/`** (project-relative). Default training file:

`data/pakistan_crime_dataset_1000.csv`

```bash
python scripts/train.py
```

Options:

```bash
python scripts/train.py --data data/pakistan_crime_dataset.csv --random-state 42
```

Writes to `models/`:

- `crime_pipeline.joblib` — fitted preprocessing + classifier  
- `crime_label_encoder.joblib` — maps encoded labels to category names  
- `metrics.json` — accuracy, comparison, classification report, confusion matrix  
- `confusion_matrix.png` — confusion matrix figure for reports  

### In-app training (development only)

With the web app running, open **`/train`** to pick a `*.csv` from `data/` and train in the background. **Do not expose this route on the public Internet**—it runs heavy CPU work and has no authentication. Prefer `debug=False` when testing training (Flask's reloader can interact oddly with background threads).

## Step 3 — Dashboard charts

`/dashboard` loads the **active** dataset (same CSV as the last successful training, or the default under `data/` on startup) via [`app/services/charts.py`](app/services/charts.py), builds Plotly visuals (counts by hour, top crime types, category mix, province counts, geographic scatter).

Requires `pip install -r requirements.txt` (includes **plotly**).

## Step 4 — Prediction UI

Train first (Step 2 or `/train`), then run the app. **`/`** has a hero and CTAs; **`/predict`** submits province, city, hour, month, and weapon; the response shows the predicted **Crime_Category** plus confidence bars when `predict_proba` is available. **`/about`** summarizes data and limits.

City bucketing matches training via [`app/utils/crime_data.py`](app/utils/crime_data.py).

## Step 5 — Gemini assistant (optional)

The **`/assistant`** page calls **Google Gemini** with a **server-built summary** of the active CSV (schema, row count, top-value counts). It does **not** send every raw row.

1. Get an API key from [Google AI Studio](https://aistudio.google.com/) (usage subject to Google’s terms and quotas).

2. Set the API key (**do not commit it**). Either export `GEMINI_API_KEY` in the shell, or add a **`.env`** file in the project root (already listed in `.gitignore`) with:

   ```
   GEMINI_API_KEY=your_key_here
   ```

   The app loads `.env` automatically via `python-dotenv` when you start it.

3. Before starting the app (PowerShell example without `.env`):

   ```powershell
   $env:GEMINI_API_KEY="your_key_here"
   # Optional: $env:GEMINI_MODEL="gemini-2.0-flash"
   python run.py
   ```

4. Do **not** commit the key; do **not** expose `/assistant` or `/api/assistant` on the public Internet—there is **no authentication**.

Default model name is set in [`config/gemini.py`](config/gemini.py) (`GEMINI_MODEL` env override).

## Run the web app (development)

```bash
python run.py
```

Or:

```bash
set FLASK_APP=run:app
flask run
```

Open http://127.0.0.1:5000/

## Routes

- `/` — Hero landing  
- `/dashboard` — Interactive Plotly charts  
- `/predict` — Form + prediction (needs `models/*.joblib`)  
- `/train` — Dataset picker + background training (**dev / localhost only**)  
- `/assistant` — Optional Gemini Q&A (needs `GEMINI_API_KEY`; **localhost only**)  
- `/about` — Dataset and limitations  

## Project layout

- `app/` — Flask package (`routes`, `templates`, `services/`, `utils/crime_data`)  
- `config/` — `training.py`, `gemini.py` (optional Gemini env wiring)  
- `data/` — CSV datasets (canonical location for defaults and UI listing)  
- `models/` — trained artifacts (`scripts/train.py`)  
- `scripts/` — `train.py`  
