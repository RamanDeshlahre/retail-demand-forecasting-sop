-- Executed against SQLite using 20,160 real M5 holdout rows.
-- Historical USD prices determine ex-post prioritisation only.
WITH item_store AS (
  SELECT store_id, item_id,
         ROUND(SUM(actual_units), 1) AS observed_units,
         ROUND(SUM(model_units), 1) AS forecast_units,
         ROUND(SUM(model_units - actual_units), 1) AS signed_bias_units,
         ROUND(SUM(ABS(model_units - actual_units) * COALESCE(sell_price, 0)), 2)
           AS absolute_error_value_usd
  FROM forecast_actual
  GROUP BY store_id, item_id
), ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY store_id ORDER BY absolute_error_value_usd DESC
  ) AS priority_within_store
  FROM item_store
)
SELECT * FROM ranked
WHERE priority_within_store <= 10
ORDER BY store_id, priority_within_store;
