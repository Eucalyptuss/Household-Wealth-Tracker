from __future__ import annotations

import html
import io
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from zoneinfo import ZoneInfo

# ============================================================
# App configuration
# ============================================================

APP_TITLE = "Household Wealth Tracker"
CREATOR_NAME = "Eucalyptuss"
APP_VERSION = "1.0.11"
BASE_DIR = Path(__file__).resolve().parent
ET = ZoneInfo("America/New_York")
TODAY = datetime.now(ET).date()

ACCOUNTS_CSV_NAME = "accounts.csv"
PORTFOLIO_CSV_NAME = "portfolio.csv"
DIVIDENDS_CSV_NAME = "dividends.csv"
SAMPLE_ACCOUNTS_CSV_NAME = "sample_accounts.csv"
SAMPLE_PORTFOLIO_CSV_NAME = "sample_portfolio.csv"
SAMPLE_DIVIDENDS_CSV_NAME = "sample_dividends.csv"

ACCOUNT_REQUIRED_COLUMNS = ["account_id", "owner", "account_name"]
ACCOUNT_OPTIONAL_DEFAULTS = {
    "broker": "Unknown",
    "account_type": "Unknown",
    "tax_bucket": "Unclassified",
    "currency": "USD",
    "is_active": True,
    "note": "",
}
ACCOUNT_COLUMNS = ACCOUNT_REQUIRED_COLUMNS + list(ACCOUNT_OPTIONAL_DEFAULTS.keys())

TRANSACTION_TYPES = ["BUY", "SELL"]
TX_REQUIRED_COLUMNS = ["transaction_date", "transaction_type", "ticker", "shares", "price", "account_id"]
TX_OPTIONAL_DEFAULTS = {"fee": 0.0, "note": ""}
TX_COLUMNS = TX_REQUIRED_COLUMNS + ["fee", "note"]
LEGACY_TX_REQUIRED_COLUMNS = ["ticker", "purchase_date", "shares", "buy_price"]

DIV_REQUIRED_COLUMNS = ["payment_date", "ticker", "net_amount", "account_id"]
DIV_OPTIONAL_DEFAULTS = {"note": ""}
DIV_COLUMNS = DIV_REQUIRED_COLUMNS + ["note"]

PERIOD_MAP = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "YTD": "ytd",
    "1Y": "1y",
    "3Y": "3y",
    "MAX": "max",
}
BENCHMARK_OPTIONS = ["None", "SPY", "QQQ", "DIA", "VTI", "SCHD"]
DIVIDEND_MODES = ["Last 12M", "Recent Dividend × Frequency", "Scenario"]

SAMPLE_ACCOUNTS_CSV = """account_id,owner,account_name,broker,account_type,tax_bucket,currency,is_active,note
ME_FID_ROTH,Me,Fidelity Roth IRA,Fidelity,Roth IRA,Retirement,USD,TRUE,my retirement account
ME_RH_TAXABLE,Me,Robinhood Taxable,Robinhood,Taxable Brokerage,Taxable,USD,TRUE,my taxable brokerage
SP_FID_IRA,Spouse,Fidelity IRA,Fidelity,Traditional IRA,Retirement,USD,TRUE,spouse retirement account
SP_FID_TAXABLE,Spouse,Fidelity Taxable,Fidelity,Taxable Brokerage,Taxable,USD,TRUE,spouse taxable brokerage
"""

SAMPLE_PORTFOLIO_CSV = """transaction_date,transaction_type,ticker,shares,price,fee,account_id,note
2025-03-12,BUY,SCHD,20,77.35,0,ME_FID_ROTH,dividend core
2026-01-10,SELL,SCHD,5,82.00,0,ME_FID_ROTH,partial sell example
2025-04-10,BUY,JEPI,15,56.20,0,SP_FID_IRA,income
2025-05-02,BUY,VOO,5,474.10,0,ME_RH_TAXABLE,index core
2025-06-03,BUY,QQQ,3,455.00,0,SP_FID_TAXABLE,closed position example
2026-02-15,SELL,QQQ,3,475.00,0,SP_FID_TAXABLE,full sell example
"""

SAMPLE_DIVIDENDS_CSV = """payment_date,ticker,net_amount,account_id,note
2025-06-30,SCHD,12.34,ME_FID_ROTH,actual dividend example
2025-07-08,JEPI,6.82,SP_FID_IRA,monthly dividend example
2025-09-30,SCHD,11.98,ME_FID_ROTH,actual dividend example
2025-12-31,SCHD,13.10,ME_FID_ROTH,actual dividend example
2026-01-08,JEPI,7.05,SP_FID_IRA,monthly dividend example
2026-02-20,QQQ,1.92,SP_FID_TAXABLE,received before full sell
"""

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Styling
# ============================================================


