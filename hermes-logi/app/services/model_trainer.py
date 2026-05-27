"""
Model training:
  Step 1: 생산량 → movement  (EWMA-weighted OLS + breakpoint detection)
  Step 2: movement → 반송량  (DR×line EWMA OLS)
  Step 3: 반송량 → 반송시간  (queuing curve_fit: base_time + a_line)
  Storage: product storage  (LightGBM)
"""
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.linear_model import LinearRegression
import lightgbm as lgb
import joblib
import os
from pathlib import Path

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "model_store"))


def _ewma_weights(n: int, lam: float = 0.1) -> np.ndarray:
    """Exponential decay weights, newest data = weight 1."""
    ages = np.arange(n - 1, -1, -1, dtype=float)
    w = np.exp(-lam * ages)
    return w / w.sum() * n  # scale so sum = n (compatible with sample_weight)


def _detect_breakpoint(series: pd.Series, threshold: float = 0.15) -> int | None:
    """Return index of most recent month where 3-month avg changes by >threshold."""
    vals = series.values
    for i in range(len(vals) - 1, 2, -1):
        prev_avg = vals[max(0, i - 3) : i].mean()
        if prev_avg == 0:
            continue
        if abs(vals[i] - prev_avg) / prev_avg > threshold:
            return i
    return None


def _weighted_ols(X: np.ndarray, y: np.ndarray, weights: np.ndarray):
    reg = LinearRegression()
    reg.fit(X, y, sample_weight=weights)
    return reg


# ──────────────────────────────────────────────
# Step 1: 생산량 → movement
# ──────────────────────────────────────────────

def train_movement_model(df: pd.DataFrame, lam: float = 0.1) -> dict:
    """
    df must have: site, line, floor, dr_type, actual_month,
                  movement_actual (y), movement_plan (X) — plan of same month as actuals.
    Returns per-(site, line, dr_type) coefficients + breakpoint info.
    """
    results = {}
    groups = df.groupby(["site", "line", "dr_type"])

    for key, grp in groups:
        grp = grp.sort_values("actual_month").dropna(subset=["movement_actual", "movement_plan"])
        if len(grp) < 3:
            continue

        bp = _detect_breakpoint(grp["movement_plan"], threshold=0.15)
        if bp is not None and len(grp) - bp >= 3:
            grp = grp.iloc[bp:]  # use post-breakpoint data only

        n = len(grp)
        X = grp["movement_plan"].values.reshape(-1, 1)
        y = grp["movement_actual"].values
        w = _ewma_weights(n, lam)

        reg = _weighted_ols(X, y, w)
        r2 = reg.score(X, y, sample_weight=w)

        results[key] = {
            "coef": float(reg.coef_[0]),
            "intercept": float(reg.intercept_),
            "r2": round(r2, 4),
            "n": n,
            "breakpoint_detected": bp is not None,
        }

    path = MODEL_DIR / "movement" / "coefficients.joblib"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(results, path)
    return results


def predict_movement(movement_plan: float, site: str, line: str, dr_type: str) -> float:
    path = MODEL_DIR / "movement" / "coefficients.joblib"
    results = joblib.load(path)
    key = (site, line, dr_type)
    if key not in results:
        # fallback: identity
        return movement_plan
    c = results[key]
    return c["coef"] * movement_plan + c["intercept"]


# ──────────────────────────────────────────────
# Step 2: movement → 반송량
# ──────────────────────────────────────────────

