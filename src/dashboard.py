"""Build a self-contained planning dashboard from verified project outputs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build(results: Path) -> None:
    daily = pd.read_csv(results / "daily_forecasts.csv")
    # Daily store-series data is needed to filter the chart without recomputing forecasts.
    store_daily = pd.read_csv(results / "store_daily_forecasts.csv")
    metrics = pd.read_csv(results / "metrics.csv")
    exceptions = pd.read_csv(results / "priority_exceptions.csv").head(15)
    payload = {
        "daily": store_daily.to_dict(orient="records"),
        "metrics": metrics.to_dict(orient="records"),
        "exceptions": exceptions.fillna(0).to_dict(orient="records"),
        "overall": daily.to_dict(orient="records"),
    }
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Retail Demand Planning | M5 Case Study</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#17273b;background:#f5f7f8}
*{box-sizing:border-box}body{margin:0}header{background:#122f3d;color:white;padding:24px max(28px,calc((100% - 1200px)/2))}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#9dd8c8;font-weight:750}
h1{font-size:clamp(26px,3vw,38px);margin:9px 0 6px;letter-spacing:-.03em}header p{max-width:850px;color:#d3e1e6;margin:0;line-height:1.5}
main{max-width:1200px;margin:0 auto;padding:26px 28px 55px}.notice{border-left:4px solid #137e73;background:#e6f3ef;padding:14px 18px;margin-bottom:22px;line-height:1.5}
.controls{display:flex;gap:14px;flex-wrap:wrap;align-items:end;margin-bottom:22px}.controls label{font-size:13px;font-weight:700;color:#425467;display:grid;gap:6px}
select,input[type=range]{font:inherit}select{border:1px solid #bed1d4;background:white;padding:10px 12px;border-radius:7px;min-width:180px}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px}.card,.panel{background:white;border:1px solid #dce5e8;border-radius:12px;box-shadow:0 3px 15px #102c400a}
.card{padding:18px}.card .label{font-size:12px;color:#5c6c79;text-transform:uppercase;letter-spacing:.08em;font-weight:750}.card strong{display:block;font-size:29px;margin:8px 0 4px;font-variant-numeric:tabular-nums}.card small{color:#5c6c79;line-height:1.4}
.two{display:grid;grid-template-columns:1.65fr 1fr;gap:16px;margin-top:18px}.panel{padding:20px;min-width:0}.panel h2{font-size:18px;letter-spacing:-.02em;margin:0 0 5px}.panel p{font-size:13px;color:#536a77;line-height:1.55;margin:0 0 14px}
.chart{width:100%;height:auto;display:block}.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:#47606a;margin-top:4px}.legend i{display:inline-block;width:13px;height:3px;vertical-align:middle;margin-right:6px}
.scenario{display:grid;gap:11px}.scenario .big{font-size:29px;font-weight:750;font-variant-numeric:tabular-nums}.scenario .big.warn{color:#ab593b}.bar{height:15px;border-radius:9px;background:#e2edea;overflow:hidden}.bar span{display:block;height:100%;background:#157e75;width:92%}
.tablewrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}td,th{text-align:left;padding:10px;border-bottom:1px solid #e7edef}th{color:#516b78;font-size:11px;letter-spacing:.06em;text-transform:uppercase}td.num{text-align:right;font-variant-numeric:tabular-nums}
.foot{color:#637987;font-size:12px;line-height:1.6;padding-top:16px}a{color:#136f66}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}}@media(max-width:550px){.grid{grid-template-columns:1fr}.card strong{font-size:25px}}
</style></head><body>
<header><div class="eyebrow">Evidence-led planning · Public M5 retail data</div><h1>Demand forecasting and replenishment</h1>
<p>120 actual food items across three California stores. Two 28-day out-of-time backtests. Observed sales and forecast performance are real; stock and supply constraints are labelled scenarios.</p></header>
<main><div class="notice"><strong>Planning recommendation:</strong> Pilot the ML model for daily exceptions. Keep the seasonal baseline for weekly and 28-day volume decisions until a broader backtest supports switching.</div>
<div class="controls"><label>Store<select id="store"><option value="all">All three stores</option><option>CA_1</option><option>CA_2</option><option>CA_3</option></select></label>
<label>Holdout period<select id="period"><option value="all">Both 28-day windows</option><option value="1857">First 28 days</option><option value="1885">Second 28 days</option></select></label></div>
<section class="grid"><div class="card"><div class="label">Observed units</div><strong id="units">—</strong><small>Public historical sales</small></div>
<div class="card"><div class="label">Baseline WAPE</div><strong id="baseline">—</strong><small>Same weekday, prior four weeks</small></div>
<div class="card"><div class="label">ML WAPE</div><strong id="model">—</strong><small>Daily item-store error</small></div>
<div class="card"><div class="label">ML bias</div><strong id="bias">—</strong><small>Positive means over-forecast</small></div></section>
<section class="two"><div class="panel"><h2>Daily demand versus forecast</h2><p>Aggregated across the selected real item-store rows. The plotted aggregation is for context; WAPE cards are computed at item-store-day level.</p><svg id="chart" class="chart" role="img" aria-label="Actual sales, baseline and machine learning forecasts over time" viewBox="0 0 740 350"></svg><div class="legend"><span><i style="background:#153a50"></i>Observed</span><span><i style="background:#ac7544"></i>Seasonal baseline</span><span><i style="background:#2b907d"></i>ML forecast</span></div></div>
<div class="panel"><h2>Supply capacity scenario</h2><p>Set hypothetical capacity as a share of forecast demand. This slider changes a planning assumption, not actual Walmart capacity.</p>
<label for="capacity"><strong id="capacitylabel">92%</strong> of projected units</label><input id="capacity" style="width:100%;accent-color:#157e75;margin:16px 0" type="range" min="75" max="110" value="92">
<div class="scenario"><div><small>Forecast demand</small><div id="projected" class="big">—</div></div><div><small>Capacity gap / surplus</small><div id="gap" class="big warn">—</div></div><div class="bar"><span id="bar"></span></div><small>Commercial and Distribution can use this gap to prioritise allocations. Supplier limits and deliveries were not provided in M5.</small></div></div></section>
<section class="panel" style="margin-top:18px"><h2>Largest forecast exceptions</h2><p>First 15 item-store lines ranked by absolute unit error × observed historical unit price (USD). This ex-post ranking helps analyse mistakes; it is not a real-time alert.</p><div class="tablewrap"><table><thead><tr><th>Store</th><th>Item</th><th>Department</th><th>Observed</th><th>ML forecast</th><th>Bias units</th><th>Estimated error value</th></tr></thead><tbody id="exceptions"></tbody></table></div></section>
<div class="foot">Source: M5 Forecasting Accuracy dataset, Walmart US historical data. Backtest code, assumptions and checks appear in the project README and decision brief. This is an independent portfolio case study and has no affiliation with John Lewis Partnership or Waitrose.</div>
</main><script>const DATA=__PAYLOAD__;
const $=id=>document.getElementById(id);const fmt=(x,d=0)=>Number(x).toLocaleString('en-GB',{maximumFractionDigits:d,minimumFractionDigits:d});
function linePath(points,key,max,min){const left=50,right=715,top=18,bottom=305;return points.map((p,i)=>(i?'L':'M')+(left+i*(right-left)/Math.max(1,points.length-1)).toFixed(1)+','+(bottom-(p[key]-min)/(max-min||1)*(bottom-top)).toFixed(1)).join(' ')}
function render(){let store=$('store').value,period=$('period').value,seg=store==='all'?'overall':'store_'+store;
if(period!=='all'&&store==='all')seg='origin_'+period;
let m=DATA.metrics.find(x=>x.segment===seg&&x.policy==='model');let b=DATA.metrics.find(x=>x.segment===seg&&x.policy==='baseline');
let rows=DATA.daily.filter(x=>(store==='all'||x.store_id===store)&&(period==='all'||String(x.origin_day)===period));
if(period!=='all'&&store!=='all') {let observed=rows.reduce((a,x)=>a+x.units,0),mae=rows.reduce((a,x)=>a+Math.abs(x.units-x.model),0),base=rows.reduce((a,x)=>a+Math.abs(x.units-x.baseline),0);m={actual_units:observed,wape:100*mae/observed,bias_pct:100*rows.reduce((a,x)=>a+x.model-x.units,0)/observed};b={wape:100*base/observed}}
// Store + window cards use item-store-day metrics computed from the source series.
if(period!=='all'&&store!=='all'){m=DATA.metrics.find(x=>x.segment==='store_'+store+'_origin_'+period&&x.policy==='model');b=DATA.metrics.find(x=>x.segment==='store_'+store+'_origin_'+period&&x.policy==='baseline')}
$('units').textContent=fmt(m.actual_units);$('baseline').textContent=fmt(b.wape,2)+'%';$('model').textContent=fmt(m.wape,2)+'%';$('bias').textContent=(m.bias_pct>0?'+':'')+fmt(m.bias_pct,2)+'%';
let grouped=new Map();rows.forEach(x=>{let v=grouped.get(x.date)||{date:x.date,units:0,baseline:0,model:0};['units','baseline','model'].forEach(k=>v[k]+=x[k]);grouped.set(x.date,v)});
let points=[...grouped.values()].sort((a,b)=>a.date.localeCompare(b.date));let max=Math.max(...points.flatMap(x=>[x.units,x.baseline,x.model]))*1.08;let svg=$('chart');
let inner=['<rect x="0" y="0" width="740" height="350" fill="white"/>'];for(let j=0;j<=4;j++){let y=305-j*(287/4);inner.push(`<line x1="50" y1="${y}" x2="715" y2="${y}" stroke="#e7edef"/><text x="45" y="${y+4}" text-anchor="end" fill="#68808a" font-size="11">${fmt(max*j/4)}</text>`)}
[['units','#153a50'],['baseline','#ac7544'],['model','#2b907d']].forEach(([key,color])=>inner.push(`<path d="${linePath(points,key,max,0)}" fill="none" stroke="${color}" stroke-width="2.4"/>`));
for(let i=0;i<points.length;i+=Math.max(1,Math.floor(points.length/5))){let x=50+i*665/Math.max(1,points.length-1);inner.push(`<text x="${x}" y="329" text-anchor="middle" fill="#68808a" font-size="11">${points[i].date.slice(5)}</text>`)}svg.innerHTML=inner.join('');
let projected=rows.reduce((a,x)=>a+x.model,0),cap=Number($('capacity').value),gap=projected*(cap/100-1);
$('capacitylabel').textContent=cap+'%';$('projected').textContent=fmt(projected)+' units';$('gap').textContent=(gap<0?'Shortfall ':'Surplus ')+fmt(Math.abs(gap))+' units';$('gap').classList.toggle('warn',gap<0);$('bar').style.width=Math.min(cap,100)+'%';
let ex=DATA.exceptions.filter(x=>store==='all'||x.store_id===store).slice(0,12);
$('exceptions').innerHTML=ex.map(x=>`<tr><td>${x.store_id}</td><td>${x.item_id}</td><td>${x.dept_id}</td><td class="num">${fmt(x.actual_units)}</td><td class="num">${fmt(x.model_units)}</td><td class="num">${fmt(x.bias_units,1)}</td><td class="num">$${fmt(x.estimated_error_value_usd)}</td></tr>`).join('');}
['store','period','capacity'].forEach(id=>$(id).addEventListener(id==='capacity'?'input':'change',render));render();</script></body></html>"""
    (results / "planning_dashboard.html").write_text(page.replace("__PAYLOAD__", json.dumps(payload)))


if __name__ == "__main__":
    build(Path("results"))
