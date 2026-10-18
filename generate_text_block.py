import csv

out = []
out.append("⚙️ TRADING JOURNAL SETTINGS,")
out.append(",")
out.append("ACCOUNT SETTINGS,")
out.append("Starting Capital,300000")
out.append("Account Name,My Trading Account")
out.append("Broker,Zerodha")
out.append(",")
out.append("RISK MANAGEMENT,")
out.append("Max Risk Per Trade (%),0.01")
out.append("Max Risk Amount (₹),3000")
out.append("Max Open Positions,6")
out.append(",")
out.append("TARGET SETTINGS,")
out.append("Monthly P&L Target (₹),10000")
out.append("Target Win Rate (%),0.5")
out.append("Target Avg R:R,2")
out.append(",")
out.append("SETUP TYPES,")
out.append("Setup 1,Breakout")
out.append("Setup 2,Pullback")
out.append("Setup 3,Reversal")
out.append("Setup 4,Trend Follow")
out.append("Setup 5,Range")
out.append("Setup 6,Gap Fill")
out.append("Setup 7,Other")
out.append("\"ADD TRADE ID (T001, T002...) in Column A to group orders. Then paste Zerodha CSV from Column B.\",,,,,,,,,,,,,")
out.append(open('raw_trades.csv').read().strip())
out.append("TRADE SUMMARY - Grouped by ISIN,,,,,,,,,,,,,,")
out.append(open('Trading_Journal_Fixed.csv').read().strip().replace('Trade ID', 'Trade ID (ISIN)'))

with open('Trading_Journal_Full.csv') as f:
    dashboard_text = f.read()

out.append("CLOSED TRADES - Fully exited positions,,,,,,,,,,,,")
# ... I'll just give them the excel file and the text.

