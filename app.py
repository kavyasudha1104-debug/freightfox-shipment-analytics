import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="FreightFox Shipment Analytics", layout="wide")

DATA_PATH = "shipments.csv"


# ---------------------------------------------------------------- data
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    for c in [
        "booking_date", "pickup_date", "delivery_date",
        "promised_delivery_date", "actual_delivery_date",
    ]:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    n_raw = len(df)
    df = df.drop_duplicates().copy()
    n_dupes = n_raw - len(df)

    df["cost_per_km"] = df["freight_cost"] / df["distance_km"]
    df["promised_window_days"] = (df["promised_delivery_date"] - df["pickup_date"]).dt.days
    df["transit_days"] = (df["actual_delivery_date"] - df["pickup_date"]).dt.days
    df["delay_days"] = (df["actual_delivery_date"] - df["promised_delivery_date"]).dt.days
    df["impossible_dates"] = df["actual_delivery_date"] < df["pickup_date"]
    df["same_city"] = df["origin_city"] == df["destination_city"]

    measurable = df[df["actual_delivery_date"].notna() & ~df["impossible_dates"]].copy()
    measurable["on_time"] = measurable["delay_days"] <= 0
    return df, measurable, n_dupes


df, m, n_dupes = load_data()

st.title("FreightFox — Shipment Delivery Performance")
st.caption(
    f"5,015 raw rows → {n_dupes} exact duplicates removed → {len(df):,} shipments. "
    f"On-time performance is measurable for {len(m):,} of them "
    "(actual delivery date present, dates physically valid). "
    "On-time = actual ≤ promised."
)

# ---------------------------------------------------------------- KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Measurable on-time rate", f"{m['on_time'].mean():.1%}")
k2.metric("Avg transit (days)", f"{m['transit_days'].mean():.1f}")
k3.metric("Median cost/km (excl. CARR_07)",
          f"₹{df.loc[df.carrier_id != 'CARR_07', 'cost_per_km'].median():.1f}")
k4.metric("Missing actual delivery date",
          int((df.status.isin(['Delivered', 'Delayed']) & df.actual_delivery_date.isna()).sum()),
          help="Delivered/Delayed rows with no actual_delivery_date — mostly South region")
at_risk = df[(df.status == "In-Transit") &
             (df.promised_delivery_date < df[["booking_date"]].max().iloc[0])]
k5.metric("In-transit past promise (at-risk)",
          f"{len(at_risk):,} / {int((df.status == 'In-Transit').sum()):,}",
          help="The one metric I'd track weekly — leading indicator of delivery problems")

tab1, tab2, tab3, tab4 = st.tabs(
    ["1 · Regions & what drives lateness", "2 · Cost vs distance",
     "3 · Customers", "4 · Data quality"]
)

