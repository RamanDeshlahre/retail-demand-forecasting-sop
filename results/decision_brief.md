# Executive decision brief | Item-store demand forecasting

## Decision for a weekly S&OP forum

A global model forecast daily observed unit sales for 120 real food items across three M5 stores. Across two held-out 28-day windows, model WAPE was **48.37%** versus **49.21%** for a seasonal baseline (+0.84 percentage points; a positive figure favours the model). Signed bias was **-5.38%**. This is a historical backtest, not a live business saving.

## Validation and segmentation

Window | Baseline WAPE | Model WAPE | Model bias | Observed units
---|---:|---:|---:|---:
Day 1858–1885 | 49.17% | 51.19% | -5.95% | 106,910
Day 1886–1913 | 49.25% | 45.45% | -4.78% | 103,312

Store | Baseline WAPE | Model WAPE | Model bias
---|---:|---:|---:
CA_1 | 48.24% | 49.74% | -4.55%
CA_2 | 53.64% | 50.81% | -13.54%
CA_3 | 47.25% | 45.99% | -1.11%

A simple 90th-percentile calibration interval had ±10.8 units daily width and 90.3% observed coverage. This is a pooled illustrative interval, not a product-specific service-level guarantee.

## Choosing the planning forecast

At item-store **weekly** level, the baseline WAPE was 30.78% versus 33.24% for the model; at **28-day** level, 24.6% versus 28.01%. The ML model's small daily advantage does not justify automatic adoption for order-volume planning. Pilot the model for daily exceptions, retain the seasonal baseline for weekly/28-day category review, and re-evaluate by horizon and store as more weeks arrive.
A store-level bias adjustment learned exclusively from calibration data produced 49.2% test WAPE and +2.29% bias. Record this as an unsuccessful candidate override; do not apply it automatically.

## Planning actions

1. Commercial: review the largest model-versus-baseline changes alongside the known event calendar.
2. Supply Chain: prioritise item-store exceptions in `priority_exceptions.csv`; review high-risk bias rather than overriding every line.
3. Distribution: compare demand with the explicit capacity scenario in `capacity_scenario.csv`, then agree allocations and owners.
4. Forecast owner: record any adjustment and its reason, and compare post-override errors with the original forecast.

## Illustrative replenishment experiment

For the first holdout window, both order policies faced the same observed sales proxy, starting stock and assumed two-day lead time, seven-day shelf life and six-unit case pack. The simulation evaluates 25 days, allowing full look-ahead for its ordering rule. The seasonal policy served 85,089 of 91,482 units and discarded 2,270; the ML policy served 83,075 and discarded 2,509. Stock availability and shelf life are not in M5, so these outcomes are scenario results, not measured Walmart outcomes.

## Promotional planning case

`promotion_scenario.csv` models an assumed 20% uplift for one high-volume food item at CA_1 over seven days, then rounds incremental units to six-unit cases. This is a what-if exercise, not an estimated price elasticity or an observed promotion.

## Known limitations

- M5 records sales, not unrestricted demand; historical out-of-stocks and true lost sales are unknown.
- M5 does not provide shelf life, stock on hand, supplier lead times, capacity or real forecast overrides. All such inputs are clearly simulated.
- Prices are actual historical values used only after the forecast for approximate exception materiality in USD; future prices are not model inputs.
- Calendar events are known ahead; all sales-derived features in each 28-day forecast are from before that window's origin.
- Store and item sample was selected using only pre-test data, and performance cannot be assumed for Waitrose.

## Evidence

See `metrics.csv`, `holdout_forecast.png`, `priority_exceptions.csv`, `capacity_scenario.csv`, `replenishment_results.csv`, `data_quality.csv` and `run_manifest.txt`.
