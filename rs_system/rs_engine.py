"""
rs_engine.py

Core Relative Strength (RS) calculation engine for the automated RS stock screening system.
"""

import pandas as pd
import numpy as np

# Fallback in case MIN_INDUSTRY_STOCKS is not found in config
try:
    from . import config
    MIN_INDUSTRY_STOCKS = getattr(config, 'MIN_INDUSTRY_STOCKS', 3)
except ImportError:
    MIN_INDUSTRY_STOCKS = 3


def calculate_stock_rs(prices: dict, benchmark: pd.Series) -> pd.DataFrame:
    """
    Calculates RS percentile rating for every stock in the given prices dictionary.
    
    Args:
        prices: dict of {ticker: DataFrame} with OHLCV columns
        benchmark: pd.Series of benchmark (e.g. Nifty 50) Close prices
        
    Returns:
        pd.DataFrame with RS percentiles and return metrics, sorted by RS_Percentile descending.
    """
    results = []
    
    # Optional: Calculate benchmark returns if RS spread is needed
    # (RS spread vs Nifty wasn't in required columns, but could be useful)
    
    for ticker, df in prices.items():
        if df is None or df.empty or 'Close' not in df.columns or 'High' not in df.columns or 'Volume' not in df.columns:
            continue
            
        current_price = df['Close'].iloc[-1]
        high_52w = df['High'].max()
        low_52w = df['Low'].min()
        pct_from_high = ((current_price / high_52w) - 1) * 100 if high_52w > 0 else 0
        pct_from_low = ((current_price / low_52w) - 1) * 100 if low_52w > 0 else 0
        avg_volume = df['Volume'].mean()
        
        # Helper to compute returns
        def get_return(days):
            if len(df) > days:
                past_close = df['Close'].iloc[-days-1]
            elif len(df) > 1:
                past_close = df['Close'].iloc[0]
            else:
                past_close = current_price
                
            if past_close == 0 or pd.isna(past_close):
                return 0.0
            return (current_price / past_close) - 1.0
            
        r_6m = get_return(126)
        r_3m = get_return(63)
        r_1m = get_return(21)
        r_1w = get_return(5)
        
        # Composite RS formula
        rs_composite = 0.40 * r_6m + 0.30 * r_3m + 0.20 * r_1m + 0.10 * r_1w
        
        # Moving Averages calculations
        close_series = df['Close'].dropna()
        
        # 10 SMA
        sma_10 = close_series.rolling(window=10).mean().iloc[-1] if len(close_series) >= 10 else None
        # 10 EMA
        ema_10 = close_series.ewm(span=10, adjust=False).mean().iloc[-1] if len(close_series) >= 10 else None
        # 20 EMA
        ema_20 = close_series.ewm(span=20, adjust=False).mean().iloc[-1] if len(close_series) >= 20 else None
        # 50 SMA
        sma_50 = close_series.rolling(window=50).mean().iloc[-1] if len(close_series) >= 50 else None
        # 50 SMA 10 days ago (for slope)
        sma_50_past = close_series.rolling(window=50).mean().iloc[-11] if len(close_series) >= 61 else None
        sma_50_rising = (sma_50 >= sma_50_past) if (sma_50 is not None and sma_50_past is not None) else False

        # 100 SMA
        sma_100 = close_series.rolling(window=100).mean().iloc[-1] if len(close_series) >= 100 else None
        # 200 SMA
        sma_200 = close_series.rolling(window=200).mean().iloc[-1] if len(close_series) >= 200 else None
        # 200 SMA 20 days ago (for slope)
        sma_200_past = close_series.rolling(window=200).mean().iloc[-21] if len(close_series) >= 221 else None
        sma_200_rising = (sma_200 >= sma_200_past) if (sma_200 is not None and sma_200_past is not None) else False
        
        # Check 10 SMA Reclaim in the last 5 days:
        # Currently above 10 SMA, but was below (or equal to) 10 SMA at least once in the last 5 bars
        reclaimed_10_sma = False
        if len(close_series) >= 15:
            sma_10_series = close_series.rolling(window=10).mean()
            last_5_close = close_series.iloc[-5:]
            last_5_sma10 = sma_10_series.iloc[-5:]
            if current_price > sma_10_series.iloc[-1]:
                # was below or touched SMA 10 in the last 5 days
                if (last_5_close <= last_5_sma10).any():
                    reclaimed_10_sma = True

        # --- VCP / Basing specific metrics ---
        days_since_peak = 0
        max_base_dd = 0.0
        prior_leg_gain = 0.0
        vol_dry_up = False
        listing_bars = len(df)
        listing_day_low = df['Low'].iloc[0] if len(df) > 0 else 0
        
        base_low_price = current_price
        if len(df) >= 15:
            peak_idx = int(df['High'].argmax())
            days_since_peak = len(df) - 1 - peak_idx
            
            if days_since_peak > 0:
                base_low_price = df['Low'].iloc[peak_idx:].min()
                max_base_dd = ((base_low_price / high_52w) - 1) * 100 if high_52w > 0 else 0
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

        # --- Gap Analysis Metrics (Last 10 bars) ---
        has_breakaway_gap = False
        gap_days_ago = -1
        gap_pct = 0.0
        gap_day_low = 0.0
        gap_rvol = 0.0
        is_gap_and_hold = False
        is_ipo_gap = False

        if len(df) >= 15:
            # Check for gap occurrence in recent 10 bars (from bar -1 to bar -10)
            # A gap up occurs when Open[i] >= High[i-1] * 1.015 or Open[i] >= Close[i-1] * 1.025
            vol_50_series = df['Volume'].rolling(window=min(len(df), 50), min_periods=10).mean()
            
            # Scan from most recent bar backwards
            lookback_gap = min(10, len(df) - 1)
            for i in range(1, lookback_gap + 1):
                idx = len(df) - i
                prev_idx = idx - 1
                
                bar_open = df['Open'].iloc[idx]
                bar_close = df['Close'].iloc[idx]
                bar_high = df['High'].iloc[idx]
                bar_low = df['Low'].iloc[idx]
                bar_vol = df['Volume'].iloc[idx]
                
                prev_close = df['Close'].iloc[prev_idx]
                prev_high = df['High'].iloc[prev_idx]
                
                avg_v = vol_50_series.iloc[prev_idx] if prev_idx < len(vol_50_series) else df['Volume'].mean()
                if avg_v <= 0 or pd.isna(avg_v):
                    avg_v = 1.0
                rvol = bar_vol / avg_v
                
                calc_gap = ((bar_open / prev_close) - 1) * 100 if prev_close > 0 else 0
                
                # Gap Up Criteria:
                # 1. Gap size >= 2.5% (Open vs prev Close) or Open > prev High
                # 2. Volume expansion: RVOL >= 1.8x
                # 3. Closed well: Close >= Open * 0.985 and Close > prev_close
                if calc_gap >= 2.5 and rvol >= 1.8 and bar_close > prev_close and (bar_high > bar_low):
                    bar_candle_pct = (bar_close - bar_low) / (bar_high - bar_low)
                    if bar_candle_pct >= 0.40: # closed in upper 60% of day's range
                        gap_days_ago = i - 1  # 0 means today, 1 means yesterday, etc.
                        gap_pct = calc_gap
                        gap_day_low = bar_low
                        gap_rvol = rvol
                        
                        # Breakaway Gap: happened in last 2 days (today or yesterday)
                        if gap_days_ago <= 1:
                            has_breakaway_gap = True
                            
                        # Gap & Hold: happened 2 to 10 days ago, and price has NOT undercut gap day low
                        if gap_days_ago >= 2:
                            subsequent_low = df['Low'].iloc[idx:].min()
                            # Holds above gap day low (or within 1% buffer)
                            if subsequent_low >= gap_day_low * 0.99 and current_price >= gap_day_low:
                                is_gap_and_hold = True
                                
                        # IPO Gap: Listing bars 15 to 150, gap happened within last 10 days
                        if 15 <= listing_bars <= 150 and (has_breakaway_gap or is_gap_and_hold):
                            is_ipo_gap = True
                            
                        break # Found most recent prominent gap

        results.append({
            'Ticker': ticker,
            'Current_Price': current_price,
            'High_52W': high_52w,
            'Low_52W': low_52w,
            'Pct_From_High': pct_from_high,
            'Pct_From_Low': pct_from_low,
            'Avg_Volume': avg_volume,
            'Return_1W': r_1w * 100,
            'Return_1M': r_1m * 100,
            'Return_3M': r_3m * 100,
            'Return_6M': r_6m * 100,
            'RS_Composite': rs_composite,
            'SMA_10': sma_10,
            'EMA_10': ema_10,
            'EMA_20': ema_20,
            'SMA_50': sma_50,
            'SMA_100': sma_100,
            'SMA_200': sma_200,
            'SMA_50_Rising': sma_50_rising,
            'SMA_200_Rising': sma_200_rising,
            'Base_Low_Price': base_low_price,
            'Listing_Bars': listing_bars,
            'Listing_Day_Low': listing_day_low,
            'Reclaimed_10_SMA': reclaimed_10_sma,
            'Days_Since_Peak': days_since_peak,
            'Max_Base_DD': max_base_dd,
            'Prior_Leg_Gain': prior_leg_gain,
            'Vol_Dry_Up': vol_dry_up,
            'Has_Breakaway_Gap': has_breakaway_gap,
            'Is_Gap_And_Hold': is_gap_and_hold,
            'Is_IPO_Gap': is_ipo_gap,
            'Gap_Days_Ago': gap_days_ago,
            'Gap_Pct': gap_pct,
            'Gap_Day_Low': gap_day_low,
            'Gap_RVOL': gap_rvol
        })

        
    res_df = pd.DataFrame(results)
    
    if res_df.empty:
        return pd.DataFrame(columns=[
            'Ticker', 'Current_Price', 'High_52W', 'Low_52W', 'Pct_From_High', 'Pct_From_Low', 'Avg_Volume',
            'Return_1W', 'Return_1M', 'Return_3M', 'Return_6M',
            'RS_Composite', 'RS_Percentile',
            'SMA_10', 'EMA_10', 'EMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'SMA_50_Rising', 'SMA_200_Rising', 'Base_Low_Price', 'Listing_Bars', 'Listing_Day_Low', 'Reclaimed_10_SMA', 'Days_Since_Peak', 'Max_Base_DD', 'Prior_Leg_Gain', 'Vol_Dry_Up',
            'Has_Breakaway_Gap', 'Is_Gap_And_Hold', 'Is_IPO_Gap', 'Gap_Days_Ago', 'Gap_Pct', 'Gap_Day_Low', 'Gap_RVOL'
        ])
        
    # Rank and calculate percentile (0-99)
    res_df['RS_Percentile'] = res_df['RS_Composite'].rank(pct=True) * 99
    res_df['RS_Percentile'] = res_df['RS_Percentile'].fillna(0).round().astype(int)
    
    res_df = res_df.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    return res_df