def inject_css() -> None:
    st.markdown(
        """
        <style>
        /* Theme-aware custom UI. Avoid fixed black/white text. */
        :root {
            color-scheme: light dark;
            --hwt-primary: var(--primary-color, #2563eb);
            --hwt-text: var(--text-color, light-dark(#111827, #f9fafb));
            --hwt-bg: var(--background-color, light-dark(#ffffff, #0e1117));
            --hwt-soft-bg: var(--secondary-background-color, light-dark(#f8fafc, #1f2937));
            --hwt-muted: light-dark(#475569, #cbd5e1);
            --hwt-card-bg: light-dark(#ffffff, #111827);
            --hwt-border: light-dark(rgba(15, 23, 42, 0.16), rgba(226, 232, 240, 0.24));
            --hwt-positive: light-dark(#166534, #86efac);
            --hwt-negative: light-dark(#b91c1c, #fca5a5);
            --hwt-dividend: light-dark(#1d4ed8, #93c5fd);
            --hwt-estimated: light-dark(#92400e, #fcd34d);
            --hwt-warning-bg: light-dark(#fffbeb, #451a03);
            --hwt-dividend-bg: light-dark(#eff6ff, #172554);
        }
        html, body, .stApp, [data-testid="stAppViewContainer"], .main {
            color: var(--hwt-text) !important;
            background-color: var(--hwt-bg);
        }
        .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        .dashboard-title { color: var(--hwt-text) !important; font-size: 2.05rem; font-weight: 850; line-height: 1.15; letter-spacing: -0.02em; margin-bottom: 0.2rem; }
        .dashboard-subtitle { color: var(--hwt-muted) !important; font-size: 0.96rem; margin-bottom: 1rem; }
        .meta-box { color: var(--hwt-text) !important; border: 1px solid var(--hwt-border); border-radius: 16px; padding: 0.8rem 1rem; background: var(--hwt-soft-bg); margin-bottom: 1rem; font-size: 0.92rem; }
        .meta-box * { color: var(--hwt-text) !important; }
        .version-banner { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; border: 1px solid light-dark(rgba(29,78,216,0.28), rgba(147,197,253,0.30)); border-radius: 16px; padding: 0.75rem 1rem; background: linear-gradient(135deg, var(--hwt-dividend-bg), var(--hwt-soft-bg)); margin: 0.15rem 0 0.9rem 0; box-shadow: 0 6px 18px rgba(15,23,42,0.06); }
        .version-banner-title { font-weight: 850; color: var(--hwt-text) !important; letter-spacing: -0.01em; }
        .version-banner-meta { color: var(--hwt-muted) !important; font-size: 0.9rem; font-weight: 700; white-space: nowrap; }
        .kpi-card { color: var(--hwt-text) !important; border: 1px solid var(--hwt-border); border-radius: 18px; padding: 1rem 1rem; background: var(--hwt-card-bg); box-shadow: 0 8px 22px rgba(15,23,42,0.08); height: 150px; min-height: 150px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 0.25rem; }
        .kpi-card * { color: inherit; }
        .kpi-row-gap { height: 1.25rem; min-height: 1.25rem; }
        .kpi-label { color: var(--hwt-muted) !important; font-size: 0.80rem; font-weight: 850; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.45rem; line-height: 1.2; min-height: 1.95rem; }
        .kpi-value { color: var(--hwt-text) !important; font-size: 1.48rem; line-height: 1.15; font-weight: 850; white-space: nowrap; }
        .kpi-help { color: var(--hwt-muted) !important; font-size: 0.76rem; margin-top: 0.35rem; line-height: 1.2; min-height: 1.0rem; }
        .positive { color: var(--hwt-positive) !important; }
        .negative { color: var(--hwt-negative) !important; }
        .neutral { color: var(--hwt-text) !important; }
        .blue { color: var(--hwt-dividend) !important; }
        .amber { color: var(--hwt-estimated) !important; }
        .warning-box { color: var(--hwt-text) !important; border-left: 4px solid var(--hwt-estimated); background: var(--hwt-warning-bg); padding: 0.75rem 1rem; border-radius: 12px; margin: 0.6rem 0 1rem 0; }
        .warning-box * { color: var(--hwt-text) !important; }
        .small-note { color: var(--hwt-muted) !important; font-size: 0.86rem; }
        div[data-testid="stMetric"] { color: var(--hwt-text) !important; border: 1px solid var(--hwt-border); border-radius: 16px; padding: 0.75rem 0.9rem; background: var(--hwt-soft-bg); }
        div[data-testid="stMetric"] * { color: var(--hwt-text) !important; }
        div[data-testid="stMetricDelta"] svg { fill: currentColor !important; }
        div[data-testid="stMarkdownContainer"], div[data-testid="stCaptionContainer"], .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span, .stMarkdown div { color: var(--hwt-text) !important; }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 { color: var(--hwt-text) !important; }
        label, .stSelectbox label, .stMultiSelect label, .stSlider label, .stFileUploader label, .stRadio label, .stCheckbox label { color: var(--hwt-text) !important; }
        div[data-testid="stAlert"] * { color: var(--hwt-text) !important; }
        div[data-testid="stExpander"] * { color: var(--hwt-text); }
        [data-testid="stSidebar"] * { color: var(--hwt-text); }
        [data-testid="stSidebar"] .stCaptionContainer, [data-testid="stSidebar"] small { color: var(--hwt-muted) !important; }
        .hwt-muted-text { color: var(--hwt-muted) !important; }
        .hwt-table-note { color: var(--hwt-muted) !important; font-size: 0.86rem; }
        .hwt-table-wrap {
            width: 100%;
            overflow: auto;
            border: 1px solid var(--hwt-border);
            border-radius: 12px;
            background: var(--hwt-bg);
        }
        table.hwt-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            color: var(--hwt-text);
        }
        table.hwt-table th {
            position: sticky;
            top: 0;
            z-index: 2;
            background: var(--hwt-soft-bg);
            color: var(--hwt-text);
            font-weight: 850;
            text-align: left;
            white-space: nowrap;
            padding: 0.55rem 0.65rem;
            border-bottom: 1px solid var(--hwt-border);
        }
        table.hwt-table td {
            color: var(--hwt-text);
            padding: 0.50rem 0.65rem;
            border-bottom: 1px solid var(--hwt-border);
            white-space: nowrap;
            vertical-align: middle;
        }
        table.hwt-table tr:nth-child(even) td { background: color-mix(in srgb, var(--hwt-soft-bg) 55%, transparent); }
        table.hwt-table .hwt-pos { color: #16A34A !important; font-weight: 850; }
        table.hwt-table .hwt-neg { color: #DC2626 !important; font-weight: 850; }
        table.hwt-table .hwt-blue { color: #2563EB !important; font-weight: 850; }
        table.hwt-table .hwt-strong { font-weight: 850; }
        .kpi-value.positive { color: #16A34A !important; }
        .kpi-value.negative { color: #DC2626 !important; }
        .kpi-value.blue { color: #2563EB !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# Generic helpers
# ============================================================


def fmt_currency(value: Any, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"${float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


def fmt_number(value: Any, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return "N/A"


def fmt_pct(value: Any, decimals: int = 2, signed: bool = True) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        sign = "+" if signed and float(value) > 0 else ""
        return f"{sign}{float(value) * 100:.{decimals}f}%"
    except Exception:
        return "N/A"


def fmt_date(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Unknown"
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return "Unknown"


def now_et_str() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d %H:%M ET")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _is_blank_like(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "nat", "<na>"}


def drop_fully_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    if df.empty:
        return df.copy()
    out = df.copy()
    non_empty_mask = out.apply(lambda row: any(not _is_blank_like(v) for v in row), axis=1)
    return out.loc[non_empty_mask].reset_index(drop=True)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return drop_fully_empty_rows(df).to_csv(index=False).encode("utf-8-sig")


def clean_id(value: Any, default: str = "DEFAULT") -> str:
    text = str(value).strip().upper() if not _is_blank_like(value) else default
    text = "_".join(text.replace("/", " ").replace("-", " ").split())
    return text or default


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = drop_fully_empty_rows(df).copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    return out


def add_quality_issue(issues: List[Dict[str, Any]], severity: str, row: Any, column: str, raw_value: Any, issue: str) -> None:
    issues.append({
        "Severity": severity,
        "Row": row,
        "Column": column,
        "Raw Value": "" if raw_value is None else str(raw_value),
        "Issue": issue,
    })

# ============================================================
# File loading
# ============================================================


def find_csv(filename: str) -> Optional[Path]:
    candidates = [BASE_DIR / filename, Path.cwd() / filename]
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


def csv_signature(path: Path) -> str:
    try:
        stat = path.stat()
        return f"{path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}"
    except Exception:
        return "missing"


def read_csv_path(path: Path) -> pd.DataFrame:
    return drop_fully_empty_rows(pd.read_csv(path))


def embedded_sample_df(kind: str) -> pd.DataFrame:
    if kind == "accounts":
        return drop_fully_empty_rows(pd.read_csv(io.StringIO(SAMPLE_ACCOUNTS_CSV)))
    if kind == "portfolio":
        return drop_fully_empty_rows(pd.read_csv(io.StringIO(SAMPLE_PORTFOLIO_CSV)))
    if kind == "dividends":
        return drop_fully_empty_rows(pd.read_csv(io.StringIO(SAMPLE_DIVIDENDS_CSV)))
    raise ValueError(kind)


def load_default_csv(filename: str, sample_filename: str, kind: str) -> Tuple[pd.DataFrame, str, str, str]:
    path = find_csv(filename)
    if path is not None:
        try:
            return read_csv_path(path), f"{filename} ({path})", f"{kind}_file", csv_signature(path)
        except Exception as exc:
            st.warning(f"{filename} could not be read. Falling back to sample data. Error: {exc}")
    sample_path = find_csv(sample_filename)
    if sample_path is not None:
        try:
            return read_csv_path(sample_path), f"{sample_filename} ({sample_path})", f"sample_{kind}_file", csv_signature(sample_path)
        except Exception as exc:
            st.warning(f"{sample_filename} could not be read. Falling back to embedded sample data. Error: {exc}")
    return embedded_sample_df(kind), f"embedded {sample_filename}", f"embedded_sample_{kind}", f"embedded::{kind}"


def load_file_into_session(kind: str) -> None:
    if kind == "accounts":
        df, source, source_type, sig = load_default_csv(ACCOUNTS_CSV_NAME, SAMPLE_ACCOUNTS_CSV_NAME, "accounts")
        st.session_state.accounts_df = df
        st.session_state.accounts_source = source
        st.session_state.accounts_source_type = source_type
        st.session_state.accounts_signature = sig
    elif kind == "portfolio":
        df, source, source_type, sig = load_default_csv(PORTFOLIO_CSV_NAME, SAMPLE_PORTFOLIO_CSV_NAME, "portfolio")
        st.session_state.portfolio_df = df
        st.session_state.portfolio_source = source
        st.session_state.portfolio_source_type = source_type
        st.session_state.portfolio_signature = sig
    elif kind == "dividends":
        df, source, source_type, sig = load_default_csv(DIVIDENDS_CSV_NAME, SAMPLE_DIVIDENDS_CSV_NAME, "dividends")
        st.session_state.dividends_df = df
        st.session_state.dividends_source = source
        st.session_state.dividends_source_type = source_type
        st.session_state.dividends_signature = sig


def initialize_session_state() -> None:
    for kind in ["accounts", "portfolio", "dividends"]:
        key = f"{kind}_df" if kind != "dividends" else "dividends_df"
        if key not in st.session_state:
            load_file_into_session(kind)

# ============================================================
# Normalization and validation
# ============================================================


def normalize_accounts(df: pd.DataFrame) -> pd.DataFrame:
    out = standardize_columns(df)
    for col, default in ACCOUNT_OPTIONAL_DEFAULTS.items():
        if col not in out.columns:
            out[col] = default
    for col in ACCOUNT_REQUIRED_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    out = out[ACCOUNT_COLUMNS].copy()
    out["account_id"] = out["account_id"].map(clean_id)
    out["owner"] = out["owner"].astype("string").fillna("Unknown").str.strip().replace("", "Unknown")
    out["account_name"] = out["account_name"].astype("string").fillna("").str.strip()
    out["account_name"] = np.where(out["account_name"].astype(str).str.strip() == "", out["account_id"], out["account_name"])
    for col in ["broker", "account_type", "tax_bucket", "currency", "note"]:
        out[col] = out[col].astype("string").fillna(ACCOUNT_OPTIONAL_DEFAULTS.get(col, "")).str.strip()
    out["currency"] = out["currency"].replace("", "USD").str.upper()
    out["broker"] = out["broker"].replace("", "Unknown")
    out["account_type"] = out["account_type"].replace("", "Unknown")
    out["tax_bucket"] = out["tax_bucket"].replace("", "Unclassified")
    out["is_active"] = out["is_active"].astype(str).str.strip().str.upper().isin(["TRUE", "1", "YES", "Y", "ACTIVE"])
    return drop_fully_empty_rows(out)


def validate_accounts(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    issues: List[Dict[str, Any]] = []
    df = drop_fully_empty_rows(df)
    if df is None or df.empty:
        add_quality_issue(issues, "Error", "ACCOUNTS_ALL", "accounts.csv", "", "accounts.csv is empty.")
        empty = pd.DataFrame(columns=["row_id"] + ACCOUNT_COLUMNS)
        return empty, pd.DataFrame(issues), pd.Series(dtype=bool)
    original_cols = [str(c).strip().lower() for c in df.columns]
    for col in ACCOUNT_REQUIRED_COLUMNS:
        if col not in original_cols:
            add_quality_issue(issues, "Error", "ACCOUNTS_ALL", col, "Missing", f"accounts.csv: required column '{col}' is missing.")
    clean = normalize_accounts(df)
    clean.insert(0, "row_id", range(1, len(clean) + 1))
    valid_mask = pd.Series(True, index=clean.index)
    for idx, row in clean.iterrows():
        row_no = row["row_id"]
        if _is_blank_like(row["account_id"]):
            add_quality_issue(issues, "Error", row_no, "account_id", row["account_id"], "accounts.csv: account_id is missing.")
            valid_mask.loc[idx] = False
        if _is_blank_like(row["owner"]):
            add_quality_issue(issues, "Error", row_no, "owner", row["owner"], "accounts.csv: owner is missing.")
            valid_mask.loc[idx] = False
        if _is_blank_like(row["account_name"]):
            add_quality_issue(issues, "Warning", row_no, "account_name", row["account_name"], "accounts.csv: account_name is blank. account_id will be displayed.")
        if str(row["currency"]).upper() != "USD":
            add_quality_issue(issues, "Warning", row_no, "currency", row["currency"], "This version assumes USD-denominated security data.")
    duplicated = clean.duplicated(subset=["account_id"], keep=False)
    if duplicated.any():
        for _, row in clean.loc[duplicated].iterrows():
            add_quality_issue(issues, "Error", row["row_id"], "account_id", row["account_id"], "accounts.csv: duplicate account_id.")
            valid_mask.loc[row.name] = False
    if any(col not in original_cols for col in ACCOUNT_REQUIRED_COLUMNS):
        valid_mask[:] = False
    return clean, pd.DataFrame(issues), valid_mask


def account_lookup(accounts: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    if accounts is None or accounts.empty:
        return {}
    data = accounts.copy()
    data["account_id"] = data["account_id"].map(clean_id)
    return data.set_index("account_id").to_dict(orient="index")


def enrich_with_accounts(df: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()
    out = df.copy()
    meta_cols = ["account_id", "owner", "account_name", "broker", "account_type", "tax_bucket", "currency", "is_active"]
    meta = accounts[meta_cols].copy() if accounts is not None and not accounts.empty else pd.DataFrame(columns=meta_cols)
    if "account_id" not in out.columns:
        out["account_id"] = "DEFAULT"
    out["account_id"] = out["account_id"].map(clean_id)
    out = out.merge(meta, on="account_id", how="left")
    out["owner"] = out["owner"].fillna("Unmapped")
    out["account_name"] = out["account_name"].fillna(out["account_id"])
    out["broker"] = out["broker"].fillna("Unknown")
    out["account_type"] = out["account_type"].fillna("Unknown")
    out["tax_bucket"] = out["tax_bucket"].fillna("Unclassified")
    out["currency"] = out["currency"].fillna("USD")
    out["is_active"] = out["is_active"].fillna(True)
    return out


def migrate_transaction_schema(df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
    out = standardize_columns(df)
    migrated = False
    if "purchase_date" in out.columns and "transaction_date" not in out.columns:
        out = out.rename(columns={"purchase_date": "transaction_date"})
        migrated = True
    if "buy_price" in out.columns and "price" not in out.columns:
        out = out.rename(columns={"buy_price": "price"})
        migrated = True
    if "account" in out.columns and "account_id" not in out.columns:
        out["account_id"] = out["account"].map(clean_id)
        migrated = True
    if "transaction_type" not in out.columns and {"transaction_date", "ticker", "shares", "price"}.issubset(set(out.columns)):
        out["transaction_type"] = "BUY"
        migrated = True
    for col, default in TX_OPTIONAL_DEFAULTS.items():
        if col not in out.columns:
            out[col] = default
    for col in TX_REQUIRED_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    return out[TX_COLUMNS].copy(), migrated


def clean_and_validate_transactions(df: pd.DataFrame, known_account_ids: Iterable[str]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, bool]:
    issues: List[Dict[str, Any]] = []
    df = drop_fully_empty_rows(df)
    known_accounts = {clean_id(a) for a in known_account_ids if not _is_blank_like(a)}
    if df is None or df.empty:
        add_quality_issue(issues, "Error", "TRANSACTIONS_ALL", "portfolio.csv", "", "portfolio.csv is empty.")
        empty = pd.DataFrame(columns=["row_id"] + TX_COLUMNS)
        return empty, pd.DataFrame(issues), pd.Series(dtype=bool), False
    original_cols = [str(c).strip().lower() for c in df.columns]
    has_new = all(c in original_cols for c in TX_REQUIRED_COLUMNS)
    has_legacy = all(c in original_cols for c in LEGACY_TX_REQUIRED_COLUMNS)
    if not has_new and not has_legacy:
        for col in TX_REQUIRED_COLUMNS:
            if col not in original_cols:
                add_quality_issue(issues, "Error", "TRANSACTIONS_ALL", col, "Missing", f"portfolio.csv: required column '{col}' is missing.")
    clean, migrated = migrate_transaction_schema(df)
    clean.insert(0, "row_id", range(1, len(clean) + 1))
    if migrated:
        add_quality_issue(issues, "Info", "TRANSACTIONS_ALL", "schema", "legacy/account", "portfolio.csv was migrated to transaction/account_id schema in session.")
    clean["account_id"] = clean["account_id"].map(clean_id)
    clean["ticker"] = clean["ticker"].astype("string").fillna("").str.strip().str.upper()
    clean["transaction_type"] = clean["transaction_type"].astype("string").fillna("").str.strip().str.upper()
    clean["note"] = clean["note"].astype("string").fillna("")
    raw_dates = clean["transaction_date"].copy()
    clean["transaction_date"] = pd.to_datetime(clean["transaction_date"], errors="coerce").dt.date
    for col in ["shares", "price", "fee"]:
        clean[col] = pd.to_numeric(clean[col], errors="coerce")
    valid_mask = pd.Series(True, index=clean.index)
    for idx, row in clean.iterrows():
        row_no = row["row_id"]
        if _is_blank_like(row["account_id"]):
            add_quality_issue(issues, "Error", row_no, "account_id", row["account_id"], "portfolio.csv: account_id is missing.")
            valid_mask.loc[idx] = False
        elif known_accounts and row["account_id"] not in known_accounts:
            add_quality_issue(issues, "Error", row_no, "account_id", row["account_id"], "portfolio.csv: account_id is not registered in accounts.csv. Row is still displayed but should be fixed.")
        if row["ticker"] == "" or pd.isna(row["ticker"]):
            add_quality_issue(issues, "Error", row_no, "ticker", row["ticker"], "portfolio.csv: ticker is missing.")
            valid_mask.loc[idx] = False
        if row["transaction_type"] not in TRANSACTION_TYPES:
            add_quality_issue(issues, "Error", row_no, "transaction_type", row["transaction_type"], "transaction_type must be BUY or SELL.")
            valid_mask.loc[idx] = False
        if pd.isna(row["transaction_date"]):
            add_quality_issue(issues, "Error", row_no, "transaction_date", raw_dates.loc[idx], "transaction_date format is invalid. Expected YYYY-MM-DD.")
            valid_mask.loc[idx] = False
        elif row["transaction_date"] > TODAY:
            add_quality_issue(issues, "Warning", row_no, "transaction_date", row["transaction_date"], "Transaction date is in the future.")
        if pd.isna(row["shares"]):
            add_quality_issue(issues, "Error", row_no, "shares", row["shares"], "shares must be numeric.")
            valid_mask.loc[idx] = False
        elif row["shares"] <= 0:
            add_quality_issue(issues, "Error", row_no, "shares", row["shares"], "shares must be greater than 0. Use transaction_type=SELL for sales.")
            valid_mask.loc[idx] = False
        if pd.isna(row["price"]):
            add_quality_issue(issues, "Error", row_no, "price", row["price"], "price must be numeric.")
            valid_mask.loc[idx] = False
        elif row["price"] <= 0:
            add_quality_issue(issues, "Error", row_no, "price", row["price"], "price must be greater than 0.")
            valid_mask.loc[idx] = False
        if pd.isna(row["fee"]):
            clean.loc[idx, "fee"] = 0.0
        elif row["fee"] < 0:
            add_quality_issue(issues, "Warning", row_no, "fee", row["fee"], "fee is negative. Check if intentional.")
    duplicate_cols = ["transaction_date", "transaction_type", "ticker", "shares", "price", "fee", "account_id", "note"]
    duplicated = clean.duplicated(subset=duplicate_cols, keep=False)
    for _, row in clean.loc[duplicated].iterrows():
        add_quality_issue(issues, "Warning", row["row_id"], "duplicate row", row["ticker"], "Potential duplicate transaction row.")
    available: Dict[Tuple[str, str], float] = defaultdict(float)
    sorted_rows = clean.loc[valid_mask].sort_values(["account_id", "ticker", "transaction_date", "row_id"])
    for idx, row in sorted_rows.iterrows():
        key = (str(row["account_id"]), str(row["ticker"]))
        shares = safe_float(row["shares"])
        if row["transaction_type"] == "BUY":
            available[key] += shares
        elif row["transaction_type"] == "SELL":
            if shares > available[key] + 1e-9:
                add_quality_issue(issues, "Error", row["row_id"], "shares", row["shares"], f"SELL exceeds available shares for {key[1]} in account_id {key[0]}. Available before this row: {available[key]:,.6f}.")
                valid_mask.loc[idx] = False
            else:
                available[key] -= shares
    return clean, pd.DataFrame(issues), valid_mask, migrated


def migrate_dividend_schema(df: pd.DataFrame) -> Tuple[pd.DataFrame, bool]:
    out = standardize_columns(df)
    migrated = False
    if "account" in out.columns and "account_id" not in out.columns:
        out["account_id"] = out["account"].map(clean_id)
        migrated = True
    for col, default in DIV_OPTIONAL_DEFAULTS.items():
        if col not in out.columns:
            out[col] = default
    for col in DIV_REQUIRED_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    return out[DIV_COLUMNS].copy(), migrated


def clean_and_validate_dividends(df: pd.DataFrame, known_account_ids: Iterable[str], known_tickers: Iterable[str]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, bool]:
    issues: List[Dict[str, Any]] = []
    df = drop_fully_empty_rows(df)
    known_accounts = {clean_id(a) for a in known_account_ids if not _is_blank_like(a)}
    known_ticker_set = {str(t).upper() for t in known_tickers if not _is_blank_like(t)}
    if df is None or df.empty:
        empty = pd.DataFrame(columns=["row_id"] + DIV_COLUMNS)
        return empty, pd.DataFrame(issues), pd.Series(dtype=bool), False
    original_cols = [str(c).strip().lower() for c in df.columns]
    for col in DIV_REQUIRED_COLUMNS:
        if col not in original_cols and not (col == "account_id" and "account" in original_cols):
            add_quality_issue(issues, "Error", "DIVIDENDS_ALL", col, "Missing", f"dividends.csv: required column '{col}' is missing.")
    clean, migrated = migrate_dividend_schema(df)
    clean.insert(0, "row_id", range(1, len(clean) + 1))
    if migrated:
        add_quality_issue(issues, "Info", "DIVIDENDS_ALL", "schema", "legacy/account", "dividends.csv account column was migrated to account_id in session.")
    clean["account_id"] = clean["account_id"].map(clean_id)
    clean["ticker"] = clean["ticker"].astype("string").fillna("").str.strip().str.upper()
    clean["note"] = clean["note"].astype("string").fillna("")
    raw_dates = clean["payment_date"].copy()
    clean["payment_date"] = pd.to_datetime(clean["payment_date"], errors="coerce").dt.date
    clean["net_amount"] = pd.to_numeric(clean["net_amount"], errors="coerce")
    valid_mask = pd.Series(True, index=clean.index)
    for idx, row in clean.iterrows():
        row_no = row["row_id"]
        if _is_blank_like(row["account_id"]):
            add_quality_issue(issues, "Error", row_no, "dividend.account_id", row["account_id"], "dividends.csv: account_id is missing.")
            valid_mask.loc[idx] = False
        elif known_accounts and row["account_id"] not in known_accounts:
            add_quality_issue(issues, "Error", row_no, "dividend.account_id", row["account_id"], "dividends.csv: account_id is not registered in accounts.csv.")
        if row["ticker"] == "" or pd.isna(row["ticker"]):
            add_quality_issue(issues, "Error", row_no, "dividend.ticker", row["ticker"], "dividends.csv: ticker is missing.")
            valid_mask.loc[idx] = False
        elif known_ticker_set and row["ticker"] not in known_ticker_set:
            add_quality_issue(issues, "Warning", row_no, "dividend.ticker", row["ticker"], "dividends.csv: ticker does not exist in current transaction ledger.")
        if pd.isna(row["payment_date"]):
            add_quality_issue(issues, "Error", row_no, "dividend.payment_date", raw_dates.loc[idx], "payment_date format is invalid. Expected YYYY-MM-DD.")
            valid_mask.loc[idx] = False
        elif row["payment_date"] > TODAY:
            add_quality_issue(issues, "Warning", row_no, "dividend.payment_date", row["payment_date"], "payment_date is in the future.")
        if pd.isna(row["net_amount"]):
            add_quality_issue(issues, "Error", row_no, "dividend.net_amount", row["net_amount"], "net_amount must be numeric.")
            valid_mask.loc[idx] = False
        elif row["net_amount"] < 0:
            add_quality_issue(issues, "Warning", row_no, "dividend.net_amount", row["net_amount"], "net_amount is negative. Check if reversal/correction.")
        elif row["net_amount"] == 0:
            add_quality_issue(issues, "Warning", row_no, "dividend.net_amount", row["net_amount"], "net_amount is zero. Verify intentional.")
    duplicate_cols = ["payment_date", "ticker", "net_amount", "account_id", "note"]
    duplicated = clean.duplicated(subset=duplicate_cols, keep=False)
    for _, row in clean.loc[duplicated].iterrows():
        add_quality_issue(issues, "Warning", row["row_id"], "dividend.duplicate row", row["ticker"], "Potential duplicate dividend payment row.")
    return clean, pd.DataFrame(issues), valid_mask, migrated

# ============================================================
# Online market data
# ============================================================


@dataclass
class PriceResult:
    ticker: str
    price: Optional[float]
    currency: str
    as_of: str
    error: Optional[str] = None


@st.cache_data(ttl=15 * 60, show_spinner=False)
def fetch_current_price(ticker: str) -> Dict[str, Any]:
    result = PriceResult(ticker=ticker, price=None, currency="USD", as_of=now_et_str(), error=None)
    try:
        ticker_obj = yf.Ticker(ticker)
        try:
            fast_info = ticker_obj.fast_info
            for key in ["last_price", "regular_market_price", "previous_close", "lastPrice"]:
                value = None
                try:
                    value = fast_info.get(key) if hasattr(fast_info, "get") else getattr(fast_info, key, None)
                except Exception:
                    value = None
                if value is not None and not pd.isna(value) and float(value) > 0:
                    result.price = float(value)
                    break
            try:
                currency = fast_info.get("currency") if hasattr(fast_info, "get") else getattr(fast_info, "currency", None)
                if currency:
                    result.currency = str(currency)
            except Exception:
                pass
        except Exception:
            pass
        if result.price is None:
            hist = ticker_obj.history(period="5d", auto_adjust=False)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                close = hist["Close"].dropna()
                if not close.empty and float(close.iloc[-1]) > 0:
                    result.price = float(close.iloc[-1])
        if result.price is None:
            result.error = "No current price returned by yfinance."
    except Exception as exc:
        result.error = f"Current price lookup failed: {exc}"
    return result.__dict__


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_price_history(ticker: str, period: str) -> Dict[str, Any]:
    try:
        yf_period = PERIOD_MAP.get(period, "1y")
        hist = yf.Ticker(ticker).history(period=yf_period, auto_adjust=False)
        if hist is None or hist.empty:
            return {"ticker": ticker, "history": pd.DataFrame(), "error": "No historical price data returned."}
        hist = hist.reset_index()
        date_col = "Date" if "Date" in hist.columns else hist.columns[0]
        hist = hist.rename(columns={date_col: "Date"})
        hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce").dt.tz_localize(None)
        keep = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits"] if c in hist.columns]
        hist = hist[keep].dropna(subset=["Date"])
        return {"ticker": ticker, "history": hist, "error": None}
    except Exception as exc:
        return {"ticker": ticker, "history": pd.DataFrame(), "error": f"Historical price lookup failed: {exc}"}


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def fetch_dividend_history(ticker: str) -> Dict[str, Any]:
    try:
        div = yf.Ticker(ticker).dividends
        if div is None or len(div) == 0:
            return {"ticker": ticker, "dividends": pd.DataFrame(columns=["Date", "Dividend"]), "error": None, "info": "No dividend history."}
        div_df = div.reset_index()
        div_df.columns = ["Date", "Dividend"]
        div_df["Date"] = pd.to_datetime(div_df["Date"], errors="coerce").dt.tz_localize(None)
        div_df["Dividend"] = pd.to_numeric(div_df["Dividend"], errors="coerce")
        div_df = div_df.dropna(subset=["Date", "Dividend"])
        return {"ticker": ticker, "dividends": div_df, "error": None, "info": None}
    except Exception as exc:
        return {"ticker": ticker, "dividends": pd.DataFrame(columns=["Date", "Dividend"]), "error": f"Dividend lookup failed: {exc}", "info": None}


def fetch_all_online_data(tickers: List[str], period: str, benchmark: str) -> Tuple[Dict[str, Dict[str, Any]], pd.DataFrame]:
    online: Dict[str, Dict[str, Any]] = {}
    quality: List[Dict[str, Any]] = []
    tickers_to_fetch = sorted({t for t in tickers if str(t).strip()})
    if benchmark and benchmark != "None":
        tickers_to_fetch = sorted(set(tickers_to_fetch + [benchmark]))
    for ticker in tickers_to_fetch:
        price = fetch_current_price(ticker)
        history = fetch_price_history(ticker, period)
        dividends = fetch_dividend_history(ticker)
        online[ticker] = {"price": price, "history": history, "dividends": dividends}
        if price.get("error"):
            add_quality_issue(quality, "Warning", "ONLINE", ticker, ticker, price["error"])
        if history.get("error"):
            add_quality_issue(quality, "Warning", "ONLINE", ticker, ticker, history["error"])
        if dividends.get("error"):
            add_quality_issue(quality, "Warning", "ONLINE", ticker, ticker, dividends["error"])
        elif dividends.get("info"):
            add_quality_issue(quality, "Info", "ONLINE", ticker, ticker, dividends["info"])
    return online, pd.DataFrame(quality)

# ============================================================
# Dividend forecast analysis
# ============================================================


def infer_dividend_frequency(div_df: pd.DataFrame) -> Dict[str, Any]:
    if div_df is None or div_df.empty or len(div_df) < 2:
        return {"frequency": "Unknown", "frequency_count": 0, "avg_interval_days": np.nan, "confidence_note": "Insufficient dividend history to infer frequency."}
    dates = pd.to_datetime(div_df["Date"]).sort_values().dropna()
    intervals = dates.diff().dt.days.dropna()
    if intervals.empty:
        return {"frequency": "Unknown", "frequency_count": 0, "avg_interval_days": np.nan, "confidence_note": "Insufficient dividend intervals."}
    avg_interval = float(intervals.tail(8).mean())
    if 20 <= avg_interval <= 40:
        frequency, count = "Monthly", 12
    elif 70 <= avg_interval <= 110:
        frequency, count = "Quarterly", 4
    elif 150 <= avg_interval <= 220:
        frequency, count = "Semi-Annual", 2
    elif avg_interval >= 300:
        frequency, count = "Annual", 1
    else:
        frequency, count = "Unknown", 0
    return {"frequency": frequency, "frequency_count": count, "avg_interval_days": avg_interval, "confidence_note": f"Estimated from average historical dividend interval of {avg_interval:.0f} days."}


def analyze_dividend_history(div_df: pd.DataFrame) -> Dict[str, Any]:
    if div_df is None or div_df.empty:
        return {
            "last_12m_dividend_per_share": 0.0,
            "recent_dividend_per_share": 0.0,
            "frequency": "Unknown",
            "frequency_count": 0,
            "next_estimated_ex_date": None,
            "next_estimated_pay_date": None,
            "dividend_status": "No Dividend History",
            "confidence_note": "No historical dividend data found from yfinance.",
        }
    div = div_df.copy()
    div["Date"] = pd.to_datetime(div["Date"], errors="coerce")
    div["Dividend"] = pd.to_numeric(div["Dividend"], errors="coerce")
    div = div.dropna(subset=["Date", "Dividend"]).sort_values("Date")
    if div.empty:
        return analyze_dividend_history(pd.DataFrame())
    cutoff = pd.Timestamp(TODAY - timedelta(days=365))
    last_12m = float(div.loc[div["Date"] >= cutoff, "Dividend"].sum())
    recent = float(div["Dividend"].iloc[-1])
    freq = infer_dividend_frequency(div)
    last_date = div["Date"].iloc[-1]
    next_ex = None
    status = "Unknown"
    note = freq["confidence_note"]
    if freq["frequency_count"] > 0 and not pd.isna(freq["avg_interval_days"]):
        next_ex = last_date + pd.Timedelta(days=int(round(freq["avg_interval_days"])))
        while next_ex.date() <= TODAY:
            next_ex = next_ex + pd.Timedelta(days=int(round(freq["avg_interval_days"])))
        status = "Estimated"
        note += " Next ex-date is estimated from historical interval."
    else:
        note += " Next dividend date is unknown."
    return {
        "last_12m_dividend_per_share": last_12m,
        "recent_dividend_per_share": recent,
        "frequency": freq["frequency"],
        "frequency_count": freq["frequency_count"],
        "avg_interval_days": freq["avg_interval_days"],
        "next_estimated_ex_date": next_ex.date() if next_ex is not None else None,
        "next_estimated_pay_date": None,
        "dividend_status": status,
        "confidence_note": note,
    }


def annual_dividend_per_share(analysis: Dict[str, Any], mode: str) -> float:
    if mode == "Recent Dividend × Frequency":
        return safe_float(analysis.get("recent_dividend_per_share")) * safe_float(analysis.get("frequency_count"))
    return safe_float(analysis.get("last_12m_dividend_per_share"))

# ============================================================
# FIFO portfolio calculation
# ============================================================


def fifo_calculate(transactions: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return transaction detail, realized lot matches, and open lots using FIFO by account_id+ticker."""
    if transactions is None or transactions.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    tx = transactions.copy().sort_values(["account_id", "ticker", "transaction_date", "row_id"]).reset_index(drop=True)
    lots: Dict[Tuple[str, str], Deque[Dict[str, Any]]] = defaultdict(deque)
    details: List[Dict[str, Any]] = []
    realized: List[Dict[str, Any]] = []
    for _, row in tx.iterrows():
        account_id = str(row["account_id"])
        ticker = str(row["ticker"])
        key = (account_id, ticker)
        shares = safe_float(row["shares"])
        price = safe_float(row["price"])
        fee = safe_float(row["fee"])
        gross = shares * price
        if row["transaction_type"] == "BUY":
            cost_basis = gross + fee
            unit_cost = cost_basis / shares if shares else 0.0
            lot = {
                "account_id": account_id,
                "ticker": ticker,
                "buy_row_id": row["row_id"],
                "buy_date": row["transaction_date"],
                "remaining_shares": shares,
                "original_shares": shares,
                "unit_cost": unit_cost,
                "remaining_cost_basis": cost_basis,
                "note": row.get("note", ""),
            }
            lots[key].append(lot)
            details.append({
                "Row": row["row_id"], "Date": row["transaction_date"], "Type": "BUY", "Account ID": account_id, "Ticker": ticker,
                "Shares": shares, "Price": price, "Fee": fee, "Gross Amount": gross, "Net Cash Flow": -cost_basis,
                "Matched Cost Basis": 0.0, "Realized P/L": 0.0, "Realized Return %": np.nan, "Note": row.get("note", ""),
            })
        elif row["transaction_type"] == "SELL":
            remaining_to_sell = shares
            sell_net_total = gross - fee
            matched_cost_total = 0.0
            realized_total = 0.0
            while remaining_to_sell > 1e-9 and lots[key]:
                lot = lots[key][0]
                matched_shares = min(remaining_to_sell, lot["remaining_shares"])
                matched_cost = matched_shares * lot["unit_cost"]
                sell_fee_alloc = fee * (matched_shares / shares) if shares else 0.0
                net_proceeds = matched_shares * price - sell_fee_alloc
                pl = net_proceeds - matched_cost
                realized.append({
                    "Account ID": account_id, "Ticker": ticker, "Sell Row": row["row_id"], "Buy Row": lot["buy_row_id"],
                    "Buy Date": lot["buy_date"], "Sell Date": row["transaction_date"], "Shares Sold": matched_shares,
                    "Buy Unit Cost": lot["unit_cost"], "Sell Price": price, "Cost Basis Sold": matched_cost,
                    "Net Proceeds": net_proceeds, "Realized P/L": pl,
                    "Realized Return %": pl / matched_cost if matched_cost else np.nan,
                    "Sell Note": row.get("note", ""),
                })
                matched_cost_total += matched_cost
                realized_total += pl
                lot["remaining_shares"] -= matched_shares
                lot["remaining_cost_basis"] -= matched_cost
                remaining_to_sell -= matched_shares
                if lot["remaining_shares"] <= 1e-9:
                    lots[key].popleft()
            details.append({
                "Row": row["row_id"], "Date": row["transaction_date"], "Type": "SELL", "Account ID": account_id, "Ticker": ticker,
                "Shares": shares, "Price": price, "Fee": fee, "Gross Amount": gross, "Net Cash Flow": sell_net_total,
                "Matched Cost Basis": matched_cost_total, "Realized P/L": realized_total,
                "Realized Return %": realized_total / matched_cost_total if matched_cost_total else np.nan, "Note": row.get("note", ""),
            })
    open_lots: List[Dict[str, Any]] = []
    for (account_id, ticker), queue in lots.items():
        for lot in queue:
            if lot["remaining_shares"] > 1e-9:
                open_lots.append({
                    "Account ID": account_id, "Ticker": ticker, "Buy Row": lot["buy_row_id"], "Buy Date": lot["buy_date"],
                    "Remaining Shares": lot["remaining_shares"], "Unit Cost": lot["unit_cost"], "Remaining Cost Basis": lot["remaining_cost_basis"], "Note": lot.get("note", ""),
                })
    return pd.DataFrame(details), pd.DataFrame(realized), pd.DataFrame(open_lots)


def actual_dividend_metrics(dividends: pd.DataFrame) -> Dict[str, float]:
    if dividends is None or dividends.empty:
        return {"all_time": 0.0, "ytd": 0.0, "last_12m": 0.0, "recent_3m": 0.0, "monthly_average_all_time": 0.0, "monthly_average_last_12m": 0.0}
    div = dividends.copy()
    div["payment_date"] = pd.to_datetime(div["payment_date"], errors="coerce")
    div["net_amount"] = pd.to_numeric(div["net_amount"], errors="coerce").fillna(0.0)
    div = div.dropna(subset=["payment_date"])
    if div.empty:
        return actual_dividend_metrics(pd.DataFrame())
    today_ts = pd.Timestamp(TODAY)
    ytd_start = pd.Timestamp(date(TODAY.year, 1, 1))
    all_time = safe_float(div["net_amount"].sum())
    ytd = safe_float(div.loc[div["payment_date"] >= ytd_start, "net_amount"].sum())
    last_12m = safe_float(div.loc[div["payment_date"] >= today_ts - pd.Timedelta(days=365), "net_amount"].sum())
    recent_3m = safe_float(div.loc[div["payment_date"] >= today_ts - pd.Timedelta(days=92), "net_amount"].sum())
    month_count = max(1, div["payment_date"].dt.to_period("M").nunique())
    return {"all_time": all_time, "ytd": ytd, "last_12m": last_12m, "recent_3m": recent_3m, "monthly_average_all_time": all_time / month_count, "monthly_average_last_12m": last_12m / 12.0}


def build_portfolio_tables(
    transactions: pd.DataFrame,
    dividends: pd.DataFrame,
    accounts: pd.DataFrame,
    online_data: Dict[str, Dict[str, Any]],
    dividend_mode: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Dict[str, Any]], Dict[str, float]]:
    tx_detail, realized_df, open_lots = fifo_calculate(transactions)
    tx_enriched = enrich_with_accounts(transactions, accounts)
    realized_enriched = enrich_with_accounts(realized_df.rename(columns={"Account ID": "account_id"}), accounts) if not realized_df.empty else realized_df.copy()
    if not realized_enriched.empty:
        realized_enriched = realized_enriched.rename(columns={"account_id": "Account ID"})
    dividend_analysis: Dict[str, Dict[str, Any]] = {}
    for ticker in sorted(tx_enriched["ticker"].dropna().astype(str).unique().tolist()) if not tx_enriched.empty else []:
        div_df = online_data.get(ticker, {}).get("dividends", {}).get("dividends", pd.DataFrame())
        dividend_analysis[ticker] = analyze_dividend_history(div_df)
    active_pairs = set()
    if open_lots is not None and not open_lots.empty:
        active_pairs = set(zip(open_lots["Account ID"].astype(str), open_lots["Ticker"].astype(str)))
    all_pairs = set(zip(tx_enriched["account_id"].astype(str), tx_enriched["ticker"].astype(str))) if not tx_enriched.empty else set()
    records: List[Dict[str, Any]] = []
    realized_pair = realized_df.groupby(["Account ID", "Ticker"], as_index=False)["Realized P/L"].sum() if not realized_df.empty else pd.DataFrame(columns=["Account ID", "Ticker", "Realized P/L"])
    div_pair = pd.DataFrame(columns=["account_id", "ticker", "Actual_Dividends"])
    if dividends is not None and not dividends.empty:
        div_tmp = dividends.copy()
        div_tmp["net_amount"] = pd.to_numeric(div_tmp["net_amount"], errors="coerce").fillna(0.0)
        div_pair = div_tmp.groupby(["account_id", "ticker"], as_index=False)["net_amount"].sum().rename(columns={"net_amount": "Actual_Dividends"})
    for account_id, ticker in sorted(all_pairs):
        pair_lots = open_lots[(open_lots["Account ID"].astype(str) == account_id) & (open_lots["Ticker"].astype(str) == ticker)] if open_lots is not None and not open_lots.empty else pd.DataFrame()
        shares = safe_float(pair_lots["Remaining Shares"].sum()) if not pair_lots.empty else 0.0
        cost_basis = safe_float(pair_lots["Remaining Cost Basis"].sum()) if not pair_lots.empty else 0.0
        avg_buy = cost_basis / shares if shares else np.nan
        price = online_data.get(ticker, {}).get("price", {}).get("price")
        current_price = safe_float(price, np.nan)
        market_value = shares * current_price if not pd.isna(current_price) else 0.0
        unrealized = market_value - cost_basis if shares else 0.0
        realized_val = safe_float(realized_pair.loc[(realized_pair["Account ID"].astype(str) == account_id) & (realized_pair["Ticker"].astype(str) == ticker), "Realized P/L"].sum()) if not realized_pair.empty else 0.0
        actual_div = safe_float(div_pair.loc[(div_pair["account_id"].astype(str) == account_id) & (div_pair["ticker"].astype(str) == ticker), "Actual_Dividends"].sum()) if not div_pair.empty else 0.0
        analysis = dividend_analysis.get(ticker, {})
        per_share = annual_dividend_per_share(analysis, dividend_mode)
        est_annual = per_share * shares
        current_yield = per_share / current_price if current_price and not pd.isna(current_price) else np.nan
        yield_on_cost = est_annual / cost_basis if cost_basis else np.nan
        records.append({
            "Account ID": account_id,
            "Ticker": ticker,
            "Shares": shares,
            "Avg Buy Price": avg_buy,
            "Current Price": current_price,
            "Cost Basis": cost_basis,
            "Market Value": market_value,
            "Unrealized P/L": unrealized,
            "Return %": unrealized / cost_basis if cost_basis else np.nan,
            "Realized P/L": realized_val,
            "Actual Dividends": actual_div,
            "Total Return incl. Dividends": realized_val + unrealized + actual_div,
            "Last 12M Dividend / Share": safe_float(analysis.get("last_12m_dividend_per_share")),
            "Estimated Annual Dividend": est_annual,
            "Yield on Cost": yield_on_cost,
            "Current Yield": current_yield,
            "Dividend Frequency": analysis.get("frequency", "Unknown") if shares else "Excluded - Closed",
            "Next Estimated Ex-Date": analysis.get("next_estimated_ex_date") if shares else None,
            "Next Estimated Pay Date": analysis.get("next_estimated_pay_date") if shares else None,
            "Dividend Status": analysis.get("dividend_status", "Unknown") if shares else "Excluded - Closed",
            "Confidence Note": analysis.get("confidence_note", "") if shares else "Closed position is excluded from future dividend projection.",
            "Holding Status": "Active" if shares > 1e-9 else "Closed",
        })
    holdings = pd.DataFrame(records)
    if not holdings.empty:
        holdings = enrich_with_accounts(holdings.rename(columns={"Account ID": "account_id"}), accounts).rename(columns={"account_id": "Account ID"})
        active_mv = holdings.loc[holdings["Holding Status"] == "Active", "Market Value"].sum()
        holdings["Portfolio Weight %"] = np.where((holdings["Holding Status"] == "Active") & (active_mv > 0), holdings["Market Value"] / active_mv, 0.0)
        sort_cols = ["Holding Status", "Market Value"]
        holdings = holdings.sort_values(sort_cols, ascending=[True, False]).reset_index(drop=True)
    sold_cost_basis = safe_float(realized_df["Cost Basis Sold"].sum()) if not realized_df.empty and "Cost Basis Sold" in realized_df.columns else 0.0
    current_open_cost = safe_float(holdings.loc[holdings["Holding Status"] == "Active", "Cost Basis"].sum()) if not holdings.empty else 0.0
    tracked_cost = current_open_cost + sold_cost_basis
    metrics = actual_dividend_metrics(dividends)
    summary = {
        "current_holdings_cost": current_open_cost,
        "current_value": safe_float(holdings.loc[holdings["Holding Status"] == "Active", "Market Value"].sum()) if not holdings.empty else 0.0,
        "unrealized_pl": safe_float(holdings.loc[holdings["Holding Status"] == "Active", "Unrealized P/L"].sum()) if not holdings.empty else 0.0,
        "realized_pl": safe_float(realized_df["Realized P/L"].sum()) if not realized_df.empty and "Realized P/L" in realized_df.columns else 0.0,
        "actual_dividends_all_time": metrics["all_time"],
        "actual_dividends_ytd": metrics["ytd"],
        "actual_dividends_last_12m": metrics["last_12m"],
        "estimated_annual_dividend": safe_float(holdings.loc[holdings["Holding Status"] == "Active", "Estimated Annual Dividend"].sum()) if not holdings.empty else 0.0,
        "tracked_cost_basis": tracked_cost,
    }
    summary["total_pl"] = summary["realized_pl"] + summary["unrealized_pl"]
    summary["total_return_pct"] = summary["total_pl"] / tracked_cost if tracked_cost else np.nan
    summary["dividend_inclusive_pl"] = summary["total_pl"] + summary["actual_dividends_all_time"]
    summary["dividend_adjusted_return_pct"] = summary["dividend_inclusive_pl"] / tracked_cost if tracked_cost else np.nan
    return tx_detail, realized_enriched, holdings, dividend_analysis, summary

