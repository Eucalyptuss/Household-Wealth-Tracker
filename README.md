# Household Wealth Tracker

Version: v1.0.22

# Household Wealth Tracker

**Code Version:** 1.0.22

**Creator:** Eucalyptuss  
**Code Version:** 1.0.22

Household Wealth Tracker is a Streamlit-based household investment dashboard for managing household investment holdings across multiple owners, retirement accounts, and taxable brokerage accounts. It supports account master data, BUY/SELL transaction tracking, FIFO realized P/L, active and closed position handling, actual dividend cash-flow tracking, estimated dividend forecasting, and household-level exposure analysis.

> This project is not investment, tax, or financial advice. Online market and dividend data may be delayed, incomplete, or inaccurate. Always verify all data with your broker, official fund documents, and qualified professionals when needed.

---

## Version 1.0.22 Cash Events and SPAXX Interest Update

- Added `cash_events.csv` for account-level cash baselines, external contributions/withdrawals, adjustments, and SPAXX/MMF interest.
- Added `INITIAL_BALANCE` logic: BUY/SELL/dividend activity before the baseline date is excluded from cash calculations.
- Added calculated cash balance, total account value, cash weight, cash interest YTD/Last 12M, and estimated annual cash interest.
- Added `Household Cash Exposure` table in Overview.
- Allocation donut charts can include calculated cash slices such as `Cash / SPAXX`.
- Added Cash Events Manager in Data Manager.

## Version 1.0.21 Account Allocation Layout Update

- Updated the Overview account-level ticker allocation chart layout.
- Account ID-Level Allocation by Ticker now uses one row for up to four account donuts.
- When five or more Account ID donuts are present, the chart automatically switches to two rows and distributes the donuts across columns.
- Removed the previous fixed two-column limitation so the full-width Overview area is used more efficiently.

## 1. Project Structure

