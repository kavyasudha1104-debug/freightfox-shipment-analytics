# Business Answers

**Candidate Name:** Kavya Sudha V  
**Date:** 30 July 2026

**Note:** After removing 15 duplicate rows, the analysis was performed on valid shipment records. A shipment was considered **on time** if the `actual_delivery_date` was on or before the `promised_delivery_date`. All numbers below are reproducible by running `analysis.py`.

---

# Q1. Which region has the worst on-time delivery performance, and what's actually driving it?

### Answer

Central has the lowest observed on-time delivery rate (**48.3%**), but I would not conclude that Central is the problem. The differences between regions are **not statistically significant**, which means they could simply be due to random variation.

The bigger issue is data quality. Around **84.5% of completed shipments in the South region are missing actual delivery dates**, making South's performance unreliable to compare.

The strongest driver of late deliveries is **the promised delivery window**, not geography. Shipments promised in **2 days were late 81.7% of the time**, while those promised in **8 days were late only 19.3% of the time**.

I also found that **CARR_02** consistently performed worse than the rest of the fleet, with a late-delivery rate of **59.6% compared to 49.3% for all other carriers**.

### How I checked it

- Removed duplicate and invalid records.
- Calculated on-time delivery using actual and promised delivery dates.
- Compared on-time rates by region.
- Used a chi-square test to check whether regional differences were significant.
- Compared late rates by promise window and by carrier.

---

# Q2. Is there a relationship between freight cost and distance? Which carrier(s) deviate?

### Answer

Yes. Freight cost generally increases as distance increases.

However, one carrier (**CARR_07**) is a clear outlier. Including this carrier makes the overall relationship appear much weaker than it really is. After excluding CARR_07, the correlation between freight cost and distance rises from **0.296 overall to roughly 0.985 within each transport mode** — an almost perfectly linear relationship.

CARR_07 has a median freight cost of **₹125.6 per km**, compared with **₹12.9 per km** for the rest of the fleet—almost **10 times higher**. Since this pattern appears across all transport modes, it suggests a possible pricing or data-quality issue rather than normal business behavior.

### How I checked it

- Calculated the Pearson correlation between freight cost and distance.
- Compared freight cost per kilometer across carriers.
- Verified that the difference was not caused by transport mode.

---

# Q3. Which customers are experiencing the most delivery delays? Is it carrier-driven, region-driven, or something else?

### Answer

Customers such as **CUST_026**, **CUST_050**, **CUST_116**, and **CUST_063** have the highest late-delivery rates (around **70%**, against a company-wide rate of **50%**).

However, I would not label them as problem customers. Their higher delay rates are mainly explained by **shorter promised delivery windows** and **small sample sizes**, rather than by a specific region or carrier.

The only consistent operational issue I found was **CARR_02**, which performed significantly worse than the rest of the fleet.

### How I checked it

- Ranked customers by late-delivery rate.
- Compared their carrier and region distribution.
- Used statistical tests to verify whether the differences were meaningful.
- Compared average promise windows across customers.

---

# Q4. What data quality issues did you find, and how did you handle them?

### Answer

Before analyzing the data, I identified several important quality issues:

- Removed **15 duplicate shipment records**.
- Found **682 completed shipments** with missing actual delivery dates — **84.5% of the South region's** completed shipments.
- Removed **72 records** with impossible date sequences (delivery before pickup).
- Ignored the `status` column for performance analysis because it often disagreed with the shipment dates.
- Identified **CARR_07** as a pricing outlier.
- Found inconsistent distance values for the same shipping routes.

Instead of deleting large parts of the dataset, I handled each issue only where it affected the analysis and clearly mentioned any limitations in my findings.

---

# Q5. If you could track exactly one metric weekly to catch delivery problems early, what would it be and why?

### Answer

I would track the **percentage of in-transit shipments that are close to or past their promised delivery date**.

This is a leading indicator that highlights delivery problems before customers are affected. It also helps identify unrealistic delivery promises and poor carrier performance early, allowing the operations team to take corrective action before delays become customer issues.

---

# Anything else you'd flag if this were a real dataset at FreightFox?

- Improve data collection for the South region, where most actual delivery dates are missing.
- Review delivery promise windows because they have a much bigger impact on delays than geography.
- Investigate CARR_07's unusually high freight costs.
- Validate the distance data before using it for pricing or benchmarking.
- Ensure shipment status is automatically updated based on delivery dates to avoid inconsistent reporting.