# ============================================================
# Filtering and summary tables
# ============================================================


def filter_frame_by_controls(df: pd.DataFrame, controls: Dict[str, Any]) -> pd.DataFrame:
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()
    out = enrich_with_accounts(df, controls["accounts_clean"])
    if controls.get("owners"):
        out = out[out["owner"].astype(str).isin(controls["owners"])]
    if controls.get("tax_buckets"):
        out = out[out["tax_bucket"].astype(str).isin(controls["tax_buckets"])]
    if controls.get("account_types"):
        out = out[out["account_type"].astype(str).isin(controls["account_types"])]
    if controls.get("account_ids"):
        out = out[out["account_id"].astype(str).isin(controls["account_ids"])]
    if controls.get("tickers") and "ticker" in out.columns:
        out = out[out["ticker"].astype(str).isin(controls["tickers"])]
    cols_to_drop = [c for c in ["owner", "account_name", "broker", "account_type", "tax_bucket", "currency", "is_active"] if c in out.columns]
    return out.drop(columns=cols_to_drop, errors="ignore")


def filtered_dividends(dividends: pd.DataFrame, controls: Dict[str, Any]) -> pd.DataFrame:
    if dividends is None or dividends.empty:
        return pd.DataFrame(columns=DIV_COLUMNS)
    return filter_frame_by_controls(dividends, controls)


