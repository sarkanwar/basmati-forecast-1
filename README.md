
# Basmati Forecast — Automated Price Prediction System

This project builds an **automatic basmati rice price forecasting pipeline** that:
- Ingests price history from a CSV (e.g., mandi/export prices) and optional market indicators (USD/INR, Brent) via `yfinance`.
- Adds technical and weather features (from Open‑Meteo; no key required).
- Trains a **SARIMAX** time‑series model for the baseline forecast and an **XGBoost** regressor on engineered features to correct residuals.
- Produces **1‑week, 1‑month, and 6‑month** forecasts with prediction intervals.
- Saves outputs (CSV + PNG charts + model artifacts) under `artifacts/`.
- Can be run on a schedule (cron or GitHub Actions) for hands‑free operation.

> ⚠️ You must supply your actual basmati price history in `data/basmati_prices.csv` (Date,Price). A small synthetic sample is provided for demo.

---

## Quick Start

```bash
# 1) Create and activate an environment (example using Python >=3.10)
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Put your real data at data/basmati_prices.csv with columns: Date,Price
#    or use the provided sample to test.

# 4) Run a one-shot train + forecast (7d, 30d, 180d) and generate charts
python cli.py run-all --horizons 7 30 180
```

Outputs go to `artifacts/YYYY-MM-DD/`, including:
- `forecast_7d.csv`, `forecast_30d.csv`, `forecast_180d.csv`
- `forecast_plot_7d.png`, `forecast_plot_30d.png`, `forecast_plot_180d.png`
- Trained model files in `artifacts/models/`

---

## Data Layout

- **`data/basmati_prices.csv`** — Required. Two columns:  
  - `Date` (YYYY-MM-DD)  
  - `Price` (numeric, e.g., INR/Quintal or USD/MT — be consistent)

- **Optional market indicators (fetched automatically if enabled in `basmati/config.yaml`)**
  - USD/INR (ticker: `USDINR=X` via yfinance)
  - Brent crude front month (ticker: `BZ=F` via yfinance)

- **Weather features** (Open‑Meteo): daily precipitation & temperature for major basmati regions (Punjab, Haryana, Western UP by default).
  Adjust lat/lon in `basmati/config.yaml` as needed.

---

## Scheduling (Automatic Runs)

### Cron (Linux/macOS)
Edit your crontab (`crontab -e`) and add, for example, **09:00 IST daily**:
```
0 9 * * * cd /path/to/basmati-forecast && . .venv/bin/activate && python cli.py run-all --horizons 7 30 180 >> logs/cron.log 2>&1
```
> Asia/Kolkata is UTC+5:30. Ensure your server time zone or use `TZ='Asia/Kolkata'` before the command.

### Windows Task Scheduler
Create a Basic Task → **Daily** at 09:00 → Action: *Start a program* → Program: `python`, Args: `cli.py run-all --horizons 7 30 180`, Start in: project folder.

### GitHub Actions (optional)
See [`/.github/workflows/forecast.yml`](.github/workflows/forecast.yml) for a template that runs every day at 03:30 UTC (09:00 IST).

---

## Configuration

Edit `basmati/config.yaml`:

```yaml
price_csv: data/basmati_prices.csv

# Optional external indicators (set enabled: true/false)
indicators:
  usd_inr:
    enabled: true
    ticker: "USDINR=X"
    lookback_days: 1095
  brent:
    enabled: true
    ticker: "BZ=F"
    lookback_days: 1095

# Weather regions (Open-Meteo; no API key needed)
weather:
  enabled: true
  regions:
    - { name: "Punjab-Ludhiana", lat: 30.9010, lon: 75.8573 }
    - { name: "Haryana-Karnal",  lat: 29.6857, lon: 76.9905 }
    - { name: "UP-Meerut",       lat: 28.9845, lon: 77.7064 }

# Modeling
model:
  sarimax:
    order: [1,1,1]
    seasonal_order: [0,1,1,7]   # weekly seasonality
  xgboost:
    enabled: true
    n_estimators: 400
    max_depth: 4
    learning_rate: 0.05
  test_size_days: 60

# Forecast horizons (days) default
horizons: [7, 30, 180]
```

---

## Replacing the Sample Data

Replace `data/basmati_prices.csv` with your historical basmati price series. At least 1–2 years of **daily** data is recommended.
If your data is weekly or monthly, adjust resampling in `basmati/data_sources/csv_source.py` (see comments).

---

## Notes & Extensions

- Add more indicators by creating new files under `basmati/data_sources/` or `basmati/features/`.
- If you have access to NCDEX/Agmarknet APIs or enterprise data, write a new loader and reference it in `basmati/config.yaml`.
- For confidence intervals we use SARIMAX’s forecast intervals. Residual booster (XGBoost) adjusts the point forecast.
- You can export results to databases or Google Sheets by extending `basmati/pipeline.py`.

---

## License
MIT


---

## Fetch Agmarknet (Basmati) Data Automatically

This project includes a fetcher that uses the **CEDA Agmarknet public API** (Ashoka University mirror) to pull mandi prices and filter Basmati-related varieties.

Examples:
```bash
# List dependencies first
pip install -r requirements.txt

# Fetch Basmati Paddy prices for Karnal, Haryana, last two years
python cli.py fetch-agmarknet --state "Haryana" --market "Karnal" \
  --variety_keywords "Basmati,1121,1509,1718,PB-1" \
  --date_from 2023-01-01 --date_to 2025-10-25 --out_csv data/basmati_prices.csv

# Then run the pipeline
python cli.py run-all --horizons 7 30 180
```

> Notes:
> - Endpoint base: `https://api.ceda.ashoka.edu.in` (subject to availability).
> - If you need the official Agmarknet site instead, we can build a form-scraper, but many users find the CEDA API more stable.
> - You can change `commodity_name` to `"Rice"` if your target series is for milled rice instead of paddy.


### Second backend: data.gov.in (Retail/Wholesale)

You can also fetch prices from **data.gov.in** CKAN datasets (requires a free API key).  
Use the dataset resource that contains daily retail/wholesale commodity prices, then pass its **resource_id**.

Example:
```bash
# Replace with your API key and the correct resource_id from data.gov.in
python cli.py fetch-datagov   --api_key YOUR_KEY   --resource_id YOUR_RESOURCE_ID   --commodity "Rice"   --state "Haryana"   --centre "Karnal"   --date_from 2023-01-01 --date_to 2025-10-25   --out_csv data/basmati_prices.csv

# Then run forecasts
python cli.py run-all --horizons 7 30 180
```

> The helper tries to auto-detect the price field (e.g., `retail`, `wholesale`, `modal_price`, or `price`). You can inspect the dataset schema on data.gov.in and adjust filters accordingly.
