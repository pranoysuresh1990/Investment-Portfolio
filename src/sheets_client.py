"""Reads data live from a Google Sheet using a service account."""

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


@st.cache_resource
def get_gspread_client() -> gspread.Client:
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=60, show_spinner="Fetching latest data from Google Sheets...")
def load_worksheet(sheet_url: str, worksheet_name: str) -> pd.DataFrame:
    client = get_gspread_client()
    workbook = client.open_by_url(sheet_url)
    worksheet = workbook.worksheet(worksheet_name)
    values = worksheet.get_all_values()
    if not values:
        return pd.DataFrame()
    header, *rows = values
    return pd.DataFrame(rows, columns=header)
