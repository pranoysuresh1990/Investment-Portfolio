import altair as alt
import pandas as pd
import streamlit as st

from src.data_loader import (
    closed_positions,
    current_holdings,
    holding_periods,
    parse_mutual_funds,
    parse_portfolio,
    parse_transactions,
)
from src.fx import usd_to_inr_rate
from src.sheets_client import load_worksheet

GOOD = "#0ca30c"
CRITICAL = "#d03b3b"

st.set_page_config(page_title="My Portfolio Dashboard", layout="wide")
st.title("📊 My Investment Portfolio")

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
    raw_ind_portfolio = load_worksheet(sheet_url, "Indian Stock Portfolio")
    ind_portfolio = parse_portfolio(raw_ind_portfolio)
    raw_ind_txns = load_worksheet(sheet_url, "Indian Stock Transactions", data_start_row=3)
    ind_periods = holding_periods(parse_transactions(raw_ind_txns))

    raw_mfs = load_worksheet(sheet_url, "MFs")
    mfs = parse_mutual_funds(raw_mfs)

    raw_us_portfolio = load_worksheet(sheet_url, "US Stock Portfolio")
    us_portfolio = parse_portfolio(raw_us_portfolio)
    raw_us_wallet = load_worksheet(sheet_url, "US Stock Wallet Transaction", data_start_row=3)
    us_periods = holding_periods(
        parse_transactions(raw_us_wallet, date_format=None), buy_type="Invested", sell_type="Withdrawn"
    )
except Exception as e:
    st.error(f"Couldn't load your portfolio: {e}")
    st.stop()

usd_inr_rate = usd_to_inr_rate()

today = pd.Timestamp.today().normalize()


def with_pl_and_holding_period(df: pd.DataFrame, periods: pd.DataFrame, end_date: pd.Timestamp) -> pd.DataFrame:
    """Adds Current Price/Value, Unrealized P&L, and holding-period columns to
    a parsed portfolio slice (current holdings or closed positions)."""
    if df.empty:
        return df
    df = df.copy()
    df["Current Price"] = df["Current Price (Sheet)"]
    df["Current Value"] = df["Quantity"] * df["Current Price"]
    df["Unrealized P&L"] = df["Current Value"] - df["Invested Value"]
    df["Unrealized P&L %"] = (df["Unrealized P&L"] / df["Invested Value"]) * 100
    df = df.merge(periods, on="YF Ticker", how="left")
    df["Holding Days"] = (end_date - df["First Buy Date"]).dt.days
    df["Holding Years"] = df["Holding Days"] / 365.25
    return df


ind_current = with_pl_and_holding_period(current_holdings(ind_portfolio), ind_periods, today)
ind_closed_raw = closed_positions(ind_portfolio)
if not ind_closed_raw.empty:
    ind_closed_raw["Current Price"] = ind_closed_raw["Current Price (Sheet)"]
    ind_closed_raw = ind_closed_raw.merge(ind_periods, on="YF Ticker", how="left")
    ind_closed_raw["Holding Days"] = (
        ind_closed_raw["Last Sell Date"] - ind_closed_raw["First Buy Date"]
    ).dt.days
    ind_closed_raw["Holding Years"] = ind_closed_raw["Holding Days"] / 365.25
ind_closed = ind_closed_raw

us_current = with_pl_and_holding_period(current_holdings(us_portfolio), us_periods, today)
us_closed = closed_positions(us_portfolio)
if not us_closed.empty:
    us_closed["Current Price"] = us_closed["Current Price (Sheet)"]
    us_closed = us_closed.merge(us_periods, on="YF Ticker", how="left")
    us_closed["Holding Days"] = (us_closed["Last Sell Date"] - us_closed["First Buy Date"]).dt.days
    us_closed["Holding Years"] = us_closed["Holding Days"] / 365.25

if usd_inr_rate:
    for df in (us_current, us_closed):
        if not df.empty:
            for col in ["Invested Value", "Current Value", "Unrealized P&L", "Realized P&L"]:
                if col in df.columns:
                    df[f"{col} (₹)"] = df[col] * usd_inr_rate

if ind_current.empty and ind_closed.empty and mfs.empty and us_current.empty and us_closed.empty:
    st.warning("No holdings found in any sheet.")
    st.stop()

