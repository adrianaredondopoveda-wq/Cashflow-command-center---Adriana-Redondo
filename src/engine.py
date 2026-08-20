"""CashFlow Command Center — deterministic finance simulation engine.

The demo deliberately uses generated records so it can be deployed without
credentials or private company data. Replace `generate_demo_portfolio` with
your finance-system adapters in a real deployment.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Scenario:
    opening_cash: float = 350_000
    minimum_cash: float = 175_000
    collection_delay_days: int = 0
    revenue_change_pct: float = 0.0
    discretionary_cost_reduction_pct: float = 0.0
    shock_amount: float = 0.0
    horizon_days: int = 90


def generate_demo_portfolio(seed: int = 17) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return invoice and expense ledgers with sensible operational features."""
    rng = np.random.default_rng(seed)
    customers = ["Northstar Retail", "Atlas Health", "Lumen Commerce", "Cobalt Labs", "Nova Foods", "Helio Media", "Orion Works", "Pioneer Group"]
    today = pd.Timestamp(date.today())
    n = 130
    issued = today - pd.to_timedelta(rng.integers(4, 115, n), unit="D")
    terms = rng.choice([15, 30, 45, 60], n, p=[.12, .51, .27, .10])
    amount = np.exp(rng.normal(9.0, .75, n)).clip(1_000, 65_000).round(2)
    customer = rng.choice(customers, n, p=[.23, .19, .15, .12, .10, .08, .07, .06])
    paid = rng.random(n) < .51
    invoices = pd.DataFrame({"invoice_id": [f"INV-{2000+i}" for i in range(n)], "customer": customer, "issued_date": issued, "due_date": issued + pd.to_timedelta(terms, unit="D"), "amount": amount, "paid": paid})
    invoices["customer_delay_bias"] = invoices.customer.map({"Northstar Retail": 12, "Atlas Health": 5, "Lumen Commerce": 18, "Cobalt Labs": 2, "Nova Foods": 8, "Helio Media": 23, "Orion Works": 4, "Pioneer Group": 9})
    invoices["days_overdue"] = np.maximum(0, (today - invoices.due_date).dt.days)
    # A transparent synthetic collection-risk score, standing in for a trained model.
    logits = -2.4 + .035 * invoices.days_overdue + .000025 * invoices.amount + .025 * invoices.customer_delay_bias
    invoices["late_probability"] = 1 / (1 + np.exp(-logits))
    invoices.loc[invoices.paid, "late_probability"] = 0
    invoices["expected_collection_date"] = invoices.due_date + pd.to_timedelta((invoices.late_probability * 28).round().astype(int), unit="D")
    invoices.loc[invoices.paid, "expected_collection_date"] = pd.NaT

    categories = ["Payroll", "Cloud infrastructure", "Marketing", "Rent & utilities", "Professional services", "Travel"]
    base = [78_000, 15_000, 23_000, 11_000, 12_000, 4_000]
    discretionary = [False, False, True, False, True, True]
    expenses = pd.DataFrame({"category": categories, "monthly_amount": base, "discretionary": discretionary})
    return invoices, expenses


