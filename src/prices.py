"""Fetches live NSE/BSE prices via yfinance."""

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300, show_spinner="Fetching live prices...")
def fetch_live_prices(yf_tickers: tuple[str, ...]) -> pd.DataFrame:
    """Returns a DataFrame of YF Ticker -> Current Price for each ticker given."""
    rows = []
    tickers = yf.Tickers(" ".join(yf_tickers))
    for symbol in yf_tickers:
        price = None
        try:
            price = tickers.tickers[symbol].fast_info.last_price
        except Exception:
            pass
        rows.append({"YF Ticker": symbol, "Current Price": price})
    return pd.DataFrame(rows)
