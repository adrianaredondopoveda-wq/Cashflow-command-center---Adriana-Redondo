from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.engine import Scenario, data_drift, forecast, generate_demo_portfolio, recommendations, risk_summary

st.set_page_config(page_title="CashFlow Command Center", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

@st.cache_data(show_spinner=False)
def load_portfolio():
    return generate_demo_portfolio()


invoices, expenses = load_portfolio()

with st.sidebar:
    st.title("◈ CashFlow\nCommand Center")
    st.caption("Decision intelligence for treasury teams")
    st.divider()
    st.subheader("Scenario controls")
    opening_cash = st.number_input("Opening cash (€)", 0, value=350_000, step=10_000)
    cash_floor = st.number_input("Minimum cash floor (€)", 0, value=175_000, step=10_000)
    delay = st.slider("Collection delay (days)", -10, 45, 0)
    revenue_change = st.slider("Prospective revenue change", -30, 30, 0) / 100
    cost_reduction = st.slider("Discretionary-cost reduction", 0, 50, 0) / 100
    shock = st.number_input("One-off cash shock (€)", 0, value=0, step=5_000)
    st.divider()
    st.caption("Demo uses transparent synthetic records; it is not financial advice.")

scenario = Scenario(float(opening_cash), float(cash_floor), delay, revenue_change, cost_reduction, float(shock))
cash_forecast = forecast(invoices, expenses, scenario)
summary = risk_summary(cash_forecast, invoices, scenario)
actions = recommendations(invoices, expenses, summary, scenario)

st.title("Treasury, before the surprise.")
st.caption(f"Live scenario · generated {date.today().strftime('%d %b %Y')} · 90-day liquidity horizon")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Lowest projected cash", f"€{summary['minimum_balance']:,.0f}", summary["minimum_date"].strftime("%d %b"))
c2.metric("Cash floor", f"€{scenario.minimum_cash:,.0f}", f"{summary['days_below_minimum']} days breached" if summary["breach_date"] else "No projected breach")
c3.metric("Receivables at risk", f"€{summary['receivables_at_risk']:,.0f}", f"of €{summary['open_receivables']:,.0f} open")
c4.metric("Actions identified", len(actions), f"€{actions.cash_impact.sum():,.0f} potential impact")

chart, decision = st.columns([1.7, 1])
with chart:
    st.subheader("90-day liquidity forecast")
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=cash_forecast.date, y=cash_forecast.cash_balance, name="Projected cash", mode="lines", line=dict(color="#55D6BE", width=3), fill="tozeroy", fillcolor="rgba(85,214,190,.08)"))
    figure.add_hline(y=scenario.minimum_cash, line_dash="dash", line_color="#FFB547", annotation_text="Minimum cash floor")
    if summary["breach_date"]:
        figure.add_vline(x=summary["breach_date"], line_dash="dot", line_color="#FF5C77", annotation_text="First breach")
    figure.update_layout(template="plotly_dark", height=390, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="Cash (€)", xaxis_title=None, legend=dict(orientation="h", y=1.1))
    st.plotly_chart(figure, use_container_width=True)
with decision:
    st.subheader("Executive decision")
    if summary["breach_date"]:
        gap = scenario.minimum_cash - summary["minimum_balance"]
        st.error(f"**Liquidity risk detected**\n\nCash is projected to breach the floor on **{summary['breach_date'].strftime('%d %b')}**. Peak deficit versus floor: **€{gap:,.0f}**.")
    else:
        buffer = summary["minimum_balance"] - scenario.minimum_cash
        st.success(f"**Liquidity protected**\n\nThe forecast stays above the floor. Tightest buffer: **€{buffer:,.0f}** on {summary['minimum_date'].strftime('%d %b')}.")
    st.caption("Recommendation engine prioritises actions by expected cash impact and collection risk.")

st.subheader("Recommended action queue")
view = actions.copy()
view["cash_impact"] = view.cash_impact.map(lambda value: f"€{value:,.0f}")
st.dataframe(view, hide_index=True, use_container_width=True, column_config={"priority": st.column_config.TextColumn("Priority", width="small"), "cash_impact": st.column_config.TextColumn("Expected cash impact")})

t1, t2, t3 = st.tabs(["Receivables intelligence", "Scenario narrative", "Model health"])
with t1:
    receivables = invoices[~invoices.paid].sort_values("late_probability", ascending=False)[["invoice_id", "customer", "amount", "due_date", "days_overdue", "late_probability", "expected_collection_date"]].head(12).copy()
    receivables.amount = receivables.amount.map(lambda value: f"€{value:,.0f}")
    receivables.late_probability = receivables.late_probability.map(lambda value: f"{value:.0%}")
    st.dataframe(receivables, hide_index=True, use_container_width=True)
with t2:
    change = "no change" if revenue_change == 0 else f"{revenue_change:+.0%} prospective revenue change"
    st.markdown(f"""### Board-ready narrative

Under this scenario, the organisation starts with **€{scenario.opening_cash:,.0f}** and reaches its lowest cash position of **€{summary['minimum_balance']:,.0f}** on **{summary['minimum_date'].strftime('%d %B')}**. The model incorporates a **{scenario.collection_delay_days:+d}-day** collection movement, **{change}**, and **{scenario.discretionary_cost_reduction_pct:.0%}** discretionary-spend reduction.

The priority is to protect liquidity by resolving the three highest-risk invoices, which represent the strongest near-term intervention opportunities.
""")
    report = f"CashFlow Command Center report\nLowest projected cash: €{summary['minimum_balance']:,.0f}\nDate: {summary['minimum_date'].date()}\nReceivables at risk: €{summary['receivables_at_risk']:,.0f}\n"
    st.download_button("Download executive snapshot", report, file_name="cashflow-executive-snapshot.txt", mime="text/plain")
with t3:
    drift = data_drift(invoices)
    st.caption("Population Stability Index (PSI) compares current operational data with the model baseline. PSI > 0.25 requires investigation before automated use.")
    st.dataframe(drift.style.format({"psi": "{:.3f}"}), hide_index=True, use_container_width=True)
    st.info("Governance status: demo model only. A production implementation requires time-based backtesting, data lineage, access controls, monitoring and human approval for actions.")
