import csv
from collections import defaultdict

with open('Trading_Journal_Fixed.csv', 'r') as f:
    reader = csv.DictReader(f)
    trades = list(reader)

closed_trades = [t for t in trades if t['Status'] == 'CLOSED']
open_trades = [t for t in trades if t['Status'] == 'OPEN']

total_closed = len(closed_trades)
wins = [t for t in closed_trades if float(t['P&L ₹']) > 0]
losses = [t for t in closed_trades if float(t['P&L ₹']) <= 0]

win_rate = len(wins) / total_closed if total_closed > 0 else 0
total_pnl = sum(float(t['P&L ₹']) for t in closed_trades)
total_buy_value = sum(float(t['Buy Value']) for t in closed_trades)
roc = total_pnl / total_buy_value if total_buy_value > 0 else 0
avg_pnl = total_pnl / total_closed if total_closed > 0 else 0
avg_winner = sum(float(t['P&L ₹']) for t in wins) / len(wins) if wins else 0
avg_loser = sum(float(t['P&L ₹']) for t in losses) / len(losses) if losses else 0
profit_factor = abs(sum(float(t['P&L ₹']) for t in wins) / sum(float(t['P&L ₹']) for t in losses)) if losses and sum(float(t['P&L ₹']) for t in losses) != 0 else 0

best_trade = max((float(t['P&L ₹']) for t in closed_trades), default=0)
worst_trade = min((float(t['P&L ₹']) for t in closed_trades), default=0)
avg_holding = sum(int(t['Holding Days']) for t in closed_trades) / total_closed if total_closed > 0 else 0

# Sort closed trades by Last Sell Date to compute cumulative P&L
closed_trades_sorted = sorted(closed_trades, key=lambda x: x['Last Sell Date'])
cum_pnl = 0
for t in closed_trades_sorted:
    cum_pnl += float(t['P&L ₹'])
    t['Cumulative P&L'] = cum_pnl

with open('Trading_Journal_Full.csv', 'w', newline='') as f:
    # Write summary
    writer = csv.writer(f)
    writer.writerow(['TRADE SUMMARY - Grouped by ISIN'])
    f.write(open('Trading_Journal_Fixed.csv').read())
    
    # Write Dashboard
    writer.writerow([])
    writer.writerow(['📊 TRADING DASHBOARD'])
    writer.writerow(['OVERALL PERFORMANCE'])
    writer.writerow(['Total Closed Trades', total_closed])
    writer.writerow(['Wins', len(wins)])
    writer.writerow(['Losses', len(losses)])
    writer.writerow(['Win Rate', f"{win_rate:.3f}"])
    writer.writerow(['Total P&L ₹', f"{total_pnl:.2f}"])
    writer.writerow(['Return on Capital', f"{roc:.5f}"])
    writer.writerow(['Average P&L/Trade', f"{avg_pnl:.2f}"])
    writer.writerow(['Average Winner', f"{avg_winner:.2f}"])
    writer.writerow(['Average Loser', f"{avg_loser:.2f}"])
    writer.writerow(['Profit Factor', f"{profit_factor:.3f}"])
    writer.writerow(['Best Trade', f"{best_trade:.2f}"])
    writer.writerow(['Worst Trade', f"{worst_trade:.2f}"])
    writer.writerow(['Avg Holding Days', f"{avg_holding:.2f}"])
    
    # Write Open Positions
    writer.writerow([])
    writer.writerow(['OPEN POSITIONS - Not yet fully closed'])
    writer.writerow(['Trade ID', 'Symbol', 'First Buy Date', 'Avg Entry', 'Qty Open', 'Capital Deployed'])
    for t in open_trades:
        writer.writerow([t['Trade ID'], t['Symbol'], t['First Buy Date'], t['Avg Entry'], t['Qty Open'], t['Buy Value']])

print("Generated full journal at Trading_Journal_Full.csv")
