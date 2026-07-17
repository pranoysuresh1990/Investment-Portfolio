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
    "roce": "ROCE (TTM)",
    "piotroski": "Piotroski F Score",
}


def _to_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
    )
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


def parse_portfolio(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Parses every row of the 'My Portfolio' sheet (current and closed positions alike)."""
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
            "Moneycontrol URL": raw_df[SHEET_COLUMNS["url_moneycontrol"]].replace("", None),
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
            "ROCE (TTM)": _to_numeric(raw_df[SHEET_COLUMNS["roce"]]),
            "Piotroski F Score": raw_df[SHEET_COLUMNS["piotroski"]],
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


def parse_transactions(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Parses the 'Transactions' sheet down to Ticker/Type/Date, used to work
    out how long each stock has been (or was) held."""
    df = pd.DataFrame(
        {
            "Ticker": raw_df["Ticker"],
            "Type": raw_df["Transaction Type"],
            "Date": pd.to_datetime(raw_df["Date (Text)"], format="%d-%m-%y", errors="coerce"),
        }
    )
    df["YF Ticker"] = df["Ticker"].map(to_yfinance_ticker)
    return df.dropna(subset=["YF Ticker", "Date"])


def holding_periods(transactions: pd.DataFrame) -> pd.DataFrame:
    """First buy date and last sell date per stock. First buy date is used as
    the start of the holding period even if a stock was bought in multiple
    lots over time."""
    first_buy = transactions[transactions["Type"] == "Buy"].groupby("YF Ticker")["Date"].min()
    last_sell = transactions[transactions["Type"] == "Sell"].groupby("YF Ticker")["Date"].max()
    return pd.DataFrame({"First Buy Date": first_buy, "Last Sell Date": last_sell}).reset_index()


def annualized_return(start_value: float, end_value: float, days: float) -> float | None:
    """CAGR: normalizes a raw % gain by how long it took, so a 50% gain in 5
    days and a 50% gain in 5 years don't read the same."""
    if pd.isna(start_value) or pd.isna(end_value) or pd.isna(days):
        return None
    if start_value <= 0 or days <= 0:
        return None
    years = days / 365.25
    return ((end_value / start_value) ** (1 / years) - 1) * 100
