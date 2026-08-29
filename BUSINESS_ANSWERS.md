# Shipment Delivery Analytics — Findings
*By Kavya Sudha V*

A shipment was considered on time if the `actual_delivery_date` was on or before the `promised_delivery_date`. After removing 15 duplicate rows, the analysis was performed on the remaining valid shipment records. All numbers below are reproducible by running `analysis.py`.

## 1. Which region has the worst on-time delivery performance — and what's actually driving it?

I started by looking at on-time rates region by region. Central came out lowest on the surface, at 48.3% — but I didn't want to stop there, because a single number without a significance check can be misleading.

Running a chi-square test showed the regional differences weren't statistically significant, meaning they could easily be due to random variation rather than a real regional problem.

Digging further, I found a bigger issue: around 84.5% of completed shipments in the South region were missing actual delivery dates entirely. That makes South's on-time rate essentially unmeasurable and unreliable to compare against other regions.

The real driver of lateness turned out to be the promised delivery window, not geography. Shipments promised in 2 days were late 81.7% of the time, while shipments promised in 8 days were late only 19.3% of the time — a massive gap that had nothing to do with region.

I also found one carrier-level signal that held up statistically: CARR_02 had a late-delivery rate of 59.6%, compared to 49.3% across the rest of the fleet.

**How I checked it:**
- Removed duplicate and invalid records
- Calculated on-time delivery from actual vs. promised delivery dates
- Compared on-time rates by region
- Ran a chi-square test to check whether regional differences were statistically meaningful
- Compared late rates by promise window and by carrier

## 2. Is there a relationship between freight cost and distance? Which carrier(s) deviate?

Yes — freight cost generally rises with distance, but the overall correlation looked surprisingly weak at first (0.296). I suspected this was being distorted by an outlier rather than reflecting the real relationship.

That turned out to be right. One carrier, CARR_07, was pricing wildly out of line with the rest of the fleet. Once I excluded CARR_07 and looked within each transport mode separately, the correlation jumped to roughly 0.985 — an almost perfectly linear relationship between cost and distance.

CARR_07's median freight cost was ₹125.6 per km, compared to ₹12.9 per km for the rest of the fleet — nearly 10x higher. Since this pattern held consistently across every transport mode, it points to a pricing or data-quality issue rather than normal business behavior.

**How I checked it:**
- Calculated the Pearson correlation between freight cost and distance
- Compared freight cost per kilometer across carriers
- Verified the deviation wasn't explained by transport mode

## 3. Which customers are experiencing the most delivery delays — and is it carrier-driven, region-driven, or something else?

A few customers — CUST_026, CUST_050, CUST_116, and CUST_063 — stood out with late-delivery rates around 70%, well above the company-wide baseline of 50%.

My instinct was to check whether this pointed to a specific carrier or region problem before calling them "problem customers." After testing, I found their higher delay rates were mostly explained by shorter promised delivery windows and small sample sizes — not by a distinct regional or carrier pattern.

The one consistent operational issue that held up was CARR_02 again, performing significantly worse than the rest of the fleet.

**How I checked it:**
- Ranked customers by late-delivery rate
- Compared their carrier and region distribution
- Ran statistical tests to check whether the differences were meaningful, not noise
- Compared average promise windows across customers

## 4. What data quality issues did I find, and how did I handle them?

Before drawing any business conclusions, I audited the dataset itself:

- Removed 15 duplicate shipment records
- Found 682 completed shipments missing actual delivery dates — 84.5% of them concentrated in the South region
- Removed 72 records with impossible date sequences (delivery logged before pickup)
- Chose not to rely on the `status` column for performance analysis, since it frequently disagreed with the actual shipment dates
- Identified CARR_07 as a clear pricing outlier
- Found inconsistent distance values recorded for the same shipping routes

Rather than deleting large chunks of the dataset, I handled each issue only where it actually affected a specific analysis, and flagged the relevant limitation wherever it came up in the findings above.

## 5. If I could track exactly one metric weekly to catch delivery problems early, what would it be — and why?

I'd track the percentage of in-transit shipments that are already close to or past their promised delivery date.

This is a leading indicator — it flags delivery problems before customers are actually affected, rather than after the fact. It also surfaces unrealistic delivery promises and underperforming carriers early enough for an operations team to intervene before delays turn into customer complaints.

## What I'd flag if this were a live production dataset

- Improve data collection in the South region, where most actual delivery dates are missing
- Review delivery promise windows — they have a far bigger impact on delays than geography does
- Investigate CARR_07's unusually high freight costs
- Validate the distance data before using it for pricing or benchmarking decisions
- Automate shipment status updates based on delivery dates, to avoid inconsistent reporting between `status` and the actual dates
