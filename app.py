import altair as alt
import pandas as pd
import streamlit as st

from src.data_loader import (
    closed_positions,
    current_holdings,
    holding_periods,
    parse_portfolio,
    parse_transactions,
)
from src.prices import fetch_live_prices
from src.sheets_client import load_worksheet

GOOD = "#0ca30c"
CRITICAL = "#d03b3b"

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
    raw_transactions = load_worksheet(sheet_url, "Transactions", data_start_row=3)
    periods = holding_periods(parse_transactions(raw_transactions))
except Exception as e:
    st.error(f"Couldn't load your portfolio: {e}")
    st.stop()

current = current_holdings(portfolio)
closed = closed_positions(portfolio)

if current.empty and closed.empty:
    st.warning("No stocks found in the 'My Portfolio' sheet.")
    st.stop()

all_yf_tickers = tuple(sorted(portfolio["YF Ticker"].dropna().unique()))
prices = fetch_live_prices(all_yf_tickers)

today = pd.Timestamp.today().normalize()

if not current.empty:
    current = current.merge(prices, on="YF Ticker", how="left")

    used_fallback = current["Current Price"].isna() & current["Current Price (Sheet)"].notna()
    current["Current Price"] = current["Current Price"].fillna(current["Current Price (Sheet)"])

    current["Current Value"] = current["Quantity"] * current["Current Price"]
    current["Unrealized P&L"] = current["Current Value"] - current["Invested Value"]
    current["Unrealized P&L %"] = (current["Unrealized P&L"] / current["Invested Value"]) * 100

    current = current.merge(periods, on="YF Ticker", how="left")
    current["Holding Days"] = (today - current["First Buy Date"]).dt.days
    current["Holding Years"] = current["Holding Days"] / 365.25

if not closed.empty:
    closed = closed.merge(prices, on="YF Ticker", how="left")
    closed["Current Price"] = closed["Current Price"].fillna(closed["Current Price (Sheet)"])

    closed = closed.merge(periods, on="YF Ticker", how="left")
    closed["Holding Days"] = (closed["Last Sell Date"] - closed["First Buy Date"]).dt.days
    closed["Holding Years"] = closed["Holding Days"] / 365.25

total_invested = current["Invested Value"].sum() if not current.empty else 0
total_current_value = current["Current Value"].sum() if not current.empty else 0
total_unrealized_pl = total_current_value - total_invested
total_unrealized_pct = (total_unrealized_pl / total_invested * 100) if total_invested else 0
total_realized_pl = portfolio["Realized P&L"].sum()
total_dividend = portfolio["Total Dividend"].sum()


def highlight_pl(val):
    if pd.isna(val):
        return ""
    color = "#d4edda" if val >= 0 else "#f8d7da"
    return f"background-color: {color}"


tab_overview, tab_current, tab_closed = st.tabs(
    ["Overview", f"Current Holdings ({len(current)})", f"Closed Positions ({len(closed)})"]
)

