"""As-of 28-day M5 forecasting, planning exceptions and illustrative replenishment.

Run: python -m src.pipeline --data-dir data/raw --output-dir results
"""
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

FILES = {
    "calendar.csv": "3ffeab2991b0c8e861d008b39ea4c95c",
    "sales_train_validation.csv": "26a366a25beb57b0a8f4c7b148758f94",
    "sell_prices.csv": "08c591caa99e55daf3e0ccac913f7c85",
}
STORES = ("CA_1", "CA_2", "CA_3")
FIRST_DAY = 1200
TRAIN_START, TRAIN_END = 1290, 1801
CAL_START, CAL_END = 1802, 1857
TEST_START, TEST_END = 1858, 1913
NUM_ITEMS = 120
LAGS = (28, 35, 42, 49, 56)
FEATURES = [
    "item_code", "store_code", "dept_code", "weekday", "month", "event_flag",
    "snap", "lag_28", "lag_35", "lag_42", "lag_49", "lag_56",
    "mean_28_shift28", "mean_56_shift28", "nonzero_28_shift28",
]


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_sources(data_dir: Path, verify: bool) -> None:
    for name, expected in FILES.items():
        file = data_dir / name
        if not file.is_file():
            raise FileNotFoundError(f"Missing {file}; see README for download instructions")
        if verify and md5(file) != expected:
            raise ValueError(f"Checksum mismatch: {file}")


