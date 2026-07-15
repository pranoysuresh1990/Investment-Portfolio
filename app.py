import pandas as pd
import streamlit as st

from src.data_loader import closed_positions, current_holdings, parse_portfolio
from src.prices import fetch_live_prices
from src.sheets_client import load_worksheet

st.set_page_config(page_title="My Portfolio Dashboard", layout="wide")
st.title("📊 My Indian Stock Portfolio")

try:
    configured_url = st.secrets.get("sheet_url", "")
except Exception:
    configured_url = ""

if configured_url:
    sheet_url = configured_url
else:
    sheet_url = st.text_input("Google Sheet URL")
    if not sheet_url:
        st.info(
            "Paste your Google Sheet URL above to load your portfolio, or set "
            "`sheet_url` in the app's Secrets so you never have to paste it "
            "again (see README.md)."
        )
        st.stop()

try:
    raw_portfolio = load_worksheet(sheet_url, "My Portfolio")
    portfolio = parse_portfolio(raw_portfolio)
except Exception as e:
    st.error(f"Couldn't load your portfolio: {e}")
    st.stop()

current = current_holdings(portfolio)
closed = closed_positions(portfolio)

if current.empty and closed.empty:
    st.warning("No stocks found in the 'My Portfolio' sheet.")
    st.stop()

if not current.empty:
    yf_tickers = tuple(sorted(current["YF Ticker"].dropna().unique()))
    prices = fetch_live_prices(yf_tickers)
    current = current.merge(prices, on="YF Ticker", how="left")
    current["Current Value"] = current["Quantity"] * current["Current Price"]
    current["Unrealized P&L"] = current["Current Value"] - current["Invested Value"]
    current["Unrealized P&L %"] = (current["Unrealized P&L"] / current["Invested Value"]) * 100

total_invested = current["Invested Value"].sum() if not current.empty else 0
total_current_value = current["Current Value"].sum() if not current.empty else 0
total_unrealized_pl = total_current_value - total_invested
total_unrealized_pct = (total_unrealized_pl / total_invested * 100) if total_invested else 0
total_realized_pl = portfolio["Realized P&L"].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Invested (current holdings)", f"₹{total_invested:,.0f}")
col2.metric("Current Value", f"₹{total_current_value:,.0f}")
col3.metric("Unrealized P&L", f"₹{total_unrealized_pl:,.0f}", f"{total_unrealized_pct:.1f}%")
col4.metric("Realized P&L (all-time)", f"₹{total_realized_pl:,.0f}")


def highlight_pl(val):
    if pd.isna(val):
        return ""
    color = "#d4edda" if val >= 0 else "#f8d7da"
    return f"background-color: {color}"


tab_current, tab_closed = st.tabs(
    [f"Current Holdings ({len(current)})", f"Closed Positions ({len(closed)})"]
)

with tab_current:
    if current.empty:
        st.info("No current holdings.")
    else:
        display_cols = [
            "S.No",
            "Stock",
            "Quantity",
            "Avg Buy Price",
            "Current Price",
            "Invested Value",
            "Current Value",
            "Unrealized P&L",
            "Unrealized P&L %",
            "Realized P&L",
        ]
        styled = (
            current[display_cols]
            .sort_values("Unrealized P&L %", ascending=False)
            .style.map(highlight_pl, subset=["Unrealized P&L", "Unrealized P&L %", "Realized P&L"])
            .format(
                {
                    "Avg Buy Price": "₹{:.2f}",
                    "Current Price": "₹{:.2f}",
                    "Invested Value": "₹{:,.0f}",
                    "Current Value": "₹{:,.0f}",
                    "Unrealized P&L": "₹{:,.0f}",
                    "Unrealized P&L %": "{:.1f}%",
                    "Realized P&L": "₹{:,.0f}",
                }
            )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        missing_prices = current[current["Current Price"].isna()]
        if not missing_prices.empty:
            st.caption(
                "⚠️ Couldn't fetch a live price for: "
                + ", ".join(missing_prices["Stock"].tolist())
            )

with tab_closed:
    if closed.empty:
        st.info("No closed positions.")
    else:
        display_cols = [
            "S.No",
            "Stock",
            "Buy Quantity",
            "Sell Quantity",
            "Avg Buy Price",
            "Avg Sell Price",
            "Total Investment (Historical)",
            "Realized P&L",
            "% Gain/Loss (Sheet)",
        ]
        styled = (
            closed[display_cols]
            .sort_values("% Gain/Loss (Sheet)", ascending=False)
            .style.map(highlight_pl, subset=["Realized P&L", "% Gain/Loss (Sheet)"])
            .format(
                {
                    "Avg Buy Price": "₹{:.2f}",
                    "Avg Sell Price": "₹{:.2f}",
                    "Total Investment (Historical)": "₹{:,.0f}",
                    "Realized P&L": "₹{:,.0f}",
                    "% Gain/Loss (Sheet)": "{:.1f}%",
                }
            )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
