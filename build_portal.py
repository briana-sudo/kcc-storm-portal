"""
build_portal.py — generate the TEMPEST portal index.html from the PROVEN
storm-engine viewer template, preserving every §3 locked decision verbatim.

It mechanically: (1) reuses the template's <style> + #wrap body + the entire map
build script (the §3 render core) wrapped as renderMap(D); (2) swaps the vendored
Leaflet for the CDN (the portal is online); (3) wraps it in the TEMPEST shell —
brand header + a storm-aware date calendar + a proxy fetch layer that pulls each
date's cached render payload from the read-only proxy via the Netlify forwarder.
The map ALWAYS renders (interactive basemap + service-area reference) even when a
date has no storm; the "no storm" notice is a non-blocking bottom banner. No §3
color/layer/legend logic is touched — only the chrome around the map.

Run:  py build_portal.py   (reads ../storm-engine/storm/review/template.html)
"""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATE = Path(r"C:\KCC_Local\storm-engine\storm\review\template.html")
OUT = Path(__file__).parent / "index.html"
LEAFLET = "1.9.4"

POLISH_CSS = """
/* ── TEMPEST presentation polish (chrome only; §3 map colors untouched) ── */
html,body{height:100%}
#app{display:flex;flex-direction:column;height:100%}
#tbar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  background:linear-gradient(90deg,#0b1220,#16223c);color:#e9eef7;
  padding:8px 14px;box-shadow:0 2px 10px rgba(0,0,0,.3);z-index:1200}
#tbar .brand{display:flex;align-items:center;gap:8px;font-weight:800;letter-spacing:.5px;font-size:16px}
#tbar .brand .logo{font-size:18px;filter:drop-shadow(0 0 6px #5b8cff)}
#tbar .brand .sub{font-weight:500;color:#9fb3d9;font-size:12px;letter-spacing:.3px}
#tbar .datenav{display:flex;align-items:center;gap:6px;position:relative}
#tbar .datenav button{background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;border-radius:6px;
  padding:5px 10px;font-size:13px;cursor:pointer;line-height:1}
#tbar .datenav button:hover{background:#274069}
#tbar .datenav .datebtn{min-width:132px;font-weight:600}
#tbar .perils{color:#9fb3d9;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
#tbar .status{margin-left:auto;color:#ffd28a;font-size:12px}
#main{flex:1;min-height:0;position:relative}
#wrap{height:100%}
#side h1{font-size:14px}
.legend{font-size:11.5px}
/* ── operator summary panel (replaces the engine debug readout) ── */
#side .op-verdict{font-size:15px;font-weight:800;margin:8px 0 3px;padding:6px 11px;border-radius:7px;color:#fff;display:inline-block}
.op-verdict.strong{background:#bd0026}.op-verdict.sig{background:#e8430a}.op-verdict.mod{background:#f97316}
.op-verdict.weak{background:#8a7d00}.op-verdict.none{background:#6b7280}
#side .op-sub{color:#667;font-size:12px;margin:0 0 10px}
#side .op-maxhail{font-size:13px;margin:6px 0 10px;padding:8px 11px;background:#fff4e6;border-left:4px solid #e8430a;border-radius:5px}
#side .op-maxhail b{font-size:21px;color:#bd0026;vertical-align:-2px}
#side .op-peril{border-top:1px solid #eee;padding:9px 0 7px}
#side .op-peril h3{margin:0 0 4px;font-size:13px;display:flex;align-items:center;gap:6px;letter-spacing:.3px}
#side .op-peril .swatch{width:13px;height:13px;border-radius:3px;display:inline-block}
#side .op-peril .metric{font-size:13px}
#side .op-peril .metric b{font-size:16px}
#side .op-peril .tiers{color:#566;font-size:12px;margin-top:3px}
#side .op-peril .tiers b{color:#111}
#side .op-row{font-size:12px;padding:7px 0;border-top:1px solid #eee;color:#445}
#side .op-adspend .muted{font-style:italic}
#side .op-forecast{font-size:12px;padding:8px 10px;background:#eef3ff;border-radius:6px;margin:9px 0;border-left:4px solid #5b8cff;color:#234}
/* ── FULL-SCREEN RADAR (item 2): the map content fills the whole viewport so the
   operator can study the swath/circles up close. Pure flex reflow — header + side
   panel collapse, #main(flex:1) fills; on mobile the bottom control toolbar stays so
   Layers/Legend/Details remain reachable. Leaflet controls (bands/opacity/basemap,
   legend, readout, zoom) live INSIDE #map so they ride along in the corners. ── */
#tbar #expandBtn{background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar #expandBtn:hover{background:#274069}
body.fullmap #tbar{display:none}
body.fullmap #side{display:none}
#fmExit{display:none}
body.fullmap #fmExit{display:inline-flex;align-items:center;gap:6px;position:fixed;top:10px;left:50%;
  transform:translateX(-50%);z-index:2600;background:rgba(11,18,32,.92);color:#e9eef7;border:1px solid #2c3c5e;
  border-radius:8px;padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.45)}
body.fullmap #fmExit:hover{background:#1e2b46}
/* ── STATUS DASHBOARD (item 3): "is Tempest alive" surface — both heartbeats ── */
#tbar #statusBtn{display:flex;align-items:center;gap:7px;background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;
  border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar #statusBtn:hover{background:#274069}
#statusBtn .hbdot{width:9px;height:9px;border-radius:50%;background:#6b7280;box-shadow:0 0 0 2px rgba(255,255,255,.08)}
#statusBackdrop{position:fixed;inset:0;z-index:2390;background:transparent}
#statusBackdrop.hidden,#statusPanel.hidden{display:none}
#statusPanel{position:fixed;top:54px;right:12px;z-index:2400;width:374px;max-width:94vw;background:#0f1830;color:#e9eef7;
  border:1px solid #2c3c5e;border-radius:12px;box-shadow:0 18px 44px rgba(0,0,0,.6);padding:13px 14px 12px;font-size:13px;box-sizing:border-box}
#statusPanel h2{margin:0;font-size:14px;letter-spacing:.3px;display:flex;align-items:center;gap:8px}
#statusPanel h2 .x{margin-left:auto;background:transparent;border:none;color:#9fb3d9;font-size:18px;cursor:pointer;line-height:1}
#statusPanel .sp-sub{color:#8298c0;font-size:11px;margin:2px 0 8px}
.svc{border:1px solid #24324e;border-radius:10px;padding:10px 11px;margin:8px 0;background:#13203c}
.svc-h{display:flex;align-items:center;gap:8px;font-weight:800;font-size:13px;margin-bottom:6px}
.svc-h .dot{width:11px;height:11px;border-radius:50%;flex:none}
.svc-h .st{margin-left:auto;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;padding:2px 7px;border-radius:20px}
.dot.green{background:#16a34a}.dot.stale{background:#d9a600}.dot.red{background:#dc2626}.dot.unknown{background:#6b7280}
.st.green{background:rgba(22,163,74,.18);color:#5fe39a}.st.stale{background:rgba(217,166,0,.18);color:#ffd86b}
.st.red{background:rgba(220,38,38,.2);color:#ff8d8d}.st.unknown{background:rgba(107,114,128,.25);color:#c2c9d6}
.svc-row{display:flex;justify-content:space-between;gap:10px;padding:2px 0;font-size:12px}
.svc-row span:first-child{color:#8298c0}
.svc-row .ago{color:#6f86ad;font-size:11px}
.svc-risk{margin-top:7px;padding:6px 9px;border-radius:7px;background:#16223c;font-size:12px;color:#cfe}
.svc-why{margin-top:5px;font-size:11px;color:#ffb27a}
/* ── NATIONAL RADAR overlay control (item 7): IEM NEXRAD N0Q, toggle + opacity dial.
   Tile layer lives in its own pane UNDER the engine swath (swath-above-all-tiles). ── */
.nexctl{background:#fff;padding:6px 9px;border-radius:6px;box-shadow:0 1px 5px rgba(0,0,0,.3);font-size:12px;max-width:210px}
.nexctl label{display:flex;align-items:center;gap:6px;font-weight:700;cursor:pointer}
.nexctl .muted{color:#888;font-weight:400}
.nexctl .nexsub{display:flex;align-items:center;gap:7px;margin-top:5px}
.nexctl .nexsub.off{opacity:.45}
.nexctl input[type=range]{flex:1}
.nexctl #nexv{min-width:34px;text-align:right;color:#555}
/* storm-aware calendar popup */
.cal{position:absolute;top:calc(100% + 6px);left:0;z-index:1300;background:#16223c;
  border:1px solid #2c3c5e;border-radius:10px;padding:13px;width:404px;max-width:96vw;color:#e9eef7;
  box-shadow:0 12px 30px rgba(0,0,0,.5);font-size:14px;box-sizing:border-box}
.cal.hidden{display:none}
.cal *{box-sizing:border-box}
.cal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-weight:700;font-size:14px}
.cal-head button{background:#1e2b46;border:1px solid #2c3c5e;color:#e9eef7;border-radius:6px;
  width:30px;height:30px;cursor:pointer;font-size:16px}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
.cal-dow span{color:#7e90b3;font-size:12px;text-align:center;padding-bottom:4px}
/* deterministic cell: fixed height, number in a fixed top zone, dots in a fixed
   bottom strip -- the number never moves and dots never crowd it, 0 dots or 3. */
.cal-day{height:56px;border:none;background:#1a2740;color:#cdd8ee;border-radius:8px;cursor:pointer;font-size:16px;
  display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:0;padding-top:8px}
.cal-day .cal-num{line-height:1;height:18px;display:flex;align-items:center}
.cal-day:hover{background:#274069}
.cal-day.blank{background:transparent;cursor:default}
.cal-day.today{outline:2px solid #5b8cff}
.cal-day.selected{background:#3056a8;color:#fff;font-weight:700}
.cal-day.storm{font-weight:700;color:#fff}
.cal-day.dim{opacity:.38}
.cal-dots{display:flex;gap:4px;justify-content:center;align-items:center;height:14px;margin-top:6px}
.cal-dots i{width:9px;height:9px;border-radius:50%;border:1.5px solid transparent;box-sizing:border-box}
/* §3 peril colors: hail warm [247,182,0] / wind blue [107,175,215] / tornado violet [158,155,200] */
.dot.hail,.cal-dots i.hail{background:#f7b600}
.dot.wind,.cal-dots i.wind{background:#6bafd7}
.dot.torn,.cal-dots i.torn{background:#9e9bc8}
/* tier treatment (item 4): P1 core = bright + halo ring, P2 = solid, P3 margin = hollow/faint */
.cal-dots i.t1{width:10px;height:10px;box-shadow:0 0 0 2px rgba(255,255,255,.9),0 0 4px rgba(0,0,0,.5)}
.cal-dots i.t3{background:transparent;opacity:.7}
.cal-dots i.t3.hail{border-color:#f7b600}
.cal-dots i.t3.wind{border-color:#6bafd7}
.cal-dots i.t3.torn{border-color:#9e9bc8}
.cal-legend{display:flex;gap:12px;margin-top:7px;color:#9fb3d9;font-size:10px}
.cal-legend span{display:flex;align-items:center;gap:4px}
.cal-legend .dot{width:7px;height:7px;border-radius:50%}
/* non-blocking bottom banner (replaces the old center "no data" modal) */
#banner{position:absolute;left:50%;transform:translateX(-50%);bottom:16px;z-index:900;
  background:rgba(22,34,60,.95);color:#e9eef7;border:1px solid #2c3c5e;border-radius:9px;
  padding:9px 18px;font-size:13px;box-shadow:0 6px 20px rgba(0,0,0,.4);max-width:90%;text-align:center}
#banner.hidden{display:none}
/* ── MOBILE LANE (device-detected via body.mobile, NOT viewport width) ──
   Full-screen interactive map; Layers / Legend / Details become slide-up bottom
   sheets opened from a bottom toolbar, all closed by default. PC lane untouched. */
#mtoolbar{display:none}
.msheet,#mbackdrop{display:none}
body.mobile #tbar{gap:8px}
body.mobile #tbar .brand .sub{display:none}
body.mobile #expandBtn{display:none}   /* the mobile map is already full-screen */
body.mobile #wrap{height:100%}
body.mobile #map{width:100% !important;height:100% !important;flex:1 1 auto}
body.mobile #mtoolbar{display:flex;flex:none;height:52px;background:#0b1220;border-top:1px solid #2c3c5e;z-index:1460}
body.mobile #mtoolbar button{flex:1;background:transparent;color:#cdd8ee;border:none;border-right:1px solid #1d2b46;
  font-size:13px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center}
body.mobile #mtoolbar button:last-child{border-right:none}
body.mobile #mtoolbar button.active{background:#1e2b46;color:#fff}
body.mobile #mbackdrop{display:block;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1420}
body.mobile #mbackdrop.hidden{display:none}
body.mobile .msheet{display:block;position:fixed;left:0;right:0;bottom:52px;max-height:72vh;overflow:auto;
  background:#fff;border-radius:14px 14px 0 0;z-index:1450;box-shadow:0 -8px 28px rgba(0,0,0,.4)}
body.mobile .msheet.hidden{display:none}
body.mobile .msheet-head{position:sticky;top:0;background:#16223c;color:#fff;display:flex;align-items:center;
  justify-content:space-between;padding:11px 16px;font-weight:700;font-size:14px}
body.mobile .msheet-x{background:transparent;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1}
body.mobile .msheet-body{padding:10px 12px}
/* the moved panels render full-width inside their sheet (drop their floating chrome) */
body.mobile .msheet-body .ctlpanel,body.mobile .msheet-body .legend{position:static !important;width:auto !important;
  max-width:none !important;max-height:none !important;box-shadow:none !important}
body.mobile .msheet-body #side{width:auto;border:none;overflow:visible}
/* the moved Leaflet controls leave empty corner wrappers — hide them */
body.mobile .leaflet-top.leaflet-right,body.mobile .leaflet-bottom.leaflet-left{display:none}
"""