def train_transport_count_model(df: pd.DataFrame, dr_steps: dict, lam: float = 0.1) -> dict:
    """
    df: actuals with movement_actual, transport_count_actual, dr_type, line.
    dr_steps: {dr_type: step_count}
    Features: [movement, movement × step_count]
    """
    results = {}
    groups = df.groupby(["site", "line", "dr_type"])

    for key, grp in groups:
        site, line, dr_type = key
        grp = grp.sort_values("actual_month").dropna(
            subset=["movement_actual", "transport_count_actual"]
        )
        if len(grp) < 3:
            continue

        steps = dr_steps.get(dr_type, 1)
        n = len(grp)
        mv = grp["movement_actual"].values
        X = np.column_stack([mv, mv * steps])
        y = grp["transport_count_actual"].values
        w = _ewma_weights(n, lam)

        reg = _weighted_ols(X, y, w)
        r2 = reg.score(X, y, sample_weight=w)

        results[key] = {
            "coef_movement": float(reg.coef_[0]),
            "coef_movement_x_steps": float(reg.coef_[1]),
            "intercept": float(reg.intercept_),
            "r2": round(r2, 4),
            "n": n,
            "dr_steps": steps,
        }

    path = MODEL_DIR / "transport_count" / "coefficients.joblib"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(results, path)
    return results


def predict_transport_count(
    movement: float, site: str, line: str, dr_type: str, dr_steps: int
) -> float:
    path = MODEL_DIR / "transport_count" / "coefficients.joblib"
    results = joblib.load(path)
    key = (site, line, dr_type)
    if key not in results:
        # fallback: use dr_type-agnostic key by searching same site+line
        fallback = next(
            (v for k, v in results.items() if k[0] == site and k[1] == line), None
        )
        if fallback is None:
            return movement * dr_steps * 10  # crude default
        c = fallback
    else:
        c = results[key]
    return c["coef_movement"] * movement + c["coef_movement_x_steps"] * movement * dr_steps + c["intercept"]


# ──────────────────────────────────────────────
# Step 3: 반송량 → 반송시간 (queuing model)
# ──────────────────────────────────────────────

def _queuing_model(transport_count, base_time, a, oht_capacity_seconds):
    """M/G/1 approximation. oht_capacity_seconds = OHT_count × monthly_hours × 3600."""
    rho = transport_count * base_time / oht_capacity_seconds
    rho = np.clip(rho, 1e-6, 0.999)
    return base_time * (1 + a * rho / (1 - rho))


def train_transport_time_model(
    df: pd.DataFrame, floor_config: pd.DataFrame, lam: float = 0.1
) -> dict:
    """
    df: actuals with transport_count_actual, transport_time_actual.
    floor_config: site, floor, line, oht_count, oht_monthly_hours
    """
    # Merge OHT capacity into actuals
    oht = floor_config.groupby(["site", "floor"]).agg(
        oht_count=("oht_count", "first"),
        oht_monthly_hours=("oht_monthly_hours", "first"),
    ).reset_index()
    df = df.merge(oht, on=["site", "floor"], how="left")
    df["oht_capacity_sec"] = df["oht_count"] * df["oht_monthly_hours"] * 3600

    results = {}
    groups = df.groupby(["site", "line", "floor", "dr_type"])

    for key, grp in groups:
        grp = grp.sort_values("actual_month").dropna(
            subset=["transport_count_actual", "transport_time_actual", "oht_capacity_sec"]
        )
        if len(grp) < 4:
            continue

        cap = grp["oht_capacity_sec"].iloc[0]
        X = grp["transport_count_actual"].values
        y = grp["transport_time_actual"].values

        min_time = float(y.min())
        min_rho = float((X * min_time / cap).min())
        base_time_p0 = min_time * max(1 - min_rho, 0.1)

        try:
            popt, pcov = curve_fit(
                lambda tc, bt, a: _queuing_model(tc, bt, a, cap),
                X, y,
                p0=[base_time_p0, 0.5],
                bounds=([0, 0], [np.inf, np.inf]),
                maxfev=5000,
            )
            base_time, a_line = float(popt[0]), float(popt[1])
            perr = np.sqrt(np.diag(pcov))
            y_pred = _queuing_model(X, base_time, a_line, cap)
            ss_res = ((y - y_pred) ** 2).sum()
            ss_tot = ((y - y.mean()) ** 2).sum()
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

            results[key] = {
                "base_time": base_time,
                "a_line": a_line,
                "base_time_stderr": float(perr[0]),
                "a_line_stderr": float(perr[1]),
                "r2": round(r2, 4),
                "n": len(grp),
                "oht_capacity_sec": cap,
            }
        except RuntimeError:
            # curve_fit failed: store linear fallback
            reg = LinearRegression().fit(X.reshape(-1, 1), y)
            results[key] = {
                "base_time": None,
                "a_line": None,
                "linear_coef": float(reg.coef_[0]),
                "linear_intercept": float(reg.intercept_),
                "r2": round(reg.score(X.reshape(-1, 1), y), 4),
                "n": len(grp),
                "oht_capacity_sec": cap,
                "fallback": True,
            }

    path = MODEL_DIR / "transport_time" / "coefficients.joblib"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(results, path)
    return results


