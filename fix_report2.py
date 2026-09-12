import re

with open('rs_system/report.py', 'r') as f:
    code = f.read()

# 1. Update function signature
code = code.replace("def generate_dashboard(stock_rs: pd.DataFrame, industry_rs: pd.DataFrame, sector_rs: pd.DataFrame, leaders: pd.DataFrame, history_df: pd.DataFrame = None, basing_df: pd.DataFrame = None, launch_pad_df: pd.DataFrame = None) -> str:",
                    "def generate_dashboard(stock_rs: pd.DataFrame, industry_rs: pd.DataFrame, sector_rs: pd.DataFrame, leaders: pd.DataFrame, history_df: pd.DataFrame = None, sector_history_df: pd.DataFrame = None, basing_df: pd.DataFrame = None, launch_pad_df: pd.DataFrame = None) -> str:")

# 2. Convert sector history to JSON
history_json_block = """    # ── History Data for Chart.js ──
    history_json = "[]"
    if history_df is not None and not history_df.empty:
        history_df = history_df.sort_values("Date")
        history_json = history_df.to_json(orient="records")
        
    sector_history_json = "[]"
    if sector_history_df is not None and not sector_history_df.empty:
        sector_history_df = sector_history_df.sort_values("Date")
        sector_history_json = sector_history_df.to_json(orient="records")
"""
code = re.sub(r'    # ── History Data for Chart.js ──.*?history_json = history_df.to_json\(orient="records"\)', history_json_block, code, flags=re.DOTALL)

# 3. Add Canvas HTML
html_canvas_replacement = """  <!-- Tab: Industry Trend -->
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
    
    <div class="section" style="margin-top: 24px;">
      <div class="section-header">
        <span class="section-num">00.5</span>
        <span class="section-title">Historical Sector Rotation</span>
      </div>
      <div class="chart-container">
        <canvas id="sectorChart"></canvas>
      </div>
    </div>
  </div>
"""
code = re.sub(r'  <!-- Tab: Industry Trend -->.*?</div>\n    </div>\n  </div>\n', html_canvas_replacement, code, flags=re.DOTALL)

# 4. Add Javascript for Sector chart
js_chart_replacement = """  // ── Chart.js Logic ──
  const historyData = {history_json};
  const sectorHistoryData = {sector_history_json};
  
  if (historyData.length > 0) {{
      // Group by Industry
      const industries = [...new Set(historyData.map(d => d.Industry))];
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
              backgroundColor: 'transparent',
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.1
          }};
      }});
      
      new Chart(document.getElementById('industryChart'), {{
          type: 'line',
          data: {{
              labels: dates,
              datasets: datasets
          }},
          options: {{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {{
                  legend: {{
                      position: 'right',
                      labels: {{ color: '#8b9bb4', font: {{ family: "'JetBrains Mono', monospace", size: 10 }} }}
                  }}
              }},
              scales: {{
                  x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8b9bb4' }} }},
                  y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8b9bb4' }} }}
              }}
          }}
      }});
  }}
  
  if (sectorHistoryData && sectorHistoryData.length > 0) {{
      // Group by Sector
      const dates = [...new Set(sectorHistoryData.map(d => d.Date))].sort();
      const latestDate = dates[dates.length - 1];
      
      const latestRanks = sectorHistoryData.filter(d => d.Date === latestDate)
                                     .sort((a, b) => a.Rank - b.Rank)
                                     .map(d => d.Sector);
                                     
      const topSectors = latestRanks.slice(0, 10);
      
      const colors = [
          '#00e676', '#ff4081', '#29b6f6', '#ffee58', '#ab47bc',
          '#ff7043', '#26a69a', '#ec407a', '#7e57c2', '#9ccc65'
      ];
      
      const datasets = topSectors.map((sec, i) => {{
          const secData = dates.map(date => {{
              const row = sectorHistoryData.find(d => d.Date === date && d.Sector === sec);
              return row ? row.Composite_RS : null;
          }});
          
          return {{
              label: sec,
              data: secData,
              borderColor: colors[i % colors.length],
              backgroundColor: 'transparent',
              borderWidth: 2,
              pointRadius: 3,
              tension: 0.1
          }};
      }});
      
      new Chart(document.getElementById('sectorChart'), {{
          type: 'line',
          data: {{
              labels: dates,
              datasets: datasets
          }},
          options: {{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {{
                  legend: {{
                      position: 'right',
                      labels: {{ color: '#8b9bb4', font: {{ family: "'JetBrains Mono', monospace", size: 10 }} }}
                  }}
              }},
              scales: {{
                  x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8b9bb4' }} }},
                  y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#8b9bb4' }} }}
              }}
          }}
      }});
  }}
"""
code = re.sub(r'  // ── Chart\.js Logic ──.*?(?=</script>)', js_chart_replacement, code, flags=re.DOTALL)

code = code.replace("{history_json}", "{history_json}").replace("{sector_history_json}", "{sector_history_json}")

with open('rs_system/report.py', 'w') as f:
    f.write(code)
print("Updated report.py for Sector Rotation Chart.")