SHELL_HEAD = """  <div id="tbar">
    <div class="brand"><span class="logo">&#9731;</span> TEMPEST <span class="sub">KCC Storm Review</span></div>
    <div class="datenav">
      <button id="navPrev" title="Previous day">&#9664;</button>
      <button id="navDateBtn" class="datebtn">&mdash;</button>
      <button id="navNext" title="Next day">&#9654;</button>
      <button id="navToday">Today</button>
      <span class="perils" id="navPerils"></span>
      <div id="cal" class="cal hidden">
        <div class="cal-head"><button id="calPrev">&#8249;</button><span id="calTitle"></span><button id="calNext">&#8250;</button></div>
        <div class="cal-grid cal-dow"><span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span></div>
        <div class="cal-grid" id="calDays"></div>
        <div class="cal-legend"><span><i class="dot hail"></i>hail</span><span><i class="dot wind"></i>wind</span><span><i class="dot torn"></i>tornado</span><span style="margin-left:auto;color:#7e90b3">&#9679;core &#9675;margin</span></div>
      </div>
    </div>
    <button id="expandBtn" title="Full-screen radar">&#9974; Full-screen radar</button>
    <button id="statusBtn" title="Service health (is Tempest alive)"><span class="hbdot"></span>Status</button>
    <div class="status" id="connStatus"></div>
  </div>
  <div id="main">
"""

