# Outlet Intelligence — Web App

A locally-runnable decision tool for the trade-marketing team, built for **Data Storm v7.0**
by **Team Cypher Sentinels**. It turns our latent-potential model into something a sales
manager can actually use: browse every outlet's predicted January-2026 potential, filter by
province and distributor, drill into a single outlet to see *why* it scored what it did
(SHAP drivers + a plain-language explanation), and review the Western-province budget plan.

This is the user-facing deliverable. The full modelling pipeline that produced the data it
displays lives in our separate **Enterprise Codebase** repository.

## What it shows

- **🗺️ Potential map** — every outlet plotted, dot size & colour by predicted potential.
- **📋 Browse** — searchable, sortable table of all ~20,000 predictions; province +
  distributor filters; CSV export of the current view.
- **🔎 Outlet detail** — for one outlet: predicted potential vs historical peak, the SHAP
  driver chart (what pushed the score up/down), a location map, and the cached plain-language
  explanation (badged 🤖 LLM or 📝 grounded template by source).
- **💰 Western budget** — how the LKR 5,000,000 promotional budget is allocated across
  Western-province outlets to maximise incremental volume, with spend-type breakdown.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (default http://localhost:8501).

## How it works

The app is **read-only and offline**: it never retrains a model or calls an external API at
request time. It loads precomputed artifacts bundled in `data/`:

| File | Contents |
|---|---|
| `predictions.csv` | `Outlet_ID, Maximum_Monthly_Liters` — the latent-potential prediction |
| `predictions_diagnostic.parquet` | per-outlet reasoning columns (peak, peer, ceiling, constraint signals) |
| `outlet_features_slim.parquet` | the few context features the UI needs (distributor, coolers, footfall, competitors) |
| `outlet_coordinates.parquet` | lat/lon for the maps |
| `budget_allocation_detail.parquet` + `budget_allocations.csv` | the Western 5M-LKR plan |
| `outlet_explanations.json` | per-outlet SHAP drivers + cached plain-language explanation |

Explanations were generated once (and validated for grounding) in the pipeline; serving the
cache keeps the demo instant, reproducible, and able to run with no API key.

## Notes

- The explanation text is grounded only in each outlet's real numbers; a validation step in
  the pipeline rejected any LLM output that introduced figures not in the evidence packet and
  replaced it with a deterministic grounded template. Each card shows its source.
- 240 of the 20,000 outlets have out-of-bounds coordinates (legacy export artifacts) and are
  omitted from map layers only — they remain in all tables and metrics.
