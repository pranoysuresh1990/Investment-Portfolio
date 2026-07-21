"""Reads data live from a Google Sheet via the Sheets API.

Uses the actual Sheets API (not the CSV/gviz export) because those export
paths reflect the sheet's active Filter, silently hiding filtered-out rows.
The API reads the real underlying data regardless of any filter.
"""

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
def load_worksheet(sheet_url: str, worksheet_name: str, data_start_row: int = 1) -> pd.DataFrame:
    """data_start_row is the 0-indexed row where data begins; row 0 is always
    treated as the column header. Sheets with a multi-row header (e.g. a
    merged sub-header row, or a blank spacer row) should pass a higher value."""
    sheet_id = extract_sheet_id(sheet_url)

    try:
        api_key = st.secrets["gcp_api_key"]
    except Exception:
        raise ValueError(
            "No Google Sheets API key configured. Add `gcp_api_key` to the "
            "app's Secrets (see README.md)."
        )

    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/"
        f"{quote(worksheet_name)}?key={api_key}"
    )
    response = requests.get(url, timeout=15)

    if response.status_code != 200:
        detail = response.json().get("error", {}).get("message", response.text)
        raise ValueError(
            f"Couldn't read the '{worksheet_name}' tab (HTTP {response.status_code}): "
            f"{detail}. Make sure the sheet is shared as 'Anyone with the link' -> "
            f"Viewer, the API key is valid, and a tab named exactly "
            f"'{worksheet_name}' exists."
        )

    values = response.json().get("values", [])
    if not values:
        return pd.DataFrame()

    header = values[0]
    rows = values[data_start_row:]
    width = len(header)
    # Pad rows shorter than the header, and truncate rows longer than it --
    # a row can end up wider than the header if a cell beyond the header's
    # last column still holds a value (e.g. leftover data after a column
    # was deleted elsewhere in the sheet).
    fitted_rows = [(row + [""] * (width - len(row)))[:width] for row in rows]
    return pd.DataFrame(fitted_rows, columns=header)
