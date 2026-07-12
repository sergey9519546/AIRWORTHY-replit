# Frontend Audit — Rentalizer

**Auditor:** Senior Frontend Developer  
**Date:** 2026-06-29  
**Files reviewed:** `templates/index.html`, `static/style.css`, `static/app.js`

---

## 1. UX — Flow & Intuitiveness

### Issues

- **No autocomplete on address field.** Users typing "350 5th Ave" have zero guidance on formatting. This is the #1 friction point. Without geocoding autocomplete, users will guess formats and get errors.
- **Nightly rate defaults to $150 with no explanation.** Where did this number come from? A user seeing this will either trust it blindly or ignore it. It should either be contextual ("NYC average: $150") or removed as a default—make it optional with a placeholder.
- **Results appear below the fold.** After clicking "Estimate Revenue," the page doesn't scroll to results. On mobile, the user sees the spinner vanish and has to manually scroll down to find the results.
- **No empty state for comps.** If `data.comps` is empty, the "Comparable Properties" card shows just a header with nothing below it.
- **The "Studio" option is value `0` bedrooms.** This is technically correct but confusing UX—most platforms say "Studio" and let the backend handle the mapping. The label is fine, but the form should hint that "Studio = 0 bedrooms" isn't obvious to everyone.
- **No input for property type** (entire home vs. private room vs. shared room). This is a major revenue driver on Airbnb and its absence will produce misleading estimates.

### Recommendations

```html
<!-- Add property type -->
<div class="form-group">
    <label for="room_type">Property Type</label>
    <select id="room_type" name="room_type">
        <option value="Entire home/apt" selected>Entire Home</option>
        <option value="Private room">Private Room</option>
        <option value="Shared room">Shared Room</option>
    </select>
</div>
```

```js
// After rendering results, scroll to them
results.scrollIntoView({ behavior: 'smooth', block: 'start' });
```

---

## 2. Design — Professionalism

### Issues

- **The Airbnb red `#ff5a5f` as the primary accent is a legal/trust liability.** This is Airbnb's trademark color. Using it makes the tool look like a knock-off or phishing site. Pick your own brand color.
- **No visual hierarchy in results.** The revenue number is big, but the confidence badge, market stats, and comps all compete equally. There's no visual "story" guiding the user from "here's your estimate" → "here's how confident we are" → "here's why."
- **Box shadows are flat and identical.** Every card uses `0 2px 8px rgba(0,0,0,0.1)`. This creates a monotone, template-like feel. Use elevation hierarchy—form card gets more shadow on hover, results cards get subtle depth variation.
- **No favicon.** Browser tabs show a generic icon. Kills trust instantly.
- **No logo.** Just an emoji `🏠`. Looks like a weekend project, not a product.
- **The form and results have no visual connection.** The form disappears (mentally) when results appear below it. Consider a sticky form summary or a "change inputs" button in results.

### Recommendations

```css
/* Replace Airbnb red with your own brand */
:root {
    --color-primary: #4f46e5;      /* Indigo — professional, trustworthy */
    --color-primary-hover: #4338ca;
    --color-surface: #ffffff;
    --color-bg: #f8fafc;
    --color-text: #1e293b;
    --color-text-muted: #64748b;
}

button[type="submit"] {
    background: var(--color-primary);
}
button[type="submit"]:hover {
    background: var(--color-primary-hover);
}

/* Add elevation hierarchy */
form:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.result-card {
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.result-header {
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid #e2e8f0;
}
```

---

## 3. Responsiveness

### Issues

- **600px breakpoint is too narrow.** The form-row goes to 4 columns at any width above 600px. On a 768px tablet, four dropdowns crammed side-by-side are unreadable. Need a 768px breakpoint too.
- **No touch-friendly tap targets.** The select dropdowns and button meet the 44px minimum, but the comp rows are only `padding: 8px 0` — way too small for mobile tapping.
- **Map height is fixed at 300px.** On mobile, this takes up most of the viewport. On desktop, it's tiny.
- **No safe-area-inset handling** for notched iPhones (the footer touches the home indicator).
- **Revenue font at 1.6rem on mobile** is still large but the layout doesn't adapt—the two result cards stack but the comp table's 4-column grid stays, causing overflow on narrow screens.

