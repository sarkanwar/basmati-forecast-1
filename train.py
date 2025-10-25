
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List, Tuple
import pandas as pd
import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor
import joblib

@dataclass
class TrainResult:
    sarimax_model_path: str
    xgb_model_path: str | None
    metrics: dict

def fit_sarimax(series: pd.Series, order=(1,1,1), seasonal_order=(0,1,1,7)):
    model = SARIMAX(series, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False)
    res = model.fit(disp=False)
    return res

def time_series_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    mape = (np.abs((y_true - y_pred) / y_true).replace(np.inf, np.nan)).dropna().mean() * 100
    return {"MAE": float(mae), "RMSE": float(rmse), "MAPE_pct": float(mape)}

def train_models(
    series: pd.Series,
    features: pd.DataFrame,
    artifacts_dir: str,
    sarimax_cfg: dict,
    xgb_cfg: dict | None,
    test_size_days: int = 60,
) -> TrainResult:
    os.makedirs(artifacts_dir, exist_ok=True)

    df = features.copy()
    df['price'] = series
    df = df.dropna()
    y = df['price']
    X = df.drop(columns=['price'])

    cutoff = y.index.max() - pd.Timedelta(days=test_size_days)
    y_train, y_test = y[y.index <= cutoff], y[y.index > cutoff]
    X_train, X_test = X.loc[y_train.index], X.loc[y_test.index]

    sarimax_res = fit_sarimax(y_train, order=tuple(sarimax_cfg.get("order", (1,1,1))),
                              seasonal_order=tuple(sarimax_cfg.get("seasonal_order", (0,1,1,7))))
    base_pred_test = sarimax_res.get_forecast(steps=len(y_test)).predicted_mean
    base_pred_test.index = y_test.index

    metrics_base = time_series_metrics(y_test, base_pred_test)

    xgb_model_path = None
    if xgb_cfg and xgb_cfg.get("enabled", True):
        xgb = XGBRegressor(
            n_estimators=xgb_cfg.get("n_estimators", 400),
            max_depth=xgb_cfg.get("max_depth", 4),
            learning_rate=xgb_cfg.get("learning_rate", 0.05),
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
        )
        base_pred_train = sarimax_res.fittedvalues.reindex(y_train.index).ffill()
        resid_train = (y_train - base_pred_train).dropna()
        X_train_resid = X_train.loc[resid_train.index]
        xgb.fit(X_train_resid, resid_train.values)

        resid_test = y_test - base_pred_test
        resid_pred_test = pd.Series(xgb.predict(X_test), index=X_test.index)
        hybrid_pred_test = (base_pred_test + resid_pred_test).reindex(y_test.index)
        metrics_hybrid = time_series_metrics(y_test, hybrid_pred_test)
    else:
        xgb = None
        metrics_hybrid = metrics_base

    sarimax_full = fit_sarimax(y, order=tuple(sarimax_cfg.get("order", (1,1,1))),
                               seasonal_order=tuple(sarimax_cfg.get("seasonal_order", (0,1,1,7))))
    sarimax_model_path = os.path.join(artifacts_dir, "sarimax.pkl")
    joblib.dump(sarimax_full, sarimax_model_path)

    if xgb is not None:
        base_fit_full = sarimax_full.fittedvalues.reindex(y.index).ffill()
        resid_full = (y - base_fit_full).dropna()
        X_full_resid = X.loc[resid_full.index]
        xgb.fit(X_full_resid, resid_full.values)
        xgb_model_path = os.path.join(artifacts_dir, "xgb.pkl")
        joblib.dump(xgb, xgb_model_path)

    metrics = {"baseline_SARIMAX": metrics_base, "hybrid": metrics_hybrid}
    return TrainResult(sarimax_model_path=sarimax_model_path, xgb_model_path=xgb_model_path, metrics=metrics)
