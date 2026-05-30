# Outlet Intelligence — Web App

A locally-runnable decision tool for the trade-marketing team, built for **Data Storm v7.0**
by **Team Cypher Sentinels**. It turns our latent-potential model into something a sales
manager can actually use: browse every outlet's predicted January-2026 potential, filter by
province and distributor, drill into a single outlet to see *why* it scored what it did
(SHAP drivers + a plain-language explanation), and review the Western-province budget plan.

This is the user-facing deliverable. The full modelling pipeline that produced the data it
displays lives in our separate **Enterprise Codebase** repository — this app only *serves*
the results, so it stays fast, reproducible, and runnable offline.

## At a glance

| | |
|---|---|
| **Outlets covered** | 20,000 across 4 provinces (Central, North-Western, Southern, Western) |
| **Mean predicted potential** | ~430 L / month |
| **Total latent volume** | 8.61 M L / month |
| **Supply-constrained outlets** | ~10.5% |
| **Western budget modelled** | LKR 5,000,000 → 805 outlets funded → +154,524 L/mo projected |
| **Runtime** | Streamlit, read-only, fully offline (no model retrain, no API call) |

## What it shows

The UI is four tabs, all driven by the sidebar **Province / Distributor / Outlet-ID** filters:

- **🗺️ Potential map** — every outlet plotted over Sri Lanka; dot size and colour scale with
  predicted potential (blue → amber ramp). Dots are pixel-sized, so they stay clearly visible
  at the default country-wide zoom without zooming in.
- **📋 Browse** — searchable, sortable table of all 20,000 predictions with potential,
  historical peak, uplift %, and supply/demand constraint; one-click CSV export of the current
  filtered view.
- **🔎 Outlet detail** — for one outlet: predicted potential vs historical peak vs uplift
  (three metric cards), the SHAP driver chart (what pushed the score up/down), a location map,
  and the cached plain-language explanation — badged **🤖 LLM** or **📝 grounded template** by
  source.
- **💰 Western budget** — how the LKR 5,000,000 promotional budget is allocated across
  Western-province outlets to maximise incremental volume, with a spend-type breakdown
  (discount / merchandising / cooler) and the funded-outlet table.

## Run it

Requires **Python 3.10+**.

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (default <http://localhost:8501>).

Runtime dependencies are minimal — `streamlit`, `pandas`, `pyarrow`, `pydeck` (see
[`requirements.txt`](requirements.txt)).

## How it works

The app is **read-only and offline**: it never retrains a model or calls an external API at
request time. On startup it loads — and caches — the precomputed artifacts bundled in
[`data/`](data/):

| File | Contents |
|---|---|
| `predictions.csv` | `Outlet_ID, Maximum_Monthly_Liters` — the latent-potential prediction |
| `predictions_diagnostic.parquet` | per-outlet reasoning columns (peak, peer, ceiling, constraint signals) |
| `outlet_features_slim.parquet` | the context features the UI needs (distributor, coolers, footfall, competitors) |
| `outlet_coordinates.parquet` | lat/lon for the maps |
| `budget_allocation_detail.parquet` + `budget_allocations.csv` | the Western 5M-LKR plan |
| `outlet_explanations.json` | per-outlet SHAP drivers + cached plain-language explanation |

These artifacts are committed to the repo on purpose — they are what make the app run
standalone immediately after a clone, with no setup beyond `pip install`.

## Project layout

```
outlet-intelligence-app/
├── app.py              # the entire Streamlit app (loaders, maps, 4 tabs)
├── requirements.txt    # runtime deps only
├── data/               # bundled precomputed artifacts (see table above)
└── README.md
```

## Notes & caveats

- **Grounded explanations.** Explanation text is grounded only in each outlet's real numbers.
  A validation step in the pipeline rejected any LLM output that introduced figures not in the
  evidence packet and replaced it with a deterministic grounded template. In the bundled cache
  the vast majority of the 20,000 outlets use the grounded template; a small set carry a
  validated `gpt-4o-mini` explanation. Each card shows its source badge.
- **Map coverage.** 240 of the 20,000 outlets have out-of-bounds coordinates (legacy export
  artifacts) and are omitted from the map layers only — they remain in every table and metric.
- **Secrets.** No API keys or secrets are needed to run the app; `.streamlit/secrets.toml` is
  git-ignored should you add any.