# ---- Indian stocks totals ----
ind_total_invested = ind_current["Invested Value"].sum() if not ind_current.empty else 0
ind_total_current_value = ind_current["Current Value"].sum() if not ind_current.empty else 0
ind_total_unrealized_pl = ind_total_current_value - ind_total_invested
ind_total_unrealized_pct = (ind_total_unrealized_pl / ind_total_invested * 100) if ind_total_invested else 0
ind_total_realized_pl = ind_portfolio["Realized P&L"].sum()
ind_total_dividend = ind_portfolio["Total Dividend"].sum()

# ---- Mutual funds totals ----
mf_total_invested = mfs["Invested Value"].sum() if not mfs.empty else 0
mf_total_current_value = mfs["Current Value"].sum() if not mfs.empty else 0
mf_total_unrealized_pl = mfs["Unrealized P&L"].sum() if not mfs.empty else 0
mf_total_unrealized_pct = (mf_total_unrealized_pl / mf_total_invested * 100) if mf_total_invested else 0

# ---- US stocks totals (USD, with INR alongside) ----
us_total_invested = us_current["Invested Value"].sum() if not us_current.empty else 0
us_total_current_value = us_current["Current Value"].sum() if not us_current.empty else 0
us_total_unrealized_pl = us_total_current_value - us_total_invested
us_total_unrealized_pct = (us_total_unrealized_pl / us_total_invested * 100) if us_total_invested else 0
us_total_realized_pl = us_portfolio["Realized P&L"].sum()
us_total_dividend = us_portfolio["Total Dividend"].sum()


def highlight_pl(val):
    if pd.isna(val):
        return ""
    color = "#d4edda" if val >= 0 else "#f8d7da"
    return f"background-color: {color}"


def render_performance_charts(df: pd.DataFrame, currency: str):
    valid_pl = df[df["Unrealized P&L"].notna()]

    st.markdown("##### Top Performing")
    top_performing = valid_pl[valid_pl["Unrealized P&L"] >= 0].sort_values("Unrealized P&L", ascending=False)
    if top_performing.empty:
        st.caption("No gaining holdings right now.")
    else:
        chart = (
            alt.Chart(top_performing)
            .mark_bar(color=GOOD, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X(
                    "Stock:N", sort=list(top_performing["Stock"]), title=None, axis=alt.Axis(labelAngle=-45)
                ),
                y=alt.Y("Unrealized P&L %:Q", title="Unrealized P&L %"),
                tooltip=[
                    "Stock",
                    alt.Tooltip("Unrealized P&L %:Q", format=".1f", title="P&L %"),
                    alt.Tooltip("Unrealized P&L:Q", format=",.0f", title=f"P&L ({currency})"),
                    alt.Tooltip("Invested Value:Q", format=",.0f", title=f"Invested ({currency})"),
                ],
            )
            .properties(height=280, width=alt.Step(50))
        )
        st.altair_chart(chart, use_container_width=False)

    st.markdown("##### Top Underperforming")
    underperforming = valid_pl[valid_pl["Unrealized P&L"] < 0].sort_values("Unrealized P&L", ascending=True)
    if underperforming.empty:
        st.caption("No underperforming holdings right now.")
    else:
        chart = (
            alt.Chart(underperforming)
            .mark_bar(color=CRITICAL, cornerRadiusBottomLeft=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X(
                    "Stock:N", sort=list(underperforming["Stock"]), title=None, axis=alt.Axis(labelAngle=-45)
                ),
                y=alt.Y("Unrealized P&L %:Q", title="Unrealized P&L %"),
                tooltip=[
                    "Stock",
                    alt.Tooltip("Unrealized P&L %:Q", format=".1f", title="P&L %"),
                    alt.Tooltip("Unrealized P&L:Q", format=",.0f", title=f"P&L ({currency})"),
                    alt.Tooltip("Invested Value:Q", format=",.0f", title=f"Invested ({currency})"),
                ],
            )
            .properties(height=280, width=alt.Step(50))
        )
        st.altair_chart(chart, use_container_width=False)

    st.markdown("##### Investment vs. Performance")
    bubble_df = df.copy()
    bubble_df["Status"] = bubble_df["Unrealized P&L"].apply(lambda v: "Gaining" if v >= 0 else "Losing")
    bubble = alt.Chart(bubble_df).mark_circle(opacity=0.75, stroke="white", strokeWidth=1).encode(
        x=alt.X("Unrealized P&L:Q", title=f"Unrealized P&L ({currency})"),
        y=alt.Y("Unrealized P&L %:Q", title="Unrealized P&L (%)"),
        size=alt.Size(
            "Invested Value:Q",
            title=f"Invested Value ({currency})",
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
            alt.Tooltip("Invested Value:Q", format=",.0f", title=f"Invested ({currency})"),
            alt.Tooltip("Unrealized P&L:Q", format=",.0f", title=f"P&L ({currency})"),
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


def render_moneycontrol_table(df: pd.DataFrame, display_cols: list, sort_col: str, pl_cols: list, formats: dict):
    styled = (
        df[display_cols]
        .sort_values(sort_col, ascending=False)
        .style.map(highlight_pl, subset=pl_cols)
        .format(formats)
    )
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Moneycontrol URL": st.column_config.LinkColumn("Moneycontrol", display_text="🔗 View")
        },
    )