SHELL_NODATA = """    <div id="banner" class="hidden"></div>
  </div>
"""

BOOTSTRAP = """
// ── TEMPEST data + date-navigation shell (chrome; renderMap is the §3 core) ──
// API = the Netlify server-side forwarder (/api/storm). It holds the proxy bearer
// token server-side, so this public bundle carries NO credential of any kind.
const CFG = window.TEMPEST_CONFIG || {};
const API = (CFG.api || "").replace(/\\/$/, "");
const ARCHIVE_START = "2020-10-14";
const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
let AVAIL = {};        // {date: [perils]} for the storm-aware calendar
let calView = null;    // {y,m} currently-viewed calendar month

// Capture the Leaflet map instance WITHOUT touching renderMap(D): wrap the L.map
// factory before renderMap() runs (it calls L.map('map')). Gives full-screen a crisp
// invalidateSize() and a handle for future display-only layers. §3 core untouched.
let TMAP = null;
const _origLmap = L.map;
L.map = function(){ const m = _origLmap.apply(this, arguments); TMAP = m; return m; };

function todayUTC(){ return new Date().toISOString().slice(0,10); }
function getDate(){ return new URLSearchParams(location.search).get("date") || todayUTC(); }
function goDate(d){ location.search = "?date=" + d; }
function shiftDate(d, n){ const t=new Date(d+"T00:00:00Z"); t.setUTCDate(t.getUTCDate()+n); return t.toISOString().slice(0,10); }
function fmtDate(d){ const t=new Date(d+"T00:00:00Z"); return t.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}); }
function parseJSON(s){ try{ return JSON.parse(s||"[]"); }catch(e){ return []; } }
async function pquery(name, params){
  const r = await fetch(API, { method:"POST", headers:{ "Content-Type":"application/json" },
    body: JSON.stringify({ name, params: params||{} }) });
  if(!r.ok) throw new Error(name+" HTTP "+r.status);
  return (await r.json()).rows || [];
}
function showBanner(msg){ const b=document.getElementById("banner"); b.textContent=msg; b.classList.remove("hidden"); }
function hideBanner(){ document.getElementById("banner").classList.add("hidden"); }

// portal default basemap = Street (the engine viewer is offline-first; the hosted
// portal is online). Synced through the §3 band-control base switcher, untouched.
function setBaseStreet(){
  const s=document.querySelector('select[data-base]');
  if(s && s.value!=='street'){ s.value='street'; s.dispatchEvent(new Event('change',{bubbles:true})); }
}

function assemble(date, rows, geo){
  const byPeril = {}; rows.forEach(r => byPeril[r.peril] = r);
  const h = byPeril.hail;
  const layer = r => r ? { swath_cells: parseJSON(r.swath_json), circles: parseJSON(r.circles_json),
                           evidence: parseJSON(r.evidence_json),
                           summary: { cells: parseJSON(r.swath_json).length, circles: r.circle_count } } : null;
  const D = {
    storm_date: date,
    summary: { events: 0, swath_cells: h ? parseJSON(h.swath_json).length : 0,
               swath_mode: h ? "per_cell" : "none", evidence_points: h ? parseJSON(h.evidence_json).length : 0,
               circles: h ? h.circle_count : 0, qualifying: 0, priority: 0, in_area: 0, buffer: 0 },
    center: [38.63, -90.2], events: [], zips: [],
    evidence_points: h ? parseJSON(h.evidence_json) : [],
    swath_cells: h ? parseJSON(h.swath_json) : [],
    swath_mode: h ? "per_cell" : "none",
    geo_ref: geo || { boundaries: [], cities: [] },
    circles: h ? parseJSON(h.circles_json) : [],
    overlay: null,
    wind: layer(byPeril.wind),
    tornado: layer(byPeril.tornado),
  };
  const pts = [];
  (D.circles||[]).forEach(c => pts.push([c.center_lat, c.center_lng]));
  ["wind","tornado"].forEach(p => { if(D[p]) (D[p].circles||[]).forEach(c => pts.push([c.center_lat, c.center_lng])); });
  if(pts.length){ const la=pts.map(p=>p[0]), lo=pts.map(p=>p[1]);
    D.center=[la.reduce((a,b)=>a+b,0)/la.length, lo.reduce((a,b)=>a+b,0)/lo.length]; }
  return D;
}

// ── operator summary panel: per-peril verdict + numbers (replaces debug pills) ──
const CELL_AREA = 0.374;
const PERIL_SWATCH = {hail:"#e8430a", wind:"#2171b5", tornado:"#6a3fa0"};
function tierCounts(circles){ const t={P1:0,P2:0,P3:0}; (circles||[]).forEach(c=>{ if(t[c.tier]!=null)t[c.tier]++; }); return t; }
function maxMetric(circles){ return (circles||[]).reduce((m,c)=>Math.max(m, c.max_hail_size_in||0), 0); }
function buildOperatorPanel(D, forecast){
  const side=document.getElementById("side"); if(!side) return;
  const perils=[];
  if(D.circles && D.circles.length) perils.push({k:"hail",label:"HAIL",circles:D.circles,swath:D.swath_cells,ev:D.evidence_points});
  if(D.wind) perils.push({k:"wind",label:"WIND",circles:D.wind.circles,swath:D.wind.swath_cells,ev:D.wind.evidence});
  if(D.tornado) perils.push({k:"tornado",label:"TORNADO",circles:D.tornado.circles,swath:D.tornado.swath_cells,ev:D.tornado.evidence});
  let P1=0,P2=0,P3=0; perils.forEach(p=>{const t=tierCounts(p.circles);P1+=t.P1;P2+=t.P2;P3+=t.P3;});
  let verdict,vc;
  if(!perils.length){ verdict="No qualifying storm"; vc="none"; }
  else if(P1>=10){ verdict="Strong, widespread event"; vc="strong"; }
  else if(P1>=1){ verdict="Significant \\u2014 strong localized core"; vc="sig"; }
  else if(P2>=15){ verdict="Moderate event"; vc="mod"; }
  else if(P2>=1){ verdict="Weak \\u2014 mostly margin"; vc="weak"; }
  else { verdict="Marginal \\u2014 margin only"; vc="weak"; }
  let h='<h1>Storm Review <span class="muted">'+D.storm_date+'</span></h1>';
  h+='<div class="op-verdict '+vc+'">'+verdict+'</div>';
  h+='<div class="op-sub">'+(perils.length ? ('P1 '+P1+' \\u00b7 P2 '+P2+' \\u00b7 P3 '+P3+' across '+perils.map(p=>p.k).join(", ")) : 'nothing processed for this date')+'</div>';
  const hail=perils.find(p=>p.k==="hail");
  if(hail) h+='<div class="op-maxhail">Max hail <b>'+maxMetric(hail.circles).toFixed(2)+'"</b></div>';
  perils.forEach(p=>{
    const t=tierCounts(p.circles), targets=t.P1+t.P2, ev=p.ev||[];
    const dmg = p.k==="tornado" ? ev.length : ev.filter(e=>e.damage).length;
    let metric;
    if(p.k==="hail") metric='Max size <b>'+maxMetric(p.circles).toFixed(2)+'"</b>';
    else if(p.k==="wind") metric='Peak gust <b>'+Math.round(maxMetric(p.circles))+' mph</b>';
    else metric='Debris swath <b>'+Math.round((p.swath||[]).length*CELL_AREA)+' mi\\u00b2</b> \\u00b7 rotation peak '+Math.round(maxMetric(p.circles));
    h+='<div class="op-peril"><h3><span class="swatch" style="background:'+PERIL_SWATCH[p.k]+'"></span>'+p.label+'</h3>'+
       '<div class="metric">'+metric+'</div>'+
       '<div class="tiers">Targets (P1/P2): <b>'+targets+'</b> &nbsp;\\u00b7&nbsp; tiers P1 '+t.P1+' \\u00b7 P2 '+t.P2+' \\u00b7 P3 '+t.P3+'</div>'+
       '<div class="tiers">Evidence: '+ev.length+' SPC/LSR \\u00b7 <b>'+dmg+'</b> damage-confirmed</div></div>';
  });
  if(forecast) h+='<div class="op-forecast"><b>Forecast (today):</b> '+forecast+'</div>';
  h+='<div class="op-row op-adspend"><b>Ad spend:</b> <span class="muted">pending parcel data + CPC</span></div>';
  h+='<div id="detail" class="op-row"><span class="muted">Click a target circle for lead detail.</span></div>';
  side.innerHTML=h;
}

// ── storm-aware calendar: dates with data get peril dots (one cached query) ──
async function loadAvailable(){
  // instant first-paint from cache (if any) so the grid isn't empty on load
  try { const c = sessionStorage.getItem("tempest_avail"); if(c){ AVAIL = JSON.parse(c); renderCal(); } } catch(e){}
  // ALWAYS refresh from the proxy (cheap tenant-guarded read) so storm-days added
  // since last visit -- this backfill, or the daily monitor -- appear with no
  // manual cache clear. sessionStorage is a first-paint hint only, not authoritative.
  try {
    const av = await pquery("storm_available_dates", {});
    AVAIL = {}; av.forEach(x => { AVAIL[x.storm_date] = x.perils || []; });
    sessionStorage.setItem("tempest_avail", JSON.stringify(AVAIL));
  } catch(e){ AVAIL = AVAIL || {}; }
  const cur = AVAIL[getDate()];
  if(cur && cur.length) document.getElementById("navPerils").textContent = cur.join("  \\u00b7  ");
  renderCal();
}
function renderCal(){
  const sel = getDate();
  if(!calView){ const t=new Date(sel+"T00:00:00Z"); calView={ y:t.getUTCFullYear(), m:t.getUTCMonth() }; }
  const y=calView.y, m=calView.m;
  document.getElementById("calTitle").textContent = MONTHS[m]+" "+y;
  const first = new Date(Date.UTC(y,m,1)).getUTCDay();
  const days = new Date(Date.UTC(y,m+1,0)).getUTCDate();
  const grid = document.getElementById("calDays"); grid.innerHTML="";
  for(let i=0;i<first;i++){ const b=document.createElement("div"); b.className="cal-day blank"; grid.appendChild(b); }
  const today = todayUTC();
  for(let d=1; d<=days; d++){
    const ds = y+"-"+String(m+1).padStart(2,"0")+"-"+String(d).padStart(2,"0");
    const btn = document.createElement("button"); btn.className="cal-day"; btn.dataset.date=ds;
    const num=document.createElement("span"); num.className="cal-num"; num.textContent=d; btn.appendChild(num);
    if(ds===today) btn.classList.add("today");
    if(ds===sel) btn.classList.add("selected");
    if(ds<ARCHIVE_START) btn.classList.add("dim");
    // dots strip is ALWAYS present (fixed-height) so the number never shifts and
    // dots never crowd it -- deterministic whether the day has 0 or 3 perils.
    const dots=document.createElement("div"); dots.className="cal-dots"; btn.appendChild(dots);
    const per = AVAIL[ds];
    if(per && per.length){
      btn.classList.add("storm");
      const tt = TIERS[ds] || {};
      per.forEach(p=>{ const i=document.createElement("i"); const cls=(p==="hail"?"hail":p==="wind"?"wind":"torn");
        const tier=tt[p]; const tcl=(tier==="P1"?" t1":tier==="P3"?" t3":"");   // P2 = base solid dot
        i.className=cls+tcl; dots.appendChild(i); });
    }
    btn.onclick = ()=>goDate(ds);
    grid.appendChild(btn);
  }
  enrichVisibleTiers();   // refine dots to P1/P2/P3 for storm dates in view (cached, read-only)
}
function toggleCal(){ const c=document.getElementById("cal"); c.classList.toggle("hidden"); if(!c.classList.contains("hidden")) renderCal(); }

// ── MOBILE LANE: relocate Layers / Legend / Details into slide-up bottom sheets
//    opened from a bottom toolbar (all closed by default). Device-detected. ──
function setupMobile(){
  if(!document.body.classList.contains("mobile") || document.getElementById("mtoolbar")) return;
  const app=document.getElementById("app");
  const tb=document.createElement("div"); tb.id="mtoolbar";
  const bd=document.createElement("div"); bd.id="mbackdrop"; bd.className="hidden";
  const sheets={};
  function closeAll(){ for(const k in sheets) sheets[k].classList.add("hidden"); bd.classList.add("hidden");
    tb.querySelectorAll("button").forEach(b=>b.classList.remove("active")); }
  function openSheet(id){ const wasOpen=!sheets[id].classList.contains("hidden"); closeAll();
    if(!wasOpen){ sheets[id].classList.remove("hidden"); bd.classList.remove("hidden");
      tb.querySelector('[data-sheet="'+id+'"]').classList.add("active"); } }
  [["layers","Layers",".ctlpanel"],["legend","Legend",".legend"],["details","Details","#side"]].forEach(function(def){
    const id=def[0], label=def[1], sel=def[2];
    const btn=document.createElement("button"); btn.dataset.sheet=id; btn.textContent=label; tb.appendChild(btn);
    const sh=document.createElement("div"); sh.id="sheet-"+id; sh.className="msheet hidden";
    const head=document.createElement("div"); head.className="msheet-head"; head.innerHTML='<span>'+label+'</span>';
    const x=document.createElement("button"); x.className="msheet-x"; x.innerHTML="&#10005;"; x.onclick=closeAll;
    head.appendChild(x);
    const body=document.createElement("div"); body.className="msheet-body";
    const node=document.querySelector(sel); if(node) body.appendChild(node);   // move the panel DOM in (keeps its wiring)
    sh.appendChild(head); sh.appendChild(body); document.body.appendChild(sh); sheets[id]=sh;
  });
  const fbtn=document.createElement("button"); fbtn.id="mFull"; fbtn.textContent="\\u26f6";
  fbtn.title="Full-screen radar"; fbtn.onclick=()=>setFullmap(!document.body.classList.contains("fullmap")); tb.appendChild(fbtn);
  document.body.appendChild(bd); app.appendChild(tb);
  tb.addEventListener("click",function(e){ const b=e.target.closest("button[data-sheet]"); if(b) openSheet(b.dataset.sheet); });
  bd.addEventListener("click",closeAll);
  window.dispatchEvent(new Event("resize"));   // map recomputes to full size (side panel moved out)
}

// ── FULL-SCREEN RADAR (item 2): flex reflow (header+side collapse) so the map fills
//    the viewport; controls ride along (Leaflet controls live inside #map; on mobile
//    they stay in the bottom-sheet toolbar). invalidateSize keeps tiles crisp. ──
function setFullmap(on){
  document.body.classList.toggle("fullmap", !!on);
  const eb=document.getElementById("expandBtn");
  if(eb) eb.innerHTML = on ? "\\u26f6 Exit full-screen" : "\\u26f6 Full-screen radar";
  const fix=()=>{ if(TMAP) TMAP.invalidateSize(); window.dispatchEvent(new Event("resize")); };
  fix(); setTimeout(fix,60); setTimeout(fix,220);   // after CSS reflow settles
}

// ── STATUS DASHBOARD (item 3): read BOTH heartbeats via the existing whitelist
//    queries; render green / stale / red per service. Read-only. ──
let STATUS_CACHE={mon:null, fc:null, err:null};
function _ts(s){ const t=Date.parse(s); return isNaN(t)?0:t; }
function fmtTs(s){ if(!s) return "\\u2014"; const t=_ts(s); if(!t) return s;
  return new Date(t).toISOString().slice(0,16).replace("T"," ")+"Z"; }
function agoStr(s){ const t=_ts(s); if(!t) return ""; const m=Math.round((Date.now()-t)/60000);
  if(m<0) return "in "+(-m)+"m"; if(m<60) return m+"m ago"; const h=Math.floor(m/60);
  if(h<48) return h+"h ago"; return Math.floor(h/24)+"d ago"; }
const _OKSET=["ok","no_risk","no_data","waiting",""];
function _okStatus(hb){ return _OKSET.indexOf((hb.last_status||"").toLowerCase())>=0; }
// storm_forecast_status omits last_success_at; derive it from a healthy last run.
function _lastSuccess(hb){ return hb.last_success_at || (_okStatus(hb) ? hb.last_run_at : ""); }
function svcHealth(hb, isForecast){
  const now=Date.now(), lr=_ts(hb.last_run_at), ls=_ts(_lastSuccess(hb)), ns=_ts(hb.next_scheduled_at);
  if(!lr) return {state:"red", why:"never run"};
  if(!_okStatus(hb)) return {state:"red", why:"last status: "+hb.last_status};
  const interval = (ns>lr) ? (ns-lr) : (isForecast? 14400000 : 86400000);   // cadence from heartbeat
  if(ns && now>ns){ const late=now-ns;
    return (late>interval) ? {state:"red", why:"silent \\u2014 overdue since "+fmtTs(hb.next_scheduled_at)}
                           : {state:"stale", why:"running late (within one cycle)"}; }
  if(ls && (now-ls) > interval*3) return {state:"stale", why:"no recent success"};
  return {state:"green", why:""};
}
function _svcCard(title, hb, isForecast){
  if(!hb) return '<div class="svc"><div class="svc-h"><span class="dot unknown"></span>'+title+
    '<span class="st unknown">no data</span></div><div class="svc-row"><span>heartbeat</span><span>unreachable</span></div></div>';
  const h=svcHealth(hb, isForecast);
  const row=(k,v,a)=>'<div class="svc-row"><span>'+k+'</span><span>'+v+(a?' <span class="ago">'+a+'</span>':'')+'</span></div>';
  let s='<div class="svc"><div class="svc-h"><span class="dot '+h.state+'"></span>'+title+
        '<span class="st '+h.state+'">'+h.state+'</span></div>';
  s+=row("Last run", fmtTs(hb.last_run_at), agoStr(hb.last_run_at));
  const lsv=_lastSuccess(hb);
  s+=row("Last success", lsv?fmtTs(lsv):"\\u2014", lsv?agoStr(lsv):"");
  s+=row("Next scheduled", fmtTs(hb.next_scheduled_at), "");
  s+=row("Last alert sent", hb.last_alert_at?fmtTs(hb.last_alert_at):"never", hb.last_alert_at?agoStr(hb.last_alert_at):"");
  s+=row("Status \\u00b7 runs \\u00b7 alerts", (hb.last_status||"\\u2014")+" \\u00b7 "+(hb.runs_total!=null?hb.runs_total:"\\u2014")+" \\u00b7 "+(hb.alerts_total!=null?hb.alerts_total:"\\u2014"), "");
  if(isForecast){ const r=hb.current_active_risk; s+='<div class="svc-risk">Current active risk: <b>'+((r&&r!=="none")?r:"none")+'</b></div>'; }
  if(h.why) s+='<div class="svc-why">'+h.why+'</div>';
  return s+'</div>';
}
function renderStatusPanel(){
  const p=document.getElementById("statusPanel"); if(!p) return;
  const c=STATUS_CACHE;
  let h='<h2>Tempest service health <button class="x" id="spX" title="Close">&times;</button></h2>'+
        '<div class="sp-sub">Live read of both heartbeats \\u00b7 times UTC</div>';
  h+=_svcCard("Monitor (hail)", c.mon, false);
  h+=_svcCard("Forecast (SPC)", c.fc, true);
  if(c.err && !c.mon && !c.fc) h+='<div class="svc-why">proxy: '+c.err+'</div>';
  p.innerHTML=h;
  const x=document.getElementById("spX"); if(x) x.onclick=closeStatus;
}
function _worstState(){ const rank={green:0,stale:1,red:2}; let w=null;
  [[STATUS_CACHE.mon,false],[STATUS_CACHE.fc,true]].forEach(a=>{ if(a[0]){ const s=svcHealth(a[0],a[1]).state;
    if(w===null || rank[s]>rank[w]) w=s; } }); return w; }
async function refreshStatus(renderPanel){
  let mon=null, fc=null, err=null;
  try{ const m=await pquery("storm_engine_status",{}); mon=(m&&m[0])||null; }catch(e){ err=e.message; }
  try{ const f=await pquery("storm_forecast_status",{}); fc=(f&&f[0])||null; }catch(e){ err=err||e.message; }
  STATUS_CACHE={mon,fc,err};
  const dot=document.querySelector("#statusBtn .hbdot"), w=_worstState();
  if(dot) dot.style.background = (w===null)?"#6b7280":(w==="red"?"#dc2626":w==="stale"?"#d9a600":"#16a34a");
  if(renderPanel) renderStatusPanel();
}
function closeStatus(){ const p=document.getElementById("statusPanel"), b=document.getElementById("statusBackdrop");
  if(p)p.classList.add("hidden"); if(b)b.classList.add("hidden"); }
function openStatus(){ const p=document.getElementById("statusPanel"), b=document.getElementById("statusBackdrop");
  renderStatusPanel(); if(p)p.classList.remove("hidden"); if(b)b.classList.remove("hidden"); refreshStatus(true); }
function toggleStatus(){ const p=document.getElementById("statusPanel");
  if(p && p.classList.contains("hidden")) openStatus(); else closeStatus(); }

// ── CALENDAR TIER ENRICHMENT (item 4): peril dots render immediately from
//    storm_available_dates; tier (P1 core / P2 / P3 margin) is refined per visible
//    storm date via the existing storm_date_layers read, cached. Read-only. ──
let TIERS = {};
try { TIERS = JSON.parse(sessionStorage.getItem("tempest_tiers")||"{}"); } catch(e){ TIERS={}; }
function topTier(circles){ let p1=0,p2=0,p3=0; (circles||[]).forEach(c=>{ if(c.tier==="P1")p1++; else if(c.tier==="P2")p2++; else if(c.tier==="P3")p3++; });
  return p1?"P1":p2?"P2":p3?"P3":null; }
async function enrichVisibleTiers(){
  if(!calView) return;
  const y=calView.y, m=calView.m;
  const targets=Object.keys(AVAIL).filter(ds=>{ const t=new Date(ds+"T00:00:00Z");
    return t.getUTCFullYear()===y && t.getUTCMonth()===m && !TIERS[ds]; });
  if(!targets.length) return;
  for(const ds of targets){
    try{ const rows=await pquery("storm_date_layers",{date:ds}); const tt={};
      rows.forEach(r=>{ try{ tt[r.peril]=topTier(JSON.parse(r.circles_json||"[]")); }catch(e){} });
      TIERS[ds]=tt;
    }catch(e){ TIERS[ds]=TIERS[ds]||{}; }
  }
  try{ sessionStorage.setItem("tempest_tiers", JSON.stringify(TIERS)); }catch(e){}
  renderCal();   // repaint with tier treatment (targets now cached -> no re-loop)
}

// ── NATIONAL RADAR (item 7): add IEM NEXRAD N0Q base-reflectivity as a toggleable
//    national overlay so the operator can see hail anywhere. DISPLAY ONLY — no data is
//    computed/fetched/written outside the geofence; the engine swath/circles stay put.
//    Wired from the bootstrap via the captured map handle so renderMap(D) is untouched.
//    The tile goes in a dedicated pane (z230) ABOVE the basemap but BELOW the swath/
//    geofence (z250+), so swath-above-all-tiles holds. Off by default; it is the LATEST
//    national mosaic (current time), labelled as such, independent of the reviewed date. ──
function addNexrad(){
  if(!TMAP || document.querySelector(".nexctl")) return;
  if(!TMAP.getPane("nexradPane")){ TMAP.createPane("nexradPane");
    const pn=TMAP.getPane("nexradPane"); pn.style.zIndex=230; pn.style.pointerEvents="none"; }
  const radar=L.tileLayer("https://mesonet.agron.iastate.edu/cache/tile.py/1.0.0/nexrad-n0q-900913/{z}/{x}/{y}.png",
    { pane:"nexradPane", opacity:0.7, maxZoom:19, attribution:"NEXRAD N0Q &copy; IEM / NOAA" });
  const ctl=L.control({position:"bottomright"});
  ctl.onAdd=function(){
    const d=L.DomUtil.create("div","nexctl");
    d.innerHTML='<label><input type="checkbox" id="nexOn"> \\u2622 Live NEXRAD <span class="muted">(current)</span></label>'+
                '<div class="nexsub off" id="nexSub"><input type="range" id="nexOp" min="0" max="100" value="70"><span id="nexv">70%</span></div>';
    L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d);
    return d;
  };
  ctl.addTo(TMAP);
  const on=document.getElementById("nexOn"), op=document.getElementById("nexOp"),
        v=document.getElementById("nexv"), sub=document.getElementById("nexSub");
  if(on) on.addEventListener("change",()=>{ if(on.checked){ radar.addTo(TMAP); sub.classList.remove("off"); }
    else { if(TMAP.hasLayer(radar)) TMAP.removeLayer(radar); sub.classList.add("off"); } });
  if(op) op.addEventListener("input",()=>{ radar.setOpacity(op.value/100); if(v) v.textContent=op.value+"%"; });
}

async function boot(){
  if(matchMedia("(pointer:coarse)").matches || /Android|iPhone|iPad|iPod|Mobile|Silk/i.test(navigator.userAgent))
    document.body.classList.add("mobile");
  const date = getDate();
  document.getElementById("navDateBtn").textContent = fmtDate(date)+" \\u25be";
  document.getElementById("navDateBtn").onclick = e => { e.stopPropagation(); toggleCal(); };
  document.getElementById("navPrev").onclick  = () => goDate(shiftDate(date, -1));
  document.getElementById("navNext").onclick  = () => goDate(shiftDate(date,  1));
  document.getElementById("navToday").onclick = () => goDate(todayUTC());
  document.getElementById("calPrev").onclick = e => { e.stopPropagation(); if(!calView)renderCal(); calView.m--; if(calView.m<0){calView.m=11;calView.y--;} renderCal(); };
  document.getElementById("calNext").onclick = e => { e.stopPropagation(); if(!calView)renderCal(); calView.m++; if(calView.m>11){calView.m=0;calView.y++;} renderCal(); };
  document.addEventListener("click", e => { const c=document.getElementById("cal");
    if(!c.classList.contains("hidden") && !c.contains(e.target) && e.target.id!=="navDateBtn") c.classList.add("hidden"); });
  const eb=document.getElementById("expandBtn");
  if(eb) eb.onclick=()=>setFullmap(!document.body.classList.contains("fullmap"));
  // floating Exit (header is hidden in full-screen) + status panel/backdrop, appended
  // to <body> so their fixed positioning is never clipped by the app layout.
  if(!document.getElementById("fmExit")){ const fx=document.createElement("button"); fx.id="fmExit";
    fx.innerHTML="\\u26f6 Exit full-screen"; fx.onclick=()=>setFullmap(false); document.body.appendChild(fx); }
  if(!document.getElementById("statusPanel")){
    const bp=document.createElement("div"); bp.id="statusBackdrop"; bp.className="hidden"; bp.onclick=closeStatus;
    const sp=document.createElement("div"); sp.id="statusPanel"; sp.className="hidden";
    document.body.appendChild(bp); document.body.appendChild(sp); }
  const sb=document.getElementById("statusBtn"); if(sb) sb.onclick=toggleStatus;
  document.addEventListener("keydown", e=>{ if(e.key==="Escape"){
    if(document.body.classList.contains("fullmap")) setFullmap(false); closeStatus(); } });
  refreshStatus(false);   // color the header heartbeat dot on load (silent-death at a glance)

  loadAvailable();   // calendar dots + perils chip (cached in sessionStorage; non-blocking)

  let geo = { boundaries: [], cities: [] };
  try { geo = await (await fetch("public/geo_ref.json")).json(); } catch(e){}

  let rows = [], banner = null;
  if(date < ARCHIVE_START){
    banner = "No operational radar before "+ARCHIVE_START+" — pick a later date.";
  } else {
    try { rows = await pquery("storm_date_layers", { date }); }
    catch(e){
      try { rows = await (await fetch("public/sample/"+date+".json")).json();
            document.getElementById("connStatus").textContent = "DEMO DATA (proxy offline)"; }
      catch(_){ rows = []; banner = "Couldn't reach the storm proxy — check the connection."; }
    }
    if(!banner && (!rows || !rows.length))
      banner = "No storm on record for "+date+" — nothing processed for this date yet.";
  }
  // forecast tie-in (today's view only): current SPC-outlook risk from the heartbeat
  let forecast = null;
  if(date === todayUTC()){
    try { const fs = await pquery("storm_forecast_status", {});
      if(fs && fs[0]){ const r=fs[0].current_active_risk;
        forecast = (r && r!=="none") ? r : "No qualifying severe risk in the SPC outlook right now."; } }
    catch(e){}
  }
  // ALWAYS render the interactive map (basemap + service-area reference), storm or not.
  const D = assemble(date, rows||[], geo);
  renderMap(D);
  setBaseStreet();
  addNexrad();          // item 7: national NEXRAD overlay (display-only, off by default)
  buildOperatorPanel(D, forecast);
  setupMobile();
  if(banner) showBanner(banner); else hideBanner();
}
boot();
"""


