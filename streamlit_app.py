
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent))

import streamlit as st
from basmati.pipeline import run_pipeline
from basmati.data_sources.agmarknet_api import fetch_basmati_prices_csv
from basmati.data_sources.data_gov_india import fetch_datagov_prices_csv

st.set_page_config(page_title="Basmati Forecast", page_icon="🌾", layout="wide")

st.title("🌾 Basmati Price Forecast")

with st.expander("Fetch data from Agmarknet (CEDA API)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        state = st.text_input("State", "Haryana")
        market = st.text_input("Market", "Karnal")
        variety = st.text_input("Variety keywords (comma-separated)", "Basmati,1121,1509,1718,PB-1")
    with col2:
        date_from = st.text_input("From (YYYY-MM-DD)", "")
        date_to = st.text_input("To (YYYY-MM-DD)", "")
        out_csv = st.text_input("Save to CSV", "data/basmati_prices.csv")

    if st.button("Fetch from Agmarknet"):
        keys = [k.strip() for k in variety.split(",") if k.strip()]
        path = fetch_basmati_prices_csv(
            out_csv=out_csv,
            state=state or None,
            market=market or None,
            variety_keywords=keys,
            date_from=date_from or None,
            date_to=date_to or None,
        )
        st.success(f"Saved: {path}")

with st.expander("Fetch data from data.gov.in (Retail/Wholesale)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        api_key = st.text_input("API key", type="password")
        resource_id = st.text_input("Resource ID", "")
        commodity = st.text_input("Commodity filter", "Rice")
    with col2:
        state2 = st.text_input("State (optional)", "")
        centre = st.text_input("Centre/City (optional)", "")
        date_from2 = st.text_input("From (YYYY-MM-DD)", "")
        date_to2 = st.text_input("To (YYYY-MM-DD)", "")
        out_csv2 = st.text_input("Save to CSV", "data/basmati_prices.csv")

    if st.button("Fetch from data.gov.in"):
        if not api_key or not resource_id:
            st.error("Please enter API key and resource_id")
        else:
            path = fetch_datagov_prices_csv(
                api_key=api_key,
                resource_id=resource_id,
                out_csv=out_csv2,
                commodity_filter=commodity,
                state=state2 or None,
                centre=centre or None,
                date_from=date_from2 or None,
                date_to=date_to2 or None,
            )
            st.success(f"Saved: {path}")

st.divider()
st.subheader("Run Forecast")

c1, c2, c3 = st.columns(3)
with c1:
    h1 = st.number_input("Horizon 1 (days)", min_value=1, value=7)
with c2:
    h2 = st.number_input("Horizon 2 (days)", min_value=1, value=30)
with c3:
    h3 = st.number_input("Horizon 3 (days)", min_value=1, value=180)

if st.button("Train & Forecast"):
    with st.spinner("Training models and generating forecasts..."):
        try:
            run_pipeline("basmati/config.yaml", horizons=[h1, h2, h3])
            st.success("Done! Check the artifacts/ folder for CSVs and plots.")
            st.info("Outputs: artifacts/YYYY-MM-DD/forecast_{h}d.csv and PNG charts")
        except Exception as e:
            st.exception(e)

st.caption("Tip: Replace data/basmati_prices.csv with your real time series (Date,Price).")
