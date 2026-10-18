import pandas as pd
import numpy as np

# Load raw trades
df = pd.read_csv('raw_trades.csv')
df['trade_date'] = pd.to_datetime(df['trade_date'])

trades_data = []

for isin, group in df.groupby('isin', sort=False):
    symbol = group['symbol'].iloc[0]
    
    buys = group[group['trade_type'].str.lower() == 'buy']
    sells = group[group['trade_type'].str.lower() == 'sell']
    
    qty_bought = buys['quantity'].sum() if not buys.empty else 0
    qty_sold = sells['quantity'].sum() if not sells.empty else 0
    
    buy_value = (buys['quantity'] * buys['price']).sum() if not buys.empty else 0
    sell_value = (sells['quantity'] * sells['price']).sum() if not sells.empty else 0
    
    avg_entry = buy_value / qty_bought if qty_bought > 0 else np.nan
    avg_exit = sell_value / qty_sold if qty_sold > 0 else np.nan
    
    qty_open = qty_bought - qty_sold
    
    first_buy_date = buys['trade_date'].min().strftime('%Y-%m-%d') if not buys.empty else '1899-12-31'
    last_sell_date = sells['trade_date'].max().strftime('%Y-%m-%d') if not sells.empty else '1899-12-31'
    
    pnl = sell_value - (avg_entry * qty_sold) if (qty_bought > 0 and qty_sold > 0) else np.nan
    pnl_pct = pnl / (avg_entry * qty_sold) if (qty_bought > 0 and qty_sold > 0) else np.nan
    
    if not buys.empty and not sells.empty:
        holding_days = (sells['trade_date'].max() - buys['trade_date'].min()).days
    else:
        holding_days = np.nan
        
    if qty_bought == 0 and qty_sold > 0:
        status = 'SELL ONLY'
    elif qty_open == 0:
        status = 'CLOSED'
    elif qty_open > 0:
        status = 'OPEN'
    else:
        status = 'ERROR'
        
    trades_data.append({
        'Trade ID': isin,
        'Symbol': symbol,
        'First Buy Date': first_buy_date,
        'Last Sell Date': last_sell_date,
        'Avg Entry': avg_entry,
        'Avg Exit': avg_exit,
        'Qty Bought': qty_bought,
        'Qty Sold': qty_sold,
        'Qty Open': qty_open,
        'Buy Value': buy_value,
        'Sell Value': sell_value,
        'P&L ₹': pnl,
        'P&L %': pnl_pct,
        'Holding Days': holding_days,
        'Status': status
    })

summary = pd.DataFrame(trades_data)

closed_df = summary[summary['Status'] == 'CLOSED'].copy()
closed_df = closed_df.sort_values(by='Last Sell Date')
closed_df['Result'] = np.where(closed_df['P&L ₹'] > 0, 'WIN', 'LOSS')
closed_df['Cumulative P&L'] = closed_df['P&L ₹'].cumsum()
closed_df['Month'] = pd.to_datetime(closed_df['Last Sell Date']).dt.to_period('M').astype(str)

open_df = summary[summary['Status'] == 'OPEN'].copy()

# Excel writing
with pd.ExcelWriter('Trading_Journal.xlsx', engine='xlsxwriter') as writer:
    summary.to_excel(writer, sheet_name='Trade Summary', index=False)
    closed_df[['Trade ID', 'Symbol', 'First Buy Date', 'Last Sell Date', 'Avg Entry', 'Avg Exit', 'Qty Bought', 'P&L ₹', 'P&L %', 'Holding Days', 'Result', 'Cumulative P&L', 'Month']].to_excel(writer, sheet_name='Closed Trades', index=False)
    open_df[['Trade ID', 'Symbol', 'First Buy Date', 'Avg Entry', 'Qty Open', 'Buy Value']].to_excel(writer, sheet_name='Open Positions', index=False)
    
    # Dashboard
    total_closed = len(closed_df)
    wins = len(closed_df[closed_df['Result'] == 'WIN'])
    losses = len(closed_df[closed_df['Result'] == 'LOSS'])
    win_rate = wins / total_closed if total_closed else 0
    total_pnl = closed_df['P&L ₹'].sum()
    avg_pnl = closed_df['P&L ₹'].mean()
    
    dashboard_data = {
        'Metric': ['Total Closed Trades', 'Wins', 'Losses', 'Win Rate', 'Total P&L ₹', 'Average P&L/Trade'],
        'Value': [total_closed, wins, losses, win_rate, total_pnl, avg_pnl]
    }
    pd.DataFrame(dashboard_data).to_excel(writer, sheet_name='Dashboard', index=False)

print("Created Trading_Journal.xlsx")