def main():
    html = TEMPLATE.read_text(encoding="utf-8")
    styles = re.findall(r"<style>(.*?)</style>", html, re.S)
    portal_css = styles[1] if len(styles) > 1 else styles[0]
    body_wrap = html[html.index("<body>") + len("<body>"): html.index("<script>")].strip()
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    build = next(s for s in scripts if "STORM_DATA" in s)
    build = build.replace("const STORM_DATA = /*__STORM_DATA__*/null;", "")
    build = build.replace("const D = STORM_DATA;", "")
    # Suppress the vestigial "events 0" summary pill. `summary.events` is hardcoded 0 in
    # assemble() (the read-only portal serves the cached per-peril layer payload, not Event
    # nodes; real Event nodes still exist in the graph). Nothing the operator panel renders
    # depends on it, so the only effect of this pill is to read like an error. Drop it from
    # the reused engine render script (engine template.html itself is never modified).
    build = build.replace('`<span class="pill">events <b>${s.events}</b></span>`+', "")
    render_fn = "function renderMap(D){\n" + build.strip() + "\n}"

    out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
<title>TEMPEST — KCC Storm Review</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@{LEAFLET}/dist/leaflet.css"/>
<style>
{portal_css}
{POLISH_CSS}
</style>
</head>
<body>
<div id="app">
{SHELL_HEAD}{body_wrap}
{SHELL_NODATA}
</div>
<script src="config.js"></script>
<script src="https://unpkg.com/leaflet@{LEAFLET}/dist/leaflet.js"></script>
<script>
{render_fn}
{BOOTSTRAP}
</script>
</body>
</html>
"""
    OUT.write_text(out, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
