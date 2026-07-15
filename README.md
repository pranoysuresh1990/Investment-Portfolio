# My Indian Stock Portfolio Dashboard

A Streamlit dashboard that reads your portfolio live from a public Google
Sheet and shows current holdings with live NSE/BSE prices from `yfinance`.

## 1. Share your Google Sheet

Open your sheet -> **Share** -> under "General access" choose
**Anyone with the link** -> **Viewer** -> Copy link.

Note: anyone who has this exact link can view your portfolio (no login
needed). Don't post the link anywhere public.

## 2. Local setup

```bash
pip install -r requirements.txt
```

## 3. Run it

```bash
streamlit run app.py
```

This opens the dashboard in your browser. Paste your Google Sheet link into
the box at the top. It reads the `My Portfolio` tab, keeps only stocks you
currently hold (Holding Quantity > 0), fetches live prices for each via
`yfinance`, and shows a table with P&L highlighted green (gain) or red
(loss).

## Project structure

```
app.py                  Streamlit entry point / page layout
src/sheets_client.py    Live Google Sheets connection (public link, CSV export)
src/data_loader.py      Parses the "My Portfolio" tab into a clean table
src/prices.py           Live price fetch via yfinance
```

## Status

- [x] Live Google Sheets connection ("My Portfolio" tab, public link)
- [x] Current holdings table with live prices and P&L highlighting
- [ ] Transactions tab (buy/sell/dividend history)
- [ ] Technical analysis (moving averages, RSI)
- [ ] Fundamentals beyond ROCE (P/E, promoter holding, etc.)