with tab_overview:
    if current.empty:
        st.info("No current holdings to show.")
    else:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Active Holdings", len(current))
        m2.metric("Total Invested (current holdings)", f"₹{total_invested:,.0f}")
        m3.metric("Current Value of Holdings", f"₹{total_current_value:,.0f}")
        m4.metric("Unrealized P&L", f"₹{total_unrealized_pl:,.0f}", f"{total_unrealized_pct:.1f}%")
        m5.metric("Realized P&L (all-time)", f"₹{total_realized_pl:,.0f}")
        m6.metric("Total Dividend (all-time)", f"₹{total_dividend:,.0f}")

        valid_pl = current[current["Unrealized P&L"].notna()]

        st.markdown("#### Top Performing")
        top_performing = valid_pl[valid_pl["Unrealized P&L"] >= 0].sort_values(
            "Unrealized P&L", ascending=False
        )
        chart = (
            alt.Chart(top_performing)
            .mark_bar(color=GOOD, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X(
                    "Stock:N",
                    sort=list(top_performing["Stock"]),
                    title=None,
                    axis=alt.Axis(labelAngle=-45),
                ),
                y=alt.Y("Unrealized P&L %:Q", title="Unrealized P&L %"),
                tooltip=[
                    "Stock",
                    alt.Tooltip("Unrealized P&L %:Q", format=".1f", title="P&L %"),
                    alt.Tooltip("Unrealized P&L:Q", format=",.0f", title="P&L (₹)"),
                    alt.Tooltip("Invested Value:Q", format=",.0f", title="Invested (₹)"),
                ],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, use_container_width=True)

        st.markdown("#### Top Underperforming")
        underperforming = valid_pl[valid_pl["Unrealized P&L"] < 0].sort_values(
            "Unrealized P&L", ascending=True
        )
        if underperforming.empty:
            st.caption("No underperforming holdings right now.")
        else:
            chart = (
                alt.Chart(underperforming)
                .mark_bar(color=CRITICAL, cornerRadiusBottomLeft=4, cornerRadiusBottomRight=4)
                .encode(
                    x=alt.X(
                        "Stock:N",
                        sort=list(underperforming["Stock"]),
                        title=None,
                        axis=alt.Axis(labelAngle=-45),
                    ),
                    y=alt.Y("Unrealized P&L %:Q", title="Unrealized P&L %"),
                    tooltip=[
                        "Stock",
                        alt.Tooltip("Unrealized P&L %:Q", format=".1f", title="P&L %"),
                        alt.Tooltip("Unrealized P&L:Q", format=",.0f", title="P&L (₹)"),
                        alt.Tooltip("Invested Value:Q", format=",.0f", title="Invested (₹)"),
                    ],
                )
                .properties(height=280)
            )
            st.altair_chart(chart, use_container_width=True)

        st.markdown("#### Investment vs. Performance")
        bubble_df = current.copy()
        bubble_df["Status"] = bubble_df["Unrealized P&L"].apply(
            lambda v: "Gaining" if v >= 0 else "Losing"
        )
        bubble = alt.Chart(bubble_df).mark_circle(opacity=0.75, stroke="white", strokeWidth=1).encode(
            x=alt.X("Unrealized P&L:Q", title="Unrealized P&L (₹)"),
            y=alt.Y("Unrealized P&L %:Q", title="Unrealized P&L (%)"),
            size=alt.Size(
                "Invested Value:Q",
                title="Invested Value (₹)",
                scale=alt.Scale(range=[30, 4000], zero=False),
                legend=None,
            ),
            color=alt.Color(
                "Status:N",
                scale=alt.Scale(domain=["Gaining", "Losing"], range=[GOOD, CRITICAL]),
                legend=alt.Legend(title=None),
            ),
            tooltip=[
                "Stock",
                alt.Tooltip("Invested Value:Q", format=",.0f", title="Invested (₹)"),
                alt.Tooltip("Unrealized P&L:Q", format=",.0f", title="P&L (₹)"),
                alt.Tooltip("Unrealized P&L %:Q", format=".1f", title="P&L %"),
            ],
        )
        zero_x = (
            alt.Chart(pd.DataFrame({"Unrealized P&L": [0]}))
            .mark_rule(color="#898781", strokeWidth=1.5)
            .encode(x="Unrealized P&L:Q")
        )
        zero_y = (
            alt.Chart(pd.DataFrame({"Unrealized P&L %": [0]}))
            .mark_rule(color="#898781", strokeWidth=1.5)
            .encode(y="Unrealized P&L %:Q")
        )
        st.altair_chart(
            (zero_x + zero_y + bubble).properties(height=420).interactive(),
            use_container_width=True,
        )

with tab_current:
    if current.empty:
        st.info("No current holdings.")
    else:
        display_cols = [
            "S.No",
            "Stock",
            "Moneycontrol URL",
            "Quantity",
            "Avg Buy Price",
            "Current Price",
            "Invested Value",
            "Current Value",
            "Unrealized P&L",
            "Unrealized P&L %",
            "Holding Years",
            "Realized P&L",
        ]
        styled = (
            current[display_cols]
            .sort_values("Unrealized P&L %", ascending=False)
            .style.map(
                highlight_pl,
                subset=["Unrealized P&L", "Unrealized P&L %", "Realized P&L"],
            )
            .format(
                {
                    "Avg Buy Price": "₹{:.2f}",
                    "Current Price": "₹{:.2f}",
                    "Invested Value": "₹{:,.0f}",
                    "Current Value": "₹{:,.0f}",
                    "Unrealized P&L": "₹{:,.0f}",
                    "Unrealized P&L %": "{:.1f}%",
                    "Holding Years": "{:.1f}",
                    "Realized P&L": "₹{:,.0f}",
                }
            )
        )
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Moneycontrol URL": st.column_config.LinkColumn("Moneycontrol", display_text="🔗 View")
            },
        )

        fallback_stocks = current.loc[used_fallback, "Stock"].tolist()
        if fallback_stocks:
            st.caption(
                "ℹ️ Live price unavailable, used the sheet's price instead for: "
                + ", ".join(fallback_stocks)
            )

        missing_prices = current[current["Current Price"].isna()]
        if not missing_prices.empty:
            st.caption(
                "⚠️ No price available (live or sheet) for: "
                + ", ".join(missing_prices["Stock"].tolist())
            )

with tab_closed:
    if closed.empty:
        st.info("No closed positions.")
    else:
        display_cols = [
            "S.No",
            "Stock",
            "Moneycontrol URL",
            "Buy Quantity",
            "Current Price",
            "Avg Buy Price",
            "Avg Sell Price",
            "Total Investment (Historical)",
            "Holding Years",
            "Realized P&L",
            "% Gain/Loss (Sheet)",
        ]
        styled = (
            closed[display_cols]
            .sort_values("% Gain/Loss (Sheet)", ascending=False)
            .style.map(
                highlight_pl,
                subset=["Realized P&L", "% Gain/Loss (Sheet)"],
            )
            .format(
                {
                    "Current Price": "₹{:.2f}",
                    "Avg Buy Price": "₹{:.2f}",
                    "Avg Sell Price": "₹{:.2f}",
                    "Total Investment (Historical)": "₹{:,.0f}",
                    "Holding Years": "{:.1f}",
                    "Realized P&L": "₹{:,.0f}",
                    "% Gain/Loss (Sheet)": "{:.1f}%",
                }
            )
        )
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Moneycontrol URL": st.column_config.LinkColumn("Moneycontrol", display_text="🔗 View")
            },
        )
