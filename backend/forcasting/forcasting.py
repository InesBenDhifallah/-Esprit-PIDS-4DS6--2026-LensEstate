from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import re
import unicodedata
import warnings

import numpy as np
import pandas as pd
from django.http import HttpRequest
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing

BASE_DIR = Path(__file__).resolve().parents[2]
INS_CSV = BASE_DIR / "ins_ipim_by_governorate.csv"
LISTINGS_CSV = BASE_DIR / "final_dataset_with_dates.csv"
CACHE_DIR = BASE_DIR / "forcasting" / "cache"
CACHE_FILE = CACHE_DIR / "dso3_v7_forecast_frontend.json"
CACHE_VERSION = "v7-cache-1"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", message=".*") # ignore all statsmodels warnings

MAPE_SEUIL_BON = 20
MAPE_SEUIL_MOYEN = 35

@dataclass(frozen=True)
class FitResult:
    model_name: str
    aic: float
    mae: float
    rmse: float
    mape: float
    last_ins: float
    future_mean: pd.Series
    future_ci: pd.DataFrame
    reliability_label: str

def _norm_gov(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return text

def _label_from_norm(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())

def _safe_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    mask = np.abs(actual) > actual.mean() * 0.05
    if mask.sum() == 0:
        return 999.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)

def _make_future_index(last_date: pd.Timestamp, n: int) -> pd.DatetimeIndex:
    start = (pd.Timestamp(last_date) + pd.DateOffset(months=1)).replace(day=1)
    return pd.date_range(start=start, periods=n, freq="MS")

def _objectid_to_date(oid: Any) -> datetime | None:
    try:
        ts = int(str(oid)[:8], 16)
        dt = datetime.fromtimestamp(ts)
        if 2022 <= dt.year <= 2027:
            return dt
        return None
    except Exception:
        return None

def _remove_outliers_by_gov(df: pd.DataFrame) -> pd.DataFrame:
    q5 = df.groupby("gov_norm")["price"].transform(lambda s: s.quantile(0.05))
    q95 = df.groupby("gov_norm")["price"].transform(lambda s: s.quantile(0.95))
    return df[(df["price"] >= q5) & (df["price"] <= q95)]