```text
household_wealth_tracker/
├── app.py
├── accounts.csv
├── portfolio.csv
├── dividends.csv
├── cash_events.csv
├── sample_accounts.csv
├── sample_portfolio.csv
├── sample_dividends.csv
├── sample_cash_events.csv
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
cash_events.csv
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

### 4.4 `cash_events.csv`

Account-level cash event ledger. This file is designed so users do not need to update cash after every BUY or SELL.

```csv
date,account_id,event_type,amount,cash_label,annual_yield,note
2026-10-07,ME_FID_ROTH,INITIAL_BALANCE,1000.00,SPAXX,0.0349,Starting SPAXX cash balance
2026-10-31,ME_FID_ROTH,INTEREST,2.91,SPAXX,0.0349,SPAXX monthly interest
```

Supported `event_type` values:

- `INITIAL_BALANCE`: confirmed current cash or SPAXX balance on the given date. Earlier BUY/SELL/dividend activity is excluded from cash calculation.
- `CONTRIBUTION`: external cash deposit.
- `WITHDRAWAL`: external cash withdrawal; enter a positive amount, the app subtracts it automatically.
- `INTEREST`: cash sweep/MMF interest such as SPAXX distributions.
- `ADJUSTMENT`: signed reconciliation adjustment.

`annual_yield` can be entered as either `0.0349` or `3.49` for 3.49%. The app normalizes values greater than 1 as percentages.

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
- Cash balance / total account value / cash weight
- Estimated annual cash interest and actual cash interest metrics
- Allocation by ETF, cash, and tax bucket
- Concentration warning
- Household ETF exposure
- Household cash exposure

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
- Cash deposits/withdrawals and SPAXX-style sweep interest are tracked through `cash_events.csv` starting in v1.0.22.
- IRR / TWR / MWR calculations are not included.
- Broker statement import is not included.
- yfinance data can be delayed, incomplete, or inaccurate.
- Currency support is assumed to be USD for this version.

---

## 11. Version 1.0 Release Notes
### Version: 1.0.9 Semantic Color Highlight Patch
- General table and chart text colors are no longer forced by the app.
- Only semantically meaningful values are highlighted: red for losses/sells/errors, green for gains/buys/active states, and blue for dividend-related values.
- Unhighlighted cells inherit Streamlit's active Light/Dark theme automatically.
- Sidebars, backgrounds, CSV schemas, and calculation logic are unchanged.

- Fixed table text contrast in Account Summary, Holdings, Cross-Account Holding Exposure, Actual Dividend Table, Upcoming Estimated Dividend Table, and Estimated vs Actual Last 12M.
- Fixed chart text contrast by using Streamlit theme-aware CSS variables for Plotly text.
- Updated actual dividend date-axis rendering to display date only.
- Updated the Price Trend average open cost horizontal line to follow light/dark text contrast.


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
- Household ETF exposure
- Household cash exposure and concentration warning.
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

---

## Version 1.0.14 Update

- Synchronized the Overview lower-row chart heights.
- `Top Gainers / Losers by Account ID` now calculates its chart height from the number of visible ticker/account rows.
- `Upcoming Estimated Dividends in Next 30 Days` receives the same calculated height so both charts remain visually aligned in the same row.
- No portfolio calculation, CSV schema, dividend logic, or account grouping logic was changed.

## Version 1.0.13 Update

- Account-level charts now use `account_id` / `Account ID` as the grouping key instead of `account_name`.
- Overview account allocation donut charts now separate holdings by account ID.
- Top Gainers / Losers now displays and colors bars by account ID.
- Account Summary market value chart now groups and colors by account ID.
- Dividend-by-account chart now groups by account ID.
- Holdings and closed-position tables now include Account ID before account name.

## Version 1.0.12 Update

- Added account-level donut charts below the main allocation charts.
- Improved Allocation by Ticker labels to show share quantities directly on the donut chart.
- Adjusted donut text orientation for better center alignment.
- Improved Top Gainers / Losers readability by displaying Ticker / Account and coloring bars by account.
- Added color differentiation to the Account Summary account-level market value chart.
- Added percentage values to Portfolio Summary KPI cards where a meaningful return/yield percentage can be calculated.


## Version 1.0.15 Top Gainers / Losers Full Account-ID View Patch

Version 1.0.15 focuses on the Overview chart row that contains `Top Gainers / Losers by Account ID` and `Upcoming Estimated Dividends in Next 30 Days`.

Changes:

- Fixed the issue where some `Ticker / Account ID` rows appeared to be missing from `Top Gainers / Losers by Account ID`.
- Replaced the previous `top 5 gainers + bottom 5 losers` selection with all active account-level positions.
- Added compact Account ID labels on the y-axis so long account IDs do not make the chart difficult to read.
- Preserved the full Account ID in the hover tooltip.
- Kept the shared height behavior so the adjacent upcoming dividend chart uses the same height as the gain/loss chart.
- No CSV schema, FIFO, dividend, account, or market-data calculation logic was changed.


## Version 1.0.16

- Added Cost Basis, Unrealized P/L, and Return % to the Household Holding Exposure table.
- Kept the exposure table grouped by Ticker and Account IDs while preserving the existing chart and CSV logic.


## Version 1.0.17

- Reduced the horizontal bar thickness in `Top Gainers / Losers by Account ID` to approximately half of the previous visual weight.
- Added responsive CSS for donut chart labels so text shrinks as the Plotly chart container becomes narrower.
- Set a readable donut label lower limit with `clamp(8px, 2.2cqw, 12px)` so labels do not become too small on compact screens.
- Lowered donut chart `uniformtext_minsize` to 8 for both household-level and account-level donut charts.
- No CSV schema, FIFO, dividend, account grouping, or market-data calculation logic was changed.

## Version 1.0.18

- Reduced the `Top Gainers / Losers by Account ID` chart canvas height to match the previously reduced horizontal bar thickness.
- Changed the dynamic height formula from a tall row allowance to a compact row allowance: minimum 360px, 24px per ticker/account row, and maximum 1000px.
- Kept the paired `Upcoming Estimated Dividends in Next 30 Days` chart synchronized to the same computed height.
- No CSV schema, FIFO, dividend, account grouping, or market-data calculation logic was changed.



## Version 1.0.19

- Improved `Top Gainers / Losers by Account ID` y-axis labels by using semantic account-ID abbreviation instead of simple truncation.
- Common broker/filler tokens such as `FID`, `FIDELITY`, `RH`, `ROBINHOOD`, `ACCOUNT`, and `BROKERAGE` are removed from the short label.
- Traditional IRA patterns such as `ME_FID_TRA_IRA` and `WIFE_FID_TRA_IRA` are now displayed as `ME_TIRA` and `WIFE_TIRA`.
- Full Account ID remains available in the chart hover tooltip.


## v1.0.20 Update

- Removed the Overview `Account ID-Level Allocation by Tax Bucket` chart.
- Expanded `Account ID-Level Allocation by Ticker` to the full Overview width.
- Added `Avg Buy Price` to the `Household Holding Exposure` table.
- Added optional sidebar auto-refresh for online data with a default 10-second interval.
- Set the `CSV Sources` sidebar expander to load collapsed by default.

## v1.0.23 Update

- Fixed `Household Cash Exposure` display formatting for `Cash Label` and `Initial Balance Date`.
- Root cause: the generic money-table formatter treated `Cash Label` as currency because it contains `cash`, and treated `Initial Balance Date` as currency because it contains `balance`.
- Date columns are now formatted before money columns, and text identifier columns such as label/name/id/type/status/note/owner/bucket are excluded from currency formatting.
- Cash calculation logic, `cash_events.csv` schema, BUY/SELL cash-impact logic, dividend cash-impact logic, and allocation charts were not changed.

## v1.0.24 Update

- Changed the sidebar `Auto refresh interval (seconds)` default from 10 seconds to 60 seconds.
- Updated the related help text to state that the default interval is 60 seconds.
- Auto refresh remains disabled on first load.
- No cash calculation, allocation chart, CSV schema, FIFO, dividend, or online-data refresh logic was changed.
