"""Build a self-contained interactive HTML dashboard from data/tickers.csv.

Reads ticker/sector/industry/description data and embeds it as JSON inside a
single HTML file (CSS + JS inlined). The output opens directly in any browser,
no server or external dependencies required.

Usage:
    python src/build_dashboard.py

Output:
    data/dashboard.html
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "tickers.csv"
OUT_PATH = ROOT / "data" / "dashboard.html"


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        rows = [
            {
                "ticker": r["ticker"].strip(),
                "sector": r["sector"].strip(),
                "industry": r["industry"].strip(),
                "description": r["description"].strip(),
            }
            for r in csv.DictReader(f)
        ]
    rows.sort(key=lambda r: r["ticker"])
    return rows


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ticker Dashboard &mdash; Sectors &amp; Industries</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1" integrity="sha384-jb8JQMbMoBUzgWatfe6COACi2ljcDdZQ2OxczGA3bGNeWe+6DChMTBJemed7ZnvJ" crossorigin="anonymous"></script>
<style>
:root {
  --bg-primary:#f4f6fa; --bg-card:#ffffff; --bg-header:#16213e;
  --text-primary:#1f2933; --text-secondary:#6b7280; --text-on-dark:#ffffff;
  --border:#e5e7eb; --accent:#4C72B0;
  --gap:16px; --radius:10px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:var(--bg-primary); color:var(--text-primary); line-height:1.5; }
.dashboard-container { max-width:1400px; margin:0 auto; padding:var(--gap); }
.dashboard-header { background:var(--bg-header); color:var(--text-on-dark);
  padding:22px 26px; border-radius:var(--radius); margin-bottom:var(--gap); }
.dashboard-header h1 { font-size:22px; font-weight:600; }
.dashboard-header p { font-size:13px; opacity:.7; margin-top:4px; }

.kpi-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:var(--gap); margin-bottom:var(--gap); }
.kpi-card { background:var(--bg-card); border-radius:var(--radius); padding:20px 24px;
  box-shadow:0 1px 3px rgba(0,0,0,.08); }
.kpi-label { font-size:12px; color:var(--text-secondary); text-transform:uppercase;
  letter-spacing:.5px; margin-bottom:6px; }
.kpi-value { font-size:30px; font-weight:700; }

.chart-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(400px,1fr));
  gap:var(--gap); margin-bottom:var(--gap); }
.card { background:var(--bg-card); border-radius:var(--radius); padding:20px 24px;
  box-shadow:0 1px 3px rgba(0,0,0,.08); }
.card h3 { font-size:14px; font-weight:600; margin-bottom:16px; }
.chart-box { position:relative; height:340px; }

.table-section { margin-bottom:var(--gap); }
.data-table { width:100%; border-collapse:collapse; font-size:13px; }
.data-table thead th { text-align:left; padding:9px 12px; border-bottom:2px solid var(--border);
  color:var(--text-secondary); font-weight:600; font-size:11px; text-transform:uppercase;
  letter-spacing:.5px; cursor:pointer; user-select:none; white-space:nowrap; }
.data-table thead th:hover { color:var(--text-primary); }
.data-table tbody td { padding:9px 12px; border-bottom:1px solid #f0f0f0; }
.data-table tbody tr:hover { background:#f8f9fa; }
.data-table td.num, .data-table th.num { text-align:right; }
.bar-cell { position:relative; min-width:120px; }
.bar-cell .bar { position:absolute; left:0; top:0; bottom:0; background:var(--accent);
  opacity:.15; border-radius:3px; z-index:0; }
.bar-cell span { position:relative; z-index:1; }

.two-col { display:grid; grid-template-columns:repeat(auto-fit,minmax(380px,1fr)); gap:var(--gap); }

/* Browser */
.browser-controls { display:flex; gap:14px; flex-wrap:wrap; margin-bottom:16px; align-items:flex-end; }
.filter-group { display:flex; flex-direction:column; gap:4px; }
.filter-group label { font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:.5px; }
.filter-group select, .filter-group input {
  padding:8px 10px; border:1px solid var(--border); border-radius:6px; font-size:13px;
  background:#fff; min-width:200px; }
.browser-layout { display:grid; grid-template-columns:340px 1fr; gap:var(--gap); }
.company-list { max-height:520px; overflow-y:auto; border:1px solid var(--border); border-radius:8px; }
.company-item { padding:10px 14px; border-bottom:1px solid #f0f0f0; cursor:pointer; }
.company-item:hover { background:#f0f4fa; }
.company-item.active { background:#e3ecf9; }
.company-item .tk { font-weight:700; font-size:14px; }
.company-item .meta { font-size:11px; color:var(--text-secondary); }
.detail-panel { padding:6px 4px; }
.detail-panel .tk { font-size:26px; font-weight:700; }
.detail-panel .tags { margin:10px 0 16px; display:flex; gap:8px; flex-wrap:wrap; }
.tag { background:#eef2f9; color:#374151; font-size:12px; padding:4px 10px; border-radius:20px; }
.detail-panel .desc { font-size:14px; color:#374151; line-height:1.65; }
.detail-empty { color:var(--text-secondary); font-size:14px; padding:30px; text-align:center; }
.list-count { font-size:12px; color:var(--text-secondary); margin-bottom:8px; }

.dashboard-footer { text-align:center; color:var(--text-secondary); font-size:12px; padding:16px; }
@media (max-width:768px){ .browser-layout{ grid-template-columns:1fr; } .chart-box{ height:300px; } }
</style>
</head>
<body>
<div class="dashboard-container">
  <header class="dashboard-header">
    <h1>Ticker Dashboard</h1>
    <p>Sector &amp; industry breakdown of __TOTAL__ companies &middot; generated from data/tickers.csv</p>
  </header>

  <section class="kpi-row">
    <div class="kpi-card"><div class="kpi-label">Companies</div><div class="kpi-value" id="kpi-companies"></div></div>
    <div class="kpi-card"><div class="kpi-label">Sectors</div><div class="kpi-value" id="kpi-sectors"></div></div>
    <div class="kpi-card"><div class="kpi-label">Industries</div><div class="kpi-value" id="kpi-industries"></div></div>
    <div class="kpi-card"><div class="kpi-label">Largest Sector</div><div class="kpi-value" id="kpi-top" style="font-size:20px"></div></div>
  </section>

  <section class="chart-row">
    <div class="card"><h3>Companies by Sector</h3><div class="chart-box"><canvas id="sectorChart"></canvas></div></div>
    <div class="card"><h3>Top 15 Industries</h3><div class="chart-box"><canvas id="industryChart"></canvas></div></div>
  </section>

  <section class="two-col table-section">
    <div class="card">
      <h3>Sectors &mdash; count &amp; %</h3>
      <table class="data-table" id="sectorTable"></table>
    </div>
    <div class="card">
      <h3>Industries &mdash; count &amp; %</h3>
      <table class="data-table" id="industryTable"></table>
    </div>
  </section>

  <section class="card table-section">
    <h3>Browse Companies</h3>
    <div class="browser-controls">
      <div class="filter-group">
        <label for="fSector">Sector</label>
        <select id="fSector"><option value="">All sectors</option></select>
      </div>
      <div class="filter-group">
        <label for="fIndustry">Industry</label>
        <select id="fIndustry"><option value="">All industries</option></select>
      </div>
      <div class="filter-group">
        <label for="fSearch">Search</label>
        <input type="text" id="fSearch" placeholder="ticker or text in description...">
      </div>
    </div>
    <div class="browser-layout">
      <div>
        <div class="list-count" id="listCount"></div>
        <div class="company-list" id="companyList"></div>
      </div>
      <div class="detail-panel" id="detailPanel">
        <div class="detail-empty">Select a company to read its description.</div>
      </div>
    </div>
  </section>

  <footer class="dashboard-footer">Self-contained &middot; data embedded &middot; no server required</footer>
</div>

<script>
const DATA = __DATA__;
const COLORS = ['#4C72B0','#DD8452','#55A868','#C44E52','#8172B3','#937860',
                '#DA8BC3','#8C8C8C','#CCB974','#64B5CD','#4E79A7','#F28E2B'];

function countBy(rows, key){
  const m = {};
  rows.forEach(r => { m[r[key]] = (m[r[key]]||0)+1; });
  return Object.entries(m).sort((a,b)=>b[1]-a[1]);
}

const total = DATA.length;
const sectorCounts = countBy(DATA,'sector');
const industryCounts = countBy(DATA,'industry');

document.getElementById('kpi-companies').textContent = total;
document.getElementById('kpi-sectors').textContent = sectorCounts.length;
document.getElementById('kpi-industries').textContent = industryCounts.length;
document.getElementById('kpi-top').textContent = sectorCounts[0][0]+' ('+sectorCounts[0][1]+')';

// ---- Charts ----
new Chart(document.getElementById('sectorChart'), {
  type:'doughnut',
  data:{ labels:sectorCounts.map(s=>s[0]), datasets:[{ data:sectorCounts.map(s=>s[1]),
    backgroundColor:sectorCounts.map((_,i)=>COLORS[i%COLORS.length]), borderColor:'#fff', borderWidth:2 }] },
  options:{ responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{ position:'right', labels:{ usePointStyle:true, padding:10, font:{size:11} } },
      tooltip:{ callbacks:{ label:c=>{ const p=(c.parsed/total*100).toFixed(1); return c.label+': '+c.parsed+' ('+p+'%)'; } } } } }
});

const topInd = industryCounts.slice(0,15);
new Chart(document.getElementById('industryChart'), {
  type:'bar',
  data:{ labels:topInd.map(s=>s[0]), datasets:[{ data:topInd.map(s=>s[1]),
    backgroundColor:'#4C72B0CC', borderColor:'#4C72B0', borderWidth:1, borderRadius:4 }] },
  options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{display:false},
      tooltip:{ callbacks:{ label:c=>{ const p=(c.parsed.x/total*100).toFixed(1); return c.parsed.x+' ('+p+'%)'; } } } },
    scales:{ x:{ beginAtZero:true, ticks:{precision:0} }, y:{ ticks:{font:{size:11}} } } }
});

// ---- Breakdown tables ----
function renderBreakdownTable(elId, counts){
  const max = counts[0][1];
  let html = '<thead><tr><th data-c="0">Name</th><th class="num" data-c="1">Count</th><th class="num" data-c="2">%</th></tr></thead><tbody>';
  counts.forEach(([name,n])=>{
    const pct=(n/total*100).toFixed(1);
    html += '<tr><td>'+esc(name)+'</td>'
      + '<td class="num bar-cell"><div class="bar" style="width:'+(n/max*100)+'%"></div><span>'+n+'</span></td>'
      + '<td class="num">'+pct+'%</td></tr>';
  });
  html += '</tbody>';
  const t = document.getElementById(elId);
  t.innerHTML = html;
  makeSortable(t, counts.map(([name,n])=>[name,n,n/total*100]));
}

function makeSortable(table, rows){
  let dir = {};
  table.querySelectorAll('th').forEach(th=>{
    th.addEventListener('click',()=>{
      const c = +th.dataset.c;
      dir[c] = dir[c]==='asc' ? 'desc' : 'asc';
      const s = [...rows].sort((a,b)=>{
        const x=a[c], y=b[c];
        const cmp = (typeof x==='number') ? x-y : String(x).localeCompare(String(y));
        return dir[c]==='asc'?cmp:-cmp;
      });
      const max = Math.max(...rows.map(r=>r[1]));
      const body = s.map(([name,n,pct])=>'<tr><td>'+esc(name)+'</td>'
        +'<td class="num bar-cell"><div class="bar" style="width:'+(n/max*100)+'%"></div><span>'+n+'</span></td>'
        +'<td class="num">'+pct.toFixed(1)+'%</td></tr>').join('');
      table.querySelector('tbody').innerHTML = body;
    });
  });
}

renderBreakdownTable('sectorTable', sectorCounts);
renderBreakdownTable('industryTable', industryCounts);

// ---- Company browser ----
const fSector = document.getElementById('fSector');
const fIndustry = document.getElementById('fIndustry');
const fSearch = document.getElementById('fSearch');
const listEl = document.getElementById('companyList');
const countEl = document.getElementById('listCount');
const detailEl = document.getElementById('detailPanel');

sectorCounts.map(s=>s[0]).sort().forEach(s=>fSector.add(new Option(s,s)));

function refreshIndustryOptions(){
  const sec = fSector.value;
  const prev = fIndustry.value;
  const inds = [...new Set(DATA.filter(r=>!sec||r.sector===sec).map(r=>r.industry))].sort();
  fIndustry.innerHTML = '<option value="">All industries</option>';
  inds.forEach(i=>fIndustry.add(new Option(i,i)));
  if (inds.includes(prev)) fIndustry.value = prev;
}

function currentRows(){
  const sec=fSector.value, ind=fIndustry.value, q=fSearch.value.trim().toLowerCase();
  return DATA.filter(r=>{
    if(sec && r.sector!==sec) return false;
    if(ind && r.industry!==ind) return false;
    if(q && !(r.ticker.toLowerCase().includes(q) || r.description.toLowerCase().includes(q))) return false;
    return true;
  });
}

function renderList(){
  const rows = currentRows();
  countEl.textContent = rows.length+' compan'+(rows.length===1?'y':'ies');
  listEl.innerHTML = rows.map(r=>
    '<div class="company-item" data-tk="'+r.ticker+'"><div class="tk">'+esc(r.ticker)+'</div>'
    +'<div class="meta">'+esc(r.sector)+' &middot; '+esc(r.industry)+'</div></div>').join('')
    || '<div class="detail-empty">No matches.</div>';
  listEl.querySelectorAll('.company-item').forEach(el=>{
    el.addEventListener('click',()=>showDetail(el.dataset.tk, el));
  });
}

function showDetail(tk, el){
  listEl.querySelectorAll('.company-item').forEach(x=>x.classList.remove('active'));
  if(el) el.classList.add('active');
  const r = DATA.find(d=>d.ticker===tk);
  if(!r){ return; }
  detailEl.innerHTML = '<div class="tk">'+esc(r.ticker)+'</div>'
    +'<div class="tags"><span class="tag">'+esc(r.sector)+'</span><span class="tag">'+esc(r.industry)+'</span></div>'
    +'<div class="desc">'+esc(r.description)+'</div>';
}

function esc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

fSector.addEventListener('change',()=>{ refreshIndustryOptions(); renderList(); });
fIndustry.addEventListener('change', renderList);
fSearch.addEventListener('input', renderList);

refreshIndustryOptions();
renderList();
</script>
</body>
</html>
"""


def main() -> None:
    rows = load_rows(CSV_PATH)
    data_json = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    html = (
        HTML_TEMPLATE
        .replace("__DATA__", data_json)
        .replace("__TOTAL__", str(len(rows)))
    )
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(rows)} companies, {OUT_PATH.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
