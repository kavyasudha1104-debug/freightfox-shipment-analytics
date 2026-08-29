# Shipment Analytics 

This project analyzes a shipment dataset containing 5,015 records to evaluate delivery performance, freight pricing, customer delays, and the data-quality issues that affect business conclusions.

**Live dashboard:** <https://freightfox-shipment-analytics-bqnjl8y22czwhtwtmqkcgr.streamlit.app/>

## Repo contents

| File | Description |
|------|-------------|
| `BUSINESS_ANSWERS.md` | Written answers to the five business questions |
| `analysis.py` | Reproducible analysis script |
| `app.py` | Interactive Streamlit dashboard |
| `shipments.csv` | Source dataset |
| `requirements.txt` | Python dependencies |

## Run locally

```bash
git clone <this-repo>
cd shipment-delivery-analytics
pip install -r requirements.txt

python analysis.py       # reproduce every quoted number in the terminal
streamlit run app.py     # dashboard at http://localhost:8501
```

Requires Python 3.10+.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub (public).
2. Go to https://share.streamlit.io → "Create app" → pick the repo, branch `main`, file `app.py`.
3. Deploy — no secrets or config needed; the CSV ships with the repo.

## Approach 
1. I started by checking the quality of the dataset before answering any business questions. I found duplicate rows, missing delivery dates (concentrated almost entirely in the South region, making its on-time rate unreliable), impossible date sequences, inconsistencies in the `status` column, and one carrier with unusually high pricing. Instead of deleting everything, I handled each issue only where it affected the analysis, so every result clearly states the data it is based on.

2. Rather than relying on the `status` column, I calculated on-time delivery directly by comparing the actual and promised delivery dates. This ensured the analysis was based on shipment dates rather than potentially inconsistent status labels.

3. I used statistical tests to check whether the observed differences were meaningful rather than due to random variation. Regional differences in on-time delivery were not statistically significant, while promise windows showed a strong effect (2-day promises were 82% late compared with 19% for 8-day promises). I also found that **CARR_02** had a significantly higher late-delivery rate than the rest of the fleet (59.6% vs. 49.3%).

4. Finally, I built a Streamlit dashboard that presents the findings, visualizations, and relevant data-quality caveats alongside each business question. Since the dataset contains several quality issues, highlighting those caveats is an important part of interpreting the results correctly.

## Tools used

Python (pandas, scipy, plotly), Streamlit, and I used AI tools (Claude, ChatGPT) selectively during development — for debugging and speeding up boilerplate code — while the analytical decisions, statistical approach, and interpretation were my own. 
