import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add parent directory to path to allow importing rs_system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rs_system import config
from rs_system import data_fetcher
from rs_system import rs_engine

def backfill(weeks_to_backfill=12):
    print("=" * 60)
    print(f"Starting Historical Backfill ({weeks_to_backfill} weeks)")
    print("=" * 60)

    print("\n1. Fetching universe and caching full price data...")
    universe = data_fetcher.fetch_universe()
    
    # Filter universe for speed
    if config.MIN_AVG_VOLUME > 0 and 'Avg_Volume_10D' in universe.columns:
        universe = universe[universe['Avg_Volume_10D'].fillna(0) >= config.MIN_AVG_VOLUME]
    if config.MIN_MARKET_CAP > 0 and 'Market_Cap' in universe.columns:
        universe = universe[universe['Market_Cap'].fillna(0) >= config.MIN_MARKET_CAP]
    universe = universe.reset_index(drop=True)

    tickers = universe['Ticker'].tolist()
    
    # Need 1 year + extra buffer for the oldest backfill date
    # yfinance '2y' gets enough data to simulate 1y back in time 12 weeks ago
    full_prices = data_fetcher.fetch_prices(tickers, period='2y')
    benchmark_series = data_fetcher.fetch_benchmark(period='2y')
    
    history_records = []
    
    # Iterate backwards in time, simulating weekend scans (Fridays)
    today = datetime.now()
    
    for i in range(weeks_to_backfill, 0, -1):
        target_date = today - timedelta(weeks=i)
        
        # Snap to nearest Friday if weekend, just to be consistent
        if target_date.weekday() >= 5:
            target_date = target_date - timedelta(days=target_date.weekday() - 4)
            
        target_date_str = target_date.strftime('%Y-%m-%d')
        print(f"\nProcessing simulated run for: {target_date_str} ({i} weeks ago)")
        
        # 1. Truncate prices to only include data UP TO the target date
        target_ts = pd.Timestamp(target_date)
        
        sim_prices = {}
        for t, df in full_prices.items():
            if not df.empty:
                truncated = df[df.index <= target_ts]
                if len(truncated) >= 126: # Need at least 6 months of history for the RS calc
                    sim_prices[t] = truncated
                    
        sim_bench = benchmark_series[benchmark_series.index <= target_ts]
        
        if len(sim_prices) < 100:
            print(f"Not enough data for {target_date_str}, skipping.")
            continue
            
        # 2. Run engine calculations
        stock_rs = rs_engine.calculate_stock_rs(sim_prices, sim_bench)
        industry_rs = rs_engine.calculate_industry_rs(stock_rs, universe)
        
        # 3. Extract top industries for this week
        for _, row in industry_rs.iterrows():
            history_records.append({
                'Date': target_date_str,
                'Industry': row['Industry'],
                'Rank': row['Rank'],
                'Median_RS': row['Median_RS']
            })
            
    print("\nBackfill complete! Saving to history file...")
    
    history_df = pd.DataFrame(history_records)
    
    # Append to existing history if present
    os.makedirs(config.HISTORY_DIR, exist_ok=True)
    if os.path.exists(config.INDUSTRY_HISTORY_FILE):
        old_hist = pd.read_csv(config.INDUSTRY_HISTORY_FILE)
        # Drop old dates that we just backfilled to avoid duplicates
        backfill_dates = history_df['Date'].unique()
        old_hist = old_hist[~old_hist['Date'].isin(backfill_dates)]
        history_df = pd.concat([old_hist, history_df], ignore_index=True)
        
    history_df.to_csv(config.INDUSTRY_HISTORY_FILE, index=False)
    print(f"Saved {len(history_df)} records to {config.INDUSTRY_HISTORY_FILE}")

if __name__ == "__main__":
    backfill(weeks_to_backfill=8) # 8 weeks is usually enough to see a solid trend
