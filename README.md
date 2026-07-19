# My Indian Stock Portfolio Dashboard

A Streamlit dashboard that reads your portfolio live from a public Google
Sheet and shows current holdings using the price in column I ("Current
Share Price (google Finance)") of the "My Portfolio" tab.

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

It reads the `My Portfolio` tab, keeps only stocks you currently hold
(Holding Quantity > 0), uses each stock's price from column I of that
sheet, and shows a table with P&L highlighted green (gain) or red (loss).

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
src/data_loader.py      Parses the "My Portfolio" and "Transactions" tabs into clean tables
```

## Status

- [x] Live Google Sheets connection ("My Portfolio" tab, ignores sheet filters)
- [x] Current holdings table with prices from the sheet and P&L highlighting
- [x] Realized/unrealized P&L, closed positions in a separate tab
- [ ] Transactions tab (buy/sell/dividend history)
- [ ] Technical analysis (moving averages, RSI)
- [ ] Fundamentals beyond ROCE (P/E, promoter holding, etc.)