def predict_transport_time(
    transport_count: float, site: str, line: str, floor: str, dr_type: str
) -> dict:
    """Returns predicted transport_time and utilization rho."""
    path = MODEL_DIR / "transport_time" / "coefficients.joblib"
    results = joblib.load(path)
    key = (site, line, floor, dr_type)

    # Try exact key, then without dr_type, then site+floor
    for lookup in [key, (site, line, floor, ""), (site, "", floor, "")]:
        c = results.get(lookup)
        if c:
            break

    if c is None:
        return {"transport_time": 60.0, "rho": None, "fallback": True}

    if c.get("fallback"):
        t = c["linear_coef"] * transport_count + c["linear_intercept"]
        return {"transport_time": max(t, 1.0), "rho": None, "fallback": True}

    cap = c["oht_capacity_sec"]
    rho = transport_count * c["base_time"] / cap
    rho = min(rho, 0.999)
    t = c["base_time"] * (1 + c["a_line"] * rho / (1 - rho))
    return {"transport_time": t, "rho": rho, "fallback": False}


# ──────────────────────────────────────────────
# Storage: product storage (LightGBM)
# ──────────────────────────────────────────────

STORAGE_FEATURES = ["wip_plan_or_actual", "lot_size", "dr_step_count", "month_of_year"]


def train_storage_model(df: pd.DataFrame, dr_steps: dict) -> dict:
    """
    df: merged plan+actual with wip, lot_size, dr_type, storage_product_actual, actual_month.
    Returns per-(site, line) model metadata; models saved to disk.
    """
    df = df.copy()
    df["dr_step_count"] = df["dr_type"].map(dr_steps).fillna(1)
    df["month_of_year"] = pd.to_datetime(df["actual_month"]).dt.month
    df = df.rename(columns={"wip_plan": "wip_plan_or_actual"})

    results = {}
    groups = df.groupby(["site", "line"])

    for key, grp in groups:
        grp = grp.dropna(subset=["storage_product_actual"] + STORAGE_FEATURES)
        if len(grp) < 6:
            continue

        X = grp[STORAGE_FEATURES].values
        y = grp["storage_product_actual"].values

        model = lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=15, verbose=-1)
        model.fit(X, y)
        y_pred = model.predict(X)
        ss_res = ((y - y_pred) ** 2).sum()
        ss_tot = ((y - y.mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        model_path = MODEL_DIR / "storage_product" / f"{'_'.join(key)}.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)

        results[key] = {"r2": round(r2, 4), "n": len(grp), "model_path": str(model_path)}

    return results


def predict_storage_product(
    wip: float, lot_size: float, dr_type: str, dr_steps: int,
    month_of_year: int, site: str, line: str,
) -> float:
    model_path = MODEL_DIR / "storage_product" / f"{site}_{line}.joblib"
    if not model_path.exists():
        # Linear fallback: wip × lot_size_factor
        return wip * (lot_size / 25) if lot_size else wip
    model = joblib.load(model_path)
    X = np.array([[wip, lot_size, dr_steps, month_of_year]])
    return float(model.predict(X)[0])
