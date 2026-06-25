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
/* storm-aware calendar popup */
.cal{position:absolute;top:calc(100% + 6px);left:0;z-index:1300;background:#16223c;
  border:1px solid #2c3c5e;border-radius:10px;padding:11px;width:300px;max-width:94vw;color:#e9eef7;
  box-shadow:0 12px 30px rgba(0,0,0,.5);font-size:13px;box-sizing:border-box}
.cal.hidden{display:none}
.cal *{box-sizing:border-box}
.cal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-weight:700;font-size:14px}
.cal-head button{background:#1e2b46;border:1px solid #2c3c5e;color:#e9eef7;border-radius:6px;
  width:30px;height:30px;cursor:pointer;font-size:16px}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:5px}
.cal-dow span{color:#7e90b3;font-size:11px;text-align:center;padding-bottom:4px}
.cal-day{height:40px;border:none;background:#1a2740;color:#cdd8ee;border-radius:7px;cursor:pointer;font-size:13px;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px}
.cal-day:hover{background:#274069}
.cal-day.blank{background:transparent;cursor:default}
.cal-day.today{outline:2px solid #5b8cff}
.cal-day.selected{background:#3056a8;color:#fff;font-weight:700}
.cal-day.storm{font-weight:700;color:#fff}
.cal-day.dim{opacity:.38}
.cal-dots{display:flex;gap:3px;justify-content:center;min-height:6px}
.cal-dots i{width:6px;height:6px;border-radius:50%}
.dot.hail,.cal-dots i.hail{background:#e8430a}
.dot.wind,.cal-dots i.wind{background:#2171b5}
.dot.torn,.cal-dots i.torn{background:#6a3fa0}
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
        <div class="cal-legend"><span><i class="dot hail"></i>hail</span><span><i class="dot wind"></i>wind</span><span><i class="dot torn"></i>tornado</span></div>
      </div>
    </div>
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

// ── storm-aware calendar: dates with data get peril dots (one cached query) ──
async function loadAvailable(){
  try {
    const cached = sessionStorage.getItem("tempest_avail");
    if(cached){ AVAIL = JSON.parse(cached); }
    else {
      const av = await pquery("storm_available_dates", {});
      AVAIL = {}; av.forEach(x => { AVAIL[x.storm_date] = x.perils || []; });
      sessionStorage.setItem("tempest_avail", JSON.stringify(AVAIL));
    }
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
    const btn = document.createElement("button"); btn.className="cal-day"; btn.textContent=d; btn.dataset.date=ds;
    if(ds===today) btn.classList.add("today");
    if(ds===sel) btn.classList.add("selected");
    if(ds<ARCHIVE_START) btn.classList.add("dim");
    const per = AVAIL[ds];
    if(per && per.length){
      btn.classList.add("storm");
      const dots=document.createElement("div"); dots.className="cal-dots";
      per.forEach(p=>{ const i=document.createElement("i"); i.className=(p==="hail"?"hail":p==="wind"?"wind":"torn"); dots.appendChild(i); });
      btn.appendChild(dots);
    }
    btn.onclick = ()=>goDate(ds);
    grid.appendChild(btn);
  }
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
  document.body.appendChild(bd); app.appendChild(tb);
  tb.addEventListener("click",function(e){ const b=e.target.closest("button[data-sheet]"); if(b) openSheet(b.dataset.sheet); });
  bd.addEventListener("click",closeAll);
  window.dispatchEvent(new Event("resize"));   // map recomputes to full size (side panel moved out)
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
  // ALWAYS render the interactive map (basemap + service-area reference), storm or not.
  renderMap(assemble(date, rows||[], geo));
  setBaseStreet();
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