def account_summary_table(holdings: pd.DataFrame, accounts: pd.DataFrame, dividends: pd.DataFrame) -> pd.DataFrame:
    if accounts is None or accounts.empty:
        return pd.DataFrame()
    base = accounts[["account_id", "owner", "account_name", "broker", "account_type", "tax_bucket", "is_active"]].copy()
    if holdings is not None and not holdings.empty:
        h = holdings.groupby("Account ID", as_index=False).agg({
            "Cost Basis": "sum", "Market Value": "sum", "Unrealized P/L": "sum", "Realized P/L": "sum",
            "Actual Dividends": "sum", "Total Return incl. Dividends": "sum", "Estimated Annual Dividend": "sum",
        }).rename(columns={"Account ID": "account_id"})
        base = base.merge(h, on="account_id", how="left")
    for col in ["Cost Basis", "Market Value", "Unrealized P/L", "Realized P/L", "Actual Dividends", "Total Return incl. Dividends", "Estimated Annual Dividend"]:
        if col not in base.columns:
            base[col] = 0.0
        base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0.0)
    base["Return incl. Dividends %"] = np.where(base["Cost Basis"] > 0, base["Total Return incl. Dividends"] / base["Cost Basis"], np.nan)
    return base.sort_values("Market Value", ascending=False)


def group_summary(holdings: pd.DataFrame, group_col: str) -> pd.DataFrame:
    if holdings is None or holdings.empty or group_col not in holdings.columns:
        return pd.DataFrame()
    df = holdings.groupby(group_col, as_index=False).agg({
        "Cost Basis": "sum", "Market Value": "sum", "Unrealized P/L": "sum", "Realized P/L": "sum",
        "Actual Dividends": "sum", "Total Return incl. Dividends": "sum", "Estimated Annual Dividend": "sum",
    })
    df["Return incl. Dividends %"] = np.where(df["Cost Basis"] > 0, df["Total Return incl. Dividends"] / df["Cost Basis"], np.nan)
    return df.sort_values("Market Value", ascending=False)


def exposure_by_ticker(holdings: pd.DataFrame) -> pd.DataFrame:
    if holdings is None or holdings.empty:
        return pd.DataFrame()
    active = holdings[holdings["Holding Status"] == "Active"].copy()
    if active.empty:
        return pd.DataFrame()
    exp = active.groupby("Ticker", as_index=False).agg({"Shares": "sum", "Market Value": "sum", "Estimated Annual Dividend": "sum"})
    accounts = active.groupby("Ticker")["account_name"].apply(lambda x: ", ".join(sorted(set(map(str, x))))).reset_index(name="Accounts")
    exp = exp.merge(accounts, on="Ticker", how="left")
    total_mv = exp["Market Value"].sum()
    exp["Household Weight %"] = np.where(total_mv > 0, exp["Market Value"] / total_mv, 0.0)
    return exp.sort_values("Market Value", ascending=False)

# ============================================================
# Charts
# ============================================================



def active_theme_base() -> str:
    """Return the active display theme for non-CSS renderers.

    Plotly SVG and Pandas Styler need concrete colors. Streamlit's active UI
    theme is not always exposed to Python in every deployment mode, so the app
    uses Auto detection first and provides a sidebar override for chart/table
    contrast when needed.
    """
    override = str(st.session_state.get("display_theme_mode", "Auto")).lower()
    if override in {"dark", "light"}:
        return override
    try:
        # Streamlit config theme. Works when theme.base is explicitly set.
        base = st.get_option("theme.base")
        if str(base).lower() in {"dark", "light"}:
            return str(base).lower()
    except Exception:
        pass
    try:
        # Defensive support for newer Streamlit context objects, if available.
        ctx = getattr(st, "context", None)
        theme = getattr(ctx, "theme", None) if ctx is not None else None
        if isinstance(theme, dict):
            base = theme.get("base") or theme.get("type")
            if str(base).lower() in {"dark", "light"}:
                return str(base).lower()
        elif theme is not None:
            base = getattr(theme, "base", None) or getattr(theme, "type", None)
            if str(base).lower() in {"dark", "light"}:
                return str(base).lower()
    except Exception:
        pass
    return "light"


def hwt_palette() -> Dict[str, str]:
    """Theme-aware CSS colors for custom HTML and optional table highlighting.

    Do not use Python-side dark/light detection for table/chart text. Streamlit's
    active browser theme is the source of truth. CSS variables are resolved by the
    browser after the user switches Light/Dark mode, so the same app run can adapt
    without stale bright/dark text being carried over from session state.
    """
    return {
        "text": "var(--text-color, #111827)",
        "muted": "var(--hwt-muted, var(--text-color, #475569))",
        "background": "var(--background-color, #ffffff)",
        "secondary_background": "var(--secondary-background-color, #f8fafc)",
        "table_header_bg": "var(--secondary-background-color, #f8fafc)",
        "table_row_bg": "transparent",
        "table_alt_bg": "var(--secondary-background-color, rgba(148, 163, 184, 0.08))",
        "border": "var(--hwt-border, rgba(128, 128, 128, 0.24))",
        "grid": "rgba(128, 128, 128, 0.24)",
        "positive": "var(--hwt-positive, #166534)",
        "negative": "var(--hwt-negative, #b91c1c)",
        "dividend": "var(--hwt-dividend, #1d4ed8)",
        "estimated": "var(--hwt-estimated, #92400e)",
        "info": "var(--hwt-muted, var(--text-color, #475569))",
    }

CHART_LABELS = {
    "ticker": "Ticker",
    "Ticker": "Ticker",
    "account_id": "Account ID",
    "Account ID": "Account ID",
    "account_name": "Account",
    "Account": "Account",
    "owner": "Owner",
    "tax_bucket": "Tax Bucket",
    "account_type": "Account Type",
    "Market Value": "Market Value ($)",
    "Cost Basis": "Cost Basis ($)",
    "Unrealized P/L": "Unrealized P/L ($)",
    "Realized P/L": "Realized P/L ($)",
    "Total Return incl. Dividends": "Total Return incl. Dividends ($)",
    "Estimated Annual Dividend": "Estimated Annual Dividend ($)",
    "Actual Dividends": "Actual Dividends ($)",
    "Estimated Dividend Amount": "Estimated Dividend Amount ($)",
    "Return %": "Return (%)",
    "Dividend Yield": "Dividend Yield (%)",
    "Month": "Month",
    "payment_date": "Payment Date",
    "Estimated Ex-Date": "Estimated Ex-Date",
    "Date": "Date",
    "Close": "Close Price ($)",
    "Normalized": "Normalized Performance (Start = 100)",
    "Drawdown": "Drawdown (%)",
}


