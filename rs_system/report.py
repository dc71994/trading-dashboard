"""
Automated RS System — Report Generator
Produces CSV exports and an interactive HTML dashboard.
"""

import os
import pandas as pd
from datetime import datetime
from .config import OUTPUT_DIR, SITE_DIR, TOP_INDUSTRIES_COUNT, TOP_STOCKS_DISPLAY


def ensure_output_dir():
    """Create output directories if they don't exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SITE_DIR, exist_ok=True)
    # Ensure .nojekyll exists so GitHub Pages serves raw HTML cleanly
    open(os.path.join(SITE_DIR, ".nojekyll"), "a").close()


def get_date_stamp() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


# ─── CSV Report Generators ──────────────────────────────────────────

def export_all_stocks(stock_rs: pd.DataFrame) -> str:
    """Export full universe RS rankings to CSV."""
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_All_Stocks_{get_date_stamp()}.csv")
    stock_rs.to_csv(path, index=False)
    return path


def export_top_industries(industry_rs: pd.DataFrame) -> str:
    """Export top industry rankings to CSV."""
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_Top_Industries_{get_date_stamp()}.csv")
    top = industry_rs.head(TOP_INDUSTRIES_COUNT)
    top.to_csv(path, index=False)
    return path


def export_sector_index_rs(sector_rs: pd.DataFrame) -> str:
    """Export sectoral index RS rankings to CSV."""
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_Sector_Index_Ranking_{get_date_stamp()}.csv")
    sector_rs.to_csv(path, index=False)
    return path


def export_leaders(leaders: pd.DataFrame) -> str:
    """Export leaders-in-leading-groups to CSV."""
    ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, f"RS_Leaders_In_Top_Groups_{get_date_stamp()}.csv")
    leaders.to_csv(path, index=False)
    return path


# ─── HTML Dashboard Generator ───────────────────────────────────────

def _rs_color(val: float, is_pct: bool = False) -> str:
    """Return CSS color based on RS value. Green = strong, Red = weak."""
    if is_pct:
        # For percentage returns
        if val > 30: return "#00e676"
        if val > 15: return "#66bb6a"
        if val > 5: return "#a5d6a7"
        if val > 0: return "#c8e6c9"
        if val > -5: return "#ffcdd2"
        if val > -15: return "#ef5350"
        return "#d32f2f"
    else:
        # For RS percentile (0-99)
        if val >= 90: return "#00e676"
        if val >= 80: return "#66bb6a"
        if val >= 70: return "#a5d6a7"
        if val >= 50: return "#78909c"
        if val >= 30: return "#ffcdd2"
        return "#ef5350"


def _format_num(val, decimals=1) -> str:
    """Format number with fallback for NaN."""
    try:
        if pd.isna(val):
            return "—"
        return f"{val:,.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)


def _format_volume(val) -> str:
    """Format volume as human-readable (e.g., 1.2M, 450K)."""
    try:
        if pd.isna(val):
            return "—"
        val = float(val)
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        if val >= 1_000:
            return f"{val / 1_000:.0f}K"
        return f"{val:.0f}"
    except (TypeError, ValueError):
        return "—"


def generate_dashboard(
    stock_rs: pd.DataFrame,
    industry_rs: pd.DataFrame,
    sector_rs: pd.DataFrame,
    leaders: pd.DataFrame,
) -> str:
    """Generate self-contained interactive HTML dashboard."""
    ensure_output_dir()
    date_stamp = get_date_stamp()
    path = os.path.join(OUTPUT_DIR, f"RS_Dashboard_{date_stamp}.html")

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
            <td class="mono">{row.get('Top_Stock', '—').replace('.NS', '')}</td>
            <td style="color:{_rs_color(row.get('Top_Stock_RS', 0))}">{_format_num(row.get('Top_Stock_RS', 0), 0)}</td>
        </tr>"""

    # ── Build top stocks rows ──
    stock_rows = ""
    for i, (_, row) in enumerate(stock_rs.head(TOP_STOCKS_DISPLAY).iterrows()):
        ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
        stock_rows += f"""
        <tr>
            <td class="rank-cell">{i + 1}</td>
            <td class="sticky-col mono">{ticker_clean}</td>
            <td>₹{_format_num(row.get('Current_Price', 0))}</td>
            <td>₹{_format_num(row.get('High_52W', 0))}</td>
            <td style="color:{_rs_color(row.get('Pct_From_High', 0), True)}">{_format_num(row.get('Pct_From_High', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_1M', 0), True)}">{_format_num(row.get('Return_1M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
            <td class="rs-cell" style="color:{_rs_color(row.get('RS_Percentile', 0))}">{int(row.get('RS_Percentile', 0))}</td>
            <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
        </tr>"""

    # ── Build leaders rows ──
    leader_rows = ""
    for i, (_, row) in enumerate(leaders.iterrows()):
        ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
        leader_rows += f"""
        <tr>
            <td class="rank-cell">{i + 1}</td>
            <td class="sticky-col mono">{ticker_clean}</td>
            <td>{row.get('Industry', '—')}</td>
            <td>{row.get('Sector', '—')}</td>
            <td>₹{_format_num(row.get('Current_Price', 0))}</td>
            <td style="color:{_rs_color(row.get('Pct_From_High', 0), True)}">{_format_num(row.get('Pct_From_High', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
            <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
            <td class="rs-cell" style="color:{_rs_color(row.get('RS_Percentile', 0))}">{int(row.get('RS_Percentile', 0))}</td>
            <td>{int(row.get('Industry_Rank', 0))}</td>
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
  .header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
  }}
  .header h1 span {{
    color: var(--accent);
  }}
  .header .date {{
    font-family: var(--mono);
    font-size: 13px;
    color: var(--text-muted);
  }}

  /* ── Stats Bar ── */
  .stats-bar {{
    display: flex;
    gap: 16px;
    margin-bottom: 36px;
    flex-wrap: wrap;
  }}
  .stat-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    padding: 16px 24px;
    flex: 1;
    min-width: 140px;
    position: relative;
  }}
  .stat-card::before,
  .stat-card::after {{
    content: '';
    position: absolute;
    width: 8px;
    height: 8px;
    border-color: var(--accent);
    border-style: solid;
  }}
  .stat-card::before {{
    top: -1px; left: -1px;
    border-width: 1px 0 0 1px;
  }}
  .stat-card::after {{
    bottom: -1px; right: -1px;
    border-width: 0 1px 1px 0;
  }}
  .stat-value {{
    font-size: 28px;
    font-weight: 700;
    color: var(--accent);
    font-family: var(--mono);
  }}
  .stat-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-top: 4px;
  }}

  /* ── Section ── */
  .section {{
    margin-bottom: 40px;
  }}
  .section-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
  }}
  .section-num {{
    font-family: var(--mono);
    font-size: 12px;
    color: var(--accent);
    background: var(--accent-dim);
    padding: 2px 8px;
  }}
  .section-title {{
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.02em;
  }}

  /* ── Tables ── */
  .table-wrap {{
    overflow-x: auto;
    border: 1px solid var(--border);
    background: var(--surface);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  thead th {{
    background: var(--surface-2);
    padding: 10px 14px;
    text-align: left;
    font-weight: 500;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
    position: sticky;
    top: 0;
    z-index: 2;
  }}
  thead th:hover {{
    color: var(--accent);
  }}
  thead th.sorted-asc::after {{ content: ' ▲'; color: var(--accent); font-size: 9px; }}
  thead th.sorted-desc::after {{ content: ' ▼'; color: var(--accent); font-size: 9px; }}
  tbody td {{
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }}
  tbody tr:hover {{
    background: rgba(255,255,255,0.03);
  }}
  .rank-cell {{
    font-family: var(--mono);
    color: var(--text-muted);
    font-size: 12px;
    width: 36px;
  }}
  .rs-cell {{
    font-family: var(--mono);
    font-weight: 600;
    font-size: 14px;
  }}
  .mono {{
    font-family: var(--mono);
    font-size: 12px;
  }}
  .sticky-col {{
    font-weight: 500;
  }}

  /* ── Tabs ── */
  .tab-bar {{
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0;
  }}
  .tab-btn {{
    padding: 10px 20px;
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-muted);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .tab-btn:hover {{ color: var(--text); }}
  .tab-btn.active {{
    color: var(--accent);
    border-bottom-color: var(--accent);
  }}
  .tab-panel {{
    display: none;
  }}
  .tab-panel.active {{
    display: block;
  }}

  /* ── Responsive ── */
  @media (max-width: 768px) {{
    .header h1 {{ font-size: 20px; }}
    .stat-value {{ font-size: 22px; }}
    .stats-bar {{ gap: 8px; }}
    .stat-card {{ padding: 12px 16px; }}
    table {{ font-size: 12px; }}
    tbody td, thead th {{ padding: 6px 10px; }}
  }}
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
    <button class="tab-btn active" onclick="showTab('sectors')">// Sector Indices</button>
    <button class="tab-btn" onclick="showTab('industries')">// Top Industries</button>
    <button class="tab-btn" onclick="showTab('stocks')">// Top Stocks</button>
    <button class="tab-btn" onclick="showTab('leaders')">// Leaders × Top Groups</button>
  </div>

  <!-- Tab: Sector Index RS -->
  <div id="tab-sectors" class="tab-panel active">
    <div class="section">
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
    <div class="section">
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
    <div class="section">
      <div class="section-header">
        <span class="section-num">03</span>
        <span class="section-title">Top {TOP_STOCKS_DISPLAY} Stocks by RS Percentile</span>
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
              <th>1M</th>
              <th>3M</th>
              <th>6M</th>
              <th>RS</th>
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
    <div class="section">
      <div class="section-header">
        <span class="section-num">04</span>
        <span class="section-title">Leaders in Top {TOP_INDUSTRIES_COUNT} Industries (RS ≥ 80)</span>
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
              <th>3M</th>
              <th>6M</th>
              <th>RS</th>
              <th>Ind. Rank</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{leader_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

</div>

<script>
  // ── Tab switching ──
  function showTab(name) {{
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    event.target.classList.add('active');
  }}

  // ── Table sorting ──
  document.querySelectorAll('table').forEach(table => {{
    const headers = table.querySelectorAll('thead th');
    headers.forEach((th, colIdx) => {{
      th.addEventListener('click', () => {{
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isAsc = th.classList.contains('sorted-asc');

        // Clear all sort classes
        headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));

        rows.sort((a, b) => {{
          let aVal = a.cells[colIdx]?.textContent.replace(/[₹,%—\\s]/g, '').trim() || '';
          let bVal = b.cells[colIdx]?.textContent.replace(/[₹,%—\\s]/g, '').trim() || '';
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
