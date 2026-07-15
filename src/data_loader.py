"""Turns the raw 'My Portfolio' Google Sheet tab into clean portfolio tables."""

import pandas as pd

SHEET_COLUMNS = {
    "serial_no": "S.No",
    "name": "Shares (Unique)",
    "ticker": "Ticker",
    "buy_quantity": "Buy Quantity",
    "sell_quantity": "Sell Quantity",
    "quantity": "Holding Quantity",
    "avg_buy_price": "Average Buying Price per Share",
    "avg_sell_price": "Average Selling Price per Share",
    "invested_value": "Total Investment (Holding)",
    "invested_historical": "Total Investment (Historical)",
    "realized_pl": "Realized Profit/Loss (Including Dividends)",
    "unrealized_pl_sheet": "Unrealized Profit/Loss",
    "pct_gain_loss": "% Gain/Loss (Including Dividends)",
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
            "Buy Quantity": _to_numeric(raw_df[SHEET_COLUMNS["buy_quantity"]]),
            "Sell Quantity": _to_numeric(raw_df[SHEET_COLUMNS["sell_quantity"]]),
            "Quantity": _to_numeric(raw_df[SHEET_COLUMNS["quantity"]]),
            "Avg Buy Price": _to_numeric(raw_df[SHEET_COLUMNS["avg_buy_price"]]),
            "Avg Sell Price": _to_numeric(raw_df[SHEET_COLUMNS["avg_sell_price"]]),
            "Invested Value": _to_numeric(raw_df[SHEET_COLUMNS["invested_value"]]),
            "Total Investment (Historical)": _to_numeric(
                raw_df[SHEET_COLUMNS["invested_historical"]]
            ),
            "Realized P&L": _to_numeric(raw_df[SHEET_COLUMNS["realized_pl"]]),
            "Unrealized P&L (Sheet)": _to_numeric(raw_df[SHEET_COLUMNS["unrealized_pl_sheet"]]),
            "% Gain/Loss (Sheet)": _to_numeric(raw_df[SHEET_COLUMNS["pct_gain_loss"]]),
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
