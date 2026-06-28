// Public config — NO credential. Points at the Netlify server-side forwarders, which hold the
// proxy bearer tokens in Netlify env vars (STORM_PROXY_TOKEN read / STORM_WRITE_TOKEN write).
// The VAPID PUBLIC key is safe to ship (the private key lives only in the engine .env).
window.TEMPEST_CONFIG = {
  api: "https://kcc-proxy.netlify.app/api/storm",          // read (storm_date_layers etc.)
  spendApi: "https://kcc-proxy.netlify.app/api/spend",     // -solve (read) / -approve (write)
  pushApi: "https://kcc-proxy.netlify.app/api/push",       // store a push subscription (write)
  approveApi: "https://kcc-proxy.netlify.app/api/approve", // -validate (read) / approve (write)
  vapidPublicKey: "BE4wxfQF_g8uW8ApIUqj4KrQDVi2tdkprEn_5ldyn5PBjqZRS0IVflIuvYst38qIvcHE34V51iIFpaOusnWKTe8",
  remainingAnnualCapacity: null                            // operator state (jobs); set when known
};