### Recommendations

```css
@media (max-width: 768px) {
    .form-row { grid-template-columns: 1fr 1fr; }
    .comp-item { grid-template-columns: 1fr 1fr; font-size: 0.85rem; }
    .map-container { height: 200px; }
    .container { padding: 16px; padding-bottom: env(safe-area-inset-bottom, 16px); }
}

@media (max-width: 480px) {
    .form-row { grid-template-columns: 1fr; }
    .comp-item { grid-template-columns: 1fr; }
    .revenue-range { font-size: 1.4rem; }
    header h1 { font-size: 1.5rem; }
}
```

---

## 4. Accessibility

### Issues

- **Zero ARIA attributes.** No `aria-live` on results/error/loading. Screen readers won't announce when results appear or when an error occurs.
- **No focus management.** After form submission, focus stays on the submit button. It should move to the results or error.
- **Color contrast: `#666` on `#f5f5f5` background.** The ratio is ~4.0:1 — fails WCAG AA for normal text (requires 4.5:1). The subtitle, stat labels, and disclaimer all fail.
- **The spinner has no accessible label.** `role="status"` and `aria-label="Loading"` are missing.
- **Error div has no `role="alert"`.** Screen readers won't announce errors.
- **No `:focus-visible` styles.** Keyboard users can't see where they are.
- **`<select>` elements have no visible focus indicator** beyond the browser default.

### Recommendations

```html
<!-- Loading spinner -->
<div id="loading" class="hidden" role="status" aria-live="polite">
    <div class="spinner" aria-hidden="true"></div>
    <p>Analyzing property...</p>
</div>

<!-- Error -->
<div id="error" class="hidden" role="alert" aria-live="assertive">
    <p id="error-message"></p>
</div>

<!-- Results -->
<div id="results" class="hidden" aria-live="polite" tabindex="-1">
```

```css
/* Fix contrast — use #64748b instead of #666 */
.subtitle { color: #64748b; }
.stat-label { color: #64748b; }
.disclaimer { color: #64748b; }

/* Focus styles */
:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}
button[type="submit"]:focus-visible {
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.4);
}
```

```js
// After results render
results.classList.remove('hidden');
results.focus(); // Move focus to results container

// After error
error.classList.remove('hidden');
document.getElementById('error-message').focus();
```

---

## 5. Performance

### Issues

