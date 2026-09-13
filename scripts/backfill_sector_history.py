"""
Backfill sector RS history by computing weekly snapshots from 6 months of index price data.
Run once to populate history/sector_rs_history.csv with historical weekly data points.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yfinance as yf
import warnings
from datetime import datetime, timedelta
from rs_system import config

warnings.filterwarnings("ignore")

def main():
    print("Backfilling sector RS history (6 months, weekly snapshots)...")
    
    # Download benchmark (Nifty 50) - 1 year of data to have enough lookback
    bench = yf.download(config.BENCHMARK_SYMBOL, period="1y", progress=False)
    if bench.empty:
        print("Failed to download benchmark. Exiting.")
        return
    
    bench_close = bench['Close']
    if isinstance(bench_close, pd.DataFrame):
        bench_close = bench_close.iloc[:, 0]
    
    # Download all sector indices
    sector_data = {}
    for name, symbol in config.SECTORAL_INDICES.items():
        data = yf.download(symbol, period="1y", progress=False)
        if data is not None and not data.empty:
            close = data['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            sector_data[name] = close
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} (no data)")
    
    print(f"\nLoaded {len(sector_data)} sector indices. Computing weekly snapshots...")
    
    # Generate weekly dates going back 6 months
    end_date = bench_close.index[-1]
    start_date = end_date - timedelta(days=180)
    
    # Get all Fridays (or last trading day of the week)
    all_dates = bench_close.index
    weekly_dates = []
    
    # Group by week and take last date of each week
    for date in all_dates:
        if date >= start_date:
            weekly_dates.append(date)
    
    # Keep only 1 date per week (the last trading day of each week)
    week_groups = {}
    for d in weekly_dates:
        week_key = d.isocalendar()[:2]  # (year, week_number)
        week_groups[week_key] = d
    
    snapshot_dates = sorted(week_groups.values())
    print(f"  Computing RS for {len(snapshot_dates)} weekly snapshots...")
    
    def get_return(series, end_idx, days):
        """Get return ending at end_idx, looking back 'days' trading days."""
        if end_idx < days:
            start_idx = 0
        else:
            start_idx = end_idx - days
        
        end_val = series.iloc[end_idx]
        start_val = series.iloc[start_idx]
        
        if pd.isna(start_val) or start_val == 0:
            return 0.0
        return (end_val / start_val) - 1.0
    
    all_rows = []
    
    for snap_date in snapshot_dates:
        # Find the index position in benchmark for this date
        bench_idx = bench_close.index.get_indexer([snap_date], method='ffill')[0]
        if bench_idx < 0:
            continue
        
        bm_1m = get_return(bench_close, bench_idx, 21)
        bm_3m = get_return(bench_close, bench_idx, 63)
        bm_6m = get_return(bench_close, bench_idx, 126)
        
        sector_scores = []
        
        for name, series in sector_data.items():
            # Find closest date in this sector's data
            valid_dates = series.index[series.index <= snap_date]
            if len(valid_dates) < 21:
                continue
            
            sec_idx = len(valid_dates) - 1
            sec_series = series.loc[valid_dates]
            
            s_1m = get_return(sec_series, sec_idx, 21)
            s_3m = get_return(sec_series, sec_idx, 63)
            s_6m = get_return(sec_series, sec_idx, 126)
            
            spread_1m = (s_1m - bm_1m) * 100
            spread_3m = (s_3m - bm_3m) * 100
            spread_6m = (s_6m - bm_6m) * 100
            
            comp_rs = 0.40 * spread_6m + 0.35 * spread_3m + 0.25 * spread_1m
            
            sector_scores.append({
                'Sector': name,
                'Composite_RS': round(comp_rs, 4),
                'Date': snap_date.strftime('%Y-%m-%d')
            })
        
        # Rank by Composite RS
        sector_scores.sort(key=lambda x: x['Composite_RS'], reverse=True)
        for rank, s in enumerate(sector_scores, 1):
            s['Rank'] = rank
        
        all_rows.extend(sector_scores)
    
    result_df = pd.DataFrame(all_rows)
    
    # Write out
    os.makedirs(config.HISTORY_DIR, exist_ok=True)
    hist_path = os.path.join(config.HISTORY_DIR, 'sector_rs_history.csv')
    result_df.to_csv(hist_path, index=False)
    
    dates_count = result_df['Date'].nunique()
    print(f"\n✓ Backfilled {len(result_df)} rows across {dates_count} weekly snapshots.")
    print(f"  Saved to: {hist_path}")

if __name__ == "__main__":
    main()