def chart_label(name: str) -> str:
    if name is None:
        return ""
    return CHART_LABELS.get(str(name), str(name).replace("_", " ").replace("/", " / ").title())


def is_money_measure(label_or_name: str) -> bool:
    text = chart_label(label_or_name)
    return any(token in text for token in ["$", "P/L", "Dividend", "Value", "Cost", "Price", "Proceeds", "Amount", "Basis"])


def is_percent_measure(label_or_name: str) -> bool:
    text = chart_label(label_or_name)
    return "%" in text or "Yield" in text or "Return (%)" in text or "Drawdown" in text


def label_template_for_measure(label_or_name: str, value_is_fraction: bool = False) -> str:
    if is_money_measure(label_or_name):
        return "$%{text:,.2f}"
    if is_percent_measure(label_or_name):
        return "%{text:.1%}" if value_is_fraction else "%{text:,.1f}%"
    return "%{text:,.2f}"


def add_numeric_axis_padding(fig: go.Figure, values: Iterable[Any], axis: str = "y", zero_floor: bool = True) -> None:
    numeric = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    if numeric.empty:
        return
    vmin = float(numeric.min())
    vmax = float(numeric.max())
    if math.isclose(vmin, vmax):
        pad = max(abs(vmax) * 0.18, 1.0)
    else:
        pad = max((vmax - vmin) * 0.18, abs(vmax) * 0.06, abs(vmin) * 0.06, 1e-9)
    lower = 0.0 if zero_floor and vmin >= 0 else vmin - pad
    upper = vmax + pad
    if axis == "x":
        fig.update_xaxes(range=[lower, upper])
    else:
        fig.update_yaxes(range=[lower, upper])


