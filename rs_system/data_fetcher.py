import os
import sys
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import warnings
from . import config

warnings.filterwarnings('ignore')

def fetch_universe() -> pd.DataFrame:
    """
    Fetches the full NSE equity universe + industry/sector mapping from TradingView Scanner API.
    
    Returns:
        pd.DataFrame: DataFrame containing universe data.
    """
    url = "https://scanner.tradingview.com/india/scan"
    payload = {
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
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    data = response.json().get('data', [])
    
    rows = [row['d'] for row in data]
    
    df = pd.DataFrame(rows, columns=[
        'Symbol', 'Name', 'Sector', 'Industry', 'Close', 
        'Volume', 'Avg_Volume_10D', 'High_All_Time', 'Market_Cap'
    ])
    
    df['Ticker'] = df['Symbol'] + '.NS'
    
    # Cache the industry mapping
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    df[['Ticker', 'Sector', 'Industry']].to_csv(config.INDUSTRY_MAP_CACHE, index=False)
    
    print(f"Fetched {len(df)} stocks from TradingView universe.")
    return df

def fetch_prices(tickers: list, period: str = '1y', batch_size: int = 80) -> dict:
    """
    Bulk downloads OHLCV data via yfinance in batches.
    
    Args:
        tickers (list): List of ticker symbols to download.
        period (str): Data period to fetch (e.g. '1y').
        batch_size (int): Number of tickers per batch.
        
    Returns:
        dict: A dictionary mapping ticker strings to their OHLCV DataFrames.
    """
    result = {}
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    
    for i in range(total_batches):
        batch_tickers = tickers[i*batch_size : (i+1)*batch_size]
        chunk_str = " ".join(batch_tickers)
        
        success = False
        data = None
        for attempt in range(2):
            try:
                data = yf.download(chunk_str, period=period, progress=False, threads=True, group_by='ticker')
                success = True
                break
            except Exception as e:
                print(f"Batch {i+1} failed: {e}. Retrying in 2s...")
                time.sleep(2)
                
        if not success or data is None or data.empty:
            print(f"Failed to fetch data for batch {i+1}.")
            continue
            
        loaded_count = 0
        if len(batch_tickers) == 1:
            ticker = batch_tickers[0]
            df = data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten the MultiIndex returned by newer yfinance versions
                df.columns = [col[0] for col in df.columns]
            if len(df) >= 100:
                result[ticker] = df
                loaded_count += 1
        else:
            for ticker in batch_tickers:
                if ticker in data:
                    df = data[ticker].dropna(how='all').copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [col[0] for col in df.columns]
                    if len(df) >= 100:
                        result[ticker] = df
                        loaded_count += 1
                        
        print(f"Batch {i+1}/{total_batches} complete ({loaded_count} tickers loaded)")
        
    return result

def fetch_sectoral_indices(period: str = '1y') -> dict:
    """
    Downloads all NSE sectoral index histories.
    
    Returns:
        dict: A dictionary mapping index names to their Close price pd.Series.
    """
    # Use config indices, with fallback if not found
    indices = getattr(config, 'SECTORAL_INDICES', {
        "Nifty Bank": "^NSEBANK",
        "Nifty IT": "^CNXIT",
        "Nifty Auto": "^CNXAUTO",
        "Nifty FMCG": "^CNXFMCG",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty Realty": "^CNXREALTY",
        "Nifty Energy": "^CNXENERGY",
        "Nifty Infra": "^CNXINFRA",
        "Nifty Media": "^CNXMEDIA",
        "Nifty PSU Bank": "^CNXPSUBANK",
        "Nifty Financial Services": "NIFTY_FIN_SERVICE.NS",
        "Nifty Private Bank": "NIFTY_PVT_BANK.NS",
        "Nifty Healthcare": "NIFTY_HEALTHCARE.NS",
        "Nifty Consumer Durables": "NIFTY_CONSR_DURBL.NS",
        "Nifty Oil & Gas": "NIFTY_OIL_AND_GAS.NS",
        "Nifty Commodities": "^CNXCMDT",
        "Nifty Consumption": "^CNXCONSUM",
        "Nifty PSE": "^CNXPSE",
        "Nifty Services": "^CNXSERVICE",
        "Nifty MNC": "^CNXMNC",
    })
    
    result = {}
    for name, ticker in indices.items():
        try:
            data = yf.download(ticker, period=period, progress=False, threads=False)
            if data is not None and not data.empty:
                df = data.copy()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                if 'Close' in df.columns:
                    result[name] = df['Close'].dropna()
        except Exception as e:
            print(f"Failed to fetch index {name} ({ticker}): {e}")
            
    return result

def fetch_benchmark(symbol: str = '^NSEI', period: str = '1y') -> pd.Series:
    """
    Downloads the benchmark (Nifty 50) Close series.
    
    Returns:
        pd.Series: Close prices for the benchmark.
    """
    try:
        data = yf.download(symbol, period=period, progress=False, threads=False)
        if data is not None and not data.empty:
            df = data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
            if 'Close' in df.columns:
                return df['Close'].dropna()
    except Exception as e:
        print(f"Failed to fetch benchmark {symbol}: {e}")
        
    return pd.Series(dtype=float)
