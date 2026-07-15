# My Indian Stock Portfolio Dashboard

A Streamlit dashboard that reads your portfolio live from Google Sheets and
shows current holdings with live NSE/BSE prices from `yfinance`.

## 1. One-time Google Sheets setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and
   create a new project (any name).
2. In that project, enable **Google Sheets API** and **Google Drive API**
   (use the search box, click each, click Enable).
3. Go to **APIs & Services -> Credentials -> Create Credentials -> Service
   Account**. Give it any name and finish the wizard (you can skip the
   optional permission/access steps).
4. Open the service account -> **Keys** tab -> **Add Key -> Create new key
   -> JSON**. This downloads a `.json` key file. Keep it private -- it's a
   credential, like a password.
5. Open your Google Sheet -> **Share** -> paste in the service account's
   email address (looks like
   `something@your-project.iam.gserviceaccount.com`, also found in the JSON
   file as `client_email`) -> give it **Viewer** access -> Share.

## 2. Local setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and:
- Paste each field from the downloaded JSON key file into the matching
  field under `[gcp_service_account]`.
- Set `sheet_url` to your Google Sheet's URL (optional -- you can also just
  paste it into the app each time).

`.streamlit/secrets.toml` is gitignored and will never be committed.

## 3. Run it

```bash
streamlit run app.py
```

This opens the dashboard in your browser. It reads the `My Portfolio` tab
of your sheet, keeps only stocks you currently hold (Holding Quantity > 0),
fetches live prices for each via `yfinance`, and shows a table with P&L
highlighted green (gain) or red (loss).

## Project structure

```
app.py                  Streamlit entry point / page layout
src/sheets_client.py    Live Google Sheets connection (service account)
src/data_loader.py      Parses the "My Portfolio" tab into a clean table
src/prices.py           Live price fetch via yfinance
.streamlit/secrets.toml Your credentials (gitignored, not committed)
```

## Status

- [x] Live Google Sheets connection ("My Portfolio" tab)
- [x] Current holdings table with live prices and P&L highlighting
- [ ] Transactions tab (buy/sell/dividend history)
- [ ] Technical analysis (moving averages, RSI)
- [ ] Fundamentals beyond ROCE (P/E, promoter holding, etc.)
