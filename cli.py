
from __future__ import annotations
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent))
import typer
from typing import List, Optional
from basmati.pipeline import run_pipeline
from basmati.data_sources.agmarknet_api import fetch_basmati_prices_csv
from basmati.data_sources.data_gov_india import fetch_datagov_prices_csv

app = typer.Typer(help="Basmati Forecast CLI")


@app.command("run-all")
def run_all(
    config: str = typer.Option("basmati/config.yaml", help="Path to config file"),
    horizons: Optional[List[int]] = typer.Option(None, help="List of forecast horizons in days, e.g. --horizons 7 30 180"),
):
    run_pipeline(config_path=config, horizons=horizons)

@app.command("fetch-agmarknet")
def fetch_agmarknet(
    out_csv: str = typer.Option("data/basmati_prices.csv", help="Where to save the filtered CSV"),
    state: str = typer.Option(None, help="State filter, e.g. 'Haryana'"),
    market: str = typer.Option(None, help="Market/Mandi filter, e.g. 'Karnal'"),
    variety_keywords: str = typer.Option("Basmati,1121,1509,1718,PB-1", help="Comma-separated variety keywords to match"),
    date_from: str = typer.Option(None, help="Start date YYYY-MM-DD"),
    date_to: str = typer.Option(None, help="End date YYYY-MM-DD"),
    commodity_name: str = typer.Option("Paddy", help="Commodity name (often 'Paddy' for basmati varieties)"),
):
    keys = [k.strip() for k in variety_keywords.split(',') if k.strip()]
    path = fetch_basmati_prices_csv(
        out_csv=out_csv,
        state=state,
        market=market,
        variety_keywords=keys,
        date_from=date_from,
        date_to=date_to,
        commodity_name=commodity_name,
    )
    typer.echo(f"Saved: {path}")

@app.command("fetch-datagov")
def fetch_datagov(
    api_key: str = typer.Option(..., help="data.gov.in API key"),
    resource_id: str = typer.Option(..., help="CKAN resource_id for the dataset"),
    out_csv: str = typer.Option("data/basmati_prices.csv", help="Where to save CSV"),
    commodity: str = typer.Option("Rice", help="Commodity filter (dataset dependent)"),
    state: str = typer.Option(None, help="State filter (optional)"),
    centre: str = typer.Option(None, help="Centre/City filter (optional)"),
    date_from: str = typer.Option(None, help="Start date YYYY-MM-DD"),
    date_to: str = typer.Option(None, help="End date YYYY-MM-DD"),
):
    path = fetch_datagov_prices_csv(
        api_key=api_key,
        resource_id=resource_id,
        out_csv=out_csv,
        commodity_filter=commodity,
        state=state,
        centre=centre,
        date_from=date_from,
        date_to=date_to,
    )
    typer.echo(f"Saved: {path}")

if __name__ == "__main__":
    app()