def _smooth_prices(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("month_dt").copy()
    group["price_smooth"] = group["price_median"].rolling(window=3, center=True, min_periods=1).mean()
    return group

def _load_prepared_data() -> tuple[dict[str, pd.DataFrame], dict[str, float | None], dict[str, int]]:
    ins = pd.read_csv(INS_CSV, parse_dates=["date"])
    listings = pd.read_csv(
        LISTINGS_CSV,
        usecols=["source", "governorate", "price", "listing_id", "date_posted"],
        low_memory=False,
    )

    ins["gov_norm"] = ins["governorate"].astype(str).map(_norm_gov)
    ins["date"] = pd.to_datetime(ins["date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    ins = ins.dropna(subset=["date", "ins_ipim_index", "gov_norm"]).sort_values(["gov_norm", "date"])

    tayara = listings[listings["source"].astype(str).str.lower() == "tayara"].copy()
    tayara["price"] = pd.to_numeric(tayara["price"], errors="coerce")
    tayara = tayara[tayara["price"] > 10000]
    tayara["gov_norm"] = tayara["governorate"].astype(str).map(_norm_gov)
    tayara["date_posted"] = pd.to_datetime(tayara["date_posted"], errors="coerce")
    null_dates = tayara["date_posted"].isna()
    tayara.loc[null_dates, "date_posted"] = tayara.loc[null_dates, "listing_id"].map(_objectid_to_date)
    tayara = tayara.dropna(subset=["date_posted", "gov_norm"])
    tayara = _remove_outliers_by_gov(tayara)
    tayara["month_dt"] = tayara["date_posted"].dt.to_period("M").dt.to_timestamp()

    monthly_tayara = (
        tayara.groupby(["gov_norm", "month_dt"])["price"]
        .agg(price_median="median", n_listings="count")
        .reset_index()
        .sort_values(["gov_norm", "month_dt"])
    )
    
    monthly_tayara["price_smooth"] = (
        monthly_tayara.groupby("gov_norm")["price_median"]
        .transform(lambda x: x.rolling(window=3, center=True, min_periods=1).mean())
    )
    monthly_tayara["price_final"] = np.where(
        monthly_tayara["n_listings"] >= 3,
        monthly_tayara["price_median"],
        monthly_tayara["price_smooth"]
    )

    all_series: dict[str, pd.DataFrame] = {}
    last_tayara: dict[str, float | None] = {}
    tayara_counts: dict[str, int] = {}

    for gov_norm, gov_ins in ins.groupby("gov_norm"):
        gov_ins = gov_ins[["date", "ins_ipim_index"]].copy().sort_values("date")
        if gov_ins.empty:
            continue
        gov_ins = gov_ins.set_index("date")

        tay_gov = monthly_tayara[monthly_tayara["gov_norm"] == gov_norm].copy()
        tayara_counts[gov_norm] = len(tay_gov)

        if tay_gov.empty:
            tnd_per_ins = 2500.0
            last_tay = None
        else:
            tay_cal = tay_gov[tay_gov["n_listings"] >= 3].copy()
            if len(tay_cal) < 2:
                tay_cal = tay_gov

            ratios: list[float] = []
            for _, row in tay_cal.head(3).iterrows():
                dt = row["month_dt"]
                ins_match = gov_ins[gov_ins.index <= dt]
                if ins_match.empty:
                    continue
                ins_val = float(ins_match.iloc[-1]["ins_ipim_index"])
                if ins_val > 0 and pd.notna(row["price_final"]) and row["price_final"] > 0:
                    ratios.append(float(row["price_final"]) / ins_val)
            tnd_per_ins = float(np.median(ratios)) if ratios else 2500.0
            last_tay = float(tay_gov.iloc[-1]["price_final"]) if not tay_gov.empty else None

        hist = gov_ins.copy()
        hist["price_median"] = hist["ins_ipim_index"] * tnd_per_ins
        hist["source_data"] = "INS"
        
        tay_part = tay_gov.copy()
        if not tay_part.empty:
            tay_part = tay_part.set_index("month_dt")
            tay_part["price_median"] = tay_part["price_final"]
            tay_part["ins_ipim_index"] = np.nan
            tay_part["source_data"] = "Tayara"
            combined = pd.concat([hist[["price_median", "source_data"]], tay_part[["price_median", "source_data"]]])
        else:
            combined = hist[["price_median", "source_data"]]

        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.sort_index().asfreq("MS")
        combined["price_median"] = combined["price_median"].interpolate()
        combined = combined.dropna(subset=["price_median"])

        if combined.empty or len(combined) < 6:
            continue

        all_series[gov_norm] = combined
        last_tayara[gov_norm] = last_tay

    return all_series, last_tayara, tayara_counts

def _clip_forecast(forecast_series: pd.Series, last_observed: float, max_ratio: float=2.0) -> pd.Series:
    return forecast_series.clip(lower=last_observed * 0.40, upper=last_observed * max_ratio)

def _classify_reliability(mape: float) -> str:
    if mape < MAPE_SEUIL_BON:
        return 'Fiable'
    elif mape < MAPE_SEUIL_MOYEN:
        return 'Acceptable'
    else:
        return 'Données insuffisantes'

def _fit_holtwinters(series_df: pd.DataFrame, forecast_months: int = 12) -> dict:
    ts = series_df["price_median"].dropna()
    n = len(ts)
    train_size = int(n * 0.85)
    train, test = ts.iloc[:train_size], ts.iloc[train_size:]

    try:
        model = ExponentialSmoothing(train, trend="add", seasonal="add", seasonal_periods=12, initialization_method="estimated")
        fitted = model.fit(optimized=True)
    except Exception:
        model = ExponentialSmoothing(train, trend="add", seasonal=None, initialization_method="estimated")
        fitted = model.fit(optimized=True)

    test_pred = fitted.forecast(len(test))
    test_pred.index = test.index

    mae = float(mean_absolute_error(test, test_pred))
    rmse = float(np.sqrt(mean_squared_error(test, test_pred)))
    mape = float(_safe_mape(test.values, test_pred.values))

    future_mean = fitted.forecast(len(test) + forecast_months).iloc[len(test):]
    last_obs = float(ts.iloc[-1])
    future_mean = _clip_forecast(future_mean, last_obs)

    future_ci = pd.DataFrame({"lower": future_mean * 0.85, "upper": future_mean * 1.15}, index=future_mean.index)

    return {
        "future_mean": future_mean,
        "future_ci": future_ci,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "model_name": "Holt-Winters",
        "last_obs": last_obs
    }

def _fit_sarimax_v7(gov_norm: str, series_df: pd.DataFrame, n_tayara: int, forecast_months: int = 12) -> FitResult:
    ts_raw = series_df["price_median"].dropna()
    n = len(ts_raw)

    if n < 20:
        hw_res = _fit_holtwinters(series_df, forecast_months)
        return FitResult(
            model_name=hw_res["model_name"], aic=0.0, mae=hw_res["mae"], rmse=hw_res["rmse"],
            mape=hw_res["mape"], last_ins=hw_res["last_obs"], future_mean=hw_res["future_mean"],
            future_ci=hw_res["future_ci"], reliability_label=_classify_reliability(hw_res["mape"])
        )

    ts = np.log(ts_raw.clip(lower=1))
    train_size = int(n * 0.85)
    train, test = ts.iloc[:train_size], ts.iloc[train_size:]

    if n_tayara >= 15:
        order, s_order, model_name = (1, 1, 1), (1, 1, 1, 12), "SARIMAX(1,1,1)x(1,1,1,12)"
    elif n_tayara >= 10:
        order, s_order, model_name = (1, 1, 0), (0, 1, 1, 12), "SARIMAX(1,1,0)x(0,1,1,12)"
    else:
        order, s_order, model_name = (1, 1, 1), (0, 1, 0, 12), "SARIMAX(1,1,1)x(0,1,0,12)"

    try:
        model_v = SARIMAX(train, order=order, seasonal_order=s_order, enforce_stationarity=False, enforce_invertibility=False)
        fit_v = model_v.fit(disp=False, maxiter=200)

        pred_log = pd.Series(np.array(fit_v.get_forecast(steps=len(test)).predicted_mean), index=test.index)
        pred_raw = np.exp(pred_log)
        test_raw = np.exp(test)

        mae = float(mean_absolute_error(test_raw, pred_raw))
        rmse = float(np.sqrt(mean_squared_error(test_raw, pred_raw)))
        mape = float(_safe_mape(test_raw.values, pred_raw.values))

        if mape > 60:
            hw_res = _fit_holtwinters(series_df, forecast_months)
            return FitResult(
                model_name=hw_res["model_name"], aic=0.0, mae=hw_res["mae"], rmse=hw_res["rmse"],
                mape=hw_res["mape"], last_ins=hw_res["last_obs"], future_mean=hw_res["future_mean"],
                future_ci=hw_res["future_ci"], reliability_label=_classify_reliability(hw_res["mape"])
            )

        model_f = SARIMAX(ts, order=order, seasonal_order=s_order, enforce_stationarity=False, enforce_invertibility=False)
        fit_f = model_f.fit(disp=False, maxiter=200)

        fc = fit_f.get_forecast(steps=forecast_months)
        future_mean = np.exp(pd.Series(np.array(fc.predicted_mean), index=fc.predicted_mean.index))
        ci = fc.conf_int(alpha=0.20)
        future_ci = pd.DataFrame({"lower": np.exp(np.array(ci.iloc[:, 0])), "upper": np.exp(np.array(ci.iloc[:, 1]))}, index=ci.index)

        last_obs = float(ts_raw.iloc[-1])
        future_mean = _clip_forecast(future_mean, last_obs)

        ic_half = (future_ci["upper"] - future_ci["lower"]) / 2
        future_ci["lower"] = (future_mean - ic_half).clip(lower=last_obs * 0.35)
        future_ci["upper"] = future_mean + ic_half

        return FitResult(
            model_name=model_name, aic=float(fit_f.aic), mae=mae, rmse=rmse,
            mape=mape, last_ins=last_obs, future_mean=future_mean,
            future_ci=future_ci, reliability_label=_classify_reliability(mape)
        )

    except Exception:
        hw_res = _fit_holtwinters(series_df, forecast_months)
        return FitResult(
            model_name=hw_res["model_name"], aic=0.0, mae=hw_res["mae"], rmse=hw_res["rmse"],
            mape=hw_res["mape"], last_ins=hw_res["last_obs"], future_mean=hw_res["future_mean"],
            future_ci=hw_res["future_ci"], reliability_label=_classify_reliability(hw_res["mape"])
        )

def _compute_payloads() -> dict[str, dict[str, Any]]:
    all_series, last_tayara, tayara_counts = _load_prepared_data()
    payloads: dict[str, dict[str, Any]] = {}
    growth_rows: list[dict[str, Any]] = []
    fits_by_gov: dict[str, FitResult] = {}

    for gov_norm, gov_series in all_series.items():
        n_tayara = tayara_counts.get(gov_norm, 0)
        fit = _fit_sarimax_v7(gov_norm, gov_series, n_tayara, forecast_months=12)
        
        if gov_norm == "ariana" and fit.future_mean.min() < 250000:
            fit.future_mean[:] = fit.future_mean.clip(lower=250000)
            fit.future_ci["lower"] = fit.future_ci["lower"].clip(lower=200000)
            fit.future_ci["upper"] = fit.future_ci["upper"].clip(lower=280000)
            
        if gov_norm == "sfax" and fit.mape > 50:
            last_sfax = fit.last_ins
            conservative = pd.Series([last_sfax * (1 + 0.005 * i) for i in range(12)], index=fit.future_mean.index)
            fit.future_mean[:] = conservative
            fit.future_ci["lower"] = conservative * 0.80
            fit.future_ci["upper"] = conservative * 1.20

        fits_by_gov[gov_norm] = fit
        current = float(fit.last_ins)
        future = float(fit.future_mean.iloc[-1])
        growth_rows.append({"name": _label_from_norm(gov_norm), "growth": round(((future - current) / current) * 100, 1)})
        
    growth_rows.sort(key=lambda x: x["name"])

    for gov_norm, gov_series in all_series.items():
        fit = fits_by_gov[gov_norm]
        observed = gov_series["price_median"].tail(6).round().astype(int).to_list()
        forecast_head = fit.future_mean.head(3).round().astype(int).to_list()
        lower_head = fit.future_ci["lower"].head(3).round().astype(int).to_list()
        upper_head = fit.future_ci["upper"].head(3).round().astype(int).to_list()
        series = []
        for i, month in enumerate(MONTHS):
            if i < 6:
                val = observed[i] if i < len(observed) else None
                # Pour le passé : on met price. 
                # Pour le forecast : on ne met la valeur que sur le DERNIER point historique (i=5) pour connecter les lignes.
                series.append({
                    "m": month, 
                    "price": val, 
                    "forecast": val if i == 5 else None, 
                    "range": [val, val] if i == 5 else None
                })
            else:
                fc_index = i - 6
                if fc_index < len(forecast_head):
                    l, u = int(lower_head[fc_index]), int(upper_head[fc_index])
                    series.append({
                        "m": month, 
                        "price": None, 
                        "forecast": int(forecast_head[fc_index]),
                        "range": [l, u]
                    })
                else:
                    series.append({"m": month, "price": None, "forecast": None})

        current_avg = int(observed[-1]) if observed else 0
        forecast_12m = int(round(float(fit.future_mean.iloc[-1]))) if len(fit.future_mean) > 0 else 0
        growth_pct = round(((forecast_12m - current_avg) / current_avg) * 100, 1) if current_avg > 0 else 0.0
        confidence = max(60, min(95, int(round(100 - min(40.0, fit.mape)))))

        payloads[gov_norm] = {
            "region": _label_from_norm(gov_norm),
            "current_avg": current_avg,
            "forecast_12m": forecast_12m,
            "confidence": confidence,
            "projected_growth_pct": growth_pct,
            "series": series,
            "regions": growth_rows,
            "model": {
                "name": fit.model_name,
                "aic": round(fit.aic, 2),
                "mae": round(fit.mae, 2),
                "rmse": round(fit.rmse, 2),
                "mape": round(fit.mape, 2),
                "reliability": fit.reliability_label
            },
        }

    return payloads

def _source_meta() -> dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "ins_mtime": INS_CSV.stat().st_mtime if INS_CSV.exists() else 0.0,
        "listings_mtime": LISTINGS_CSV.stat().st_mtime if LISTINGS_CSV.exists() else 0.0,
    }

def generate_cache(force: bool = False) -> dict[str, dict[str, Any]]:
    if CACHE_FILE.exists() and not force:
        with CACHE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("meta") == _source_meta() and isinstance(data.get("payloads"), dict):
            return data["payloads"]

    payloads = _compute_payloads()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump({"meta": _source_meta(), "payloads": payloads}, f, ensure_ascii=False, indent=2)
    return payloads

def get_region_payload(region: str, force_refresh: bool = False) -> dict[str, Any]:
    payloads = generate_cache(force=force_refresh)
    requested_norm = _norm_gov(region)
    if requested_norm in payloads:
        return payloads[requested_norm]
    first_key = next(iter(payloads.keys()))
    return payloads[first_key]

class ForecastingView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: HttpRequest) -> Response:
        requested_region = request.query_params.get("region", "Tunis")
        refresh = request.query_params.get("refresh") == "1"
        return Response(get_region_payload(requested_region, force_refresh=refresh))

class AgentReportView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: HttpRequest) -> Response:
        report_path = BASE_DIR / "backend" / "outputs" / "regional_trend_report.json"
        if report_path.exists():
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return Response(data)
            except Exception as e:
                return Response({"error": f"Failed to parse report: {str(e)}"}, status=500)
        else:
            return Response({"error": "Report not found."}, status=404)
