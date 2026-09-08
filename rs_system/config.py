"""
Automated RS System — Configuration
All tunable parameters, index symbols, and thresholds in one place.
"""

# ─── RS Weighting (IBD / Minervini style) ───────────────────────────
RS_WEIGHTS = {
    "6m": 0.40,   # 126 trading days
    "3m": 0.30,   # 63 trading days
    "1m": 0.20,   # 21 trading days
    "1w": 0.10,   # 5 trading days
}

LOOKBACK_DAYS = {
    "6m": 126,
    "3m": 63,
    "1m": 21,
    "1w": 5,
}

# ─── Data Fetching ──────────────────────────────────────────────────
YFINANCE_BATCH_SIZE = 80          # Tickers per yfinance batch call
YFINANCE_PERIOD = "1y"            # Download window
YFINANCE_RETRY_COUNT = 1          # Retry failed tickers once
MIN_TRADING_DAYS = 100            # Minimum data points needed

# ─── Filters ────────────────────────────────────────────────────────
MIN_AVG_VOLUME = 10_000           # Minimum avg daily volume (shares)
MIN_MARKET_CAP = 10_000_000_000   # ₹1,000 Crore = ₹10 Billion
MIN_PRICE = 35                    # Minimum last traded price (₹)
MIN_INDUSTRY_STOCKS = 3           # Min stocks for an industry to rank
RS_LEADER_THRESHOLD = 80          # RS percentile cutoff for "leaders"
NEAR_HIGH_PCT = 0.10              # Within 10% of 52W high

# ─── Benchmark ──────────────────────────────────────────────────────
BENCHMARK_SYMBOL = "^NSEI"        # Nifty 50
BENCHMARK_NAME = "Nifty 50"

# ─── NSE Sectoral & Thematic Index Symbols (Yahoo Finance) ─────────
SECTORAL_INDICES = {
    "Nifty Bank":               "^NSEBANK",
    "Nifty IT":                 "^CNXIT",
    "Nifty Auto":               "^CNXAUTO",
    "Nifty FMCG":               "^CNXFMCG",
    "Nifty Metal":              "^CNXMETAL",
    "Nifty Pharma":             "^CNXPHARMA",
    "Nifty Realty":             "^CNXREALTY",
    "Nifty Energy":             "^CNXENERGY",
    "Nifty Infra":              "^CNXINFRA",
    "Nifty Media":              "^CNXMEDIA",
    "Nifty PSU Bank":           "^CNXPSUBANK",
    "Nifty Financial Services": "NIFTY_FIN_SERVICE.NS",
    "Nifty Private Bank":       "NIFTY_PVT_BANK.NS",
    "Nifty Healthcare":         "NIFTY_HEALTHCARE.NS",
    "Nifty Consumer Durables":  "NIFTY_CONSR_DURBL.NS",
    "Nifty Oil & Gas":          "NIFTY_OIL_AND_GAS.NS",
    "Nifty Commodities":        "^CNXCMDT",
    "Nifty Consumption":        "^CNXCONSUM",
    "Nifty PSE":                "^CNXPSE",
    "Nifty Services":           "^CNXSERVICE",
    "Nifty MNC":                "^CNXMNC",
}

# ─── Broad Market Indices (for reference / future use) ──────────────
BROAD_INDICES = {
    "Nifty 50":         "^NSEI",
    "Nifty Next 50":    "^NSMIDCP",
    "Nifty 100":        "^CNX100",
    "Nifty 200":        "^CNX200",
    "Nifty 500":        "^CRSLDX",
    "Nifty Midcap 50":  "^NSEMDCP50",
    "Nifty Midcap 100": "^CNXMIDCAP",
    "Nifty Smallcap 100": "^CNXSC",
}

# ─── TradingView Scanner API ────────────────────────────────────────
TV_SCANNER_URL = "https://scanner.tradingview.com/india/scan"
TV_SCANNER_PAYLOAD = {
    "filter": [
        {"left": "exchange", "operation": "equal", "right": "NSE"},
        {"left": "typespecs", "operation": "has", "right": ["common"]},
    ],
    "options": {"lang": "en"},
    "symbols": {"query": {"types": []}},
    "columns": [
        "name", "description", "sector", "industry",
        "close", "volume", "average_volume_10d_calc",
        "High.All", "market_cap_basic",
    ],
    "sort": {"sortBy": "name", "sortOrder": "asc"},
    "range": [0, 5000],
}

# ─── Cache Settings ─────────────────────────────────────────────────
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
SITE_DIR = os.path.join(PROJECT_ROOT, "docs")  # GitHub Pages serves from /docs

INDUSTRY_MAP_CACHE = os.path.join(CACHE_DIR, "industry_map.csv")
INDUSTRY_MAP_TTL_DAYS = 7   # Refresh industry mapping weekly

# ─── Output Settings ────────────────────────────────────────────────
TOP_INDUSTRIES_COUNT = 20
TOP_STOCKS_DISPLAY = 50
