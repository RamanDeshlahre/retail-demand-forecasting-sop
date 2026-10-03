"""Execute portfolio SQL against the real M5 backtest without a database server."""
from pathlib import Path
import sqlite3
import pandas as pd


def build(test: pd.DataFrame, output: Path) -> None:
    columns = {"units": "actual_units", "model": "model_units",
               "baseline": "baseline_units"}
    frame = test[["store_id", "item_id", "day", *columns, "sell_price"]].rename(columns=columns)
    sql = (Path(__file__).resolve().parents[1] / "sql" / "exception_audit.sql").read_text()
    with sqlite3.connect(":memory:") as connection:
        frame.to_sql("forecast_actual", connection, index=False, if_exists="replace")
        audit = pd.read_sql_query(sql, connection)
    if len(audit) != 30:
        raise ValueError("Expected 10 audited exceptions per store")
    audit.to_csv(output / "sql_exception_audit.csv", index=False)
