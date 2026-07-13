// Shared helper for pages that call /v1/estimate client-side (app.js,
// property.js, compare.js). The API requires an X-API-Key header on every
// request; the browser's key is a public, low-privilege value rendered
// server-side into a <meta name="airworthy-browser-key"> tag on each page
// (see src/api.py BROWSER_API_KEY) — it's visible in page source by design,
// the same trust model as a Stripe publishable key.
function apiHeaders() {
    const meta = document.querySelector('meta[name="airworthy-browser-key"]');
    const headers = { 'Content-Type': 'application/json' };
    if (meta && meta.content) {
        headers['X-API-Key'] = meta.content;
    }
    return headers;
}
