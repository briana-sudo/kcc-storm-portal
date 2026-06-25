"""
build_portal.py — generate the TEMPEST portal index.html from the PROVEN
storm-engine viewer template, preserving every §3 locked decision verbatim.

It mechanically: (1) reuses the template's <style> + #wrap body + the entire map
build script (the §3 render core) wrapped as renderMap(D); (2) swaps the vendored
Leaflet for the CDN (the portal is online); (3) wraps it in the TEMPEST shell —
brand header + date navigation (today / back / forward / calendar) + a proxy
fetch layer that pulls each date's cached render payload from the read-only
FastAPI proxy. No §3 color/layer/legend logic is touched — only the chrome
around the map and the data source.

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
:root{ --tmp-bg:#0b1220; --tmp-bg2:#131c2e; --tmp-line:#243456; --tmp-accent:#5b8cff; --tmp-text:#e9eef7; }
html,body{height:100%}
#app{display:flex;flex-direction:column;height:100%}
#tbar{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
  background:linear-gradient(90deg,#0b1220,#16223c);color:#e9eef7;
  padding:8px 14px;box-shadow:0 2px 10px rgba(0,0,0,.3);z-index:1200}
#tbar .brand{display:flex;align-items:center;gap:8px;font-weight:800;letter-spacing:.5px;font-size:16px}
#tbar .brand .logo{font-size:18px;filter:drop-shadow(0 0 6px #5b8cff)}
#tbar .brand .sub{font-weight:500;color:#9fb3d9;font-size:12px;letter-spacing:.3px}
#tbar .datenav{display:flex;align-items:center;gap:6px}
#tbar .datenav button{background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;border-radius:6px;
  padding:5px 10px;font-size:13px;cursor:pointer;line-height:1}
#tbar .datenav button:hover{background:#274069}
#tbar .datenav input[type=date]{background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;
  border-radius:6px;padding:4px 8px;font-size:13px;color-scheme:dark}
#tbar .perils{color:#9fb3d9;font-size:12px;text-transform:uppercase;letter-spacing:.4px}
#tbar .status{margin-left:auto;color:#ffd28a;font-size:12px}
#main{flex:1;min-height:0;position:relative}
#wrap{height:100%}
#side h1{font-size:14px}
.legend{font-size:11.5px}
#nodata{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:rgba(13,20,34,.55);z-index:800}
#nodata.hidden{display:none}
#nodata .nd-card{background:#fff;border-radius:12px;padding:22px 26px;max-width:420px;
  box-shadow:0 8px 30px rgba(0,0,0,.35);text-align:center}
#nodata .nd-card h2{margin:0 0 8px;font-size:18px;color:#16223c}
#nodata .nd-card p{margin:0;color:#5a6b86;font-size:13px;line-height:1.5}
/* mobile: stack the side panel under the map */
@media (max-width:760px){
  #wrap{flex-direction:column}
  #map{flex:none;height:58vh}
  #side{width:auto;max-height:42vh;border-left:none;border-top:1px solid #ddd}
  #tbar{gap:8px}
  #tbar .brand .sub{display:none}
}
"""

SHELL_HEAD = """  <div id="tbar">
    <div class="brand"><span class="logo">&#9731;</span> TEMPEST <span class="sub">KCC Storm Review</span></div>
    <div class="datenav">
      <button id="navPrev" title="Previous day">&#9664;</button>
      <input id="navDate" type="date">
      <button id="navNext" title="Next day">&#9654;</button>
      <button id="navToday">Today</button>
      <span class="perils" id="navPerils"></span>
    </div>
    <div class="status" id="connStatus"></div>
  </div>
  <div id="main">
"""

SHELL_NODATA = """    <div id="nodata" class="hidden"><div class="nd-card">
      <h2 id="ndTitle"></h2><p id="ndMsg"></p></div></div>
  </div>
"""

BOOTSTRAP = """
// ── TEMPEST data + date-navigation shell (chrome; renderMap is the §3 core) ──
// API = the Netlify server-side forwarder (/api/storm). It holds the proxy bearer
// token server-side, so this public bundle carries NO credential of any kind.
const CFG = window.TEMPEST_CONFIG || {};
const API = (CFG.api || "").replace(/\\/$/, "");
const ARCHIVE_START = "2020-10-14";
function todayUTC(){ return new Date().toISOString().slice(0,10); }
function getDate(){ return new URLSearchParams(location.search).get("date") || todayUTC(); }
function goDate(d){ location.search = "?date=" + d; }
function shiftDate(d, n){ const t=new Date(d+"T00:00:00Z"); t.setUTCDate(t.getUTCDate()+n); return t.toISOString().slice(0,10); }
function parseJSON(s){ try{ return JSON.parse(s||"[]"); }catch(e){ return []; } }
async function pquery(name, params){
  const r = await fetch(API, { method:"POST",
    headers:{ "Content-Type":"application/json" },
    body: JSON.stringify({ name, params: params||{} }) });
  if(!r.ok) throw new Error(name+" HTTP "+r.status);
  return (await r.json()).rows || [];
}
function showNoData(title, msg){
  const n=document.getElementById("nodata"); n.classList.remove("hidden");
  document.getElementById("ndTitle").textContent=title;
  document.getElementById("ndMsg").textContent=msg;
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
async function boot(){
  const date = getDate();
  document.getElementById("navDate").value = date;
  document.getElementById("navPrev").onclick  = () => goDate(shiftDate(date, -1));
  document.getElementById("navNext").onclick  = () => goDate(shiftDate(date,  1));
  document.getElementById("navToday").onclick = () => goDate(todayUTC());
  document.getElementById("navDate").onchange = e => goDate(e.target.value);

  if(date < ARCHIVE_START){
    showNoData("No data for "+date, "Operational radar begins "+ARCHIVE_START+". Pick a later date."); return; }

  let geo = { boundaries: [], cities: [] };
  try { geo = await (await fetch("public/geo_ref.json")).json(); } catch(e){}

  let rows = null;
  try { rows = await pquery("storm_date_layers", { date }); }
  catch(e){
    try { rows = await (await fetch("public/sample/"+date+".json")).json();
          document.getElementById("connStatus").textContent = "DEMO DATA (proxy offline)"; }
    catch(_){ showNoData("Proxy unreachable",
        "Could not reach the storm proxy. The site needs VITE_PROXY_URL / token (Cloudflare tunnel) configured."); return; }
  }
  try { const av = await pquery("storm_available_dates", {});
        const m = (av.find(x => x.storm_date === date) || {}).perils;
        if(m && m.length) document.getElementById("navPerils").textContent = m.join("  \\u00b7  "); } catch(e){}

  if(!rows || !rows.length){
    showNoData("No storm on record for "+date,
      "Nothing was processed for this date yet. The daily monitor processes the prior storm day after 13:00 UTC; earlier dates can be backfilled."); return; }

  renderMap(assemble(date, rows, geo));
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