tab_overview, tab_ind_current, tab_ind_closed, tab_mf, tab_us_current, tab_us_closed = st.tabs(
    [
        "Overview",
        f"Indian Holdings ({len(ind_current)})",
        f"Indian Closed ({len(ind_closed)})",
        f"Mutual Funds ({len(mfs)})",
        f"US Holdings ({len(us_current)})",
        f"US Closed ({len(us_closed)})",
    ]
)

with tab_overview:
    st.markdown("### 🇮🇳 Indian Stocks")
    if ind_current.empty:
        st.info("No current Indian stock holdings.")
    else:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Active Holdings", len(ind_current))
        m2.metric("Total Invested", f"₹{ind_total_invested:,.0f}")
        m3.metric("Current Value", f"₹{ind_total_current_value:,.0f}")
        m4.metric("Unrealized P&L", f"₹{ind_total_unrealized_pl:,.0f}", f"{ind_total_unrealized_pct:.1f}%")
        m5.metric("Realized P&L (all-time)", f"₹{ind_total_realized_pl:,.0f}")
        m6.metric("Total Dividend (all-time)", f"₹{ind_total_dividend:,.0f}")
        render_performance_charts(ind_current, "₹")

    st.divider()
    st.markdown("### 💰 Mutual Funds")
    if mfs.empty:
        st.info("No mutual fund holdings.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Active Funds", len(mfs))
        m2.metric("Total Invested", f"₹{mf_total_invested:,.0f}")
        m3.metric("Current Value", f"₹{mf_total_current_value:,.0f}")
        m4.metric("Unrealized P&L", f"₹{mf_total_unrealized_pl:,.0f}", f"{mf_total_unrealized_pct:.1f}%")

    st.divider()
    st.markdown("### 🇺🇸 US Stocks")
    if us_current.empty:
        st.info("No current US stock holdings.")
    else:
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Active Holdings", len(us_current))
        m2.metric("Total Invested", f"${us_total_invested:,.2f}")
        m3.metric("Current Value", f"${us_total_current_value:,.2f}")
        m4.metric("Unrealized P&L", f"${us_total_unrealized_pl:,.2f}", f"{us_total_unrealized_pct:.1f}%")
        if usd_inr_rate:
            m5.metric("Current Value (₹)", f"₹{us_total_current_value * usd_inr_rate:,.0f}")
            m6.metric("Unrealized P&L (₹)", f"₹{us_total_unrealized_pl * usd_inr_rate:,.0f}")
        else:
            m5.metric("Total Dividend (all-time)", f"${us_total_dividend:,.2f}")
        render_performance_charts(us_current, "$")

with tab_ind_current:
    if ind_current.empty:
        st.info("No current holdings.")
    else:
        display_cols = [
            "S.No", "Stock", "Moneycontrol URL", "Quantity", "Avg Buy Price", "Current Price",
            "Invested Value", "Current Value", "Unrealized P&L", "Unrealized P&L %",
            "Holding Years", "Realized P&L", "Total Dividend",
        ]
        render_moneycontrol_table(
            ind_current, display_cols, "Unrealized P&L %",
            ["Unrealized P&L", "Unrealized P&L %", "Realized P&L"],
            {
                "Avg Buy Price": "₹{:.2f}", "Current Price": "₹{:.2f}", "Invested Value": "₹{:,.0f}",
                "Current Value": "₹{:,.0f}", "Unrealized P&L": "₹{:,.0f}", "Unrealized P&L %": "{:.1f}%",
                "Holding Years": "{:.1f}", "Realized P&L": "₹{:,.0f}", "Total Dividend": "₹{:,.0f}",
            },
        )
        missing_prices = ind_current[ind_current["Current Price"].isna()]
        if not missing_prices.empty:
            st.caption(
                "⚠️ No price in column I of 'Indian Stock Portfolio' for: "
                + ", ".join(missing_prices["Stock"].tolist())
            )

