// Public config — NO credential. Points at the Netlify server-side forwarder,
// which holds the proxy bearer token in a Netlify env var (STORM_PROXY_TOKEN).
window.TEMPEST_CONFIG = { api: "https://kcc-proxy.netlify.app/api/storm" };
