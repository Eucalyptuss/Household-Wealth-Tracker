# Household Wealth Tracker

**Creator:** Eucalyptuss  
**Code Version:** 1.0

Household Wealth Tracker is a Streamlit-based household investment dashboard for managing ETF portfolios across multiple owners, retirement accounts, and taxable brokerage accounts. It supports account master data, BUY/SELL transaction tracking, FIFO realized P/L, active and closed position handling, actual dividend cash-flow tracking, estimated dividend forecasting, and household-level exposure analysis.

> This project is not investment, tax, or financial advice. Online market and dividend data may be delayed, incomplete, or inaccurate. Always verify all data with your broker, official fund documents, and qualified professionals when needed.

---

## 1. Project Structure

```text
household_wealth_tracker/
├── app.py
├── accounts.csv
├── portfolio.csv
├── dividends.csv
├── sample_accounts.csv
├── sample_portfolio.csv
├── sample_dividends.csv
├── requirements.txt
└── README.md
```

The app can still run from any folder name as long as the CSV files are in the same folder as `app.py`.

---

## 2. Installation

```bash
pip install -r requirements.txt
```

---

## 3. Run Locally

```bash
streamlit run app.py
```

By default, the app reads these files from the same folder as `app.py`:

```text
accounts.csv
portfolio.csv
dividends.csv
```

Completely empty CSV rows are automatically ignored before validation, calculation, export, and local save. This prevents blank rows such as `,,,,` from being reported as ticker/date/amount errors.

---

## 4. CSV Files

### 4.1 `accounts.csv`

Account master file. Use aliases only. Do not store real account numbers.

```csv
account_id,owner,account_name,broker,account_type,tax_bucket,currency,is_active,note
ME_FID_ROTH,Me,Fidelity Roth IRA,Fidelity,Roth IRA,Retirement,USD,TRUE,my retirement account
SP_FID_IRA,Spouse,Fidelity IRA,Fidelity,Traditional IRA,Retirement,USD,TRUE,spouse retirement account
```

Required columns:

```text
account_id, owner, account_name
```

Recommended values:

- `owner`: `Me`, `Spouse`, or another household member alias
- `tax_bucket`: `Retirement`, `Taxable`, or `Unclassified`
- `is_active`: `TRUE` or `FALSE`

---

### 4.2 `portfolio.csv`

BUY / SELL transaction ledger.

```csv
transaction_date,transaction_type,ticker,shares,price,fee,account_id,note
2025-03-12,BUY,SCHD,20,77.35,0,ME_FID_ROTH,dividend core
2026-01-10,SELL,SCHD,5,82.00,0,ME_FID_ROTH,partial sell
```

Important rules:

- `transaction_type` must be `BUY` or `SELL`.
- `shares` must always be positive.
- Do not enter negative shares for a sale.
- Sales are FIFO-matched within the same `account_id + ticker`.
- A fully sold ticker becomes a `Closed` position for that specific account.

Legacy files with `purchase_date`, `buy_price`, or `account` can be migrated in session:

- `purchase_date` → `transaction_date`
- `buy_price` → `price`
- `account` → `account_id`
- missing `transaction_type` → `BUY`

---

### 4.3 `dividends.csv`

Actual dividend cash-flow ledger.

```csv
payment_date,ticker,net_amount,account_id,note
2026-01-15,SCHD,18.42,ME_FID_ROTH,Q1 dividend
2026-01-20,JEPI,7.85,SP_FID_IRA,monthly dividend
```

Use `net_amount` as the actual amount deposited into the account. Do not mix dividends into `portfolio.csv`; dividends are cash flows, not quantity-changing trades.

---

## 5. Dashboard Tabs

### Overview

- Household KPI summary
- Current holdings cost
- Current value
- Unrealized P/L
- Realized P/L
- Actual dividends YTD / All-Time
- Total return including dividends
- Estimated annual dividend
- Allocation by ETF and tax bucket
- Concentration warning
- Household ETF exposure

### Accounts

- Account summary table
- Owner-level market value
- Account-level market value
- Tax bucket allocation
- Estimated annual dividend by owner

### Holdings