with tab_ind_closed:
    if ind_closed.empty:
        st.info("No closed positions.")
    else:
        display_cols = [
            "S.No", "Stock", "Moneycontrol URL", "Buy Quantity", "Current Price", "Avg Buy Price",
            "Avg Sell Price", "Total Investment (Historical)", "Holding Years", "Realized P&L",
            "% Gain/Loss (Sheet)",
        ]
        render_moneycontrol_table(
            ind_closed, display_cols, "% Gain/Loss (Sheet)",
            ["Realized P&L", "% Gain/Loss (Sheet)"],
            {
                "Current Price": "₹{:.2f}", "Avg Buy Price": "₹{:.2f}", "Avg Sell Price": "₹{:.2f}",
                "Total Investment (Historical)": "₹{:,.0f}", "Holding Years": "{:.1f}",
                "Realized P&L": "₹{:,.0f}", "% Gain/Loss (Sheet)": "{:.1f}%",
            },
        )

with tab_mf:
    if mfs.empty:
        st.info("No mutual fund holdings.")
    else:
        styled = (
            mfs.sort_values("Unrealized P&L %", ascending=False)
            .style.map(highlight_pl, subset=["Unrealized P&L", "Unrealized P&L %"])
            .format(
                {
                    "Units": "{:,.3f}", "Current NAV": "₹{:.2f}", "Current Value": "₹{:,.0f}",
                    "Invested Value": "₹{:,.0f}", "Unrealized P&L": "₹{:,.0f}", "Unrealized P&L %": "{:.1f}%",
                }
            )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

with tab_us_current:
    if us_current.empty:
        st.info("No current holdings.")
    else:
        display_cols = [
            "S.No", "Stock", "Quantity", "Avg Buy Price", "Current Price",
            "Invested Value", "Current Value", "Unrealized P&L", "Unrealized P&L %",
            "Holding Years", "Realized P&L",
        ]
        formats = {
            "Quantity": "{:,.4f}", "Avg Buy Price": "${:.2f}", "Current Price": "${:.2f}",
            "Invested Value": "${:,.2f}", "Current Value": "${:,.2f}", "Unrealized P&L": "${:,.2f}",
            "Unrealized P&L %": "{:.1f}%", "Holding Years": "{:.1f}", "Realized P&L": "${:,.2f}",
        }
        if usd_inr_rate:
            display_cols += ["Invested Value (₹)", "Current Value (₹)", "Unrealized P&L (₹)"]
            formats.update(
                {
                    "Invested Value (₹)": "₹{:,.0f}", "Current Value (₹)": "₹{:,.0f}",
                    "Unrealized P&L (₹)": "₹{:,.0f}",
                }
            )
        styled = (
            us_current[display_cols]
            .sort_values("Unrealized P&L %", ascending=False)
            .style.map(highlight_pl, subset=["Unrealized P&L", "Unrealized P&L %", "Realized P&L"])
            .format(formats)
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        if not usd_inr_rate:
            st.caption("⚠️ Couldn't fetch the live USD→INR exchange rate right now.")
        missing_prices = us_current[us_current["Current Price"].isna()]
        if not missing_prices.empty:
            st.caption(
                "⚠️ No price in column I of 'US Stock Portfolio' for: "
                + ", ".join(missing_prices["Stock"].tolist())
            )

with tab_us_closed:
    if us_closed.empty:
        st.info("No closed positions.")
    else:
        display_cols = [
            "S.No", "Stock", "Buy Quantity", "Current Price", "Avg Buy Price", "Avg Sell Price",
            "Total Investment (Historical)", "Holding Years", "Realized P&L", "% Gain/Loss (Sheet)",
        ]
        formats = {
            "Buy Quantity": "{:,.4f}", "Current Price": "${:.2f}", "Avg Buy Price": "${:.2f}",
            "Avg Sell Price": "${:.2f}", "Total Investment (Historical)": "${:,.2f}",
            "Holding Years": "{:.1f}", "Realized P&L": "${:,.2f}", "% Gain/Loss (Sheet)": "{:.1f}%",
        }
        if usd_inr_rate:
            display_cols += ["Realized P&L (₹)"]
            formats.update({"Realized P&L (₹)": "₹{:,.0f}"})
        styled = (
            us_closed[display_cols]
            .sort_values("% Gain/Loss (Sheet)", ascending=False)
            .style.map(highlight_pl, subset=["Realized P&L", "% Gain/Loss (Sheet)"])
            .format(formats)
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
