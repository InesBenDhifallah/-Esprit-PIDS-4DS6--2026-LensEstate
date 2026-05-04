from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
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

BASE_DIR = Path(__file__).resolve().parents[2]
INS_CSV = BASE_DIR / "ins_ipim_by_governorate.csv"
LISTINGS_CSV = BASE_DIR / "final_dataset_with_dates.csv"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
warnings.filterwarnings("ignore", category=ConvergenceWarning)


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


def _norm_gov(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("�", "e")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return text


def _label_from_norm(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def _safe_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual > 0.01
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


def _remove_outliers(group: pd.DataFrame) -> pd.DataFrame:
    q5 = group["price"].quantile(0.05)
    q95 = group["price"].quantile(0.95)
    return group[(group["price"] >= q5) & (group["price"] <= q95)]


@lru_cache(maxsize=1)
def _load_prepared_data() -> tuple[dict[str, pd.DataFrame], dict[str, float | None]]:
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
    tayara = tayara.groupby("gov_norm", group_keys=False).apply(_remove_outliers)
    tayara["month_dt"] = tayara["date_posted"].dt.to_period("M").dt.to_timestamp()

    monthly_tayara = (
        tayara.groupby(["gov_norm", "month_dt"])["price"]
        .agg(price_median="median", n_listings="count")
        .reset_index()
        .sort_values(["gov_norm", "month_dt"])
    )

    all_series: dict[str, pd.DataFrame] = {}
    last_tayara: dict[str, float | None] = {}

    for gov_norm, gov_ins in ins.groupby("gov_norm"):
        gov_ins = gov_ins[["date", "ins_ipim_index"]].copy().sort_values("date")
        if gov_ins.empty:
            continue
        gov_ins = gov_ins.set_index("date")

        tay_gov = monthly_tayara[monthly_tayara["gov_norm"] == gov_norm].copy()
        if tay_gov.empty:
            tnd_per_ins = 2500.0
            last_tay = None
        else:
            tay_cal = tay_gov[tay_gov["n_listings"] >= 3].copy()
            if len(tay_cal) < 2:
                tay_cal = tay_gov

            ratios: list[float] = []
            for _, row in tay_cal.iterrows():
                dt = row["month_dt"]
                ins_match = gov_ins[gov_ins.index <= dt]
                if ins_match.empty:
                    continue
                ins_val = float(ins_match.iloc[-1]["ins_ipim_index"])
                if ins_val > 0 and pd.notna(row["price_median"]) and row["price_median"] > 0:
                    ratios.append(float(row["price_median"]) / ins_val)
            tnd_per_ins = float(np.median(ratios)) if ratios else 2500.0
            last_tay = float(tay_gov.iloc[-1]["price_median"]) if not tay_gov.empty else None

        series = gov_ins.copy()
        series["price_median"] = series["ins_ipim_index"] * tnd_per_ins
        series = series.resample("MS").last().ffill()

        all_series[gov_norm] = series
        last_tayara[gov_norm] = last_tay

    return all_series, last_tayara


def _fit_sarimax_v6(gov_norm: str, series: pd.DataFrame, last_tayara_price: float | None, forecast_months: int = 12) -> FitResult:
    ts_raw = series["price_median"].dropna().copy()
    ts_log = np.log(ts_raw.clip(lower=1))
    n = len(ts_raw)
    train_size = int(n * 0.85)
    train_log = ts_log.iloc[:train_size]
    test_log = ts_log.iloc[train_size:]

    orders = [
        ((1, 1, 1), (1, 1, 1, 12), "SARIMAX(1,1,1)(1,1,1,12)"),
        ((1, 1, 1), (0, 1, 1, 12), "SARIMAX(1,1,1)(0,1,1,12)"),
        ((1, 1, 0), (1, 1, 0, 12), "SARIMAX(1,1,0)(1,1,0,12)"),
        ((1, 1, 0), (0, 1, 1, 12), "SARIMAX(1,1,0)(0,1,1,12)"),
        ((2, 1, 1), (1, 1, 0, 12), "SARIMAX(2,1,1)(1,1,0,12)"),
        ((1, 1, 1), (0, 0, 0, 0), "ARIMA(1,1,1)"),
    ]

    best_fit = None
    best_aic = np.inf
    best_name = ""
    best_order = (1, 1, 0)
    best_sorder = (0, 0, 0, 0)

    for order, sorder, name in orders:
        try:
            model = SARIMAX(
                train_log,
                order=order,
                seasonal_order=sorder,
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fit = model.fit(disp=False, maxiter=400, method="lbfgs")
            if fit.aic < best_aic:
                best_aic = float(fit.aic)
                best_fit = fit
                best_name = name
                best_order = order
                best_sorder = sorder
        except Exception:
            continue

    if best_fit is None:
        fallback = SARIMAX(
            train_log,
            order=(1, 1, 0),
            seasonal_order=(0, 0, 0, 0),
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        best_fit = fallback.fit(disp=False, maxiter=200)
        best_name = "ARIMA(1,1,0)"

    try:
        fc_test = best_fit.get_forecast(steps=len(test_log))
        pred_tnd = np.exp(np.array(fc_test.predicted_mean))
    except Exception:
        pred_tnd = np.exp(train_log.iloc[-len(test_log) :].values)

    test_tnd = np.exp(test_log.values)
    mae = float(mean_absolute_error(test_tnd, pred_tnd))
    rmse = float(np.sqrt(mean_squared_error(test_tnd, pred_tnd)))
    mape = _safe_mape(test_tnd, pred_tnd)

    try:
        m_final = SARIMAX(
            ts_log,
            order=best_order,
            seasonal_order=best_sorder,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        fit_final = m_final.fit(disp=False, maxiter=400, method="lbfgs")
    except Exception:
        fit_final = best_fit

    try:
        fc_future = fit_final.get_forecast(steps=forecast_months)
        future_tnd = np.exp(np.array(fc_future.predicted_mean))
        ci = fc_future.conf_int(alpha=0.20)
        ci_lower = np.exp(np.array(ci.iloc[:, 0]))
        ci_upper = np.exp(np.array(ci.iloc[:, 1]))
    except Exception:
        last_val = float(ts_raw.iloc[-1])
        trend_12 = float((ts_raw.iloc[-1] - ts_raw.iloc[-13]) / 12) if len(ts_raw) > 13 else 0.0
        future_tnd = np.array([last_val + trend_12 * (i + 1) for i in range(forecast_months)])
        ci_lower = future_tnd * 0.87
        ci_upper = future_tnd * 1.13

    last_ins_price = float(ts_raw.iloc[-1])
    if last_tayara_price and last_tayara_price > 0:
        anchor_ratio = float(last_tayara_price) / last_ins_price
        anchor_weights = np.linspace(anchor_ratio, 1.0, forecast_months)
        future_tnd = future_tnd * anchor_weights
        ci_lower = ci_lower * anchor_weights
        ci_upper = ci_upper * anchor_weights

    ref_price = float(last_tayara_price) if last_tayara_price else last_ins_price
    max_bound = ref_price * 1.50
    min_bound = ref_price * 0.60
    future_tnd_c = np.clip(future_tnd, min_bound, max_bound)
    ratio_clip = np.where(future_tnd != 0, future_tnd_c / future_tnd, 1.0)
    ci_lower_c = ci_lower * ratio_clip
    ci_upper_c = ci_upper * ratio_clip

    future_idx = _make_future_index(ts_raw.index[-1], forecast_months)
    return FitResult(
        model_name=best_name,
        aic=best_aic,
        mae=mae,
        rmse=rmse,
        mape=mape,
        last_ins=last_ins_price,
        future_mean=pd.Series(future_tnd_c, index=future_idx),
        future_ci=pd.DataFrame({"lower": ci_lower_c, "upper": ci_upper_c}, index=future_idx),
    )


@lru_cache(maxsize=16)
def _build_payload(region: str) -> dict[str, Any]:
    all_series, last_tayara = _load_prepared_data()
    requested_norm = _norm_gov(region)
    if requested_norm not in all_series:
        requested_norm = next(iter(all_series.keys()))

    fit = _fit_sarimax_v6(requested_norm, all_series[requested_norm], last_tayara.get(requested_norm), forecast_months=12)
    observed = all_series[requested_norm]["price_median"].tail(6).round().astype(int).to_list()
    forecast_head = fit.future_mean.head(3).round().astype(int).to_list()

    series: list[dict[str, Any]] = []
    for i, month in enumerate(MONTHS):
        if i < 6:
            series.append({"m": month, "price": observed[i], "forecast": observed[i]})
        else:
            series.append({"m": month, "price": None, "forecast": int(forecast_head[i - 6])})

    region_growth: list[dict[str, Any]] = []
    for gov_norm, gov_series in all_series.items():
        gov_fit = _fit_sarimax_v6(gov_norm, gov_series, last_tayara.get(gov_norm), forecast_months=12)
        current = float(gov_fit.last_ins)
        future = float(gov_fit.future_mean.iloc[-1])
        growth = round(((future - current) / current) * 100, 1)
        region_growth.append({"name": _label_from_norm(gov_norm), "growth": growth})
    region_growth.sort(key=lambda x: x["name"])

    current_avg = int(observed[-1])
    forecast_12m = int(round(float(fit.future_mean.iloc[-1])))
    growth_pct = round(((forecast_12m - current_avg) / current_avg) * 100, 1)
    confidence = max(60, min(95, int(round(100 - min(40.0, fit.mape)))))

    return {
        "region": _label_from_norm(requested_norm),
        "current_avg": current_avg,
        "forecast_12m": forecast_12m,
        "confidence": confidence,
        "projected_growth_pct": growth_pct,
        "series": series,
        "regions": region_growth,
    }


class ForecastingView(APIView):
    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: HttpRequest) -> Response:
        requested_region = request.query_params.get("region", "Tunis")
        return Response(_build_payload(requested_region))
