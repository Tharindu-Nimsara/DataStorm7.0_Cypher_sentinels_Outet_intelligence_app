"""Outlet Intelligence — standalone web app (Data Storm v7.0, Team Cypher Sentinels).

A self-contained Streamlit app for the trade-marketing team. It reads only the precomputed
artifacts bundled in `data/` (predictions, a slim gold-feature table, the cached SHAP+LLM
explanations, and the Western budget allocation) — it never retrains a model or calls an API
at request time, so it loads fast and works offline.

This is the deliverable-#4 web app, packaged as its own repository. The full modelling
pipeline that produced these artifacts lives in the separate Enterprise Codebase repo.

Run:  pip install -r requirements.txt  &&  streamlit run app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent / "data"

st.set_page_config(page_title="Outlet Intelligence — Cypher Sentinels",
                   page_icon="🧊", layout="wide")
ACCENT = "#3DA5D9"


# ──────────────────────────────────────────────────────────────────────────────
# Data loading (cached) — bundled artifacts, flat data/ folder
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading precomputed predictions…")
def load_data() -> pd.DataFrame:
    preds = pd.read_csv(DATA / "predictions.csv")
    diag = pd.read_parquet(DATA / "predictions_diagnostic.parquet")
    gold = pd.read_parquet(DATA / "outlet_features_slim.parquet")
    # only pull gold columns not already in diag, to avoid _x/_y merge collisions
    gold = gold[["Outlet_ID"] + [c for c in gold.columns
                                 if c != "Outlet_ID" and c not in diag.columns]]
    coords = pd.read_parquet(DATA / "outlet_coordinates.parquet")

    df = (preds.merge(diag, on="Outlet_ID", how="left")
                .merge(gold, on="Outlet_ID", how="left")
                .merge(coords, on="Outlet_ID", how="left"))
    df["constraint_type"] = (df["censoring_score"] > 0.12).map(
        {True: "supply-constrained", False: "demand-led"})
    df["uplift_pct"] = (df["Maximum_Monthly_Liters"] / df["vol_max"].clip(lower=1) - 1) * 100
    return df


@st.cache_data
def load_explanations() -> dict:
    p = DATA / "outlet_explanations.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@st.cache_data
def load_budget() -> pd.DataFrame:
    p = DATA / "budget_allocation_detail.parquet"
    if p.exists():
        return pd.read_parquet(p)
    csv = DATA / "budget_allocations.csv"
    return pd.read_csv(csv) if csv.exists() else pd.DataFrame()


def _valid_coords(df: pd.DataFrame) -> pd.Series:
    return df["Latitude"].between(5.9, 9.9) & df["Longitude"].between(79.5, 82.0)


# ──────────────────────────────────────────────────────────────────────────────
# Maps
# ──────────────────────────────────────────────────────────────────────────────
def _potential_color(t: float) -> list[int]:
    # Clean low→high ramp driven by percentile rank t (0–1):
    # light blue (low) → teal (mid) → amber (high).
    t = min(max(t, 0.0), 1.0)
    low, mid, high = (173, 216, 230), (79, 176, 198), (240, 150, 40)
    if t < 0.5:
        a, b, f = low, mid, t / 0.5
    else:
        a, b, f = mid, high, (t - 0.5) / 0.5
    return [int(a[i] + (b[i] - a[i]) * f) for i in range(3)] + [180]


def hero_map(df: pd.DataFrame):
    import pydeck as pdk
    m = df[_valid_coords(df)].copy()
    # Size & colour on PERCENTILE RANK across the currently-displayed rows, so the
    # full ramp is used even when filtered to one province (raw/vmax flattened it).
    t = m["Maximum_Monthly_Liters"].rank(pct=True)
    m["color"] = t.apply(_potential_color)
    m["radius"] = 3 + t * 13  # ~3px smallest → ~16px largest
    layer = pdk.Layer("ScatterplotLayer",
                      data=m[["Latitude", "Longitude", "color", "radius",
                              "Outlet_ID", "Maximum_Monthly_Liters"]],
                      get_position=["Longitude", "Latitude"], get_fill_color="color",
                      get_radius="radius", radius_units="pixels",
                      radius_min_pixels=3, radius_max_pixels=18,
                      pickable=True, opacity=0.7)
    view = pdk.ViewState(latitude=float(m["Latitude"].median()),
                         longitude=float(m["Longitude"].median()), zoom=7, pitch=0)
    return pdk.Deck(layers=[layer], initial_view_state=view, map_style="road",
                    tooltip={"text": "{Outlet_ID}\n{Maximum_Monthly_Liters} L"})


def outlet_map(row: pd.Series):
    import pydeck as pdk
    if not (5.9 <= row.get("Latitude", 0) <= 9.9):
        return None
    pt = pd.DataFrame([{"Latitude": row["Latitude"], "Longitude": row["Longitude"]}])
    layer = pdk.Layer("ScatterplotLayer", data=pt,
                      get_position=["Longitude", "Latitude"],
                      get_fill_color=[61, 165, 217, 220], get_radius=10,
                      radius_units="pixels", radius_min_pixels=6, radius_max_pixels=14)
    view = pdk.ViewState(latitude=float(row["Latitude"]),
                         longitude=float(row["Longitude"]), zoom=13, pitch=0)
    return pdk.Deck(layers=[layer], initial_view_state=view, map_style="road")


# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
def main():
    df = load_data()
    explanations = load_explanations()
    budget = load_budget()

    st.title("🧊 Outlet Intelligence")
    st.caption("Latent monthly-volume potential for ~20,000 Sri Lankan outlets — "
               "Jan 2026. Team Cypher Sentinels · Data Storm v7.0.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Outlets", f"{len(df):,}")
    c2.metric("Mean potential", f"{df['Maximum_Monthly_Liters'].mean():.0f} L")
    c3.metric("Total latent volume", f"{df['Maximum_Monthly_Liters'].sum()/1e6:.2f} M L")
    c4.metric("Supply-constrained",
              f"{(df['constraint_type']=='supply-constrained').mean()*100:.1f}%")

    st.sidebar.header("Filters")
    provinces = sorted(df["Province"].dropna().unique().tolist())
    sel_prov = st.sidebar.multiselect("Province", provinces, default=provinces)
    dists = sorted(df.loc[df["Province"].isin(sel_prov), "primary_distributor"]
                   .dropna().unique().tolist())
    sel_dist = st.sidebar.multiselect("Distributor", dists, default=dists)
    search = st.sidebar.text_input("Search Outlet_ID")

    fdf = df[df["Province"].isin(sel_prov) & df["primary_distributor"].isin(sel_dist)]
    if search:
        fdf = fdf[fdf["Outlet_ID"].str.contains(search, case=False, na=False)]
    st.sidebar.caption(f"{len(fdf):,} outlets match")

    tab_map, tab_browse, tab_outlet, tab_budget = st.tabs(
        ["🗺️ Potential map", "📋 Browse", "🔎 Outlet detail", "💰 Western budget"])

    with tab_map:
        st.subheader("Predicted potential across outlets")
        st.caption("Dot colour ∝ predicted January-2026 potential (liters).")
        try:
            st.pydeck_chart(hero_map(fdf), use_container_width=True)
            st.markdown(
                "<div style='display:flex;justify-content:space-between;"
                "font-size:0.8em;color:#666;margin-bottom:2px;'>"
                "<span>Lower</span><span>Higher (Jan-2026 predicted L)</span></div>"
                "<div style='height:14px;width:100%;border-radius:3px;"
                "background:linear-gradient(to right,rgb(173,216,230),"
                "rgb(79,176,198),rgb(240,150,40));'></div>",
                unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Map unavailable ({e}); sample table below.")
            st.dataframe(fdf.head(500)[["Outlet_ID", "Province", "Maximum_Monthly_Liters"]])

    with tab_browse:
        st.subheader("Outlet predictions")
        cols = ["Outlet_ID", "Province", "primary_distributor", "Outlet_Type",
                "Outlet_Size", "vol_max", "Maximum_Monthly_Liters", "uplift_pct",
                "constraint_type"]
        show = fdf[cols].rename(columns={
            "primary_distributor": "Distributor", "vol_max": "Hist. peak (L)",
            "Maximum_Monthly_Liters": "Potential (L)", "uplift_pct": "Uplift %",
            "constraint_type": "Constraint"})
        st.dataframe(show.sort_values("Potential (L)", ascending=False),
                     use_container_width=True, height=560,
                     column_config={"Uplift %": st.column_config.NumberColumn(format="%.0f%%")})
        st.download_button("Download this view (CSV)", show.to_csv(index=False),
                           "outlet_view.csv", "text/csv")

    with tab_outlet:
        ids = fdf["Outlet_ID"].tolist()
        if not ids:
            st.info("No outlets match the current filters.")
        else:
            oid = st.selectbox("Choose an outlet", ids,
                               index=int(fdf["Maximum_Monthly_Liters"].argmax()))
            row = fdf[fdf["Outlet_ID"] == oid].iloc[0]
            left, right = st.columns([1, 1])
            with left:
                st.markdown(f"### {oid}")
                st.write(f"**{row['Outlet_Size']} {row['Outlet_Type']}** · "
                         f"{row['Province']} · {row['primary_distributor']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Potential", f"{row['Maximum_Monthly_Liters']:.0f} L")
                m2.metric("Historical peak", f"{row['vol_max']:.0f} L")
                m3.metric("Uplift", f"{row['uplift_pct']:.0f}%")
                st.write(f"**Constraint:** {row['constraint_type']}  ·  "
                         f"**Cooler ceiling:** {row.get('physical_max', float('nan')):.0f} L  ·  "
                         f"**Competitors ≤500m:** {int(row.get('n_competitors_500m', 0))}")
                rec = explanations.get(oid)
                if rec:
                    st.markdown("#### Why this score")
                    badge = ("🤖 LLM (gpt-4o-mini)" if rec["source"].startswith("github_models")
                             else "📝 grounded template")
                    st.caption(f"Explanation source: {badge}")
                    st.info(rec["explanation"])
            with right:
                rec = explanations.get(oid)
                if rec:
                    st.markdown("#### Top drivers (SHAP)")
                    ev = rec["evidence"]
                    drivers = ([{"feature": d["feature"], "impact": d["shap"]}
                                for d in ev.get("top_drivers_up", [])] +
                               [{"feature": d["feature"], "impact": d["shap"]}
                                for d in ev.get("top_drivers_down", [])])
                    if drivers:
                        st.bar_chart(pd.DataFrame(drivers).set_index("feature"),
                                     horizontal=True, color=ACCENT)
                        st.caption("Positive = pushes potential up; negative = pulls it down.")
                m = outlet_map(row)
                if m is not None:
                    st.markdown("#### Location")
                    st.pydeck_chart(m, use_container_width=True)

    with tab_budget:
        st.subheader("Western-province trade-spend allocation (LKR 5,000,000)")
        if budget.empty:
            st.info("Budget allocation artifact not bundled.")
        else:
            funded = budget[budget["Trade_Spend_Allocation_LKR"] > 1.0]
            b1, b2, b3 = st.columns(3)
            b1.metric("Budget allocated",
                      f"{budget['Trade_Spend_Allocation_LKR'].sum()/1e6:.2f} M LKR")
            b2.metric("Outlets funded", f"{len(funded):,}")
            if "projected_incremental_L" in budget.columns:
                b3.metric("Projected incremental",
                          f"{budget['projected_incremental_L'].sum():,.0f} L/mo")
            if "spend_type" in funded.columns:
                st.markdown("**Spend by type**")
                st.bar_chart(funded.groupby("spend_type")["Trade_Spend_Allocation_LKR"].sum(),
                             color=ACCENT)
            disp = [c for c in ["Outlet_ID", "primary_distributor", "constraint_type",
                                "spend_type", "gap", "Trade_Spend_Allocation_LKR",
                                "projected_incremental_L"] if c in funded.columns]
            st.dataframe(funded[disp].sort_values("Trade_Spend_Allocation_LKR", ascending=False),
                         use_container_width=True, height=420)


if __name__ == "__main__":
    main()
