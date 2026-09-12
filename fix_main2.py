import re

with open('rs_system/main.py', 'r') as f:
    code = f.read()

history_replacement = """    # --- HISTORY TRACKING ---
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    history_file = config.INDUSTRY_HISTORY_FILE
    sector_history_file = os.path.join(config.HISTORY_DIR, 'sector_rs_history.csv')
    
    # 1. Prepare today's data for appending
    today_history = industry_rs[['Industry', 'Rank', 'Median_RS']].copy()
    today_history['Date'] = date_stamp
    
    today_sector_hist = sector_rs[['Sector_Index', 'Rank', 'Composite_RS']].copy()
    today_sector_hist.rename(columns={'Sector_Index': 'Sector'}, inplace=True)
    today_sector_hist['Date'] = date_stamp
    
    # 2. Append to CSV
    os.makedirs(config.HISTORY_DIR, exist_ok=True)
    
    # Industry History
    if os.path.exists(history_file):
        old_hist = pd.read_csv(history_file)
        old_hist = old_hist[old_hist['Date'] != date_stamp]
        full_hist = pd.concat([old_hist, today_history], ignore_index=True)
    else:
        full_hist = today_history
    full_hist.to_csv(history_file, index=False)
    
    # Sector History
    if os.path.exists(sector_history_file):
        old_sec_hist = pd.read_csv(sector_history_file)
        old_sec_hist = old_sec_hist[old_sec_hist['Date'] != date_stamp]
        sec_full_hist = pd.concat([old_sec_hist, today_sector_hist], ignore_index=True)
    else:
        sec_full_hist = today_sector_hist
    sec_full_hist.to_csv(sector_history_file, index=False)
"""
code = re.sub(r'    # --- HISTORY TRACKING ---.*?(?=    basing = find_basing_stocks)', history_replacement + '\n', code, flags=re.DOTALL)

with open('rs_system/main.py', 'w') as f:
    f.write(code)
print("Updated main.py properly.")
