"""
Automated RS System — Main CLI Entry Point
Usage:
    python -m rs_system.main                     # Full scan, all outputs
    python -m rs_system.main --top 30            # Show top 30 stocks in terminal
    python -m rs_system.main --industry "Steel"  # Filter by industry
    python -m rs_system.main --no-dashboard      # Skip HTML generation
    python -m rs_system.main --min-volume 50000  # Override min avg volume filter
"""

import argparse
import sys
import time
import os
import warnings
from datetime import datetime

import pandas as pd

from . import config
from .data_fetcher import fetch_universe, fetch_prices, fetch_benchmark, fetch_sectoral_indices
from .rs_engine import (
    calculate_stock_rs,
    calculate_industry_rs,
    calculate_sector_index_rs,
    find_leaders_in_leading_groups,
)
from .report import (
    export_all_stocks,
    export_top_industries,
    export_sector_index_rs as export_sector_csv,
    export_leaders,
    generate_dashboard,
)

warnings.filterwarnings("ignore")


def print_banner():
    """Print startup banner."""
    print()
    print("=" * 60)
    print("  // AUTOMATED RELATIVE STRENGTH SYSTEM")
    print("  // NSE Full Market Scanner")
    print(f"  // {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Automated RS System — Full NSE Market Scanner"
    )
    parser.add_argument(
        "--top", type=int, default=20,
        help="Number of top stocks to display in terminal (default: 20)"
    )
    parser.add_argument(
        "--industry", type=str, default=None,
        help="Filter results to a specific industry (e.g., 'Steel')"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="Skip HTML dashboard generation"
    )
    parser.add_argument(
        "--min-volume", type=int, default=None,
        help=f"Override minimum avg volume filter (default: {config.MIN_AVG_VOLUME:,})"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only fetch universe, skip price downloads (for testing connectivity)"
    )
    args = parser.parse_args()

    print_banner()
    t_start = time.time()

    # ── Step 1: Fetch Universe ──────────────────────────────────────
    print("[1/6] Fetching NSE universe from TradingView...")
    try:
        universe = fetch_universe()
    except Exception as e:
        print(f"\n✗ Failed to fetch universe: {e}")
        print("  Check your internet connection and try again.")
        sys.exit(1)

    # Apply volume filter
    min_vol = args.min_volume if args.min_volume is not None else config.MIN_AVG_VOLUME
    pre_filter = len(universe)
    filters_applied = []

    if min_vol > 0 and 'Avg_Volume_10D' in universe.columns:
        universe = universe[universe['Avg_Volume_10D'].fillna(0) >= min_vol]
        filters_applied.append(f"Avg Volume ≥ {min_vol:,}")

    # Apply market cap filter
    if config.MIN_MARKET_CAP > 0 and 'Market_Cap' in universe.columns:
        universe = universe[universe['Market_Cap'].fillna(0) >= config.MIN_MARKET_CAP]
        filters_applied.append(f"Market Cap ≥ ₹{config.MIN_MARKET_CAP / 1e7:,.0f} Cr")

    # Apply minimum price filter
    if config.MIN_PRICE > 0 and 'Close' in universe.columns:
        universe = universe[universe['Close'].fillna(0) >= config.MIN_PRICE]
        filters_applied.append(f"Price ≥ ₹{config.MIN_PRICE}")

    universe = universe.reset_index(drop=True)
    print(f"  Filters ({', '.join(filters_applied)}): {pre_filter} → {len(universe)} stocks")

    tickers = universe['Ticker'].tolist()

    if args.dry_run:
        print(f"\n✓ Dry run complete. {len(tickers)} tickers ready.")
        print("  Top 10 by market cap:")
        if 'Market_Cap' in universe.columns:
            top_mc = universe.nlargest(10, 'Market_Cap')[['Symbol', 'Sector', 'Industry', 'Close']]
            print(top_mc.to_string(index=False))
        print(f"\n  Unique sectors: {universe['Sector'].nunique()}")
        print(f"  Unique industries: {universe['Industry'].nunique()}")
        return

    # ── Step 2: Fetch Benchmark ─────────────────────────────────────
    print(f"\n[2/6] Fetching benchmark ({config.BENCHMARK_NAME})...")
    benchmark = fetch_benchmark(config.BENCHMARK_SYMBOL, config.YFINANCE_PERIOD)
    if benchmark.empty:
        print("✗ Failed to fetch benchmark. Exiting.")
        sys.exit(1)
    print(f"  ✓ {len(benchmark)} days of benchmark data")

    # ── Step 3: Fetch Stock Prices ──────────────────────────────────
    print(f"\n[3/6] Downloading price data for {len(tickers)} stocks (batches of {config.YFINANCE_BATCH_SIZE})...")
    t_prices = time.time()
    prices = fetch_prices(tickers, config.YFINANCE_PERIOD, config.YFINANCE_BATCH_SIZE)
    print(f"  ✓ {len(prices)} stocks loaded in {time.time() - t_prices:.1f}s")

    # ── Step 4: Fetch Sectoral Indices ──────────────────────────────
    print(f"\n[4/6] Fetching {len(config.SECTORAL_INDICES)} sectoral indices...")
    sector_prices = fetch_sectoral_indices(config.YFINANCE_PERIOD)
    print(f"  ✓ {len(sector_prices)} indices loaded")

    # ── Step 5: Calculate RS Metrics ────────────────────────────────
    print("\n[5/6] Calculating Relative Strength metrics...")

    stock_rs = calculate_stock_rs(prices, benchmark)
    print(f"  ✓ {len(stock_rs)} stocks rated")

    industry_rs = calculate_industry_rs(stock_rs, universe)
    print(f"  ✓ {len(industry_rs)} industries ranked")

    sector_rs = calculate_sector_index_rs(sector_prices, benchmark)
    print(f"  ✓ {len(sector_rs)} sectoral indices compared")

    leaders = find_leaders_in_leading_groups(
        stock_rs, industry_rs, universe,
        top_n_industries=config.TOP_INDUSTRIES_COUNT,
        min_rs=config.RS_LEADER_THRESHOLD,
    )
    print(f"  ✓ {len(leaders)} leaders in top {config.TOP_INDUSTRIES_COUNT} industries")

    # ── Step 6: Generate Reports ────────────────────────────────────
    print(f"\n[6/6] Generating reports...")
    
    # --- HISTORY TRACKING ---
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    history_file = config.INDUSTRY_HISTORY_FILE
    
    # 1. Prepare today's data for appending
    today_history = industry_rs[['Industry', 'Rank', 'Median_RS']].copy()
    today_history['Date'] = date_stamp
    
    # 2. Append to CSV
    os.makedirs(config.HISTORY_DIR, exist_ok=True)
    if os.path.exists(history_file):
        # Load existing, remove today's data if we are re-running on the same day
        old_hist = pd.read_csv(history_file)
        old_hist = old_hist[old_hist['Date'] != date_stamp]
        full_hist = pd.concat([old_hist, today_history], ignore_index=True)
    else:
        full_hist = today_history
        
    full_hist.to_csv(history_file, index=False)
    
    # ------------------------

    report.export_all_stocks(stock_rs)
    report.export_top_industries(industry_rs)
    report.export_sector_index_rs(sector_rs)
    report.export_leaders(leaders)

    if not args.no_dashboard:
        html_path = report.generate_dashboard(stock_rs, industry_rs, sector_rs, leaders, history_df=full_hist)
        print(f"  → {html_path}")
    else:
        print("  (HTML dashboard skipped)")

    # ── Summary ─────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    print()
    print("=" * 60)
    print(f"  ✓ COMPLETE in {elapsed:.1f} seconds")
    print("=" * 60)

    # ── Terminal Output ─────────────────────────────────────────────

    # Apply industry filter if specified
    display_stocks = stock_rs.copy()
    display_leaders = leaders.copy()
    if args.industry:
        industry_filter = args.industry.lower()
        # Merge industry info for filtering
        merged = display_stocks.merge(
            universe[['Ticker', 'Industry']], on='Ticker', how='left'
        )
        merged = merged[merged['Industry'].str.lower().str.contains(industry_filter, na=False)]
        display_stocks = merged.drop(columns=['Industry'], errors='ignore')
        if not display_leaders.empty and 'Industry' in display_leaders.columns:
            display_leaders = display_leaders[
                display_leaders['Industry'].str.lower().str.contains(industry_filter, na=False)
            ]
        print(f"\n  Filtered to industry: '{args.industry}'")

    # Show Sector Index RS
    print("\n┌─ SECTORAL INDEX RS (vs Nifty 50) ───────────────────────┐")
    if not sector_rs.empty:
        display_cols = ['Rank', 'Sector_Index', 'Return_1M', 'Return_3M', 'Return_6M', 'Composite_RS']
        existing = [c for c in display_cols if c in sector_rs.columns]
        print(sector_rs[existing].to_string(index=False))
    print()

    # Show Top Industries
    print(f"┌─ TOP {config.TOP_INDUSTRIES_COUNT} INDUSTRIES ──────────────────────────────────┐")
    if not industry_rs.empty:
        display_cols = ['Rank', 'Industry', 'Median_RS', 'Pct_Above_70', 'Stock_Count', 'Top_Stock']
        existing = [c for c in display_cols if c in industry_rs.columns]
        print(industry_rs.head(config.TOP_INDUSTRIES_COUNT)[existing].to_string(index=False))
    print()

    # Show Top Stocks
    n = args.top
    print(f"┌─ TOP {n} STOCKS BY RS PERCENTILE ──────────────────────┐")
    if not display_stocks.empty:
        display_cols = ['Ticker', 'Current_Price', 'Pct_From_High', 'Return_3M', 'Return_6M', 'RS_Percentile']
        existing = [c for c in display_cols if c in display_stocks.columns]
        print(display_stocks.head(n)[existing].to_string(index=False))
    print()

    # Show Leaders
    if not display_leaders.empty:
        print(f"┌─ LEADERS IN TOP INDUSTRIES (RS ≥ {config.RS_LEADER_THRESHOLD}) ─────────────┐")
        display_cols = ['Ticker', 'Industry', 'RS_Percentile', 'Return_6M', 'Industry_Rank']
        existing = [c for c in display_cols if c in display_leaders.columns]
        print(display_leaders[existing].to_string(index=False))
        print()


if __name__ == "__main__":
    main()
