
from __future__ import annotations
import pandas as pd
import requests
from typing import List, Optional
from urllib.parse import urlencode

# Public mirror of Agmarknet by CEDA (Ashoka University)
# Docs: https://api.ceda.ashoka.edu.in/documentation/ (subject to change)
BASE_URL = "https://api.ceda.ashoka.edu.in"

class AgmarknetClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        r = requests.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_commodities(self) -> pd.DataFrame:
        data = self._get("/agmarknet/commodities")
        return pd.DataFrame(data)

    def list_states(self) -> pd.DataFrame:
        data = self._get("/agmarknet/states")
        return pd.DataFrame(data)

    def list_markets(self, state: Optional[str] = None, district: Optional[str] = None) -> pd.DataFrame:
        params = {}
        if state: params["state"] = state
        if district: params["district"] = district
        data = self._get("/agmarknet/markets", params=params or None)
        return pd.DataFrame(data)

    def prices(
        self,
        commodity: str,
        variety: Optional[str] = None,
        state: Optional[str] = None,
        market: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 10000,
    ) -> pd.DataFrame:
        params = {"commodity": commodity, "limit": limit}
        if variety: params["variety"] = variety
        if state: params["state"] = state
        if market: params["market"] = market
        if date_from: params["from"] = date_from
        if date_to: params["to"] = date_to
        data = self._get("/agmarknet/prices", params=params)
        df = pd.DataFrame(data)
        if not df.empty:
            # Normalize common fields if present
            for c in ["date", "modal_price", "min_price", "max_price"]:
                if c in df.columns and c == "date":
                    df[c] = pd.to_datetime(df[c]).dt.date
            # Rename to standard names when available
            rename_map = {
                "date": "Date",
                "state": "State",
                "district": "District",
                "market": "Market",
                "commodity": "Commodity",
                "variety": "Variety",
                "unit": "Unit",
                "arrival": "Arrivals",
                "modal_price": "ModalPrice",
                "min_price": "MinPrice",
                "max_price": "MaxPrice",
            }
            df = df.rename(columns={k:v for k,v in rename_map.items() if k in df.columns})
        return df


def fetch_basmati_prices_csv(
    out_csv: str,
    state: Optional[str] = None,
    market: Optional[str] = None,
    variety_keywords: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    commodity_name: str = "Paddy",
) -> str:
    """Fetch basmati-related mandi prices filtered by variety keywords and save to CSV.
    Defaults to commodity='Paddy' because Agmarknet often lists basmati as paddy varieties.
    Example varieties: ['Basmati', '1121', '1509', '1718', 'PB-1']
    Returns the path of the written CSV.
    """
    client = AgmarknetClient()
    df = client.prices(
        commodity=commodity_name,
        variety=None,
        state=state,
        market=market,
        date_from=date_from,
        date_to=date_to,
        limit=100000,
    )
    if df.empty:
        pd.DataFrame(columns=['Date','Price']).to_csv(out_csv, index=False)
        return out_csv

    # Filter basmati-like varieties
    if variety_keywords:
        pat = "|".join([str(x) for x in variety_keywords])
        mask = df['Variety'].str.contains(pat, case=False, na=False)
        df = df[mask].copy()

    # Aggregate to a single daily price (Modal) per day; you can change to Min/Max/Avg
    if 'ModalPrice' in df.columns:
        daily = df.groupby('Date', as_index=False)['ModalPrice'].mean().rename(columns={'ModalPrice':'Price'})
    elif 'MaxPrice' in df.columns and 'MinPrice' in df.columns:
        tmp = df.groupby('Date', as_index=False)[['MinPrice','MaxPrice']].mean()
        tmp['Price'] = (tmp['MinPrice'] + tmp['MaxPrice'])/2.0
        daily = tmp[['Date','Price']]
    else:
        # Fallback: count as NaN
        daily = df.groupby('Date', as_index=False).size().rename(columns={'size':'Price'})
        daily['Price'] = float('nan')

    daily = daily.sort_values('Date')
    daily.to_csv(out_csv, index=False)
    return out_csv