def load_panel(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    meta = ["item_id", "dept_id", "store_id", "cat_id"]
    days = [f"d_{i}" for i in range(FIRST_DAY, TEST_END + 1)]
    sales = pd.read_csv(data_dir / "sales_train_validation.csv", usecols=meta + days)
    # Selection uses only information available by the end of model training.
    ranking_days = [f"d_{i}" for i in range(1650, TRAIN_END + 1)]
    eligible = sales.loc[sales.store_id.isin(STORES) & sales.cat_id.eq("FOODS")].copy()
    eligible["selection_units"] = eligible[ranking_days].sum(axis=1)
    selected = (eligible.groupby("item_id").selection_units.sum()
                .sort_values(ascending=False).head(NUM_ITEMS).index)
    selected = sorted(selected)
    panel = eligible[eligible.item_id.isin(selected)].drop(columns="selection_units")
    if len(panel) != NUM_ITEMS * len(STORES):
        raise ValueError("Expected complete item-store coverage")
    panel = panel.melt(id_vars=meta, value_vars=days, var_name="d", value_name="units")
    panel["day"] = panel.d.str[2:].astype("int16")
    panel["units"] = panel.units.astype("float32")
    panel = panel.sort_values(["item_id", "store_id", "day"]).reset_index(drop=True)

    cal = pd.read_csv(data_dir / "calendar.csv")
    cal["day"] = cal.d.str[2:].astype("int16")
    cal["weekday"] = pd.to_datetime(cal.date).dt.dayofweek.astype("int8")
    cal["event_flag"] = cal.event_name_1.notna().astype("int8")
    keep = ["day", "date", "wm_yr_wk", "weekday", "month", "event_name_1", "event_flag", "snap_CA"]
    panel = panel.merge(cal[keep], on="day", validate="many_to_one")
    panel = panel.rename(columns={"snap_CA": "snap"})
    for name, column in [("item_code", "item_id"), ("store_code", "store_id"), ("dept_code", "dept_id")]:
        panel[name] = pd.Categorical(panel[column]).codes.astype("int16")
    groups = panel.groupby(["item_id", "store_id"], sort=False).units
    for lag in LAGS:
        panel[f"lag_{lag}"] = groups.shift(lag)
    for window in (28, 56):
        panel[f"mean_{window}_shift28"] = groups.transform(
            lambda s: s.shift(28).rolling(window, min_periods=window).mean()
        )
    panel["nonzero_28_shift28"] = groups.transform(
        lambda s: s.gt(0).shift(28).rolling(28, min_periods=28).mean()
    )
    if panel.loc[panel.day.ge(TRAIN_START), FEATURES].isna().any().any():
        raise AssertionError("Unexpected missing model features")
    selection = {"stores": list(STORES), "items": NUM_ITEMS, "series": len(selected) * len(STORES),
                 "selection_days": [1650, TRAIN_END], "item_ids": selected}
    return panel, cal, selection


def baseline(frame: pd.DataFrame) -> np.ndarray:
    return np.maximum(0, frame[["lag_28", "lag_35", "lag_42", "lag_49"]].mean(axis=1).to_numpy())


def metrics(frame: pd.DataFrame, column: str) -> dict:
    actual = frame.units.to_numpy(float)
    predicted = frame[column].to_numpy(float)
    denom = max(actual.sum(), 1)
    return {"rows": int(len(frame)), "actual_units": round(actual.sum(), 1),
            "wape": round(100 * np.abs(actual - predicted).sum() / denom, 2),
            "bias_pct": round(100 * (predicted.sum() - actual.sum()) / denom, 2),
            "mae": round(np.abs(actual - predicted).mean(), 3)}


def forecast(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    train = panel[panel.day.between(TRAIN_START, TRAIN_END)]
    calibration = panel[panel.day.between(CAL_START, CAL_END)].copy()
    test = panel[panel.day.between(TEST_START, TEST_END)].copy()
    model = HistGradientBoostingRegressor(
        max_iter=160, max_leaf_nodes=31, learning_rate=0.07,
        min_samples_leaf=40, l2_regularization=1, early_stopping=False,
        categorical_features=["item_code", "store_code", "dept_code", "weekday", "month", "event_flag", "snap"],
        random_state=42,
    )
    model.fit(train[FEATURES], train.units)
    calibration["model"] = np.maximum(0, model.predict(calibration[FEATURES]))
    test["model"] = np.maximum(0, model.predict(test[FEATURES]))
    calibration["baseline"] = baseline(calibration)
    test["baseline"] = baseline(test)
    # A realistic candidate manual override: calibrate store bias using only
    # the calibration window. Backtest it rather than presuming it helps.
    factors = (calibration.groupby("store_id").units.sum()
               / calibration.groupby("store_id").model.sum()).clip(0.8, 1.2)
    test["calibrated_override"] = test.model * test.store_id.map(factors).astype(float)
    # Empirical interval for individual daily sales; calibrated on a later, unseen period.
    residual = np.abs(calibration.units - calibration.model)
    interval = float(np.quantile(residual, 0.90))
    test["low_90"] = np.maximum(0, test.model - interval)
    test["high_90"] = test.model + interval
    # Every future target day uses actuals from at least 28 days earlier.
    # Thus each 28-day block can be scored at its start without peeking inside it.
    test["origin_day"] = np.where(test.day < 1886, 1857, 1885)
    assert (test.day - test.origin_day).between(1, 28).all()
    assert (test.day - 28 <= test.origin_day).all()
    return calibration, test, interval


def inventory_policy(forecasts: np.ndarray, demand: np.ndarray, initial_stock: int,
                     lead_days: int = 2, shelf_days: int = 7,
                     pack: int = 6) -> dict:
    """Daily order-up-to experiment; observed sales stand in for latent demand.

    At close of day t, order target demand for t+1..t+lead+1. The horizon
    needs two extra forecast days, so simulate at most n-lead-1 days.
    """
    inventory = [0] * shelf_days
    inventory[0] = int(initial_stock)
    inbound: dict[int, int] = {}
    lost = waste = ordered = served = 0.0
    horizon = max(0, len(demand) - lead_days - 1)
    for t in range(horizon):
        inventory[0] += inbound.pop(t, 0)
        required = max(0, float(demand[t]))
        served_today = 0.0
        # Consume oldest stock first, preserving newly delivered products.
        for age in range(shelf_days - 1, -1, -1):
            take = min(inventory[age], required - served_today)
            inventory[age] -= take
            served_today += take
        served += served_today
        lost += required - served_today
        waste += inventory[-1]
        inventory = [0] + inventory[:-1]
        if t + lead_days >= horizon:
            continue
        future_end = min(horizon, t + lead_days + 2)
        target = np.maximum(0, forecasts[t + 1:future_end]).sum()
        position = sum(inventory) + sum(q for day, q in inbound.items() if day <= t + lead_days)
        order = int(pack * math.ceil(max(0, target - position) / pack))
        inbound[t + lead_days] = inbound.get(t + lead_days, 0) + order
        ordered += order
    return {"demand": round(float(np.maximum(0, demand[:horizon]).sum()), 1),
            "served": round(served, 1), "lost": round(lost, 1),
            "waste": round(waste, 1), "ordered": round(ordered, 1),
            "ending_stock": round(sum(inventory) + sum(inbound.values()), 1),
            "days": horizon}


def simulate(test: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    recent = panel[panel.day.between(TEST_START - 28, TEST_START - 1)]
    init = recent.groupby(["store_id", "item_id"]).units.mean().mul(3).clip(lower=6)
    records = []
    first = test[test.day.between(1858, 1885)]
    for (store, item), g in first.groupby(["store_id", "item_id"]):
        g = g.sort_values("day")
        stock = int(math.ceil(init.loc[store, item] / 6) * 6)
        for policy in ("baseline", "model"):
            result = inventory_policy(g[policy].to_numpy(), g.units.to_numpy(), stock)
            records.append({"store_id": store, "item_id": item, "policy": policy, **result})
    return pd.DataFrame(records)


def price_and_exceptions(data_dir: Path, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = pd.read_csv(data_dir / "sell_prices.csv", usecols=["item_id", "store_id", "wm_yr_wk", "sell_price"])
    scoped = prices[prices.item_id.isin(test.item_id.unique()) & prices.store_id.isin(STORES)]
    test = test.merge(scoped, on=["item_id", "store_id", "wm_yr_wk"], how="left", validate="many_to_one")
    # Observed future prices are used for ex-post materiality only, not as model features.
    test["estimated_revenue"] = test.units * test.sell_price
    test["forecast_delta"] = test.model - test.baseline
    test["absolute_error"] = (test.model - test.units).abs()
    per_item = test.groupby(["item_id", "store_id", "dept_id"], as_index=False).agg(
        model_units=("model", "sum"), baseline_units=("baseline", "sum"),
        actual_units=("units", "sum"), abs_error=("absolute_error", "sum"),
        avg_price=("sell_price", "mean"),
    )
    per_item["estimated_error_value_usd"] = (per_item.abs_error * per_item.avg_price).round(2)
    per_item["bias_units"] = (per_item.model_units - per_item.actual_units).round(1)
    per_item["action"] = np.where(per_item.bias_units < -15,
                                  "Review availability / demand uplift", "Review excess / forecast bias")
    return test, per_item.sort_values("estimated_error_value_usd", ascending=False)


def charts(test: pd.DataFrame, output: Path) -> None:
    daily = test.groupby(["date", "origin_day"], as_index=False)[["units", "baseline", "model"]].sum()
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.plot(daily.date, daily.units, label="Observed unit sales", lw=2, color="#153a50")
    ax.plot(daily.date, daily.baseline, label="Seasonal baseline", lw=1.5, color="#ac7544")
    ax.plot(daily.date, daily.model, label="ML forecast", lw=1.5, color="#2b907d")
    ax.set(xlabel="Date", ylabel="Units/day", title="Holdout forecasts | 120 food items × 3 California stores")
    positions = list(range(0, len(daily), 7))
    ax.set_xticks(positions, daily.date.iloc[positions].str[5:], rotation=0)
    ax.legend(frameon=False, ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "holdout_forecast.png", dpi=180)
    plt.close(fig)
    daily.to_csv(output / "daily_forecasts.csv", index=False)
    test.groupby(["store_id", "date", "origin_day"], as_index=False)[
        ["units", "baseline", "model"]].sum().to_csv(output / "store_daily_forecasts.csv", index=False)


def write_report(output: Path, test: pd.DataFrame, calibration: pd.DataFrame,
                 inventory: pd.DataFrame, interval: float, selection: dict) -> None:
    baseline_m, model_m = metrics(test, "baseline"), metrics(test, "model")
    override_m = metrics(test, "calibrated_override")
    test = test.copy()
    test["week_in_origin"] = ((test.day - test.origin_day - 1) // 7).astype(int)
    weekly = test.groupby(["item_id", "store_id", "origin_day", "week_in_origin"], as_index=False)[
        ["units", "model", "baseline"]].sum()
    four_week = test.groupby(["item_id", "store_id", "origin_day"], as_index=False)[
        ["units", "model", "baseline"]].sum()
    weekly_baseline, weekly_model = metrics(weekly, "baseline"), metrics(weekly, "model")
    four_baseline, four_model = metrics(four_week, "baseline"), metrics(four_week, "model")
    change = baseline_m["wape"] - model_m["wape"]
    coverage = 100 * test.units.between(test.low_90, test.high_90).mean()
    by_origin = [(int(origin), metrics(g, "baseline"), metrics(g, "model"))
                 for origin, g in test.groupby("origin_day")]
    by_store = [(store, metrics(g, "baseline"), metrics(g, "model"))
                for store, g in test.groupby("store_id")]
    suminv = inventory.groupby("policy")[["demand", "served", "lost", "waste", "ordered"]].sum().round(1)
    baseline_inv, model_inv = suminv.loc["baseline"], suminv.loc["model"]
    lines = [
        "# Executive decision brief | Item-store demand forecasting",
        "", "## Decision for a weekly S&OP forum", "",
        f"A global model forecast daily observed unit sales for {selection['items']} real food items across three M5 stores. "
        f"Across two held-out 28-day windows, model WAPE was **{model_m['wape']}%** versus "
        f"**{baseline_m['wape']}%** for a seasonal baseline "
        f"({change:+.2f} percentage points; a positive figure favours the model). "
        f"Signed bias was **{model_m['bias_pct']:+.2f}%**. "
        "This is a historical backtest, not a live business saving.",
        "", "## Validation and segmentation", "",
        "Window | Baseline WAPE | Model WAPE | Model bias | Observed units", "---|---:|---:|---:|---:",
    ]
    for origin, b, m in by_origin:
        lines.append(f"Day {origin+1}–{origin+28} | {b['wape']}% | {m['wape']}% | {m['bias_pct']:+.2f}% | {m['actual_units']:,.0f}")
    lines += ["", "Store | Baseline WAPE | Model WAPE | Model bias", "---|---:|---:|---:"]
    for store, b, m in by_store:
        lines.append(f"{store} | {b['wape']}% | {m['wape']}% | {m['bias_pct']:+.2f}%")
    lines += [
        "", f"A simple 90th-percentile calibration interval had ±{interval:.1f} units daily width "
        f"and {coverage:.1f}% observed coverage. This is a pooled illustrative interval, "
        "not a product-specific service-level guarantee.",
        "", "## Choosing the planning forecast", "",
        f"At item-store **weekly** level, the baseline WAPE was {weekly_baseline['wape']}% "
        f"versus {weekly_model['wape']}% for the model; at **28-day** level, "
        f"{four_baseline['wape']}% versus {four_model['wape']}%. "
        "The ML model's small daily advantage does not justify automatic adoption for order-volume planning. "
        "Pilot the model for daily exceptions, retain the seasonal baseline for weekly/28-day category review, "
        "and re-evaluate by horizon and store as more weeks arrive.",
        f"A store-level bias adjustment learned exclusively from calibration data "
        f"produced {override_m['wape']}% test WAPE and {override_m['bias_pct']:+.2f}% bias. "
        "Record this as an unsuccessful candidate override; do not apply it automatically.",
        "", "## Planning actions", "",
        "1. Commercial: review the largest model-versus-baseline changes alongside the known event calendar.",
        "2. Supply Chain: prioritise item-store exceptions in `priority_exceptions.csv`; review high-risk bias rather than overriding every line.",
        "3. Distribution: compare demand with the explicit capacity scenario in `capacity_scenario.csv`, then agree allocations and owners.",
        "4. Forecast owner: record any adjustment and its reason, and compare post-override errors with the original forecast.",
        "", "## Illustrative replenishment experiment", "",
        f"For the first holdout window, both order policies faced the same observed sales proxy, "
        f"starting stock and assumed two-day lead time, seven-day shelf life and six-unit case pack. "
        f"The simulation evaluates 25 days, allowing full look-ahead for its ordering rule. "
        f"The seasonal policy served {baseline_inv.served:,.0f} of {baseline_inv.demand:,.0f} units "
        f"and discarded {baseline_inv.waste:,.0f}; the ML policy served {model_inv.served:,.0f} "
        f"and discarded {model_inv.waste:,.0f}. Stock availability and shelf life are not in M5, "
        "so these outcomes are scenario results, not measured Walmart outcomes.",
        "", "## Promotional planning case", "",
        "`promotion_scenario.csv` models an assumed 20% uplift for one high-volume food item at CA_1 "
        "over seven days, then rounds incremental units to six-unit cases. This is a what-if exercise, "
        "not an estimated price elasticity or an observed promotion.",
        "", "## Known limitations", "",
        "- M5 records sales, not unrestricted demand; historical out-of-stocks and true lost sales are unknown.",
        "- M5 does not provide shelf life, stock on hand, supplier lead times, capacity or real forecast overrides. All such inputs are clearly simulated.",
        "- Prices are actual historical values used only after the forecast for approximate exception materiality in USD; future prices are not model inputs.",
        "- Calendar events are known ahead; all sales-derived features in each 28-day forecast are from before that window's origin.",
        "- Store and item sample was selected using only pre-test data, and performance cannot be assumed for Waitrose.",
        "", "## Evidence", "",
        "See `metrics.csv`, `holdout_forecast.png`, `priority_exceptions.csv`, `capacity_scenario.csv`, "
        "`replenishment_results.csv`, `data_quality.csv` and `run_manifest.txt`.", "",
    ]
    (output / "decision_brief.md").write_text("\n".join(lines))
    pd.DataFrame([
        {"segment": "overall", "policy": policy, **metrics(test, policy)}
        for policy in ("baseline", "model", "calibrated_override")
    ] + [
        {"segment": f"origin_{origin}", "policy": policy, **metrics(g, policy)}
        for origin, g in test.groupby("origin_day") for policy in ("baseline", "model")
    ] + [
        {"segment": f"store_{store}", "policy": policy, **metrics(g, policy)}
        for store, g in test.groupby("store_id") for policy in ("baseline", "model")
    ] + [
        {"segment": f"store_{store}_origin_{origin}", "policy": policy, **metrics(g, policy)}
        for (store, origin), g in test.groupby(["store_id", "origin_day"])
        for policy in ("baseline", "model")
    ] + [
        {"segment": "item_store_weekly", "policy": policy, **metrics(weekly, policy)}
        for policy in ("baseline", "model")
    ] + [
        {"segment": "item_store_28day", "policy": policy, **metrics(four_week, policy)}
        for policy in ("baseline", "model")
    ]).to_csv(output / "metrics.csv", index=False)
    print(f"Backtest: baseline WAPE {baseline_m['wape']}%; ML WAPE {model_m['wape']}%; bias {model_m['bias_pct']:+.2f}%")


def run(data_dir: Path, output: Path, verify: bool = True) -> None:
    check_sources(data_dir, verify)
    output.mkdir(parents=True, exist_ok=True)
    panel, cal, selection = load_panel(data_dir)
    calibration, test, interval = forecast(panel)
    inventory = simulate(test, panel)
    test, exception = price_and_exceptions(data_dir, test)
    exception.head(50).to_csv(output / "priority_exceptions.csv", index=False)
    from .sql_audit import build as build_sql_audit
    build_sql_audit(test, output)
    inventory.to_csv(output / "replenishment_results.csv", index=False)
    factors = (calibration.groupby("store_id").units.sum()
               / calibration.groupby("store_id").model.sum()).clip(0.8, 1.2)
    pd.DataFrame({"store_id": factors.index, "proposed_multiplier": factors.values,
                  "reason": "Calibration-period model bias correction",
                  "decision": "Do not deploy: overall holdout WAPE deteriorated"}).to_csv(
        output / "override_experiment.csv", index=False)
    # Illustrative capacity at 92% of the model plan, with no claim about real supply.
    capacity = test.groupby(["origin_day", "dept_id"], as_index=False).model.sum()
    capacity["assumed_capacity_units"] = capacity.model.mul(0.92).round()
    capacity["shortfall_units"] = (capacity.model - capacity.assumed_capacity_units).round(1)
    capacity["assumption"] = "illustrative capacity = 92% of model plan"
    capacity.to_csv(output / "capacity_scenario.csv", index=False)
    first_week = test.loc[test.day.between(TEST_START, TEST_START + 6) & test.store_id.eq("CA_1")]
    item = first_week.groupby("item_id").model.sum().idxmax()
    base = float(first_week.loc[first_week.item_id.eq(item), "model"].sum())
    uplift = 0.20
    increment = base * uplift
    pd.DataFrame([{"store_id": "CA_1", "item_id": item, "days": 7,
                   "base_forecast_units": round(base, 1), "assumed_uplift_pct": 20,
                   "scenario_units": round(base + increment, 1),
                   "extra_six_unit_cases": math.ceil(increment / 6),
                   "assumption": "hypothetical promotion uplift; no causal estimate"}]).to_csv(
        output / "promotion_scenario.csv", index=False)
    diagnostics = pd.DataFrame([
        {"check": "selected_item_store_series", "value": selection["series"]},
        {"check": "panel_rows", "value": len(panel)},
        {"check": "zero_sales_days_pct", "value": round(100 * panel.units.eq(0).mean(), 2)},
        {"check": "negative_sales_values", "value": int(panel.units.lt(0).sum())},
        {"check": "missing_scored_model_features", "value": int(panel.loc[panel.day.ge(TRAIN_START), FEATURES].isna().sum().sum())},
        {"check": "warmup_rows_excluded_from_training", "value": int(panel.day.lt(TRAIN_START).sum())},
        {"check": "missing_test_prices", "value": int(test.sell_price.isna().sum())},
        {"check": "calibration_rows", "value": len(calibration)},
        {"check": "test_rows", "value": len(test)},
    ])
    diagnostics.to_csv(output / "data_quality.csv", index=False)
    charts(test, output)
    write_report(output, test, calibration, inventory, interval, selection)
    from .dashboard import build
    build(output)
    manifest = ["Dataset: M5 Forecasting Accuracy, original data via Zenodo DOI 10.5281/zenodo.10203108",
                *[f"{name}: md5 {md5(data_dir/name)}" for name in FILES],
                f"Food item selection: top {NUM_ITEMS} by unit sales in days 1650..{TRAIN_END}, across {STORES}",
                f"Training: days {TRAIN_START}..{TRAIN_END}; calibration: {CAL_START}..{CAL_END}; test: {TEST_START}..{TEST_END}",
                f"Selected item IDs: {','.join(selection['item_ids'])}"]
    (output / "run_manifest.txt").write_text("\n".join(manifest) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("results"))
    parser.add_argument("--skip-checksums", action="store_true")
    args = parser.parse_args()
    run(args.data_dir, args.output_dir, verify=not args.skip_checksums)
