# My Indian Stock Portfolio Dashboard

A Streamlit dashboard that reads your portfolio live from a public Google
Sheet and shows current holdings with live NSE/BSE prices from `yfinance`.

## 1. Share your Google Sheet

Open your sheet -> **Share** -> under "General access" choose
**Anyone with the link** -> **Viewer** -> Copy link.

Note: anyone who has this exact link can view your portfolio (no login
needed). Don't post the link anywhere public.

## 2. Run it on Streamlit Community Cloud (no install needed)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   your GitHub account.
2. Click **New app**, pick this repository, pick the branch
   `claude/portfolio-dashboard-india-cxqa7r`, and set the main file to
   `app.py`.
3. Optional but convenient: in **Advanced settings -> Secrets**, add:
   ```toml
   sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
   ```
   This pre-fills your sheet link so you don't have to paste it every visit.
4. Click **Deploy**. You'll get a permanent URL you can bookmark and open
   any time, on any device.
5. In the app's **Settings -> Sharing** on Streamlit Cloud, you can restrict
   who's allowed to view it (e.g. only your Google account) if you don't
   want it fully public.

It reads the `My Portfolio` tab, keeps only stocks you currently hold
(Holding Quantity > 0), fetches live prices for each via `yfinance`, and
shows a table with P&L highlighted green (gain) or red (loss).

## Running locally instead (optional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

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