def calculate_industry_rs(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates stock-level RS into industry rankings.
    
    Args:
        stock_rs: DataFrame from calculate_stock_rs
        universe: DataFrame from data_fetcher.fetch_universe (has Ticker, Sector, Industry)
        
    Returns:
        pd.DataFrame with industry RS rankings and statistics.
    """
    if stock_rs.empty or universe.empty:
        return pd.DataFrame(columns=[
            'Rank', 'Industry', 'Sector', 'Median_RS', 'Mean_RS', 'Pct_Above_70', 'Pct_Near_High',
            'Stock_Count', 'Top_Stock', 'Top_Stock_RS', 'Industry_Rank_Score'
        ])
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    industry_data = []
    
    for industry, group in merged.groupby('Industry'):
        stock_count = len(group)
        if stock_count < MIN_INDUSTRY_STOCKS:
            continue
            
        median_rs = group['RS_Percentile'].median()
        mean_rs = group['RS_Percentile'].mean()
        pct_above_70 = (group['RS_Percentile'] >= 70).mean() * 100
        pct_near_high = (group['Pct_From_High'] >= -10).mean() * 100
        
        sector_mode = group['Sector'].mode()
        sector = sector_mode.iloc[0] if not sector_mode.empty else group['Sector'].iloc[0]
        
        top_stock_idx = group['RS_Percentile'].idxmax()
        top_stock = group.loc[top_stock_idx, 'Ticker']
        top_stock_rs = group.loc[top_stock_idx, 'RS_Percentile']
        
        industry_rank_score = 0.50 * median_rs + 0.30 * pct_above_70 + 0.20 * pct_near_high
        
        industry_data.append({
            'Industry': industry,
            'Sector': sector,
            'Median_RS': median_rs,
            'Mean_RS': mean_rs,
            'Pct_Above_70': pct_above_70,
            'Pct_Near_High': pct_near_high,
            'Stock_Count': stock_count,
            'Top_Stock': top_stock,
            'Top_Stock_RS': top_stock_rs,
            'Industry_Rank_Score': industry_rank_score
        })
        
    ind_df = pd.DataFrame(industry_data)
    
    if ind_df.empty:
        return pd.DataFrame(columns=[
            'Rank', 'Industry', 'Sector', 'Median_RS', 'Mean_RS', 'Pct_Above_70', 'Pct_Near_High',
            'Stock_Count', 'Top_Stock', 'Top_Stock_RS', 'Industry_Rank_Score'
        ])
        
    ind_df = ind_df.sort_values(by='Industry_Rank_Score', ascending=False).reset_index(drop=True)
    ind_df.insert(0, 'Rank', ind_df.index + 1)
    
    return ind_df


def calculate_sector_index_rs(sector_prices: dict, benchmark: pd.Series) -> pd.DataFrame:
    """
    Direct RS comparison of NSE sectoral indices vs Nifty 50.
    
    Args:
        sector_prices: dict of {index_name: close_series}
        benchmark: pd.Series of Nifty 50 Close
        
    Returns:
        pd.DataFrame with sectoral index rankings based on relative strength vs benchmark.
    """
    if benchmark.empty:
        return pd.DataFrame(columns=[
            'Rank', 'Sector_Index', 'Return_1M', 'Return_3M', 'Return_6M',
            'RS_Spread_1M', 'RS_Spread_3M', 'RS_Spread_6M', 'Composite_RS'
        ])
        
    def get_returns(series):
        if series.empty:
            return pd.Series({'1M': 0.0, '3M': 0.0, '6M': 0.0})
        current = series.iloc[-1]
        
        def r(days):
            if len(series) > days:
                past = series.iloc[-days-1]
            elif len(series) > 1:
                past = series.iloc[0]
            else:
                past = current
            if past == 0 or pd.isna(past): return 0.0
            return (current / past) - 1.0
            
        return pd.Series({'1M': r(21), '3M': r(63), '6M': r(126)})
        
    bm_ret = get_returns(benchmark)
    
    res = []
    for sec, series in sector_prices.items():
        if series is None or series.empty:
            continue
            
        sec_ret = get_returns(series)
        
        # Calculate Outperformance Spread vs Benchmark (%)
        spread_1m = (sec_ret['1M'] - bm_ret['1M']) * 100
        spread_3m = (sec_ret['3M'] - bm_ret['3M']) * 100
        spread_6m = (sec_ret['6M'] - bm_ret['6M']) * 100
        
        # Sector Composite RS
        comp_rs = 0.40 * spread_6m + 0.35 * spread_3m + 0.25 * spread_1m
        
        res.append({
            'Sector_Index': sec,
            'Return_1M': sec_ret['1M'] * 100,
            'Return_3M': sec_ret['3M'] * 100,
            'Return_6M': sec_ret['6M'] * 100,
            'RS_Spread_1M': spread_1m,
            'RS_Spread_3M': spread_3m,
            'RS_Spread_6M': spread_6m,
            'Composite_RS': comp_rs
        })
        
    df = pd.DataFrame(res)
    
    if df.empty:
        return pd.DataFrame(columns=[
            'Rank', 'Sector_Index', 'Return_1M', 'Return_3M', 'Return_6M',
            'RS_Spread_1M', 'RS_Spread_3M', 'RS_Spread_6M', 'Composite_RS'
        ])
        
    df = df.sort_values(by='Composite_RS', ascending=False).reset_index(drop=True)
    df.insert(0, 'Rank', df.index + 1)
    
    return df


def find_leaders_in_leading_groups(stock_rs: pd.DataFrame, industry_rs: pd.DataFrame, universe: pd.DataFrame, 
                                  top_n_industries: int = 15, min_rs: int = 80) -> pd.DataFrame:
    """
    Finds the strongest stocks within the strongest industries.
    
    Args:
        stock_rs: DataFrame from calculate_stock_rs
        industry_rs: DataFrame from calculate_industry_rs
        universe: DataFrame with Universe data
        top_n_industries: number of top industries to consider
        min_rs: minimum RS percentile a stock must have to be considered a leader
        
    Returns:
        pd.DataFrame containing the leading stocks in the leading industries.
    """
    if industry_rs.empty or stock_rs.empty or universe.empty:
        return pd.DataFrame(columns=[
            'Ticker', 'Industry', 'Sector', 'Current_Price', 'High_52W', 'Pct_From_High', 
            'RS_Percentile', 'Return_3M', 'Return_6M', 'Avg_Volume', 'Industry_Rank'
        ])
        
    top_inds = industry_rs.head(top_n_industries)[['Industry', 'Rank']].rename(columns={'Rank': 'Industry_Rank'})
    
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    merged = merged.merge(top_inds, on='Industry', how='inner')
    
    filtered = merged[merged['RS_Percentile'] >= min_rs]
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    cols = ['Ticker', 'Industry', 'Sector', 'Current_Price', 'High_52W', 'Pct_From_High', 
            'Return_3M', 'Return_6M', 'RS_Percentile', 'Industry_Rank', 'Avg_Volume',
            'EMA_10', 'EMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'Days_Since_Peak', 'Max_Base_DD', 'Prior_Leg_Gain', 'Vol_Dry_Up']
    
    # Only return columns that exist (in case of changes)
    existing_cols = [col for col in cols if col in filtered.columns]
    
    return filtered[existing_cols]

def find_basing_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Finds stocks consolidating in constructive Stage 2 bases."""
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    if 'Days_Since_Peak' not in merged.columns:
        return pd.DataFrame()
        
    # Valid MAs check
    valid_ma = merged[['SMA_50', 'SMA_200']].notna().all(axis=1)
    df = merged[valid_ma].copy()
    if df.empty:
        return df

    # Stage 2 Trend Template:
    # 1. Moving Average Alignment: Current Price > 50 SMA > 200 SMA
    ma_align = (df['Current_Price'] > df['SMA_50']) & (df['SMA_50'] > df['SMA_200'])
    
    # 2. Upward Trend Slopes: 200 SMA and 50 SMA rising
    rising_ma = (df['SMA_200_Rising'] == True) & (df['SMA_50_Rising'] == True)
    
    # 3. Base support: Base low must not violate deeply below the 200 SMA (support respected)
    base_floor = df['Base_Low_Price'] >= (df['SMA_200'] * 0.95)
    
    # 4. Above 52W low by at least 25%
    low_clearance = df['Pct_From_Low'] >= 25.0
    
    # 5. Base context: 25-150 days consolidation, max drawdown <= 35%, within 35% of 52W high
    base_cond = (df['Days_Since_Peak'] >= 25) & (df['Days_Since_Peak'] <= 150)
    dd_cond = (df['Max_Base_DD'] >= -35.0) & (df['Pct_From_High'] >= -35.0)
    
    # 6. Prior momentum
    prior_leg_cond = (df['Prior_Leg_Gain'] >= 25.0) | (df['Return_3M'] >= 25.0) | (df['Return_6M'] >= 25.0)
    
    filtered = df[ma_align & rising_ma & base_floor & low_clearance & base_cond & dd_cond & prior_leg_cond].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    return filtered


def find_reclaimed_10_sma_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Finds Stage 2 stocks that consolidated for >=15 bars and reclaimed their 10-day SMA in the last 5 days.
    """
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    if 'Reclaimed_10_SMA' not in merged.columns or 'Days_Since_Peak' not in merged.columns:
        return pd.DataFrame()
        
    # Valid MAs check
    valid_ma = merged[['SMA_10', 'SMA_50', 'SMA_200']].notna().all(axis=1)
    df = merged[valid_ma].copy()
    if df.empty:
        return df

    # 1. Reclaimed 10 SMA in the last 5 days
    reclaim_cond = df['Reclaimed_10_SMA'] == True
    
    # 2. Stage 2 Trend Template:
    # Current Price > 50 SMA > 200 SMA
    ma_align = (df['Current_Price'] > df['SMA_50']) & (df['SMA_50'] > df['SMA_200'])
    # 200 SMA rising
    rising_ma = df['SMA_200_Rising'] == True
    # Base low respecting 200 SMA
    base_floor = df['Base_Low_Price'] >= (df['SMA_200'] * 0.95)
    # Above 52W low by >= 25%
    low_clearance = df['Pct_From_Low'] >= 25.0
    # Prior uptrend / momentum
    prior_cond = (df['Prior_Leg_Gain'] >= 25.0) | (df['Return_3M'] >= 25.0) | (df['Return_6M'] >= 25.0)
    
    # 3. Consolidation: >= 15 bars, max depth up to 35%
    base_cond = (df['Days_Since_Peak'] >= 15) & (df['Days_Since_Peak'] <= 150)
    dd_cond = (df['Max_Base_DD'] >= -35.0) & (df['Pct_From_High'] >= -35.0)
    
    filtered = df[reclaim_cond & ma_align & rising_ma & base_floor & low_clearance & prior_cond & base_cond & dd_cond].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    return filtered


def find_ipo_reclaimed_10_sma_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Finds newly listed / IPO stocks (15 to 150 trading days history) that consolidated and reclaimed their 10 SMA.
    """
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    if 'Reclaimed_10_SMA' not in merged.columns or 'Listing_Bars' not in merged.columns:
        return pd.DataFrame()
        
    # Check valid 10 SMA
    valid_ma = merged['SMA_10'].notna()
    df = merged[valid_ma].copy()
    if df.empty:
        return df

    # 1. IPO Listing Age: between 15 and 150 trading days
    ipo_age = (df['Listing_Bars'] >= 15) & (df['Listing_Bars'] <= 150)
    
    # 2. Reclaimed 10 SMA in the last 5 days
    reclaim_cond = df['Reclaimed_10_SMA'] == True
    
    # 3. IPO Support & Trend:
    # - Price above listing day low (no broken IPOs)
    floor_cond = df['Current_Price'] >= df['Listing_Day_Low']
    # - If 20 EMA is available, Price > 20 EMA
    ema20_cond = df['EMA_20'].isna() | (df['Current_Price'] >= df['EMA_20'])
    # - If 50 SMA is available, Price > 50 SMA
    sma50_cond = df['SMA_50'].isna() | (df['Current_Price'] >= df['SMA_50'])
    
    # 4. Prior IPO Run-Up / Demand: gained >= 15% from listing low to high OR from recent low
    momentum_cond = (df['Pct_From_Low'] >= 15.0) | (df['Prior_Leg_Gain'] >= 15.0) | (df['Return_1M'] >= 10.0)
    
    # 5. Consolidation: >= 8 bars base, max depth <= 35%
    base_cond = (df['Days_Since_Peak'] >= 8) & (df['Days_Since_Peak'] <= 120)
    dd_cond = (df['Max_Base_DD'] >= -35.0) & (df['Pct_From_High'] >= -35.0)
    
    filtered = df[ipo_age & reclaim_cond & floor_cond & ema20_cond & sma50_cond & momentum_cond & base_cond & dd_cond].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    
    return filtered


def find_launch_pad_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """Finds Stage 2 stocks resting on tight MA clusters with 10 EMA above 20 EMA near 50 SMA."""
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    
    if 'Days_Since_Peak' not in merged.columns:
        return pd.DataFrame()
    
    # Valid MAs
    valid_ma = merged[['EMA_10', 'EMA_20', 'SMA_50', 'SMA_200']].notna().all(axis=1)
    df = merged[valid_ma].copy()
    if df.empty:
        return df

    # 1. 10 EMA above 20 EMA
    ema_cond = df['EMA_10'] >= df['EMA_20']

    # 2. Tightness with 50 SMA (MA cluster within 8%)
    df['MA_Max'] = df[['EMA_10', 'EMA_20', 'SMA_50']].max(axis=1)
    df['MA_Min'] = df[['EMA_10', 'EMA_20', 'SMA_50']].min(axis=1)
    bunching_cond = (df['MA_Max'] / df['MA_Min'] - 1) <= 0.08

    # 3. Price near the MA cluster
    price_cond = (df['Current_Price'] >= df['MA_Min'] * 0.96) & (df['Current_Price'] <= df['MA_Max'] * 1.08)

    # 4. Stage 2 Trend Template:
    # 50 SMA > 200 SMA and Price > 200 SMA
    ma_align = (df['Current_Price'] > df['SMA_200']) & (df['SMA_50'] > df['SMA_200'])
    # 200 SMA rising
    rising_ma = df['SMA_200_Rising'] == True
    # Base low respecting 200 SMA
    base_floor = df['Base_Low_Price'] >= (df['SMA_200'] * 0.95)
    # Above 52W low by >= 25%
    low_clearance = df['Pct_From_Low'] >= 25.0

    # 5. Base context
    base_days = (df['Days_Since_Peak'] >= 15) & (df['Days_Since_Peak'] <= 150)
    dd_cond = (df['Max_Base_DD'] >= -30.0) & (df['Pct_From_High'] >= -25.0)

    # 6. Prior trend / momentum
    prior_cond = (df['Prior_Leg_Gain'] >= 25.0) | (df['Return_3M'] >= 25.0) | (df['Return_6M'] >= 25.0)

    filtered = df[ema_cond & bunching_cond & price_cond & ma_align & rising_ma & base_floor & low_clearance & base_days & dd_cond & prior_cond].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)

    filtered = filtered.drop(columns=['MA_Max', 'MA_Min'])
    return filtered


