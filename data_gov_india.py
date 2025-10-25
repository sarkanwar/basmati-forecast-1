
from __future__ import annotations
import math
import pandas as pd
import requests
from typing import Optional, Dict, Any

BASE = "https://api.data.gov.in/resource"

def fetch_datagov_prices_csv(
    api_key: str,
    resource_id: str,
    out_csv: str,
    commodity_filter: str = "Rice",
    state: Optional[str] = None,
    centre: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    price_field_candidates = ("retail", "wholesale", "modal_price", "price"),
) -> str:
    """Fetch daily prices from data.gov.in CKAN API and save to Date,Price CSV.
    You must provide a valid `resource_id` from the target dataset and an API key.
    Common dataset: 'Retail and Wholesale Prices of Essential Commodities'.
    Filters by commodity/state/centre and date range if fields exist.
    We try to detect a usable price column from `price_field_candidates` (case-insensitive).
    """
    session = requests.Session()
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 1000,
    }
    url = f"{BASE}/{resource_id}"

    # We'll iterate with offset pagination
    offset = 0
    rows_all = []
    while True:
        qp = params.copy()
        qp["offset"] = offset
        # Use CKAN 'filters' to reduce transfer where supported
        filters = {}
        if commodity_filter:
            filters["commodity"] = commodity_filter
        if state:
            filters["state"] = state
        if centre:
            # some datasets use 'centre' (city) or 'market' field
            # filters only work if the field matches exactly; otherwise post-filter
            filters["centre"] = centre
        if date_from:
            qp["from"] = date_from
        if date_to:
            qp["to"] = date_to
        if filters:
            # CKAN style: filters={"field":"value",...}
            import json as _json
            qp["filters"] = _json.dumps(filters)

        r = session.get(url, params=qp, timeout=45)
        r.raise_for_status()
        payload = r.json()
        recs = payload.get("records", [])
        if not recs:
            break
        rows_all.extend(recs)
        if len(recs) < qp["limit"]:
            break
        offset += qp["limit"]

    df = pd.DataFrame(rows_all)
    if df.empty:
        pd.DataFrame(columns=["Date","Price"]).to_csv(out_csv, index=False)
        return out_csv

    # Normalize columns to lower for flexible access
    lower_map = {c: c.lower() for c in df.columns}
    df = df.rename(columns=lower_map)

    # Try best-effort filters if not handled at source
    if "commodity" in df.columns and commodity_filter:
        df = df[df["commodity"].str.contains(commodity_filter, case=False, na=False)]
    if state and "state" in df.columns:
        df = df[df["state"].str.contains(state, case=False, na=False)]
    if centre and "centre" in df.columns:
        df = df[df["centre"].str.contains(centre, case=False, na=False)]

    # Pick a date column
    date_col = None
    for cand in ("date", "reported_date", "price_date"):
        if cand in df.columns:
            date_col = cand
            break
    if not date_col:
        raise ValueError("Could not find a date column in the chosen dataset. Inspect the dataset's fields.")

    df[date_col] = pd.to_datetime(df[date_col]).dt.date

    # Find a usable price column
    price_col = None
    for cand in price_field_candidates:
        if cand in df.columns:
            price_col = cand
            break
    if not price_col:
        # try to find any numeric column that looks like a price
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(pd.to_numeric(df[c], errors="coerce"))]
        if num_cols:
            price_col = num_cols[0]
        else:
            raise ValueError("Could not detect a numeric price column in the dataset.")

    # Ensure numeric
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
    df = df.dropna(subset=[price_col])

    # Aggregate to daily mean
    daily = df.groupby(date_col, as_index=False)[price_col].mean().rename(columns={date_col:"Date", price_col:"Price"})
    daily = daily.sort_values("Date")
    daily.to_csv(out_csv, index=False)
    return out_csv
