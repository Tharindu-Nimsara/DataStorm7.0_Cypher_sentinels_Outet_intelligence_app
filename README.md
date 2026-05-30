# Outlet Intelligence — Web App

A read-only **Streamlit** decision tool for the trade-marketing team, built for **Data Storm
v7.0** by **Team Cypher Sentinels**. It serves precomputed latent-potential predictions for
~20,000 Sri Lankan outlets (January 2026): browse every outlet, filter by province and
distributor, drill into one outlet to see *why* it scored what it did (SHAP drivers + a
plain-language explanation), and review the Western-province budget plan. The app only
*serves* results — it never retrains a model or calls an API at request time. The full
modelling pipeline that produced these artifacts lives in the separate **Enterprise Codebase**
repository.

## At a glance

| Metric | Value |
|---|---|
| Outlets | **20,000** across 4 provinces (Central, North-Western, Southern, Western) |
| Mean predicted potential | **~430 L / month** |
| Total latent volume | **8.61 M L / month** |
| Supply-constrained outlets | **~10.5%** |
| Western budget modelled | **LKR 5,000,000** → **805 outlets** funded → **+154,524 L/mo** projected |
| Runtime | Offline · read-only · no model retrain · no API call |

*(Figures verified directly against the bundled `data/` artifacts.)*

## What it shows

Four tabs, all driven by the sidebar **Province / Distributor / Outlet-ID** filters:

- **🗺️ Potential map** — every outlet plotted over Sri Lanka; dot size and colour scale with
  predicted potential (blue → amber ramp). Dots use pixel-sized radii, so they stay clearly
  visible at the default country-wide zoom without zooming in.
- **📋 Browse** — searchable, sortable table of all 20,000 predictions with potential,
  historical peak, uplift %, and supply/demand constraint; one-click CSV export of the current
  filtered view.
- **🔎 Outlet detail** — for one outlet: three metric cards (potential / historical peak /
  uplift), the SHAP driver chart (what pushed the score up or down), a location map, and the
  cached plain-language explanation — badged **🤖 LLM (gpt-4o-mini)** or **📝 grounded
  template** by source.
- **💰 Western budget** — how the LKR 5,000,000 promotional budget is allocated across
  Western-province outlets to maximise incremental volume, with a spend-by-type chart and the
  funded-outlet table.

## Run it

Requires **Python 3.10+**.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (default <http://localhost:8501>).

Runtime dependencies (from [`requirements.txt`](requirements.txt)):

- `streamlit>=1.30`
- `pandas>=2.0`
- `pyarrow>=14.0`
- `pydeck>=0.8`

## How it works / data

The app is **read-only and offline**: on startup it loads — and caches — the precomputed
artifacts bundled in [`data/`](data/), then never touches a model or external service again.
These files are what make the app run standalone immediately after a clone.

| File | Contents |
|---|---|
| `predictions.csv` | `Outlet_ID, Maximum_Monthly_Liters` — the latent-potential prediction |
| `predictions_diagnostic.parquet` | per-outlet reasoning columns (historical peak, ceiling, censoring/constraint signals) |
| `outlet_features_slim.parquet` | context features the UI needs (distributor, type/size, coolers, competitors) |
| `outlet_coordinates.parquet` | `Latitude` / `Longitude` for the maps |
| `budget_allocation_detail.parquet` | the Western 5M-LKR plan (spend type, allocation, projected incremental) |
| `budget_allocations.csv` | CSV fallback for the budget plan |
| `outlet_explanations.json` | per-outlet SHAP drivers + cached plain-language explanation and its source |

## Project layout

```
outlet-intelligence-app/
├── app.py              # the entire Streamlit app (loaders, maps, 4 tabs)
├── requirements.txt    # runtime deps only
├── README.md
├── .gitignore
└── data/               # bundled precomputed artifacts (see table above)
    ├── predictions.csv
    ├── predictions_diagnostic.parquet
    ├── outlet_features_slim.parquet
    ├── outlet_coordinates.parquet
    ├── budget_allocation_detail.parquet
    ├── budget_allocations.csv
    └── outlet_explanations.json
```

## Notes

- **Grounded explanations.** Explanation text is grounded only in each outlet's real numbers.
  A validation step in the pipeline rejected any LLM output that introduced figures not in the
  evidence packet and replaced it with a deterministic grounded template. In the bundled cache,
  12 of the 20,000 outlets carry a validated `gpt-4o-mini` explanation and the remaining 19,988
  use the grounded template; each card shows its source badge.
- **Map coverage.** 240 of the 20,000 outlets have out-of-bounds coordinates (legacy export
  artifacts) and are omitted from the map layers only — they remain in every table and metric.
- **No secrets needed.** The app runs with no API keys or credentials of any kind.
