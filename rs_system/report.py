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
    sector_history_df: pd.DataFrame = None,
    basing_df: pd.DataFrame = None,
    launch_pad_df: pd.DataFrame = None,
    reclaimed_10_sma_df: pd.DataFrame = None,
    ipo_reclaimed_10_sma_df: pd.DataFrame = None,
    breakaway_gaps_df: pd.DataFrame = None,
    gap_and_hold_df: pd.DataFrame = None,
    ipo_gaps_df: pd.DataFrame = None,
    prices: dict = None,
) -> str:
    ensure_output_dir()
    date_stamp = get_date_stamp()
    path = os.path.join(OUTPUT_DIR, f"RS_Dashboard_{date_stamp}.html")

    # ── History Data for Chart.js ──
    history_json = "[]"
    if history_df is not None and not history_df.empty:
        history_df = history_df.sort_values("Date")
        history_json = history_df.to_json(orient="records")
        
    sector_history_json = "[]"
    if sector_history_df is not None and not sector_history_df.empty:
        sector_history_df = sector_history_df.sort_values("Date")
        sector_history_json = sector_history_df.to_json(orient="records")

    # ── Stock Candle & MA Data for Grid View ──
    # Extract up to 250 bars (full 1 year) for candidates across setups
    candidate_tickers = set()
    for df_cand in [
        basing_df, launch_pad_df, reclaimed_10_sma_df, ipo_reclaimed_10_sma_df,
        breakaway_gaps_df, gap_and_hold_df, ipo_gaps_df
    ]:
        if df_cand is not None and not df_cand.empty and 'Ticker' in df_cand.columns:
            candidate_tickers.update(df_cand['Ticker'].dropna().tolist())

    candles_data = {}
    if prices is not None:
        for t in candidate_tickers:
            if t in prices and prices[t] is not None and not prices[t].empty:
                df_p = prices[t].dropna(how='all').copy()
                if isinstance(df_p.columns, pd.MultiIndex):
                    df_p.columns = [c[0] for c in df_p.columns]
                if len(df_p) >= 10:
                    recent = df_p.tail(250)
                    close_s = df_p['Close']
                    ema10_s = close_s.ewm(span=10, adjust=False).mean()
                    ema20_s = close_s.ewm(span=20, adjust=False).mean()
                    sma50_s = close_s.rolling(window=50).mean()
                    sma200_s = close_s.rolling(window=200).mean()
                    vol50_s = df_p['Volume'].rolling(window=50).mean()

                    bars = []
                    for idx, row in recent.iterrows():
                        d_str = idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx)[:10]
                        c_val = float(row.get('Close', 0))
                        o_val = float(row.get('Open', c_val))
                        h_val = float(row.get('High', max(c_val, o_val)))
                        l_val = float(row.get('Low', min(c_val, o_val)))
                        v_val = float(row.get('Volume', 0))
                        
                        e10 = float(ema10_s.loc[idx]) if idx in ema10_s and not pd.isna(ema10_s.loc[idx]) else None
                        e20 = float(ema20_s.loc[idx]) if idx in ema20_s and not pd.isna(ema20_s.loc[idx]) else None
                        s50 = float(sma50_s.loc[idx]) if idx in sma50_s and not pd.isna(sma50_s.loc[idx]) else None
                        s200 = float(sma200_s.loc[idx]) if idx in sma200_s and not pd.isna(sma200_s.loc[idx]) else None
                        v50 = float(vol50_s.loc[idx]) if idx in vol50_s and not pd.isna(vol50_s.loc[idx]) else None

                        bars.append({
                            'time': d_str, 'open': round(o_val, 2), 'high': round(h_val, 2),
                            'low': round(l_val, 2), 'close': round(c_val, 2), 'volume': round(v_val, 0),
                            'ema10': round(e10, 2) if e10 else None,
                            'ema20': round(e20, 2) if e20 else None,
                            'sma50': round(s50, 2) if s50 else None,
                            'sma200': round(s200, 2) if s200 else None,
                            'vol50': round(v50, 0) if v50 else None,
                        })
                    candles_data[t.replace('.NS', '')] = bars
    candles_json = json.dumps(candles_data)


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

    # ── Build basing rows & cards ──
    basing_rows = ""
    basing_cards = ""
    basing_count = 0
    if basing_df is not None:
        basing_count = len(basing_df)
        for i, (_, row) in enumerate(basing_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            basing_rows += f"""
            <tr data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td class="pct-high-cell" style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</td>
                <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
                <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            basing_cards += f"""
            <div class="chart-card" data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)} · <span style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</span></div>
                </div>
                <div class="chart-card-canvas" id="chart-basing-{ticker_clean}"></div>
            </div>"""

    # ── Build launch pad rows & cards ──
    launch_pad_rows = ""
    launch_pad_cards = ""
    launch_pad_count = 0
    if launch_pad_df is not None:
        launch_pad_count = len(launch_pad_df)
        for i, (_, row) in enumerate(launch_pad_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            launch_pad_rows += f"""
            <tr data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td>{_format_ma(price, row.get('EMA_10'))}</td>
                <td>{_format_ma(price, row.get('EMA_20'))}</td>
                <td>{_format_ma(price, row.get('SMA_50'))}</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            launch_pad_cards += f"""
            <div class="chart-card" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)}</div>
                </div>
                <div class="chart-card-canvas" id="chart-launchpad-{ticker_clean}"></div>
            </div>"""

    # ── Build 10 SMA Reclaim rows & cards ──
    reclaimed_10_sma_rows = ""
    reclaimed_10_sma_cards = ""
    reclaimed_10_sma_count = 0
    if reclaimed_10_sma_df is not None:
        reclaimed_10_sma_count = len(reclaimed_10_sma_df)
        for i, (_, row) in enumerate(reclaimed_10_sma_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            reclaimed_10_sma_rows += f"""
            <tr data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td>{_format_ma(price, row.get('SMA_10'))}</td>
                <td class="pct-high-cell" style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</td>
                <td style="color:{_rs_color(row.get('Return_3M', 0), True)}">{_format_num(row.get('Return_3M', 0))}%</td>
                <td style="color:{_rs_color(row.get('Return_6M', 0), True)}">{_format_num(row.get('Return_6M', 0))}%</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            reclaimed_10_sma_cards += f"""
            <div class="chart-card" data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)} · <span style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</span></div>
                </div>
                <div class="chart-card-canvas" id="chart-reclaim10-{ticker_clean}"></div>
            </div>"""

    # ── Build IPO 10 SMA Reclaim rows & cards ──
    ipo_reclaimed_10_sma_rows = ""
    ipo_reclaimed_10_sma_cards = ""
    ipo_reclaimed_10_sma_count = 0
    if ipo_reclaimed_10_sma_df is not None:
        ipo_reclaimed_10_sma_count = len(ipo_reclaimed_10_sma_df)
        for i, (_, row) in enumerate(ipo_reclaimed_10_sma_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            listing_bars = int(row.get('Listing_Bars', 0))
            ipo_reclaimed_10_sma_rows += f"""
            <tr data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td>{listing_bars}d</td>
                <td>{_format_ma(price, row.get('SMA_10'))}</td>
                <td class="pct-high-cell" style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</td>
                <td style="color:{_rs_color(row.get('Return_1M', 0), True)}">{_format_num(row.get('Return_1M', 0))}%</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            ipo_reclaimed_10_sma_cards += f"""
            <div class="chart-card" data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)} · {listing_bars}d · <span style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</span></div>
                </div>
                <div class="chart-card-canvas" id="chart-iporeclaim10-{ticker_clean}"></div>
            </div>"""

    # ── Build Breakaway Gaps rows & cards ──
    breakaway_gaps_rows = ""
    breakaway_gaps_cards = ""
    breakaway_gaps_count = 0
    if breakaway_gaps_df is not None:
        breakaway_gaps_count = len(breakaway_gaps_df)
        for i, (_, row) in enumerate(breakaway_gaps_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            gap_pct = row.get('Gap_Pct', 0)
            gap_rvol = row.get('Gap_RVOL', 0)
            gap_days = int(row.get('Gap_Days_Ago', 0))
            gap_time_str = "Today" if gap_days == 0 else f"{gap_days}d ago"
            breakaway_gaps_rows += f"""
            <tr data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td style="color:var(--accent); font-weight:600;">+{gap_pct:.1f}% ({gap_time_str})</td>
                <td style="color:#ffee58; font-family:var(--mono); font-weight:600;">{gap_rvol:.1f}x</td>
                <td class="pct-high-cell" style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</td>
                <td style="color:{_rs_color(row.get('Return_1M', 0), True)}">{_format_num(row.get('Return_1M', 0))}%</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            breakaway_gaps_cards += f"""
            <div class="chart-card" data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)} · <span style="color:var(--accent);">Gap +{gap_pct:.1f}% ({gap_rvol:.1f}x)</span> · <span style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</span></div>
                </div>
                <div class="chart-card-canvas" id="chart-breakaway-{ticker_clean}"></div>
            </div>"""

    # ── Build Gap & Hold rows & cards ──
    gap_and_hold_rows = ""
    gap_and_hold_cards = ""
    gap_and_hold_count = 0
    if gap_and_hold_df is not None:
        gap_and_hold_count = len(gap_and_hold_df)
        for i, (_, row) in enumerate(gap_and_hold_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            gap_pct = row.get('Gap_Pct', 0)
            gap_rvol = row.get('Gap_RVOL', 0)
            gap_days = int(row.get('Gap_Days_Ago', 0))
            gap_and_hold_rows += f"""
            <tr data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td style="color:var(--accent); font-weight:600;">+{gap_pct:.1f}% ({gap_days}d ago)</td>
                <td style="color:#ffee58; font-family:var(--mono); font-weight:600;">{gap_rvol:.1f}x</td>
                <td class="pct-high-cell" style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</td>
                <td style="color:{_rs_color(row.get('Return_1M', 0), True)}">{_format_num(row.get('Return_1M', 0))}%</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            gap_and_hold_cards += f"""
            <div class="chart-card" data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)} · <span style="color:var(--accent);">Held {gap_days}d (+{gap_pct:.1f}%)</span> · <span style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</span></div>
                </div>
                <div class="chart-card-canvas" id="chart-gaphold-{ticker_clean}"></div>
            </div>"""

    # ── Build IPO Gaps rows & cards ──
    ipo_gaps_rows = ""
    ipo_gaps_cards = ""
    ipo_gaps_count = 0
    if ipo_gaps_df is not None:
        ipo_gaps_count = len(ipo_gaps_df)
        for i, (_, row) in enumerate(ipo_gaps_df.iterrows()):
            ticker_clean = str(row.get('Ticker', '—')).replace('.NS', '')
            price = row.get('Current_Price', 0)
            rs_val = int(row.get('RS_Percentile', 0))
            pct_high = row.get('Pct_From_High', 0)
            ind_name = row.get('Industry', 'Unknown')
            gap_pct = row.get('Gap_Pct', 0)
            gap_rvol = row.get('Gap_RVOL', 0)
            listing_bars = int(row.get('Listing_Bars', 0))
            gap_days = int(row.get('Gap_Days_Ago', 0))
            gap_time_str = "Today" if gap_days == 0 else f"{gap_days}d ago"
            ipo_gaps_rows += f"""
            <tr data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <td class="rank-cell">{i + 1}</td>
                <td class="sticky-col">{get_copy_html(ticker_clean)}</td>
                <td class="industry-cell">{ind_name}</td>
                <td>{row.get('Sector', '—')}</td>
                <td>₹{_format_num(price)}</td>
                <td>{listing_bars}d</td>
                <td style="color:var(--accent); font-weight:600;">+{gap_pct:.1f}% ({gap_time_str})</td>
                <td style="color:#ffee58; font-family:var(--mono); font-weight:600;">{gap_rvol:.1f}x</td>
                <td class="pct-high-cell" style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</td>
                <td class="rs-cell" style="color:{_rs_color(rs_val)}">{rs_val}</td>
                <td>{_format_volume(row.get('Avg_Volume', 0))}</td>
            </tr>"""
            ipo_gaps_cards += f"""
            <div class="chart-card" data-pct-from-high="{pct_high:.2f}" data-industry="{ind_name}" data-ticker="{ticker_clean}">
                <div class="chart-card-header">
                    <div class="chart-card-title">
                        {get_copy_html(ticker_clean)}
                        <span class="chart-card-rs">RS {rs_val}</span>
                    </div>
                    <div class="chart-card-meta">₹{_format_num(price)} · {listing_bars}d · <span style="color:var(--accent);">Gap +{gap_pct:.1f}%</span> · <span style="color:{_rs_color(pct_high, True)}">{_format_num(pct_high)}%</span></div>
                </div>
                <div class="chart-card-canvas" id="chart-ipogap-{ticker_clean}"></div>
            </div>"""

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
<script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
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

  /* ── View Switcher Buttons ── */
  .view-switch {{
    display: inline-flex;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 2px;
    gap: 2px;
  }}
  .view-switch-btn {{
    background: none;
    border: none;
    color: var(--text-muted);
    font-family: var(--mono);
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.15s;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .view-switch-btn:hover {{ color: var(--text); }}
  .view-switch-btn.active {{
    background: var(--surface);
    color: var(--accent);
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }}

  /* ── Chart Grid (Deepvue Style Box Layout) ── */
  .chart-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 16px;
    margin-top: 16px;
  }}
  .chart-grid.cols-2 {{
    grid-template-columns: repeat(2, 1fr);
  }}
  .chart-grid.cols-2 .chart-card-canvas {{
    height: 360px;
  }}
  .chart-grid.cols-3 {{
    grid-template-columns: repeat(3, 1fr);
  }}
  .chart-grid.cols-3 .chart-card-canvas {{
    height: 270px;
  }}
  @media (max-width: 900px) {{
    .chart-grid.cols-2, .chart-grid.cols-3 {{
      grid-template-columns: 1fr;
    }}
  }}
  .chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: border-color 0.2s, box-shadow 0.2s;
  }}
  .chart-card:hover {{
    border-color: rgba(0, 230, 118, 0.3);
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}
  .chart-card-header {{
    padding: 10px 14px;
    background: var(--surface-2);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .chart-card-title {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .chart-card-ticker {{
    font-family: var(--mono);
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }}
  .chart-card-rs {{
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 3px;
    background: rgba(0, 230, 118, 0.12);
    color: var(--accent);
  }}
  .chart-card-meta {{
    font-size: 11px;
    color: var(--text-muted);
    font-family: var(--mono);
  }}
  .chart-card-canvas {{
    width: 100%;
    height: 270px;
    position: relative;
    background: #0d0d14;
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
    <button class="tab-btn active" onclick="showTab('trend')">// Industry Trend</button>
    <button class="tab-btn" onclick="showTab('sectors')">// Sector Indices</button>
    <button class="tab-btn" onclick="showTab('industries')">// Top Industries</button>
    <button class="tab-btn" onclick="showTab('stocks')">// Top Stocks</button>
    <button class="tab-btn" onclick="showTab('leaders')">// Leaders × Top Groups</button>
    <button class="tab-btn" onclick="showTab('basing')" style="color:var(--accent);">// Basing Setups</button>
    <button class="tab-btn" onclick="showTab('launchpad')" style="color:var(--accent);">// Launch Pads</button>
    <button class="tab-btn" onclick="showTab('reclaim10')" style="color:var(--accent);">// 10 SMA Reclaim</button>
    <button class="tab-btn" onclick="showTab('iporeclaim10')" style="color:var(--accent);">// IPO 10 SMA Reclaim</button>
    <button class="tab-btn" onclick="showTab('breakaway')" style="color:#ffee58;">// Breakaway Gaps</button>
    <button class="tab-btn" onclick="showTab('gaphold')" style="color:#ffee58;">// Gap & Hold</button>
    <button class="tab-btn" onclick="showTab('ipogap')" style="color:#ffee58;">// IPO Gaps</button>
  </div>
  
  <!-- Tab: Industry Trend -->
  <div id="tab-trend" class="tab-panel active">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">00</span>
          <span class="section-title">Industry RS Rotation</span>
          <select id="industry-count-filter" onchange="rebuildIndustryChart()" style="margin-left:16px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 12px; border-radius:4px; font-family:var(--mono); font-size:12px; cursor:pointer;">
            <option value="10">Top 10</option>
            <option value="20">Top 20</option>
          </select>
        </div>
      </div>
      <div class="chart-container" style="height:480px;">
        <canvas id="industryChart"></canvas>
      </div>
    </div>
    
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">01</span>
          <span class="section-title">Sector Index RS Rotation (vs Nifty 50)</span>
        </div>
      </div>
      <div class="chart-container" style="height:480px;">
        <canvas id="sectorChart"></canvas>
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
            <option value="35">Max 35% Depth</option>
            <option value="30">Max 30% Depth</option>
            <option value="25">Max 25% Depth</option>
            <option value="20">Max 20% Depth</option>
            <option value="15">Max 15% Depth</option>
          </select>
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('basing', 'table')" id="btn-view-basing-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('basing', 'grid')" id="btn-view-basing-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-basing" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-basing">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-basing">3 View</button>
          </div>
          <select id="grid-ma-filter-basing" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-basing" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="basing-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-basing')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-basing">
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
      <div class="chart-grid" id="view-grid-basing" style="display:none;">
        {basing_cards}
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
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('launchpad', 'table')" id="btn-view-launchpad-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('launchpad', 'grid')" id="btn-view-launchpad-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-launchpad" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-launchpad">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-launchpad">3 View</button>
          </div>
          <select id="grid-ma-filter-launchpad" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-launchpad" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="launchpad-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-launchpad')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-launchpad">
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
      <div class="chart-grid" id="view-grid-launchpad" style="display:none;">
        {launch_pad_cards}
      </div>
    </div>
  </div>

  <!-- Tab: 10 SMA Reclaim -->
  <div id="tab-reclaim10" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">07</span>
          <span class="section-title">10-Day SMA Reclaim ({reclaimed_10_sma_count})</span>
          <select id="reclaim-depth-filter" onchange="filterReclaim()" style="margin-left:16px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="35">Max 35% Depth</option>
            <option value="30">Max 30% Depth</option>
            <option value="25">Max 25% Depth</option>
            <option value="20">Max 20% Depth</option>
            <option value="15">Max 15% Depth</option>
          </select>
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('reclaim10', 'table')" id="btn-view-reclaim10-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('reclaim10', 'grid')" id="btn-view-reclaim10-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-reclaim10" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-reclaim10">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-reclaim10">3 View</button>
          </div>
          <select id="grid-ma-filter-reclaim10" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-reclaim10" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="reclaim-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-reclaim10')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-reclaim10">
        <table id="table-reclaim10">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>10 SMA</th>
              <th>% From High</th>
              <th>3M</th>
              <th>6M</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{reclaimed_10_sma_rows}</tbody>
        </table>
      </div>
      <div class="chart-grid" id="view-grid-reclaim10" style="display:none;">
        {reclaimed_10_sma_cards}
      </div>
    </div>
  </div>

  <!-- Tab: IPO 10 SMA Reclaim -->
  <div id="tab-iporeclaim10" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num">08</span>
          <span class="section-title">IPO 10-Day SMA Reclaim ({ipo_reclaimed_10_sma_count})</span>
          <select id="ipo-reclaim-depth-filter" onchange="filterIPOReclaim()" style="margin-left:16px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="35">Max 35% Depth</option>
            <option value="30">Max 30% Depth</option>
            <option value="25">Max 25% Depth</option>
            <option value="20">Max 20% Depth</option>
            <option value="15">Max 15% Depth</option>
          </select>
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('iporeclaim10', 'table')" id="btn-view-iporeclaim10-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('iporeclaim10', 'grid')" id="btn-view-iporeclaim10-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-iporeclaim10" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-iporeclaim10">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-iporeclaim10">3 View</button>
          </div>
          <select id="grid-ma-filter-iporeclaim10" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-iporeclaim10" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="ipo-reclaim-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-iporeclaim10')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-iporeclaim10">
        <table id="table-iporeclaim10">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>Age</th>
              <th>10 SMA</th>
              <th>% From High</th>
              <th>1M</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{ipo_reclaimed_10_sma_rows}</tbody>
        </table>
      </div>
      <div class="chart-grid" id="view-grid-iporeclaim10" style="display:none;">
        {ipo_reclaimed_10_sma_cards}
      </div>
    </div>
  </div>

  <!-- Tab: Breakaway Gaps -->
  <div id="tab-breakaway" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num" style="color:#ffee58; background:rgba(255,238,88,0.12);">09</span>
          <span class="section-title">Breakaway / High-Volume Gap-Ups ({breakaway_gaps_count})</span>
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('breakaway', 'table')" id="btn-view-breakaway-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('breakaway', 'grid')" id="btn-view-breakaway-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-breakaway" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-breakaway">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-breakaway">3 View</button>
          </div>
          <select id="grid-ma-filter-breakaway" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-breakaway" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="breakaway-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-breakaway')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-breakaway">
        <table id="table-breakaway">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>Gap %</th>
              <th>Gap RVOL</th>
              <th>% From High</th>
              <th>1M</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{breakaway_gaps_rows}</tbody>
        </table>
      </div>
      <div class="chart-grid" id="view-grid-breakaway" style="display:none;">
        {breakaway_gaps_cards}
      </div>
    </div>
  </div>

  <!-- Tab: Gap & Hold -->
  <div id="tab-gaphold" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num" style="color:#ffee58; background:rgba(255,238,88,0.12);">10</span>
          <span class="section-title">Gap & Hold / Consolidation ({gap_and_hold_count})</span>
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('gaphold', 'table')" id="btn-view-gaphold-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('gaphold', 'grid')" id="btn-view-gaphold-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-gaphold" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-gaphold">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-gaphold">3 View</button>
          </div>
          <select id="grid-ma-filter-gaphold" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-gaphold" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="gaphold-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-gaphold')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-gaphold">
        <table id="table-gaphold">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>Initial Gap</th>
              <th>Gap RVOL</th>
              <th>% From High</th>
              <th>1M</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{gap_and_hold_rows}</tbody>
        </table>
      </div>
      <div class="chart-grid" id="view-grid-gaphold" style="display:none;">
        {gap_and_hold_cards}
      </div>
    </div>
  </div>

  <!-- Tab: IPO Gaps -->
  <div id="tab-ipogap" class="tab-panel">
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <div class="section-header-left">
          <span class="section-num" style="color:#ffee58; background:rgba(255,238,88,0.12);">11</span>
          <span class="section-title">IPO Power Gaps ({ipo_gaps_count})</span>
          <div class="view-switch" style="margin-left:12px;">
            <button class="view-switch-btn active" onclick="switchView('ipogap', 'table')" id="btn-view-ipogap-table">≡ Table</button>
            <button class="view-switch-btn" onclick="switchView('ipogap', 'grid')" id="btn-view-ipogap-grid">⊞ Chart Grid</button>
          </div>
          <div class="view-switch col-switch" id="col-switch-ipogap" style="margin-left:8px; display:none;">
            <button class="view-switch-btn" onclick="updateGlobalCols(2)" id="btn-col-2-ipogap">2 View</button>
            <button class="view-switch-btn active" onclick="updateGlobalCols(3)" id="btn-col-3-ipogap">3 View</button>
          </div>
          <select id="grid-ma-filter-ipogap" onchange="updateGlobalMA(this.value)" style="margin-left:10px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="10-50">MAs: 10 EMA + 50 SMA</option>
            <option value="10-20-50">MAs: 10 + 20 + 50</option>
            <option value="all">MAs: All (10, 20, 50, 200)</option>
            <option value="none">MAs: None (Candles Only)</option>
          </select>
          <select id="grid-bars-filter-ipogap" onchange="updateGlobalBars(this.value)" style="margin-left:8px; background:var(--surface-2); color:var(--text); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-family:var(--mono); font-size:12px;">
            <option value="120">Bars: 120 (~6M)</option>
            <option value="60">Bars: 60 (~3M)</option>
            <option value="180">Bars: 180 (~9M)</option>
            <option value="250">Bars: 250 (1 Year)</option>
          </select>
          <span id="ipogap-insights" style="margin-left:16px; font-size:12px; color:var(--text-muted); font-family:var(--mono);"></span>
        </div>
        <button class="copy-all-btn" onclick="copyAllTickers(this, 'table-ipogap')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy
        </button>
      </div>
      <div class="table-wrap" id="view-table-ipogap">
        <table id="table-ipogap">
          <thead>
            <tr>
              <th>#</th>
              <th>Ticker</th>
              <th>Industry</th>
              <th>Sector</th>
              <th>Price</th>
              <th>Age</th>
              <th>Gap %</th>
              <th>Gap RVOL</th>
              <th>% From High</th>
              <th>RS</th>
              <th>Avg Vol</th>
            </tr>
          </thead>
          <tbody>{ipo_gaps_rows}</tbody>
        </table>
      </div>
      <div class="chart-grid" id="view-grid-ipogap" style="display:none;">
        {ipo_gaps_cards}
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
    const cards = document.querySelectorAll('#view-grid-basing .chart-card');
    let visibleCount = 0;
    
    rows.forEach(row => {{
      const pctFromHigh = parseFloat(row.getAttribute('data-pct-from-high'));
      if (pctFromHigh >= maxDepth) {{
        row.style.display = '';
        visibleCount++;
      }} else {{
        row.style.display = 'none';
      }}
    }});

    cards.forEach(card => {{
      const pctFromHigh = parseFloat(card.getAttribute('data-pct-from-high'));
      card.style.display = (pctFromHigh >= maxDepth) ? '' : 'none';
    }});
    
    updateInsights('table-basing', 'basing-insights');
  }}

  // ── 10 SMA Reclaim Filter & Insights ──
  function filterReclaim() {{
    const maxDepth = parseFloat(document.getElementById('reclaim-depth-filter').value) * -1;
    const rows = document.querySelectorAll('#table-reclaim10 tbody tr');
    const cards = document.querySelectorAll('#view-grid-reclaim10 .chart-card');
    let visibleCount = 0;
    
    rows.forEach(row => {{
      const pctFromHigh = parseFloat(row.getAttribute('data-pct-from-high'));
      if (pctFromHigh >= maxDepth) {{
        row.style.display = '';
        visibleCount++;
      }} else {{
        row.style.display = 'none';
      }}
    }});

    cards.forEach(card => {{
      const pctFromHigh = parseFloat(card.getAttribute('data-pct-from-high'));
      card.style.display = (pctFromHigh >= maxDepth) ? '' : 'none';
    }});
    
    updateInsights('table-reclaim10', 'reclaim-insights');
  }}

  // ── IPO 10 SMA Reclaim Filter & Insights ──
  function filterIPOReclaim() {{
    const maxDepth = parseFloat(document.getElementById('ipo-reclaim-depth-filter').value) * -1;
    const rows = document.querySelectorAll('#table-iporeclaim10 tbody tr');
    const cards = document.querySelectorAll('#view-grid-iporeclaim10 .chart-card');
    let visibleCount = 0;
    
    rows.forEach(row => {{
      const pctFromHigh = parseFloat(row.getAttribute('data-pct-from-high'));
      if (pctFromHigh >= maxDepth) {{
        row.style.display = '';
        visibleCount++;
      }} else {{
        row.style.display = 'none';
      }}
    }});

    cards.forEach(card => {{
      const pctFromHigh = parseFloat(card.getAttribute('data-pct-from-high'));
      card.style.display = (pctFromHigh >= maxDepth) ? '' : 'none';
    }});
    
    updateInsights('table-iporeclaim10', 'ipo-reclaim-insights');
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
    filterReclaim();
    filterIPOReclaim();
    updateInsights('table-launchpad', 'launchpad-insights');
    updateInsights('table-breakaway', 'breakaway-insights');
    updateInsights('table-gaphold', 'gaphold-insights');
    updateInsights('table-ipogap', 'ipogap-insights');
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
  const sectorHistoryData = {sector_history_json};
  
  const chartColors = [
      '#00e676', '#ff4081', '#29b6f6', '#ffee58', '#ab47bc',
      '#ff7043', '#26a69a', '#ec407a', '#7e57c2', '#9ccc65',
      '#f06292', '#4dd0e1', '#aed581', '#ffb74d', '#ce93d8',
      '#80cbc4', '#fff176', '#e57373', '#64b5f6', '#81c784'
  ];
  
  // Shorten long industry names for chart legend
  function shortName(name) {{
      const map = {{
          'Electronic Production Equipment': 'Elec Prod Equip',
          'Electronics Distributors': 'Elec Distrib',
          'Electronic Components': 'Elec Components',
          'Electronic Equipment/Instruments': 'Elec Equip/Instr',
          'Oilfield Services/Equipment': 'Oilfield Svcs',
          'Chemicals: Specialty': 'Specialty Chem',
          'Chemicals: Major': 'Major Chem',
          'Pharmaceuticals: Major': 'Pharma Major',
          'Pharmaceuticals: Other': 'Pharma Other',
          'Wholesale Distributors': 'Wholesale Dist',
          'Other Consumer Specialties': 'Consumer Spec',
          'Investment Banks/Brokers': 'Inv Banks/Brkrs',
          'Trucks/Construction/Farm Machinery': 'Trucks/Farm Mach',
          'Oil Refining/Marketing': 'Oil Refining',
          'Aerospace & Defense': 'Aero & Defense',
          'Internet Software/Services': 'Internet SW/Svcs',
          'Medical/Nursing Services': 'Medical Svcs',
          'Nifty Financial Services': 'Fin Services',
          'Nifty Consumer Durables': 'Consumer Dur',
          'Nifty Private Bank': 'Private Bank',
          'Nifty PSU Bank': 'PSU Bank',
          'Nifty Oil & Gas': 'Oil & Gas',
          'Nifty Commodities': 'Commodities',
          'Nifty Consumption': 'Consumption',
          'Nifty Healthcare': 'Healthcare',
      }};
      return map[name] || name.replace('Nifty ', '');
  }}
  
  // Common chart config
  function getChartOptions(yLabel) {{
      return {{
          responsive: true,
          maintainAspectRatio: false,
          interaction: {{
              mode: 'index',
              intersect: false
          }},
          plugins: {{
              legend: {{
                  position: 'bottom',
                  labels: {{
                      color: '#8b9bb4',
                      font: {{ family: "'JetBrains Mono', monospace", size: 11 }},
                      padding: 16,
                      usePointStyle: true,
                      pointStyle: 'circle'
                  }}
              }},
              tooltip: {{
                  backgroundColor: '#1a1a26',
                  titleColor: '#e8e8ed',
                  bodyColor: '#8b9bb4',
                  borderColor: 'rgba(255,255,255,0.1)',
                  borderWidth: 1,
                  titleFont: {{ family: "'JetBrains Mono', monospace", size: 12 }},
                  bodyFont: {{ family: "'JetBrains Mono', monospace", size: 11 }},
                  padding: 12,
                  callbacks: {{
                      label: function(ctx) {{
                          return ctx.dataset.label + ': ' + (ctx.parsed.y !== null ? ctx.parsed.y.toFixed(1) : '—');
                      }}
                  }}
              }}
          }},
          scales: {{
              x: {{
                  grid: {{ color: 'rgba(255,255,255,0.04)' }},
                  ticks: {{
                      color: '#6b6b7b',
                      font: {{ family: "'JetBrains Mono', monospace", size: 10 }},
                      maxRotation: 45,
                      autoSkip: true,
                      maxTicksLimit: 15
                  }}
              }},
              y: {{
                  grid: {{ color: 'rgba(255,255,255,0.04)' }},
                  ticks: {{
                      color: '#6b6b7b',
                      font: {{ family: "'JetBrains Mono', monospace", size: 10 }}
                  }},
                  title: {{
                      display: !!yLabel,
                      text: yLabel || '',
                      color: '#6b6b7b',
                      font: {{ family: "'JetBrains Mono', monospace", size: 11 }}
                  }}
              }}
          }}
      }};
  }}
  
  // ── Industry Chart (with Top 10/20 toggle) ──
  let industryChartInstance = null;
  
  function rebuildIndustryChart() {{
      const count = parseInt(document.getElementById('industry-count-filter').value) || 10;
      
      if (historyData.length === 0) return;
      
      const dates = [...new Set(historyData.map(d => d.Date))].sort();
      const latestDate = dates[dates.length - 1];
      
      const latestRanks = historyData.filter(d => d.Date === latestDate)
                                     .sort((a, b) => a.Rank - b.Rank)
                                     .map(d => d.Industry);
                                     
      const topN = latestRanks.slice(0, count);
      
      const datasets = topN.map((ind, i) => {{
          const indData = dates.map(date => {{
              const row = historyData.find(d => d.Date === date && d.Industry === ind);
              return row ? row.Median_RS : null;
          }});
          
          return {{
              label: shortName(ind),
              data: indData,
              borderColor: chartColors[i % chartColors.length],
              backgroundColor: 'transparent',
              borderWidth: 2,
              pointRadius: 2,
              pointHoverRadius: 5,
              tension: 0.2
          }};
      }});
      
      // Destroy old chart if exists
      if (industryChartInstance) {{
          industryChartInstance.destroy();
      }}
      
      industryChartInstance = new Chart(document.getElementById('industryChart'), {{
          type: 'line',
          data: {{
              labels: dates,
              datasets: datasets
          }},
          options: getChartOptions('Median RS Percentile')
      }});
  }}
  
  // Build industry chart on load
  rebuildIndustryChart();
  
  // ── Sector Chart ──
  if (sectorHistoryData && sectorHistoryData.length > 0) {{
      const dates = [...new Set(sectorHistoryData.map(d => d.Date))].sort();
      const latestDate = dates[dates.length - 1];
      
      const latestRanks = sectorHistoryData.filter(d => d.Date === latestDate)
                                     .sort((a, b) => a.Rank - b.Rank)
                                     .map(d => d.Sector);
                                     
      const topSectors = latestRanks;
      
      const datasets = topSectors.map((sec, i) => {{
          const secData = dates.map(date => {{
              const row = sectorHistoryData.find(d => d.Date === date && d.Sector === sec);
              return row ? row.Composite_RS : null;
          }});
          
          return {{
              label: shortName(sec),
              data: secData,
              borderColor: chartColors[i % chartColors.length],
              backgroundColor: 'transparent',
              borderWidth: 2,
              pointRadius: 2,
              pointHoverRadius: 5,
              tension: 0.2
          }};
      }});
      
      new Chart(document.getElementById('sectorChart'), {{
          type: 'line',
          data: {{
              labels: dates,
              datasets: datasets
          }},
          options: getChartOptions('Composite RS Spread (%)')
      }});
  }}

  // ── Candle & Indicator Data for Chart Grid ──
  const candlesData = {candles_json};
  const chartsCreated = {{}};
  let currentMAMode = '10-50';
  let currentBarsCount = 120;
  let currentGridCols = 3;

  function switchView(tabKey, mode) {{
    const tblWrap = document.getElementById(`view-table-${{tabKey}}`);
    const gridWrap = document.getElementById(`view-grid-${{tabKey}}`);
    const btnTable = document.getElementById(`btn-view-${{tabKey}}-table`);
    const btnGrid = document.getElementById(`btn-view-${{tabKey}}-grid`);
    const colSwitch = document.getElementById(`col-switch-${{tabKey}}`);

    if (mode === 'grid') {{
      tblWrap.style.display = 'none';
      gridWrap.style.display = 'grid';
      btnTable.classList.remove('active');
      btnGrid.classList.add('active');
      if (colSwitch) colSwitch.style.display = 'inline-flex';
      renderGridCharts(tabKey);
      setTimeout(() => resizeTabCharts(tabKey), 20);
    }} else {{
      tblWrap.style.display = 'block';
      gridWrap.style.display = 'none';
      btnTable.classList.add('active');
      btnGrid.classList.remove('active');
      if (colSwitch) colSwitch.style.display = 'none';
    }}
  }}

  function updateGlobalCols(cols) {{
    currentGridCols = cols;
    ['basing', 'launchpad', 'reclaim10', 'iporeclaim10', 'breakaway', 'gaphold', 'ipogap'].forEach(k => {{
      const grid = document.getElementById(`view-grid-${{k}}`);
      if (grid) {{
        if (cols === 2) {{
          grid.classList.add('cols-2');
          grid.classList.remove('cols-3');
        }} else {{
          grid.classList.add('cols-3');
          grid.classList.remove('cols-2');
        }}
      }}
      const b2 = document.getElementById(`btn-col-2-${{k}}`);
      const b3 = document.getElementById(`btn-col-3-${{k}}`);
      if (b2 && b3) {{
        if (cols === 2) {{
          b2.classList.add('active');
          b3.classList.remove('active');
        }} else {{
          b3.classList.add('active');
          b2.classList.remove('active');
        }}
      }}
    }});

    // Resize all existing charts to fit their new container width and height
    setTimeout(() => {{
      Object.keys(chartsCreated).forEach(canvasId => {{
        const cObj = chartsCreated[canvasId];
        const container = document.getElementById(canvasId);
        if (cObj && container) {{
          const targetHeight = cols === 2 ? 360 : 270;
          cObj.chart.resize(container.clientWidth || (cols === 2 ? 650 : 420), targetHeight);
          cObj.chart.timeScale().fitContent();
        }}
      }});
    }}, 40);
  }}

  function resizeTabCharts(tabKey) {{
    const gridWrap = document.getElementById(`view-grid-${{tabKey}}`);
    if (!gridWrap) return;
    const cards = gridWrap.querySelectorAll('.chart-card');
    cards.forEach(card => {{
      const ticker = card.getAttribute('data-ticker');
      const canvasId = `chart-${{tabKey}}-${{ticker}}`;
      const cObj = chartsCreated[canvasId];
      const container = document.getElementById(canvasId);
      if (cObj && container) {{
        const targetHeight = currentGridCols === 2 ? 360 : 270;
        cObj.chart.resize(container.clientWidth, targetHeight);
      }}
    }});
  }}

  function updateGlobalMA(val) {{
    currentMAMode = val;
    // sync all MA dropdowns across tabs
    ['basing', 'launchpad', 'reclaim10', 'iporeclaim10', 'breakaway', 'gaphold', 'ipogap'].forEach(k => {{
      const sel = document.getElementById(`grid-ma-filter-${{k}}`);
      if (sel) sel.value = val;
    }});

    // Update lines visibility across all instantiated charts
    Object.keys(chartsCreated).forEach(canvasId => {{
      const cObj = chartsCreated[canvasId];
      if (!cObj) return;
      cObj.ema10.applyOptions({{ visible: (val === '10-50' || val === '10-20-50' || val === 'all') }});
      cObj.ema20.applyOptions({{ visible: (val === '10-20-50' || val === 'all') }});
      cObj.sma50.applyOptions({{ visible: (val === '10-50' || val === '10-20-50' || val === 'all') }});
      cObj.sma200.applyOptions({{ visible: (val === 'all') }});
    }});
  }}

  function updateGlobalBars(val) {{
    const count = parseInt(val, 10);
    currentBarsCount = count;
    // sync all bars dropdowns across tabs
    ['basing', 'launchpad', 'reclaim10', 'iporeclaim10', 'breakaway', 'gaphold', 'ipogap'].forEach(k => {{
      const sel = document.getElementById(`grid-bars-filter-${{k}}`);
      if (sel) sel.value = val;
    }});

    // Update time range / visible bars across all charts
    Object.keys(chartsCreated).forEach(canvasId => {{
      const cObj = chartsCreated[canvasId];
      if (!cObj || !cObj.bars || cObj.bars.length === 0) return;
      const bLen = cObj.bars.length;
      const fromIdx = Math.max(0, bLen - count);
      cObj.chart.timeScale().setVisibleRange({{
        from: cObj.bars[fromIdx].time,
        to: cObj.bars[bLen - 1].time
      }});
    }});
  }}

  function renderGridCharts(tabKey) {{
    const gridWrap = document.getElementById(`view-grid-${{tabKey}}`);
    if (!gridWrap || !window.LightweightCharts) return;

    const cards = gridWrap.querySelectorAll('.chart-card');
    cards.forEach(card => {{
      const ticker = card.getAttribute('data-ticker');
      const canvasId = `chart-${{tabKey}}-${{ticker}}`;
      const container = document.getElementById(canvasId);

      if (!container || chartsCreated[canvasId]) return;

      const bars = candlesData[ticker];
      if (!bars || bars.length === 0) {{
        container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-muted);font-size:12px;font-family:var(--mono);">No chart data available</div>';
        return;
      }}

      try {{
        const targetHeight = currentGridCols === 2 ? 360 : 270;
        const chart = LightweightCharts.createChart(container, {{
          width: container.clientWidth || (currentGridCols === 2 ? 650 : 400),
          height: targetHeight,
          layout: {{
            background: {{ color: '#0e0e17' }},
            textColor: '#8e8ea0',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
          }},
          grid: {{
            vertLines: {{ color: 'rgba(255,255,255,0.03)' }},
            horzLines: {{ color: 'rgba(255,255,255,0.03)' }},
          }},
          crosshair: {{
            mode: LightweightCharts.CrosshairMode.Normal,
          }},
          rightPriceScale: {{
            borderColor: 'rgba(255,255,255,0.06)',
            scaleMargins: {{ top: 0.1, bottom: 0.25 }},
          }},
          timeScale: {{
            borderColor: 'rgba(255,255,255,0.06)',
            visible: true,
          }},
        }});

        // 1. Candlestick series (ONLY price tag visible on the price axis)
        const candleSeries = chart.addCandlestickSeries({{
          upColor: '#00e676',
          downColor: '#ef5350',
          borderVisible: false,
          wickUpColor: '#00e676',
          wickDownColor: '#ef5350',
          lastValueVisible: true,
          priceLineVisible: false,
        }});
        candleSeries.setData(bars.map(b => ({{
          time: b.time, open: b.open, high: b.high, low: b.low, close: b.close
        }})));

        // 2. Volume series at bottom
        const volumeSeries = chart.addHistogramSeries({{
          priceFormat: {{ type: 'volume' }},
          priceScaleId: '',
          lastValueVisible: true,
          scaleMargins: {{ top: 0.8, bottom: 0 }},
        }});
        volumeSeries.setData(bars.map(b => ({{
          time: b.time,
          value: b.volume,
          color: b.close >= b.open ? 'rgba(0, 230, 118, 0.4)' : 'rgba(239, 83, 80, 0.4)'
        }})));

        // 3. 10 EMA (cyan) - axis label and price tag disabled for clean view
        const ema10Series = chart.addLineSeries({{
          color: '#00e5ff',
          lineWidth: 1.5,
          lastValueVisible: false,
          priceLineVisible: false,
          visible: (currentMAMode === '10-50' || currentMAMode === '10-20-50' || currentMAMode === 'all')
        }});
        ema10Series.setData(bars.filter(b => b.ema10 !== null).map(b => ({{ time: b.time, value: b.ema10 }})));

        // 4. 20 EMA (purple)
        const ema20Series = chart.addLineSeries({{
          color: '#b388ff',
          lineWidth: 1.5,
          lastValueVisible: false,
          priceLineVisible: false,
          visible: (currentMAMode === '10-20-50' || currentMAMode === 'all')
        }});
        ema20Series.setData(bars.filter(b => b.ema20 !== null).map(b => ({{ time: b.time, value: b.ema20 }})));

        // 5. 50 SMA (orange)
        const sma50Series = chart.addLineSeries({{
          color: '#ff9100',
          lineWidth: 1.5,
          lastValueVisible: false,
          priceLineVisible: false,
          visible: (currentMAMode === '10-50' || currentMAMode === '10-20-50' || currentMAMode === 'all')
        }});
        sma50Series.setData(bars.filter(b => b.sma50 !== null).map(b => ({{ time: b.time, value: b.sma50 }})));

        // 6. 200 SMA (white)
        const sma200Series = chart.addLineSeries({{
          color: '#ffffff',
          lineWidth: 1.5,
          lastValueVisible: false,
          priceLineVisible: false,
          visible: (currentMAMode === 'all')
        }});
        sma200Series.setData(bars.filter(b => b.sma200 !== null).map(b => ({{ time: b.time, value: b.sma200 }})));

        // Apply initial bars view range
        const bLen = bars.length;
        const fromIdx = Math.max(0, bLen - currentBarsCount);
        chart.timeScale().setVisibleRange({{
          from: bars[fromIdx].time,
          to: bars[bLen - 1].time
        }});

        chartsCreated[canvasId] = {{
          chart: chart,
          bars: bars,
          candleSeries: candleSeries,
          volumeSeries: volumeSeries,
          ema10: ema10Series,
          ema20: ema20Series,
          sma50: sma50Series,
          sma200: sma200Series
        }};
      }} catch (err) {{
        console.error('Error rendering chart for ' + ticker, err);
      }}
    }});
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
