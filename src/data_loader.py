"""Turns the raw 'My Portfolio' Google Sheet tab into clean portfolio tables."""

import pandas as pd

SHEET_COLUMNS = {
    "serial_no": "S.No",
    "name": "Shares (Unique)",
    "ticker": "Ticker",
    "url_moneycontrol": "URL (Moneycontrol)",
    "buy_quantity": "Buy Quantity",
    "sell_quantity": "Sell Quantity",
    "quantity": "Holding Quantity",
    "current_price_sheet": "Current Share Price (google Finance)",
    "avg_buy_price": "Average Buying Price per Share",
    "avg_sell_price": "Average Selling Price per Share",
    "invested_value": "Total Investment (Holding)",
    "invested_historical": "Total Investment (Historical)",
    "realized_pl": "Realized Profit/Loss (Including Dividends)",
    "unrealized_pl_sheet": "Unrealized Profit/Loss",
    "pct_gain_loss": "% Gain/Loss (Including Dividends)",
    "total_dividend": "Total Dividend",
}


def _to_numeric(series: pd.Series) -> pd.Series:
    """Numbers come back from the Sheets API formatted for display, not raw
    -- e.g. '$81.46', '₹1,234.50', '29.25%' -- so strip anything that isn't
    part of the number itself before parsing."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def to_yfinance_ticker(raw_ticker: str) -> str | None:
    """'NSE:HDFCBANK' -> 'HDFCBANK.NS', 'BOM:500124' -> '500124.BO',
    'NYSE:UBER'/'NASDAQ:NVDA' -> 'UBER'/'NVDA' (US tickers need no suffix)."""
    if not raw_ticker or ":" not in raw_ticker:
        return None
    exchange, code = raw_ticker.split(":", 1)
    exchange = exchange.strip().upper()
    code = code.strip()
    if exchange == "NSE":
        return f"{code}.NS"
    if exchange == "BOM":
        return f"{code}.BO"
    if exchange in ("NYSE", "NASDAQ"):
        return code
    return None


def _clean_url(series: pd.Series) -> pd.Series:
    """Blanks out empty cells and sheet formula errors (#VALUE!, #REF!, etc.)."""
    return series.where(~series.isin(["", "None"]) & ~series.str.startswith("#"), None)


def parse_portfolio(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Parses every row of a stock portfolio sheet ('Indian Stock Portfolio' or
    'US Stock Portfolio' -- both share the same layout), current and closed
    positions alike."""
    missing = [col for col in SHEET_COLUMNS.values() if col not in raw_df.columns]
    if missing:
        raise ValueError(
            "The portfolio sheet is missing expected columns: " + ", ".join(missing)
        )

    df = pd.DataFrame(
        {
            "S.No": _to_numeric(raw_df[SHEET_COLUMNS["serial_no"]]).astype("Int64"),
            "Stock": raw_df[SHEET_COLUMNS["name"]],
            "Ticker": raw_df[SHEET_COLUMNS["ticker"]],
            "Moneycontrol URL": _clean_url(raw_df[SHEET_COLUMNS["url_moneycontrol"]]),
            "Buy Quantity": _to_numeric(raw_df[SHEET_COLUMNS["buy_quantity"]]),
            "Sell Quantity": _to_numeric(raw_df[SHEET_COLUMNS["sell_quantity"]]),
            "Quantity": _to_numeric(raw_df[SHEET_COLUMNS["quantity"]]),
            "Current Price (Sheet)": _to_numeric(raw_df[SHEET_COLUMNS["current_price_sheet"]]),
            "Avg Buy Price": _to_numeric(raw_df[SHEET_COLUMNS["avg_buy_price"]]),
            "Avg Sell Price": _to_numeric(raw_df[SHEET_COLUMNS["avg_sell_price"]]),
            "Invested Value": _to_numeric(raw_df[SHEET_COLUMNS["invested_value"]]),
            "Total Investment (Historical)": _to_numeric(
                raw_df[SHEET_COLUMNS["invested_historical"]]
            ),
            "Realized P&L": _to_numeric(raw_df[SHEET_COLUMNS["realized_pl"]]),
            "Unrealized P&L (Sheet)": _to_numeric(raw_df[SHEET_COLUMNS["unrealized_pl_sheet"]]),
            "% Gain/Loss (Sheet)": _to_numeric(raw_df[SHEET_COLUMNS["pct_gain_loss"]]),
            "Total Dividend": _to_numeric(raw_df[SHEET_COLUMNS["total_dividend"]]),
        }
    )

    df["YF Ticker"] = df["Ticker"].map(to_yfinance_ticker)
    return df


def current_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """Stocks you currently hold (quantity > 0)."""
    return df[df["Quantity"].fillna(0) > 0].reset_index(drop=True)


def closed_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Stocks fully sold (quantity == 0) that you previously held."""
    return df[
        (df["Quantity"].fillna(0) == 0) & (df["Buy Quantity"].fillna(0) > 0)
    ].reset_index(drop=True)


def parse_transactions(raw_df: pd.DataFrame, date_format: str | None = "%d-%m-%y") -> pd.DataFrame:
    """Parses a transactions sheet down to Ticker/Type/Date, used to work out
    how long each stock has been (or was) held. date_format=None auto-infers
    the date format instead of requiring an exact match (for sheets where the
    date column is a real Date cell rather than free-typed text)."""
    dates = raw_df["Date (Text)"]
    parsed_dates = (
        pd.to_datetime(dates, format=date_format, errors="coerce")
        if date_format
        else pd.to_datetime(dates, dayfirst=True, errors="coerce")
    )
    df = pd.DataFrame(
        {
            "Ticker": raw_df["Ticker"],
            "Type": raw_df["Transaction Type"],
            "Date": parsed_dates,
        }
    )
    df["YF Ticker"] = df["Ticker"].map(to_yfinance_ticker)
    return df.dropna(subset=["YF Ticker", "Date"])


def holding_periods(
    transactions: pd.DataFrame, buy_type: str = "Buy", sell_type: str = "Sell"
) -> pd.DataFrame:
    """First buy date and last sell date per stock. First buy date is used as
    the start of the holding period even if a stock was bought in multiple
    lots over time."""
    first_buy = transactions[transactions["Type"] == buy_type].groupby("YF Ticker")["Date"].min()
    last_sell = transactions[transactions["Type"] == sell_type].groupby("YF Ticker")["Date"].max()
    return pd.DataFrame({"First Buy Date": first_buy, "Last Sell Date": last_sell}).reset_index()


MF_SHEET_COLUMNS = {
    "serial_no": "S.no",
    "name": "MF",
    "units": "No. of Units",
    "nav": "NAV",
    "current_value": "Total Value of Holding",
    "invested_value": "Invested Amount",
    "gain_loss": "Gain/Loss",
    "gain_loss_pct": "Gain/Loss %",
}


def parse_mutual_funds(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Parses the 'MFs' sheet. Unlike equity, invested/current value and P&L
    are already computed in the sheet, so this just reads them through."""
    missing = [col for col in MF_SHEET_COLUMNS.values() if col not in raw_df.columns]
    if missing:
        raise ValueError("The 'MFs' sheet is missing expected columns: " + ", ".join(missing))

    df = pd.DataFrame(
        {
            "S.No": _to_numeric(raw_df[MF_SHEET_COLUMNS["serial_no"]]).astype("Int64"),
            "Fund": raw_df[MF_SHEET_COLUMNS["name"]],
            "Units": _to_numeric(raw_df[MF_SHEET_COLUMNS["units"]]),
            "Current NAV": _to_numeric(raw_df[MF_SHEET_COLUMNS["nav"]]),
            "Current Value": _to_numeric(raw_df[MF_SHEET_COLUMNS["current_value"]]),
            "Invested Value": _to_numeric(raw_df[MF_SHEET_COLUMNS["invested_value"]]),
            "Unrealized P&L": _to_numeric(raw_df[MF_SHEET_COLUMNS["gain_loss"]]),
            "Unrealized P&L %": _to_numeric(raw_df[MF_SHEET_COLUMNS["gain_loss_pct"]]),
        }
    )
    return df[df["Units"].fillna(0) > 0].reset_index(drop=True)
