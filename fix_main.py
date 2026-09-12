import re

with open('rs_system/main.py', 'r') as f:
    code = f.read()

# Fix history tracking for sectors
history_replacement = """    # ── Update Historical Data ──
    history_file = os.path.join(config.HISTORY_DIR, 'industry_rs_history.csv')
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
code = re.sub(r'    # ── Update Historical Data ──.*?(?=    # ------------------------)', history_replacement, code, flags=re.DOTALL)

# Update generate_dashboard call
dash_call = "html_path = generate_dashboard(stock_rs, industry_rs, sector_rs, leaders, history_df=full_hist, sector_history_df=sec_full_hist, basing_df=basing, launch_pad_df=launch_pad)"
code = re.sub(r'html_path = generate_dashboard\(stock_rs, industry_rs, sector_rs, leaders, history_df=full_hist, basing_df=basing, launch_pad_df=launch_pad\)', dash_call, code)

with open('rs_system/main.py', 'w') as f:
    f.write(code)
print("Updated main.py for sector tracking.")
