"""
Automated RS System — Report Generator
Produces CSV exports and an interactive HTML dashboard.
"""

import os
import json
import pandas as pd
from datetime import datetime
from .config import OUTPUT_DIR, SITE_DIR, HISTORY_DIR, TOP_INDUSTRIES_COUNT, TOP_STOCKS_DISPLAY


def ensure_output_dir():
    """Create output directories if they don't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SITE_DIR, exist_ok=True)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    # Ensure .nojekyll exists so GitHub Pages serves raw HTML cleanly
    open(os.path.join(SITE_DIR, ".nojekyll"), "a").close()


def get_date_stamp() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


# ─── CSV Report Generators ──────────────────────────────────────────

def export_all_stocks(stock_rs: pd.DataFrame) -> str:
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_All_Stocks_{get_date_stamp()}.csv")
    stock_rs.to_csv(path, index=False)
    return path


def export_top_industries(industry_rs: pd.DataFrame) -> str:
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_Top_Industries_{get_date_stamp()}.csv")
    top = industry_rs.head(TOP_INDUSTRIES_COUNT)
    top.to_csv(path, index=False)
    return path


def export_sector_index_rs(sector_rs: pd.DataFrame) -> str:
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_Sector_Index_Ranking_{get_date_stamp()}.csv")
    sector_rs.to_csv(path, index=False)
    return path


def export_leaders(leaders: pd.DataFrame) -> str:
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_Leaders_In_Top_Groups_{get_date_stamp()}.csv")
    leaders.to_csv(path, index=False)
    return path


# ─── HTML Dashboard Generator ───────────────────────────────────────

def _rs_color(val: float, is_pct: bool = False) -> str:
    if is_pct:
        if val > 30: return "#00e676"
        if val > 15: return "#66bb6a"
        if val > 5: return "#a5d6a7"
        if val > 0: return "#c8e6c9"
        if val > -5: return "#ffcdd2"
        if val > -15: return "#ef5350"
        return "#d32f2f"
    else:
        if val >= 90: return "#00e676"
        if val >= 80: return "#66bb6a"
        if val >= 70: return "#a5d6a7"
        if val >= 50: return "#78909c"
        if val >= 30: return "#ffcdd2"
        return "#ef5350"


def _format_num(val, decimals=1) -> str:
    try:
        if pd.isna(val): return "—"
        return f"{val:,.{decimals}f}"
    except:
        return str(val)


def _format_volume(val) -> str:
    try:
        if pd.isna(val): return "—"
        val = float(val)
        if val >= 1_000_000: return f"{val / 1_000_000:.1f}M"
        if val >= 1_000: return f"{val / 1_000:.0f}K"
        return f"{val:.0f}"
    except:
        return "—"


def _format_ma(price, ma_val) -> str:
    try:
        if pd.isna(ma_val) or ma_val is None or ma_val == 0:
            return "—"
        pct_diff = ((price / ma_val) - 1.0) * 100.0
        color = "#00e676" if pct_diff >= 0 else "#ef5350"
        sign = "+" if pct_diff >= 0 else ""
        return f"<div style='font-family:var(--mono); line-height:1.2;'><span>₹{ma_val:,.1f}</span><div style='font-size:10px; color:{color}; font-weight:500;'>{sign}{pct_diff:.1f}%</div></div>"
    except:
        return "—"


def get_copy_html(ticker_clean: str) -> str:
    """Returns the HTML for the copy button."""
    return f"""
    <div style="display:flex; align-items:center; gap:6px;">
        <span class="mono">{ticker_clean}</span>
        <button class="copy-btn" onclick="copyTicker(this, 'NSE:{ticker_clean}')" title="Copy NSE:{ticker_clean}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
        </button>
    </div>"""


def generate_dashboard(
    stock_rs: pd.DataFrame,
    industry_rs: pd.DataFrame,
    sector_rs: pd.DataFrame,
    leaders: pd.DataFrame,
    history_df: pd.DataFrame = None,
    basing_df: pd.DataFrame = None,
    launch_pad_df: pd.DataFrame = None,
) -> str:
    ensure_output_dir()
    date_stamp = get_date_stamp()
    path = os.path.join(OUTPUT_DIR, f"RS_Dashboard_{date_stamp}.html")

    # ── History Data for Chart.js ──
    history_json = "[]"
    if history_df is not None and not history_df.empty:
        # Sort by date
        history_df = history_df.sort_values("Date")
        history_json = history_df.to_json(orient="records")

    # ── Build sector index heatmap rows ──
    sector_rows = ""
    for _, row in sector_rs.iterrows():
        sector_rows += f"""
        <tr>
            <td class="sticky-col">{row.get('Sector_Index', '—')}</td>
            <td style="color:{_rs_color(row.get('Return_1M', 0), True)}">{_format_num(row.get('Return_1M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
            <td style="color:{_rs_color(row.get('RS_Spread_6M', 0), True)}">{_format_num(row.get('RS_Spread_6M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Composite_RS', 0) * 100 if abs(row.get('Composite_RS', 0)) < 5 else row.get('Composite_RS', 0), True)}">{_format_num(row.get('Composite_RS', 0))}%</td>
        </tr>"""

    # ── Build industry leaderboard rows ──
    industry_rows = ""
    for _, row in industry_rs.head(TOP_INDUSTRIES_COUNT).iterrows():
        industry_rows += f"""
        <tr>
            <td class="rank-cell">{int(row.get('Rank', 0))}</td>
            <td class="sticky-col">{row.get('Industry', '—')}</td>
            <td>{row.get('Sector', '—')}</td>
            <td style="color:{_rs_color(row.get('Median_RS', 0))}">{_format_num(row.get('Median_RS', 0), 0)}</td>
            <td>{_format_num(row.get('Pct_Above_70', 0), 0)}%</td>
            <td>{_format_num(row.get('Pct_Near_High', 0), 0)}%</td>
            <td>{int(row.get('Stock_Count', 0))}</td>
            <td>{get_copy_html(row.get('Top_Stock', '—').replace('.NS', ''))}</td>
            <td style="color:{_rs_color(row.get('Top_Stock_RS', 0))}">{_format_num(row.get('Top_Stock_RS', 0), 0)}</td>
        </tr>"""

    # ── Build top stocks rows ──
    stock_rows = ""
    for i, (_, row) in enumerate(stock_rs.head(TOP_STOCKS_DISPLAY).iterrows()):
        ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
        price = row.get('Current_Price', 0)
        stock_rows += f"""
        <tr>
            <td class="rank-cell">{i + 1}</td>
            <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
            <td>₹{_format_num(price)}</td>
            <td>₹{_format_num(row.get('High_52W', 0))}</td>
            <td style="color:{_rs_color(row.get('Pct_From_High', 0), True)}">{_format_num(row.get('Pct_From_High', 0))}%</td>
            <td class="rs-cell" style="color:{_rs_color(row.get('RS_Percentile', 0))}">{int(row.get('RS_Percentile', 0))}</td>
            <td style="color:{_rs_color(row.get('Return_1M', 0), True)}">{_format_num(row.get('Return_1M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
            <td>{_format_ma(price, row.get('EMA_10'))}</td>
            <td>{_format_ma(price, row.get('EMA_20'))}</td>
            <td>{_format_ma(price, row.get('SMA_50'))}</td>
            <td>{_format_ma(price, row.get('SMA_100'))}</td>
            <td>{_format_ma(price, row.get('SMA_200'))}</td>
            <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
        </tr>"""

    # ── Build leaders rows ──
    leader_rows = ""
    for i, (_, row) in enumerate(leaders.iterrows()):
        ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
        price = row.get('Current_Price', 0)
        leader_rows += f"""
        <tr>
            <td class="rank-cell">{i + 1}</td>
            <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
            <td>{row.get('Industry', '—')}</td>
            <td>{row.get('Sector', '—')}</td>
            <td>₹{_format_num(price)}</td>
            <td style="color:{_rs_color(row.get('Pct_From_High', 0), True)}">{_format_num(row.get('Pct_From_High', 0))}%</td>
            <td class="rs-cell" style="color:{_rs_color(row.get('RS_Percentile', 0))}">{int(row.get('RS_Percentile', 0))}</td>
            <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
            <td>{int(row.get('Industry_Rank', 0))}</td>
            <td>{_format_ma(price, row.get('EMA_10'))}</td>
            <td>{_format_ma(price, row.get('EMA_20'))}</td>
            <td>{_format_ma(price, row.get('SMA_50'))}</td>
            <td>{_format_ma(price, row.get('SMA_100'))}</td>
            <td>{_format_ma(price, row.get('SMA_200'))}</td>
            <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
        </tr>"""

    # ── Build basing rows ──
    basing_rows = ""
    basing_count = 0
    if basing_df is not None:
        basing_count = len(basing_df)
        for i, (_, row) in enumerate(basing_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            basing_rows += f"""
            <tr data-pct-from-high="{row.get('Pct_From_High', 0):.2f}" data-industry="{row.get('Industry', 'Unknown')}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{row.get('Industry', '—')}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td class="pct-high-cell" style="color:{_rs_color(row.get('Pct_From_High', 0), True)}">{_format_num(row.get('Pct_From_High', 0))}%</td>
                <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
                <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
                <td class="rs-cell" style="color:{_rs_color(row.get('RS_Percentile', 0))}">{int(row.get('RS_Percentile', 0))}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""

    # ── Build launch pad rows ──
    launch_pad_rows = ""
    launch_pad_count = 0
    if launch_pad_df is not None:
        launch_pad_count = len(launch_pad_df)
        for i, (_, row) in enumerate(launch_pad_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            launch_pad_rows += f"""
            <tr data-industry="{row.get('Industry', 'Unknown')}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{row.get('Industry', '—')}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td>{_format_ma(price, row.get('EMA_10'))}</td>
                <td>{_format_ma(price, row.get('EMA_20'))}</td>
                <td>{_format_ma(price, row.get('SMA_50'))}</td>
                <td class="rs-cell" style="color:{_rs_color(row.get('RS_Percentile', 0))}">{int(row.get('RS_Percentile', 0))}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""

    # ── Assemble stats ──
    total_stocks = len(stock_rs)
    total_industries = len(industry_rs)
    stocks_above_80 = len(stock_rs[stock_rs['RS_Percentile'] >= 80]) if 'RS_Percentile' in stock_rs.columns else 0
    leader_count = len(leaders)

    # ── Generate HTML ──
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RS Dashboard — {date_stamp}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {{
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface-2: #1a1a26;
    --border: rgba(255,255,255,0.06);
    --text: #e8e8ed;
    --text-muted: #6b6b7b;
    --accent: #00e676;
    --accent-dim: rgba(0,230,118,0.12);
    --red: #ef5350;
    --font: 'Inter', system-ui, sans-serif;
    --mono: 'JetBrains Mono', ui-monospace, monospace;
  }}

  * {{ margin:0; padding:0; box-sizing:border-box; }}

  body {{
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}

  .container {{
    max-width: 1400px;
    margin: 0 auto;
    padding: 24px 20px 80px;
  }}

  /* ── Header ── */
  .header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 32px 0 24px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .header h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.03em; }}
  .header h1 span {{ color: var(--accent); }}
  .header .date {{ font-family: var(--mono); font-size: 13px; color: var(--text-muted); }}

  /* ── Stats Bar ── */
  .stats-bar {{ display: flex; gap: 16px; margin-bottom: 36px; flex-wrap: wrap; }}
  .stat-card {{ background: var(--surface); border: 1px solid var(--border); padding: 16px 24px; flex: 1; min-width: 140px; position: relative; }}
  .stat-card::before, .stat-card::after {{ content: ''; position: absolute; width: 8px; height: 8px; border-color: var(--accent); border-style: solid; }}
  .stat-card::before {{ top: -1px; left: -1px; border-width: 1px 0 0 1px; }}
  .stat-card::after {{ bottom: -1px; right: -1px; border-width: 0 1px 1px 0; }}
  .stat-value {{ font-size: 28px; font-weight: 700; color: var(--accent); font-family: var(--mono); }}
  .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-top: 4px; }}

  /* ── Section & Chart ── */
  .section {{ margin-bottom: 40px; }}
  .section-header {{ display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }}
  .section-header-left {{ display: flex; align-items: center; gap: 10px; }}
  .section-num {{ font-family: var(--mono); font-size: 12px; color: var(--accent); background: var(--accent-dim); padding: 2px 8px; }}
  .section-title {{ font-size: 18px; font-weight: 600; letter-spacing: -0.02em; }}
  
  .chart-container {{
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 20px;
    height: 400px;
    width: 100%;
    margin-bottom: 24px;
  }}

  /* ── Tables ── */
  .table-wrap {{ overflow-x: auto; border: 1px solid var(--border); background: var(--surface); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead th {{ background: var(--surface-2); padding: 10px 14px; text-align: left; font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); border-bottom: 1px solid var(--border); white-space: nowrap; cursor: pointer; user-select: none; position: sticky; top: 0; z-index: 2; }}
  thead th:hover {{ color: var(--accent); }}
  thead th.sorted-asc::after {{ content: ' ▲'; color: var(--accent); font-size: 9px; }}
  thead th.sorted-desc::after {{ content: ' ▼'; color: var(--accent); font-size: 9px; }}
  tbody td {{ padding: 8px 14px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
  .rank-cell {{ font-family: var(--mono); color: var(--text-muted); font-size: 12px; width: 36px; }}
  .rs-cell {{ font-family: var(--mono); font-weight: 600; font-size: 14px; }}
  .mono {{ font-family: var(--mono); font-size: 12px; }}
  .sticky-col {{ font-weight: 500; }}

  /* ── Buttons & UI ── */
  .copy-btn {{
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border-radius: 4px;
    transition: all 0.2s;
  }}
  .copy-btn:hover {{
    color: var(--accent);
    background: var(--surface-2);
  }}
  .copy-btn.copied {{
    color: #fff;
    background: var(--accent);
  }}
  
  .copy-all-btn {{
    padding: 6px 14px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .copy-all-btn:hover {{
    background: rgba(255,255,255,0.08);
    border-color: var(--accent);
    color: var(--accent);
  }}

  .tab-bar {{ display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 0; flex-wrap: wrap; }}
  .tab-btn {{ padding: 10px 20px; font-family: var(--mono); font-size: 12px; color: var(--text-muted); background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; transition: all 0.15s; }}
  .tab-btn:hover {{ color: var(--text); }}
  .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <h1><span>//</span> RS System — NSE Full Market</h1>
    <div class="date">Generated: {date_stamp}</div>
  </div>

  <!-- Stats Bar -->
  <div class="stats-bar">
    <div class="stat-card">
      <div class="stat-value">{total_stocks:,}</div>
      <div class="stat-label">Stocks Scanned</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{total_industries}</div>
      <div class="stat-label">Industries Ranked</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{stocks_above_80}</div>
      <div class="stat-label">RS ≥ 80</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{leader_count}</div>
      <div class="stat-label">Leaders in Top Groups</div>
    </div>
  </div>

  <!-- Tabs -->
  <div class="tab-bar">
    <button class="tab-btn active" onclick="showTab('trend')">// Industry Trend</button>
    <button class="tab-btn" onclick="showTab('sectors')">// Sector Indices</button>
    <button class="tab-btn" onclick="showTab('industries')">// Top Industries</button>
    <button class="tab-btn" onclick="showTab('stocks')">// Top Stocks</button>
    <button class="tab-btn" onclick="showTab('leaders')">// Leaders × Top Groups</button>
    <button class="tab-btn" onclick="showTab('basing')" style="color:var(--accent);">// Basing Setups</button>
    <button class="tab-btn" onclick="showTab('launchpad')" style="color:var(--accent);">// Launch Pads</button>
  </div>
  
  <!-- Tab: Industry Trend -->
  <div id="tab-trend" class="tab-panel active">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <span class="section-num">00</span>
        <span class="section-title">Historical Rotation (Top 10 Industries)</span>
      </div>
      <div class="chart-container">
        <canvas id="industryChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Tab: Sector Index RS -->
  <div id="tab-sectors" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <span class="section-num">01</span>
        <span class="section-title">Sectoral Index Relative Strength vs Nifty 50</span>
      </div>
      <div class="table-wrap">
        <table id="table-sectors">
          <thead>
            <tr>
              <th>Sector Index</th>
              <th>1M Return</th>
              <th>3M Return</th>
              <th>6M Return</th>
              <th>RS Spread (6M)</th>
              <th>Composite RS</th>
            </tr>
          </thead>
          <tbody>{sector_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: Industry Leaderboard -->
  <div id="tab-industries" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <span class="section-num">02</span>
        <span class="section-title">Top {TOP_INDUSTRIES_COUNT} Industries by Relative Strength</span>
      </div>
      <div class="table-wrap">
        <table id="table-industries">
          <thead>
            <tr>
              <th>#</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Median RS</th>
              <th>% RS≥70</th>
              <th>% Near High</th>
              <th>Stocks</th>
              <th>Top Stock</th>
              <th>Top RS</th>
            </tr>
          </thead>
          <tbody>{industry_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: Top Stocks -->
  <div id="tab-stocks" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">03</span>
          <span class="section-title">Top {TOP_STOCKS_DISPLAY} Stocks by RS Percentile</span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-stocks')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap">
        <table id="table-stocks">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Price</th>
              <th>52W High</th>
              <th>% From High</th>
              <th>RS</th>
              <th>1M</th>
              <th>3M</th>
              <th>6M</th>
              <th>10 EMA</th>
              <th>20 EMA</th>
              <th>50 SMA</th>
              <th>100 SMA</th>
              <th>200 SMA</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{stock_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: Leaders in Leading Groups -->
  <div id="tab-leaders" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">04</span>
          <span class="section-title">Leaders in Top {TOP_INDUSTRIES_COUNT} Industries (RS ≥ 80)</span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-leaders')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap">
        <table id="table-leaders">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>% From High</th>
              <th>RS</th>
              <th>3M</th>
              <th>6M</th>
              <th>Ind. Rank</th>
              <th>10 EMA</th>
              <th>20 EMA</th>
              <th>50 SMA</th>
              <th>100 SMA</th>
              <th>200 SMA</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{leader_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: Basing Setups -->
  <div id="tab-basing" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">05</span>
          <span class="section-title">High Momentum Basing ({basing_count})</span>
          <select id="base-depth-filter" onchange="filterBasing()" style="margin-left:16px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="25">Max 25% Depth</option>
            <option value="20">Max 20% Depth</option>
            <option value="15">Max 15% Depth</option>
            <option value="10">Max 10% Depth</option>
          </select>
          <span id="basing-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-basing')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap">
        <table id="table-basing">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>% From High</th>
              <th>3M</th>
              <th>6M</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{basing_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Tab: Launch Pads -->
  <div id="tab-launchpad" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">06</span>
          <span class="section-title">Launch Pad Setups ({launch_pad_count})</span>
          <span id="launchpad-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-launchpad')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap">
        <table id="table-launchpad">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>10 EMA</th>
              <th>20 EMA</th>
              <th>50 SMA</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{launch_pad_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

</div>

<script>
  // ── Copy to Clipboard ──
  function copyTicker(btn, ticker) {{
    navigator.clipboard.writeText(ticker).then(() => {{
      const originalHtml = btn.innerHTML;
      btn.classList.add('copied');
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
      setTimeout(() => {{
        btn.classList.remove('copied');
        btn.innerHTML = originalHtml;
      }}, 1500);
    }});
  }}

  function copyAllTickers(btn, tableId) {{
    const table = document.getElementById(tableId);
    if (!table) return;
    const rows = table.querySelectorAll('tbody tr');
    const tickers = [];
    rows.forEach(row => {{
      const tickerSpan = row.querySelector('.mono');
      if (tickerSpan) {{
        tickers.push('NSE:' + tickerSpan.textContent.trim());
      }}
    }});
    
    if (tickers.length === 0) return;
    
    const textToCopy = tickers.join(',');
    navigator.clipboard.writeText(textToCopy).then(() => {{
      const originalHtml = btn.innerHTML;
      btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied!';
      btn.style.color = 'var(--accent)';
      setTimeout(() => {{
        btn.innerHTML = originalHtml;
        btn.style.color = '';
      }}, 1500);
    }});
  }}

  // ── Tab switching ──
  function showTab(name) {{
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.target.classList.add('active');
  }}

  // ── Basing Filter & Insights ──
  function filterBasing() {{
    const maxDepth = parseFloat(document.getElementById('base-depth-filter').value) * -1;
    const rows = document.querySelectorAll('#table-basing tbody tr');
    let visibleCount = 0;
    
    rows.forEach(row => {{
      const pctFromHigh = parseFloat(row.getAttribute('data-pct-from-high'));
      if (pctFromHigh >= maxDepth && pctFromHigh <= 0) {{
        row.style.display = '';
        visibleCount++;
      }} else {{
        row.style.display = 'none';
      }}
    }});
    
    updateInsights('table-basing', 'basing-insights');
  }}
  
  function updateInsights(tableId, spanId) {{
    const rows = document.querySelectorAll(`#${{tableId}} tbody tr`);
    const counts = {{}};
    let totalVisible = 0;
    
    rows.forEach(row => {{
      if (row.style.display !== 'none') {{
        const ind = row.getAttribute('data-industry');
        if (ind && ind !== 'Unknown' && ind !== '—') {{
          counts[ind] = (counts[ind] || 0) + 1;
        }}
        totalVisible++;
      }}
    }});
    
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 3);
    const span = document.getElementById(spanId);
    if (span && sorted.length > 0) {{
      const txt = sorted.map(s => `${{s[0]}} (${{s[1]}})`).join(', ');
      span.textContent = `Top Industries: ${{txt}}`;
    }} else if (span) {{
      span.textContent = '';
    }}
  }}
  
  // Run on load
  setTimeout(() => {{
    filterBasing();
    updateInsights('table-launchpad', 'launchpad-insights');
  }}, 100);

  // ── Table sorting ──
  document.querySelectorAll('table').forEach(table => {{
    const headers = table.querySelectorAll('thead th');
    headers.forEach((th, colIdx) => {{
      th.addEventListener('click', () => {{
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isAsc = th.classList.contains('sorted-asc');

        headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));

        rows.sort((a, b) => {{
          let aVal = a.cells[colIdx]?.textContent.replace(/[₹,%—\\s]/g, '').replace('NSE:', '').trim() || '';
          let bVal = b.cells[colIdx]?.textContent.replace(/[₹,%—\\s]/g, '').replace('NSE:', '').trim() || '';
          const aNum = parseFloat(aVal);
          const bNum = parseFloat(bVal);
          if (!isNaN(aNum) && !isNaN(bNum)) {{
            return isAsc ? bNum - aNum : aNum - bNum;
          }}
          return isAsc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
        }});

        th.classList.add(isAsc ? 'sorted-desc' : 'sorted-asc');
        rows.forEach(row => tbody.appendChild(row));
      }});
    }});
  }});
  
  // ── Chart.js Logic ──
  const historyData = {history_json};
  
  if (historyData.length > 0) {{
      // Group by Industry
      const industries = [...new Set(historyData.map(d => d.Industry))];
      // Get the latest date to find current top 10
      const dates = [...new Set(historyData.map(d => d.Date))].sort();
      const latestDate = dates[dates.length - 1];
      
      const latestRanks = historyData.filter(d => d.Date === latestDate)
                                     .sort((a, b) => a.Rank - b.Rank)
                                     .map(d => d.Industry);
                                     
      const top10 = latestRanks.slice(0, 10);
      
      const colors = [
          '#00e676', '#ff4081', '#29b6f6', '#ffee58', '#ab47bc',
          '#ff7043', '#26a69a', '#ec407a', '#7e57c2', '#9ccc65'
      ];
      
      const datasets = top10.map((ind, i) => {{
          const indData = dates.map(date => {{
              const row = historyData.find(d => d.Date === date && d.Industry === ind);
              return row ? row.Median_RS : null;
          }});
          
          return {{
              label: ind,
              data: indData,
              borderColor: colors[i % colors.length],
              backgroundColor: colors[i % colors.length],
              tension: 0.3,
              borderWidth: 2,
              pointRadius: 3,
              pointHoverRadius: 5
          }};
      }});
      
      const ctx = document.getElementById('industryChart').getContext('2d');
      Chart.defaults.color = '#6b6b7b';
      Chart.defaults.font.family = "'Inter', sans-serif";
      
      new Chart(ctx, {{
          type: 'line',
          data: {{
              labels: dates,
              datasets: datasets
          }},
          options: {{
              responsive: true,
              maintainAspectRatio: false,
              interaction: {{
                  mode: 'index',
                  intersect: false,
              }},
              plugins: {{
                  legend: {{
                      position: 'right',
                      labels: {{ boxWidth: 12, usePointStyle: true, padding: 15 }}
                  }},
                  tooltip: {{
                      backgroundColor: '#1a1a26',
                      titleColor: '#e8e8ed',
                      bodyColor: '#e8e8ed',
                      borderColor: 'rgba(255,255,255,0.06)',
                      borderWidth: 1
                  }}
              }},
              scales: {{
                  y: {{
                      grid: {{ color: 'rgba(255,255,255,0.03)' }},
                      title: {{ display: true, text: 'Median RS Score' }}
                  }},
                  x: {{
                      grid: {{ color: 'rgba(255,255,255,0.03)' }}
                  }}
              }}
          }}
      }});
  }} else {{
      document.getElementById('industryChart').parentElement.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding-top:40px;">No historical data available yet. Check back after a few updates!</div>';
  }}
</script>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    # Also save to the docs folder as index.html for GitHub Pages
    site_path = os.path.join(SITE_DIR, "index.html")
    with open(site_path, "w", encoding="utf-8") as f:
        f.write(html)

    return path
