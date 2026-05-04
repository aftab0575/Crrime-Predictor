# FYP Implementation Plan (Short)

**Goal:** Flask app + model trained on your Pakistan crime CSV (e.g. `pakistan_crime_dataset_1000.csv` or full `pakistan_crime_dataset.csv`).  
**Thesis alignment:** preprocessing → charts → prediction (crime type/category) → optional clustering for “hotspots.” Social media = write in thesis only, not required in code.

---

## Stack (minimal backend + rich UI)

**Backend:** Python, Flask, pandas, scikit-learn, joblib — one `requirements.txt`, one venv.

**UI (pick a consistent set — all work with Jinja):**

| Piece | Suggestion | Why |
|-------|------------|-----|
| Layout & components | **Bootstrap 5** (CDN) or **Tailwind** (CDN build) | Navbar, cards, grid, forms, spacing — fast “pro” look |
| Fonts | **Google Font** (e.g. DM Sans, Plus Jakarta Sans) | Typography upgrade in 2 lines |
| Icons | **Bootstrap Icons** or **Font Awesome** (CDN) | Clear nav and section headers |
| Charts (interactive) | **Plotly** (`plotly.graph_objects` or `express`) — pass `fig.to_json()` / `fig.to_html(full_html=False)` into templates | Rich tooltips, zoom, responsive; good for thesis screenshots |
| Charts (lighter) | **Chart.js** via CDN + small JSON from Flask | Fast bar/line/pie if Plotly feels heavy |
| Map (optional “hotspot”) | **Plotly** scatter mapbox **or** Folium export iframe **or** Plotly scatter on lat/lon | One map elevates the dashboard |

**Design tips (quick wins):** one **dark or light theme** across pages; **cards** for each chart; **hero** strip on home with title + short subtitle; **consistent primary color** (e.g. deep blue / teal) + neutral grays; prediction result in a **highlight card** with badge for predicted class.

---

## 5 Steps (do in order)

### Step 1 — Project skeleton (½ day)
- Folders: `data/`, `models/`, `app/` or `train.py` + Flask files, `templates/`, `static/css` (optional custom overrides).
- Base template: `base.html` with navbar links (Home | Dashboard | Predict), block for `content`, Bootstrap + font link, `{% block scripts %}` for chart divs.
- `requirements.txt`, tiny `README`.

### Step 2 — Train script (1 day)
- Load CSV; pick **target**: `Crime_Category` (fewer classes = easier).
- **Inputs:** Province, City, Hour, Month, Weapon_Used — encode with `ColumnTransformer` + `OneHotEncoder`.
- Missing/`Unknown` filled.
- **Random Forest** + **Logistic Regression**; compare; save best + preprocessor (`joblib`); note **accuracy** + confusion matrix for thesis.

### Step 3 — Dashboard data + charts (½–1 day)
- Backend: functions that return **pandas aggregates** JSON-ready (counts by hour, by province, top crime types, etc.).
- Build **at least 4** visuals for a rich dashboard, e.g.:
  - Bar or line: **crimes by hour**  
  - Bar: **top 10 crime types**  
  - Pie or donut: **Crime_Category** share  
  - Bar: **counts by Province** OR line by **Month**
- Optional: **lat/lon** scatter (Plotly) or cluster colors from K-Means → “hotspot” story.
- Pass Plotly figures into template as `div` (or pre-render Chart.js datasets in JSON).

### Step 4 — Flask app — beautiful pages (1 day)
- **`/`** — Hero section + 3 short feature bullets + CTA buttons (“Dashboard”, “Predict”).
- **`/dashboard`** — Responsive grid (**row of cards**), each card = chart + title; no cluttered full-width mess; spacing (`py-4`, `g-4`).
- **`/predict`** — Clean form (selects aligned, labels clear); POST shows **result card** (predicted crime + optional probability bar chart if model supports `predict_proba`).
- Optional **`/about`** — data source & limitations — same layout as base.
- Load **model once** at startup.

### Step 5 — Finish (½ day)
- Screenshots (**full dashboard**, **prediction result**) for thesis.  
- Simple architecture diagram. Limitations paragraph.

---

## Skip if time is very tight

- Database, login, second Punjab CSV.

---

## Done when

- Train script saves under `models/`.  
- **Dashboard** feels **rich**: multiple interactive charts + neat layout—not plain `<img>` placeholders only.  
- **Predict** page looks polished + real prediction.  
- Report includes screenshots + accuracy.
