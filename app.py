import pandas as pd
import streamlit as st

from src.data_loader import parse_holdings
from src.prices import fetch_live_prices
from src.sheets_client import load_worksheet

st.set_page_config(page_title="My Portfolio Dashboard", layout="wide")
st.title("📊 My Indian Stock Portfolio")

if "gcp_service_account" not in st.secrets:
    st.error(
        "No Google credentials found. Add your service account key to "
        "`.streamlit/secrets.toml` (see README.md) before running the app."
    )
    st.stop()

default_url = st.secrets.get("sheet_url", "")
sheet_url = st.text_input("Google Sheet URL", value=default_url)

if not sheet_url:
    st.info("Paste your Google Sheet URL above to load your portfolio.")
    st.stop()

try:
    raw_portfolio = load_worksheet(sheet_url, "My Portfolio")
    holdings = parse_holdings(raw_portfolio)
except Exception as e:
    st.error(f"Couldn't load your portfolio: {e}")
    st.stop()

if holdings.empty:
    st.warning("No current holdings found (everything shows Holding Quantity = 0).")
    st.stop()

yf_tickers = tuple(sorted(holdings["YF Ticker"].dropna().unique()))
prices = fetch_live_prices(yf_tickers)

holdings = holdings.merge(prices, on="YF Ticker", how="left")
holdings["Current Value"] = holdings["Quantity"] * holdings["Current Price"]
holdings["P&L"] = holdings["Current Value"] - holdings["Invested Value"]
holdings["P&L %"] = (holdings["P&L"] / holdings["Invested Value"]) * 100

total_invested = holdings["Invested Value"].sum()
total_current = holdings["Current Value"].sum()
total_pl = total_current - total_invested
total_pl_pct = (total_pl / total_invested * 100) if total_invested else 0

col1, col2, col3 = st.columns(3)
col1.metric("Invested", f"₹{total_invested:,.0f}")
col2.metric("Current Value", f"₹{total_current:,.0f}")
col3.metric("Overall P&L", f"₹{total_pl:,.0f}", f"{total_pl_pct:.1f}%")

display_cols = [
    "Stock",
    "Ticker",
    "Quantity",
    "Avg Buy Price",
    "Current Price",
    "Invested Value",
    "Current Value",
    "P&L",
    "P&L %",
    "ROCE (TTM)",
]


def highlight_pl(val):
    if pd.isna(val):
        return ""
    color = "#d4edda" if val >= 0 else "#f8d7da"
    return f"background-color: {color}"


styled = (
    holdings[display_cols]
    .sort_values("P&L %", ascending=False)
    .style.map(highlight_pl, subset=["P&L", "P&L %"])
    .format(
        {
            "Avg Buy Price": "₹{:.2f}",
            "Current Price": "₹{:.2f}",
            "Invested Value": "₹{:,.0f}",
            "Current Value": "₹{:,.0f}",
            "P&L": "₹{:,.0f}",
            "P&L %": "{:.1f}%",
            "ROCE (TTM)": "{:.1f}%",
        }
    )
)

st.dataframe(styled, use_container_width=True, hide_index=True)

missing_prices = holdings[holdings["Current Price"].isna()]
if not missing_prices.empty:
    st.caption(
        "⚠️ Couldn't fetch a live price for: "
        + ", ".join(missing_prices["Stock"].tolist())
    )
