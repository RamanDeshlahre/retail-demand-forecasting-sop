# Retail Demand Forecasting and S&OP Decision Support

**Independent portfolio case study for a Forecasting Analyst role.** Real historical Walmart M5 sales power the item-store forecast. Stock on hand, spoilage, lead times, promotion uplift and supplier capacity are explicitly hypothetical because M5 does not provide those facts. This project has no affiliation with John Lewis Partnership, Waitrose, Walmart or Blue Yonder.

Open [`results/planning_dashboard.html`](results/planning_dashboard.html) in a browser for the interactive executive view and [`results/decision_brief.md`](results/decision_brief.md) for the S&OP recommendation. The code and output files are included so a reviewer can audit the result.

## The business problem

Every day, a demand planner needs a reliable unit forecast by **item and store**, with a way to explain forecast changes, focus manual attention, and reconcile demand with supply. This case study demonstrates a 28-day as-of forecast, error diagnosis, an override experiment and clearly marked what-if planning scenarios.

| Role requirement | Project evidence |
|---|---|
| Item-location forecasting | 120 real food items × three M5 stores × two 28-day holdouts |
| Complex data and SQL checks | Source checksums, missing-feature and zero-sales checks, price joins, executed SQLite window query for exception ranking |
| ML and baseline challenge | HistGradientBoosting versus a four-point historical weekday baseline |
| Event and seasonal conditions | Known calendar event, month, weekday and SNAP features; hypothetical promotion case |
| S&OP and logistics alignment | 92% capacity what-if, prioritised demand gaps, named cross-functional actions |
| Availability and waste | Same-input comparison of two forecast-based order rules under simulated lead time and shelf life |
| Manual overrides | Store bias adjustment tested on untouched holdout, rejected after worse WAPE |
| Automation and stakeholder communication | Reproducible command, self-contained dashboard, executive brief, operating procedure |

## Verified result

The actual run's evidence is in `results/metrics.csv` and `results/decision_brief.md`. Across 20,160 held-out item-store-days, the seasonal baseline achieved **49.21% daily WAPE** and the ML model achieved **48.37%**. This is a **0.84 percentage-point** improvement, with ML bias of **-5.38%**. The model was worse than baseline in the first 28-day window, better in the second. At weekly and four-week item-store aggregation, the baseline performed better. The recommendation is therefore a **limited daily-exception pilot**, not blanket replacement of the baseline. A simulated store-level override learned from calibration worsened holdout WAPE.

These figures apply only to a selected, high-volume M5 food cohort in the US. They are not Waitrose performance or realised commercial savings. The inventory experiment uses observed sales as a proxy for unconstrained demand, which is a material limitation.

## Reproduce

Requires Python 3.11+ and about 1 GB free disk space. The checked source files total about 309 MiB.

From this project folder, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.download_data
python -m src.pipeline --data-dir data/raw --output-dir results
python -m unittest discover -s tests -v
```

The download step fetches `calendar.csv`, `sales_train_validation.csv` and `sell_prices.csv` from the [M5 Zenodo record](https://zenodo.org/records/10203108), verifies their MD5 hashes, and skips correct copies on repeat runs. You can download the same three files manually into `data/raw/` if you prefer. Keep the source files out of GitHub because of size and dataset terms.

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. The project was run with pandas 2.2.3, NumPy 2.3.5 and scikit-learn 1.8.0. Results may shift slightly with library versions.

## Time and leakage controls

Selected items are the top 120 food products across stores CA_1–CA_3 by actual units on days 1650–1801, **before** calibration and test. The global model trains on days 1290–1801 (10 August 2014–3 January 2016). Calibration uses days 1802–1857 (4 January–28 February 2016). Two untouched 28-day test origins follow: 29 February and 28 March 2016. The last test date is 24 April 2016.

Sales features use lags of at least 28 days. For any of the 28 forecast days, a lagged sale is known by the **start** of that window. The rolling features also end at least 28 days before their target. Calendar events and SNAP dates are assumed to be known ahead. No future realised transaction counts or future observed prices are model inputs. The M5 daily series includes recorded zero-sales dates, but zero sales cannot prove zero demand or availability.

The baseline averages the corresponding weekday's unit sales **four, five, six and seven weeks earlier**. We assess WAPE = total absolute error / total actual units and signed bias = (total forecast − total actual) / total actual. WAPE is useful for volume-weighted planning but hides performance differences for slow sellers, hence the store/window cuts. The pooled daily prediction interval uses an unseen calibration block and is descriptive, not a service-level promise.

## Data provenance and disclosure

Source: [M5 Forecasting Accuracy](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data), reproduced from [Zenodo DOI 10.5281/zenodo.10203108](https://doi.org/10.5281/zenodo.10203108). MD5 hashes and exact selected item IDs are written to `results/run_manifest.txt`. Raw data are excluded from this repository. Prices are real historical USD prices used after forecasting for approximate error materiality. Calendar event names and SNAP flags are historical facts. The project does not claim access to proprietary Waitrose or Luminate systems.

Promotion uplift (20%), six-unit case pack, two-day lead time, seven-day shelf life, initial stock and 92% capacity are **assumptions**. M5 has no item-level promotion flag, inventory history, supplier contract data or recorded planner overrides. Simulated sales lost and waste cannot be described as measured savings. Read `docs/methodology.md` for the full assumptions and limitations.

## Review order

1. Open the offline HTML dashboard; change the store, validation period and capacity assumption.
2. Read the brief and its counterintuitive model-selection decision.
3. Inspect `results/metrics.csv`, `results/override_experiment.csv`, and `results/data_quality.csv`.
4. Read the as-of feature code and run the pipeline using the original M5 files.

## Repository layout

```text
retail-forecasting/
  README.md
  requirements.txt
  src/pipeline.py               # data processing, backtest and planning simulation
  src/dashboard.py              # self-contained offline dashboard generator
  src/sql_audit.py              # executes a 20,160-row holdout audit in SQLite
  src/download_data.py          # verified source-data acquisition
  sql/exception_audit.sql       # item-store error ranking by store
  docs/methodology.md           # design and limitations
  docs/planner_sop.md           # daily / weekly decision workflow
  docs/cv_bullets.md            # accurately evidenced CV wording
  docs/github_guide.md          # upload and presentation steps
  tests/test_pipeline.py        # causal and conservation checks
  results/                     # verified outputs, no raw source data
```
