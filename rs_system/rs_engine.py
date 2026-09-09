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
        pct_from_high = ((current_price / high_52w) - 1) * 100 if high_52w > 0 else 0
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
            'RS_Composite': rs_composite
        })
        
    res_df = pd.DataFrame(results)
    
    if res_df.empty:
        return pd.DataFrame(columns=[
            'Ticker', 'Current_Price', 'High_52W', 'Pct_From_High', 'Avg_Volume',
            'Return_1W', 'Return_1M', 'Return_3M', 'Return_6M',
            'RS_Composite', 'RS_Percentile'
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
            'RS_Percentile', 'Return_3M', 'Return_6M', 'Avg_Volume', 'Industry_Rank']
    
    # Only return columns that exist (in case of changes)
    existing_cols = [col for col in cols if col in filtered.columns]
    
    return filtered[existing_cols]
