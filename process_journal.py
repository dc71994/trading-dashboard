import csv
from datetime import datetime

with open('raw_trades.csv', 'r') as f:
    reader = csv.DictReader(f)
    trades = list(reader)

grouped = {}
for row in trades:
    isin = row['isin']
    if isin not in grouped:
        grouped[isin] = {'symbol': row['symbol'], 'buys': [], 'sells': []}
    
    trade_type = row['trade_type'].lower()
    date_obj = datetime.strptime(row['trade_date'], '%Y-%m-%d')
    qty = int(row['quantity'])
    price = float(row['price'])
    
    if trade_type == 'buy':
        grouped[isin]['buys'].append({'date': date_obj, 'qty': qty, 'price': price})
    elif trade_type == 'sell':
        grouped[isin]['sells'].append({'date': date_obj, 'qty': qty, 'price': price})

trades_data = []

for isin, data in grouped.items():
    symbol = data['symbol']
    buys = data['buys']
    sells = data['sells']
    
    qty_bought = sum(b['qty'] for b in buys)
    qty_sold = sum(s['qty'] for s in sells)
    
    buy_value = sum(b['qty'] * b['price'] for b in buys)
    sell_value = sum(s['qty'] * s['price'] for s in sells)
    
    avg_entry = buy_value / qty_bought if qty_bought > 0 else ''
    avg_exit = sell_value / qty_sold if qty_sold > 0 else ''
    
    qty_open = qty_bought - qty_sold
    
    first_buy_date = min((b['date'] for b in buys), default=None)
    last_sell_date = max((s['date'] for s in sells), default=None)
    
    first_buy_str = first_buy_date.strftime('%Y-%m-%d') if first_buy_date else '1899-12-31'
    last_sell_str = last_sell_date.strftime('%Y-%m-%d') if last_sell_date else '1899-12-31'
    
    if qty_bought > 0 and qty_sold > 0:
        pnl = sell_value - (avg_entry * qty_sold)
        pnl_pct = pnl / (avg_entry * qty_sold)
        holding_days = (last_sell_date - first_buy_date).days
    else:
        pnl = ''
        pnl_pct = ''
        holding_days = ''
        
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
        'First Buy Date': first_buy_str,
        'Last Sell Date': last_sell_str,
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

fieldnames = ['Trade ID', 'Symbol', 'First Buy Date', 'Last Sell Date', 
    'Avg Entry', 'Avg Exit', 'Qty Bought', 'Qty Sold', 'Qty Open', 
    'Buy Value', 'Sell Value', 'P&L ₹', 'P&L %', 'Holding Days', 'Status']

with open('Trading_Journal_Fixed.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(trades_data)

print("Saved summary")
