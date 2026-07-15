"""Reads data live from a public Google Sheet (no login required).

Requires the sheet's sharing setting to be "Anyone with the link" -> Viewer.
"""

import io
import re
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st


def extract_sheet_id(sheet_url: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError(
            "That doesn't look like a Google Sheets URL. It should look like "
            "https://docs.google.com/spreadsheets/d/XXXXXXXX/edit"
        )
    return match.group(1)


@st.cache_data(ttl=60, show_spinner="Fetching latest data from Google Sheets...")
def load_worksheet(sheet_url: str, worksheet_name: str) -> pd.DataFrame:
    sheet_id = extract_sheet_id(sheet_url)
    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(worksheet_name)}"
    )
    response = requests.get(csv_url, timeout=15)

    if response.status_code != 200 or "text/csv" not in response.headers.get("Content-Type", ""):
        raise ValueError(
            f"Couldn't read the '{worksheet_name}' tab. Make sure the sheet's "
            "sharing setting is 'Anyone with the link' -> Viewer, and that a "
            f"tab named exactly '{worksheet_name}' exists."
        )

    return pd.read_csv(io.StringIO(response.text))
