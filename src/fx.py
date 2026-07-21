"""Fetches the current USD->INR exchange rate, used to show a blended INR
figure for US stock holdings (which are tracked in USD)."""

import requests
import streamlit as st


@st.cache_data(ttl=3600, show_spinner="Fetching USD/INR rate...")
def usd_to_inr_rate() -> float | None:
    try:
        response = requests.get(
            "https://api.frankfurter.dev/v1/latest?from=USD&to=INR", timeout=10
        )
        response.raise_for_status()
        return float(response.json()["rates"]["INR"])
    except Exception:
        return None