# ---------------------------------------------------------------- Q1
with tab1:
    left, right = st.columns(2)

    with left:
        st.subheader("On-time rate by region")
        q1 = (m.groupby("region")
                .agg(otd=("on_time", "mean"), n=("on_time", "size"))
                .reset_index()
                .sort_values("otd"))
        fig = px.bar(q1, x="region", y="otd", text=q1["otd"].map("{:.1%}".format),
                     hover_data=["n"], labels={"otd": "On-time rate"})
        fig.update_yaxes(range=[0, 0.7], tickformat=".0%")
        fig.add_hline(y=m["on_time"].mean(), line_dash="dot",
                      annotation_text="overall")
        st.plotly_chart(fig, use_container_width=True)
        st.warning(
            "⚠️ Central is nominally worst (48.3%) but region differences are **not "
            "statistically significant** (χ² p = 0.75). And South's bar rests on only "
            "124 measurable shipments — 84.5% of its completed shipments have no "
            "actual delivery date."
        )

    with right:
        st.subheader("The real driver: promise window")
        win = (m.dropna(subset=["promised_window_days"])
                 .groupby("promised_window_days")
                 .agg(late=("on_time", lambda s: 1 - s.mean()), n=("on_time", "size"))
                 .reset_index())
        fig = px.bar(win, x="promised_window_days", y="late",
                     color="late", color_continuous_scale="Reds",
                     range_color=[0, 0.9],
                     text=win["late"].map("{:.0%}".format), hover_data=["n"],
                     labels={"promised_window_days": "Days promised (pickup → promise)",
                             "late": "Late rate"})
        fig.update_yaxes(tickformat=".0%")
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.info(
            "Actual transit averages ~5.5 days and is **flat across distance, mode and "
            "region**. Lateness is mostly decided at booking time: 2-day promises are "
            "82% late; 8-day promises 19%. The one carrier-level signal: **CARR_02 is "
            "late 59.6% vs 49.3% for the rest (p = 0.003).**"
        )

    st.subheader("Transit days vs distance (why geography isn't the story)")
    sample = m.dropna(subset=["transit_days"]).sample(min(1500, len(m)), random_state=1)
    fig = px.scatter(sample, x="distance_km", y="transit_days", color="region",
                     opacity=0.4, labels={"distance_km": "Distance (km)",
                                          "transit_days": "Actual transit (days)"})
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- Q2
with tab2:
    st.subheader("Freight cost vs distance")
    incl7 = st.toggle("Include CARR_07 (the 9.7× pricing outlier)", value=True)
    plot_df = df if incl7 else df[df.carrier_id != "CARR_07"]
    corr = plot_df["freight_cost"].corr(plot_df["distance_km"])

    fig = px.scatter(
        plot_df.sample(min(2500, len(plot_df)), random_state=1),
        x="distance_km", y="freight_cost", color="mode",
        symbol=plot_df.sample(min(2500, len(plot_df)), random_state=1)["carrier_id"]
        .eq("CARR_07").map({True: "CARR_07", False: "other carriers"}),
        opacity=0.5,
        labels={"distance_km": "Distance (km)", "freight_cost": "Freight cost (₹)"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.metric("Correlation (cost vs distance) for current view", f"{corr:.3f}")
    st.info(
        "Naive correlation is 0.296 — but **within each mode and excluding CARR_07 it "
        "is ≈ 0.985** (₹25/km FTL · ₹12/km LTL · ₹8/km PTL). The weak headline number "
        "is an artifact of mode mixing plus one outlier carrier."
    )

    st.subheader("Median cost per km by carrier")
    cpk = (df.groupby("carrier_id")["cost_per_km"].median()
             .sort_values(ascending=False).reset_index())
    fig = px.bar(cpk, x="carrier_id", y="cost_per_km",
                 color=cpk.carrier_id.eq("CARR_07"),
                 color_discrete_map={True: "#d62728", False: "#1f77b4"},
                 labels={"cost_per_km": "Median ₹/km"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.error(
        "**CARR_07: ₹125.6/km vs fleet median ₹12.9/km — 9.7×, across all modes.** "
        "Cost still scales linearly with distance for CARR_07 (r = 0.73), so the shape "
        "of pricing is normal and only the level is 10× off → likely a unit/currency "
        "recording error rather than real pricing. Flagged, and excluded from fleet "
        "benchmarks."
    )

# ---------------------------------------------------------------- Q3
with tab3:
    st.subheader("Late rate by customer (≥ 20 measurable shipments)")
    m2 = m.copy()
    m2["late"] = ~m2["on_time"]
    cust = (m2.groupby("customer_id")
              .agg(n=("late", "size"), late_rate=("late", "mean"),
                   avg_window=("promised_window_days", "mean"))
              .query("n >= 20").sort_values("late_rate", ascending=False)
              .reset_index())
    fig = px.bar(cust.head(15), x="customer_id", y="late_rate",
                 hover_data=["n", "avg_window"],
                 text=cust.head(15)["late_rate"].map("{:.0%}".format),
                 labels={"late_rate": "Late rate"},
                 color_discrete_sequence=["#c0504d"])
    fig.add_hline(y=m2["late"].mean(), line_dash="dot", annotation_text="baseline 50%")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.warning(
        "CUST_026 / CUST_050 / CUST_116 top the table at ~70–74% late — but none of "
        "these survive multiple-comparison correction across 120 customers "
        "(Bonferroni p ≈ 1.0), their carrier/region mixes are unremarkable, and their "
        "late rates partly track shorter promise windows (r = −0.32 across customers). "
        "**Verdict: not carrier-driven, not region-driven — promise-window exposure "
        "plus small-sample noise.** The actionable fixes are promise-setting and "
        "CARR_02, not customer-specific interventions."
    )

    fig = px.scatter(cust, x="avg_window", y="late_rate", hover_name="customer_id",
                     size="n", labels={"avg_window": "Avg promise window (days)",
                                       "late_rate": "Late rate"})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------- Q4
with tab4:
    st.subheader("Data quality inventory")
    issues = pd.DataFrame([
        ["Completed shipments missing actual_delivery_date", 682,
         "84.5% of South's completed shipments — South OTD is unmeasurable"],
        ["'Delivered' rows that were actually late", "50.2%",
         "status label carries no lateness signal → recomputed from dates"],
        ["'Delayed' rows that were actually late", "48.6%", "same issue, other direction"],
        ["Impossible dates (actual < pickup)", 72, "excluded from duration math"],
        ["Same-city shipments with long distances", 244,
         "median 1,254 km for e.g. Bengaluru→Bengaluru"],
        ["Within-lane distance inconsistency", "~2,100 km median spread",
         "same city pair ranges e.g. 56–2,488 km → distance_km untrustworthy"],
        ["CARR_07 cost level", "9.7× fleet",
         "consistent across modes → suspected unit/currency error"],
        ["Exact duplicate rows", 15, "dropped (5,015 → 5,000)"],
        ["promised_delivery_date == delivery_date", "100% of rows",
         "redundant/ambiguous column"],
        ["Missing booking / pickup dates", "71 / 87", "excluded row-wise where needed"],
    ], columns=["Issue", "Magnitude", "Handling / implication"])
    issues["Magnitude"] = issues["Magnitude"].astype(str)
    st.dataframe(issues, use_container_width=True, hide_index=True)

    st.subheader("Missing actual delivery dates, by region (completed shipments)")
    comp = df[df.status.isin(["Delivered", "Delayed"])]
    missr = (comp.groupby("region")["actual_delivery_date"]
                 .apply(lambda s: s.isna().mean()).reset_index(name="missing"))
    fig = px.bar(missr, x="region", y="missing",
                 text=missr["missing"].map("{:.0%}".format),
                 labels={"missing": "% missing actual date"},
                 color_discrete_sequence=["#e8a33d"])
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(
    "Weekly metric recommendation: **at-risk in-transit rate** — share of in-transit "
    "shipments already past their promised date. Leading (acts before the customer is "
    "let down), catches over-aggressive promise windows, and breaks loudly when a "
    "region stops reporting dates. Full reasoning in BUSINESS_ANSWERS.md."
)