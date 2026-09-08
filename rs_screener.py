import pandas as pd
import yfinance as yf
import argparse
import sys
import warnings
import os

# Suppress pandas/yfinance warnings for clean CLI output
warnings.filterwarnings("ignore")

def main():
    parser = argparse.ArgumentParser(description="Relative Strength Swing Trading Screener")
    parser.add_argument("csv_file", help="Path to the weekly CSV file containing tickers (e.g., 'Up on the day_2026-09-06.csv')")
    args = parser.parse_args()

    if not os.path.exists(args.csv_file):
        print(f"Error: Could not find the file '{args.csv_file}'. Please check the path.")
        sys.exit(1)

    try:
        df = pd.read_csv(args.csv_file)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    # Automatically identify the column that contains the tickers
    ticker_col = None
    for col in df.columns:
        if col.strip().lower() in ['symbol', 'ticker', 'scrip']:
            ticker_col = col
            break
    if not ticker_col:
        ticker_col = df.columns[0]
        print(f"No 'Symbol' or 'Ticker' column found. Assuming the first column '{ticker_col}' contains the tickers.")

    raw_tickers = df[ticker_col].dropna().astype(str).tolist()
    
    # Clean tickers and append .NS (National Stock Exchange of India) if not present
    tickers = []
    for t in raw_tickers:
        t_clean = t.strip().upper()
        if not t_clean.endswith('.NS') and not t_clean.endswith('.BO'):
            t_clean += '.NS'
        tickers.append(t_clean)
        
    print(f"Found {len(tickers)} tickers in the file.")
    print("Fetching benchmark data for Nifty 50 (^NSEI)...")
    
    bench_data = yf.download("^NSEI", period="1y", progress=False)
    if bench_data.empty:
        print("Failed to download benchmark data (^NSEI). Please check your internet connection. Exiting.")
        sys.exit(1)
        
    # Calculate Benchmark 6-month return (approx 126 trading days)
    bench_len = len(bench_data)
    idx = -126 if bench_len >= 126 else 0
    
    close_col_bench = bench_data['Close'] if isinstance(bench_data['Close'], pd.Series) else bench_data['Close'].iloc[:, 0]
    bench_6m_ret = (float(close_col_bench.iloc[-1]) / float(close_col_bench.iloc[idx])) - 1

    results = []
    
    print(f"Evaluating {len(tickers)} stocks against your setup criteria...")
    print("Criteria: >=30% prior run, >=40 days consolidation, <=25% base drawdown.")
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            print(f"Processed {i + 1}/{len(tickers)} stocks...")
            
        try:
            # Fetch 1 year of daily data
            data = yf.download(ticker, period="1y", progress=False)
            
            # Skip if we don't have enough data (need at least ~4 months to form setup)
            if data.empty or len(data) < 80:
                continue
                
            close_col = data['Close'] if isinstance(data['Close'], pd.Series) else data['Close'].iloc[:, 0]
            high_col = data['High'] if isinstance(data['High'], pd.Series) else data['High'].iloc[:, 0]
            low_col = data['Low'] if isinstance(data['Low'], pd.Series) else data['Low'].iloc[:, 0]

            current_price = float(close_col.iloc[-1])
            high_52w = float(high_col.max())
            
            # 1. CURRENT PRICE DRAWDOWN CHECK (Max 25%)
            if current_price < high_52w * 0.75:
                continue
                
            # Find the index/day the stock hit its peak
            peak_idx = int(high_col.argmax())
            
            # 2. CONSOLIDATION DURATION CHECK (>= 40 trading days)
            days_since_peak = len(data) - 1 - peak_idx
            if days_since_peak < 40:
                continue
                
            # 3. BASE DEPTH CHECK (MAX 25% DD from Peak)
            base_low = float(low_col.iloc[peak_idx:].min())
            if base_low < high_52w * 0.75:
                continue
                
            # 4. PRIOR LEG UP CHECK (>= 30% run in 40 days prior to peak)
            start_of_run_idx = max(0, peak_idx - 40)
            price_before_run = float(close_col.iloc[start_of_run_idx])
            peak_close = float(close_col.iloc[peak_idx])
            
            prior_leg_gain = (peak_close - price_before_run) / price_before_run
            if prior_leg_gain < 0.30:
                continue
                
            # 5. RELATIVE STRENGTH (RS) CALCULATION (6-month outperformance spread vs Nifty)
            stock_idx = -126 if len(data) >= 126 else 0
            stock_6m_ret = (current_price / float(close_col.iloc[stock_idx])) - 1
            rs_rating = stock_6m_ret - bench_6m_ret
            
            results.append({
                'Ticker': ticker,
                'Current Price': round(current_price, 2),
                '52W High': round(high_52w, 2),
                'Days Since Peak': days_since_peak,
                'Max Base DD %': round(((high_52w - base_low) / high_52w) * 100, 2),
                'Prior Leg Gain %': round(prior_leg_gain * 100, 2),
                'RS vs Nifty (6m) %': round(rs_rating * 100, 2)
            })
            
        except Exception as e:
            continue
            
    print("-" * 50)
    if not results:
        print("\nNo stocks matched your strict swing trading criteria today.")
    else:
        results_df = pd.DataFrame(results)
        # Rank by Relative Strength
        results_df = results_df.sort_values('RS vs Nifty (6m) %', ascending=False)
        
        output_file = args.csv_file.replace('.csv', '_Filtered_Setups.csv')
        results_df.to_csv(output_file, index=False)
        print(f"\nSuccess! Found {len(results_df)} matching setups.")
        print(f"Results saved to: {output_file}\n")
        print("Top 10 Setups by Relative Strength:")
        print(results_df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
