"""Turns the raw 'My Portfolio' Google Sheet tab into a clean holdings table."""

import pandas as pd

SHEET_COLUMNS = {
    "serial_no": "S.No",
    "name": "Shares (Unique)",
    "ticker": "Ticker",
    "quantity": "Holding Quantity",
    "avg_buy_price": "Average Buying Price per Share",
    "invested_value": "Total Investment (Holding)",
    "roce": "ROCE (TTM)",
    "piotroski": "Piotroski F Score",
}


def _to_numeric(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def to_yfinance_ticker(raw_ticker: str) -> str | None:
    """'NSE:HDFCBANK' -> 'HDFCBANK.NS', 'BOM:500124' -> '500124.BO'."""
    if not raw_ticker or ":" not in raw_ticker:
        return None
    exchange, code = raw_ticker.split(":", 1)
    exchange = exchange.strip().upper()
    code = code.strip()
    if exchange == "NSE":
        return f"{code}.NS"
    if exchange == "BOM":
        return f"{code}.BO"
    return None


def parse_holdings(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Filters the raw sheet down to stocks you currently hold (quantity > 0)."""
    missing = [col for col in SHEET_COLUMNS.values() if col not in raw_df.columns]
    if missing:
        raise ValueError(
            "The 'My Portfolio' sheet is missing expected columns: " + ", ".join(missing)
        )

    df = pd.DataFrame(
        {
            "S.No": _to_numeric(raw_df[SHEET_COLUMNS["serial_no"]]).astype("Int64"),
            "Stock": raw_df[SHEET_COLUMNS["name"]],
            "Ticker": raw_df[SHEET_COLUMNS["ticker"]],
            "Quantity": _to_numeric(raw_df[SHEET_COLUMNS["quantity"]]),
            "Avg Buy Price": _to_numeric(raw_df[SHEET_COLUMNS["avg_buy_price"]]),
            "Invested Value": _to_numeric(raw_df[SHEET_COLUMNS["invested_value"]]),
            "ROCE (TTM)": _to_numeric(raw_df[SHEET_COLUMNS["roce"]]),
            "Piotroski F Score": raw_df[SHEET_COLUMNS["piotroski"]],
        }
    )

    df["YF Ticker"] = df["Ticker"].map(to_yfinance_ticker)
    df = df[df["Quantity"].fillna(0) > 0].reset_index(drop=True)
    return df