- **Mapbox GL JS loaded on every page load** (~200KB gzipped) even if the user never submits the form. This is the single largest performance issue.
- **No `defer` or `async` on scripts.** Both Mapbox and app.js block rendering.
- **No preload for critical resources.** The CSS is render-blocking.
- **No `loading="lazy"` on the map container** (it's below the fold).
- **No `<link rel="preconnect">` for Mapbox CDN.**
- **The Carto basemap style JSON** (`basemaps.cartocdn.com`) is loaded at runtime with no preconnect hint.
- **No service worker or caching strategy** for the static assets.

### Recommendations

```html
<!-- Preconnect -->
<link rel="preconnect" href="https://api.mapbox.com">
<link rel="preconnect" href="https://basemaps.cartocdn.com">

<!-- Defer scripts -->
<script src="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js" defer></script>
<script src="/static/app.js" defer></script>
```

```js
// Lazy-load Mapbox only when results are shown
let mapboxLoaded = false;
function loadMapbox() {
    if (mapboxLoaded) return Promise.resolve();
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js';
        script.onload = () => { mapboxLoaded = true; resolve(); };
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// In renderResults, before renderMap:
await loadMapbox();
renderMap(data.lat, data.lng, data.comps);
```

---

## 6. Error Handling

### Issues

- **Generic error messages.** `err.message` from `catch` could be a network error, JSON parse error, or API error. The user sees "Failed to fetch" or "Unexpected token < in JSON" — meaningless to a non-developer.
- **No retry mechanism.** If the API times out, the user has to manually re-submit.
- **No handling for non-JSON error responses.** If the server returns a 502 HTML page, `resp.json()` will throw a parse error, and the user sees a cryptic JSON parse message instead of "Server error."
- **No timeout on fetch.** A hung request leaves the spinner spinning forever.
- **No handling for `data.comps` being undefined/null.** The `for...of` loop will throw.
- **No handling for missing `data.confidence` fields.** If the API shape changes, `data.confidence.cv.toFixed(2)` throws.

### Recommendations

```js
// Improved fetch with timeout and better errors
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 15000);

try {
    const resp = await fetch('/v1/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
    });
    clearTimeout(timeout);

    let data;
    try {
        data = await resp.json();
    } catch {
        throw new Error('Server returned an invalid response. Please try again.');
    }

    if (!resp.ok) {
        throw new Error(data.detail || data.error || `Request failed (${resp.status})`);
    }

    // Validate response shape
    if (!data.confidence || !data.market) {
        throw new Error('Unexpected response format. The API may have changed.');
    }

    renderResults(data);
    results.classList.remove('hidden');
    results.scrollIntoView({ behavior: 'smooth' });
} catch (err) {
    clearTimeout(timeout);
    let message = err.message;
    if (err.name === 'AbortError') {
        message = 'Request timed out. The server may be overloaded — please try again.';
    } else if (err.message === 'Failed to fetch') {
        message = 'Cannot reach the server. Please check your connection.';
    }
    document.getElementById('error-message').textContent = message;
    error.classList.remove('hidden');
}
```

---

## 7. Loading States

### Issues

- **The spinner is CSS-only with no reduced-motion support.** Users with `prefers-reduced-motion` see a spinning animation they may have configured their OS to avoid.
- **No skeleton loading.** The results area just pops in. A skeleton/shimmer would feel smoother.
- **Submit button just disables** with no visual change beyond gray color. Should show inline progress.
- **No progress indication for map loading** after the API results arrive. The user sees comps but an empty map box.

### Recommendations

```css
@media (prefers-reduced-motion: reduce) {
    .spinner {
        animation: none;
        border-top-color: var(--color-primary);
    }
}
```

```js
// Better button state
btn.disabled = true;
btn.innerHTML = '<span class="spinner-inline"></span> Analyzing…';
// On complete:
btn.textContent = 'Estimate Revenue';
```

---

## 8. Form Validation

### Issues

- **Only `required` on the address field.** No other client-side validation.
- **Nightly rate `min="25" max="5000"` is HTML-only.** No JavaScript validation, no user feedback if they enter `5` or `99999`. The browser shows a generic "Value must be less than or equal to 5000" tooltip that's easy to miss.
- **No address format validation.** An empty string with spaces passes `required`.
- **No debounce or real-time validation.** The user fills everything out, clicks submit, waits for the API, and only then discovers the address is garbage.
- **No validation that nightly_rate is a number.** If the user types "abc", `parseFloat` returns `NaN` and the API gets garbage.

### Recommendations

```js
// Add before the fetch call
const rate = parseFloat(form.nightly_rate.value);
if (isNaN(rate) || rate < 25 || rate > 5000) {
    document.getElementById('error-message').textContent = 'Nightly rate must be between $25 and $5,000.';
    error.classList.remove('hidden');
    loading.classList.add('hidden');
    btn.disabled = false;
    return;
}

const address = form.address.value.trim();
if (address.length < 5) {
    document.getElementById('error-message').textContent = 'Please enter a valid address.';
    error.classList.remove('hidden');
    loading.classList.add('hidden');
    btn.disabled = false;
    return;
}
```

---

## 9. Map Integration

### Issues

- **Mapbox access token is empty string.** `mapboxgl.accessToken = ''` means every Mapbox GL call will fail with an auth error. The fallback to the OpenStreetMap iframe will always trigger, making the entire Mapbox dependency pointless dead weight (~200KB for nothing).
- **Comp markers all placed at the same coordinates as the property.** `setLngLat([lng, lat])` for every comp — they all stack on top of each other. The comment says "Would need comp coords" — so this feature is incomplete.
- **The Carto basemap style** (`basemaps.cartocdn.com/gl/positron-gl-style/style.json`) is a third-party dependency with no SLA. If it goes down, the map breaks.
- **The OSM iframe fallback** uses fixed bbox offsets (`±0.05` lng, `±0.03` lat) regardless of zoom level or area density.
- **No attribution in the Mapbox map** (Mapbox requires it per TOS).

### Recommendations

- Either commit to Mapbox (set a real token, get comp coordinates from the API) or drop it entirely and use Leaflet + OpenStreetMap (free, no token required, ~40KB).
- The API should return comp coordinates. Without them, the map is useless for comparisons.

```js
// If going the Leaflet route (recommended — free, lighter)
// Replace Mapbox with:
// <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css">
// <script src="https://unpkg.com/leaflet@1.9/dist/leaflet.js" defer></script>

function renderMap(lat, lng, comps) {
    const map = L.map('map').setView([lat, lng], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    L.marker([lat, lng]).addTo(map).bindPopup('<b>Your property</b>');

    for (const comp of comps) {
        if (comp.lat && comp.lng) {
            L.marker([comp.lat, comp.lng], { icon: blueIcon })
                .addTo(map)
                .bindPopup(`${comp.bedrooms} BR — ${formatCurrency(comp.revenue)}/yr`);
        }
    }
}
```

---

## 10. SEO

### Issues

- **No meta description.** Search engines show a snippet from the page body, which is just "Estimate Airbnb revenue for any NYC property."
- **No Open Graph tags.** Sharing this link on Slack/Twitter/LinkedIn shows nothing — no image, no description.
- **No structured data (JSON-LD).** No `SoftwareApplication` or `WebApplication` schema.
- **No canonical URL.**
- **No `robots.txt` consideration** (though this may be intentional if it's a private tool).
- **No `<meta name="theme-color">`** for mobile browser chrome.

### Recommendations

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rentalizer — Airbnb Revenue Estimator | NYC</title>
    <meta name="description" content="Estimate annual Airbnb revenue for any NYC property. Based on real InsideAirbnb data with confidence intervals and market comparisons.">
    <meta name="theme-color" content="#4f46e5">

    <!-- Open Graph -->
    <meta property="og:title" content="Rentalizer — Airbnb Revenue Estimator">
    <meta property="og:description" content="Estimate annual Airbnb revenue for any NYC property.">
    <meta property="og:type" content="website">
    <meta property="og:image" content="/static/og-image.png">  <!-- Create one -->
    <meta property="og:url" content="https://your-domain.com">

    <!-- Favicon -->
    <link rel="icon" href="/static/favicon.ico" type="image/x-icon">

    <link rel="stylesheet" href="/static/style.css">
</head>
```

---

## 11. Security

### Issues

- **XSS via `innerHTML`.** Every `renderResults` call uses `innerHTML` to inject API response data directly into the DOM. If the API returns malicious content in `borough`, `disclaimer`, or any comp field, it executes as HTML.

  ```js
  // This is vulnerable:
  document.getElementById('market-details').innerHTML = `...${data.market.borough}...`;
  ```

- **No Content Security Policy.** No `<meta http-equiv="Content-Security-Policy">` tag. Inline scripts and `eval` are unrestricted.
- **No `X-Content-Type-Options` or `X-Frame-Options` headers** (though these are server-side, the frontend should document the need).
- **Mapbox token is empty** — but if someone adds it client-side, it's exposed in the source. Mapbox tokens should be scoped to the domain.
- **The OSM iframe fallback** could potentially be used for clickjacking if the page is framed.
- **No CSRF protection on the POST endpoint.** The form sends JSON via fetch, which provides some protection, but a `SameSite` cookie policy should be enforced server-side.

### Recommendations

```js
// Use textContent instead of innerHTML wherever possible
function renderResults(data) {
    // Revenue
    const lower = formatCurrency(data.confidence.revenue_lower);
    const upper = formatCurrency(data.confidence.revenue_upper);
    document.getElementById('revenue-range').textContent = `${lower} — ${upper}`;

    // For the comps list, build DOM nodes instead of innerHTML
    const compsList = document.getElementById('comps-list');
    compsList.innerHTML = ''; // Clear

    // Header row
    const header = document.createElement('div');
    header.className = 'comp-item comp-header-row';
    ['Borough', 'Beds', 'Revenue', 'Distance'].forEach(text => {
        const span = document.createElement('span');
        span.className = 'comp-header';
        span.textContent = text;
        header.appendChild(span);
    });
    compsList.appendChild(header);

    // Comp rows
    for (const comp of data.comps) {
        const row = document.createElement('div');
        row.className = 'comp-item';
        [comp.borough, `${comp.bedrooms} BR`, formatCurrency(comp.revenue), `${comp.distance_km} km`]
            .forEach(text => {
                const span = document.createElement('span');
                span.textContent = text; // Safe — no HTML parsing
                row.appendChild(span);
            });
        compsList.appendChild(row);
    }
}
```

```html
<!-- CSP meta tag (adjust as needed) -->
<meta http-equiv="Content-Security-Policy" content="
    default-src 'self';
    script-src 'self' https://api.mapbox.com https://unpkg.com;
    style-src 'self' 'unsafe-inline' https://api.mapbox.com https://unpkg.com https://basemaps.cartocdn.com;
    img-src 'self' data: https://*.tile.openstreetmap.org https://api.mapbox.com;
    connect-src 'self' https://api.mapbox.com https://basemaps.cartocdn.com;
    frame-src https://www.openstreetmap.org;
">
```

---

## 12. Trust Factors — What Makes Users NOT Trust This

| Issue | Impact |
|-------|--------|
| **Airbnb's brand color** | Looks like a phishing site or cheap clone |
| **No favicon/logo** | "Is this even a real product?" |
| **Empty Mapbox token** | Map fails silently; user sees a broken feature |
| **No about page or methodology link** | "How are these numbers calculated?" — users can't verify, so they don't trust |
| **Disclaimer is dynamically set from API** | If the API returns no disclaimer, the footer has an empty `<p>`. Users see no legal protection |
| **No "last updated" data timestamp** | "Is this data from 2020 or 2026?" |
| **Comp table has no links or detail** | Just borough names and numbers — feels generic, not real |
| **No user testimonials or social proof** | For a financial estimation tool, this matters |
| **Error messages are developer-facing** | "Failed to fetch" = "this is broken, leave" |
| **No keyboard navigation** | Power users and accessibility-dependent users bounce immediately |

---

## Summary — Priority Fixes

| Priority | Fix | Effort |
|----------|-----|--------|
| 🔴 P0 | **Fix XSS** — replace all `innerHTML` with `textContent`/DOM APIs | 1 hour |
| 🔴 P0 | **Add ARIA live regions** for results, errors, loading | 30 min |
| 🔴 P0 | **Fix color contrast** (`#666` → `#64748b`) | 10 min |
| 🟠 P1 | **Drop Mapbox, use Leaflet** — remove 200KB dead dependency | 1 hour |
| 🟠 P1 | **Add error handling** — timeout, user-friendly messages, retry | 1 hour |
| 🟠 P1 | **Fix responsive breakpoints** — add 768px and 480px | 30 min |
| 🟠 P1 | **Add form validation** — nightly rate, address length | 30 min |
| 🟡 P2 | **Change brand color** — stop using Airbnb's red | 15 min |
| 🟡 P2 | **Add meta tags** — OG, description, favicon | 20 min |
| 🟡 P2 | **Lazy-load map** — only load after results | 30 min |
| 🟡 P2 | **Add CSP header** | 20 min |
| 🟢 P3 | **Add address autocomplete** (Google Places or Nominatim) | 2 hours |
| 🟢 P3 | **Add skeleton loading states** | 1 hour |
| 🟢 P3 | **Add `prefers-reduced-motion` support** | 10 min |

---

## Overall Verdict

**This looks like a weekend prototype, not a production tool.** The structure is reasonable — clean HTML, organized CSS, working async fetch — but it has real security vulnerabilities (XSS), zero accessibility, and enough UX friction that most users will bounce before seeing results. The Mapbox integration is completely non-functional (empty token), which means the map feature is broken for every user.

The good news: the foundation is solid. The form layout works, the API integration pattern is correct, and the CSS is clean. Fixing P0 and P1 issues would take about half a day and transform this from "sketchy prototype" into "credible tool."