def find_breakaway_gap_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Finds High Volume Breakaway / Institutional Gap Up stocks (occurred today or yesterday).
    Criteria:
    - Gap up >= 2.5% on Day 1
    - Relative Volume >= 1.8x
    - In an uptrend or Stage 2 structure: Price > 50 SMA (or within 2%), Price > 200 SMA (if available)
    - Within 25% of 52-week high (not a deep downtrend dead-cat bounce)
    """
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    if 'Has_Breakaway_Gap' not in merged.columns:
        return pd.DataFrame()
        
    df = merged[merged['Has_Breakaway_Gap'] == True].copy()
    if df.empty:
        return df
        
    # Trend alignment: Above or within 2% of 50 SMA
    trend_50 = df['SMA_50'].isna() | (df['Current_Price'] >= df['SMA_50'] * 0.98)
    # Above 200 SMA if available
    trend_200 = df['SMA_200'].isna() | (df['Current_Price'] >= df['SMA_200'] * 0.95)
    # Proximity to 52W high: within 28% of 52W high
    near_high = df['Pct_From_High'] >= -28.0
    
    filtered = df[trend_50 & trend_200 & near_high].copy()
    filtered = filtered.sort_values(by=['Gap_Days_Ago', 'Gap_RVOL'], ascending=[True, False]).reset_index(drop=True)
    return filtered


def find_gap_and_hold_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Finds stocks that had a high-volume gap up 2 to 10 trading days ago and are now
    orderly consolidating/holding above the gap-day low.
    """
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    if 'Is_Gap_And_Hold' not in merged.columns:
        return pd.DataFrame()
        
    df = merged[merged['Is_Gap_And_Hold'] == True].copy()
    if df.empty:
        return df
        
    # Above 50 SMA and 200 SMA
    trend_50 = df['SMA_50'].isna() | (df['Current_Price'] >= df['SMA_50'] * 0.98)
    trend_200 = df['SMA_200'].isna() | (df['Current_Price'] >= df['SMA_200'] * 0.95)
    near_high = df['Pct_From_High'] >= -25.0
    
    filtered = df[trend_50 & trend_200 & near_high].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    return filtered


def find_ipo_gap_stocks(stock_rs: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    """
    Finds IPO / recent listing stocks (15 to 150 trading days) with an institutional gap up.
    """
    if stock_rs.empty or universe.empty:
        return pd.DataFrame()
        
    merged = stock_rs.merge(universe[['Ticker', 'Sector', 'Industry']], on='Ticker', how='inner')
    if 'Is_IPO_Gap' not in merged.columns:
        return pd.DataFrame()
        
    df = merged[merged['Is_IPO_Gap'] == True].copy()
    if df.empty:
        return df
        
    # IPO Listing Age & support
    ipo_age = (df['Listing_Bars'] >= 15) & (df['Listing_Bars'] <= 150)
    floor_cond = df['Current_Price'] >= df['Listing_Day_Low']
    near_high = df['Pct_From_High'] >= -25.0
    
    filtered = df[ipo_age & floor_cond & near_high].copy()
    filtered = filtered.sort_values(by='RS_Percentile', ascending=False).reset_index(drop=True)
    return filtered
