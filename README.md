# My Investment Portfolio Dashboard

A Streamlit dashboard that reads your investments live from a public Google
Sheet — Indian stocks, mutual funds, and US stocks — using prices already
present in the sheet (via `GOOGLEFINANCE()` formulas or manual entry), with
no live price-fetching from the app itself.

## 1. Share your Google Sheet

Open your sheet -> **Share** -> under "General access" choose
**Anyone with the link** -> **Viewer** -> Copy link.

Note: anyone who has this exact link can view your portfolio (no login
needed). Don't post the link anywhere public.

## 2. Get a free Google Sheets API key

This is needed so the app reads your sheet's real data, ignoring any
Filter you have turned on in the sheet (a plain CSV link would otherwise
silently hide filtered-out rows).

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and
   create a new project (any name), or reuse one you already have.
2. **APIs & Services -> Library**, search **Google Sheets API**, click
   **Enable**.
3. **APIs & Services -> Credentials -> Create Credentials -> API key**.
   Copy the key.
4. Optional but recommended: click **Restrict key**, and under "API
   restrictions" limit it to **Google Sheets API** only, so the key can't
   be used for anything else if it ever leaks.

## 3. Run it on Streamlit Community Cloud (no install needed)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   your GitHub account.
2. Click **New app**, pick this repository, pick the branch
   `claude/portfolio-dashboard-india-cxqa7r`, and set the main file to
   `app.py`.
3. In **Advanced settings -> Secrets**, add:
   ```toml
   sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
   gcp_api_key = "YOUR_API_KEY"
   ```
4. Click **Deploy**. You'll get a permanent URL you can bookmark and open
   any time, on any device.
5. In the app's **Settings -> Sharing** on Streamlit Cloud, you can restrict
   who's allowed to view it (e.g. only your Google account) if you don't
   want it fully public.

## Sheet tabs expected

| Tab name | Purpose |
|---|---|
| `Indian Stock Portfolio` | NSE/BSE holdings, one row per stock |
| `Indian Stock Transactions` | Buy/Sell/Dividend history for Indian stocks |
| `MFs` | Mutual fund holdings, one row per fund |
| `US Stock Portfolio` | US stock holdings, one row per stock (same layout as Indian) |
| `US Stock Wallet Transaction` | Deposit/Invested/Withdrawn/Dividend history for US stocks, including a `Conversion ratio` column used for USD->INR |

## Running locally instead (optional)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then fill in sheet_url and gcp_api_key in that file
streamlit run app.py
```

## Project structure

```
app.py                  Streamlit entry point / page layout
src/sheets_client.py    Live Google Sheets connection (Sheets API, filter-proof)
src/data_loader.py      Parses all five sheet tabs into clean tables
```

## Status

- [x] Live Google Sheets connection, ignores sheet filters
- [x] Indian stocks: current holdings + closed positions, P&L, holding period
- [x] Mutual funds: holdings table
- [x] US stocks: current holdings + closed positions, shown in $ and (where a
      conversion rate is available) ₹
- [x] Overview: separate metrics and performance charts per asset class
- [ ] Technical analysis (moving averages, RSI)
- [ ] Fundamentals (P/E, promoter holding, etc.)

## Known data issue to clean up

Microsoft, Alphabet, and Uber Technologies currently appear as rows in
`Indian Stock Portfolio` too (with malformed tickers like `MSFT:NASDAQ`
instead of `NASDAQ:MSFT`), duplicating what's already correctly tracked in
`US Stock Portfolio`. Worth deleting those 3 rows from `Indian Stock
Portfolio` next time you're in the sheet -- doesn't break the app, but
inflates the Indian holdings count and shows blank prices for those rows.
