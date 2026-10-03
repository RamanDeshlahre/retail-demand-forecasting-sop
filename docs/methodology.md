# Methodology and decision boundaries

## Forecast and evaluation

The unit of analysis is observed daily unit sales by item and store. The M5 data have 3,049 unique products across 10 stores, but this deliberately runnable case uses 120 foods across CA_1–CA_3. The sample is selected from training-period volume only. A global histogram gradient boosting model shares signal across items/stores. Its features include item, store, department, day of week, month, scheduled event, SNAP, five lag values (28–56 days), and old 28/56-day means and nonzero frequency. Negative predictions are floored at zero. The model receives neither future observed sales nor observed future price.

Two independent 28-day windows are scored after training. A 56-day prior calibration period estimates an overall absolute-residual interval and a proposed store multiplier. The multiplier is assessed on test data and rejected if it worsens WAPE. This demonstrates Forecast Value Added in a limited sense: one measured adjustment versus its original forecast. There are no real planners or actual override logs.

The seasonal comparison is deliberately strong: the average of the same weekday at lags 28, 35, 42 and 49. A naive random train/test split would leak neighbouring observations and flatter the model, so every score here follows calendar order. Item/store weekly and 28-day totals are scored separately because replenishment and S&OP operate at different cadences.

## Data preparation and anomalies

M5 is a complete daily item-store panel in this source, including zeros. Zero sales do not reveal whether inventory was absent. Before any operational deployment, a retailer would join stock-on-hand, availability flags, delivery and ranging data. The pipeline checks official-reproduction checksums, complete chosen item-store rows, missing model inputs, negative units, zero-sales share and missing test prices. Raw M5 prices are in USD, and the ex-post absolute-error × price calculation is **not** a forecast of commercial loss.

`sql/exception_audit.sql` is executed with Python's built-in SQLite engine over the actual held-out rows. It groups item-store error value and uses `ROW_NUMBER()` to list the ten largest historical exceptions in each store. The project does not claim that SQLite is an enterprise planning platform.

Calendar events are known ahead and used as binary flags. This simple event encoding does not model all local effects. Weather and local events are natural future improvements, but joining them credibly requires store geography, time-stamped forecasts available at the prediction origin, and governance checks. This dataset does not provide a clean per-item promotion label. The separate 20% promotion scenario is an assumed uplift, not an estimated effect.

## Replenishment simulation

Each series starts with the same simulated stock for both policies: rounded-up three days of its observed pre-test average, minimum one six-unit case. Orders arrive two days after placement; the case pack is six. Stock has a seven-day simulated shelf life, is consumed oldest first, and unfilled demand is counted as lost. The test uses the first 25 days of a 28-day forecast so the final simulated order has a full forward window. Each policy sees the identical observed unit-sales sequence as a **demand proxy**. Units can be fractional in M5, while the case pack is integral.

This comparison is useful to exercise a decision process, not for estimating Walmart stockouts, waste, fill rate or Waitrose savings. A credible operational validation would need true demand adjustments for historical stockouts, recorded stock and delivery movements, per-SKU shelf life, case sizes, lead-time distributions, supplier capacity, and service-level targets. Demand, capacity and wastage would then be replayed with common starting state and policy constraints.

## S&OP scenario

The capacity file assumes supply can cover 92% of the model's 28-day department forecast and displays the arithmetical shortfall. This is a discussion aid rather than evidence of a real shortage. The promotional file selects the highest forecast-volume CA_1 item in the first seven days and applies a hypothetical 20% uplift, converting extra units into six-unit cases. The dashboard slider changes capacity only, with no causal claim. Commercial should validate proposed promotions; Supply Chain should check suppliers, case packs and waste exposure; Distribution should validate receiving and vehicle capacity. The analyst documents any agreed override and measures its effect after actuals arrive.

## Governance

The public M5 case contains item, store, sales and price data, not personal customer records. In a real deployment, restrict access to operational data, minimise personal data, document source permissions, protect audit logs, and route any GDPR or GSCOP interpretation through the Partnership's relevant teams. This project does not claim to certify legal compliance. Nor does a working prototype equal enterprise software experience with Luminate Demand Edge, Snowflake or Tableau. It demonstrates transferable analytical methods.
