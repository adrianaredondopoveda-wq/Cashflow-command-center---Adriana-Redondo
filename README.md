# CashFlow Command Center

> **An AI decision system that detects liquidity risk before it becomes a crisis.**

CashFlow Command Center turns receivables, operating costs and scenario levers into an executive liquidity view. It makes the operational question explicit: *what needs to happen now to protect the cash floor?*

## Product capabilities

- 90-day daily liquidity forecast, with an explicit cash-floor policy.
- Transparent collection-risk scoring for open invoices.
- Scenario laboratory: collection delays, revenue movement, discretionary-cost cuts and one-off shocks.
- Prioritised action queue, assigning likely owner, expected cash impact and rationale.
- Board-ready narrative and downloadable executive snapshot.
- Data-drift monitoring using a Population Stability Index proxy.
- Unit tests and Docker support.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

Upload this complete structure, keeping `app.py` at the repository root:

```text
repo/
├── app.py
├── requirements.txt
└── src/
    ├── __init__.py
    └── engine.py
```

The live demo intentionally uses synthetic financial data. Do not claim its output as real forecasting performance. Production use requires authenticated source systems, time-based validation, data lineage, access controls, monitoring and human approval.

## Interview explanation

This is deliberately not “a dashboard.” The app links a forecast to a decision policy and concrete actions. It highlights a central treasury trade-off: reduce a possible cash shortfall while avoiding unnecessarily aggressive collection or cost-cutting measures.

## Important note

By modifying "engine.py", you can include data from different companies and compare their cashflow. The one in this code is just used as an example. 
