import re

with open('rs_system/rs_engine.py', 'r') as f:
    engine_code = f.read()

# 1. Update calculate_stock_rs to compute VCP metrics
new_calc_logic = """        # 200 SMA
        sma_200 = close_series.rolling(window=200).mean().iloc[-1] if len(close_series) >= 200 else None
        
        # --- VCP / Basing specific metrics ---
        days_since_peak = 0
        max_base_dd = 0.0
        prior_leg_gain = 0.0
        vol_dry_up = False
        
        if len(df) > 80:
            peak_idx = int(df['High'].argmax())
            days_since_peak = len(df) - 1 - peak_idx
            
            if days_since_peak > 0:
                base_low = df['Low'].iloc[peak_idx:].min()
                max_base_dd = ((base_low / high_52w) - 1) * 100 if high_52w > 0 else 0
            else:
                max_base_dd = 0
                
            start_of_run_idx = max(0, peak_idx - 40)
            price_before_run = df['Close'].iloc[start_of_run_idx]
            peak_close = df['Close'].iloc[peak_idx]
            prior_leg_gain = ((peak_close / price_before_run) - 1) * 100 if price_before_run > 0 else 0
            
            # Volume dry up: latest 5 days average volume < 50% of 50-day average volume
            if len(df) >= 50:
                vol_5d = df['Volume'].iloc[-5:].mean()
                vol_50d = df['Volume'].iloc[-50:].mean()
                vol_dry_up = (vol_5d < (vol_50d * 0.6))

        results.append({
            'Ticker': ticker,
            'Current_Price': current_price,
            'High_52W': high_52w,
            'Pct_From_High': pct_from_high,
            'Avg_Volume': avg_volume,
            'Return_1W': r_1w * 100,
            'Return_1M': r_1m * 100,
            'Return_3M': r_3m * 100,
            'Return_6M': r_6m * 100,
            'RS_Composite': rs_composite,
            'EMA_10': ema_10,
            'EMA_20': ema_20,
            'SMA_50': sma_50,
            'SMA_100': sma_100,
            'SMA_200': sma_200,
            'Days_Since_Peak': days_since_peak,
            'Max_Base_DD': max_base_dd,
            'Prior_Leg_Gain': prior_leg_gain,
            'Vol_Dry_Up': vol_dry_up
        })
"""

# Replace the end of calculate_stock_rs
engine_code = re.sub(r'        # 200 SMA\n        sma_200 =.*?\n        results\.append\(\{.*?\n        \}\)', new_calc_logic, engine_code, flags=re.DOTALL)

# Add fallback columns in the empty DataFrame return block of calculate_stock_rs
engine_code = engine_code.replace(
    "'EMA_10', 'EMA_20', 'SMA_50', 'SMA_100', 'SMA_200'", 
    "'EMA_10', 'EMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'Days_Since_Peak', 'Max_Base_DD', 'Prior_Leg_Gain', 'Vol_Dry_Up'"
)

# 2. Update find_basing_stocks
new_basing = """def find_basing_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Finds stocks with strict VCP basing rules (Prior run >30%, duration >40 days, Base DD <25%).\"\"\"
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    # Needs to be a valid stock that has the VCP columns
    if 'Days_Since_Peak' not in merged.columns:
        return pd.DataFrame()
        
    base_cond = (merged['Days_Since_Peak'] >= 40)
    dd_cond = (merged['Max_Base_DD'] >= -25.0) & (merged['Pct_From_High'] >= -25.0)
    prior_leg_cond = (merged['Prior_Leg_Gain'] >= 30.0)
    
    filtered = merged[base_cond & dd_cond & prior_leg_cond].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    return filtered
"""
engine_code = re.sub(r'def find_basing_stocks.*?return filtered\n+', new_basing + '\n', engine_code, flags=re.DOTALL)

# 3. Update find_launch_pad_stocks
new_launchpad = """def find_launch_pad_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    \"\"\"Finds stocks resting on MA clusters (launch pad) with strict VCP basing context.\"\"\"
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    if 'Days_Since_Peak' not in merged.columns:
        return pd.DataFrame()
    
    # Must meet core VCP criteria first (slightly looser for launchpad, e.g. duration >20)
    base_cond = (merged['Days_Since_Peak'] >= 20)
    dd_cond = (merged['Max_Base_DD'] >= -25.0) & (merged['Pct_From_High'] >= -25.0)
    prior_leg_cond = (merged['Prior_Leg_Gain'] >= 30.0)
    
    # Valid MAs
    valid_ma = merged[['EMA_10', 'EMA_20', 'SMA_50', 'SMA_200']].notna().all(axis=1)
    df = merged[base_cond & dd_cond & prior_leg_cond & valid_ma].copy()
    
    if df.empty: return df
    
    # Calculate MA cluster min and max (tightness)
    df['MA_Max'] = df[['EMA_10', 'EMA_20', 'SMA_50']].max(axis=1)
    df['MA_Min'] = df[['EMA_10', 'EMA_20', 'SMA_50']].min(axis=1)
    
    # Bunching condition: Max MA is within 5% of Min MA
    bunching_cond = (df['MA_Max'] / df['MA_Min'] - 1) <= 0.05
    
    # Price resting on the pad
    price_cond = (df['Current_Price'] <= df['MA_Max'] * 1.05) & (df['Current_Price'] >= df['MA_Min'] * 0.98)
    
    # Uptrend condition
    trend_cond = (df['Current_Price'] > df['SMA_200']) & (df['SMA_50'] > df['SMA_200'])
    
    # Require volume contraction
    vol_cond = df['Vol_Dry_Up'] == True
    
    filtered = df[bunching_cond & price_cond & trend_cond & vol_cond].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    # Clean up temp columns
    filtered = filtered.drop(columns=['MA_Max', 'MA_Min'])
    
    return filtered
"""
engine_code = re.sub(r'def find_launch_pad_stocks.*?return filtered\n+', new_launchpad + '\n', engine_code, flags=re.DOTALL)

with open('rs_system/rs_engine.py', 'w') as f:
    f.write(engine_code)

print("rs_engine.py updated successfully.")