def forecast(invoices: pd.DataFrame, expenses: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    """Daily cash forecast from receivables, recurring expenses and scenario levers."""
    days = pd.date_range(date.today(), periods=scenario.horizon_days + 1, freq="D")
    frame = pd.DataFrame({"date": days, "collections": 0.0, "operating_expenses": 0.0, "shock": 0.0})
    open_invoices = invoices[~invoices.paid].copy()
    collect_dates = pd.to_datetime(open_invoices.expected_collection_date) + pd.Timedelta(days=scenario.collection_delay_days)
    for collection_date, amount in zip(collect_dates, open_invoices.amount):
        mask = frame.date.dt.normalize().eq(collection_date.normalize())
        frame.loc[mask, "collections"] += amount

    daily_expense = expenses.monthly_amount.sum() / 30
    discretionary_daily = expenses.loc[expenses.discretionary, "monthly_amount"].sum() / 30
    frame["operating_expenses"] = daily_expense - discretionary_daily * scenario.discretionary_cost_reduction_pct
    # modest recurring revenue, changed only in the prospective scenario
    frame["collections"] += 8_250 * (1 + scenario.revenue_change_pct)
    frame.loc[frame.index == 0, "shock"] = -scenario.shock_amount
    frame["net_cash_flow"] = frame.collections - frame.operating_expenses + frame.shock
    frame["cash_balance"] = scenario.opening_cash + frame.net_cash_flow.cumsum()
    frame["below_minimum"] = frame.cash_balance < scenario.minimum_cash
    return frame


def risk_summary(forecast_frame: pd.DataFrame, invoices: pd.DataFrame, scenario: Scenario) -> dict:
    lowest = forecast_frame.loc[forecast_frame.cash_balance.idxmin()]
    breach = forecast_frame[forecast_frame.below_minimum]
    open_book = invoices[~invoices.paid]
    expected_at_risk = float((open_book.amount * open_book.late_probability).sum())
    return {
        "minimum_balance": float(lowest.cash_balance),
        "minimum_date": pd.Timestamp(lowest.date),
        "breach_date": None if breach.empty else pd.Timestamp(breach.iloc[0].date),
        "days_below_minimum": int(len(breach)),
        "receivables_at_risk": expected_at_risk,
        "open_receivables": float(open_book.amount.sum()),
    }


def recommendations(invoices: pd.DataFrame, expenses: pd.DataFrame, summary: dict, scenario: Scenario) -> pd.DataFrame:
    open_book = invoices[~invoices.paid].copy()
    open_book["recoverable_cash"] = open_book.amount * (0.35 + 0.65 * open_book.late_probability)
    risky = open_book.sort_values("recoverable_cash", ascending=False).head(3)
    rows = []
    for _, inv in risky.iterrows():
        rows.append({"priority": "P1", "action": f"Escalate collection: {inv.invoice_id} · {inv.customer}", "owner": "Accounts Receivable", "cash_impact": inv.recoverable_cash, "why": f"€{inv.amount:,.0f} due; {inv.late_probability:.0%} probability of late payment"})
    if summary["breach_date"] is not None:
        saving = expenses.loc[expenses.discretionary, "monthly_amount"].sum() * .20
        rows.append({"priority": "P1", "action": "Temporarily reduce discretionary spend by 20%", "owner": "Finance", "cash_impact": saving, "why": "Protects the cash floor while collections are escalated"})
    rows.append({"priority": "P2", "action": "Offer 1% early-payment incentive to the largest at-risk customer", "owner": "Revenue Operations", "cash_impact": risky.iloc[0].amount * .99, "why": "Trades a small discount for liquidity certainty"})
    return pd.DataFrame(rows).sort_values(["priority", "cash_impact"], ascending=[True, False])


def data_drift(invoices: pd.DataFrame, seed: int = 101) -> pd.DataFrame:
    """Small demo of drift monitoring via a population stability index proxy."""
    rng = np.random.default_rng(seed)
    baseline = invoices.amount.sample(min(80, len(invoices)), random_state=seed).to_numpy()
    current = baseline * rng.lognormal(mean=.05, sigma=.22, size=len(baseline))
    edges = np.quantile(baseline, np.linspace(0, 1, 7))
    edges[0], edges[-1] = -np.inf, np.inf
    expected = np.histogram(baseline, bins=edges)[0] / len(baseline)
    actual = np.histogram(current, bins=edges)[0] / len(current)
    psi = np.sum((actual - expected) * np.log((actual + 1e-6) / (expected + 1e-6)))
    status = "Stable" if psi < .1 else "Monitor" if psi < .25 else "Investigate"
    return pd.DataFrame([{"feature": "invoice_amount", "psi": psi, "status": status}, {"feature": "late_payment_probability", "psi": .07, "status": "Stable"}, {"feature": "customer_mix", "psi": .12, "status": "Monitor"}])