def apply_chart_theme(
    fig: go.Figure,
    *,
    height: int = 410,
    xaxis_title: str = "",
    yaxis_title: str = "",
    legend_title: str = "",
    top: int = 76,
    bottom: int = 76,
    left: int = 84,
    right: int = 54,
) -> go.Figure:
    """Apply layout spacing without forcing general chart text colors.

    Streamlit already applies its active Light/Dark theme to Plotly charts. Do not
    override all chart text with hard-coded or session-derived colors. Only chart
    geometry, margins, transparent backgrounds, grid lines, and axis labels are
    managed here. Red/green/blue emphasis is applied only in chart/table content
    where the value itself needs semantic highlighting.
    """
    theme_grid = "rgba(128, 128, 128, 0.24)"
    fig.update_layout(
        height=height,
        margin=dict(l=left, r=right, t=top, b=bottom),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        legend_title_text=legend_title,
        hovermode="closest",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(
        automargin=True,
        title_standoff=18,
        gridcolor=theme_grid,
        zerolinecolor=theme_grid,
        linecolor=theme_grid,
    )
    fig.update_yaxes(
        automargin=True,
        title_standoff=18,
        gridcolor=theme_grid,
        zerolinecolor=theme_grid,
        linecolor=theme_grid,
    )
    return fig

def apply_bar_label_safety(fig: go.Figure, values: Iterable[Any], *, orientation: str = "v", zero_floor: bool = True) -> go.Figure:
    """Keep bar labels inside the visible plotting area by adding axis headroom.

    Plotly labels placed outside bars can be clipped or can overlap axes when the range is
    too tight. This helper expands the numeric axis and disables clipping for label text.
    """
    axis = "x" if orientation == "h" else "y"
    add_numeric_axis_padding(fig, values, axis=axis, zero_floor=zero_floor)
    fig.update_traces(cliponaxis=False, constraintext="none")
    return fig


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[{"text": "No data available", "showarrow": False, "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5}],
    )
    return apply_chart_theme(fig, height=360, top=64, bottom=64, left=72, right=42)


def labeled_empty_figure(title: str, xaxis_title: str = "", yaxis_title: str = "") -> go.Figure:
    fig = empty_figure(title)
    return apply_chart_theme(fig, height=360, xaxis_title=xaxis_title, yaxis_title=yaxis_title, top=64, bottom=64, left=78, right=42)


def make_allocation_chart(holdings: pd.DataFrame, field: str = "Ticker", title: str = "Allocation") -> go.Figure:
    if holdings is None or holdings.empty or field not in holdings.columns:
        return labeled_empty_figure(title, chart_label(field), "Market Value ($)")
    active = holdings[holdings["Holding Status"] == "Active"].copy()
    if active.empty:
        return labeled_empty_figure(title, chart_label(field), "Market Value ($)")
    data = active.groupby(field, as_index=False)["Market Value"].sum().sort_values("Market Value", ascending=False)
    fig = px.pie(
        data,
        names=field,
        values="Market Value",
        hole=0.44,
        title=title,
        labels={field: chart_label(field), "Market Value": "Market Value ($)"},
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        insidetextorientation="radial",
        hovertemplate=f"{chart_label(field)}: %{{label}}<br>Market Value: $%{{value:,.2f}}<br>Weight: %{{percent}}<extra></extra>",
    )
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show")
    return apply_chart_theme(fig, height=420, legend_title=chart_label(field), top=76, bottom=54, left=42, right=78)


def make_bar_chart(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    if df is None or df.empty or x not in df.columns or y not in df.columns:
        return labeled_empty_figure(title, chart_label(x), chart_label(y))
    data = df.copy()
    fig = px.bar(
        data,
        x=x,
        y=y,
        title=title,
        labels={x: chart_label(x), y: chart_label(y)},
        text=y,
    )
    fig.update_traces(
        texttemplate=label_template_for_measure(y),
        textposition="outside",
        hovertemplate=f"{chart_label(x)}: %{{x}}<br>{chart_label(y)}: %{{y:,.2f}}<extra></extra>",
    )
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show")
    fig = apply_bar_label_safety(fig, data[y], orientation="v", zero_floor=True)
    return apply_chart_theme(fig, height=430, xaxis_title=chart_label(x), yaxis_title=chart_label(y), top=84, bottom=88, left=92, right=60)


def make_top_movers_chart(holdings: pd.DataFrame) -> go.Figure:
    if holdings is None or holdings.empty:
        return labeled_empty_figure("Top Gainers / Losers", "Return (%)", "Ticker")
    active = holdings[holdings["Holding Status"] == "Active"].copy()
    if active.empty:
        return labeled_empty_figure("Top Gainers / Losers", "Return (%)", "Ticker")
    top = pd.concat([active.nlargest(5, "Return %"), active.nsmallest(5, "Return %")]).drop_duplicates()
    top = top.sort_values("Return %")
    fig = px.bar(
        top,
        x="Return %",
        y="Ticker",
        orientation="h",
        hover_data={"account_name": True, "Market Value": ":$,.2f", "Unrealized P/L": ":$,.2f", "Return %": ":.2%"},
        text="Return %",
        title="Top Gainers / Losers",
        labels={"Return %": "Return (%)", "Ticker": "Ticker", "account_name": "Account", "Market Value": "Market Value ($)", "Unrealized P/L": "Unrealized P/L ($)"},
    )
    fig.update_traces(texttemplate="%{text:.1%}", textposition="outside", cliponaxis=False)
    fig = apply_bar_label_safety(fig, top["Return %"], orientation="h", zero_floor=False)
    fig.update_xaxes(tickformat=".1%", zeroline=True)
    return apply_chart_theme(fig, height=430, xaxis_title="Return (%)", yaxis_title="Ticker", top=84, bottom=76, left=86, right=76)


def make_realized_chart(realized_df: pd.DataFrame, group: str = "Ticker") -> go.Figure:
    if realized_df is None or realized_df.empty or "Realized P/L" not in realized_df.columns:
        return labeled_empty_figure("Realized P/L", chart_label(group), "Realized P/L ($)")
    if group not in realized_df.columns:
        group = "Ticker"
    data = realized_df.groupby(group, as_index=False)["Realized P/L"].sum().sort_values("Realized P/L", ascending=False)
    return make_bar_chart(data, group, "Realized P/L", f"Realized P/L by {chart_label(group)}")


def make_monthly_actual_dividend_chart(dividends: pd.DataFrame) -> go.Figure:
    if dividends is None or dividends.empty:
        return labeled_empty_figure("Monthly Actual Dividend Received", "Month", "Actual Dividends ($)")
    data = dividends.copy()
    data["payment_date"] = pd.to_datetime(data["payment_date"], errors="coerce")
    data["net_amount"] = pd.to_numeric(data["net_amount"], errors="coerce").fillna(0.0)
    data = data.dropna(subset=["payment_date"])
    if data.empty:
        return labeled_empty_figure("Monthly Actual Dividend Received", "Month", "Actual Dividends ($)")
    data["Month"] = data["payment_date"].dt.to_period("M").astype(str)
    monthly = data.groupby("Month", as_index=False)["net_amount"].sum().rename(columns={"net_amount": "Actual Dividends"})
    fig = px.bar(monthly, x="Month", y="Actual Dividends", text="Actual Dividends", title="Monthly Actual Dividend Received", labels={"Month": "Month", "Actual Dividends": "Actual Dividends ($)"})
    fig.update_traces(texttemplate="$%{text:,.2f}", textposition="outside", hovertemplate="Month: %{x}<br>Actual Dividends: $%{y:,.2f}<extra></extra>")
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show")
    fig = apply_bar_label_safety(fig, monthly["Actual Dividends"], orientation="v", zero_floor=True)
    return apply_chart_theme(fig, height=430, xaxis_title="Month", yaxis_title="Actual Dividends ($)", top=84, bottom=88, left=92, right=60)


def make_cumulative_dividend_chart(dividends: pd.DataFrame) -> go.Figure:
    if dividends is None or dividends.empty:
        return labeled_empty_figure("Cumulative Actual Dividend", "Payment Date", "Cumulative Dividend ($)")
    data = dividends.copy()
    data["payment_date"] = pd.to_datetime(data["payment_date"], errors="coerce")
    data["net_amount"] = pd.to_numeric(data["net_amount"], errors="coerce").fillna(0.0)
    data = data.dropna(subset=["payment_date"]).sort_values("payment_date")
    if data.empty:
        return labeled_empty_figure("Cumulative Actual Dividend", "Payment Date", "Cumulative Dividend ($)")
    data["Cumulative Dividend"] = data["net_amount"].cumsum()
    fig = px.line(data, x="payment_date", y="Cumulative Dividend", markers=True, title="Cumulative Actual Dividend", labels={"payment_date": "Payment Date", "Cumulative Dividend": "Cumulative Dividend ($)"})
    fig.update_traces(hovertemplate="Payment Date: %{x|%Y-%m-%d}<br>Cumulative Dividend: $%{y:,.2f}<extra></extra>")
    fig.update_xaxes(tickformat="%Y-%m-%d")
    return apply_chart_theme(fig, height=410, xaxis_title="Payment Date", yaxis_title="Cumulative Dividend ($)", top=76, bottom=82, left=92, right=54)


def build_upcoming_dividends(holdings: pd.DataFrame, dividend_analysis: Dict[str, Dict[str, Any]], days: int = 90) -> pd.DataFrame:
    rows = []
    if holdings is None or holdings.empty:
        return pd.DataFrame()
    active = holdings[holdings["Holding Status"] == "Active"].copy()
    for _, row in active.iterrows():
        ticker = row["Ticker"]
        analysis = dividend_analysis.get(ticker, {})
        ex = analysis.get("next_estimated_ex_date")
        status = analysis.get("dividend_status", "Unknown")
        if ex is None or status not in {"Estimated", "Confirmed"}:
            continue
        ex_date = pd.to_datetime(ex).date()
        if TODAY <= ex_date <= TODAY + timedelta(days=days):
            recent_div = safe_float(analysis.get("recent_dividend_per_share"))
            rows.append({
                "Ticker": ticker,
                "Account ID": row["Account ID"],
                "Account": row.get("account_name", row["Account ID"]),
                "Estimated Ex-Date": ex_date,
                "Estimated Pay Date": "Unknown",
                "Estimated Dividend / Share": recent_div,
                "Shares": row["Shares"],
                "Estimated Dividend Amount": recent_div * row["Shares"],
                "Status": status,
                "Confidence Note": analysis.get("confidence_note", ""),
            })
    return pd.DataFrame(rows).sort_values("Estimated Ex-Date") if rows else pd.DataFrame()


def make_upcoming_dividend_chart(upcoming: pd.DataFrame, days: int = 30) -> go.Figure:
    title = f"Upcoming Estimated Dividends in Next {days} Days"
    if upcoming is None or upcoming.empty:
        return labeled_empty_figure(title, "Estimated Ex-Date", "Estimated Dividend Amount ($)")
    data = upcoming.copy()
    data["Estimated Ex-Date"] = pd.to_datetime(data["Estimated Ex-Date"], errors="coerce")
    cutoff = pd.Timestamp(TODAY + timedelta(days=days))
    data = data[(data["Estimated Ex-Date"] >= pd.Timestamp(TODAY)) & (data["Estimated Ex-Date"] <= cutoff)]
    if data.empty:
        return labeled_empty_figure(title, "Estimated Ex-Date", "Estimated Dividend Amount ($)")
    grouped = data.groupby("Estimated Ex-Date", as_index=False)["Estimated Dividend Amount"].sum()
    fig = px.bar(grouped, x="Estimated Ex-Date", y="Estimated Dividend Amount", text="Estimated Dividend Amount", title=title, labels={"Estimated Ex-Date": "Estimated Ex-Date", "Estimated Dividend Amount": "Estimated Dividend Amount ($)"})
    fig.update_traces(texttemplate="$%{text:,.2f}", textposition="outside", hovertemplate="Estimated Ex-Date: %{x|%Y-%m-%d}<br>Estimated Dividend Amount: $%{y:,.2f}<extra></extra>")
    fig.update_xaxes(tickformat="%Y-%m-%d")
    fig.update_layout(uniformtext_minsize=10, uniformtext_mode="show")
    fig = apply_bar_label_safety(fig, grouped["Estimated Dividend Amount"], orientation="v", zero_floor=True)
    return apply_chart_theme(fig, height=410, xaxis_title="Estimated Ex-Date", yaxis_title="Estimated Dividend Amount ($)", top=84, bottom=88, left=92, right=60)


def make_monthly_estimated_dividend_calendar(upcoming: pd.DataFrame) -> go.Figure:
    if upcoming is None or upcoming.empty:
        return labeled_empty_figure("Monthly Estimated Dividend Calendar", "Month", "Estimated Dividend Amount ($)")
    data = upcoming.copy()
    data["Estimated Ex-Date"] = pd.to_datetime(data["Estimated Ex-Date"], errors="coerce")
    data = data.dropna(subset=["Estimated Ex-Date"])
    if data.empty:
        return labeled_empty_figure("Monthly Estimated Dividend Calendar", "Month", "Estimated Dividend Amount ($)")
    data["Month"] = data["Estimated Ex-Date"].dt.to_period("M").astype(str)
    monthly = data.groupby("Month", as_index=False)["Estimated Dividend Amount"].sum()
    return make_bar_chart(monthly, "Month", "Estimated Dividend Amount", "Monthly Estimated Dividend Calendar")


def make_price_chart(ticker: str, online_data: Dict[str, Dict[str, Any]], transactions: pd.DataFrame, holdings: pd.DataFrame) -> go.Figure:
    hist = online_data.get(ticker, {}).get("history", {}).get("history", pd.DataFrame())
    if hist is None or hist.empty or "Close" not in hist.columns:
        return labeled_empty_figure(f"{ticker} Price Trend", "Date", "Price ($)")
    data = hist.copy()
    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA60"] = data["Close"].rolling(60).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], mode="lines", name="Close Price", hovertemplate="Date: %{x|%Y-%m-%d}<br>Close Price: $%{y:,.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA20"], mode="lines", name="20D Moving Average", hovertemplate="Date: %{x|%Y-%m-%d}<br>20D MA: $%{y:,.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA60"], mode="lines", name="60D Moving Average", hovertemplate="Date: %{x|%Y-%m-%d}<br>60D MA: $%{y:,.2f}<extra></extra>"))
    tx = transactions[transactions["ticker"] == ticker].copy() if transactions is not None and not transactions.empty else pd.DataFrame()
    for ttype, symbol, name in [("BUY", "triangle-up", "Buy"), ("SELL", "triangle-down", "Sell")]:
        subset = tx[tx["transaction_type"] == ttype]
        if not subset.empty:
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(subset["transaction_date"]),
                y=subset["price"],
                mode="markers",
                name=f"{name} Transaction",
                marker=dict(symbol=symbol, size=12, line=dict(width=1)),
                hovertemplate=f"{name} Date: %{{x|%Y-%m-%d}}<br>{name} Price: $%{{y:,.2f}}<extra></extra>",
            ))
    h = holdings[(holdings["Ticker"] == ticker) & (holdings["Holding Status"] == "Active")] if holdings is not None and not holdings.empty else pd.DataFrame()
    if not h.empty and safe_float(h["Shares"].sum()) > 0:
        avg = safe_float(h["Cost Basis"].sum()) / safe_float(h["Shares"].sum())
        fig.add_hline(
            y=avg,
            line_dash="dash",
            annotation_text="Avg Open Cost",
            annotation_position="top left",
        )
    fig.update_layout(title=f"{ticker} Price Trend with BUY/SELL Markers")
    return apply_chart_theme(fig, height=540, xaxis_title="Date", yaxis_title="Price ($)", legend_title="Price / Transaction", top=86, bottom=82, left=92, right=72)


def make_normalized_chart(tickers: List[str], online_data: Dict[str, Dict[str, Any]], benchmark: str) -> go.Figure:
    fig = go.Figure()
    used = False
    for ticker in sorted(set(tickers + ([benchmark] if benchmark and benchmark != "None" else []))):
        hist = online_data.get(ticker, {}).get("history", {}).get("history", pd.DataFrame())
        if hist is None or hist.empty or "Close" not in hist.columns:
            continue
        close = hist[["Date", "Close"]].dropna().copy()
        if close.empty or close["Close"].iloc[0] == 0:
            continue
        close["Normalized"] = close["Close"] / close["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(x=close["Date"], y=close["Normalized"], mode="lines", name=ticker, hovertemplate="Date: %{x|%Y-%m-%d}<br>Normalized Performance: %{y:,.2f}<extra></extra>"))
        used = True
    if not used:
        return labeled_empty_figure("Normalized Performance Comparison", "Date", "Normalized Performance (Start = 100)")
    fig.update_layout(title="Normalized Performance Comparison")
    return apply_chart_theme(fig, height=450, xaxis_title="Date", yaxis_title="Normalized Performance (Start = 100)", legend_title="Ticker / Benchmark", top=82, bottom=82, left=96, right=64)


def make_drawdown_chart(tickers: List[str], online_data: Dict[str, Dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    used = False
    for ticker in sorted(set(tickers)):
        hist = online_data.get(ticker, {}).get("history", {}).get("history", pd.DataFrame())
        if hist is None or hist.empty or "Close" not in hist.columns:
            continue
        data = hist[["Date", "Close"]].dropna().copy()
        data["Drawdown"] = data["Close"] / data["Close"].cummax() - 1
        fig.add_trace(go.Scatter(x=data["Date"], y=data["Drawdown"], mode="lines", name=ticker, hovertemplate="Date: %{x|%Y-%m-%d}<br>Drawdown: %{y:.2%}<extra></extra>"))
        used = True
    if not used:
        return labeled_empty_figure("Drawdown Chart", "Date", "Drawdown (%)")
    fig.update_layout(title="Drawdown Chart")
    fig.update_yaxes(tickformat=".1%", zeroline=True)
    return apply_chart_theme(fig, height=450, xaxis_title="Date", yaxis_title="Drawdown (%)", legend_title="Ticker", top=82, bottom=82, left=92, right=64)

# ============================================================
# Render helpers
# ============================================================


def render_kpi_card(label: str, value: str, help_text: str = "", color_class: str = "neutral") -> None:
    st.markdown(f"""
        <div class='kpi-card'>
            <div><div class='kpi-label'>{label}</div><div class='kpi-value {color_class}'>{value}</div></div>
            <div class='kpi-help'>{help_text}</div>
        </div>
        """, unsafe_allow_html=True)


def render_version_banner() -> None:
    st.markdown(f"""
        <div class="version-banner">
            <div class="version-banner-title">Prepared by: {CREATOR_NAME}</div>
            <div class="version-banner-meta">Code Version: {APP_VERSION}</div>
        </div>
        """, unsafe_allow_html=True)


def render_header(last_refresh: str) -> None:
    st.markdown(f"<div class='dashboard-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-subtitle'>Household-level wealth tracker for investment holdings, BUY/SELL FIFO, actual dividends, and multi-account views.</div>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="meta-box">
            <b>Portfolio Source:</b> {st.session_state.get('portfolio_source', 'unknown')} &nbsp; | &nbsp;
            <b>Dividend Source:</b> {st.session_state.get('dividends_source', 'unknown')} &nbsp; | &nbsp;
            <b>Accounts Source:</b> {st.session_state.get('accounts_source', 'unknown')}<br>
            <b>Last Online Refresh:</b> {last_refresh} &nbsp; | &nbsp;
            <b>Price Source:</b> yfinance &nbsp; | &nbsp;
            <b>Dividend Forecast:</b> yfinance historical dividends + estimated pattern &nbsp; | &nbsp;
            <b>Code Version:</b> {APP_VERSION}
        </div>
    """, unsafe_allow_html=True)


def _semantic_class(value: Any, column_name: str) -> str:
    """Return a semantic CSS class only when the cell should be highlighted.

    Base table text is left to Streamlit/CSS theme variables. Only values with
    clear financial or status meaning get red/green/blue classes.
    """
    low = str(column_name).lower()
    try:
        if value is None or pd.isna(value):
            return ""
    except Exception:
        pass

    if isinstance(value, str):
        text = value.strip().lower()
        if low == "severity":
            if text == "error":
                return "hwt-neg"
            if text == "info":
                return "hwt-blue"
            return ""
        if low in {"transaction_type", "type"}:
            if text == "buy":
                return "hwt-pos"
            if text == "sell":
                return "hwt-neg"
            return ""
        if "status" in low:
            if text in {"active", "confirmed"}:
                return "hwt-pos"
            if text in {"closed", "error"}:
                return "hwt-neg"
            if "dividend" in text:
                return "hwt-blue"
            return ""

    if any(k in low for k in ["p/l", "return", "drawdown", "difference"]):
        try:
            numeric = float(value)
            if numeric > 0:
                return "hwt-pos"
            if numeric < 0:
                return "hwt-neg"
        except Exception:
            return ""
        return ""

    if (
        "dividend" in low
        or "yield" in low
        or low in {"net_amount", "actual dividends", "estimated annual dividend"}
        or "estimated dividend" in low
    ):
        try:
            numeric = float(value)
            if numeric != 0:
                return "hwt-blue"
        except Exception:
            if not _is_blank_like(value):
                return "hwt-blue"
        return ""

    return ""


def _display_value(value: Any, formatter: Optional[Any] = None, column_name: str = "") -> str:
    if formatter is not None:
        try:
            return str(formatter(value))
        except Exception:
            pass
    low = str(column_name).lower()
    if "date" in low:
        return fmt_date(value)
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float):
        return fmt_number(value, 4) if abs(value) < 1 and value != 0 else fmt_number(value, 2)
    return str(value)


def render_semantic_table(df: pd.DataFrame, formatters: Optional[Dict[str, Any]] = None, height: int = 430) -> None:
    """Render a theme-aware HTML table with semantic-only color highlights.

    Streamlit's canvas dataframe renderer can ignore Pandas Styler text color in
    some versions. This renderer uses normal HTML so red/green/blue highlights
    are applied reliably, while all unhighlighted text inherits the active
    Streamlit light/dark theme.
    """
    if df is None or df.empty:
        st.info("No data available.")
        return

    formatters = formatters or {}
    columns = list(df.columns)
    max_height = max(int(height), 180)
    parts = [f"<div class='hwt-table-wrap' style='max-height:{max_height}px;'>", "<table class='hwt-table'>", "<thead><tr>"]
    for col in columns:
        parts.append(f"<th>{html.escape(str(col))}</th>")
    parts.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        parts.append("<tr>")
        for col in columns:
            raw = row[col]
            cls = _semantic_class(raw, col)
            if str(col).lower() in {"ticker", "account id", "account_id", "account", "account name", "account_name", "owner", "tax_bucket"}:
                cls = (cls + " hwt-strong").strip()
            display = _display_value(raw, formatters.get(col), col)
            class_attr = f" class='{cls}'" if cls else ""
            parts.append(f"<td{class_attr}>{html.escape(display)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def style_dataframe_for_display(df: pd.DataFrame, formatters: Optional[Dict[str, Any]] = None) -> Any:
    """Backward-compatible helper retained for any remaining direct calls."""
    styler = df.style
    if formatters:
        styler = styler.format(formatters)
    return styler


def format_dataframe_for_native_display(df: pd.DataFrame, formatters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Return a display-only copy for native st.dataframe rendering."""
    out = df.copy()
    if formatters:
        for col, formatter in formatters.items():
            if col in out.columns:
                out[col] = out[col].map(formatter)
    for col in out.columns:
        low = str(col).lower()
        if "date" in low:
            out[col] = out[col].map(fmt_date)
    return out


def style_money_table(df: pd.DataFrame, height: int = 430) -> None:
    if df is None or df.empty:
        st.info("No data available.")
        return
    formatters = {}
    for c in df.columns:
        low = c.lower()
        if any(k in low for k in ["value", "cost", "price", "p/l", "dividend", "proceeds", "amount", "basis"]):
            formatters[c] = fmt_currency
        if "%" in c or "yield" in low or ("return" in low and c.endswith("%")) or "weight" in low:
            formatters[c] = fmt_pct
        if "shares" in low:
            formatters[c] = lambda v: fmt_number(v, 4)
    render_semantic_table(df, formatters=formatters, height=height)


def style_quality_table(df: pd.DataFrame, height: int = 360) -> None:
    if df is None or df.empty:
        st.success("No data quality issues found.")
        return
    render_semantic_table(df, height=height)

# ============================================================
# Sidebar and session controls
# ============================================================


def render_sidebar(accounts_clean: pd.DataFrame, tx_clean: pd.DataFrame) -> Dict[str, Any]:
    st.sidebar.header("Controls")
    if st.sidebar.button("Refresh Online Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.session_state.last_online_refresh = now_et_str()
        st.rerun()
    st.sidebar.caption(f"{CREATOR_NAME} · {APP_VERSION}")
    theme_options = ["Auto", "Light", "Dark"]
    current_theme_mode = st.session_state.get("display_theme_mode", "Auto")
    if current_theme_mode not in theme_options:
        current_theme_mode = "Auto"
    st.session_state.display_theme_mode = st.sidebar.selectbox(
        "Chart/Table Text Contrast",
        theme_options,
        index=theme_options.index(current_theme_mode),
        help="Auto follows Streamlit theme when exposed. Choose Light or Dark if chart/table text contrast does not match the browser mode.",
    )

    with st.sidebar.expander("CSV Sources", expanded=True):
        uploaded_accounts = st.file_uploader("Upload accounts.csv", type=["csv"], key="accounts_uploader")
        if uploaded_accounts is not None:
            try:
                st.session_state.accounts_df = drop_fully_empty_rows(pd.read_csv(uploaded_accounts))
                st.session_state.accounts_source = getattr(uploaded_accounts, "name", "uploaded accounts.csv")
                st.session_state.accounts_source_type = "uploaded"
                st.session_state.accounts_signature = f"uploaded::{datetime.now(ET).timestamp()}"
            except Exception as exc:
                st.error(f"Could not read uploaded accounts CSV: {exc}")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Reload accounts.csv", use_container_width=True):
                load_file_into_session("accounts")
                st.rerun()
        with col_b:
            if st.button("Use sample accounts", use_container_width=True):
                st.session_state.accounts_df = embedded_sample_df("accounts")
                st.session_state.accounts_source = "embedded sample_accounts.csv"
                st.session_state.accounts_source_type = "embedded_sample_accounts"
                st.session_state.accounts_signature = f"sample_accounts::{datetime.now(ET).timestamp()}"
                st.rerun()

        uploaded_portfolio = st.file_uploader("Upload portfolio.csv", type=["csv"], key="portfolio_uploader")
        if uploaded_portfolio is not None:
            try:
                st.session_state.portfolio_df = drop_fully_empty_rows(pd.read_csv(uploaded_portfolio))
                st.session_state.portfolio_source = getattr(uploaded_portfolio, "name", "uploaded portfolio.csv")
                st.session_state.portfolio_source_type = "uploaded"
                st.session_state.portfolio_signature = f"uploaded::{datetime.now(ET).timestamp()}"
            except Exception as exc:
                st.error(f"Could not read uploaded portfolio CSV: {exc}")
        col_c, col_d = st.columns(2)
        with col_c:
            if st.button("Reload portfolio.csv", use_container_width=True):
                load_file_into_session("portfolio")
                st.rerun()
        with col_d:
            if st.button("Use sample portfolio", use_container_width=True):
                st.session_state.portfolio_df = embedded_sample_df("portfolio")
                st.session_state.portfolio_source = "embedded sample_portfolio.csv"
                st.session_state.portfolio_source_type = "embedded_sample_portfolio"
                st.session_state.portfolio_signature = f"sample_portfolio::{datetime.now(ET).timestamp()}"
                st.rerun()

        uploaded_dividends = st.file_uploader("Upload dividends.csv", type=["csv"], key="dividends_uploader")
        if uploaded_dividends is not None:
            try:
                st.session_state.dividends_df = drop_fully_empty_rows(pd.read_csv(uploaded_dividends))
                st.session_state.dividends_source = getattr(uploaded_dividends, "name", "uploaded dividends.csv")
                st.session_state.dividends_source_type = "uploaded"
                st.session_state.dividends_signature = f"uploaded::{datetime.now(ET).timestamp()}"
            except Exception as exc:
                st.error(f"Could not read uploaded dividends CSV: {exc}")
        col_e, col_f = st.columns(2)
        with col_e:
            if st.button("Reload dividends.csv", use_container_width=True):
                load_file_into_session("dividends")
                st.rerun()
        with col_f:
            if st.button("Use sample dividends", use_container_width=True):
                st.session_state.dividends_df = embedded_sample_df("dividends")
                st.session_state.dividends_source = "embedded sample_dividends.csv"
                st.session_state.dividends_source_type = "embedded_sample_dividends"
                st.session_state.dividends_signature = f"sample_dividends::{datetime.now(ET).timestamp()}"
                st.rerun()

    active_accounts = accounts_clean[accounts_clean["is_active"] == True].copy() if accounts_clean is not None and not accounts_clean.empty else pd.DataFrame()
    owners = sorted(active_accounts["owner"].dropna().astype(str).unique().tolist()) if not active_accounts.empty else []
    tax_buckets = sorted(active_accounts["tax_bucket"].dropna().astype(str).unique().tolist()) if not active_accounts.empty else []
    account_types = sorted(active_accounts["account_type"].dropna().astype(str).unique().tolist()) if not active_accounts.empty else []
    account_options = active_accounts[["account_id", "account_name", "owner"]].copy() if not active_accounts.empty else pd.DataFrame(columns=["account_id", "account_name", "owner"])
    account_label_map = {r["account_id"]: f"{r['account_name']} ({r['owner']})" for _, r in account_options.iterrows()}
    ticker_options = sorted(tx_clean["ticker"].dropna().astype(str).unique().tolist()) if tx_clean is not None and not tx_clean.empty and "ticker" in tx_clean.columns else []

    st.sidebar.markdown("---")
    view_mode = st.sidebar.selectbox("View Mode", ["Household", "By Owner", "By Account", "By Tax Bucket"], index=0)
    selected_owners = st.sidebar.multiselect("Owner Filter", owners, default=owners)
    selected_tax = st.sidebar.multiselect("Tax Bucket Filter", tax_buckets, default=tax_buckets)
    selected_types = st.sidebar.multiselect("Account Type Filter", account_types, default=account_types)
    selected_account_ids = st.sidebar.multiselect("Account Filter", options=list(account_label_map.keys()), default=list(account_label_map.keys()), format_func=lambda x: account_label_map.get(x, x))
    selected_tickers = st.sidebar.multiselect("Ticker Filter", ticker_options, default=ticker_options)
    period = st.sidebar.selectbox("Price History Period", list(PERIOD_MAP.keys()), index=4)
    benchmark = st.sidebar.selectbox("Benchmark", BENCHMARK_OPTIONS, index=0)
    dividend_mode = st.sidebar.selectbox("Dividend Calculation Mode", DIVIDEND_MODES, index=0)
    show_closed = st.sidebar.checkbox("Show Closed Positions", value=False)
    concentration_threshold = st.sidebar.slider("Concentration Warning Threshold", min_value=0.05, max_value=0.75, value=0.25, step=0.05, format="%.0f%%")

    return {
        "accounts_clean": accounts_clean,
        "view_mode": view_mode,
        "owners": selected_owners,
        "tax_buckets": selected_tax,
        "account_types": selected_types,
        "account_ids": selected_account_ids,
        "tickers": selected_tickers,
        "period": period,
        "benchmark": benchmark,
        "dividend_mode": dividend_mode,
        "show_closed": show_closed,
        "concentration_threshold": concentration_threshold,
    }

# ============================================================
# Main rendering
# ============================================================


def render_overview(holdings: pd.DataFrame, realized_df: pd.DataFrame, dividends: pd.DataFrame, upcoming: pd.DataFrame, summary: Dict[str, float], concentration_threshold: float) -> None:
    render_version_banner()
    st.subheader("Portfolio Summary")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Current Holdings Cost", fmt_currency(summary["current_holdings_cost"]), "Open-lot FIFO cost basis")
    with c2:
        render_kpi_card("Current Value", fmt_currency(summary["current_value"]), "Active holdings only")
    with c3:
        tone = "positive" if summary["unrealized_pl"] >= 0 else "negative"
        render_kpi_card("Unrealized P/L", fmt_currency(summary["unrealized_pl"]), "Open positions", tone)
    with c4:
        tone = "positive" if summary["realized_pl"] >= 0 else "negative"
        render_kpi_card("Realized P/L", fmt_currency(summary["realized_pl"]), "FIFO-matched sales", tone)
    st.markdown('<div class="kpi-row-gap"></div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        render_kpi_card("Actual Dividends YTD", fmt_currency(summary["actual_dividends_ytd"]), "Net payments received", "blue")
    with d2:
        render_kpi_card("Actual Dividends All-Time", fmt_currency(summary["actual_dividends_all_time"]), "From dividends.csv", "blue")
    with d3:
        tone = "positive" if summary["dividend_inclusive_pl"] >= 0 else "negative"
        render_kpi_card("Total Return incl. Dividends", fmt_currency(summary["dividend_inclusive_pl"]), "Realized + unrealized + dividends", tone)
    with d4:
        render_kpi_card("Estimated Annual Dividend", fmt_currency(summary["estimated_annual_dividend"]), "Estimated, not guaranteed", "blue")

    exp = exposure_by_ticker(holdings)
    if not exp.empty:
        concentrated = exp[exp["Household Weight %"] >= concentration_threshold]
        if not concentrated.empty:
            tickers = ", ".join([f"{r['Ticker']} ({fmt_pct(r['Household Weight %'], 1, False)})" for _, r in concentrated.iterrows()])
            st.markdown(f"<div class='warning-box'><b>Concentration warning:</b> {tickers} exceed the selected household exposure threshold.</div>", unsafe_allow_html=True)

    a, b = st.columns(2)
    with a:
        st.plotly_chart(make_allocation_chart(holdings, "Ticker", "Allocation by Ticker"), use_container_width=True, key="overview_allocation_ticker")
    with b:
        st.plotly_chart(make_allocation_chart(holdings, "tax_bucket", "Allocation by Tax Bucket"), use_container_width=True, key="overview_allocation_tax")
    c, d = st.columns(2)
    with c:
        st.plotly_chart(make_top_movers_chart(holdings), use_container_width=True, key="overview_top_movers")
    with d:
        st.plotly_chart(make_upcoming_dividend_chart(upcoming, 30), use_container_width=True, key="overview_upcoming_dividends")

    st.markdown("### Household Holding Exposure")
    style_money_table(exp, height=320)


def render_accounts_tab(holdings: pd.DataFrame, accounts: pd.DataFrame, dividends: pd.DataFrame) -> None:
    st.subheader("Accounts")
    acct = account_summary_table(holdings, accounts, dividends)
    st.markdown("### Account Summary")
    style_money_table(acct, height=420)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_bar_chart(group_summary(holdings, "owner"), "owner", "Market Value", "Market Value by Owner"), use_container_width=True, key="acct_owner_mv")
    with c2:
        st.plotly_chart(make_bar_chart(group_summary(holdings, "account_name"), "account_name", "Market Value", "Market Value by Account"), use_container_width=True, key="acct_account_mv")
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(make_bar_chart(group_summary(holdings, "tax_bucket"), "tax_bucket", "Market Value", "Market Value by Tax Bucket"), use_container_width=True, key="acct_tax_mv")
    with c4:
        st.plotly_chart(make_bar_chart(group_summary(holdings, "owner"), "owner", "Estimated Annual Dividend", "Estimated Annual Dividend by Owner"), use_container_width=True, key="acct_owner_div")


def render_holdings_tab(holdings: pd.DataFrame, show_closed: bool) -> None:
    st.subheader("Holdings")
    display = holdings.copy() if holdings is not None else pd.DataFrame()
    if not show_closed and not display.empty:
        display = display[display["Holding Status"] == "Active"].copy()
    st.caption("Closed positions are hidden by default and are excluded from future dividend projections. Enable 'Show Closed Positions' in the sidebar to inspect fully sold positions.")
    cols = [
        "owner", "account_name", "tax_bucket", "Ticker", "Shares", "Avg Buy Price", "Current Price", "Cost Basis", "Market Value", "Unrealized P/L", "Return %", "Realized P/L", "Actual Dividends", "Total Return incl. Dividends", "Portfolio Weight %", "Estimated Annual Dividend", "Yield on Cost", "Current Yield", "Dividend Frequency", "Next Estimated Ex-Date", "Dividend Status", "Holding Status",
    ]
    cols = [c for c in cols if c in display.columns]
    style_money_table(display[cols] if not display.empty else display, height=560)
    st.markdown("### Cross-Account Holding Exposure")
    style_money_table(exposure_by_ticker(holdings), height=360)


def render_realized_tab(realized_df: pd.DataFrame, holdings: pd.DataFrame) -> None:
    st.subheader("Realized P/L")
    st.caption("SELL transactions are matched to BUY lots using FIFO by account_id and ticker. Closed positions remain visible when enabled and keep realized P/L and historical dividends.")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_realized_chart(realized_df, "Ticker"), use_container_width=True, key="realized_by_ticker")
    with c2:
        group = "account_name" if realized_df is not None and not realized_df.empty and "account_name" in realized_df.columns else "Account ID"
        st.plotly_chart(make_realized_chart(realized_df, group), use_container_width=True, key="realized_by_account")
    st.markdown("### Realized Lot Matches")
    style_money_table(realized_df, height=480)
    st.markdown("### Closed Position Performance incl. Dividends")
    if holdings is None or holdings.empty:
        st.info("No closed position data.")
    else:
        closed = holdings[holdings["Holding Status"] == "Closed"].copy()
        if closed.empty:
            st.info("No closed positions in the selected filters.")
        else:
            style_money_table(closed[[c for c in ["owner", "account_name", "Ticker", "Realized P/L", "Actual Dividends", "Total Return incl. Dividends", "Holding Status"] if c in closed.columns]], height=320)


def render_dividend_tab(holdings: pd.DataFrame, dividends: pd.DataFrame, upcoming: pd.DataFrame, dividend_analysis: Dict[str, Dict[str, Any]]) -> None:
    st.subheader("Dividend")
    st.markdown("<div class='warning-box'><b>Dividend date policy:</b> yfinance future dividend dates are not treated as confirmed. Pattern-derived dates are labeled Estimated; unavailable dates are Unknown.</div>", unsafe_allow_html=True)
    st.markdown("### Actual Dividend Payments")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(make_monthly_actual_dividend_chart(dividends), use_container_width=True, key="div_monthly_actual")
    with c2:
        st.plotly_chart(make_cumulative_dividend_chart(dividends), use_container_width=True, key="div_cumulative_actual")
    c3, c4 = st.columns(2)
    if dividends is not None and not dividends.empty:
        by_ticker = dividends.groupby("ticker", as_index=False)["net_amount"].sum().rename(columns={"ticker": "Ticker", "net_amount": "Actual Dividends"})
        div_enriched = enrich_with_accounts(dividends, holdings.rename(columns={"Account ID": "account_id"}) if False else st.session_state.get("_accounts_clean", pd.DataFrame()))
    else:
        by_ticker = pd.DataFrame()
        div_enriched = pd.DataFrame()
    with c3:
        st.plotly_chart(make_bar_chart(by_ticker, "Ticker", "Actual Dividends", "Actual Dividends by Ticker"), use_container_width=True, key="div_by_ticker")
    with c4:
        if not div_enriched.empty and "account_name" in div_enriched.columns:
            by_account = div_enriched.groupby("account_name", as_index=False)["net_amount"].sum().rename(columns={"account_name": "Account", "net_amount": "Actual Dividends"})
        else:
            by_account = pd.DataFrame()
        st.plotly_chart(make_bar_chart(by_account, "Account", "Actual Dividends", "Actual Dividends by Account"), use_container_width=True, key="div_by_account")
    st.markdown("### Actual Dividend Table")
    style_money_table(dividends, height=320)

    st.markdown("### Estimated Dividend Forecast")
    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(make_monthly_estimated_dividend_calendar(upcoming), use_container_width=True, key="div_monthly_estimated")
    with c6:
        est = holdings[holdings["Holding Status"] == "Active"].groupby("Ticker", as_index=False)["Estimated Annual Dividend"].sum() if holdings is not None and not holdings.empty else pd.DataFrame()
        st.plotly_chart(make_bar_chart(est, "Ticker", "Estimated Annual Dividend", "Estimated Annual Dividend by Ticker"), use_container_width=True, key="div_est_by_ticker")
    st.markdown("### Upcoming Estimated Dividend Table")
    style_money_table(upcoming, height=320)

    st.markdown("### Estimated vs Actual Last 12M")
    if holdings is None or holdings.empty:
        st.info("No data available.")
    else:
        est12 = holdings.groupby("Ticker", as_index=False)["Estimated Annual Dividend"].sum().rename(columns={"Estimated Annual Dividend": "Estimated Annual Dividend"})
        if dividends is not None and not dividends.empty:
            d = dividends.copy()
            d["payment_date"] = pd.to_datetime(d["payment_date"], errors="coerce")
            d = d[d["payment_date"] >= pd.Timestamp(TODAY - timedelta(days=365))]
            act12 = d.groupby("ticker", as_index=False)["net_amount"].sum().rename(columns={"ticker": "Ticker", "net_amount": "Actual Last 12M Dividends"})
        else:
            act12 = pd.DataFrame(columns=["Ticker", "Actual Last 12M Dividends"])
        comp = est12.merge(act12, on="Ticker", how="outer").fillna(0.0)
        comp["Difference"] = comp["Actual Last 12M Dividends"] - comp["Estimated Annual Dividend"]
        style_money_table(comp, height=300)


def render_price_tab(transactions: pd.DataFrame, holdings: pd.DataFrame, online_data: Dict[str, Dict[str, Any]], benchmark: str) -> None:
    st.subheader("Price Trend")
    tickers = sorted(transactions["ticker"].dropna().astype(str).unique().tolist()) if transactions is not None and not transactions.empty else []
    if not tickers:
        st.info("No tickers available.")
        return
    selected = st.selectbox("Selected Ticker", tickers)
    st.plotly_chart(make_price_chart(selected, online_data, transactions, holdings), use_container_width=True, key="price_selected_chart")
    st.plotly_chart(make_normalized_chart(tickers, online_data, benchmark), use_container_width=True, key="price_normalized_chart")
    st.plotly_chart(make_drawdown_chart(tickers, online_data), use_container_width=True, key="price_drawdown_chart")


def render_data_manager(accounts_clean: pd.DataFrame, tx_clean: pd.DataFrame, div_clean: pd.DataFrame, data_quality: pd.DataFrame) -> None:
    st.subheader("Data Manager")
    st.markdown("### Data Quality Check")
    st.caption("Review data quality issues before editing account, transaction, or dividend CSV data.")
    if data_quality is None or data_quality.empty:
        st.success("No data quality issues detected.")
    else:
        dq_errors = int((data_quality["Severity"] == "Error").sum()) if "Severity" in data_quality.columns else 0
        dq_warnings = int((data_quality["Severity"] == "Warning").sum()) if "Severity" in data_quality.columns else 0
        dq_infos = int((data_quality["Severity"] == "Info").sum()) if "Severity" in data_quality.columns else 0
        qc1, qc2, qc3 = st.columns(3)
        qc1.metric("Errors", dq_errors)
        qc2.metric("Warnings", dq_warnings)
        qc3.metric("Info", dq_infos)
        style_quality_table(data_quality, height=360)
    st.markdown("---")
    st.markdown("### Accounts Manager")
    st.code("account_id,owner,account_name,broker,account_type,tax_bucket,currency,is_active,note", language="text")
    acct_base = accounts_clean[ACCOUNT_COLUMNS].copy() if accounts_clean is not None and not accounts_clean.empty else pd.DataFrame(columns=ACCOUNT_COLUMNS)
    edited_accounts = st.data_editor(
        acct_base,
        use_container_width=True,
        num_rows="dynamic",
        height=280,
        column_config={
            "account_id": st.column_config.TextColumn("account_id", required=True),
            "owner": st.column_config.TextColumn("owner", required=True),
            "account_name": st.column_config.TextColumn("account_name", required=True),
            "broker": st.column_config.TextColumn("broker"),
            "account_type": st.column_config.TextColumn("account_type"),
            "tax_bucket": st.column_config.SelectboxColumn("tax_bucket", options=["Retirement", "Taxable", "Unclassified"]),
            "currency": st.column_config.TextColumn("currency"),
            "is_active": st.column_config.CheckboxColumn("is_active"),
            "note": st.column_config.TextColumn("note"),
        },
        key="accounts_editor",
    )
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Apply Edited Accounts", type="primary", use_container_width=True):
            st.session_state.accounts_df = normalize_accounts(drop_fully_empty_rows(edited_accounts))
            st.session_state.accounts_source = "edited in Data Manager"
            st.session_state.accounts_source_type = "edited"
            st.session_state.accounts_signature = f"edited_accounts::{datetime.now(ET).timestamp()}"
            st.success("Edited accounts applied to current session.")
            st.rerun()
    with a2:
        st.download_button("Download accounts.csv", data=to_csv_bytes(normalize_accounts(drop_fully_empty_rows(edited_accounts))), file_name=ACCOUNTS_CSV_NAME, mime="text/csv", use_container_width=True)
    with a3:
        if st.button("Save to local accounts.csv", use_container_width=True):
            try:
                normalize_accounts(drop_fully_empty_rows(edited_accounts)).to_csv(BASE_DIR / ACCOUNTS_CSV_NAME, index=False, encoding="utf-8-sig")
                load_file_into_session("accounts")
                st.success("Saved accounts.csv locally.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save accounts.csv: {exc}")

    st.markdown("### Add New Account")
    with st.form("add_account_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            new_account_id = st.text_input("Account ID", value="")
            new_owner = st.text_input("Owner", value="Me")
        with c2:
            new_account_name = st.text_input("Account Name", value="")
            new_broker = st.text_input("Broker", value="Fidelity")
        with c3:
            new_account_type = st.text_input("Account Type", value="Taxable Brokerage")
            new_tax_bucket = st.selectbox("Tax Bucket", ["Retirement", "Taxable", "Unclassified"], index=1)
        with c4:
            new_currency = st.text_input("Currency", value="USD")
            new_note = st.text_input("Account Note", value="")
        if st.form_submit_button("Add Account", type="primary"):
            row = pd.DataFrame([{"account_id": new_account_id, "owner": new_owner, "account_name": new_account_name, "broker": new_broker, "account_type": new_account_type, "tax_bucket": new_tax_bucket, "currency": new_currency, "is_active": True, "note": new_note}])
            current = normalize_accounts(drop_fully_empty_rows(st.session_state.accounts_df))
            st.session_state.accounts_df = pd.concat([current, row], ignore_index=True)
            st.session_state.accounts_source = "edited in Data Manager"
            st.session_state.accounts_source_type = "edited"
            st.session_state.accounts_signature = f"edited_accounts::{datetime.now(ET).timestamp()}"
            st.success("New account added.")
            st.rerun()

    st.markdown("---")
    st.markdown("### Portfolio Transactions Manager")
    st.code("transaction_date,transaction_type,ticker,shares,price,fee,account_id,note", language="text")
    tx_base = tx_clean[TX_COLUMNS].copy() if tx_clean is not None and not tx_clean.empty else pd.DataFrame(columns=TX_COLUMNS)
    account_ids = sorted(accounts_clean["account_id"].dropna().astype(str).unique().tolist()) if accounts_clean is not None and not accounts_clean.empty else ["DEFAULT"]
    edited_tx = st.data_editor(
        tx_base,
        use_container_width=True,
        num_rows="dynamic",
        height=320,
        column_config={
            "transaction_date": st.column_config.DateColumn("transaction_date", format="YYYY-MM-DD"),
            "transaction_type": st.column_config.SelectboxColumn("transaction_type", options=TRANSACTION_TYPES),
            "ticker": st.column_config.TextColumn("ticker", required=True),
            "shares": st.column_config.NumberColumn("shares", min_value=0.000001, step=1.0, format="%.6f"),
            "price": st.column_config.NumberColumn("price", min_value=0.000001, step=0.01, format="%.4f"),
            "fee": st.column_config.NumberColumn("fee", step=0.01, format="%.4f"),
            "account_id": st.column_config.SelectboxColumn("account_id", options=account_ids),
            "note": st.column_config.TextColumn("note"),
        },
        key="transaction_editor",
    )
    t1, t2, t3 = st.columns(3)
    with t1:
        if st.button("Apply Edited Transactions", type="primary", use_container_width=True):
            normalized, _ = migrate_transaction_schema(drop_fully_empty_rows(edited_tx))
            normalized["ticker"] = normalized["ticker"].astype("string").fillna("").str.strip().str.upper()
            normalized["account_id"] = normalized["account_id"].map(clean_id)
            st.session_state.portfolio_df = normalized
            st.session_state.portfolio_source = "edited in Data Manager"
            st.session_state.portfolio_source_type = "edited"
            st.session_state.portfolio_signature = f"edited_portfolio::{datetime.now(ET).timestamp()}"
            st.success("Edited transactions applied.")
            st.rerun()
    with t2:
        st.download_button("Download portfolio.csv", data=to_csv_bytes(migrate_transaction_schema(drop_fully_empty_rows(edited_tx))[0]), file_name=PORTFOLIO_CSV_NAME, mime="text/csv", use_container_width=True)
    with t3:
        if st.button("Save to local portfolio.csv", use_container_width=True):
            try:
                migrate_transaction_schema(drop_fully_empty_rows(edited_tx))[0].to_csv(BASE_DIR / PORTFOLIO_CSV_NAME, index=False, encoding="utf-8-sig")
                load_file_into_session("portfolio")
                st.success("Saved portfolio.csv locally.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save portfolio.csv: {exc}")

    st.markdown("### Add New Transaction")
    with st.form("add_transaction_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            new_date = st.date_input("Date", value=TODAY)
            new_type = st.selectbox("Type", TRANSACTION_TYPES)
        with c2:
            new_ticker = st.text_input("Ticker", value="")
            new_account_id = st.selectbox("Account ID", account_ids)
        with c3:
            new_shares = st.number_input("Shares", min_value=0.000001, value=1.0, step=1.0, format="%.6f")
            new_price = st.number_input("Price", min_value=0.000001, value=1.0, step=0.01, format="%.4f")
        with c4:
            new_fee = st.number_input("Fee", value=0.0, step=0.01, format="%.4f")
            new_note = st.text_input("Note", value="")
        if st.form_submit_button("Add Transaction", type="primary"):
            row = pd.DataFrame([{"transaction_date": new_date, "transaction_type": new_type, "ticker": new_ticker.strip().upper(), "shares": new_shares, "price": new_price, "fee": new_fee, "account_id": new_account_id, "note": new_note}])
            current, _ = migrate_transaction_schema(drop_fully_empty_rows(st.session_state.portfolio_df))
            st.session_state.portfolio_df = pd.concat([current, row], ignore_index=True)
            st.session_state.portfolio_source = "edited in Data Manager"
            st.session_state.portfolio_source_type = "edited"
            st.session_state.portfolio_signature = f"edited_portfolio::{datetime.now(ET).timestamp()}"
            st.success("New transaction added.")
            st.rerun()

    st.markdown("---")
    st.markdown("### Dividend Payments Manager")
    st.code("payment_date,ticker,net_amount,account_id,note", language="text")
    div_base = div_clean[DIV_COLUMNS].copy() if div_clean is not None and not div_clean.empty else pd.DataFrame(columns=DIV_COLUMNS)
    edited_div = st.data_editor(
        div_base,
        use_container_width=True,
        num_rows="dynamic",
        height=300,
        column_config={
            "payment_date": st.column_config.DateColumn("payment_date", format="YYYY-MM-DD"),
            "ticker": st.column_config.TextColumn("ticker", required=True),
            "net_amount": st.column_config.NumberColumn("net_amount", step=0.01, format="%.4f"),
            "account_id": st.column_config.SelectboxColumn("account_id", options=account_ids),
            "note": st.column_config.TextColumn("note"),
        },
        key="dividend_editor",
    )
    d1, d2, d3 = st.columns(3)
    with d1:
        if st.button("Apply Edited Dividends", type="primary", use_container_width=True):
            normalized, _ = migrate_dividend_schema(drop_fully_empty_rows(edited_div))
            normalized["ticker"] = normalized["ticker"].astype("string").fillna("").str.strip().str.upper()
            normalized["account_id"] = normalized["account_id"].map(clean_id)
            st.session_state.dividends_df = normalized
            st.session_state.dividends_source = "edited in Data Manager"
            st.session_state.dividends_source_type = "edited"
            st.session_state.dividends_signature = f"edited_dividends::{datetime.now(ET).timestamp()}"
            st.success("Edited dividends applied.")
            st.rerun()
    with d2:
        st.download_button("Download dividends.csv", data=to_csv_bytes(migrate_dividend_schema(drop_fully_empty_rows(edited_div))[0]), file_name=DIVIDENDS_CSV_NAME, mime="text/csv", use_container_width=True)
    with d3:
        if st.button("Save to local dividends.csv", use_container_width=True):
            try:
                migrate_dividend_schema(drop_fully_empty_rows(edited_div))[0].to_csv(BASE_DIR / DIVIDENDS_CSV_NAME, index=False, encoding="utf-8-sig")
                load_file_into_session("dividends")
                st.success("Saved dividends.csv locally.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save dividends.csv: {exc}")

    st.markdown("### Add New Dividend Payment")
    with st.form("add_dividend_form", clear_on_submit=True):
        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            new_payment_date = st.date_input("Payment Date", value=TODAY, key="new_div_payment_date")
        with dc2:
            new_div_ticker = st.text_input("Dividend Ticker", value="")
            new_div_account_id = st.selectbox("Dividend Account ID", account_ids)
        with dc3:
            new_net_amount = st.number_input("Net Amount", value=0.01, step=0.01, format="%.4f")
        with dc4:
            new_div_note = st.text_input("Dividend Note", value="")
        if st.form_submit_button("Add Dividend Payment", type="primary"):
            row = pd.DataFrame([{"payment_date": new_payment_date, "ticker": new_div_ticker.strip().upper(), "net_amount": new_net_amount, "account_id": new_div_account_id, "note": new_div_note}])
            current, _ = migrate_dividend_schema(drop_fully_empty_rows(st.session_state.dividends_df))
            st.session_state.dividends_df = pd.concat([current, row], ignore_index=True)
            st.session_state.dividends_source = "edited in Data Manager"
            st.session_state.dividends_source_type = "edited"
            st.session_state.dividends_signature = f"edited_dividends::{datetime.now(ET).timestamp()}"
            st.success("New dividend payment added.")
            st.rerun()

    st.markdown("---")
    st.markdown("### Migration Notes")
    st.markdown(
        """
        - `accounts.csv` is the account master. Do not use real account numbers; use aliases such as `ME_FID_ROTH`.
        - `portfolio.csv` uses `account_id` and stores only `BUY` / `SELL` transactions.
        - `dividends.csv` uses `account_id` and stores actual net dividend payments.
        - Legacy `account` columns are migrated to `account_id` in session.
        - SELL transactions use positive shares and are FIFO-matched within the same `account_id + ticker`.
        - Closed positions are hidden by default, excluded from future dividend projections, and included in realized/dividend-inclusive performance.
        """
    )


def main() -> None:
    inject_css()
    initialize_session_state()
    if "last_online_refresh" not in st.session_state:
        st.session_state.last_online_refresh = "Not refreshed in this session"

    accounts_clean, account_quality, account_valid_mask = validate_accounts(st.session_state.accounts_df)
    valid_account_ids = accounts_clean.loc[account_valid_mask, "account_id"].tolist() if not accounts_clean.empty and not account_valid_mask.empty else []
    tx_clean, tx_quality, tx_valid_mask, tx_migrated = clean_and_validate_transactions(st.session_state.portfolio_df, valid_account_ids)
    known_tickers = tx_clean["ticker"].dropna().astype(str).unique().tolist() if not tx_clean.empty else []
    div_clean, div_quality, div_valid_mask, div_migrated = clean_and_validate_dividends(st.session_state.dividends_df, valid_account_ids, known_tickers)

    st.session_state["_accounts_clean"] = accounts_clean
    controls = render_sidebar(accounts_clean, tx_clean)

    # Apply filters after validation. Unknown-account rows are retained but metadata becomes Unmapped.
    tx_valid = tx_clean.loc[tx_valid_mask].copy() if not tx_valid_mask.empty else pd.DataFrame(columns=TX_COLUMNS)
    div_valid = div_clean.loc[div_valid_mask].copy() if not div_valid_mask.empty else pd.DataFrame(columns=DIV_COLUMNS)
    filtered_tx = filter_frame_by_controls(tx_valid, controls)
    filtered_div = filtered_dividends(div_valid, controls)
    filtered_accounts = accounts_clean.copy()
    if controls.get("owners"):
        filtered_accounts = filtered_accounts[filtered_accounts["owner"].astype(str).isin(controls["owners"])]
    if controls.get("tax_buckets"):
        filtered_accounts = filtered_accounts[filtered_accounts["tax_bucket"].astype(str).isin(controls["tax_buckets"])]
    if controls.get("account_types"):
        filtered_accounts = filtered_accounts[filtered_accounts["account_type"].astype(str).isin(controls["account_types"])]
    if controls.get("account_ids"):
        filtered_accounts = filtered_accounts[filtered_accounts["account_id"].astype(str).isin(controls["account_ids"])]

    tickers = sorted(filtered_tx["ticker"].dropna().astype(str).unique().tolist()) if not filtered_tx.empty else []
    with st.spinner("Refreshing online market data..."):
        online_data, online_quality = fetch_all_online_data(tickers, controls["period"], controls["benchmark"])
        if st.session_state.last_online_refresh == "Not refreshed in this session":
            st.session_state.last_online_refresh = now_et_str()

    tx_detail, realized_df, holdings, dividend_analysis, summary = build_portfolio_tables(filtered_tx, filtered_div, filtered_accounts, online_data, controls["dividend_mode"])
    upcoming = build_upcoming_dividends(holdings, dividend_analysis, days=90)

    quality_frames = [q for q in [account_quality, tx_quality, div_quality, online_quality] if q is not None and not q.empty]
    data_quality = pd.concat(quality_frames, ignore_index=True) if quality_frames else pd.DataFrame(columns=["Severity", "Row", "Column", "Raw Value", "Issue"])

    render_header(st.session_state.last_online_refresh)

    tabs = st.tabs(["Overview", "Accounts", "Holdings", "Realized P/L", "Dividend", "Price Trend", "Data Manager"])
    with tabs[0]:
        render_overview(holdings, realized_df, filtered_div, upcoming, summary, controls["concentration_threshold"])
    with tabs[1]:
        render_accounts_tab(holdings, filtered_accounts, filtered_div)
    with tabs[2]:
        render_holdings_tab(holdings, controls["show_closed"])
    with tabs[3]:
        render_realized_tab(realized_df, holdings)
    with tabs[4]:
        render_dividend_tab(holdings, filtered_div, upcoming, dividend_analysis)
    with tabs[5]:
        render_price_tab(filtered_tx, holdings, online_data, controls["benchmark"])
    with tabs[6]:
        render_data_manager(accounts_clean, tx_clean, div_clean, data_quality)


if __name__ == "__main__":
    main()