- Active holdings by default
- Optional closed position view
- Cross-account ETF exposure
- Realized P/L and actual dividends by position
- Estimated dividend fields

### Realized P/L

- FIFO realized lot matches
- Realized P/L by ticker/account
- Closed position performance including actual dividends

### Dividend

- Actual monthly dividend chart
- Cumulative actual dividend chart
- Actual dividends by ETF/account
- Estimated monthly dividend calendar
- Upcoming estimated dividend table
- Estimated vs actual last 12 months

### Price Trend

- Selected ETF price chart
- 20D / 60D moving averages
- BUY / SELL markers
- Average open cost line
- Normalized comparison
- Drawdown chart

### Data Manager

- Data Quality check at the top
- Accounts Manager
- Portfolio Transactions Manager
- Dividend Payments Manager
- Add new account / transaction / dividend payment
- Download updated CSV files
- Save to local CSV files for local execution

---

## 6. Dividend Logic

Estimated dividends come from yfinance historical dividends and pattern-based frequency estimation.

Dividend status rules:

- Historical future dates are not treated as confirmed.
- Pattern-derived dates are labeled `Estimated`.
- Unknown dates remain `Unknown`.
- Closed positions are excluded from future dividend projection.
- Actual dividends are read only from `dividends.csv`.

Dividend-inclusive performance:

```text
Total Return incl. Dividends = Realized P/L + Unrealized P/L + Actual Dividends Received
```

---

## 7. Streamlit Cloud Deployment

1. Upload the project folder to GitHub.
2. Deploy `app.py` from Streamlit Community Cloud.
3. Keep CSV files in the repository if you want the app to load them by default.
4. Edits made inside Streamlit Cloud may not persist permanently on disk.
5. Use Data Manager download buttons, then replace the CSV files in GitHub.

---

## 8. Data Quality Rules

The app checks:

- Missing required columns
- Invalid dates
- Invalid numeric values
- Negative/zero shares
- BUY / SELL validation
- Overselling by account/ticker
- Duplicate rows
- Unknown `account_id` references
- Future transactions or dividend payment dates
- Empty rows are automatically dropped before validation

---

## 9. Data Source Limitations

- yfinance is used for current prices, historical prices, and historical dividend data.
- yfinance does not reliably provide confirmed future ETF dividend pay dates.
- Future dividend dates shown by the dashboard are estimates based on historical patterns.
- Actual dividend cash-flow numbers come only from `dividends.csv`.
- This dashboard does not calculate tax lots for tax filing and does not replace brokerage records.

---

## 10. Limitations

- This is not a tax-reporting system.
- IRA contribution limits are not tracked.
- Cash deposits/withdrawals are not tracked in version 1.0.
- IRR / TWR / MWR calculations are not included.
- Broker statement import is not included.
- yfinance data can be delayed, incomplete, or inaccurate.
- Currency support is assumed to be USD for this version.

---

## 11. Version 1.0 Release Notes

Version 1.0 is the first branded release of **Household Wealth Tracker**.

Included capabilities:

- Renamed the project from the prior ETF dashboard naming to Household Wealth Tracker.
- Multi-account household portfolio management.
- `accounts.csv` account master ledger.
- `portfolio.csv` BUY / SELL transaction ledger.
- `dividends.csv` actual dividend payment ledger.
- FIFO realized P/L by `account_id + ticker`.
- Active and Closed position handling.
- Actual dividends included in total return.
- Owner / Account / Tax Bucket filtering.
- Household ETF exposure and concentration warning.
- Account summary dashboard.
- Estimated dividend forecast from yfinance historical dividend patterns.
- Actual dividend charts from `dividends.csv`.
- Data Manager for editing all CSV ledgers.
- Data Quality check displayed at the top of Data Manager.
- Explicit chart labels, axis labels, legends, hover labels, and value labels.
- Full empty-row cleanup before validation/export.
- Streamlit Community Cloud compatibility.

---

## 12. Suggested Next Version

Potential version 1.1 scope:

- Cash contribution ledger
- Contribution target tracking
- Monthly investment plan tracking
- Account-level deposit/withdrawal history
- Money-weighted return approximation
- Broker statement CSV import templates
- Non-ETF assets such as cash, stocks, bonds, and retirement plan holdings
