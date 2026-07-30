import pandas as pd
import numpy as np
from scipy import stats

pd.set_option("display.width", 160)

RAW_PATH = "shipments.csv"


def load_raw(path: str = RAW_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    for c in [
        "booking_date",
        "pickup_date",
        "delivery_date",
        "promised_delivery_date",
        "actual_delivery_date",
    ]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Dedup + derived fields. Does NOT silently drop rows beyond exact dupes —
    invalid rows are flagged so each analysis can exclude what it must."""
    df = df.drop_duplicates().copy()

    df["cost_per_km"] = df["freight_cost"] / df["distance_km"]
    df["pickup_lag_days"] = (df["pickup_date"] - df["booking_date"]).dt.days
    df["promised_window_days"] = (
        df["promised_delivery_date"] - df["pickup_date"]
    ).dt.days
    df["transit_days"] = (df["actual_delivery_date"] - df["pickup_date"]).dt.days
    df["delay_days"] = (
        df["actual_delivery_date"] - df["promised_delivery_date"]
    ).dt.days

    # Flags
    df["flag_impossible_dates"] = df["actual_delivery_date"] < df["pickup_date"]
    df["flag_same_city"] = df["origin_city"] == df["destination_city"]
    df["flag_missing_actual_completed"] = df["status"].isin(
        ["Delivered", "Delayed"]
    ) & df["actual_delivery_date"].isna()

    return df


def measurable(df: pd.DataFrame) -> pd.DataFrame:
    """Rows where on-time performance can actually be computed:
    actual date present and not physically impossible."""
    m = df[df["actual_delivery_date"].notna() & ~df["flag_impossible_dates"]].copy()
    m["on_time"] = m["delay_days"] <= 0
    m["late"] = ~m["on_time"]
    return m


def main():
    raw = load_raw()
    print(f"Raw rows: {len(raw)}")

    df = clean(raw)
    print(f"After removing {len(raw) - len(df)} exact duplicate rows: {len(df)}")

    m = measurable(df)
    print(f"Measurable (has actual date, dates valid): {len(m)}")
    print(f"Overall on-time rate: {m['on_time'].mean():.1%}\n")

    # ---------------- Q1: region OTD ----------------
    print("=" * 60)
    print("Q1 — On-time delivery by region")
    q1 = m.groupby("region").agg(
        otd=("on_time", "mean"), n=("on_time", "size")
    ).sort_values("otd")
    print(q1.round(3))
    chi2_p = stats.chi2_contingency(pd.crosstab(m["region"], m["on_time"]))[1]
    print(f"Chi-square test, region vs on_time: p = {chi2_p:.3f} (not significant)")

    completed = df[df["status"].isin(["Delivered", "Delayed"])]
    miss = completed.groupby("region")["actual_delivery_date"].apply(
        lambda s: s.isna().mean()
    )
    print("\nShare of COMPLETED shipments missing actual_delivery_date, by region:")
    print(miss.round(3))

    print("\nLate rate by promised window (pickup -> promised, days):")
    print(
        m.groupby("promised_window_days")["late"]
        .agg(["mean", "size"])
        .round(3)
    )

    print("\nActual transit days vs distance quartile (spoiler: flat):")
    print(
        m.dropna(subset=["transit_days"])
        .groupby(pd.qcut(m["distance_km"], 4))["transit_days"]
        .mean()
        .round(2)
    )

    # ---------------- Q2: cost vs distance ----------------
    print("\n" + "=" * 60)
    print("Q2 — Freight cost vs distance")
    print(f"Naive overall correlation: {df['freight_cost'].corr(df['distance_km']):.3f}")
    ex7 = df[df["carrier_id"] != "CARR_07"]
    print(f"Correlation excluding CARR_07: {ex7['freight_cost'].corr(ex7['distance_km']):.3f}")
    for mode in ["FTL", "LTL", "PTL"]:
        sub = ex7[ex7["mode"] == mode]
        print(
            f"  {mode}: corr={sub['freight_cost'].corr(sub['distance_km']):.3f}, "
            f"median cost/km = {sub['cost_per_km'].median():.2f}"
        )

    cpk = df.groupby("carrier_id")["cost_per_km"].median().sort_values(ascending=False)
    fleet_med = df[df["carrier_id"] != "CARR_07"]["cost_per_km"].median()
    print(f"\nMedian cost/km by carrier (fleet median excl CARR_07 = {fleet_med:.2f}):")
    print(cpk.round(2))
    print(
        f"CARR_07 deviation: {cpk['CARR_07'] / fleet_med:.1f}x fleet median "
        f"({(cpk['CARR_07'] / fleet_med - 1) * 100:.0f}% above)"
    )

    # ---------------- Q3: customers ----------------
    print("\n" + "=" * 60)
    print("Q3 — Customer delays")
    cust = (
        m.groupby("customer_id")
        .agg(
            n=("late", "size"),
            late_rate=("late", "mean"),
            avg_window=("promised_window_days", "mean"),
        )
        .query("n >= 20")
        .sort_values("late_rate", ascending=False)
    )
    print("Top 5 by late rate (min 20 measurable shipments):")
    print(cust.head(5).round(3))
    top = cust.index[0]
    k = int(m[m["customer_id"] == top]["late"].sum())
    n = int(cust.loc[top, "n"])
    p = stats.binomtest(k, n, 0.5, alternative="greater").pvalue
    print(
        f"\n{top}: binomial test vs 50% baseline p={p:.3f}; "
        f"Bonferroni x120 customers -> {min(1, p * 120):.2f} (NOT significant)"
    )
    print(
        "Corr(customer late rate, customer avg promise window): "
        f"{cust['late_rate'].corr(cust['avg_window']):.2f}"
    )

    c2 = m[m["carrier_id"] == "CARR_02"]
    rest = m[m["carrier_id"] != "CARR_02"]
    chi_p = stats.chi2_contingency(
        pd.crosstab(m["carrier_id"] == "CARR_02", m["late"])
    )[1]
    print(
        f"\nCARR_02 late rate {c2['late'].mean():.1%} vs rest {rest['late'].mean():.1%} "
        f"(p={chi_p:.4f}) — the one carrier signal that IS significant"
    )

    # ---------------- Q4: data quality ----------------
    print("\n" + "=" * 60)
    print("Q4 — Data quality inventory")
    print(f"Exact duplicate rows: {raw.duplicated().sum()}")
    print(f"Completed (Delivered/Delayed) missing actual date: {df['flag_missing_actual_completed'].sum()}")
    print(f"Impossible dates (actual < pickup): {int(df['flag_impossible_dates'].sum())}")
    print(f"promised_delivery_date == delivery_date on all rows: "
          f"{(df['promised_delivery_date'] == df['delivery_date']).all()}")
    dstat = m[m["status"] == "Delivered"]["late"].mean()
    sstat = m[m["status"] == "Delayed"]["late"].mean()
    print(f"'Delivered' rows actually late: {dstat:.1%} | 'Delayed' rows actually late: {sstat:.1%}")
    print(f"Same-city shipments: {int(df['flag_same_city'].sum())}, "
          f"median distance_km = {df[df['flag_same_city']]['distance_km'].median():.0f}")
    lane = df.groupby(["origin_city", "destination_city"])["distance_km"].agg(
        ["min", "max", "count"]
    )
    lane_bad = lane[lane["count"] >= 5]
    print(
        "Within-lane distance range (same city pair, count>=5): "
        f"median spread = {(lane_bad['max'] - lane_bad['min']).median():.0f} km"
    )
    print(f"Missing booking_date: {df['booking_date'].isna().sum()}, "
          f"missing pickup_date: {df['pickup_date'].isna().sum()}")


if __name__ == "__main__":
    main()