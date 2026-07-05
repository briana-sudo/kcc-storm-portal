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
  padding:13px 16px;box-shadow:0 2px 10px rgba(0,0,0,.3);z-index:1200}
#tbar .brand{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.5px;font-size:21px}
#tbar .brand .logo{display:inline-flex;align-items:center}
#tbar .brand .tlogo{width:36px;height:36px;display:block}
#tbar .brand .sub{font-weight:600;color:#f5b100;font-size:12px;letter-spacing:1.2px;text-transform:uppercase}
/* mobile: keep the bigger logo but tighten the bar a touch so it doesn't dominate */
body.mobile #tbar{padding:10px 13px}
body.mobile #tbar .brand{font-size:19px}
body.mobile #tbar .brand .tlogo{width:32px;height:32px}
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
#tbar #alertBtn{background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar #alertBtn:hover{background:#274069}
#tbar #alertBtn.alerts-on{background:#1c7a3a;border-color:#2ea862;color:#eafff0}
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
/* ── CHASE LAYER control (item 8 Step 3): toggle + opacity for the 150mi ring fill.
   OFF by default; coexists with in-market (never hides it). ── */
.chasectl{background:#fff;padding:6px 9px;border-radius:6px;box-shadow:0 1px 5px rgba(0,0,0,.3);font-size:12px;max-width:230px}
.chasectl label{display:flex;align-items:center;gap:6px;font-weight:700;cursor:pointer}
.chasectl .muted{color:#888;font-weight:400}
.chasectl .chasesub{display:flex;align-items:center;gap:7px;margin-top:5px}
.chasectl .chasesub.off{opacity:.45}
.chasectl input[type=range]{flex:1}
.chasectl #chasev{min-width:34px;text-align:right;color:#555}
.chasectl .ckey{margin-top:5px;color:#667;font-size:11px;line-height:1.4}
.chasectl .ckey i{display:inline-block;width:13px;height:0;border-top:2px dashed #c1121f;vertical-align:middle;margin-right:4px}
/* ── BOTTOM-EDGE SLIDE-UP DRAWERS: LIVE + Active perils sit as tabs along the
   BOTTOM of the map (no longer overlay the left side). Click a tab -> the panel
   slides UP above it; click again -> slides back down to just the tab. Desktop
   only (mobile uses the slide-up sheets). Layers panel stays on the right. ── */
#bottomDrawers{position:absolute;left:8px;bottom:6px;z-index:1150;display:flex;gap:10px;align-items:flex-end;pointer-events:none}
.bdrawer{display:flex;flex-direction:column;justify-content:flex-end;pointer-events:auto;max-width:340px}
.bdrawer .btab{align-self:flex-start;background:#16223c;color:#e9eef7;border:1px solid #2c3c5e;border-bottom:none;
  border-radius:8px 8px 0 0;padding:6px 14px;font-size:11px;font-weight:800;letter-spacing:.6px;cursor:pointer;white-space:nowrap;
  box-shadow:0 -2px 9px rgba(0,0,0,.3);user-select:none}
.bdrawer .btab:hover{background:#22324f}
.bdrawer .bbody{max-width:340px;max-height:0;overflow:hidden;transition:max-height .25s ease;opacity:0}
.bdrawer.open .bbody{max-height:64vh;overflow:auto;opacity:1;margin-bottom:2px}
.bdrawer .bbody-inner .livectl,.bdrawer .bbody-inner .legend{position:static !important;margin:0 !important;max-width:330px}
/* ── MAP LOCATION SEARCH in the TOP BANNER (city/state + address typeahead) —
   navigation only. Reuses the weather tab's Photon (OSM) geocoder; no key/proxy. ── */
#tbar .hdr-search{display:flex;align-items:center;gap:5px;position:relative}
#tbar .hdr-search input{padding:5px 8px;border:1px solid #2c3c5e;border-radius:6px;background:#1e2b46;color:#e9eef7;font-size:13px}
#tbar .hdr-search input::placeholder{color:#7e90b3}
#tbar .hdr-search #msCity{width:170px}
#tbar .hdr-search #msAddr{width:300px}
#tbar .hdr-search .ms-go{background:#1e2b46;color:#e9eef7;border:1px solid #2c3c5e;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar .hdr-search .ms-go:hover{background:#274069}
#tbar .hdr-search .ms-clear{background:#1e2b46;color:#9fb3d9;border:1px solid #2c3c5e;border-radius:6px;width:24px;height:28px;
  padding:0;font-size:15px;line-height:1;cursor:pointer;flex:none}
#tbar .hdr-search .ms-clear:hover{color:#fff;background:#274069}
#tbar .hdr-search .ms-addrwrap{position:relative;display:flex;align-items:center;gap:5px}
.ms-sugg{position:absolute;left:0;top:calc(100% + 4px);z-index:1400;min-width:360px;max-width:440px;background:#fff;border:1px solid #c9d2dd;
  border-radius:6px;box-shadow:0 12px 28px rgba(0,0,0,.45);max-height:320px;overflow:auto}
.ms-sugg:empty{display:none}
.ms-sg{display:block;width:100%;text-align:left;background:none;border:none;border-bottom:1px solid #eef1f5;
  padding:7px 10px;font-size:12.5px;line-height:1.35;cursor:pointer;color:#223;white-space:normal}
.ms-sg:hover{background:#eef3ff}
body.mobile #tbar .hdr-search #msCity{width:120px}
body.mobile #tbar .hdr-search #msAddr{width:150px}
/* ── PULL (item 10): on-demand 150mi capture. Header button + a floating confirm bar. ── */
#tbar #pullBtn{background:#143a2a;color:#bdf0d6;border:1px solid #2c6e4c;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar #pullBtn:hover{background:#1a5038}
body.pull-armed #tbar #pullBtn{background:#2c6e4c;color:#fff}
#pullPanel{position:absolute;left:50%;top:64px;transform:translateX(-50%);z-index:2500;display:flex;align-items:center;gap:10px;
  background:rgba(11,18,32,.96);color:#e9eef7;border:1px solid #2c6e4c;border-radius:9px;padding:9px 14px;font-size:13px;
  box-shadow:0 8px 24px rgba(0,0,0,.5);max-width:92vw}
#pullPanel .pp-txt{font-weight:600}
#pullPanel .pp-go{background:#1a7a4f;color:#fff;border:none;border-radius:6px;padding:6px 12px;font-weight:700;cursor:pointer}
#pullPanel .pp-go:disabled{opacity:.6;cursor:default}
#pullPanel .pp-x{background:#1e2b46;color:#cdd8ee;border:1px solid #2c3c5e;border-radius:6px;padding:6px 11px;cursor:pointer}
#pullPanel .pp-status{font-size:12px;color:#ffd28a}
/* center crosshair = the pull circle's center / aim point (over the map center) */
#pullCrosshair{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:48px;height:48px;z-index:1100;pointer-events:none}
#pullCrosshair .ch-h{position:absolute;left:0;right:0;top:50%;height:2px;background:#2f6fe0;transform:translateY(-50%);box-shadow:0 0 2px #fff,0 0 2px #fff}
#pullCrosshair .ch-v{position:absolute;top:0;bottom:0;left:50%;width:2px;background:#2f6fe0;transform:translateX(-50%);box-shadow:0 0 2px #fff,0 0 2px #fff}
#pullCrosshair .ch-dot{position:absolute;left:50%;top:50%;width:9px;height:9px;border-radius:50%;background:#2f6fe0;border:2px solid #fff;transform:translate(-50%,-50%);box-shadow:0 0 3px rgba(0,0,0,.4)}
/* ── LIVE (current) awareness group (item 7 ext): NEXRAD loop + NWS warnings +
   storm-track cones. Three independent toggles + opacity dials, visually separated
   from the engine's date-driven scored layers. All display-only, in-memory only. ── */
.livectl{background:#fff;padding:8px 10px;border-radius:7px;box-shadow:0 1px 6px rgba(0,0,0,.35);font-size:12px;max-width:244px}
.livectl .live-hd{display:flex;flex-direction:column;border-bottom:1px solid #e3e8f0;padding-bottom:5px;margin-bottom:5px}
.livectl .live-hd b{font-size:11px;letter-spacing:.5px;color:#0b1220;display:flex;align-items:center;gap:6px}
.livectl .live-hd .tag{background:#0b3;color:#fff;font-size:8px;font-weight:800;letter-spacing:.5px;padding:1px 5px;border-radius:9px;text-transform:uppercase}
.livectl .live-hd small{color:#8a93a6;font-size:9px;letter-spacing:.2px;margin-top:1px}
.livectl .live-row{margin:7px 0 0}
.livectl label{display:flex;align-items:center;gap:6px;font-weight:700;cursor:pointer;color:#222}
.livectl label .muted{color:#9aa3b4;font-weight:500;font-size:10px}
.livectl .live-sub,.livectl .live-op{display:flex;align-items:center;gap:6px;margin-top:4px;padding-left:21px}
.livectl .live-sub.off,.livectl .live-op.off{opacity:.4;pointer-events:none}
.livectl .live-sub button{background:#1e2b46;border:none;color:#fff;border-radius:5px;width:27px;height:22px;cursor:pointer;font-size:11px}
.livectl .live-sub #lvNow{width:auto;padding:0 7px;font-size:9px;font-weight:800;letter-spacing:.5px;background:#0a8a2e}
.livectl .live-sub{flex-wrap:wrap}
.livectl .live-sub #lvTz{width:auto;padding:0 7px;font-size:9px;font-weight:800;letter-spacing:.5px;background:#3056a8}
.livectl .live-sub #lvTz.armed{background:#e8430a}
.livectl .live-sub .ts{min-width:88px}
/* timezone-change confirmation toast: notes area + tz, X to close, auto-closes 5s */
.tz-toast{position:fixed;top:64px;left:50%;transform:translateX(-50%);z-index:3000;background:#0f1830;color:#e9eef7;
  border:1px solid #2c3c5e;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.5);padding:11px 14px;
  display:flex;align-items:flex-start;gap:12px;max-width:92vw;font-size:13px;animation:tzin .18s ease-out}
@keyframes tzin{from{opacity:0;transform:translate(-50%,-6px)}to{opacity:1;transform:translate(-50%,0)}}
.tz-toast .tz-msg b{color:#7fd1ff}
.tz-toast .tz-ab{background:#1e2b46;color:#cfe3ff;font-size:10px;font-weight:800;padding:1px 6px;border-radius:9px;margin-left:4px}
.tz-toast .tz-area{color:#9fb3d9;font-size:11px;margin-top:3px}
.tz-toast .tz-x{background:transparent;border:none;color:#9fb3d9;font-size:20px;line-height:1;cursor:pointer;padding:0 2px;margin-top:-2px}
.tz-toast .tz-x:hover{color:#fff}
body.tz-arming .leaflet-container{cursor:crosshair}
body.tz-arming::after{content:"Click the map to set the timezone";position:fixed;top:64px;left:50%;transform:translateX(-50%);
  z-index:3000;background:#e8430a;color:#fff;font-size:12px;font-weight:700;padding:6px 13px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.4)}
.livectl input[type=range]{flex:1;min-width:60px}
.livectl .ts{font-variant-numeric:tabular-nums;color:#0a8a2e;font-weight:700;font-size:10px;min-width:104px;text-align:right}
.livectl .opv{min-width:32px;text-align:right;color:#555}
.livectl .lv-master{display:flex;align-items:center;gap:6px;cursor:pointer;margin:0}
.livectl.lv-off .live-row{opacity:.35;pointer-events:none}
/* typed storm-cell icons (item 7 ext): tornado funnel / hailstone+size / rotation swirl /
   dot. In trackPane (pointerEvents:none) so re-enable hit-testing on the icons themselves. */
.trk-ic{background:none;border:none;pointer-events:auto}
.trk-ic svg{display:block;filter:drop-shadow(0 0 1.5px rgba(0,0,0,.55))}
.ic-hail{display:flex;align-items:center;gap:1px}
.ic-hail b{font:800 11px/1 system-ui,sans-serif;text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 3px #fff,0 0 3px #fff}
.ic-dot{display:block;width:7px;height:7px;border-radius:50%;background:#2f8fff;border:1px solid #fff;box-shadow:0 0 2px rgba(0,0,0,.5)}
/* clear click popup: labeled rows (label left / value right) */
.trk-pop .leaflet-popup-content{margin:9px 12px;font-size:12px;color:#13203c;min-width:184px}
.trk-pop .pp-h{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-bottom:4px}
.trk-pop .pp-h b{font-size:13px;color:#0b1220}
.trk-pop .pp-h span{color:#8a93a6;font-size:10px}
.trk-pop .pp-row{display:flex;justify-content:space-between;gap:16px;padding:3px 0;border-top:1px solid #eef0f5}
.trk-pop .pp-row>span{color:#5a667a}
.trk-pop .pp-row>b{color:#13203c;font-weight:700}
.trk-pop .pp-ago>b{color:#0a8a2e}
/* storm-aware calendar popup */
.cal{position:absolute;top:calc(100% + 6px);left:0;z-index:1300;background:#16223c;
  border:1px solid #2c3c5e;border-radius:10px;padding:13px;width:404px;max-width:96vw;color:#e9eef7;
  box-shadow:0 12px 30px rgba(0,0,0,.5);font-size:14px;box-sizing:border-box}
.cal.hidden{display:none}
.cal *{box-sizing:border-box}
.cal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-weight:700;font-size:14px}
.cal-head button{background:#1e2b46;border:1px solid #2c3c5e;color:#e9eef7;border-radius:6px;
  width:30px;height:30px;cursor:pointer;font-size:16px}
.cal-head .cal-title{width:auto;flex:1;margin:0 6px;height:30px;font-weight:800;font-size:14px;letter-spacing:.3px}
.cal-head .cal-title:hover{background:#274069}
/* quick month/year picker (click the title) — replaces the day grid while open */
.cal.picking #calDays,.cal.picking .cal-dow,.cal.picking .cal-legend{display:none}
.cal-pick.hidden{display:none}
.cp-yr{display:flex;align-items:center;justify-content:center;gap:14px;margin:4px 0 12px;font-weight:800;font-size:15px}
.cp-yr button{background:#1e2b46;border:1px solid #2c3c5e;color:#e9eef7;border-radius:6px;width:32px;height:30px;cursor:pointer;font-size:16px}
.cp-yr span{min-width:64px;text-align:center;color:#cdeafe}
.cp-months{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.cp-mo{background:#1a2740;border:none;color:#cdd8ee;border-radius:8px;padding:11px 0;font-size:13px;font-weight:700;cursor:pointer}
.cp-mo:hover{background:#274069}
.cp-mo.sel{background:#3056a8;color:#fff}
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
.dot.torn,.cal-dots i.torn{background:#e11421}
/* tier treatment (item 4): P1 core = bright + halo ring, P2 = solid, P3 margin = hollow/faint */
.cal-dots i.t1{width:10px;height:10px;box-shadow:0 0 0 2px rgba(255,255,255,.9),0 0 4px rgba(0,0,0,.5)}
.cal-dots i.t3{background:transparent;opacity:.7}
.cal-dots i.t3.hail{border-color:#f7b600}
.cal-dots i.t3.wind{border-color:#6bafd7}
.cal-dots i.t3.torn{border-color:#e11421}
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
body.mobile #tbar .brand .sub{font-size:10px;letter-spacing:.8px}
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

/* ===== WEATHER TAB (rain forecast for scheduling) — isolated tool view ===== */
#tbar #wxBtn{background:#16324a;color:#cdeafe;border:1px solid #2c4c6e;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar #wxBtn:hover{background:#1d456a}
#wxBackdrop{position:fixed;inset:0;z-index:2490;background:rgba(6,12,22,.55)}
#wxBackdrop.hidden{display:none}
.wx-panel{position:fixed;top:0;right:0;height:100%;width:420px;max-width:96vw;z-index:2500;background:#0f1830;color:#e9eef7;
  box-shadow:-12px 0 36px rgba(0,0,0,.5);display:flex;flex-direction:column;border-left:1px solid #243352}
.wx-panel.hidden{display:none}
.wx-hd{display:flex;align-items:center;gap:10px;padding:13px 15px;border-bottom:1px solid #243352}
.wx-hd b{font-size:15px;letter-spacing:.3px}.wx-hd .wx-sub{color:#8aa0c6;font-size:11px}
.wx-hd .wx-x{margin-left:auto;background:transparent;border:none;color:#9fb3d9;font-size:22px;line-height:1;cursor:pointer}
.wx-hd .wx-x:hover{color:#fff}
.wx-loc{padding:11px 15px;border-bottom:1px solid #243352;background:#0c1426}
.wx-place{font-weight:800;font-size:14px;margin-bottom:7px;color:#cdeafe}
.wx-form{display:flex;gap:6px}
.wx-addr{flex:1;background:#16223c;border:1px solid #2c3c5e;border-radius:7px;color:#e9eef7;padding:7px 9px;font-size:12px}
.wx-form button,.wx-pick,.wx-here{background:#2f6fe0;border:none;color:#fff;border-radius:7px;padding:7px 11px;font-size:12px;font-weight:700;cursor:pointer}
.wx-loc-btns{display:flex;gap:6px;margin-top:6px}
.wx-here{flex:1;background:#1e8a4a}.wx-pick{flex:1;background:#3a4a66}
.wx-sugg{display:flex;flex-direction:column;margin-top:5px;background:#0c1426;border-radius:8px;overflow:hidden}
.wx-sugg:empty{display:none}
.wx-sg{text-align:left;background:transparent;border:none;border-bottom:1px solid #1a2740;color:#dbe7fb;padding:8px 10px;font-size:12px;cursor:pointer}
.wx-sg:last-child{border-bottom:none}.wx-sg:hover{background:#16223c}
.wx-gc-status{font-size:11px;color:#ffb27a;min-height:14px;margin-top:4px}
.wx-body{flex:1;overflow:auto;padding:13px 15px}
.wx-load,.wx-err{color:#9fb3d9;font-size:13px;padding:18px 4px;text-align:center}
.wx-err{color:#ff9a76}
.wx-now{border-radius:11px;padding:12px 13px;margin-bottom:14px}
.wx-now.wx-wet{background:#3a1b1b;border:1px solid #7a2b2b}.wx-now.wx-risk{background:#3a3320;border:1px solid #7a6a2b}.wx-now.wx-dry{background:#15301f;border:1px solid #2b6a45}
.wx-now-h{font-weight:800;font-size:15px}.wx-now-s{font-size:12px;color:#cfe;margin-top:3px}.wx-now-note{font-size:10px;color:#8aa0c6;margin-top:6px;font-style:italic}
.wx-sec-t{font-weight:800;font-size:11px;letter-spacing:.6px;text-transform:uppercase;color:#8aa0c6;margin:6px 0 7px}
.wx-sunline{display:flex;gap:18px;font-size:12px;color:#d7e6ff;margin:0 0 12px;padding:8px 11px;background:#13203c;border-radius:9px}
.wx-hours{display:flex;gap:5px;overflow-x:auto;padding-bottom:8px;margin-bottom:14px}
.wx-h{flex:0 0 auto;width:42px;display:flex;flex-direction:column;align-items:center;gap:3px;background:#13203c;border-radius:8px;padding:6px 2px}
.wx-h.wx-sunrise,.wx-h.wx-sunset{background:#1b2a17;box-shadow:inset 0 0 0 1px #3c5a2c}
.wx-ht{font-size:9px;color:#8aa0c6;white-space:nowrap}.wx-hv{font-size:10px;font-weight:800;color:#7fd1ff}.wx-htemp{font-size:9px;color:#9fb3d9}
.wx-ic{font-size:15px;line-height:1}
.wx-bar{height:42px;width:14px;display:flex;align-items:flex-end;background:#0c1426;border-radius:3px;overflow:hidden}
.wx-bar i{display:block;width:100%;background:linear-gradient(#7fd1ff,#2f6fe0);border-radius:3px}
.wx-note{color:#5a667a;font-weight:500;font-size:9px;text-transform:none;letter-spacing:0}
.wx-days{display:flex;flex-direction:column;gap:5px}
.wx-d{display:grid;grid-template-columns:74px 20px 40px 1fr auto;gap:8px;align-items:center;background:#13203c;border-radius:8px;padding:7px 10px;font-size:12px}
.wx-di{font-size:14px;line-height:1;text-align:center}
.wx-d.night{background:#0e1830;opacity:.92}
.wx-dn{font-weight:700;color:#cdeafe;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.wx-dv{font-weight:800;color:#6f87a8}.wx-dv.mid{color:#7fd1ff}.wx-dv.hi{color:#ff8aa0}
.wx-ds{color:#aebcd4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.wx-dt{color:#9fb3d9;font-weight:700}
.wx-saved{border-top:1px solid #243352;padding:11px 15px;background:#0c1426}
.wx-saved-h{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.wx-saved-h b{font-size:12px}.wx-save-cur{margin-left:auto;background:#243352;border:none;color:#cdeafe;border-radius:6px;padding:5px 9px;font-size:11px;font-weight:700;cursor:pointer}
.wx-saved-list{display:flex;flex-direction:column;gap:5px;max-height:140px;overflow:auto}
.wx-empty{color:#6f87a8;font-size:11px;font-style:italic}
.wx-srow{display:flex;gap:6px}
.wx-go{flex:1;text-align:left;background:#13203c;border:1px solid #243352;color:#e9eef7;border-radius:7px;padding:7px 9px;font-size:12px;cursor:pointer}
.wx-go:hover{background:#1b2c4e}
.wx-del{background:#2a1622;border:1px solid #5a2b3b;color:#ff9ab0;border-radius:7px;width:30px;font-size:16px;cursor:pointer}
body.wx-arming .leaflet-container{cursor:crosshair}
body.wx-arming::after{content:"Click the map to set the weather location";position:fixed;top:64px;left:50%;transform:translateX(-50%);
  z-index:3000;background:#2f6fe0;color:#fff;font-size:12px;font-weight:700;padding:6px 13px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.4)}
@media(max-width:520px){.wx-panel{width:100%}}

/* map locate / re-centre control (matches the Leaflet zoom bar) */
.locate-ctl a{display:flex;align-items:center;justify-content:center;width:30px;height:30px;font-size:18px;color:#0b1220;text-decoration:none;background:#fff}
.locate-ctl a:hover{background:#eef3ff}
/* Swath render (Cells vs Smooth) — injected into the §3 Layers panel, styled to match */
.swathrender{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:5px 0;border-bottom:1px solid #e8e8e8;margin-bottom:2px}
.swathrender .srlabel{font-size:11px;font-weight:600;color:#26344d}
.swathrender .st-btns{display:flex;gap:4px}
.swathrender button{border:1px solid #c7d2e0;background:#f3f6fb;color:#26344d;border-radius:6px;padding:2px 9px;font-size:11px;font-weight:700;cursor:pointer}
.swathrender button.on{background:#2f6fe0;border-color:#2f6fe0;color:#fff}
.leaflet-image-layer.hailheat{image-rendering:auto}
/* ── #6 RANKED-TARGETS badges (payout_score): additive label pane over the §3
   ad circles. P1 deep-red / P2 orange to echo the locked ring colors; floor-muted
   circles get a greyed, dashed badge (flagged, not deleted). Toggle = the # button. */
.rankwrap{background:none;border:none}
.rankbadge{display:flex;align-items:center;gap:3px;transform:translate(-50%,-50%);
  font:800 11px/1 system-ui,sans-serif;color:#fff;padding:2px 6px;border-radius:11px;
  white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.5);border:1.5px solid #fff}
.rankbadge b{font-size:11px}
.rankbadge .rs{font-weight:600;font-size:9px;opacity:.92;padding-left:2px;border-left:1px solid rgba(255,255,255,.5)}
.rankbadge.t1{background:#bd0026}        /* P1 core */
.rankbadge.t2{background:#e8430a}        /* P2 */
.rankbadge.muted{background:#6b7280;border-style:dashed;opacity:.78}
.rankctl a.on{background:#bd0026;color:#fff}
.rankctl a{font-weight:800}
/* ── SPEND-DIAL PANEL (operator decision surface; single-gate portal approval) ──
   Desktop: docks in the right #side region. Mobile: relocated into a bottom-sheet behind
   the "$ Spend" toolbar button (setupMobile). Solve->Send->Approve; Approve = the ONE gate
   (shared desktop + mobile modal). No email path anywhere. */
#spendPanel{font-size:12.5px;color:#13203c}
#spendPanel h2{font-size:14px;margin:2px 0 8px;display:flex;align-items:center;gap:7px}
#spendPanel h2 .pk{margin-left:auto;font-size:10px;font-weight:800;letter-spacing:.5px;color:#fff;background:#bd0026;padding:2px 7px;border-radius:10px}
.sd-row{display:flex;align-items:center;gap:8px;margin:7px 0}
.sd-row label{flex:0 0 92px;color:#445;font-weight:700;font-size:11.5px}
.sd-row input[type=range]{flex:1}
.sd-row .val{min-width:64px;text-align:right;font-variant-numeric:tabular-nums;font-weight:700;color:#13203c}
.sd-seg{display:flex;gap:4px}
.sd-seg button{border:1px solid #c7d2e0;background:#f3f6fb;color:#26344d;border-radius:6px;padding:3px 9px;font-size:11px;font-weight:700;cursor:pointer}
.sd-seg button.on{background:#2f6fe0;border-color:#2f6fe0;color:#fff}
.sd-peril button:disabled{opacity:.4;cursor:not-allowed}
.sd-cap{display:flex;gap:10px;margin:8px 0;padding:7px 9px;background:#eef3ff;border-radius:7px;font-size:11.5px}
.sd-cap b{color:#13203c}
.sd-actions{display:flex;gap:8px;margin:10px 0 4px}
.sd-actions button{flex:1;border:none;border-radius:8px;padding:9px 0;font-size:13px;font-weight:800;cursor:pointer}
#sdSolve{background:#1e2b46;color:#fff}#sdSolve:hover{background:#274069}
#sdSend{background:#1a7a4f;color:#fff}#sdSend:hover{background:#1f9160}
#sdSend:disabled{background:#9fb3a8;cursor:default}
.sd-verdict{margin:8px 0;padding:8px 10px;border-radius:7px;font-size:12px;font-weight:600;background:#fff4e6;border-left:4px solid #e8430a;color:#5a3a1a}
.sd-verdict.ok{background:#eaf7ef;border-left-color:#1a7a4f;color:#1c4a32}
.sd-verdict.warn{background:#fdeaea;border-left-color:#bd0026;color:#7a1620}
.sd-claimwarn{margin:0 0 9px;padding:8px 10px;border-radius:7px;font-size:11.5px;font-weight:700;
  background:#fff3cd;border:1px solid #e0a800;color:#7a5b00}
.sd-stale{opacity:.5;pointer-events:none}
/* NO QUALIFIED STORM: the dial has nothing to fund -> gray + dead controls. The floatbox
   chrome (drag/X) and the row-2 button stay active; only #spendPanel's controls disable. */
#spendPanel.sd-nostorm .sd-row,#spendPanel.sd-nostorm .sd-cap,#spendPanel.sd-nostorm .sd-actions,
#spendPanel.sd-nostorm #sdVerdict,#spendPanel.sd-nostorm .sd-table{opacity:.4;pointer-events:none;filter:grayscale(1)}
#spendPanel .sd-nostormmsg{display:none;margin:6px 0 4px;padding:9px 11px;border-radius:7px;
  background:#eef1f5;border-left:4px solid #9aa3b4;color:#445;font-weight:700;font-size:12px}
#spendPanel.sd-nostorm .sd-nostormmsg{display:block}
.sd-table{width:100%;border-collapse:collapse;font-size:11px;margin-top:6px}
.sd-table th{text-align:right;color:#667;font-weight:700;padding:3px 5px;border-bottom:1px solid #e3e8f0}
.sd-table th:first-child,.sd-table td:first-child{text-align:left}
.sd-table td{padding:3px 5px;border-bottom:1px solid #f0f3f7;text-align:right;cursor:pointer}
.sd-table tr:hover td{background:#eef3ff}
.sd-band{display:inline-block;width:9px;height:9px;border-radius:50%;vertical-align:-1px}
.sd-band.in_band{background:#1a7a4f}.sd-band.red_low{background:#d9a600}.sd-band.red_high{background:#bd0026}
.sd-table tr.dropped td{opacity:.5;font-style:italic}
/* circle popup (rebuilt drill-down) */
#sdPop{position:fixed;z-index:2700;max-width:320px;background:#fff;border:1px solid #c9d2dd;border-radius:10px;
  box-shadow:0 14px 36px rgba(0,0,0,.5);padding:11px 13px;font-size:12px;color:#13203c}
#sdPop.hidden{display:none}
#sdPop h3{margin:0 0 5px;font-size:13px;display:flex;align-items:center;gap:6px}
#sdPop .sd-pop-x{margin-left:auto;background:none;border:none;font-size:16px;cursor:pointer;color:#889}
#sdPop .r{display:flex;justify-content:space-between;gap:14px;padding:2px 0;border-top:1px solid #f0f3f7}
#sdPop .r span{color:#667}#sdPop .r b{color:#13203c}
#sdPop .sd-status{margin-top:6px;padding:5px 8px;border-radius:6px;font-weight:700;font-size:11.5px}
#sdPop .sd-status.funded{background:#eaf7ef;color:#1c4a32}
#sdPop .sd-status.dropped{background:#fdeaea;color:#7a1620}
#sdPop .sd-conf{color:#bd0026;font-size:10.5px;margin-top:3px}
/* APPROVE modal — the single gate (desktop + mobile) */
#sdModalBack{position:fixed;inset:0;z-index:2800;background:rgba(6,12,22,.6)}
#sdModalBack.hidden{display:none}
#sdModal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:2810;width:420px;max-width:94vw;
  background:#0f1830;color:#e9eef7;border:1px solid #2c3c5e;border-radius:13px;box-shadow:0 20px 60px rgba(0,0,0,.7);padding:16px 18px}
#sdModal h2{margin:0 0 4px;font-size:16px}
#sdModal .sd-sub{color:#8aa0c6;font-size:11px;margin-bottom:10px}
#sdModal .sd-line{display:flex;justify-content:space-between;padding:5px 0;border-top:1px solid #24324e;font-size:13px}
#sdModal .sd-line b{color:#7fd1ff}
#sdModal .sd-mbtns{display:flex;gap:9px;margin-top:14px}
#sdModal .sd-mbtns button{flex:1;border:none;border-radius:9px;padding:11px 0;font-size:14px;font-weight:800;cursor:pointer}
#sdLaunch{background:#1a7a4f;color:#fff}#sdLaunch:hover{background:#1f9160}
#sdCancel{background:#1e2b46;color:#cdd8ee}#sdCancel:hover{background:#274069}
/* desktop: the spend button in the top bar */
#tbar #spendBtn{background:#143a2a;color:#bdf0d6;border:1px solid #2c6e4c;border-radius:6px;padding:5px 10px;font-size:13px;cursor:pointer}
#tbar #spendBtn:hover{background:#1a5038}

/* MOBILE: collapsible LIVE box — sits on the map above the bottom toolbar; collapsed to
   just its header, taps slide it up/down. #banner (no-storm) parks just above it. */
body.mobile .livectl.mobile-live{position:fixed;left:8px;right:8px;bottom:60px;width:auto;max-width:none;
  max-height:34px;overflow:hidden;transition:max-height .26s ease;z-index:1455}
body.mobile .livectl.mobile-live .live-hd{cursor:pointer;margin-bottom:0}
body.mobile .livectl.mobile-live.lv-expanded{max-height:78vh !important;overflow:auto}
body.mobile #banner{bottom:102px}

/* ── DESKTOP 2ND TOOLBAR ROW (#tbar2) + FLOATING DRAGGABLE PANELS ──
   Layers / Storm Review / Spend Dial / Active perils / LIVE become draggable, closeable
   boxes opened from #tbar2 toggle buttons (Weather opens its existing slide-in tool).
   All CLOSED on load; desktop only (mobile keeps the bottom-sheet lane). No persistence. */
#tbar2{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#0d1626;
  border-top:1px solid #1d2b46;padding:7px 16px;z-index:1190}
#tbar2 .fb-btn{background:#1e2b46;color:#cdd8ee;border:1px solid #2c3c5e;border-radius:7px;
  padding:5px 11px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px;line-height:1}
#tbar2 .fb-btn:hover{background:#274069}
#tbar2 .fb-btn.active{background:#2f6fe0;border-color:#2f6fe0;color:#fff}
body.mobile #tbar2,body.fullmap #tbar2{display:none}
body:not(.mobile) #wxBtn{display:none}   /* desktop: Weather lives on row 2; mobile keeps the top-bar button */
.floatbox{position:absolute;z-index:1300;display:none;flex-direction:column;width:340px;max-height:82vh;
  background:#fff;border:1px solid #2c3c5e;border-radius:11px;box-shadow:0 14px 44px rgba(0,0,0,.5)}
.floatbox.open{display:flex}
.floatbox .fb-title{display:flex;align-items:center;gap:8px;cursor:move;user-select:none;
  background:linear-gradient(90deg,#0b1220,#16223c);color:#e9eef7;padding:8px 12px;
  border-radius:11px 11px 0 0;font-weight:700;font-size:12px;letter-spacing:.4px}
.floatbox .fb-title .fb-x{margin-left:auto;background:transparent;border:none;color:#9fb3d9;
  font-size:19px;line-height:1;cursor:pointer;padding:0 2px}
.floatbox .fb-title .fb-x:hover{color:#fff}
.floatbox .fb-body{overflow:auto;padding:9px 11px;border-radius:0 0 11px 11px}
.floatbox .fb-body>*{position:static !important;width:auto !important;max-width:none !important;
  max-height:none !important;box-shadow:none !important;border:none !important;margin:0 !important}
"""

SHELL_HEAD = """  <div id="tbar">
    <div class="brand"><span class="logo"><svg class="tlogo" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" aria-label="TEMPEST"><defs><linearGradient id="swTT" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F5B100" stop-opacity="0.55"/><stop offset="1" stop-color="#F5B100" stop-opacity="0.02"/></linearGradient><clipPath id="hxTT"><polygon points="106.00,60.00 83.00,99.84 37.00,99.84 14.00,60.00 37.00,20.16 83.00,20.16"/></clipPath></defs><g clip-path="url(#hxTT)"><path d="M60 60 L60 16 A44 44 0 0 1 98.85 39.34 Z" fill="url(#swTT)"/><line x1="60" y1="60" x2="106" y2="60" stroke="#F5B100" stroke-width="0.7" opacity="0.30"/><line x1="60" y1="60" x2="83" y2="99.84" stroke="#F5B100" stroke-width="0.7" opacity="0.30"/><line x1="60" y1="60" x2="37" y2="99.84" stroke="#F5B100" stroke-width="0.7" opacity="0.30"/><line x1="60" y1="60" x2="14" y2="60" stroke="#F5B100" stroke-width="0.7" opacity="0.30"/><line x1="60" y1="60" x2="37" y2="20.16" stroke="#F5B100" stroke-width="0.7" opacity="0.30"/><line x1="60" y1="60" x2="83" y2="20.16" stroke="#F5B100" stroke-width="0.7" opacity="0.30"/><line x1="60" y1="60" x2="98.85" y2="39.34" stroke="#9BD8FF" stroke-width="2.2"/><circle cx="76.92" cy="30.51" r="3" fill="#9BD8FF"/><circle cx="45.34" cy="43.59" r="2.2" fill="#F5B100"/><circle cx="97.24" cy="67.55" r="2.4" fill="#F5B100"/><circle cx="74.74" cy="53.77" r="2.0" fill="#F5B100"/><circle cx="54.85" cy="20.33" r="2.2" fill="#F5B100"/><circle cx="31.27" cy="51.38" r="2.6" fill="#9BD8FF"/></g><polygon points="106.00,60.00 83.00,99.84 37.00,99.84 14.00,60.00 37.00,20.16 83.00,20.16" fill="none" stroke="#F5B100" stroke-width="2.4" stroke-linejoin="round"/><polygon points="88.00,60.00 74.00,84.25 46.00,84.25 32.00,60.00 46.00,35.75 74.00,35.75" fill="none" stroke="#F5B100" stroke-width="1.6" stroke-linejoin="round" opacity="0.85"/><circle cx="60" cy="60" r="4" fill="#F5B100"/></svg></span> TEMPEST <span class="sub">KCC Hail Intelligence</span></div>
    <div class="datenav">
      <button id="navPrev" title="Previous day">&#9664;</button>
      <button id="navDateBtn" class="datebtn">&mdash;</button>
      <button id="navNext" title="Next day">&#9654;</button>
      <button id="navToday">Today</button>
      <span class="perils" id="navPerils"></span>
      <div id="cal" class="cal hidden">
        <div class="cal-head"><button id="calPrev">&#8249;</button><button id="calTitle" class="cal-title" title="Pick month / year"></button><button id="calNext">&#8250;</button></div>
        <div class="cal-grid cal-dow"><span>Su</span><span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span></div>
        <div class="cal-grid" id="calDays"></div>
        <div class="cal-pick hidden" id="calPick">
          <div class="cp-yr"><button id="cpYrPrev">&#8249;</button><span id="cpYr"></span><button id="cpYrNext">&#8250;</button></div>
          <div class="cp-months" id="cpMonths"></div>
        </div>
        <div class="cal-legend"><span><i class="dot hail"></i>hail</span><span><i class="dot wind"></i>wind</span><span><i class="dot torn"></i>tornado</span><span style="margin-left:auto;color:#7e90b3">&#9679;core &#9675;margin</span></div>
      </div>
    </div>
    <div class="hdr-search">
      <input id="msCity" type="text" placeholder="City, ST" title="Jump to a city/state">
      <button class="ms-clear" type="button" data-clear="msCity" title="Clear">&times;</button>
      <button id="msCityGo" class="ms-go" type="button">Go</button>
      <div class="ms-addrwrap"><input id="msAddr" type="text" placeholder="Address, City ST &mdash; Enter" autocomplete="off" title="Type the address WITH the city, then Enter (or pick a suggestion)"><button class="ms-clear" type="button" data-clear="msAddr" title="Clear">&times;</button><div id="msSugg" class="ms-sugg"></div></div>
    </div>
    <button id="wxBtn" title="Rain forecast for job scheduling">&#127783; Weather</button>
    <button id="expandBtn" title="Full-screen radar">&#9974; Full-screen radar</button>
    <button id="statusBtn" title="Service health (is Tempest alive)"><span class="hbdot"></span>Status</button>
    <button id="pullBtn" title="Pull on-demand storm data for a 150mi circle">&#10515; Pull</button>
    <button id="alertBtn" title="Tap to enable push alerts on this device">&#128276; Enable alerts</button>
    <div class="status" id="connStatus"></div>
  </div>
  <div id="tbar2"></div>
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
// Item 10 PULL write endpoint (separate from the read /api/storm). Token is held
// server-side in the Netlify function; this bundle carries NO credential.
const PULL_API = CFG.pullApi || API.replace(/\\/api\\/storm$/, "/api/storm-pull");
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

// STORM-DAY (mirrors engine storm.service.provisional.storm_day_of): the Central convective day runs
// D 12Z -> D+1 12Z, so a UTC hour < 12 belongs to the PRIOR calendar day (the active storm-day). This is
// the date the intraday writes its provisional under; the portal defaults here so it stops going blank
// after 00Z UTC (when the raw UTC calendar rolls ahead of the storm-day).
function stormDayUTC(){
  const n=new Date();
  const d=new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate()));
  if(n.getUTCHours() < 12) d.setUTCDate(d.getUTCDate()-1);
  return d.toISOString().slice(0,10);
}
function getDate(){ return new URLSearchParams(location.search).get("date") || stormDayUTC(); }
function goDate(d){ location.search = "?date=" + d; }
function shiftDate(d, n){ const t=new Date(d+"T00:00:00Z"); t.setUTCDate(t.getUTCDate()+n); return t.toISOString().slice(0,10); }
function fmtDate(d){ const t=new Date(d+"T00:00:00Z"); return t.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}); }
function parseJSON(s){ try{ return JSON.parse(s||"[]"); }catch(e){ return []; } }
function parseScores(s){ if(!s) return null; try{ const o=JSON.parse(s); return (o && typeof o==="object") ? o : null; }catch(e){ return null; } }
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
  // COLLAPSE FIX (item 8 Step 3): key by peril AND zone so an in-market hail row
  // and a chase hail row no longer overwrite each other. In-market ALWAYS renders
  // (renderMap, untouched); chase is a separate coexisting layer drawn by the
  // bootstrap. coverage_zone==='chase' => chase; null/'geofence' => in-market.
  const isChase = r => r.coverage_zone === "chase";
  const inmkt = {}, chaseHail = [];
  // collect ALL chase hail clusters (150mi chase-fill + any on-demand PULLs) so they
  // MERGE into one chase layer instead of overwriting each other (Item 10).
  rows.forEach(r => { if(isChase(r)){ if(r.peril==="hail") chaseHail.push(r); } else inmkt[r.peril] = r; });
  const h = inmkt.hail;
  // EVIDENCE-LEAK FIX (Step 3): the cached in-market evidence_json is only bbox-clipped
  // (engine uses full_poly.bounds, a rectangle), so points in the bbox-but-outside-
  // polygon rendered as in-market OUT in the ring. Clip in-market evidence to the
  // geofence POLYGON here (point-in-polygon vs the geo_ref outer boundary). Chase
  // evidence is NOT clipped — it is ring data, gated by the chase Evidence sub-toggle.
  const _gfRings = ((geo && geo.boundaries) || []).flatMap(g => !g ? [] :
    g.type === "Polygon" ? [g.coordinates[0]] : g.type === "MultiPolygon" ? g.coordinates.map(p => p[0]) : []);
  const _inGF = (lng, lat) => _gfRings.some(ring => { let inside = false;
    for(let i=0,j=ring.length-1;i<ring.length;j=i++){ const xi=ring[i][0],yi=ring[i][1],xj=ring[j][0],yj=ring[j][1];
      if(((yi>lat)!==(yj>lat)) && (lng < (xj-xi)*(lat-yi)/(yj-yi)+xi)) inside=!inside; } return inside; });
  const evIn = (h ? parseJSON(h.evidence_json) : []).filter(p => !_gfRings.length || _inGF(p.lng, p.lat));
  const layer = r => r ? { swath_cells: parseJSON(r.swath_json), circles: parseJSON(r.circles_json),
                           evidence: parseJSON(r.evidence_json),
                           summary: { cells: parseJSON(r.swath_json).length, circles: r.circle_count } } : null;
  // UNIFIED SWATH (Step 3 v2 Part 2): ONE seamless hail swath — geofence-interior
  // cells + 150mi ring cells concatenated — rendered by renderMap's §3 SwathLayer,
  // gated ONLY by the hail "Swath" sub-toggle. NEVER gated by chase: chase OFF still
  // shows the full 150mi swath. No chase dimming — it is just hail.
  const chaseSwath = [].concat.apply([], chaseHail.map(r => parseJSON(r.swath_json)));
  const chaseCircles = [].concat.apply([], chaseHail.map(r => parseJSON(r.circles_json)));
  const chaseEvidence = [].concat.apply([], chaseHail.map(r => parseJSON(r.evidence_json)));
  const unifiedSwath = (h ? parseJSON(h.swath_json) : []).concat(chaseSwath);
  const hasSwath = unifiedSwath.length > 0;
  const D = {
    storm_date: date,
    summary: { events: 0, swath_cells: unifiedSwath.length,
               swath_mode: hasSwath ? "per_cell" : "none", evidence_points: evIn.length,
               circles: h ? h.circle_count : 0, qualifying: 0, priority: 0, in_area: 0, buffer: 0 },
    center: [38.63, -90.2], events: [], zips: [],
    evidence_points: evIn,
    swath_cells: unifiedSwath,
    swath_mode: hasSwath ? "per_cell" : "none",
    geo_ref: geo || { boundaries: [], cities: [] },
    circles: h ? parseJSON(h.circles_json) : [],
    overlay: null,
    wind: layer(inmkt.wind),
    tornado: layer(inmkt.tornado),
    // CHASE = TARGETING ONLY (merged circles + evidence from chase-fill + pulls); the
    // chase swath is folded into the unified hail swath above (always available).
    chase: chaseHail.length ? { circles: chaseCircles, evidence: chaseEvidence } : null,
    // #6 PAYOUT TARGETING BRAIN: per-peril {idx -> {payout_score, rank, floor_pass,...}}
    // additive AdCluster prop. Graceful: absent (proxy query w/o the field) -> no ranks.
    payout: {
      hail: h ? parseScores(h.payout_scores_json) : null,
      wind: parseScores(inmkt.wind && inmkt.wind.payout_scores_json),
      tornado: parseScores(inmkt.tornado && inmkt.tornado.payout_scores_json),
    },
    list_core_count: (h && h.list_core_count != null) ? +h.list_core_count : null,
  };
  // Initial framing uses in-market targeting only — the chase toggle never moves the
  // map (Part 3), and the unified swath renders to 150mi regardless of view.
  const pts = [];
  (D.circles||[]).forEach(c => pts.push([c.center_lat, c.center_lng]));
  ["wind","tornado"].forEach(p => { if(D[p]) (D[p].circles||[]).forEach(c => pts.push([c.center_lat, c.center_lng])); });
  if(!pts.length && D.chase) (D.chase.circles||[]).forEach(c => pts.push([c.center_lat, c.center_lng]));
  if(pts.length){ const la=pts.map(p=>p[0]), lo=pts.map(p=>p[1]);
    D.center=[la.reduce((a,b)=>a+b,0)/la.length, lo.reduce((a,b)=>a+b,0)/lo.length]; }
  return D;
}

// ── operator summary panel: per-peril verdict + numbers (replaces debug pills) ──
const CELL_AREA = 0.374;
const PERIL_SWATCH = {hail:"#e8430a", wind:"#2171b5", tornado:"#d6141b"};
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
  // #6 targeting brain: ranked ad-circle count + the separate door/call list-core (>=8.5)
  if(D.payout){
    let nranked=0, nmuted=0;
    ["hail","wind","tornado"].forEach(pk=>{ const ps=D.payout[pk]; if(!ps) return;
      Object.keys(ps).forEach(k=>{ nranked++; if(!ps[k].floor_pass) nmuted++; }); });
    if(nranked) h+='<div class="op-row"><b>Ranked ad targets:</b> '+nranked+
      ' <span class="muted">('+(nranked-nmuted)+' above floor \\u00b7 '+nmuted+' muted)</span></div>';
  }
  if(D.list_core_count!=null) h+='<div class="op-row"><b>List core (\\u22658.5):</b> '+
    D.list_core_count.toLocaleString()+' parcels <span class="muted">door/call</span></div>';
  h+='<div class="op-row op-adspend"><b>Ad spend:</b> <span class="muted">pending CPC \\u00b7 targets ranked by payout_score</span></div>';
  h+='<div id="detail" class="op-row"><span class="muted">Click a target circle for lead detail.</span></div>';
  side.innerHTML=h;
}

// ── #6 RANKED-TARGETS overlay: payout_score rank badges on the ad circles.
// Reuses renderMap verbatim (§3 rings untouched); this is an additive label pane.
// Floor-excluded (muted) circles keep their ring but get a greyed badge — flagged,
// never deleted. Toggle in the top-left; ON by default. No-op if no payout data.
let RANKGRP = null, RANKON = true;
function paintRankedTargets(D){
  if(!TMAP || !D || !D.payout) return;
  const perils = [["hail", D.circles], ["wind", D.wind && D.wind.circles],
                  ["tornado", D.tornado && D.tornado.circles]];
  if(!TMAP.getPane("rankPane")){ const p=TMAP.createPane("rankPane"); p.style.zIndex=655; p.style.pointerEvents="none"; }
  const markers=[]; let scored=0, muted=0;
  perils.forEach(([pk, circles])=>{
    const ps = D.payout[pk]; if(!ps || !circles) return;
    circles.forEach((c, i)=>{
      const s = ps[String(i)]; if(!s) return;          // only in-geofence P1/P2 scored
      scored++; if(!s.floor_pass) muted++;
      const html='<div class="rankbadge t'+(c.tier||"").slice(1)+(s.floor_pass?"":" muted")+'">'
        +'<b>#'+s.rank+'</b><span class="rs">'+Math.round(s.payout_score)+'</span></div>';
      markers.push(L.marker([c.center_lat, c.center_lng], {pane:"rankPane", interactive:false,
        icon:L.divIcon({className:"rankwrap", html, iconSize:[0,0]})}));
    });
  });
  if(RANKGRP && TMAP.hasLayer(RANKGRP)) TMAP.removeLayer(RANKGRP);
  if(!markers.length) return;
  RANKGRP = L.layerGroup(markers);
  if(RANKON) RANKGRP.addTo(TMAP);
  // a tiny toggle control (top-left under zoom) so the operator can hide the badges
  if(!document.getElementById("rankToggle")){
    const RankCtl = L.Control.extend({ options:{position:"topleft"},
      onAdd:function(){ const d=L.DomUtil.create("div","leaflet-bar rankctl");
        d.innerHTML='<a id="rankToggle" href="#" title="Ranked targets (payout score)">#</a>';
        L.DomEvent.disableClickPropagation(d);
        d.querySelector("a").onclick=(e)=>{ e.preventDefault(); RANKON=!RANKON;
          if(RANKON){ RANKGRP.addTo(TMAP); d.querySelector("a").classList.add("on"); }
          else { TMAP.removeLayer(RANKGRP); d.querySelector("a").classList.remove("on"); } };
        return d; } });
    TMAP.addControl(new RankCtl());
    const a=document.getElementById("rankToggle"); if(a && RANKON) a.classList.add("on");
  }
  const cs=document.getElementById("connStatus");
  if(cs && scored) cs.textContent = scored+" ranked targets"+(muted?(" \\u00b7 "+muted+" below floor"):"");
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
  // FALLBACK (default view only): if the storm-day has NO cluster yet, land on the MOST-RECENT available
  // date so the map is never blank when recent data exists. Never overrides an explicit ?date= selection.
  if(!new URLSearchParams(location.search).get("date")){
    const sd = stormDayUTC();
    if(!AVAIL[sd]){
      const dates = Object.keys(AVAIL).sort();
      if(dates.length){ const recent = dates[dates.length-1];
        if(recent !== sd){ location.replace("?date=" + recent); return; } }   // one clean redirect, no history entry
    }
  }
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
  const today = stormDayUTC();
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
function toggleCal(){ const c=document.getElementById("cal"); closeCalPick(); c.classList.toggle("hidden"); if(!c.classList.contains("hidden")) renderCal(); }

// quick month/year picker: click the calendar title to jump months/years fast
let calPickYr=null;
function openCalPick(){ const p=document.getElementById("calPick"); if(!p) return;
  if(p.classList.contains("hidden")){ calPickYr = calView? calView.y : new Date().getUTCFullYear();
    renderCalPick(); p.classList.remove("hidden"); document.getElementById("cal").classList.add("picking"); }
  else closeCalPick(); }
function closeCalPick(){ const p=document.getElementById("calPick"); if(p) p.classList.add("hidden");
  const c=document.getElementById("cal"); if(c) c.classList.remove("picking"); }
function renderCalPick(){ const yr=document.getElementById("cpYr"); if(yr) yr.textContent=calPickYr;
  const mg=document.getElementById("cpMonths"); if(!mg) return; mg.innerHTML="";
  MONTHS.forEach((nm,i)=>{ const b=document.createElement("button"); b.className="cp-mo"; b.textContent=nm.slice(0,3);
    if(calView && calView.y===calPickYr && calView.m===i) b.classList.add("sel");
    b.onclick=()=>{ calView={y:calPickYr, m:i}; closeCalPick(); renderCal(); };
    mg.appendChild(b); }); }

// ── SPEND-DIAL PANEL (operator decision surface). Reads the brain via the proxy
//    (/api/spend-solve, /api/spend-approve); SOLVE writes nothing, APPROVE is the ONE
//    gate (shared desktop modal + mobile). No email path. Graceful if proxy absent. ──
const SPEND_API = (CFG.spendApi || "").replace(/\\/$/, "") ||
                  (API ? API.replace(/\\/api\\/storm$/, "/api/spend") : "");
let SD_STATE = { solution: null };
let SD_CIRCLES = {};          // circle_id -> {lat,lng,r} for the Solve map SNAP (built in setupSpendDial)
let SD_SNAPGRP = null;        // the funded/deselected highlight layer group (cleared each Solve)
let SD_SORT = "value";        // readout sort mode (display only): value | cheap | vpd
let SD_MANUAL_OFF = new Set(); // Part C: rings the operator manually clicked off (recompute cost/jobs)
async function sdApi(action, body){
  if(!SPEND_API) throw new Error("no spend endpoint configured (v2 proxy wiring)");
  const r = await fetch(SPEND_API + "-" + action, { method:"POST",
    headers:{ "Content-Type":"application/json" }, body: JSON.stringify(body) });
  if(!r.ok) throw new Error("HTTP " + r.status);
  return await r.json();
}
function sdReadDials(){
  // hail-size floor replaces Core/Core+/Wide; area is inert server-side (defaults to wide).
  return { date:getDate(), peril:"hail", footprint_source:"canonical",
    hail_floor:+document.getElementById("sdHail").value,
    value_floor:+document.getElementById("sdFloor").value,
    spend_cap:+document.getElementById("sdCapR").value,
    target_jobs:(+document.getElementById("sdTargetJobs").value || null) };
}
// SHARED months-since-storm helper — the SAME rule that governs the landing-page 12-month
// claim expiry (addendum §16). One helper so the spend box and the landing page can't drift.
window.tempestMonthsSince = function(dateStr){
  const d = new Date(dateStr + "T00:00:00Z"); if(isNaN(d)) return 0;
  const now = new Date();
  let m = (now.getUTCFullYear() - d.getUTCFullYear()) * 12 + (now.getUTCMonth() - d.getUTCMonth());
  if(now.getUTCDate() < d.getUTCDate()) m -= 1;
  return m;
};
function setupSpendDial(D){
  if(document.getElementById("spendPanel")) return;
  // circle_id -> coords for the Solve map SNAP (hail is the only solvable peril). circle_id is
  // CLUSTER-hail-<date>#<idx>, matching solve()'s funded_circle_ids / deselected[].circle_id.
  SD_CIRCLES = {}; const _ck = "CLUSTER-hail-" + getDate();
  ((D && D.circles) || []).forEach((c, i) => { SD_CIRCLES[_ck + "#" + i] =
    { lat: c.center_lat, lng: c.center_lng, r: c.radius_mi }; });
  const host = (document.getElementById("side") || {}).parentElement || document.getElementById("main") || document.body;
  const p = document.createElement("div"); p.id = "spendPanel";
  p.innerHTML =
    '<h2>Spend Dial <span class="pk">HAIL</span></h2>'
    + '<div class="sd-row sd-peril"><label>Peril</label><div class="sd-seg">'
    + '<button class="on" data-peril="hail">Hail</button>'
    + '<button disabled title="calibrating" data-peril="wind">Wind</button>'
    + '<button disabled title="calibrating" data-peril="tornado">Tornado</button></div></div>'
    + '<div class="sd-cap"><span>Annual room: <b id="sdCap">set in config</b></span>'
    + '<span>Target jobs: <input id="sdTargetJobs" type="number" min="0" style="width:54px"></span></div>'
    + '<div class="sd-row"><label>Hail floor</label><input id="sdHail" type="range" min="1.80" max="4.00" step="0.05" value="1.80"><span class="val" id="sdHailV">1.80\\u2033</span></div>'
    + '<div class="sd-row"><label>Value floor</label><input id="sdFloor" type="range" min="0" max="600000" step="25000" value="0"><span class="val" id="sdFloorV">$0</span></div>'
    + '<div class="sd-row"><label>Spend cap</label><input id="sdCapR" type="range" min="1000" max="100000" step="1000" value="30000"><span class="val" id="sdCapV">$30,000</span></div>'
    + '<div class="sd-actions"><button id="sdSolve">Solve</button><button id="sdSend" disabled>Send &rarr;</button></div>'
    + '<div class="sd-verdict" id="sdVerdict">Set the dials and hit Solve.</div>'
    + '<div class="sd-row" style="margin:6px 0 1px"><label>Sort</label><div class="sd-seg" id="sdSort">'
    + '<button class="on" data-sort="value">Value</button><button data-sort="cheap">Cheapest</button>'
    + '<button data-sort="vpd">Value/$</button></div></div>'
    + '<div class="sd-sortnote" style="font-size:10.5px;color:#778;margin:0 0 3px;font-style:italic">View order only \\u2014 funding stays value-ranked.</div>'
    + '<table class="sd-table" id="sdTable"><thead><tr><th>rank</th><th>ring ID</th><th>avg val</th><th>cov</th><th>cost-to-win</th><th title="modeled — target impression share, pending real auction data">IS<sup>*</sup></th></tr></thead><tbody></tbody></table>'
    + '<div class="sd-modelnote" style="font-size:10px;color:#8a6d3b;margin:3px 0 0;font-style:italic">cost-to-win = real county CPC \\u00d7 modeled CTR. <b>*IS % and $/job are modeled</b> (target-IS + funnel), pending real ad data.</div>';
  host.appendChild(p);
  // NO QUALIFIED STORM -> gray the dial: it can only fund ad targets, and there are none
  // for any peril. SAME condition as Storm Review's "No qualifying storm" verdict (no circles
  // for hail/wind/tornado), so the two never disagree. Date nav is a full reload, so this is
  // decided once per render. The floatbox drag/X and the row-2 button stay fully active.
  const sdHasStorm = !!((D && D.circles && D.circles.length) || (D && D.wind) || (D && D.tornado));
  if(!sdHasStorm){
    p.classList.add("sd-nostorm");
    const msg = document.createElement("div"); msg.className = "sd-nostormmsg";
    msg.innerHTML = "\\u26d4 No qualified storm on " + getDate() + " \\u2014 no ad targets to fund.";
    p.insertBefore(msg, p.querySelector(".sd-row.sd-peril"));
  } else if(window.tempestMonthsSince(getDate()) > 12){
    // 12-month MO claim-filing WARNING banner — warn only, NEVER blocks the solve (old dates,
    // incl. the golden 2024-05-26, stay testable). Date-driven via the shared months-since helper.
    const w = document.createElement("div"); w.className = "sd-claimwarn";
    w.innerHTML = "\\u26a0 This storm is past Missouri\\u2019s 12-month claim-filing window \\u2014 these targets aren\\u2019t claimable.";
    p.insertBefore(w, p.querySelector(".sd-row.sd-peril"));
  }
  if(CFG.remainingAnnualCapacity != null) document.getElementById("sdCap").textContent = CFG.remainingAnnualCapacity + " jobs";
  function invalidate(){ SD_STATE.solution = null; document.getElementById("sdSend").disabled = true;
    document.getElementById("sdTable").classList.add("sd-stale"); }
  const hail = document.getElementById("sdHail");
  hail.oninput = () => { document.getElementById("sdHailV").textContent = (+hail.value).toFixed(2) + "\\u2033"; invalidate(); };
  const floor = document.getElementById("sdFloor"), capr = document.getElementById("sdCapR");
  floor.oninput = () => { document.getElementById("sdFloorV").textContent = "$" + (+floor.value).toLocaleString(); invalidate(); };
  capr.oninput = () => { document.getElementById("sdCapV").textContent = "$" + (+capr.value).toLocaleString(); invalidate(); };
  document.getElementById("sdTargetJobs").oninput = invalidate;
  document.getElementById("sdSolve").onclick = sdSolve;
  document.getElementById("sdSend").onclick = sdOpenApprove;
}
async function sdSolve(){
  const sp = document.getElementById("spendPanel"); if(sp && sp.classList.contains("sd-nostorm")) return;   // grayed: nothing to fund
  const v = document.getElementById("sdVerdict"); v.textContent = "Solving\\u2026"; v.className = "sd-verdict";
  try {
    const sol = await sdApi("solve", sdReadDials());
    SD_MANUAL_OFF.clear();                              // fresh Solve = fresh selection
    SD_STATE.solution = sol; sdRenderSolution(sol);
  } catch(e){ v.textContent = "Solve unavailable (proxy offline) \\u2014 " + e.message; v.className = "sd-verdict warn"; }
}
function sdRenderSolution(sol){
  const v = document.getElementById("sdVerdict");
  v.textContent = sol.verdict; v.className = "sd-verdict " + (sol.valid ? "ok" : (sol.raise_cap ? "warn" : ""));
  // value floor inactive / coverage n/a when the date has no value rollup (never a fake 100%)
  let vn = document.getElementById("sdValNote");
  if(!sol.value_data){
    if(!vn){ vn = document.createElement("div"); vn.id = "sdValNote"; vn.className = "sd-claimwarn";
      const t = document.getElementById("sdTable"); t.parentNode.insertBefore(vn, t); }
    vn.style.display = "block";
    vn.innerHTML = "\\u2139 Value data not computed for this date \\u2014 coverage shows n/a and the value floor is inactive.";
  } else if(vn){ vn.style.display = "none"; }
  // sort control (display only — funding is fixed): wire once, then render rows in the current order
  const ss = document.getElementById("sdSort");
  if(ss && !ss.dataset.wired){ ss.dataset.wired = "1";
    ss.querySelectorAll("button").forEach(b => b.onclick = () => {
      ss.querySelectorAll("button").forEach(x => x.classList.remove("on")); b.classList.add("on");
      SD_SORT = b.dataset.sort; sdRenderRows(); }); }
  // Part C: value-floor slider max = the funded set's top avg_home_value (per-ring value is only in
  // the Solve response), re-set each Solve; clamp the current value into the new range.
  const fl = document.getElementById("sdFloor");
  if(fl){ const mx = Math.max(0, ...(sol.funded||[]).map(r => r.avg_home_value||0));
    if(mx > 0){ fl.max = Math.ceil(mx/25000)*25000;
      if(+fl.value > +fl.max){ fl.value = fl.max;
        document.getElementById("sdFloorV").textContent = "$" + (+fl.value).toLocaleString(); } } }
  sdRenderRows();
  sdRenderAdjust();                                   // Part C: manual-deselect recompute line
  document.getElementById("sdTable").classList.remove("sd-stale");
  document.getElementById("sdSend").disabled = !sol.valid;
  sdRedrawMap(sol);
}
// Part C: recompute cost/jobs over the funded set MINUS the operator's manual-off rings, using the
// SAME CTR cost basis (each ring's domination_floor is already CTR-corrected) + the same funnel.
function sdRenderAdjust(){
  const sol = SD_STATE.solution; if(!sol) return;
  let host = document.getElementById("sdAdjust");
  if(!host){ host = document.createElement("div"); host.id = "sdAdjust";
    host.style.cssText = "font-size:11px;margin:4px 0 0"; const t = document.getElementById("sdTable");
    t.parentNode.insertBefore(host, t.nextSibling); }
  const off = SD_MANUAL_OFF.size;
  if(!off){ host.style.display = "none"; return; }
  const kept = (sol.funded||[]).filter(r => !SD_MANUAL_OFF.has(r.circle_id));
  const spend = kept.reduce((s,r) => s + (r.domination_floor||0), 0);
  const homes = kept.reduce((s,r) => s + (r.damaged_homes||0), 0);
  const jobs = Math.round(Math.round(homes*0.02) * (sol.net_close||0.255));
  host.style.display = "block"; host.style.color = "#8a6d3b";
  host.innerHTML = "\\u270e adjusted (" + off + " ring" + (off>1?"s":"") + " off): <b>$"
    + Math.round(spend).toLocaleString() + "</b> \\u00b7 ~" + jobs + " jobs \\u00b7 CTR cost-to-win";
}
// readout sort is DISPLAY ONLY — it reorders the view, never the funded set (funding stays the
// value-rank deselection + cap). VALUE = funding rank; CHEAPEST = domination_floor asc; VALUE/$ =
// (roof-size x home-value) / domination_floor desc (efficiency frontier; div-by-zero guarded).
function sdSortedFunded(){
  const rows = ((SD_STATE.solution && SD_STATE.solution.funded) || []).slice();
  if(SD_SORT === "cheap"){ rows.sort((a, b) => (a.domination_floor||0) - (b.domination_floor||0)); }
  else if(SD_SORT === "vpd"){
    const vpd = r => { const sz = r.avg_squares||0, hv = r.avg_home_value||0, d = r.domination_floor||0;
      return (d > 0 && sz && hv) ? (sz*hv)/d : -1; };          // guard /0; unknown size/value sink
    rows.sort((a, b) => vpd(b) - vpd(a));
  } else { rows.sort((a, b) => (a.rank||0) - (b.rank||0)); }    // value = funding rank order
  return rows;
}
function sdRenderRows(){
  const tb = document.querySelector("#sdTable tbody"); if(!tb) return; tb.innerHTML = "";
  sdSortedFunded().forEach(r => {
    const tr = document.createElement("tr"); tr.dataset.cid = r.circle_id;
    const off = SD_MANUAL_OFF.has(r.circle_id);
    if(off){ tr.style.opacity = "0.4"; tr.style.textDecoration = "line-through"; }
    const av = r.avg_home_value ? ("$" + Math.round(r.avg_home_value/1000) + "k") : "\\u2014";
    const cov = r.coverage_known ? (Math.round((r.coverage||0)*100) + "%") : "n/a";
    tr.innerHTML = "<td>" + r.rank + "</td><td class='sd-idcell' style='cursor:help;text-decoration:underline dotted'>" + r.circle_id.split("#")[1] + "</td><td>" + av
      + "</td><td>" + cov + "</td><td>$" + Math.round(r.domination_floor).toLocaleString()
      + "</td><td><span class='sd-band " + r.band_flag + "'></span>" + Math.round((r.projected_IS||0)*100) + "%</td>";
    tr.title = "click row to toggle this ring off (recomputes cost/jobs)";
    // Part C: row click = manual deselect toggle -> recompute; the ring-ID cell = drill-down popup.
    tr.onclick = () => sdToggleOff(r.circle_id);
    const idc = tr.querySelector(".sd-idcell");
    if(idc) idc.onclick = (e) => { e.stopPropagation(); sdPopup(r.circle_id); };
    tb.appendChild(tr);
  });
}
function sdToggleOff(cid){
  if(SD_MANUAL_OFF.has(cid)) SD_MANUAL_OFF.delete(cid); else SD_MANUAL_OFF.add(cid);
  sdRenderRows(); sdRenderAdjust();
  if(SD_STATE.solution) sdRedrawMap(SD_STATE.solution);   // re-grey the deselected on the map
}
function sdRedrawMap(sol){           // v1 SNAP on Solve: highlight funded rings, grey deselected
  if(!TMAP) return;
  if(SD_SNAPGRP){ TMAP.removeLayer(SD_SNAPGRP); SD_SNAPGRP = null; }   // clear the prior snap
  if(!TMAP.getPane("sdSnap")){ const pn = TMAP.createPane("sdSnap"); pn.style.zIndex = 653; }
  const layers = [];
  // deselected first (under), funded on top — heat map + value layer stay immutable beneath
  (sol.deselected || []).forEach(d => { const c = SD_CIRCLES[d.circle_id]; if(!c) return;
    layers.push(L.circle([c.lat, c.lng], { pane:"sdSnap", radius: c.r*1609.344, color:"#6b7280",
      weight:1, opacity:.55, fillColor:"#6b7280", fillOpacity:.12 })); });
  (sol.funded_circle_ids || []).forEach(cid => { const c = SD_CIRCLES[cid]; if(!c) return;
    const off = SD_MANUAL_OFF.has(cid);                 // Part C: manually-off rings render grey
    layers.push(L.circle([c.lat, c.lng], { pane:"sdSnap", radius: c.r*1609.344,
      color: off?"#6b7280":"#16a34a", weight: off?1:3, opacity: off?.55:.95,
      fill: off, fillColor:"#6b7280", fillOpacity: off?.12:0 })); });
  if(layers.length){ SD_SNAPGRP = L.layerGroup(layers).addTo(TMAP); }
}
function sdPopup(cid){
  const sol = SD_STATE.solution; if(!sol) return;
  let r = (sol.funded || []).find(x => x.circle_id === cid), dropped = false, status = "Funded \\u00b7 rank #";
  if(!r){ const d = (sol.deselected || []).find(x => x.circle_id === cid);
    if(d){ r = d; dropped = true; status = d.reason === "below_floor" ? "Below value floor" : "Deselected \\u2014 over cap"; } }
  if(!r) return;
  let pop = document.getElementById("sdPop");
  if(!pop){ pop = document.createElement("div"); pop.id = "sdPop"; document.body.appendChild(pop); }
  pop.className = "";
  const bk = r.value_buckets || {};
  pop.innerHTML = "<h3>Ring #" + cid.split("#")[1] + "<button class='sd-pop-x'>&#10005;</button></h3>"
    + "<div class='r'><span>avg / median</span><b>" + (r.avg_home_value ? "$"+r.avg_home_value.toLocaleString() : "\\u2014")
      + " / " + (r.median_home_value ? "$"+r.median_home_value.toLocaleString() : "\\u2014") + "</b></div>"
    + "<div class='r'><span>&gt;$300k / &gt;$500k</span><b>" + (bk[">300k"]||0) + " / " + (bk[">500k"]||0) + "</b></div>"
    + "<div class='r'><span>damaged (search base) / parcels</span><b>" + (r.damaged_homes!=null?r.damaged_homes.toLocaleString():"\\u2014") + " / " + (r.parcel_count||0).toLocaleString() + "</b></div>"
    + "<div class='r'><span>squares</span><b>" + (r.avg_squares||"\\u2014") + "</b></div>"
    + "<div class='r'><span>coverage</span><b>" + (r.coverage_known ? (Math.round((r.coverage||0)*100)+"%") : "n/a") + "</b></div>"
    + "<div class='r'><span>weight raw / cov-adj</span><b>" + (r.conv_value_weight||"\\u2014") + " / " + (r.cov_adj_weight||"\\u2014") + "</b></div>"
    + "<div class='r'><span>cost-to-win / IS</span><b>$" + Math.round(r.domination_floor||0).toLocaleString()
      + " / " + (r.projected_IS!=null ? Math.round(r.projected_IS*100)+"%" : "\\u2014") + "</b></div>"
    + "<div class='sd-status " + (dropped?"dropped":"funded") + "'>" + (dropped?status:(status+(r.rank||"?"))) + "</div>"
    + ((r.coverage_known && r.coverage!=null && r.coverage<0.7) ? "<div class='sd-conf'>\\u26a0 low coverage (&lt;70%) \\u2014 value half-modeled</div>" : "");
  pop.querySelector(".sd-pop-x").onclick = () => pop.classList.add("hidden");
  pop.style.left = "50%"; pop.style.top = "22%"; pop.style.transform = "translateX(-50%)";
}
function sdOpenApprove(){
  const sol = SD_STATE.solution; if(!sol || !sol.valid) return;
  let mb = document.getElementById("sdModalBack");
  if(!mb){ mb = document.createElement("div"); mb.id = "sdModalBack";
    const m = document.createElement("div"); m.id = "sdModal"; mb.appendChild(m); document.body.appendChild(mb);
    mb.onclick = e => { if(e.target === mb) mb.classList.add("hidden"); }; }
  mb.classList.remove("hidden");
  const room = (CFG.remainingAnnualCapacity != null) ? (CFG.remainingAnnualCapacity - sol.est_jobs) : null;
  document.getElementById("sdModal").innerHTML =
    "<h2>Approve &amp; launch</h2><div class='sd-sub'>Single gate \\u00b7 " + getDate() + " \\u00b7 " + sol.area_setting + "</div>"
    + "<div class='sd-line'><span>Spend</span><b>$" + Math.round(sol.recommended_spend).toLocaleString()
      + " / $" + Math.round(sol.spend_cap).toLocaleString() + " cap</b></div>"
    + "<div class='sd-line'><span>Rings funded</span><b>" + (sol.funded||[]).length + "</b></div>"
    + "<div class='sd-line'><span>Est. jobs</span><b>~" + sol.est_jobs + " (net close " + Math.round((sol.net_close||0)*100) + "%)</b></div>"
    + "<div class='sd-line' style='color:#8a6d3b;font-style:italic;font-size:11px'><span>$/job</span><b>" + (sol.cost_per_ad_job != null ? ("$" + Math.round(sol.cost_per_ad_job).toLocaleString() + " modeled") : "modeled \\u2014 funnel pending") + "</b></div>"
    + (room != null ? "<div class='sd-line'><span>Annual room after</span><b>" + room + " jobs</b></div>" : "")
    + "<div class='sd-line'><span>Bid</span><b>" + sol.bid_strategy + "</b></div>"
    + "<div class='sd-mbtns'><button id='sdCancel'>Cancel</button><button id='sdLaunch'>Approve and launch</button></div>";
  document.getElementById("sdCancel").onclick = () => mb.classList.add("hidden");
  document.getElementById("sdLaunch").onclick = sdApprove;
}
async function sdApprove(){
  const sol = SD_STATE.solution; const btn = document.getElementById("sdLaunch");
  btn.disabled = true; btn.textContent = "Launching\\u2026";
  try {
    const res = await sdApi("approve", Object.assign(sdReadDials(), { bid_strategy: sol.bid_strategy }));
    btn.textContent = "Launched \\u2713";
    setTimeout(() => document.getElementById("sdModalBack").classList.add("hidden"), 900);
    const v = document.getElementById("sdVerdict");
    v.textContent = "Campaign live: " + (res.campaign_id||"") + " \\u00b7 $" + Math.round(res.recommended_spend||0).toLocaleString();
    v.className = "sd-verdict ok";
  } catch(e){ btn.disabled = false; btn.textContent = "Approve and launch"; alert("Approve failed: " + e.message); }
}

// ── PWA PUSH subscribe + RE-SUBSCRIBE-ON-OPEN (iOS self-heal). Push is the rich layer;
//    SMS is the backbone, so push is best-effort. Subscription POSTed every app open so a
//    stale/evicted sub is replaced server-side. ──
function _urlB64ToU8(b){ const pad="=".repeat((4-b.length%4)%4);
  const s=(b+pad).replace(/-/g,"+").replace(/_/g,"/"); const raw=atob(s);
  return Uint8Array.from(Array.prototype.map.call(raw, c=>c.charCodeAt(0))); }
async function setupPush(){   // RE-SUBSCRIBE-ON-OPEN self-heal — ONLY for an ALREADY-granted device.
  try{                        // Never prompts on load: iOS silently ignores a non-gesture permission
    if(!("serviceWorker" in navigator) || !("PushManager" in window)) return;   // request, and we don't
    const vapid = CFG.vapidPublicKey; const api = CFG.pushApi;                    // want a Chrome load prompt.
    if(!vapid || !api) return;                         // not configured yet (VAPID drops in via config)
    if(!("Notification" in window) || Notification.permission !== "granted") return;  // GESTURE-gated: enableAlerts()
    const reg = await navigator.serviceWorker.ready;
    let sub = await reg.pushManager.getSubscription();
    if(!sub){ sub = await reg.pushManager.subscribe({ userVisibleOnly:true,
      applicationServerKey:_urlB64ToU8(vapid) }); }     // permission already granted -> no prompt
    await fetch(api, { method:"POST", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ subscription: sub.toJSON(), operator:"brian" }) });   // re-POST every open (multi-device)
  }catch(e){ /* push optional — the SMS backbone + email backup still fire */ }
  finally{ updateAlertBtn(); }
}

// ── "Enable alerts" GESTURE path — iOS requires the permission request come from a user TAP. The
//    toolbar button calls this; setupPush() (on load) only re-subscribes an already-granted device. ──
async function enableAlerts(){
  try{
    if(!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)){
      alert("This browser doesn't support push notifications."); return; }
    if(Notification.permission !== "granted"){
      const perm = await Notification.requestPermission();     // MUST be inside the tap (iOS ignores otherwise)
      if(perm !== "granted"){ updateAlertBtn(); return; }
    }
    await setupPush();                                          // now granted -> subscribe + POST (+ updateAlertBtn)
  }catch(e){ updateAlertBtn(); }
}

function updateAlertBtn(){   // reflect permission state on the toolbar button
  const b = document.getElementById("alertBtn"); if(!b) return;
  const granted = ("Notification" in window) && Notification.permission === "granted";
  b.innerHTML = granted ? "&#128276; Alerts on" : "&#128276; Enable alerts";
  b.classList.toggle("alerts-on", granted);
  b.title = granted ? "Push alerts enabled on this device"
                    : "Tap to enable push alerts on this device (iOS: open from the Home-Screen app first)";
}

// ── APPROVE DEEP-LINK (?s=TOKEN). SMS/email links open a plain tab; the PWA opens standalone —
//    this renders the SAME approve modal in BOTH. Validates the storm token server-side. ──
async function handleApproveDeepLink(){
  const s = new URLSearchParams(location.search).get("s"); if(!s) return;
  const api = CFG.approveApi || (API ? API.replace(/\\/api\\/storm$/, "/api/approve") : "");
  let mb = document.getElementById("sdModalBack");
  if(!mb){ mb=document.createElement("div"); mb.id="sdModalBack"; const m=document.createElement("div"); m.id="sdModal"; mb.appendChild(m); document.body.appendChild(mb); }
  mb.classList.remove("hidden");
  const M = document.getElementById("sdModal");
  M.innerHTML = "<h2>Approve storm campaign</h2><div class='sd-sub'>Validating link\\u2026</div>";
  let info;
  try{
    const r = await fetch(api + "-validate", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ s }) });
    if(!r.ok) throw new Error("HTTP " + r.status); info = await r.json();
  }catch(e){ M.innerHTML = "<h2>Approve storm campaign</h2><div class='sd-verdict warn'>This approve link is invalid or expired \\u2014 open the portal and use the Spend Dial.</div><div class='sd-mbtns'><button id='sdCancel'>Close</button></div>"; document.getElementById("sdCancel").onclick=()=>mb.classList.add("hidden"); return; }
  if(!info || !info.valid){ M.innerHTML = "<h2>Approve storm campaign</h2><div class='sd-verdict warn'>Link invalid or expired.</div><div class='sd-mbtns'><button id='sdCancel'>Close</button></div>"; document.getElementById("sdCancel").onclick=()=>mb.classList.add("hidden"); return; }
  const d = info.default || {};
  M.innerHTML = "<h2>Approve &amp; launch</h2><div class='sd-sub'>Single gate \\u00b7 storm " + (info.storm_date||"") + " \\u00b7 CORE default</div>"
    + "<div class='sd-line'><span>Spend</span><b>$" + Math.round(d.recommended_spend||0).toLocaleString() + "</b></div>"
    + "<div class='sd-line'><span>Rings</span><b>" + (d.rings||0) + "</b></div>"
    + "<div class='sd-line'><span>Est. jobs</span><b>~" + (d.est_jobs||0) + "</b></div>"
    + "<div class='sd-sub' style='margin-top:8px'>No tap in 30 min \\u2192 this CORE-only default auto-fires (bounded). Approve now to launch immediately.</div>"
    + "<div class='sd-mbtns'><button id='sdCancel'>Not now</button><button id='sdLaunch'>Approve and launch</button></div>";
  document.getElementById("sdCancel").onclick=()=>mb.classList.add("hidden");
  document.getElementById("sdLaunch").onclick=async function(){
    const btn=this; btn.disabled=true; btn.textContent="Launching\\u2026";
    try{ const r=await fetch(api, { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify({ s }) });
      if(!r.ok) throw new Error("HTTP "+r.status); btn.textContent="Launched \\u2713"; setTimeout(()=>mb.classList.add("hidden"),900);
    }catch(e){ btn.disabled=false; btn.textContent="Approve and launch"; alert("Approve failed: "+e.message); }
  };
}

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
  [["layers","Layers",".ctlpanel"],["legend","Legend",".legend"],["details","Details","#side"],
   ["spend","$ Spend","#spendPanel"]].forEach(function(def){
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
let STATUS_CACHE={mon:null, fc:null, fill:null, dmg:null, err:null};
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
        '<div class="sp-sub">Live read of the service heartbeats \\u00b7 times UTC</div>';
  h+=_svcCard("Monitor (hail)", c.mon, false);
  h+=_svcCard("Forecast (SPC)", c.fc, true);
  h+=_svcCard("Chase-fill (150mi)", c.fill, false);
  h+=_svcCard("Chase-damage (250mi)", c.dmg, false);
  if(c.err && !c.mon && !c.fc) h+='<div class="svc-why">proxy: '+c.err+'</div>';
  p.innerHTML=h;
  const x=document.getElementById("spX"); if(x) x.onclick=closeStatus;
}
function _worstState(){ const rank={green:0,stale:1,red:2}; let w=null;
  [[STATUS_CACHE.mon,false],[STATUS_CACHE.fc,true],[STATUS_CACHE.fill,false],[STATUS_CACHE.dmg,false]].forEach(a=>{ if(a[0]){ const s=svcHealth(a[0],a[1]).state;
    if(w===null || rank[s]>rank[w]) w=s; } }); return w; }
async function refreshStatus(renderPanel){
  let mon=null, fc=null, fill=null, dmg=null, err=null;
  try{ const m=await pquery("storm_engine_status",{}); mon=(m&&m[0])||null; }catch(e){ err=e.message; }
  try{ const f=await pquery("storm_forecast_status",{}); fc=(f&&f[0])||null; }catch(e){ err=err||e.message; }
  try{ const x=await pquery("storm_fill_status",{}); fill=(x&&x[0])||null; }catch(e){ /* chase opt-in; absent until started */ }
  try{ const y=await pquery("storm_damage_status",{}); dmg=(y&&y[0])||null; }catch(e){ /* damage opt-in; absent until started */ }
  STATUS_CACHE={mon,fc,fill,dmg,err};
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
// ITEM 7 EXT — LIVE (current) awareness group. Three independent toggles + opacity
// dials: (A) animated NEXRAD reflectivity loop, (B) NWS TOR/SVR warning polygons,
// (C) storm-track cones. ALL display-only: fetched live from IEM browser-side, held
// ONLY in JS memory, discarded on refresh. NO graph, NO disk, NO engine. Panes sit
// UNDER the engine swath (z230-232 < swath z400) so scored data stays on top. While
// any layer is on, a single 5-min timer refreshes the live sources (sliding window).
function addLiveLayers(){
  if(!TMAP || document.querySelector(".livectl")) return;
  const mk=(name,z)=>{ if(!TMAP.getPane(name)){ TMAP.createPane(name);
    const p=TMAP.getPane(name); p.style.zIndex=z; p.style.pointerEvents="none"; } };
  mk("nexradPane",230); mk("warnPane",231); mk("trackPane",232);
  // smooth the blocky N0Q radar mosaic into a soft, continuous look (modern-radar feel):
  // blur softens the hard cell/colour-step edges; saturate/contrast keeps it vivid. A
  // zoom-scaled blur keeps the smoothing consistent as cells grow on zoom-in.
  const nradPane=TMAP.getPane("nexradPane");
  const smoothRadar=()=>{ if(!nradPane) return; const z=TMAP.getZoom();
    const b=Math.max(1.1, Math.min(4.2, (z-3)*0.45)).toFixed(2);   // ~1.1px out -> ~4px zoomed in
    nradPane.style.filter="blur("+b+"px) saturate(1.28) contrast(1.05)"; };
  smoothRadar(); TMAP.on("zoomend", smoothRadar);
  const R_warn=L.svg({pane:"warnPane"}), R_track=L.svg({pane:"trackPane"});

  // ===== LAYER A: NEXRAD reflectivity LOOP (national USCOMP-N0Q, 5-min frames) =====
  const N0Q=ts=>"https://mesonet.agron.iastate.edu/c/tile.py/1.0.0/ridge::USCOMP-N0Q-"+ts+"/{z}/{x}/{y}.png";
  const NFR=12, STEP=5;
  let frames=[], fIdx=0, playT=null, refreshT=null, radarOn=false, radarOp=0.7, frameOffsetMin=0;
  const pad=x=>String(x).padStart(2,"0");
  function stamps(){ const now=new Date(); now.setUTCSeconds(0,0);
    now.setUTCMinutes(now.getUTCMinutes()-(now.getUTCMinutes()%STEP)-STEP);   // back off newest for availability
    const out=[]; for(let i=NFR-1;i>=0;i--){ const d=new Date(now.getTime()-i*STEP*60000);
      out.push(""+d.getUTCFullYear()+pad(d.getUTCMonth()+1)+pad(d.getUTCDate())+pad(d.getUTCHours())+pad(d.getUTCMinutes())); }
    return out; }
  // ── frame time shown in a selectable timezone (default St. Louis / Central), 12-hour AM/PM ──
  let TZ="America/Chicago", TZLABEL="Central", tzArmed=false;
  const tzAbbr=z=>{ try{ return new Intl.DateTimeFormat("en-US",{timeZone:z,timeZoneName:"short"}).formatToParts(new Date()).find(p=>p.type==="timeZoneName").value; }catch(e){ return ""; } };
  const fmtTs=ts=>{ const d=new Date(Date.UTC(+ts.slice(0,4),+ts.slice(4,6)-1,+ts.slice(6,8),+ts.slice(8,10),+ts.slice(10,12)));
    try{ return new Intl.DateTimeFormat("en-US",{timeZone:TZ,hour:"numeric",minute:"2-digit",hour12:true,timeZoneName:"short"}).format(d); }
    catch(e){ return ts.slice(8,10)+":"+ts.slice(10,12)+"Z"; } };
  function tzFromLatLng(lat,lng){   // CONUS longitude bands -> IANA zone (DST handled by Intl)
    if(lat>=51 && lng<=-129) return ["America/Anchorage","Alaska"];
    if(lng<-150) return ["Pacific/Honolulu","Hawaii"];
    if(lng>=-87.5) return ["America/New_York","Eastern"];
    if(lng>=-101.0) return ["America/Chicago","Central"];
    if(lng>=-114.0) return ["America/Denver","Mountain"];
    return ["America/Los_Angeles","Pacific"]; }
  async function areaName(lat,lng){ try{   // reverse-geocode the clicked point (free, no key)
    const r=await fetch("https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=8&lat="+lat+"&lon="+lng,{headers:{"Accept":"application/json"}});
    const j=await r.json(), a=j.address||{};
    return [a.city||a.town||a.village||a.hamlet||a.county, a.state].filter(Boolean).join(", ")||(lat.toFixed(2)+", "+lng.toFixed(2));
  }catch(e){ return lat.toFixed(2)+", "+lng.toFixed(2); } }
  function tzToast(label,abbr,area){   // confirmation box: notes area + tz, X to close, auto-close 5s
    const ex=document.getElementById("tzToast"); if(ex) ex.remove();
    const t=document.createElement("div"); t.id="tzToast"; t.className="tz-toast";
    t.innerHTML='<div class="tz-msg">Timezone set to <b>'+label+' Time</b> <span class="tz-ab">'+abbr+'</span><div class="tz-area" id="tzArea">'+area+'</div></div><button class="tz-x" title="Close">\\u00d7</button>';
    document.body.appendChild(t);
    const close=()=>{ const e=document.getElementById("tzToast"); if(e) e.remove(); };
    t.querySelector(".tz-x").addEventListener("click",close); setTimeout(close,5000); }
  function applyTz(lat,lng){ const r=tzFromLatLng(lat,lng); TZ=r[0]; TZLABEL=r[1];
    const t=document.getElementById("lvTime"); if(t&&frames[fIdx]) t.textContent=fmtTs(frames[fIdx].ts);
    tzToast(TZLABEL,tzAbbr(TZ),"\\u2026 ("+lat.toFixed(2)+", "+lng.toFixed(2)+")");
    areaName(lat,lng).then(a=>{ const el=document.getElementById("tzArea"); if(el) el.textContent=a; }); }
  function buildFrames(){
    frames.forEach(f=>{ if(TMAP.hasLayer(f.layer)) TMAP.removeLayer(f.layer); });
    frames=stamps().map(ts=>({ts,layer:L.tileLayer(N0Q(ts),{pane:"nexradPane",opacity:0,maxZoom:19,attribution:"NEXRAD N0Q &copy; IEM/NOAA"})}));
    frames.forEach(f=>f.layer.addTo(TMAP));   // preload all; only the visible one is shown
    fIdx=frames.length-1; showFrame(); }
  function showFrame(){ frames.forEach((f,i)=>f.layer.setOpacity(i===fIdx?radarOp:0));
    const fr=document.getElementById("lvFrame"), t=document.getElementById("lvTime");
    if(fr) fr.value=fIdx; if(t) t.textContent=frames[fIdx]?fmtTs(frames[fIdx].ts):"\\u2014";
    // sync storm tracks to the displayed frame's time (newest frame = 0 min ago = live)
    frameOffsetMin=(NFR-1-fIdx)*STEP; if(trackOn) renderTracks(); }
  function play(){ stopPlay(); playT=setInterval(()=>{ fIdx=(fIdx+1)%frames.length; showFrame(); },560);
    const b=document.getElementById("lvPlay"); if(b) b.textContent="\\u23f8"; }
  function stopPlay(){ if(playT){clearInterval(playT);playT=null;} const b=document.getElementById("lvPlay"); if(b) b.textContent="\\u25b6"; }
  function radarRefresh(){ const want=stamps(); if(frames.length && want[want.length-1]===frames[frames.length-1].ts) return;
    const wasPlaying=!!playT; buildFrames(); if(wasPlaying) play(); }   // sliding 60-min window

  // ===== LAYER B: NWS warning polygons (TOR/SVR only), live =====
  const WARN="https://mesonet.agron.iastate.edu/geojson/sbw.geojson";
  let warnLayer=null, warnOn=false, warnOp=0.85;
  const warnCol=ph=>ph==="TO"?"#ff3b30":ph==="SV"?"#ffcc00":"#9aa";
  const warnStyle=f=>{ const c=warnCol(f.properties.phenomena);
    return {pane:"warnPane",color:c,weight:2.5,opacity:warnOp,fill:true,fillColor:c,fillOpacity:0.12*warnOp}; };
  async function loadWarn(){ try{
    const r=await fetch(WARN,{cache:"no-store"}); const gj=await r.json();
    gj.features=(gj.features||[]).filter(f=>{const p=f.properties;return (p.phenomena==="TO"||p.phenomena==="SV")&&p.significance==="W";});
    if(warnLayer&&TMAP.hasLayer(warnLayer)) TMAP.removeLayer(warnLayer);
    warnLayer=L.geoJSON(gj,{pane:"warnPane",renderer:R_warn,style:warnStyle,onEachFeature:(f,l)=>{const p=f.properties;
      l.bindTooltip((p.ps||p.phenomena)+" \\u00b7 "+(p.wfo||"")+" \\u00b7 until "+String(p.expire_utc||p.expire||"").slice(11,16)+"Z",{sticky:true});}});
    const cnt=document.getElementById("lvWarnN"); if(cnt) cnt.textContent=gj.features.length?(" "+gj.features.length):" none";
    if(warnOn) warnLayer.addTo(TMAP);
  }catch(e){} }

  // ===== LAYER C: storm-track cones — forward projection + on-map labels + zoom LOD =====
  const ATTR="https://mesonet.agron.iastate.edu/geojson/nexrad_attr.geojson";
  let trackLayer=null, trackOn=false, trackOp=0.9, trackData=null;
  function dest(lat,lng,brg,km){ const R=6371,b=brg*Math.PI/180,d=km/R,la=lat*Math.PI/180,lo=lng*Math.PI/180;
    const la2=Math.asin(Math.sin(la)*Math.cos(d)+Math.cos(la)*Math.sin(d)*Math.cos(b));
    const lo2=lo+Math.atan2(Math.sin(b)*Math.sin(d)*Math.cos(la),Math.cos(d)-Math.sin(la)*Math.sin(la2));
    return [la2*180/Math.PI,lo2*180/Math.PI]; }
  const compass=t=>["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"][Math.round((((t%360)+360)%360)/22.5)%16];
  // typed map icons (crisp SVG divIcons): tornado funnel / hailstone w/ size / rotation swirl / plain dot
  const icTor =()=>L.divIcon({className:"trk-ic",iconSize:[20,24],iconAnchor:[10,12],html:'<svg viewBox="0 0 20 24" width="20" height="24"><path d="M2 3 H18 L12 11 L12.5 22 L8 16 L7.5 11 Z" fill="#ff2020" stroke="#fff" stroke-width="1.2" stroke-linejoin="round"/></svg>'});
  const icMeso=()=>L.divIcon({className:"trk-ic",iconSize:[20,20],iconAnchor:[10,10],html:'<svg viewBox="0 0 20 20" width="20" height="20"><path d="M10 3 a7 7 0 1 1 -5 2" fill="none" stroke="#ff8a00" stroke-width="2.6" stroke-linecap="round"/><path d="M3 3 L6.5 5 L4 8 Z" fill="#ff8a00"/></svg>'});
  const icHail=sz=>{ const col=sz>=2?"#d11722":sz>=1?"#ff7a00":"#2f8fff";
    return L.divIcon({className:"trk-ic",iconSize:[42,18],iconAnchor:[8,9],html:'<span class="ic-hail"><svg viewBox="0 0 16 16" width="16" height="16"><circle cx="8" cy="8" r="6" fill="'+col+'" stroke="#fff" stroke-width="1.6"/><circle cx="6" cy="6" r="1.5" fill="#fff" opacity=".85"/></svg><b style="color:'+col+'">'+sz+'"</b></span>'}); };
  const icDot =()=>L.divIcon({className:"trk-ic",iconSize:[8,8],iconAnchor:[4,4],html:'<span class="ic-dot"></span>'});
  // GRADUATED DECLUTTER (like radar apps): zoom OUT shows only the worst threats, zoom IN
  // progressively reveals smaller cells. Hail-size cutoff drops as you zoom in.
  const minHail=z=>z<=4?2.0:z===5?1.5:z===6?1.25:z===7?1.0:z===8?0.75:z===9?0.5:0;
  function popupHtml(p,sz,mph,travel,tor,meso,off){
    const r=['<div class="pp-h"><b>Storm cell '+p.storm_id+'</b><span>radar '+(p.nexrad||"?")+'</span></div>'];
    r.push('<div class="pp-row"><span>Max hail size</span><b>'+(sz>0?sz+'"':"\\u2014")+'</b></div>');
    r.push('<div class="pp-row"><span>Storm motion</span><b>'+(mph?mph+" mph "+compass(travel)+" ("+Math.round(travel)+"\\u00b0)":"stationary")+'</b></div>');
    r.push('<div class="pp-row"><span>Rotation</span><b>'+(tor?"Tornado signature (TVS)":meso?"Mesocyclone":"none")+'</b></div>');
    if(+p.posh>0) r.push('<div class="pp-row"><span>Severe-hail chance</span><b>'+p.posh+'%</b></div>');
    if(+p.top>0)  r.push('<div class="pp-row"><span>Storm top</span><b>'+Math.round(p.top*3.281)+',000 ft</b></div>');
    if(off>0)     r.push('<div class="pp-row pp-ago"><span>Shown at</span><b>'+off+' min ago</b></div>');
    return r.join(""); }
  function renderTracks(){
    if(trackLayer&&TMAP.hasLayer(trackLayer)) TMAP.removeLayer(trackLayer);
    trackLayer=L.layerGroup(); if(!trackData){ return; }
    const z=TMAP.getZoom(), view=TMAP.getBounds().pad(0.3), off=frameOffsetMin;
    const minH=minHail(z), drawCones=(z>=7), PROJ=45, SPR=16; let shown=0;
    (trackData.features||[]).forEach(f=>{ const p=f.properties, c=f.geometry&&f.geometry.coordinates; if(!c) return;
      const sknt=+p.sknt||0, drct=+p.drct||0, sz=+p.max_size||0;
      const tor=(p.tvs&&p.tvs!=="NONE"), meso=(p.meso&&p.meso!=="NONE"&&p.meso!=="0");
      if(!((tor&&z>=4)||(meso&&z>=6)||(sz>=minH))) return;     // graduated LOD gate
      let lat=c[1], lng=c[0];
      if(off>0 && sknt>0){ const d2=dest(lat,lng,drct,sknt*1.852*(off/60)); lat=d2[0]; lng=d2[1]; }  // loop time-sync
      if(!view.contains([lat,lng])) return;                    // viewport cull
      const travel=(drct+180)%360, mph=Math.round(sknt*1.151);
      const icon= tor?icTor() : (sz>=0.75?icHail(sz) : (meso?icMeso():icDot()));
      const mk=L.marker([lat,lng],{pane:"trackPane",icon:icon,riseOnHover:true});
      mk.bindTooltip((tor?"Tornado":meso?"Rotation":"Hail")+(sz>0?" "+sz+'"':"")+" \\u00b7 cell "+p.storm_id+(off>0?" ("+off+"m ago)":""),{direction:"top",offset:[0,-9]});
      mk.bindPopup(popupHtml(p,sz,mph,travel,tor,meso,off),{className:"trk-pop"});
      trackLayer.addLayer(mk); shown++;
      if(drawCones && sknt>0){ const km=sknt*1.852*(PROJ/60), col=tor?"#ff2020":(sz>=1?"#ff7a00":"#2f8fff");
        [travel-SPR,travel+SPR].forEach(b=>trackLayer.addLayer(L.polyline([[lat,lng],dest(lat,lng,b,km)],
          {pane:"trackPane",renderer:R_track,interactive:false,color:col,weight:1.6,opacity:.8,dashArray:"5 4"}))); }
    });
    const pn=TMAP.getPane("trackPane"); if(pn) pn.style.opacity=trackOp;
    if(trackOn) trackLayer.addTo(TMAP);
    const cnt=document.getElementById("lvTrackN"); if(cnt) cnt.textContent=" "+shown+(off>0?" @-"+off+"m":""); }
  async function loadTrack(){ try{ const r=await fetch(ATTR,{cache:"no-store"}); trackData=await r.json(); renderTracks(); }catch(e){} }
  function trackOpacity(){ const pn=TMAP.getPane("trackPane"); if(pn) pn.style.opacity=trackOp; }

  // ===== shared 5-min refresh timer (only while a live layer is on) =====
  function tick(){ if(radarOn) radarRefresh(); if(warnOn) loadWarn(); if(trackOn) loadTrack(); }
  function ensureTimer(){ const any=radarOn||warnOn||trackOn;
    if(any&&!refreshT) refreshT=setInterval(tick,300000);
    if(!any&&refreshT){ clearInterval(refreshT); refreshT=null; } }

  // ===== control UI: grouped, all OFF by default, visually separated from scored layers =====
  const ctl=L.control({position:"bottomright"});
  ctl.onAdd=function(){ const d=L.DomUtil.create("div","livectl");
    d.innerHTML=
      '<div class="live-hd"><label class="lv-master"><input type="checkbox" id="lvMaster"> <b>\\u26a1 LIVE <span class="tag">current</span></b></label><small>live awareness \\u2014 not the scored storm</small></div>'+
      '<div class="live-row"><label><input type="checkbox" id="lvRadar"> \\u2622 NEXRAD loop <span class="muted">(60 min)</span></label>'+
        '<div class="live-sub off" id="lvRadarSub"><button id="lvPlay">\\u25b6</button><button id="lvNow" title="Stop on the current (live) frame">NOW</button><input type="range" id="lvFrame" min="0" max="'+(NFR-1)+'" value="'+(NFR-1)+'"><span class="ts" id="lvTime">\\u2014</span><button id="lvTz" title="Set timezone by clicking the map">TZ</button></div>'+
        '<div class="live-op off" id="lvRadarOp"><input type="range" id="lvRadarV" min="0" max="100" value="70"><span class="opv" id="lvRadarVv">70%</span></div></div>'+
      '<div class="live-row"><label><input type="checkbox" id="lvWarn"> \\u25a2 NWS warnings <span class="muted">TOR/SVR<span id="lvWarnN"></span></span></label>'+
        '<div class="live-op off" id="lvWarnOp"><input type="range" id="lvWarnV" min="0" max="100" value="85"><span class="opv" id="lvWarnVv">85%</span></div></div>'+
      '<div class="live-row"><label><input type="checkbox" id="lvTrack"> \\u27a4 Storm tracks <span class="muted">cone+hail<span id="lvTrackN"></span></span></label>'+
        '<div class="live-op off" id="lvTrackOp"><input type="range" id="lvTrackV" min="0" max="100" value="90"><span class="opv" id="lvTrackVv">90%</span></div></div>';
    L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d); return d; };
  ctl.addTo(TMAP);

  // wire Layer A
  const elA=document.getElementById("lvRadar");
  if(elA) elA.addEventListener("change",()=>{ radarOn=elA.checked;
    document.getElementById("lvRadarSub").classList.toggle("off",!radarOn);
    document.getElementById("lvRadarOp").classList.toggle("off",!radarOn);
    if(radarOn){ buildFrames(); play(); } else { stopPlay(); frames.forEach(f=>{ if(TMAP.hasLayer(f.layer)) TMAP.removeLayer(f.layer); }); frames=[]; frameOffsetMin=0; if(trackOn) renderTracks(); }
    ensureTimer(); });
  const pl=document.getElementById("lvPlay");
  if(pl) pl.addEventListener("click",()=>{ if(playT) stopPlay(); else play(); });
  const nw=document.getElementById("lvNow");   // snap to the current (live) frame + stop
  if(nw) nw.addEventListener("click",()=>{ stopPlay(); if(frames.length){ fIdx=frames.length-1; showFrame(); } });
  const tzb=document.getElementById("lvTz");    // arm: next map click sets the timezone
  if(tzb) tzb.addEventListener("click",()=>{ tzArmed=!tzArmed; tzb.classList.toggle("armed",tzArmed);
    document.body.classList.toggle("tz-arming",tzArmed); });
  const fr=document.getElementById("lvFrame");
  if(fr) fr.addEventListener("input",()=>{ stopPlay(); fIdx=+fr.value; showFrame(); });
  const rv=document.getElementById("lvRadarV");
  if(rv) rv.addEventListener("input",()=>{ radarOp=rv.value/100; document.getElementById("lvRadarVv").textContent=rv.value+"%"; showFrame(); });

  // wire Layer B
  const elB=document.getElementById("lvWarn");
  if(elB) elB.addEventListener("change",()=>{ warnOn=elB.checked;
    document.getElementById("lvWarnOp").classList.toggle("off",!warnOn);
    if(warnOn){ loadWarn(); } else if(warnLayer&&TMAP.hasLayer(warnLayer)) TMAP.removeLayer(warnLayer);
    ensureTimer(); });
  const wv=document.getElementById("lvWarnV");
  if(wv) wv.addEventListener("input",()=>{ warnOp=wv.value/100; document.getElementById("lvWarnVv").textContent=wv.value+"%"; if(warnLayer) warnLayer.setStyle(warnStyle); });

  // wire Layer C
  const elC=document.getElementById("lvTrack");
  if(elC) elC.addEventListener("change",()=>{ trackOn=elC.checked;
    document.getElementById("lvTrackOp").classList.toggle("off",!trackOn);
    if(trackOn){ loadTrack(); } else if(trackLayer&&TMAP.hasLayer(trackLayer)) TMAP.removeLayer(trackLayer);
    ensureTimer(); });
  const tv=document.getElementById("lvTrackV");
  if(tv) tv.addEventListener("input",()=>{ trackOp=tv.value/100; document.getElementById("lvTrackVv").textContent=tv.value+"%"; trackOpacity(); });

  // master LIVE toggle (default OFF): checking it turns ON all three sub-layers
  // (NEXRAD loop + warnings + storm tracks); unchecking turns all three OFF.
  const M=document.getElementById("lvMaster");
  if(M) M.addEventListener("change",()=>{ const card=document.querySelector(".livectl"), want=M.checked;
    ["lvRadar","lvWarn","lvTrack"].forEach(id=>{ const cb=document.getElementById(id);
      if(cb && cb.checked!==want){ cb.checked=want; cb.dispatchEvent(new Event("change")); } });
    if(card){ card.classList.toggle("lv-off", !want); } });   // checkbox = LIVE on/off only; never opens the box

  // ADD 4: zoom drives level-of-detail + viewport cull for the storm-track layer
  // (re-render from in-memory data on zoom/pan; no re-fetch). Coarse out, full in.
  TMAP.on("zoomend moveend",()=>{ if(trackOn) renderTracks(); });
  // timezone-pick: when armed (TZ button), the next map click sets the display timezone
  // from that location + shows the confirmation toast. Normal map clicks are untouched.
  TMAP.on("click",e=>{ if(tzArmed){ tzArmed=false;
    const b=document.getElementById("lvTz"); if(b) b.classList.remove("armed");
    document.body.classList.remove("tz-arming"); applyTz(e.latlng.lat,e.latlng.lng); } });

  // MOBILE: the LIVE box collapses to just its header (LIVE + checkbox); tap the header
  // to slide it up/down. Tapping the master checkbox also expands + turns the layers on.
  const card=document.querySelector(".livectl"), hd=card&&card.querySelector(".live-hd");
  if(card&&hd&&document.body.classList.contains("mobile")){
    card.classList.add("mobile-live");           // collapsed by default (CSS)
    // MOBILE tap split: the checkbox is the LIVE power switch (never opens the box); a tap
    // ANYWHERE else in the header opens/closes the box (and must NOT toggle the checkbox via
    // its label). Desktop markup is untouched, so desktop's label-toggles-LIVE still works.
    hd.addEventListener("click",e=>{
      if(e.target.id==="lvMaster") return;       // tap the checkbox -> LIVE on/off only, no box toggle
      e.preventDefault();                        // tap the LIVE text / bar -> don't toggle the checkbox-label...
      card.classList.toggle("lv-expanded"); });  // ...open / close the box instead
  }

  // LOCATE button on the map: mobile -> centre on the device location; otherwise (or if
  // denied/unavailable) -> recentre on St. Louis. Standalone Leaflet control near the zoom.
  const ST_LOUIS=[38.63,-90.23];
  const lc=L.control({position:"topleft"});
  lc.onAdd=function(){ const d=L.DomUtil.create("div","leaflet-bar locate-ctl");
    d.innerHTML='<a href="#" title="My location / re-centre on St. Louis">\\u25ce</a>';
    L.DomEvent.disableClickPropagation(d);
    d.querySelector("a").addEventListener("click",ev=>{ ev.preventDefault();
      if(navigator.geolocation){ navigator.geolocation.getCurrentPosition(
        p=>TMAP.setView([p.coords.latitude,p.coords.longitude],11),
        ()=>TMAP.setView(ST_LOUIS,9), {timeout:8000,maximumAge:60000}); }
      else TMAP.setView(ST_LOUIS,9); });
    return d; };
  lc.addTo(TMAP);
}

// ── CHASE TARGETING LAYER (item 8 Step 3 v2): chase-ZONE TARGETING only — ad-target
//    circles (P1/P2), P3 margins, evidence. The chase SWATH is NOT here; it is folded
//    into the unified hail swath (assemble) so the swath is always available, gated
//    only by the hail "Swath" sub-toggle. Presented as a peril-style block appended to
//    the BOTTOM of the §3 Layers panel; drawn via TMAP (renderMap §3 core untouched).
//    Chase OFF (default) => NOTHING here renders. Toggling NEVER moves the map. ──
const CHASE_STYLE = {
  circPaneZ: 432,                           // chase targeting sits just above in-market circles
  circleDash: "6,5",                        // DASHED (in-market is solid) = chase at a glance
  circleOpacity: 0.95, fillOpacity: 0.10,
  tierColor: { P1:"#c1121f", P2:"#f97316", P3:"#ffffff" },   // tier MEANING preserved (== in-market)
  evColor: { SPC:"#6a3d9a", LSR:"#1f78b4" },
};
let CHASE_LAYERS = null;     // { targets, p3, evidence } layer groups
function buildChaseLayers(chase){
  const map=TMAP; if(!map||!chase) return null;
  // Ad-target circles get their OWN pane so the opacity dial controls ONLY them.
  // P3 margins + evidence live in chaseCircPane and are NOT affected by the dial.
  if(!map.getPane("chaseTgtPane")){ map.createPane("chaseTgtPane"); map.getPane("chaseTgtPane").style.zIndex=CHASE_STYLE.circPaneZ+1; }
  if(!map.getPane("chaseCircPane")){ map.createPane("chaseCircPane"); map.getPane("chaseCircPane").style.zIndex=CHASE_STYLE.circPaneZ; }
  const targets=L.layerGroup(), p3=L.layerGroup(), evidence=L.layerGroup();
  (chase.circles||[]).forEach(c=>{
    const col=CHASE_STYLE.tierColor[c.tier]||"#888", r=c.radius_mi*1609.344;
    const pop="<b>CHASE "+c.tier+"</b> ring target<br>peak <b>"+c.peak_intensity+"</b> / avg <b>"+c.avg_intensity+
      "</b> intensity<br>radius "+c.radius_mi+" mi \\u00b7 max hail "+c.max_hail_size_in+'"';
    const isP3 = c.tier==="P3", dest = isP3 ? p3 : targets, pane = isP3 ? "chaseCircPane" : "chaseTgtPane";
    L.circle([c.center_lat,c.center_lng],{pane:pane,radius:r,color:col,weight:c.tier==="P1"?2.5:2,
      opacity:CHASE_STYLE.circleOpacity,dashArray:CHASE_STYLE.circleDash,fillColor:col,fillOpacity:CHASE_STYLE.fillOpacity}).bindPopup(pop).addTo(dest);
    L.circleMarker([c.center_lat,c.center_lng],{pane:pane,radius:3,color:"#fff",weight:1,
      fillColor:col,fillOpacity:0.9}).bindPopup(pop).addTo(dest);
  });
  (chase.evidence||[]).forEach(p=>{
    L.circleMarker([p.lat,p.lng],{pane:"chaseCircPane",radius:3+Math.min(p.size_in||1,3)*1.3,
      fillColor:CHASE_STYLE.evColor[p.source]||"#444",fillOpacity:.85,color:"#fff",weight:1,dashArray:CHASE_STYLE.circleDash})
      .bindTooltip((p.source||"")+" "+(p.size_in||"")+'"'+(p.city?" \\u00b7 "+p.city:"")).addTo(evidence);
  });
  return { targets, p3, evidence };
}
function setChaseOpacity(v){ const p=TMAP&&TMAP.getPane("chaseTgtPane"); if(p)p.style.opacity=v; }  // dial = AD TARGETS only (not evidence)
function addChaseLayer(chase){
  if(!TMAP || !chase || document.querySelector(".chaseband")) return;
  const circles=chase.circles||[]; if(!circles.length && !(chase.evidence||[]).length) return;
  CHASE_LAYERS = buildChaseLayers(chase);
  const tc={P1:0,P2:0,P3:0}; circles.forEach(c=>{ if(tc[c.tier]!=null)tc[c.tier]++; });
  // master OFF by default => nothing renders. Sub defaults (effective only when master
  // ON): Ad targets + Evidence ON, P3 margins OFF.
  const master={on:false}, sub={targets:true, p3:false, evidence:true};
  function apply(){
    [["targets",CHASE_LAYERS.targets],["p3",CHASE_LAYERS.p3],["evidence",CHASE_LAYERS.evidence]].forEach(a=>{
      const show=master.on && sub[a[0]];
      if(show){ if(!TMAP.hasLayer(a[1])) a[1].addTo(TMAP); } else if(TMAP.hasLayer(a[1])) TMAP.removeLayer(a[1]); });
    const blk=document.querySelector(".chaseband");
    if(blk){ blk.querySelectorAll(".sub").forEach(r=>r.style.opacity=master.on?"1":".45");
      blk.querySelectorAll(".sub input,.sub .dial").forEach(i=>i.disabled=!master.on); }
  }
  const panel=document.querySelector(".ctlpanel"); if(!panel) return;
  const blk=document.createElement("div"); blk.className="band chaseband";
  blk.innerHTML='<label class="bm"><input type="checkbox" data-cmaster> <b>CHASE FILL</b> <span class="na" style="font-style:normal;color:#888">150mi ring</span></label>'+
    '<div class="sub"><label><input type="checkbox" data-csub="targets" checked> Ad targets <span style="color:#888">P1 '+tc.P1+' \\u00b7 P2 '+tc.P2+'</span></label><input type="range" class="dial" data-cdial min="0" max="100" value="90"></div>'+
    '<div class="sub"><label><input type="checkbox" data-csub="p3"> P3 margins <span style="color:#888">'+tc.P3+'</span></label></div>'+
    '<div class="sub"><label><input type="checkbox" data-csub="evidence" checked> Evidence</label></div>'+
    '<div class="sub" style="border:none"><span style="color:#888"><span style="display:inline-block;width:13px;border-top:2px dashed #c1121f;vertical-align:middle"></span> dashed = chase (tiers as in-market)</span></div>';
  panel.appendChild(blk);
  blk.addEventListener("change",ev=>{ const t=ev.target;
    if(t.dataset.cmaster!=null){ master.on=t.checked; apply(); return; }
    if(t.dataset.csub!=null){ sub[t.dataset.csub]=t.checked; apply(); } });
  blk.addEventListener("input",ev=>{ if(ev.target.dataset.cdial!=null) setChaseOpacity(ev.target.value/100); });
  setChaseOpacity(0.90);
  apply();   // master off -> nothing renders; rows dimmed
}

// ── BOTTOM DRAWERS: relocate LIVE (.livectl) and Active perils (.legend) into two
//    tabs along the BOTTOM of the map so they don't overlay the map. Click a tab ->
//    the panel slides UP above it; click again -> slides down to just the tab.
//    Desktop only — mobile uses the slide-up sheets. Controls keep all wiring (we
//    move the DOM nodes, like the mobile lane does). ──
function setupBottomDrawers(){
  if(!TMAP || document.body.classList.contains("mobile") || document.getElementById("bottomDrawers")) return;
  const main=document.getElementById("main"); if(!main) return;
  const host=document.createElement("div"); host.id="bottomDrawers";
  L.DomEvent.disableClickPropagation(host); L.DomEvent.disableScrollPropagation(host);
  function drawer(label, node){
    const d=document.createElement("div"); d.className="bdrawer";
    const body=document.createElement("div"); body.className="bbody";
    const inner=document.createElement("div"); inner.className="bbody-inner";
    if(node) inner.appendChild(node);                    // move the control DOM in (keeps its listeners)
    body.appendChild(inner);
    const tab=document.createElement("div"); tab.className="btab"; tab.textContent=label;
    tab.addEventListener("click", ()=>d.classList.toggle("open"));
    d.appendChild(body); d.appendChild(tab);             // body (above) + tab (at the bottom)
    return d;
  }
  const live=document.querySelector(".livectl"), legend=document.querySelector(".legend");
  if(live) host.appendChild(drawer("\\u26a1 LIVE", live));
  if(legend) host.appendChild(drawer("ACTIVE PERILS", legend));
  if(host.children.length) main.appendChild(host);
}

// ── DESKTOP FLOATING PANELS: Layers / Storm Review / Spend Dial / Active perils / LIVE
//    become draggable, closeable boxes opened from the 2nd toolbar row (#tbar2). All
//    CLOSED on load; drag by the title bar, X to close, click raises to front. Desktop
//    only — mobile keeps the bottom-sheet lane (setupMobile). No persistence (resets each
//    load). Moves the panel DOM (keeps wiring), same proven pattern as the mobile sheets.
//    Weather has no box: its button opens the existing isolated slide-in tool. ──
let FB_Z=1300;
function bringFront(box){ box.style.zIndex=(++FB_Z); }
function setupFloatPanels(){
  if(!TMAP || document.body.classList.contains("mobile")) return;
  const bar=document.getElementById("tbar2"), main=document.getElementById("main");
  if(!bar || !main || bar.dataset.wired) return; bar.dataset.wired="1";
  const defs=[
    ["layers","\\u2630 Layers",".ctlpanel",{l:14,t:14,w:248}],
    ["details","\\ud83d\\udccb Storm Review","#side",{l:288,t:14,w:372}],
    ["spend","\\ud83d\\udcb0 Spend Dial","#spendPanel",{l:14,t:300,w:372}],
    ["weather","\\ud83c\\udf27 Weather",null,null],
    ["perils","\\u26a1 Active Perils",".legend",{l:408,t:300,w:240}],
    ["live","\\ud83d\\udfe2 LIVE",".livectl",{l:672,t:14,w:262}]
  ];
  function makeDraggable(box,handle){
    let drag=false,sx,sy,ox,oy;
    handle.addEventListener("mousedown",function(e){
      if(e.target.closest(".fb-x")) return;                       // X is a click, not a drag
      drag=true; const r=box.getBoundingClientRect(), pr=main.getBoundingClientRect();
      ox=r.left-pr.left; oy=r.top-pr.top; sx=e.clientX; sy=e.clientY;
      box.style.left=ox+"px"; box.style.top=oy+"px"; bringFront(box); e.preventDefault();
    });
    document.addEventListener("mousemove",function(e){ if(!drag) return;
      let nx=ox+(e.clientX-sx), ny=oy+(e.clientY-sy);
      nx=Math.max(90-box.offsetWidth, Math.min(nx, main.clientWidth-90));   // keep a grab-handle on-screen
      ny=Math.max(0, Math.min(ny, main.clientHeight-44));
      box.style.left=nx+"px"; box.style.top=ny+"px";
    });
    document.addEventListener("mouseup",function(){ drag=false; });
  }
  defs.forEach(function(def){
    const id=def[0], label=def[1], sel=def[2], pos=def[3];
    const btn=document.createElement("button"); btn.className="fb-btn"; btn.dataset.fb=id; btn.innerHTML=label;
    bar.appendChild(btn);
    if(!sel){ btn.onclick=function(){ if(window.tempestOpenWx) window.tempestOpenWx(); }; return; }   // Weather tool
    const node=document.querySelector(sel); if(!node){ btn.style.display="none"; return; }
    const box=document.createElement("div"); box.className="floatbox"; box.id="fb-"+id;
    if(pos){ box.style.left=pos.l+"px"; box.style.top=pos.t+"px"; if(pos.w) box.style.width=pos.w+"px"; }
    const ttl=document.createElement("div"); ttl.className="fb-title"; ttl.innerHTML='<span>'+label+'</span>';
    const x=document.createElement("button"); x.className="fb-x"; x.title="Close"; x.innerHTML="\\u00d7"; ttl.appendChild(x);
    const body=document.createElement("div"); body.className="fb-body"; body.appendChild(node);   // move DOM in (keeps wiring)
    box.appendChild(ttl); box.appendChild(body); main.appendChild(box);
    L.DomEvent.disableClickPropagation(box); L.DomEvent.disableScrollPropagation(box);
    box.addEventListener("mousedown",function(){ bringFront(box); });
    makeDraggable(box, ttl);
    function setOpen(on){ box.classList.toggle("open",on); btn.classList.toggle("active",on); if(on) bringFront(box); }
    x.onclick=function(){ setOpen(false); };
    btn.onclick=function(){ setOpen(!box.classList.contains("open")); };
  });
  TMAP.invalidateSize(); window.dispatchEvent(new Event("resize"));   // map reflows to full width (side panel moved out)
}

// ===================== WEATHER TAB — rain forecast for job scheduling =====================
// ISOLATED tool view. NWS api.weather.gov (public-domain, commercial-safe) for hourly +
// 7-day precip; Census geocoder via JSONP for typed addresses (no key, no CORS dependency);
// the storm map's click for coordinates. NO graph, NO engine, NO storm-scoring touch.
// Saved locations persist in localStorage (per-device).
let wxGcN=0;
function initWeather(){
  const HOME={label:"1521 N Berry Rd, Webster Groves MO 63119", lat:38.6071, lng:-90.3776};
  let curLoc=null, wxArmed=false;
  const ov=document.createElement("div"); ov.id="wxPanel"; ov.className="wx-panel hidden";
  ov.innerHTML=
    '<div class="wx-hd"><b>\\ud83c\\udf27 Weather</b><span class="wx-sub">rain timing \\u00b7 job scheduling</span><button class="wx-x" title="Close">\\u00d7</button></div>'+
    '<div class="wx-loc"><div class="wx-place">\\u2014</div>'+
      '<form class="wx-form"><input class="wx-addr" type="text" placeholder="Type an address\\u2026" autocomplete="off"><button type="submit">Go</button></form>'+
      '<div class="wx-sugg"></div>'+
      '<div class="wx-loc-btns"><button class="wx-here" type="button">\\ud83d\\udccd Use my location</button><button class="wx-pick" type="button">\\ud83d\\uddfa\\ufe0f Pick on map</button></div>'+
      '<div class="wx-gc-status"></div></div>'+
    '<div class="wx-body"></div>'+
    '<div class="wx-saved"><div class="wx-saved-h"><b>Saved locations</b><button class="wx-save-cur" type="button">+ Save current</button></div><div class="wx-saved-list"></div></div>';
  document.body.appendChild(ov);
  const bk=document.createElement("div"); bk.id="wxBackdrop"; bk.className="hidden"; document.body.appendChild(bk);

  function openWx(){ ov.classList.remove("hidden"); bk.classList.remove("hidden"); if(!curLoc) setLoc(HOME); }
  function closeWx(){ ov.classList.add("hidden"); bk.classList.add("hidden"); }
  bk.onclick=closeWx;
  const wb=document.getElementById("wxBtn"); if(wb) wb.onclick=openWx;   // mobile top-bar button
  window.tempestOpenWx=openWx;   // desktop: opened from the #tbar2 "Weather" button (setupFloatPanels)
  ov.querySelector(".wx-x").onclick=closeWx;

  const pop=p=>(p&&p.probabilityOfPrecipitation&&p.probabilityOfPrecipitation.value!=null)?p.probabilityOfPrecipitation.value:0;
  const fmtHour=iso=>{ try{ return new Intl.DateTimeFormat("en-US",{hour:"numeric",hour12:true,timeZone:"America/Chicago"}).format(new Date(iso)); }catch(e){ return String(iso).slice(11,16); } };
  const fmtHM=d=>{ try{ return new Intl.DateTimeFormat("en-US",{hour:"numeric",minute:"2-digit",hour12:true,timeZone:"America/Chicago"}).format(d); }catch(e){ return ""; } };
  // sky icon from NWS shortForecast + day/night (sun, moon, sun+cloud, rain, storm, snow, fog)
  const wxIcon=(s,day)=>{ s=(s||"").toLowerCase();
    if(/thunder|lightning|t-?storm/.test(s)) return "\\u26c8\\ufe0f";
    if(/snow|sleet|ice|flurr|wintry|blizzard/.test(s)) return "\\ud83c\\udf28\\ufe0f";
    if(/rain|shower|drizzle/.test(s)) return "\\ud83c\\udf27\\ufe0f";
    if(/fog|haze|mist|smoke/.test(s)) return "\\ud83c\\udf2b\\ufe0f";
    if(/sunny|clear|fair/.test(s)) return day?"\\u2600\\ufe0f":"\\ud83c\\udf19";
    if(/partly|mostly cloudy|few clouds|scattered|partly sunny/.test(s)) return day?"\\u26c5":"\\u2601\\ufe0f";
    if(/cloud|overcast/.test(s)) return "\\u2601\\ufe0f";
    return day?"\\u2600\\ufe0f":"\\ud83c\\udf19"; };
  // sunrise/sunset (SunCalc algorithm; no API, commercial-safe). Returns {rise,set} UTC Dates.
  function sunTimes(lat,lng,base){ const rad=Math.PI/180, dayMs=86400000, J1970=2440588, J2000=2451545, e=rad*23.4397, J0=0.0009;
    const fromJ=j=>new Date((j+0.5-J1970)*dayMs);
    const lw=rad*-lng, phi=rad*lat, d=base.valueOf()/dayMs-0.5+J1970-J2000;
    const n=Math.round(d-J0-lw/(2*Math.PI)), ds=J0+(lw)/(2*Math.PI)+n;
    const M=rad*(357.5291+0.98560028*ds);
    const L=M+rad*(1.9148*Math.sin(M)+0.02*Math.sin(2*M)+0.0003*Math.sin(3*M))+rad*102.9372+Math.PI;
    const dec=Math.asin(Math.sin(e)*Math.sin(L));
    const Jnoon=J2000+ds+0.0053*Math.sin(M)-0.0069*Math.sin(2*L);
    const cosw=(Math.sin(-0.833*rad)-Math.sin(phi)*Math.sin(dec))/(Math.cos(phi)*Math.cos(dec));
    if(cosw>1||cosw<-1) return null;
    const w0=Math.acos(cosw), Jset=J2000+(J0+(w0+lw)/(2*Math.PI)+n)+0.0053*Math.sin(M)-0.0069*Math.sin(2*L);
    return { rise: fromJ(Jnoon-(Jset-Jnoon)), set: fromJ(Jset) }; }
  const dayLabel=p=>{ if(/^(Today|Tonight|This |Overnight)/.test(p.name)) return p.name.replace(/^This /,"");
    const d=new Date(p.startTime);
    const wd=new Intl.DateTimeFormat("en-US",{weekday:"short",timeZone:"America/Chicago"}).format(d);
    const dn=new Intl.DateTimeFormat("en-US",{day:"numeric",timeZone:"America/Chicago"}).format(d);
    return wd+" "+dn+(p.isDaytime?"":" night"); };

  function geocode(addr){ return new Promise((res,rej)=>{ const cb="__wxgc"+(++wxGcN);
    window[cb]=d=>{ cleanup(); const m=d&&d.result&&d.result.addressMatches&&d.result.addressMatches[0];
      m? res({lat:m.coordinates.y, lng:m.coordinates.x, label:m.matchedAddress}) : rej("address not found"); };
    const s=document.createElement("script");
    s.src="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address="+encodeURIComponent(addr)+"&benchmark=Public_AR_Current&format=jsonp&callback="+cb;
    s.onerror=()=>{ cleanup(); rej("geocoder unreachable"); };
    function cleanup(){ try{ delete window[cb]; s.remove(); }catch(e){} }
    document.body.appendChild(s); setTimeout(()=>{ if(window[cb]){ cleanup(); rej("timeout"); } },8000); }); }

  async function loadForecast(lat,lng,label){
    const body=ov.querySelector(".wx-body"); body.innerHTML='<div class="wx-load">Loading NWS forecast\\u2026</div>';
    try{
      const pr=await (await fetch("https://api.weather.gov/points/"+(+lat).toFixed(4)+","+(+lng).toFixed(4),{headers:{Accept:"application/geo+json"}})).json();
      const pp=pr.properties; if(!pp||!pp.forecastHourly) throw new Error("no NWS coverage for this point");
      const rl=pp.relativeLocation&&pp.relativeLocation.properties;
      ov.querySelector(".wx-place").textContent = label || (rl? rl.city+", "+rl.state : (+lat).toFixed(3)+", "+(+lng).toFixed(3));
      const hr=await (await fetch(pp.forecastHourly,{headers:{Accept:"application/geo+json"}})).json();
      const dy=await (await fetch(pp.forecast,{headers:{Accept:"application/geo+json"}})).json();
      renderForecast(body, hr.properties.periods, dy.properties.periods, +lat, +lng);
    }catch(e){ body.innerHTML='<div class="wx-err">Couldn\\'t load the forecast here.<br>'+((e&&e.message)||e)+'</div>'; }
  }

  function renderForecast(body, hourly, daily, lat, lng){
    const near=Math.max(0, ...hourly.slice(0,2).map(pop));
    const nextRain=hourly.find(h=>pop(h)>=30);
    const cls= near>=50?"wet":near>=20?"risk":"dry";
    const head= near>=50?"Rain likely soon \\u2014 "+near+"% next 2 hr" : near>=20?"Some rain risk \\u2014 "+near+"% next 2 hr" : "Dry the next 2 hours";
    const sub = nextRain? "Next \\u226530% rain chance at "+fmtHour(nextRain.startTime)+" ("+pop(nextRain)+"%)" : "No \\u226530% rain chance in the hourly window";
    let h='<div class="wx-now wx-'+cls+'"><div class="wx-now-h">'+head+'</div><div class="wx-now-s">'+sub+'</div>'+
          '<div class="wx-now-note">Minute-by-minute nowcast: pending \\u2014 no free commercial source (NWS resolution is hourly)</div></div>';
    // today's sunrise/sunset for this location
    const sun = sunTimes(lat,lng,new Date());
    if(sun) h+='<div class="wx-sunline"><span>\\ud83c\\udf05 Sunrise '+fmtHM(sun.rise)+'</span><span>\\ud83c\\udf07 Sunset '+fmtHM(sun.set)+'</span></div>';
    h+='<div class="wx-sec-t">Hourly (Central)</div><div class="wx-hours">';
    hourly.slice(0,24).forEach(p=>{ const v=pop(p);
      // sky icon (sunrise/sunset glyph overrides on the hour the sun crosses)
      let ic=wxIcon(p.shortForecast,p.isDaytime), sb="";
      const st=new Date(p.startTime), en=new Date(st.getTime()+3600000), s2=sunTimes(lat,lng,st);
      if(s2){ if(s2.rise>=st&&s2.rise<en){ ic="\\ud83c\\udf05"; sb="sunrise"; } else if(s2.set>=st&&s2.set<en){ ic="\\ud83c\\udf07"; sb="sunset"; } }
      h+='<div class="wx-h'+(sb?" wx-"+sb:"")+'"><span class="wx-ht">'+fmtHour(p.startTime)+'</span><span class="wx-ic">'+ic+'</span><div class="wx-bar"><i style="height:'+Math.max(3,v)+'%"></i></div><span class="wx-hv">'+v+'%</span><span class="wx-htemp">'+p.temperature+'\\u00b0</span></div>'; });
    h+='</div>';
    h+='<div class="wx-sec-t">7-day outlook <span class="wx-note">(NWS max)</span></div><div class="wx-days">';
    daily.slice(0,14).forEach(p=>{ const v=pop(p); h+='<div class="wx-d'+(p.isDaytime?"":" night")+'"><span class="wx-dn">'+dayLabel(p)+'</span><span class="wx-di">'+wxIcon(p.shortForecast,p.isDaytime)+'</span><span class="wx-dv '+(v>=50?"hi":v>=20?"mid":"")+'">'+v+'%</span><span class="wx-ds">'+p.shortForecast+'</span><span class="wx-dt">'+p.temperature+'\\u00b0</span></div>'; });
    h+='</div>';
    body.innerHTML=h;
  }

  async function setLoc(loc){ curLoc=loc; const a=ov.querySelector(".wx-addr"); if(a) a.value=""; await loadForecast(loc.lat,loc.lng,loc.label); renderSaved(); }

  // saved locations (localStorage; server-side via the proxy is the cross-device upgrade)
  const SK="kcc_wx_saved_v1";
  const getSaved=()=>{ try{ return JSON.parse(localStorage.getItem(SK)||"[]"); }catch(e){ return []; } };
  const putSaved=a=>{ try{ localStorage.setItem(SK, JSON.stringify(a)); }catch(e){} };
  function renderSaved(){ const el=ov.querySelector(".wx-saved-list"), arr=getSaved(); el.innerHTML="";
    if(!arr.length){ el.innerHTML='<div class="wx-empty">No saved locations yet \\u2014 use \\u201c+ Save current\\u201d to add this spot.</div>'; return; }
    arr.forEach((s,i)=>{ const row=document.createElement("div"); row.className="wx-srow";
      const go=document.createElement("button"); go.className="wx-go"; go.textContent=s.label; go.onclick=()=>setLoc(s);
      const del=document.createElement("button"); del.className="wx-del"; del.title="Delete"; del.innerHTML="\\u00d7";
      del.onclick=()=>{ const a=getSaved(); a.splice(i,1); putSaved(a); renderSaved(); };
      row.appendChild(go); row.appendChild(del); el.appendChild(row); }); }
  ov.querySelector(".wx-save-cur").onclick=()=>{ if(!curLoc) return; const a=getSaved();
    if(!a.some(x=>Math.abs(x.lat-curLoc.lat)<1e-4 && Math.abs(x.lng-curLoc.lng)<1e-4)){ a.push({label:curLoc.label, lat:curLoc.lat, lng:curLoc.lng}); putSaved(a); renderSaved(); } };

  ov.querySelector(".wx-form").onsubmit=async e=>{ e.preventDefault(); const v=ov.querySelector(".wx-addr").value.trim(); if(!v) return;
    ov.querySelector(".wx-sugg").innerHTML="";
    const st=ov.querySelector(".wx-gc-status"); st.textContent="Looking up address\\u2026";
    try{ const loc=await geocode(v); st.textContent=""; setLoc(loc); }catch(err){ st.textContent="\\u26a0 "+err; } };

  // address autocomplete (suggestions as you type) via Photon (free OSM autocomplete, CORS-ok)
  let acT=null; const addrEl=ov.querySelector(".wx-addr"), suggEl=ov.querySelector(".wx-sugg");
  addrEl.addEventListener("input",()=>{ const q=addrEl.value.trim(); clearTimeout(acT);
    if(q.length<3){ suggEl.innerHTML=""; return; }
    acT=setTimeout(async()=>{ try{
      const r=await fetch("https://photon.komoot.io/api/?limit=6&lang=en&q="+encodeURIComponent(q));
      const j=await r.json(); suggEl.innerHTML="";
      (j.features||[]).forEach(f=>{ const p=f.properties, c=f.geometry&&f.geometry.coordinates; if(!c) return;
        const lbl=[p.name,(p.city||p.county||p.town),p.state,p.postcode].filter(Boolean).join(", ");
        const b=document.createElement("button"); b.type="button"; b.className="wx-sg"; b.textContent=lbl;
        b.onclick=()=>{ suggEl.innerHTML=""; addrEl.value=""; setLoc({label:lbl, lat:c[1], lng:c[0]}); };
        suggEl.appendChild(b); });
    }catch(e){ suggEl.innerHTML=""; } }, 350); });
  document.addEventListener("click",e=>{ if(!ov.querySelector(".wx-loc").contains(e.target)) suggEl.innerHTML=""; });

  // "Use my location" (browser Geolocation -> reverse-geocode the label, then NWS)
  ov.querySelector(".wx-here").onclick=()=>{ const st=ov.querySelector(".wx-gc-status");
    if(!navigator.geolocation){ st.textContent="Geolocation not available on this device"; return; }
    st.textContent="Locating\\u2026";
    navigator.geolocation.getCurrentPosition(async p=>{ st.textContent="";
      const lat=p.coords.latitude, lng=p.coords.longitude; let label="My location";
      try{ const r=await fetch("https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=12&lat="+lat+"&lon="+lng,{headers:{Accept:"application/json"}});
        const j=await r.json(), a=j.address||{}; const nm=[a.city||a.town||a.village||a.county, a.state].filter(Boolean).join(", "); if(nm) label=nm; }catch(e){}
      setLoc({label:label, lat:lat, lng:lng});
    }, err=>{ st.textContent="\\u26a0 Couldn\\'t get your location"; }, {timeout:9000,maximumAge:60000}); };

  ov.querySelector(".wx-pick").onclick=()=>{ wxArmed=true; document.body.classList.add("wx-arming"); closeWx(); };
  if(TMAP) TMAP.on("click",e=>{ if(wxArmed){ wxArmed=false; document.body.classList.remove("wx-arming"); openWx();
    setLoc({label:"Map point "+e.latlng.lat.toFixed(3)+", "+e.latlng.lng.toFixed(3), lat:e.latlng.lat, lng:e.latlng.lng}); } });

  renderSaved();
}

// ── MAP LOCATION SEARCH (navigation only): two controls on the main map —
//    (1) City/State -> forward geocode -> setView; (2) Address with PREDICTIVE
//    AUTOCOMPLETE -> exact point. REUSES the weather tab's Photon (OSM) geocoder/
//    autocomplete (free, no key, CORS-ok, already reachable from the deployed
//    portal) — no new dependency, no proxy. Read-only: only moves the map view +
//    a temporary marker. renderMap's §3 core is untouched. ──
const _PHOTON = "https://photon.komoot.io/api/";
// label INCLUDES the house number (housenumber + street) so the address reads in full.
function _photonLabel(p){
  const street = [p.housenumber, p.street || p.name].filter(Boolean).join(" ");
  return [street || p.name, (p.city||p.town||p.county), p.state, p.postcode].filter(Boolean).join(", ");
}
async function photonSuggest(q, limit){
  // Bias to the STL home point so LOCAL addresses surface first — you don't have to
  // type the city for "411 south clinton" to find New Athens, IL.
  const r = await fetch(_PHOTON+"?limit="+(limit||6)+"&lang=en&lat=38.63&lon=-90.2&q="+encodeURIComponent(q));
  const j = await r.json();
  return (j.features||[]).map(f=>{ const c=f.geometry&&f.geometry.coordinates, p=f.properties||{}; if(!c) return null;
    return { label:_photonLabel(p), lat:c[1], lng:c[0], city:(p.city||p.town||p.county||""), state:(p.state||""), postcode:(p.postcode||""), housenumber:p.housenumber||"" }; }).filter(Boolean);
}
// OSM rooftop geocoder (Nominatim) — true building point when OSM has the house. Used
// on SELECT to refine to the exact building; falls back to Census interpolation.
async function nominatimGeocode(addr){ try{
  const r=await fetch("https://nominatim.openstreetmap.org/search?format=jsonv2&addressdetails=1&limit=1&q="+encodeURIComponent(addr),{headers:{Accept:"application/json"}});
  const j=await r.json(); const f=j&&j[0]; if(!f) return null; const a=f.address||{};
  const label=[[a.house_number,a.road].filter(Boolean).join(" "), (a.city||a.town||a.village||a.hamlet), a.state, a.postcode].filter(Boolean).join(", ");
  return { lat:+f.lat, lng:+f.lon, label: label||f.display_name, hasHouse: !!a.house_number };
}catch(e){ return null; } }
// US Census rooftop geocoder (JSONP, no key) — the SAME one the weather tab uses. Gives
// the EXACT building point + matched address (with house number) when the typed address
// has a street number; Photon typeahead alone often returns only the street.
let _gcN = 0;
function censusGeocode(addr){ return new Promise(res=>{ const cb="__msgc"+(++_gcN);
  window[cb]=d=>{ cleanup(); const m=d&&d.result&&d.result.addressMatches&&d.result.addressMatches[0];
    res(m ? {lat:m.coordinates.y, lng:m.coordinates.x, label:m.matchedAddress} : null); };
  const s=document.createElement("script");
  s.src="https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address="+encodeURIComponent(addr)+"&benchmark=Public_AR_Current&format=jsonp&callback="+cb;
  s.onerror=()=>{ cleanup(); res(null); };
  function cleanup(){ try{ delete window[cb]; s.remove(); }catch(e){} }
  document.body.appendChild(s); setTimeout(()=>{ if(window[cb]){ cleanup(); res(null); } }, 7000); }); }
let SEARCH_MARKER = null;
function flyToSearch(loc, zoom){
  if(!TMAP) return;
  TMAP.setView([loc.lat, loc.lng], zoom);
  if(SEARCH_MARKER) TMAP.removeLayer(SEARCH_MARKER);
  SEARCH_MARKER = L.marker([loc.lat, loc.lng]).addTo(TMAP)
    .bindPopup(loc.label||"searched location", {autoPan:false}).openPopup();   // keep the building centered
}
function addMapSearch(){
  // Wires the TOP-BANNER search inputs (#msCity / #msAddr). Navigation only — moves
  // the map view via the captured handle; renderMap's §3 core is untouched.
  const cityEl=document.getElementById("msCity"), goEl=document.getElementById("msCityGo"),
        addrEl=document.getElementById("msAddr"), suggEl=document.getElementById("msSugg");
  if(!cityEl || !addrEl || cityEl.dataset.wired) return;
  cityEl.dataset.wired="1";
  // clear (x) buttons on both boxes — also removes the map pin
  document.querySelectorAll("#tbar .hdr-search .ms-clear").forEach(btn=>btn.addEventListener("click",()=>{
    const t=document.getElementById(btn.dataset.clear); if(t){ t.value=""; t.focus(); }
    if(btn.dataset.clear==="msAddr") suggEl.innerHTML="";
    if(SEARCH_MARKER && TMAP){ TMAP.removeLayer(SEARCH_MARKER); SEARCH_MARKER=null; } }));
  // (1) CITY/STATE: forward geocode the first match, pan/zoom to it
  async function cityGo(){ const q=cityEl.value.trim(); if(!q) return;
    try{ const hits=await photonSuggest(q,1);
      if(hits.length){ flyToSearch(hits[0], 11); } else { cityEl.value=""; cityEl.placeholder="not found \\u2014 try again"; } }
    catch(e){ cityEl.placeholder="search unreachable"; } }
  goEl.addEventListener("click", cityGo);
  cityEl.addEventListener("keydown", e=>{ if(e.key==="Enter"){ e.preventDefault(); cityGo(); } });
  // (2) ADDRESS: resolve a COMPLETE address to the EXACT building. The authoritative
  //     path is the full typed text (incl. the city) -> OSM rooftop (Nominatim) then
  //     Census interpolation. Photon typeahead is a convenience hint only; it can't
  //     disambiguate a bare street (e.g. "411 south clinton" -> needs the city).
  async function resolveAddress(text){
    let loc=null;
    if(/^\\s*\\d/.test(text)){
      const nom=await nominatimGeocode(text);
      if(nom && nom.hasHouse){ loc=nom; }                      // OSM rooftop (most accurate)
      else { const cen=await censusGeocode(text); loc=cen || nom; }   // Census, else OSM street
    }
    if(!loc){ try{ const hits=await photonSuggest(text,1); if(hits.length) loc=hits[0]; }catch(e){} }
    return loc;
  }
  async function addrGo(query){ const v=(query||addrEl.value).trim(); if(!v) return; suggEl.innerHTML="";
    const old=addrEl.placeholder; addrEl.placeholder="Looking up\\u2026";
    const loc=await resolveAddress(v); addrEl.placeholder=old;
    if(loc){ addrEl.value=loc.label||v; flyToSearch(loc, 17); } else { addrEl.placeholder="address not found \\u2014 add the city"; } }
  addrEl.addEventListener("keydown", e=>{ if(e.key==="Enter"){ e.preventDefault(); addrGo(); } });
  let acT=null;
  addrEl.addEventListener("input", ()=>{ const q=addrEl.value.trim(); clearTimeout(acT);
    if(q.length<3){ suggEl.innerHTML=""; return; }
    acT=setTimeout(async()=>{ try{ const hits=await photonSuggest(q,6); suggEl.innerHTML="";
      hits.forEach(h=>{ const b=document.createElement("button"); b.type="button"; b.className="ms-sg"; b.textContent=h.label;
        b.onclick=()=>{ const typed=addrEl.value.trim();
          // resolve a COMPLETE address: the typed text if it already has a city, else the
          // typed house+street plus the picked suggestion's city/state/ZIP.
          const query = (typed.indexOf(",")>=0) ? typed
            : typed+(h.city?", "+h.city:"")+(h.state?", "+h.state:"")+(h.postcode?" "+h.postcode:"");
          addrGo(query); };
        suggEl.appendChild(b); });
    }catch(e){ suggEl.innerHTML=""; } }, 350); });
  document.addEventListener("click", e=>{ const w=addrEl.closest(".ms-addrwrap");
    if(w && !w.contains(e.target)) suggEl.innerHTML=""; });
}

// ── PULL (item 10): the FIRST portal WRITE. Click PULL -> a FIXED 150mi circle draws
//    at the map center and follows pan (radius not resizable — it's the guardrail).
//    Aim it, CONFIRM -> POST {center, radius=150, date} to the SECURED write endpoint
//    (token server-side). On success, reload so the new chase data renders. NEVER moves
//    the map on its own; renderMap's §3 core is untouched. ──
function addPull(){
  const btn=document.getElementById("pullBtn"); if(!btn || !TMAP || btn.dataset.wired) return;
  btn.dataset.wired="1";
  let circle=null, panel=null, recenter=null, crosshair=null;
  function exitPull(){ document.body.classList.remove("pull-armed");
    if(recenter){ TMAP.off("move", recenter); recenter=null; }
    if(circle){ TMAP.removeLayer(circle); circle=null; }
    if(crosshair){ crosshair.remove(); crosshair=null; }
    if(panel){ panel.remove(); panel=null; } }
  btn.addEventListener("click", ()=>{
    if(circle){ exitPull(); return; }                          // toggle off
    document.body.classList.add("pull-armed");
    const R=150*1609.344;
    circle=L.circle(TMAP.getCenter(), {radius:R, color:"#2f6fe0", weight:3, opacity:0.95, dashArray:"9,6",
      fillColor:"#2f6fe0", fillOpacity:0.08, interactive:false}).addTo(TMAP);
    // The 150mi circle (300mi across) is bigger than the default view, so its outline
    // sits off-screen. Reveal it with a FIXED zoom (keeps center) instead of fitBounds:
    // fitBounds needs a correct map pixel size, which can read 0 mid-render. At CONUS
    // latitudes zoom 6 renders the full circle ~250px wide -> visible on phone + desktop.
    if(TMAP.getZoom()>6){ try{ TMAP.setView(TMAP.getCenter(), 6, {animate:false}); }catch(e){} }
    recenter=()=>circle.setLatLng(TMAP.getCenter());          // follows pan; radius FIXED
    TMAP.on("move", recenter);
    // center crosshair at the map center = the circle's center = the aim point
    const mapEl=document.getElementById("map");
    crosshair=document.createElement("div"); crosshair.id="pullCrosshair";
    crosshair.innerHTML='<span class="ch-h"></span><span class="ch-v"></span><span class="ch-dot"></span>';
    if(mapEl) mapEl.appendChild(crosshair);
    panel=document.createElement("div"); panel.id="pullPanel";
    panel.innerHTML='<span class="pp-txt">Pan to aim the 150mi circle over a storm</span>'+
      '<button class="pp-go" type="button">Confirm pull</button>'+
      '<button class="pp-x" type="button">Cancel</button><span class="pp-status"></span>';
    document.body.appendChild(panel);
    panel.querySelector(".pp-x").onclick=exitPull;
    panel.querySelector(".pp-go").onclick=async()=>{
      const c=TMAP.getCenter(), st=panel.querySelector(".pp-status"), go=panel.querySelector(".pp-go");
      go.disabled=true; st.textContent="Starting\\u2026";
      // FIRE: the compute is too slow for a synchronous request through the hosting
      // chain, so /api/storm-pull returns a job_id immediately and computes in the
      // background. We then POLL the read-only status until it lands, and refresh.
      let job=null;
      try{
        const r=await fetch(PULL_API, { method:"POST", headers:{ "Content-Type":"application/json" },
          body: JSON.stringify({ lat:+c.lat.toFixed(4), lon:+c.lng.toFixed(4), date:getDate(), radius_mi:150 }) });
        let j={}; try{ j=await r.json(); }catch(e){}
        if(!r.ok || j.status==="error" || !j.job_id){
          st.textContent="\\u26a0 "+(j.detail || j.error || ("HTTP "+r.status)); go.disabled=false; return; }
        job=j.job_id;
      }catch(e){ st.textContent="\\u26a0 "+e.message; go.disabled=false; return; }
      // POLL: storm_pull_status is a read-only whitelist query; polling never starts
      // a compute. Absent or 'running' -> keep waiting; terminal -> act.
      st.textContent="Computing in the background\\u2026 you can keep working; this refreshes when ready";
      const t0=Date.now(), CAP=240000;
      const poll=async()=>{
        if(Date.now()-t0>CAP){ st.textContent="\\u26a0 still computing \\u2014 reload in a moment to see it"; go.disabled=false; return; }
        let s=null; try{ const rows=await pquery("storm_pull_status",{job_id:job}); s=(rows&&rows[0])||null; }catch(e){}
        if(s && s.state==="done"){
          st.textContent="\\u2713 pulled "+s.circles+" circles \\u00b7 "+s.swath_cells+" swath cells \\u2014 refreshing\\u2026";
          if(recenter){ TMAP.off("move", recenter); recenter=null; }
          setTimeout(()=>location.reload(), 1100); return; }
        if(s && s.state==="empty"){
          st.textContent="\\u2713 no storm cells in this circle on "+getDate()+" \\u2014 nothing to pull"; go.disabled=false; return; }
        if(s && s.state==="error"){
          st.textContent="\\u26a0 "+(s.error||"pull failed"); go.disabled=false; return; }
        setTimeout(poll, 4000);
      };
      setTimeout(poll, 3000);
    };
  });
}

// ── CONTOUR PROTOTYPE (Option A): render the hail swath as smooth filled isobands
//    (marching squares via d3-contour) from the SAME swath cells, instead of the blocky
//    canvas. Display-only; the §3 SwathLayer/data/circles are untouched. A toggle flips
//    Cells (blurred canvas) <-> Contours so the look can be reviewed side by side. ──
// §3 INTENSITY ramp (amber -> orange -> red -> deep red -> magenta), interpolated to a
// continuous scale so the contour bands transition smoothly across ~10 levels. "Assumed
// math": the cell grid is smoothed/interpolated (not exact per-cell), and each level is
// drawn semi-transparent + stacked low->high, so the result is a smooth colour+opacity
// gradient -- weak/low-intensity edges fade out, strong cores stay solid.
// Continuous intensity ramp: DARK (low/less) -> BRIGHT (heavy), per the feedback (a light
// colour + transparency washes out; a dark colour holds up and reads more 3D). Dark purple
// -> purple -> magenta -> red -> orange -> bright yellow (the 1-10 legend direction).
// DARK (low) -> BRIGHT (high) ramps, one per peril family (§3 keeps hail/wind/tornado
// visually distinct): same dark->bright inversion the operator liked, different hue.
const HAIL_RAMP=[[38,9,66],[92,20,140],[173,23,158],[227,55,30],[255,150,0],[255,231,64]];   // purple -> yellow
const WIND_RAMP=[[6,20,66],[8,48,107],[33,113,181],[107,174,214],[173,216,255],[224,247,255]]; // navy -> pale cyan
const TORN_RAMP=[[61,0,0],[138,10,10],[204,20,23],[255,59,48],[255,138,128],[255,210,205]]; // dark crimson -> light red
function rampRGB(ramp,t){ t=Math.max(0,Math.min(1,t)); const x=t*(ramp.length-1), i=Math.floor(x), f=x-i;
  const a=ramp[i], b=ramp[Math.min(ramp.length-1,i+1)];
  return [Math.round(a[0]+(b[0]-a[0])*f),Math.round(a[1]+(b[1]-a[1])*f),Math.round(a[2]+(b[2]-a[2])*f)]; }
// CONTINUOUS heatmap for ANY peril swath (fades between every level -> effectively infinite
// levels): build the value grid (vIdx = which cell field), smooth it, paint with the ramp +
// a value-scaled alpha (low fainter but still dark, high solid), and scale the image smoothly
// over its bbox. Display-only; the §3 cell data + ad-circles are untouched.
function buildHeatmap(cells, valFn, ramp, paneName, paneZ){
  if(!TMAP || !cells || !cells.length) return null;
  const lats=cells.map(c=>c[0]), lons=cells.map(c=>c[1]);
  const latMin=Math.min.apply(null,lats), latMax=Math.max.apply(null,lats);
  const lonMin=Math.min.apply(null,lons), lonMax=Math.max.apply(null,lons);
  const sp=arr=>{ const u=Array.from(new Set(arr)).sort((a,b)=>a-b); let m=Infinity;
    for(let i=1;i<u.length;i++){ const d=u[i]-u[i-1]; if(d>1e-6 && d<m) m=d; } return isFinite(m)?m:0.01; };
  const dLat=sp(lats), dLon=sp(lons);
  const nLat=Math.round((latMax-latMin)/dLat)+1, nLon=Math.round((lonMax-lonMin)/dLon)+1;
  if(nLat<2 || nLon<2) return null;
  // SUPERSAMPLE coarse/thin swaths up to a smoother base resolution (a 26-row tornado or
  // 48-row wind swath upscales to hard squares otherwise). Then PAD with a transparent
  // zero-margin so the blur fades the swath to nothing before the canvas edge -> no more
  // rectangular bounding-box boundary. Wider, multi-pass separable box blur merges sparse
  // native cells into continuous blobs. DISPLAY ONLY; the cell data is untouched.
  const minDim=Math.min(nLat,nLon);
  let SS=Math.max(1, Math.min(4, Math.ceil(64/Math.max(1,minDim))));
  while(SS>1 && (nLat*SS)*(nLon*SS) > 520000) SS--;
  const PAD=Math.max(3, 2*SS+2), R=Math.max(1,SS), passes=(SS>=3?5:SS===2?4:3);
  const W=nLon*SS+2*PAD, H=nLat*SS+2*PAD;
  if(W*H>950000) return null;
  const V=new Float32Array(W*H);
  cells.forEach(c=>{ const r=Math.round((c[0]-latMin)/dLat)*SS+PAD, q=Math.round((c[1]-lonMin)/dLon)*SS+PAD;
    if(r>=0&&r<H&&q>=0&&q<W){ const i=r*W+q; const val=+valFn(c)||0; if(val>V[i]) V[i]=val; } });
  const blurAxis=(src,horiz)=>{ const out=new Float32Array(src.length);
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){ let s=0,n=0;
      for(let k=-R;k<=R;k++){ const xx=horiz?x+k:x, yy=horiz?y:y+k;
        if(xx>=0&&xx<W&&yy>=0&&yy<H){ s+=src[yy*W+xx]; n++; } }
      out[y*W+x]=s/n; } return out; };
  let G=V; for(let p=0;p<passes;p++){ G=blurAxis(G,true); G=blurAxis(G,false); }
  // Auto-fit the color range to the BLURRED grid's OWN values (per peril/storm), so the ramp
  // is fully used no matter where values floor (intensity ~2, wind ~1.2, tornado ~3.1), how
  // strong the storm is, or how much the blur diluted a sparse swath. gate (transparency)
  // = 4% of peak, excluding the faint blurred fringe; vlo/vhi = p5/p90 of the in-swath values.
  let gmax=0; for(let i=0;i<G.length;i++) if(G[i]>gmax) gmax=G[i];
  if(gmax<=0) return null;
  const gate=gmax*0.04, vals=[];
  for(let i=0;i<G.length;i++) if(G[i]>gate) vals.push(G[i]);
  if(!vals.length) return null;
  vals.sort((a,b)=>a-b);
  const vlo=vals[Math.floor(0.05*vals.length)], vhi=Math.max(vlo+1e-6, vals[Math.floor(0.90*vals.length)]);
  const span=vhi-vlo, fLoEnd=gate+0.15*span, aFloor=0.42, aTop=0.92;
  const cv=document.createElement("canvas"); cv.width=W; cv.height=H;
  const ctx=cv.getContext("2d"), img=ctx.createImageData(W,H);
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){ const v=G[y*W+x];
    const row=H-1-y, idx=(row*W+x)*4;                                  // flip so canvas top = north
    if(v<gate){ img.data[idx+3]=0; continue; }                        // outside swath -> transparent
    const t=Math.max(0,Math.min(1,(v-vlo)/span)), rgb=rampRGB(ramp,t);
    img.data[idx]=rgb[0]; img.data[idx+1]=rgb[1]; img.data[idx+2]=rgb[2];
    let a=aFloor+(aTop-aFloor)*t;                                      // brighter/more opaque with value
    if(v<fLoEnd) a*=(v-gate)/(fLoEnd-gate);                           // feather the fringe to transparent
    img.data[idx+3]=Math.round(255*Math.max(0,Math.min(aTop,a))); }
  ctx.putImageData(img,0,0);
  if(!TMAP.getPane(paneName)){ TMAP.createPane(paneName);
    const p=TMAP.getPane(paneName); p.style.zIndex=paneZ; p.style.pointerEvents="none"; }
  const fLat=dLat/SS, fLon=dLon/SS;                                    // geo-register incl. the pad margin
  const bounds=[[latMin-PAD*fLat, lonMin-PAD*fLon],[latMin+(H-1-PAD)*fLat, lonMin+(W-1-PAD)*fLon]];
  return L.layerGroup([L.imageOverlay(cv.toDataURL(), bounds,
    {pane:paneName, opacity:0.85, interactive:false, className:"hailheat"})]);
}

// ---- Zoom-scaled vector strokes/dots (portal-side, display-only) ----
// The engine §3 render gives ad-target circles a GEOGRAPHIC radius (meters) so the
// fills scale with zoom like the P3 margins do. But the ring STROKE weight and the
// center dots + evidence pins are fixed PIXELS, so zoomed out they stay bold and read
// as noise. This walks the §3 vector layers on every zoomend and scales stroke weight
// (geographic L.Circle) and dot/pin radius+weight (pixel L.CircleMarker) with zoom, so
// they thin out when zoomed out and bolden back up when zoomed in. Live/heat panes are
// skipped — they have their own LOD and re-render on zoom.
var VEC_SKIP_PANES = {trackPane:1, warnPane:1, nexradPane:1, contourPane:1,
  hHeatPane:1, wHeatPane:1, tHeatPane:1};
function scaleVectors(){
  if(!TMAP) return;
  var z = TMAP.getZoom();
  var s = Math.max(0.30, Math.min(1.15, (z-5)/6));   // z5->0.30  z11->1.00  z12+->1.15
  function walk(grp){
    grp.eachLayer(function(l){
      if(l.getLayers){ walk(l); return; }                       // recurse layer groups
      var pane = (l.options && l.options.pane) || "overlayPane";
      if(VEC_SKIP_PANES[pane]) return;
      if(l instanceof L.Circle){                                // geographic ring: scale stroke only
        if(l.__bw==null) l.__bw = l.options.weight;
        l.setStyle({weight: Math.max(0.4, l.__bw*s)});
      } else if(l instanceof L.CircleMarker){                   // px dot / evidence pin: scale radius + stroke
        if(l.__br==null) l.__br = l.options.radius;
        if(l.__bw==null) l.__bw = (l.options.weight!=null ? l.options.weight : 1);
        l.setRadius(Math.max(1.2, l.__br*s));
        l.setStyle({weight: Math.max(0.5, l.__bw*s)});
      }
    });
  }
  walk(TMAP);
}

async function boot(){
  if(matchMedia("(pointer:coarse)").matches || /Android|iPhone|iPad|iPod|Mobile|Silk/i.test(navigator.userAgent))
    document.body.classList.add("mobile");
  const date = getDate();
  document.getElementById("navDateBtn").textContent = fmtDate(date)+" \\u25be";
  document.getElementById("navDateBtn").onclick = e => { e.stopPropagation(); toggleCal(); };
  document.getElementById("navPrev").onclick  = () => goDate(shiftDate(date, -1));
  document.getElementById("navNext").onclick  = () => goDate(shiftDate(date,  1));
  document.getElementById("navToday").onclick = () => goDate(stormDayUTC());   // "Today" = storm-day (has the live swath)
  document.getElementById("calPrev").onclick = e => { e.stopPropagation(); closeCalPick(); if(!calView)renderCal(); calView.m--; if(calView.m<0){calView.m=11;calView.y--;} renderCal(); };
  document.getElementById("calNext").onclick = e => { e.stopPropagation(); closeCalPick(); if(!calView)renderCal(); calView.m++; if(calView.m>11){calView.m=0;calView.y++;} renderCal(); };
  document.getElementById("calTitle").onclick = e => { e.stopPropagation(); openCalPick(); };
  document.getElementById("cpYrPrev").onclick = e => { e.stopPropagation(); calPickYr--; renderCalPick(); };
  document.getElementById("cpYrNext").onclick = e => { e.stopPropagation(); calPickYr++; renderCalPick(); };
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
  const ab=document.getElementById("alertBtn"); if(ab) ab.onclick=enableAlerts; updateAlertBtn();
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
  if(date === stormDayUTC()){
    try { const fs = await pquery("storm_forecast_status", {});
      if(fs && fs[0]){ const r=fs[0].current_active_risk;
        forecast = (r && r!=="none") ? r : "No qualifying severe risk in the SPC outlook right now."; } }
    catch(e){}
  }
  // ALWAYS render the interactive map (basemap + service-area reference), storm or not.
  const D = assemble(date, rows||[], geo);
  renderMap(D);
  setBaseStreet();
  paintRankedTargets(D);   // #6 additive: payout-score rank badges (no-op if no data)
  // Smooth the engine hail swath (the §3 SwathLayer canvas in swathPane) the same way the
  // live radar is smoothed: a zoom-scaled blur softens the per-MESH-cell blocks into a
  // continuous heatmap. DISPLAY ONLY -- the §3 render core, the cell data, and the crisp
  // ad-circles/dots (separate panes) are untouched; only the swathPane canvas is blurred.
  if(TMAP){
    const smoothSwath=()=>{ const z=TMAP.getZoom();
      const b=Math.max(0.8, Math.min(4.0, (z-3)*0.42)).toFixed(2);
      ["swathPane","windPane","tornadoPane"].forEach(n=>{ const p=TMAP.getPane(n);
        if(p) p.style.filter="blur("+b+"px) saturate(1.12)"; }); };
    smoothSwath(); TMAP.on("zoomend", smoothSwath);
    scaleVectors(); TMAP.on("zoomend", scaleVectors); }
  // SMOOTH SWATHS: continuous heatmaps for hail + wind + tornado (each its own dark->bright
  // ramp), with one Cells|Smooth toggle. Smooth = show heatmaps + hide the blocky canvas
  // panes; Cells = the original blurred §3 canvases. Display-only; circles/dots untouched.
  if(TMAP){
    // HAIL fill modes mirror the §3 radio: intensity=c[3] (1–10), size=c[2] (in), priority=tier(c[3]).
    // Per-peril value extractor; the color range auto-fits inside buildHeatmap (p5..p90 of the
    // blurred grid), so every layer spreads across the full ramp regardless of its data floor.
    const HAIL_FILL={
      intensity:{fn:c=>+c[3]||0},
      size:     {fn:c=>+c[2]||0},
      // priority = discrete tiers (P3/P2/P1 -> 1/2/3), rendered purple/orange/yellow
      priority: {fn:c=>{const it=+c[3]||0; return it>=7?3:it>=4?2:it>0?1:0;}},
    };
    const curHailMode=()=>{ const r=document.querySelector('.ctlpanel input[name="hm"]:checked'); return (r&&HAIL_FILL[r.value])?r.value:"intensity"; };
    // A SUB-GATE swath (e.g. a live provisional day with only 0.75-1.125" hail -> every cell intensity 0)
    // makes the INTENSITY heatmap all-zero, so buildHeatmap returns null, HL stays empty, the smooth
    // machinery is skipped, and the blocky Cells canvas is left visible. Fall back to SIZE (non-zero on
    // sub-gate cells) so the live/provisional swath still renders SMOOTH/feathered like a registered date.
    // Gated storms build the intensity heatmap normally -> ZERO change to canonical dates with >=1.125" hail.
    const hailHeat=()=>{ let h=buildHeatmap(D.swath_cells,HAIL_FILL[curHailMode()].fn,HAIL_RAMP,"hHeatPane",351);
      if(!h && curHailMode()==="intensity") h=buildHeatmap(D.swath_cells,HAIL_FILL["size"].fn,HAIL_RAMP,"hHeatPane",351);
      return h; };
    const HL=[];   // {pane,group,peril,op}
    if(D.swath_mode==="per_cell" && D.swath_cells && D.swath_cells.length){
      const h=hailHeat();
      if(h) HL.push({pane:"swathPane",group:h,peril:"hail",op:0.6}); }
    if(D.wind && D.wind.swath_cells && D.wind.swath_cells.length){
      const w=buildHeatmap(D.wind.swath_cells,c=>+c[2]||0,WIND_RAMP,"wHeatPane",354); if(w) HL.push({pane:"windPane",group:w,peril:"wind",op:0.55}); }
    if(D.tornado && D.tornado.swath_cells && D.tornado.swath_cells.length){
      const t=buildHeatmap(D.tornado.swath_cells,c=>+c[2]||0,TORN_RAMP,"tHeatPane",355); if(t) HL.push({pane:"tornadoPane",group:t,peril:"tornado",op:0.55}); }
    if(HL.length){ let mode="smooth";
      const setOp=o=>o.group.eachLayer(im=>im.setOpacity(o.op));
      const chk=sel=>{ const e=document.querySelector(sel); return !e || e.checked; };
      // visible only when BOTH the §3 peril master AND its Swath sub-toggle are on
      const visOf=pk=>chk('.ctlpanel input[data-master="'+pk+'"]') && chk('.ctlpanel input[data-layer="'+pk+'-swath"]');
      const apply=()=>{ HL.forEach(o=>{ const cp=TMAP.getPane(o.pane);
        if(mode==="smooth"){ if(visOf(o.peril)){ o.group.addTo(TMAP); setOp(o); } else if(TMAP.hasLayer(o.group)) TMAP.removeLayer(o.group);
          if(cp) cp.style.display="none"; }
        else { if(TMAP.hasLayer(o.group)) TMAP.removeLayer(o.group); if(cp) cp.style.display=""; } }); };
      // initial opacity = the Layers-panel Swath dial position (so they start in sync)
      HL.forEach(o=>{ const dl=document.querySelector('.ctlpanel input[data-dial="'+o.peril+'-swath"]'); if(dl) o.op=dl.value/100; });
      // rebuild the hail heatmap when the §3 fill radio changes (int/size/priority)
      const rebuildHail=()=>{ const o=HL.find(x=>x.peril==="hail"); if(!o)return;
        if(TMAP.hasLayer(o.group)) TMAP.removeLayer(o.group);
        const g=hailHeat();   // sub-gate swath -> size fallback so it stays SMOOTH (see hailHeat above)
        if(g){ o.group=g; if(mode==="smooth"&&visOf("hail")){ o.group.addTo(TMAP); setOp(o); } } };
      // DRIVE the smooth swath from the existing §3 Layers panel:
      const panel=document.querySelector(".ctlpanel");
      if(panel){
        // Cells | Smooth toggle injected INTO the Layers panel (right under the title) — no separate box.
        const row=document.createElement("div"); row.className="swathrender";
        row.innerHTML='<span class="srlabel">Swath render</span><span class="st-btns"><button id="stCells">Cells</button><button id="stCont" class="on">Smooth</button></span>';
        const title=panel.querySelector(".ptitle");
        if(title) title.insertAdjacentElement("afterend", row); else panel.insertBefore(row, panel.firstChild);
        L.DomEvent.disableClickPropagation(row);
        // spell out the §3 hail fill labels: int -> Intensity, size -> Size, pri -> Priority
        const FILL_LABEL={intensity:"Intensity",size:"Size",priority:"Priority"};
        panel.querySelectorAll(".sub.mode label").forEach(lb=>{ const inp=lb.querySelector('input[name="hm"]'); if(!inp)return;
          const full=FILL_LABEL[inp.value]; if(!full)return;
          lb.childNodes.forEach(n=>{ if(n.nodeType===3 && n.textContent.trim()) n.textContent=" "+full; }); });
        const bc=document.getElementById("stCells"), bt=document.getElementById("stCont");
        if(bc) bc.onclick=()=>{ mode="cells"; bc.classList.add("on"); bt.classList.remove("on"); apply(); };
        if(bt) bt.onclick=()=>{ mode="smooth"; bt.classList.add("on"); bc.classList.remove("on"); apply(); };
        panel.addEventListener("input",ev=>{ const t=ev.target; if(!t.dataset||!t.dataset.dial)return;   // Swath opacity dial
          const id=t.dataset.dial; if(id.slice(-6)!=="-swath")return; const o=HL.find(x=>x.peril===id.split("-")[0]); if(!o)return;
          o.op=t.value/100; if(mode==="smooth"&&TMAP.hasLayer(o.group)) setOp(o); });
        panel.addEventListener("change",ev=>{ const t=ev.target; if(!t.dataset)return;
          if(t.name==="hm"){ rebuildHail(); return; }                                                    // fill mode
          if(t.dataset.master!=null || (t.dataset.layer!=null && t.dataset.layer.slice(-6)==="-swath")) apply(); }); // master / Swath toggle
      }
      apply();
    }
  }
  // Stable HOME view: renderMap fitBounds-to-storm over-zooms small swaths. Override to
  // a consistent STL-center view at a normal zoom (pan, don't zoom-to-fit). Post-render
  // from the bootstrap via the captured handle — renderMap's §3 core is untouched.
  if(TMAP) TMAP.setView([38.63, -90.2], 9);
  addLiveLayers();      // item 7 ext: live NEXRAD loop + NWS warnings + storm-track cones (display-only, all off by default)
  initWeather();        // weather tab: rain forecast for job scheduling (isolated tool view; NWS + Census, no graph/engine)
  addChaseLayer(D.chase);   // item 8 Step 3 v2: chase TARGETING block at the bottom of the Layers panel (master OFF)
  addMapSearch();           // map location search: City/State + address typeahead (reuses Photon; navigation only)
  addPull();                // item 10: on-demand PULL (150mi capture -> secured write endpoint)
  buildOperatorPanel(D, forecast);
  setupSpendDial(D);     // spend-dial panel (grays out when the date has no qualified storm / no ad targets)
  setupFloatPanels();    // desktop: Layers/Storm Review/Spend Dial/Active perils/LIVE -> draggable floating boxes (#tbar2); all closed on load
  setupMobile();
  setupPush();           // PWA push subscribe + re-subscribe-on-open (best-effort; SMS is the backbone)
  handleApproveDeepLink(); // ?s=TOKEN -> the shared approve modal (PWA + plain tab)
  if(banner) showBanner(banner); else hideBanner();
}
boot();
// register the service worker so Chrome offers a real app Install (icon + own window)
if("serviceWorker" in navigator){ navigator.serviceWorker.register("sw.js").catch(function(){}); }
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
<title>TEMPEST — KCC Hail Intelligence</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg"/>
<link rel="icon" href="favicon.ico" sizes="any"/>
<link rel="apple-touch-icon" href="apple-touch-icon.png"/>
<link rel="manifest" href="site.webmanifest"/>
<meta name="theme-color" content="#0B1A2F"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>
<meta name="apple-mobile-web-app-title" content="Tempest"/>
<meta property="og:title" content="TEMPEST — KCC Hail Intelligence"/>
<meta property="og:description" content="Storm-triggered hail intelligence and lead targeting."/>
<meta property="og:image" content="og-image.png"/>
<meta property="og:type" content="website"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@{LEAFLET}/dist/leaflet.css"/>
<script src="https://cdn.jsdelivr.net/npm/d3-array@3"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-contour@4"></script>
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
