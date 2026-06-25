# TEMPEST — KCC Storm Review portal

The live, date-navigable multi-peril storm viewer (hail / wind / tornado). Static
site on GitHub Pages, reads the read-only FastAPI proxy's whitelisted queries
through the named Cloudflare tunnel — **same stack/deploy as the SignalDelta
portal**. Read-only; no Start/Stop controls (deferred).

## What it shows
The exact §3-locked multi-peril map the operator already uses — per-peril swaths
(warm hail / blue wind / violet tornado) + ad-target circles + per-peril layer
bands with toggles & opacity dials + white-halo tier rings + white-density P3 +
click-to-reveal dots + legend-from-one-table + basemap switcher/opacity. The map
render core is reused verbatim from `storm-engine/storm/review/template.html`
(wrapped into `renderMap(D)` by `build_portal.py`) so no locked decision can drift.

## Date navigation
- Opens on **today** (UTC).
- **◀ / ▶** step one day; the **calendar** input jumps to any date.
- A date loads that date's persisted results from the proxy (`storm_date_layers`).
- Unprocessed in-archive dates show a clean "no storm on record" state; pre-archive
  (before **2020-10-14**, the operational-MRMS start) shows a "no data" state.
- **Read-only build:** it does not trigger detection runs. The daily monitor
  processes new dates; on-demand run-from-the-portal is a later build.

## Data path (read-only)
`portal → proxy POST /query {name, params} (Bearer token) → Neo4j (READ) → rows`.
Whitelisted queries used: `storm_available_dates`, `storm_date_layers`,
`storm_engine_status`, `storm_forecast_status`. Each is tenant-guarded
(`:StormNode`, excludes KCC/KTM/Trade). The per-date render payload (swath +
circles + evidence) is cached on the `AdCluster` nodes so the proxy serves it with
no compute. `public/geo_ref.json` ships the constant service-area reference.

## Token-free architecture (the bearer never touches the public site)
```
GitHub Pages portal  ──POST {name,params}──▶  Netlify function /api/storm
   (no credential)                              (holds STORM_PROXY_TOKEN, server-side)
                                                       │ injects Bearer
                                                       ▼
                                          proxy.signaldeltas.com /query (READ)  ──▶ Neo4j
```
The public bundle (`config.js`) holds only the **public** forwarder URL
(`https://kcc-proxy.netlify.app/api/storm`). The proxy bearer token lives **only**
in the Netlify function's `STORM_PROXY_TOKEN` environment variable — never in this
repo, never in any client bundle (same pattern `kcc-netlify-proxy` uses for the
Anthropic key). So GitHub Pages deploys with **no secrets at all**.

## Deploy (one-time)
1. **Netlify** (`kcc-proxy` site → env vars): `STORM_PROXY_TOKEN` = the SignalDelta
   proxy `PROXY_API_TOKEN`. The `/api/storm` forwarder (in the `kcc-netlify-proxy`
   repo) is already wired via a `netlify.toml` redirect.
2. **Pages**: repo → Settings → Pages → Source = GitHub Actions. Push to `main` →
   Actions publishes the static folder (no secret injection).
3. On the host: `nssm restart SignalDeltaProxy` once, so the proxy loads the
   `storm_*` whitelisted queries.

## Local dev / demo
`py -m http.server 8902` in this folder, open `index.html?date=2024-05-26`. It calls
the live `/api/storm` forwarder; if that's unreachable it falls back to a local
`public/sample/<date>.json` (gitignored) and shows a "DEMO DATA" badge.

## Local dev / demo
`py -m http.server 8902` in this folder, open `index.html?date=2024-05-26`. With a
local `config.js` pointing at the proxy it reads live; otherwise it falls back to
`public/sample/<date>.json` and shows a "DEMO DATA" badge.

## Regenerate / revert
`index.html` is generated: `py build_portal.py` (reads the engine template). The
engine viewer template is never modified by this repo; `_lastgood/` holds a copy
for reference. Reverting any polish = re-run `build_portal.py` or delete this repo
— the engine viewer stays pristine.
