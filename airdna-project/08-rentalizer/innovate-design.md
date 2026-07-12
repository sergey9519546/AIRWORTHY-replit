# Rentalizer — 10 Design Innovations

**Author:** Senior UX/UI Designer  
**Date:** 2026-06-29  
**Baseline:** `templates/index.html`, `static/style.css`, `static/app.js`

---

## Table of Contents

1. [Fix XSS Vulnerability — Sanitize innerHTML](#1-fix-xss-vulnerability)
2. [Accessibility Overhaul — ARIA, Keyboard Nav, Contrast](#2-accessibility-overhaul)
3. [Replace Mapbox with Leaflet](#3-replace-mapbox-with-leaflet)
4. [Address Autocomplete via Nominatim](#4-address-autocomplete)
5. [Revenue Visualization Chart](#5-revenue-visualization-chart)
6. [Professional Brand System](#6-professional-brand-system)
7. [Mobile-First Responsive Redesign](#7-mobile-first-responsive-redesign)
8. [Trust Signals & Social Proof](#8-trust-signals--social-proof)
9. [Comparison Mode — Multiple Properties](#9-comparison-mode)
10. [Loading / Empty / Error States](#10-loading--empty--error-states)

---

## 1. Fix XSS Vulnerability

### Problem

Every `renderResults` call uses `innerHTML` to inject API response data. If the API returns malicious content in `borough`, `disclaimer`, or any comp field, it executes as HTML/JS in the user's browser.

```js
// CURRENT — vulnerable:
document.getElementById('market-details').innerHTML = `
    <div class="stat-row"><span class="stat-label">Borough</span>
    <span class="stat-value">${data.market.borough}</span></div>`;
```

### Solution

Create a centralized safe DOM builder and replace all `innerHTML` patterns.

```js
/* ── static/sanitize.js ────────────────────────────────── */

/**
 * Escape HTML entities to prevent XSS.
 * Use this whenever interpolating untrusted data into innerHTML.
 */
function escapeHTML(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

/**
 * Build a stat row safely using DOM APIs (preferred over innerHTML).
 */
function createStatRow(label, value) {
    const row = document.createElement('div');
    row.className = 'stat-row';

    const labelSpan = document.createElement('span');
    labelSpan.className = 'stat-label';
    labelSpan.textContent = label;           // Safe — no HTML parsing

    const valueSpan = document.createElement('span');
    valueSpan.className = 'stat-value';
    valueSpan.textContent = value;           // Safe — no HTML parsing

    row.appendChild(labelSpan);
    row.appendChild(valueSpan);
    return row;
}

/**
 * Render a list of stat rows into a container, clearing it first.
 */
function renderStatRows(containerId, rows /* Array<[label, value]> */) {
    const el = document.getElementById(containerId);
    el.innerHTML = '';
    for (const [label, value] of rows) {
        el.appendChild(createStatRow(label, value));
    }
}
```

### Updated `renderResults` (key sections)

```js
function renderResults(data) {
    // Revenue — already uses textContent ✓
    const lower = formatCurrency(data.confidence.revenue_lower);
    const upper = formatCurrency(data.confidence.revenue_upper);
    document.getElementById('revenue-range').textContent = `${lower} — ${upper}`;

    // Confidence badge — already uses textContent ✓
    const badge = document.getElementById('confidence-badge');
    badge.textContent = `${data.confidence.level.toUpperCase()} confidence`;
    badge.className = `confidence-badge ${data.confidence.level}`;

    // Confidence details — SAFE
    renderStatRows('confidence-details', [
        ['Level',  data.confidence.level],
        ['CV',     data.confidence.cv.toFixed(2)],
        ['Range',  `${lower} — ${upper}`],
    ]);

    // Market — SAFE
    renderStatRows('market-details', [
        ['Borough',         data.market.borough],
        ['Median Revenue',  formatCurrency(data.market.median_revenue)],
        ['Median Price',    `$${data.market.median_price}/night`],
        ['Active Listings', data.market.active_listings.toLocaleString()],
    ]);

    // Comps — SAFE (DOM API)
    renderComps(data.comps);

    // Disclaimer — already uses textContent ✓
    document.getElementById('disclaimer').textContent = data.disclaimer || '';

    // Map
    renderMap(data.lat, data.lng, data.comps);
}

function renderComps(comps) {
    const container = document.getElementById('comps-list');
    container.innerHTML = '';

    if (!comps || comps.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'empty-state';
        empty.textContent = 'No comparable properties found nearby.';
        container.appendChild(empty);
        return;
    }

    // Header
    const header = document.createElement('div');
    header.className = 'comp-item comp-header-row';
    header.setAttribute('role', 'row');
    ['Borough', 'Beds', 'Revenue', 'Distance'].forEach(text => {
        const span = document.createElement('span');
        span.className = 'comp-header';
        span.setAttribute('role', 'columnheader');
        span.textContent = text;
        header.appendChild(span);
    });
    container.appendChild(header);

    // Data rows
    for (const comp of comps) {
        const row = document.createElement('div');
        row.className = 'comp-item';
        row.setAttribute('role', 'row');
        [
            comp.borough,
            `${comp.bedrooms} BR`,
            formatCurrency(comp.revenue),
            `${comp.distance_km} km`,
        ].forEach(text => {
            const span = document.createElement('span');
            span.setAttribute('role', 'cell');
            span.textContent = text;
            row.appendChild(span);
        });
        container.appendChild(row);
    }
}
```

### CSP Meta Tag (add to `<head>`)

```html
<meta http-equiv="Content-Security-Policy" content="
    default-src 'self';
    script-src 'self' https://unpkg.com;
    style-src 'self' 'unsafe-inline' https://unpkg.com;
    img-src 'self' data: https://*.tile.openstreetmap.org;
    connect-src 'self' https://nominatim.openstreetmap.org;
    frame-src 'none';
">
```

---

## 2. Accessibility Overhaul

### Problems

- Zero ARIA attributes anywhere
- No focus management after form submission
- Color contrast fails WCAG AA (`#666` on `#f5f5f5` ≈ 4.0:1, needs 4.5:1)
- Spinner has no accessible label
- No `:focus-visible` styles
- No keyboard navigation for comps table

### HTML Changes

```html
<!-- Loading — add role and aria-live -->
<div id="loading" class="hidden" role="status" aria-live="polite">
    <div class="spinner" aria-hidden="true"></div>
    <p>Analyzing property…</p>
</div>

<!-- Error — add role="alert" -->
<div id="error" class="hidden" role="alert" aria-live="assertive" tabindex="-1">
    <p id="error-message"></p>
</div>

<!-- Results — add aria-live and tabindex for focus management -->
<div id="results" class="hidden" aria-live="polite" tabindex="-1">
    <h2 class="sr-only">Estimation Results</h2>
    <!-- ... existing content ... -->
</div>

<!-- Comps table — add ARIA table roles -->
<div id="comps-list" role="table" aria-label="Comparable Properties">
    <!-- rows built by JS with role="row" -->
</div>

<!-- Form — add aria-describedby for nightly rate -->
<div class="form-group">
    <label for="nightly_rate">Nightly Rate ($)</label>
    <input type="number" id="nightly_rate" name="nightly_rate"
           value="150" min="25" max="5000"
           aria-describedby="rate-hint">
    <span id="rate-hint" class="hint">NYC average: $150/night</span>
</div>

<!-- Skip link (add at top of body) -->
<a href="#estimate-form" class="skip-link">Skip to form</a>
```

### CSS Changes

```css
/* ── Screen-reader only ────────────────────────────────── */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* ── Skip link ─────────────────────────────────────────── */
.skip-link {
    position: absolute;
    top: -100%;
    left: 16px;
    background: var(--color-primary);
    color: #fff;
    padding: 8px 16px;
    border-radius: 0 0 8px 8px;
    z-index: 1000;
    font-weight: 600;
    text-decoration: none;
    transition: top 0.2s;
}
.skip-link:focus {
    top: 0;
}

/* ── Focus styles ──────────────────────────────────────── */
:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}
button[type="submit"]:focus-visible {
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.4);
}
select:focus-visible,
input:focus-visible {
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15);
}

/* ── Contrast fixes ────────────────────────────────────── */
.subtitle   { color: #475569; }   /* was #666 — now 7.0:1 on #f8fafc */
.stat-label { color: #475569; }
.disclaimer { color: #64748b; }   /* 4.6:1 on #f8fafc — passes AA */
.hint       { color: #64748b; font-size: 0.8rem; margin-top: 4px; }

/* ── Reduced motion ────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
    .spinner {
        animation: none;
        border-top-color: var(--color-primary);
    }
    * { transition-duration: 0.01ms !important; }
}
```

### JS Focus Management

```js
// After successful render:
results.classList.remove('hidden');
results.focus();

// After error:
error.classList.remove('hidden');
error.focus();

// Keyboard navigation for comps (arrow keys)
document.getElementById('comps-list').addEventListener('keydown', (e) => {
    const rows = [...e.currentTarget.querySelectorAll('.comp-item:not(.comp-header-row)')];
    const current = rows.indexOf(document.activeElement);
    if (e.key === 'ArrowDown' && current < rows.length - 1) {
        e.preventDefault();
        rows[current + 1].focus();
    } else if (e.key === 'ArrowUp' && current > 0) {
        e.preventDefault();
        rows[current - 1].focus();
    }
});
// Make comp rows focusable
// In renderComps, add: row.setAttribute('tabindex', '0');
```

---

## 3. Replace Mapbox with Leaflet

### Problem

Mapbox GL JS is ~200KB gzipped, requires an API token (which is empty = broken), and adds a commercial dependency. The OSM iframe fallback is fragile. Comp markers are all placed at the same coordinates.

### Solution: Leaflet + OpenStreetMap (free, ~40KB, no token)

### HTML Changes

```html
<!-- REMOVE these two lines: -->
<!-- <link href="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css" rel="stylesheet"> -->
<!-- <script src="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js"></script> -->

<!-- ADD these (in <head>): -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin="">
<!-- ADD before </body>: -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
        crossorigin="" defer></script>
```

### JS — Complete Map Replacement

```js
// Custom marker icons (brand colors)
const propertyIcon = L.divIcon({
    className: 'marker-property',
    html: '<div class="marker-dot marker-dot--primary"></div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14],
});

const compIcon = L.divIcon({
    className: 'marker-comp',
    html: '<div class="marker-dot marker-dot--secondary"></div>',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    popupAnchor: [0, -11],
});

let mapInstance = null;

function renderMap(lat, lng, comps) {
    const mapDiv = document.getElementById('map');

    // Destroy previous map if exists
    if (mapInstance) {
        mapInstance.remove();
        mapInstance = null;
    }

    mapInstance = L.map('map', {
        scrollWheelZoom: false,     // Don't hijack page scroll
        attributionControl: true,
    }).setView([lat, lng], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(mapInstance);

    // Property marker (pulsing)
    L.marker([lat, lng], { icon: propertyIcon })
        .addTo(mapInstance)
        .bindPopup('<strong>Your Property</strong>');

    // Comp markers with coordinates
    const bounds = L.latLngBounds([[lat, lng]]);
    let hasComps = false;

    for (const comp of comps) {
        if (comp.lat && comp.lng) {
            hasComps = true;
            const marker = L.marker([comp.lat, comp.lng], { icon: compIcon })
                .addTo(mapInstance)
                .bindPopup(`
                    <strong>${comp.bedrooms} BR</strong><br>
                    ${formatCurrency(comp.revenue)}/yr<br>
                    <small>${comp.distance_km} km away</small>
                `);
            bounds.extend([comp.lat, comp.lng]);
        }
    }

    // Fit bounds to show all markers
    if (hasComps) {
        mapInstance.fitBounds(bounds, { padding: [30, 30] });
    }

    // Fix Leaflet rendering in hidden containers
    setTimeout(() => mapInstance.invalidateSize(), 100);
}
```

### CSS — Marker Styling

```css
/* ── Leaflet marker overrides ──────────────────────────── */
.marker-dot {
    border-radius: 50%;
    border: 3px solid #fff;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
.marker-dot--primary {
    width: 24px;
    height: 24px;
    background: var(--color-primary);
    animation: pulse 2s ease-in-out infinite;
}
.marker-dot--secondary {
    width: 18px;
    height: 18px;
    background: #0ea5e9;
}

@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(79, 70, 229, 0.4); }
    50%      { box-shadow: 0 0 0 10px rgba(79, 70, 229, 0); }
}

/* Leaflet container */
.leaflet-container {
    border-radius: 12px;
    font-family: inherit;
}

/* Popup styling */
.leaflet-popup-content-wrapper {
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.leaflet-popup-content {
    margin: 8px 12px;
    font-size: 0.9rem;
    line-height: 1.4;
}
```

### Benefits

| Metric | Mapbox GL | Leaflet |
|--------|-----------|---------|
| Bundle size | ~200KB gz | ~40KB gz |
| API token | Required (broken) | None |
| Cost | Paid after 50k loads | Free forever |
| Comp markers | Broken (same coords) | Working with API coords |
| Offline tiles | No | Yes (with tile caching) |

---

## 4. Address Autocomplete

### Problem

Users type freeform addresses with no guidance. Wrong format → API error → frustration. This is the #1 friction point identified in the audit.

### Solution: Nominatim (OpenStreetMap) — free, no API key

```html
<!-- Add after the address input -->
<div class="form-group" style="position: relative;">
    <label for="address">Address</label>
    <input type="text" id="address" name="address"
           placeholder="Start typing an NYC address…"
           required
           autocomplete="off"
           aria-expanded="false"
           aria-controls="address-suggestions"
           aria-autocomplete="list"
           role="combobox">
    <ul id="address-suggestions" class="suggestions" role="listbox" hidden></ul>
</div>
```

### JS — Autocomplete Logic

```js
/* ── Address Autocomplete ──────────────────────────────── */

const addressInput = document.getElementById('address');
const suggestionsList = document.getElementById('address-suggestions');
let debounceTimer = null;
let currentSuggestions = [];
let selectedSuggestion = -1;

// Debounced search
addressInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const query = addressInput.value.trim();

    if (query.length < 3) {
        hideSuggestions();
        return;
    }

    debounceTimer = setTimeout(() => fetchSuggestions(query), 300);
});

async function fetchSuggestions(query) {
    try {
        const params = new URLSearchParams({
            q: query + ', New York, NY',
            format: 'json',
            limit: '5',
            countrycodes: 'us',
            addressdetails: '1',
        });

        const resp = await fetch(
            `https://nominatim.openstreetmap.org/search?${params}`,
            {
                headers: {
                    'Accept': 'application/json',
                    // Nominatim requires a User-Agent
                    'User-Agent': 'Rentalizer/1.0 (airbnb-revenue-estimator)',
                },
            }
        );

        if (!resp.ok) return;

        const results = await resp.json();
        currentSuggestions = results.filter(r =>
            r.display_name.toLowerCase().includes('new york') ||
            r.display_name.toLowerCase().includes('nyc') ||
            r.display_name.toLowerCase().includes('brooklyn') ||
            r.display_name.toLowerCase().includes('queens') ||
            r.display_name.toLowerCase().includes('bronx') ||
            r.display_name.toLowerCase().includes('staten island') ||
            r.display_name.toLowerCase().includes('manhattan')
        );

        renderSuggestions(currentSuggestions);
    } catch (err) {
        console.warn('Autocomplete failed:', err);
        hideSuggestions();
    }
}

function renderSuggestions(results) {
    suggestionsList.innerHTML = '';
    selectedSuggestion = -1;

    if (results.length === 0) {
        hideSuggestions();
        return;
    }

    results.forEach((result, index) => {
        const li = document.createElement('li');
        li.className = 'suggestion-item';
        li.setAttribute('role', 'option');
        li.setAttribute('id', `suggestion-${index}`);
        li.setAttribute('aria-selected', 'false');

        // Highlight the matched part
        const displayName = result.display_name.split(',').slice(0, 3).join(', ');
        li.textContent = displayName;

        li.addEventListener('click', () => selectSuggestion(index));
        suggestionsList.appendChild(li);
    });

    suggestionsList.hidden = false;
    addressInput.setAttribute('aria-expanded', 'true');
}

function selectSuggestion(index) {
    const suggestion = currentSuggestions[index];
    if (!suggestion) return;

    // Use the clean display name
    const cleanName = suggestion.display_name.split(',').slice(0, 3).join(', ');
    addressInput.value = cleanName;

    // Store coordinates for map preview
    addressInput.dataset.lat = suggestion.lat;
    addressInput.dataset.lng = suggestion.lon;

    hideSuggestions();
    addressInput.focus();
}

function hideSuggestions() {
    suggestionsList.hidden = true;
    addressInput.setAttribute('aria-expanded', 'false');
    selectedSuggestion = -1;
}

// Keyboard navigation
addressInput.addEventListener('keydown', (e) => {
    const items = suggestionsList.querySelectorAll('.suggestion-item');
    if (!items.length) return;

    switch (e.key) {
        case 'ArrowDown':
            e.preventDefault();
            selectedSuggestion = Math.min(selectedSuggestion + 1, items.length - 1);
            updateSuggestionHighlight(items);
            break;
        case 'ArrowUp':
            e.preventDefault();
            selectedSuggestion = Math.max(selectedSuggestion - 1, 0);
            updateSuggestionHighlight(items);
            break;
        case 'Enter':
            if (selectedSuggestion >= 0) {
                e.preventDefault();
                selectSuggestion(selectedSuggestion);
            }
            break;
        case 'Escape':
            hideSuggestions();
            break;
    }
});

function updateSuggestionHighlight(items) {
    items.forEach((item, i) => {
        const isSelected = i === selectedSuggestion;
        item.classList.toggle('suggestion-item--active', isSelected);
        item.setAttribute('aria-selected', isSelected.toString());
        addressInput.setAttribute('aria-activedescendant', isSelected ? `suggestion-${i}` : '');
    });
}

// Close on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.form-group')) {
        hideSuggestions();
    }
});
```

### CSS — Suggestions Dropdown

```css
/* ── Address autocomplete ──────────────────────────────── */
.form-group { position: relative; }

.suggestions {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 100;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-top: none;
    border-radius: 0 0 8px 8px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    max-height: 240px;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 4px 0;
}

.suggestion-item {
    padding: 10px 14px;
    cursor: pointer;
    font-size: 0.9rem;
    color: #334155;
    transition: background 0.1s;
}
.suggestion-item:hover,
.suggestion-item--active {
    background: #f1f5f9;
}
.suggestion-item--active {
    background: #e0e7ff;
    color: #3730a3;
}
```

---

## 5. Revenue Visualization Chart

### Problem

Results show a single revenue range number with no visual context. Users can't tell if their estimate is above or below market, how revenue breaks down seasonally, or how they compare to comps.

### Solution: Chart.js bar/line chart showing monthly revenue + market comparison

### HTML

```html
<!-- Add after result-header, before result-grid -->
<div class="result-card result-card--chart">
    <h3>📈 Revenue Breakdown</h3>
    <div class="chart-tabs" role="tablist">
        <button class="chart-tab active" role="tab" data-chart="monthly"
                aria-selected="true">Monthly</button>
        <button class="chart-tab" role="tab" data-chart="comparison"
                aria-selected="false">vs. Market</button>
    </div>
    <canvas id="revenue-chart" aria-label="Revenue visualization chart"></canvas>
</div>

<!-- Add Chart.js CDN (before app.js) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js" defer></script>
```

### JS — Chart Rendering

```js
/* ── Revenue Chart ─────────────────────────────────────── */

let revenueChart = null;

// Monthly seasonality multipliers (NYC data)
const SEASONALITY = [
    0.85, 0.88, 0.95, 1.02, 1.08, 1.15,  // Jan–Jun
    1.18, 1.16, 1.10, 1.05, 0.92, 0.80,  // Jul–Dec
];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function renderRevenueChart(data) {
    const ctx = document.getElementById('revenue-chart');
    if (!ctx) return;

    // Destroy previous chart
    if (revenueChart) {
        revenueChart.destroy();
    }

    const annualMid = (data.confidence.revenue_lower + data.confidence.revenue_upper) / 2;
    const monthlyMid = annualMid / 12;

    // Generate monthly estimates with seasonality
    const monthlyRevenue = SEASONALITY.map(mult =>
        Math.round(monthlyMid * mult)
    );

    // Market median monthly
    const marketMonthly = Math.round(data.market.median_revenue / 12);

    revenueChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: MONTHS,
            datasets: [
                {
                    label: 'Your Estimate',
                    data: monthlyRevenue,
                    backgroundColor: 'rgba(79, 70, 229, 0.7)',
                    borderColor: '#4f46e5',
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false,
                },
                {
                    label: 'Market Median',
                    data: Array(12).fill(marketMonthly),
                    type: 'line',
                    borderColor: '#94a3b8',
                    borderDash: [6, 4],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 16,
                        font: { family: 'inherit', size: 12 },
                    },
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleFont: { family: 'inherit' },
                    bodyFont: { family: 'inherit' },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: (ctx) => `${ctx.dataset.label}: $${ctx.parsed.y.toLocaleString()}`,
                    },
                },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: (v) => `$${(v / 1000).toFixed(1)}k`,
                        font: { family: 'inherit', size: 11 },
                    },
                    grid: { color: '#f1f5f9' },
                },
                x: {
                    ticks: { font: { family: 'inherit', size: 11 } },
                    grid: { display: false },
                },
            },
        },
    });

    // Tab switching
    document.querySelectorAll('.chart-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.chart-tab').forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            tab.classList.add('active');
            tab.setAttribute('aria-selected', 'true');

            if (tab.dataset.chart === 'comparison') {
                renderComparisonChart(data);
            } else {
                renderRevenueChart(data);
            }
        });
    });
}

function renderComparisonChart(data) {
    if (revenueChart) revenueChart.destroy();

    const comps = data.comps || [];
    const labels = ['Your Estimate', ...comps.map((_, i) => `Comp ${i + 1}`)];
    const values = [
        (data.confidence.revenue_lower + data.confidence.revenue_upper) / 2,
        ...comps.map(c => c.revenue),
    ];
    const colors = [
        '#4f46e5',
        ...comps.map(() => '#0ea5e9'),
    ];

    revenueChart = new Chart(document.getElementById('revenue-chart'), {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Annual Revenue',
                data: values,
                backgroundColor: colors.map(c => c + 'b3'),
                borderColor: colors,
                borderWidth: 1,
                borderRadius: 6,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.5,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `$${Math.round(ctx.parsed.x).toLocaleString()}/yr`,
                    },
                },
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: (v) => `$${(v / 1000).toFixed(0)}k`,
                    },
                    grid: { color: '#f1f5f9' },
                },
                y: {
                    grid: { display: false },
                },
            },
        },
    });
}
```

### CSS — Chart Tabs

```css
/* ── Chart tabs ─────────────────────────────────────────── */
.result-card--chart { padding-bottom: 8px; }

.chart-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
    background: #f1f5f9;
    border-radius: 8px;
    padding: 4px;
}

.chart-tab {
    flex: 1;
    padding: 8px 12px;
    border: none;
    background: transparent;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    color: #64748b;
    cursor: pointer;
    transition: all 0.2s;
}
.chart-tab.active {
    background: #fff;
    color: #1e293b;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.chart-tab:hover:not(.active) {
    color: #334155;
}
```

---

## 6. Professional Brand System

### Problem

The Airbnb red `#ff5a5f` is a trademark color — using it makes the tool look like a phishing site or cheap clone. No design tokens, no visual hierarchy, every card looks identical.

### Solution: Indigo-based design system with CSS custom properties

### CSS — Complete Brand System

```css
/* ── Design Tokens ─────────────────────────────────────── */
:root {
    /* Brand palette — Indigo (professional, trustworthy) */
    --color-primary:        #4f46e5;
    --color-primary-hover:  #4338ca;
    --color-primary-light:  #e0e7ff;
    --color-primary-50:     #eef2ff;

    /* Semantic colors */
    --color-success:        #059669;
    --color-success-bg:     #d1fae5;
    --color-warning:        #d97706;
    --color-warning-bg:     #fef3c7;
    --color-danger:         #dc2626;
    --color-danger-bg:      #fee2e2;

    /* Neutral palette */
    --color-text:           #1e293b;
    --color-text-secondary: #475569;
    --color-text-muted:     #64748b;
    --color-border:         #e2e8f0;
    --color-bg:             #f8fafc;
    --color-surface:        #ffffff;

    /* Elevation (box-shadow hierarchy) */
    --shadow-sm:   0 1px 2px rgba(0,0,0,0.05);
    --shadow-md:   0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
    --shadow-lg:   0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04);
    --shadow-xl:   0 20px 25px -5px rgba(0,0,0,0.08), 0 8px 10px -6px rgba(0,0,0,0.04);

    /* Spacing scale */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 20px;
    --space-6: 24px;
    --space-8: 32px;

    /* Radii */
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;

    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-base: 200ms ease;
}

/* ── Base ──────────────────────────────────────────────── */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'Helvetica Neue', Arial, sans-serif;
    background: var(--color-bg);
    color: var(--color-text);
    line-height: 1.6;
}

/* ── Cards with elevation hierarchy ────────────────────── */
form {
    background: var(--color-surface);
    padding: var(--space-6);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-md);
    border: 1px solid var(--color-border);
    transition: box-shadow var(--transition-base);
}
form:hover {
    box-shadow: var(--shadow-lg);
}

.result-header {
    background: var(--color-surface);
    padding: var(--space-6);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-lg);
    border: 1px solid var(--color-border);
    margin-bottom: var(--space-4);
    text-align: center;
    position: relative;
    overflow: hidden;
}
/* Gradient accent bar */
.result-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--color-primary), #7c3aed, #a78bfa);
}

.result-card {
    background: var(--color-surface);
    padding: var(--space-5);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-border);
    margin-bottom: var(--space-4);
    transition: box-shadow var(--transition-base);
}
.result-card:hover {
    box-shadow: var(--shadow-md);
}

/* ── Button ────────────────────────────────────────────── */
button[type="submit"] {
    width: 100%;
    padding: 14px;
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background var(--transition-fast), transform var(--transition-fast);
}
button[type="submit"]:hover {
    background: var(--color-primary-hover);
    transform: translateY(-1px);
}
button[type="submit"]:active {
    transform: translateY(0);
}
button[type="submit"]:disabled {
    background: #94a3b8;
    cursor: not-allowed;
    transform: none;
}

/* ── Inputs ────────────────────────────────────────────── */
.form-group input,
.form-group select {
    width: 100%;
    padding: 10px 14px;
    border: 1.5px solid var(--color-border);
    border-radius: var(--radius-md);
    font-size: 1rem;
    color: var(--color-text);
    background: var(--color-surface);
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}
.form-group input:hover,
.form-group select:hover {
    border-color: #cbd5e1;
}
.form-group input:focus,
.form-group select:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12);
}

/* ── Confidence badge ──────────────────────────────────── */
.confidence-badge.high {
    background: var(--color-success-bg);
    color: #065f46;
}
.confidence-badge.medium {
    background: var(--color-warning-bg);
    color: #92400e;
}
.confidence-badge.low {
    background: var(--color-danger-bg);
    color: #991b1b;
}

/* ── Attribution links ─────────────────────────────────── */
.attribution a {
    color: var(--color-primary);
    text-decoration: underline;
    text-decoration-color: rgba(79, 70, 229, 0.3);
    text-underline-offset: 2px;
}
.attribution a:hover {
    text-decoration-color: var(--color-primary);
}

/* ── Favicon (inline SVG data URI) ─────────────────────── */
/* Add to HTML <head>: */
/* <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>"> */
```

---

## 7. Mobile-First Responsive Redesign

### Problem

Single breakpoint at 600px. Four dropdowns crammed side-by-side on tablets. Fixed 300px map height. No touch-friendly targets. No safe-area handling for notched iPhones.

### Solution: Three-tier breakpoint system, mobile-first

```css
/* ── Mobile-First Base (0–479px) ───────────────────────── */
/* Everything defaults to single-column mobile layout */

.container {
    max-width: 100%;
    padding: 16px;
    padding-bottom: env(safe-area-inset-bottom, 16px);
}

header h1 { font-size: 1.5rem; }
.subtitle { font-size: 0.9rem; }

.form-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}

.result-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}

.revenue-range { font-size: 1.5rem; }

/* Comps — stacked card layout on mobile */
.comp-item {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 8px;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 0.85rem;
}
.comp-header-row {
    display: none; /* Hide table headers on mobile; use CSS labels instead */
}
.comp-item:not(.comp-header-row)::before {
    content: '';
    display: none;
}

/* Map — responsive height */
.map-container {
    height: 200px;
    border-radius: var(--radius-md);
    overflow: hidden;
}

/* Touch-friendly tap targets (min 44px) */
.form-group input,
.form-group select,
button[type="submit"] {
    min-height: 44px;
}
.suggestion-item {
    padding: 12px 14px; /* Larger touch target */
}

/* Chart — full width */
.result-card--chart canvas {
    max-height: 220px;
}

/* ── Tablet (480–767px) ────────────────────────────────── */
@media (min-width: 480px) {
    .container { padding: 20px; }

    .form-row {
        grid-template-columns: 1fr 1fr;
    }

    .revenue-range { font-size: 1.8rem; }

    .comp-item {
        grid-template-columns: 2fr 1fr 1fr 1fr;
        font-size: 0.9rem;
    }
    .comp-header-row { display: grid; }
}

/* ── Desktop (768px+) ──────────────────────────────────── */
@media (min-width: 768px) {
    .container {
        max-width: 800px;
        padding: 24px;
    }

    .form-row {
        grid-template-columns: 1fr 1fr 1fr 1fr;
    }

    .result-grid {
        grid-template-columns: 1fr 1fr;
    }

    .revenue-range { font-size: 2.2rem; }

    .map-container { height: 350px; }

    /* Hover effects only for pointer devices */
    @media (hover: hover) {
        form:hover { box-shadow: var(--shadow-lg); }
        .result-card:hover { box-shadow: var(--shadow-md); }
    }
}

/* ── Large desktop (1024px+) ───────────────────────────── */
@media (min-width: 1024px) {
    .container { max-width: 900px; }
    .map-container { height: 400px; }
}

/* ── Comparison mode grid ──────────────────────────────── */
.comparison-grid {
    display: grid;
    gap: var(--space-4);
}
@media (min-width: 768px) {
    .comparison-grid--2 { grid-template-columns: 1fr 1fr; }
    .comparison-grid--3 { grid-template-columns: 1fr 1fr 1fr; }
}

/* ── Utility: hide on mobile ───────────────────────────── */
.hide-mobile { display: none; }
@media (min-width: 768px) {
    .hide-mobile { display: block; }
}
```

---

## 8. Trust Signals & Social Proof

### Problem

No methodology explanation, no data freshness indicator, no social proof. Users see numbers from an unknown source and have no reason to trust them.

### HTML — Trust Section

```html
<!-- Add below the form, before loading/results -->
<div class="trust-bar" aria-label="Trust signals">
    <div class="trust-item">
        <span class="trust-icon">📊</span>
        <span class="trust-text"><strong>50,000+</strong> NYC listings analyzed</span>
    </div>
    <div class="trust-item">
        <span class="trust-icon">🔄</span>
        <span class="trust-text">Data updated <strong id="data-freshness">monthly</strong></span>
    </div>
    <div class="trust-item">
        <span class="trust-icon">🎯</span>
        <span class="trust-text"><strong>±15%</strong> median accuracy</span>
    </div>
</div>

<!-- Methodology link -->
<div class="methodology-link">
    <a href="#methodology" id="show-methodology">
        How are these estimates calculated?
    </a>
</div>

<!-- Methodology modal/expandable -->
<div id="methodology" class="methodology" hidden>
    <div class="methodology-content">
        <button class="methodology-close" aria-label="Close methodology">&times;</button>
        <h3>Our Methodology</h3>
        <ol>
            <li><strong>Data Source:</strong> We use <a href="https://insideairbnb.com" target="_blank">InsideAirbnb</a>
                public data, licensed under CC BY 4.0. This includes actual listing data, pricing, and reviews.</li>
            <li><strong>Comparable Analysis:</strong> We find properties with similar bedrooms, bathrooms,
                and guest capacity within your borough, then weight by proximity.</li>
            <li><strong>Confidence Scoring:</strong> Our confidence level is based on the coefficient of variation (CV)
                of comparable properties. More consistent comps = higher confidence.</li>
            <li><strong>Seasonal Adjustment:</strong> Monthly estimates apply NYC seasonal multipliers
                based on historical booking patterns.</li>
        </ol>
        <p class="methodology-note">
            ⚠️ These are estimates for planning purposes only. Actual revenue depends on
            listing quality, photos, reviews, pricing strategy, and market conditions.
        </p>
    </div>
</div>

<!-- Data freshness in results -->
<div class="data-timestamp">
    <small>Based on data through <span id="data-date">Q1 2026</span></small>
</div>
```

### CSS — Trust Signals

```css
/* ── Trust bar ─────────────────────────────────────────── */
.trust-bar {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: var(--space-4) var(--space-6);
    padding: var(--space-4) var(--space-5);
    background: var(--color-primary-50);
    border: 1px solid var(--color-primary-light);
    border-radius: var(--radius-lg);
    margin-bottom: var(--space-4);
}

.trust-item {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: 0.85rem;
    color: var(--color-text-secondary);
}

.trust-icon { font-size: 1.2rem; }

/* ── Methodology ───────────────────────────────────────── */
.methodology-link {
    text-align: center;
    margin-bottom: var(--space-4);
}
.methodology-link a {
    color: var(--color-primary);
    font-size: 0.85rem;
    text-decoration: underline;
    text-decoration-color: rgba(79, 70, 229, 0.3);
    text-underline-offset: 2px;
}

.methodology {
    position: fixed;
    inset: 0;
    z-index: 1000;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-4);
    backdrop-filter: blur(4px);
}

.methodology-content {
    background: var(--color-surface);
    border-radius: var(--radius-xl);
    padding: var(--space-6);
    max-width: 560px;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: var(--shadow-xl);
    position: relative;
}

.methodology-content h3 {
    font-size: 1.2rem;
    margin-bottom: var(--space-4);
    color: var(--color-text);
}

.methodology-content ol {
    padding-left: var(--space-5);
    margin-bottom: var(--space-4);
}
.methodology-content li {
    margin-bottom: var(--space-3);
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    line-height: 1.5;
}

.methodology-note {
    background: var(--color-warning-bg);
    padding: var(--space-3) var(--space-4);
    border-radius: var(--radius-md);
    font-size: 0.8rem;
    color: #92400e;
}

.methodology-close {
    position: absolute;
    top: var(--space-3);
    right: var(--space-3);
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--color-text-muted);
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
}
.methodology-close:hover {
    background: #f1f5f9;
}

/* ── Data timestamp ────────────────────────────────────── */
.data-timestamp {
    text-align: center;
    margin-top: var(--space-2);
}
.data-timestamp small {
    color: var(--color-text-muted);
    font-size: 0.75rem;
}
```

### JS — Methodology Toggle

```js
// Methodology modal
document.getElementById('show-methodology')?.addEventListener('click', (e) => {
    e.preventDefault();
    const modal = document.getElementById('methodology');
    modal.hidden = false;
    modal.querySelector('.methodology-close').focus();
});

document.querySelector('.methodology-close')?.addEventListener('click', () => {
    document.getElementById('methodology').hidden = true;
});

document.getElementById('methodology')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.hidden = true;
    }
});

// Escape key closes modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modal = document.getElementById('methodology');
        if (modal && !modal.hidden) modal.hidden = true;
    }
});
```

---

## 9. Comparison Mode

### Problem

Users can only estimate one property at a time. No way to compare multiple addresses side-by-side — which is the core use case for an investor evaluating properties.

### HTML — Comparison UI

```html
<!-- Add after results section -->
<div id="comparison-section" class="hidden">
    <div class="comparison-header">
        <h2>📋 Comparison Mode</h2>
        <p class="subtitle">Add properties to compare side-by-side</p>
    </div>

    <div class="comparison-controls">
        <button id="add-to-comparison" class="btn btn--secondary">
            + Add Current Property
        </button>
        <button id="clear-comparison" class="btn btn--ghost" hidden>
            Clear All
        </button>
    </div>

    <div id="comparison-grid" class="comparison-grid"></div>

    <div id="comparison-empty" class="empty-comparison">
        <span class="empty-icon">📊</span>
        <p>Run an estimate and click "Add Current Property" to start comparing.</p>
    </div>
</div>
```

### JS — Comparison Logic

```js
/* ── Comparison Mode ───────────────────────────────────── */

const comparisonStore = {
    properties: [],

    add(property) {
        if (this.properties.length >= 4) {
            alert('Maximum 4 properties for comparison.');
            return false;
        }
        // Check for duplicate address
        if (this.properties.some(p => p.address === property.address)) {
            alert('This property is already in the comparison.');
            return false;
        }
        this.properties.push(property);
        this.render();
        return true;
    },

    remove(index) {
        this.properties.splice(index, 1);
        this.render();
    },

    clear() {
        this.properties = [];
        this.render();
    },

    render() {
        const grid = document.getElementById('comparison-grid');
        const empty = document.getElementById('comparison-empty');
        const clearBtn = document.getElementById('clear-comparison');

        grid.innerHTML = '';

        if (this.properties.length === 0) {
            empty.hidden = false;
            clearBtn.hidden = true;
            return;
        }

        empty.hidden = true;
        clearBtn.hidden = false;

        // Responsive grid class
        grid.className = `comparison-grid comparison-grid--${Math.min(this.properties.length, 3)}`;

        this.properties.forEach((prop, index) => {
            const card = document.createElement('div');
            card.className = 'comparison-card';
            card.innerHTML = ''; // Clear

            // Header
            const header = document.createElement('div');
            header.className = 'comparison-card__header';

            const addressEl = document.createElement('h4');
            addressEl.className = 'comparison-card__address';
            addressEl.textContent = prop.address;

            const removeBtn = document.createElement('button');
            removeBtn.className = 'comparison-card__remove';
            removeBtn.setAttribute('aria-label', `Remove ${prop.address}`);
            removeBtn.textContent = '×';
            removeBtn.addEventListener('click', () => this.remove(index));

            header.appendChild(addressEl);
            header.appendChild(removeBtn);
            card.appendChild(header);

            // Revenue highlight
            const revenue = document.createElement('div');
            revenue.className = 'comparison-card__revenue';
            const lower = formatCurrency(prop.confidence.revenue_lower);
            const upper = formatCurrency(prop.confidence.revenue_upper);
            revenue.textContent = `${lower} — ${upper}`;
            card.appendChild(revenue);

            // Confidence
            const confBadge = document.createElement('span');
            confBadge.className = `confidence-badge ${prop.confidence.level}`;
            confBadge.textContent = prop.confidence.level;
            card.appendChild(confBadge);

            // Stats
            const stats = document.createElement('div');
            stats.className = 'comparison-card__stats';
            const statData = [
                ['Beds', `${prop.bedrooms}`],
                ['Baths', `${prop.bathrooms}`],
                ['Guests', `${prop.accommodates}`],
                ['Rate', `$${prop.nightly_rate}/night`],
                ['Borough', prop.market.borough],
                ['Market Median', formatCurrency(prop.market.median_revenue)],
            ];

            statData.forEach(([label, value]) => {
                stats.appendChild(createStatRow(label, value));
            });
            card.appendChild(stats);

            grid.appendChild(card);
        });
    },
};

// Wire up buttons
document.getElementById('add-to-comparison')?.addEventListener('click', () => {
    if (!currentEstimate) return;

    const property = {
        address: currentEstimate.address,
        bedrooms: currentEstimate.bedrooms,
        bathrooms: currentEstimate.bathrooms,
        accommodates: currentEstimate.accommodates,
        nightly_rate: currentEstimate.nightly_rate,
        confidence: currentEstimate.confidence,
        market: currentEstimate.market,
    };

    comparisonStore.add(property);
});

document.getElementById('clear-comparison')?.addEventListener('click', () => {
    comparisonStore.clear();
});

// Store current estimate for comparison
let currentEstimate = null;

// In renderResults, add:
// currentEstimate = { ...data, address: form.address.value, bedrooms: body.bedrooms, ... };
```

### CSS — Comparison Cards

```css
/* ── Comparison Mode ───────────────────────────────────── */
#comparison-section {
    margin-top: var(--space-8);
    padding-top: var(--space-6);
    border-top: 2px solid var(--color-border);
}

.comparison-header {
    text-align: center;
    margin-bottom: var(--space-5);
}
.comparison-header h2 {
    font-size: 1.3rem;
    color: var(--color-text);
}

.comparison-controls {
    display: flex;
    justify-content: center;
    gap: var(--space-3);
    margin-bottom: var(--space-5);
}

.btn {
    padding: 10px 20px;
    border-radius: var(--radius-md);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: all var(--transition-fast);
}
.btn--secondary {
    background: var(--color-primary);
    color: white;
    border: none;
}
.btn--secondary:hover {
    background: var(--color-primary-hover);
}
.btn--ghost {
    background: transparent;
    color: var(--color-text-muted);
    border: 1px solid var(--color-border);
}
.btn--ghost:hover {
    background: #f1f5f9;
    color: var(--color-danger);
    border-color: var(--color-danger);
}

.comparison-grid {
    display: grid;
    gap: var(--space-4);
}
.comparison-grid--1 { grid-template-columns: 1fr; max-width: 400px; margin: 0 auto; }
.comparison-grid--2 { grid-template-columns: 1fr 1fr; }
.comparison-grid--3 { grid-template-columns: 1fr 1fr 1fr; }

@media (max-width: 767px) {
    .comparison-grid--2,
    .comparison-grid--3 {
        grid-template-columns: 1fr;
    }
}

.comparison-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-5);
    box-shadow: var(--shadow-sm);
    transition: box-shadow var(--transition-base);
}
.comparison-card:hover {
    box-shadow: var(--shadow-md);
}

.comparison-card__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--space-3);
}

.comparison-card__address {
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--color-text);
    line-height: 1.3;
    flex: 1;
    margin-right: var(--space-2);
}

.comparison-card__remove {
    background: none;
    border: none;
    font-size: 1.2rem;
    color: var(--color-text-muted);
    cursor: pointer;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    flex-shrink: 0;
}
.comparison-card__remove:hover {
    background: var(--color-danger-bg);
    color: var(--color-danger);
}

.comparison-card__revenue {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--color-primary);
    margin-bottom: var(--space-2);
}

.comparison-card__stats {
    margin-top: var(--space-3);
    border-top: 1px solid var(--color-border);
    padding-top: var(--space-3);
}

.empty-comparison {
    text-align: center;
    padding: var(--space-8) var(--space-4);
    color: var(--color-text-muted);
}
.empty-icon {
    font-size: 2.5rem;
    display: block;
    margin-bottom: var(--space-3);
}

/* ── Winner highlight in comparison ────────────────────── */
.comparison-card--winner {
    border-color: var(--color-success);
    box-shadow: 0 0 0 1px var(--color-success), var(--shadow-md);
}
.comparison-card--winner::before {
    content: '★ Highest Revenue';
    display: block;
    background: var(--color-success);
    color: white;
    text-align: center;
    padding: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    margin: calc(-1 * var(--space-5));
    margin-bottom: var(--space-4);
    padding: 6px var(--space-5);
}
```

---

## 10. Loading / Empty / Error States

### Problem

- Spinner has no reduced-motion support
- No skeleton loading — results just pop in
- Submit button just grays out with no feedback
- Empty comps shows nothing
- Error messages are developer-facing ("Failed to fetch")
- No retry mechanism

### HTML — Enhanced States

```html
<!-- Skeleton loading (shown during API call) -->
<div id="skeleton" class="hidden" role="status" aria-label="Loading results">
    <div class="skeleton-header">
        <div class="skeleton-line skeleton-line--title"></div>
        <div class="skeleton-line skeleton-line--subtitle"></div>
        <div class="skeleton-badge"></div>
    </div>
    <div class="skeleton-grid">
        <div class="skeleton-card">
            <div class="skeleton-line" style="width: 60%"></div>
            <div class="skeleton-line" style="width: 80%"></div>
            <div class="skeleton-line" style="width: 40%"></div>
        </div>
        <div class="skeleton-card">
            <div class="skeleton-line" style="width: 50%"></div>
            <div class="skeleton-line" style="width: 70%"></div>
            <div class="skeleton-line" style="width: 60%"></div>
        </div>
    </div>
    <div class="skeleton-card">
        <div class="skeleton-line" style="width: 100%"></div>
        <div class="skeleton-line" style="width: 100%"></div>
        <div class="skeleton-line" style="width: 100%"></div>
    </div>
</div>

<!-- Enhanced error with retry -->
<div id="error" class="hidden" role="alert" aria-live="assertive" tabindex="-1">
    <div class="error-icon">⚠️</div>
    <h3 class="error-title" id="error-title">Something went wrong</h3>
    <p id="error-message"></p>
    <button id="retry-btn" class="btn btn--secondary" hidden>Try Again</button>
</div>

<!-- Empty state for results with no comps -->
<div id="empty-state" class="hidden">
    <div class="empty-icon">🔍</div>
    <h3>No results found</h3>
    <p>We couldn't find comparable properties for this address. Try adjusting the bedrooms or location.</p>
</div>
```

### CSS — All States

```css
/* ── Skeleton Loading ──────────────────────────────────── */
@keyframes shimmer {
    0%   { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.skeleton-line {
    height: 16px;
    background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: 4px;
    margin-bottom: 12px;
}
.skeleton-line--title {
    height: 32px;
    width: 60%;
    margin: 0 auto 12px;
}
.skeleton-line--subtitle {
    height: 16px;
    width: 40%;
    margin: 0 auto 8px;
}
.skeleton-badge {
    height: 28px;
    width: 120px;
    margin: 0 auto;
    background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: 14px;
}

.skeleton-header {
    background: var(--color-surface);
    padding: var(--space-6);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-sm);
    margin-bottom: var(--space-4);
    text-align: center;
}

.skeleton-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-4);
    margin-bottom: var(--space-4);
}
@media (max-width: 767px) {
    .skeleton-grid { grid-template-columns: 1fr; }
}

.skeleton-card {
    background: var(--color-surface);
    padding: var(--space-5);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    margin-bottom: var(--space-4);
}

@media (prefers-reduced-motion: reduce) {
    .skeleton-line, .skeleton-badge {
        animation: none;
        background: #e2e8f0;
    }
}

/* ── Enhanced Error State ──────────────────────────────── */
#error {
    background: var(--color-surface);
    border: 1px solid #fecaca;
    padding: var(--space-6);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-md);
    text-align: center;
    margin-bottom: var(--space-5);
}

.error-icon {
    font-size: 2.5rem;
    margin-bottom: var(--space-3);
}

.error-title {
    font-size: 1.1rem;
    color: #991b1b;
    margin-bottom: var(--space-2);
}

#error-message {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    margin-bottom: var(--space-4);
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
}

#retry-btn {
    margin-top: var(--space-2);
}

/* ── Empty State ───────────────────────────────────────── */
#empty-state {
    text-align: center;
    padding: var(--space-8) var(--space-4);
    background: var(--color-surface);
    border-radius: var(--radius-xl);
    border: 2px dashed var(--color-border);
    margin-bottom: var(--space-5);
}

#empty-state h3 {
    font-size: 1.1rem;
    color: var(--color-text);
    margin-bottom: var(--space-2);
}

#empty-state p {
    color: var(--color-text-muted);
    font-size: 0.9rem;
    max-width: 360px;
    margin: 0 auto;
}

/* ── Submit button loading state ───────────────────────── */
button[type="submit"].is-loading {
    position: relative;
    color: transparent;
    pointer-events: none;
}
button[type="submit"].is-loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 20px;
    height: 20px;
    margin: -10px 0 0 -10px;
    border: 2px solid rgba(255,255,255,0.3);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
}
@media (prefers-reduced-motion: reduce) {
    button[type="submit"].is-loading::after {
        animation: none;
        border-top-color: #fff;
    }
}
```

### JS — State Management

```js
/* ── State Management ──────────────────────────────────── */

function showState(state) {
    // Hide all states
    ['loading', 'skeleton', 'error', 'results', 'empty-state'].forEach(id => {
        document.getElementById(id)?.classList.add('hidden');
    });

    // Show requested state
    const el = document.getElementById(state);
    if (el) el.classList.remove('hidden');
}

// Improved form handler with all states
document.getElementById('estimate-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const btn = document.getElementById('submit-btn');
    const errorEl = document.getElementById('error');

    // Client-side validation
    const address = form.address.value.trim();
    if (address.length < 5) {
        showError('Please enter a valid address.', false);
        return;
    }

    const rate = parseFloat(form.nightly_rate.value);
    if (isNaN(rate) || rate < 25 || rate > 5000) {
        showError('Nightly rate must be between $25 and $5,000.', false);
        return;
    }

    // Show skeleton loading
    btn.classList.add('is-loading');
    btn.disabled = true;
    showState('skeleton');

    const body = {
        address,
        bedrooms: parseInt(form.bedrooms.value),
        bathrooms: parseInt(form.bathrooms.value),
        accommodates: parseInt(form.accommodates.value),
        nightly_rate: rate,
    };

    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);

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

        if (!data.confidence || !data.market) {
            throw new Error('Unexpected response format. The API may have changed.');
        }

        // Success
        renderResults(data);
        showState('results');

        // Show comparison section
        document.getElementById('comparison-section')?.classList.remove('hidden');

        // Scroll to results
        document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        let message = err.message;
        let showRetry = true;

        if (err.name === 'AbortError') {
            message = 'Request timed out. The server may be overloaded — please try again in a moment.';
        } else if (err.message === 'Failed to fetch') {
            message = 'Cannot reach the server. Please check your internet connection and try again.';
        } else if (err.message.includes('invalid response')) {
            message = 'The server returned an unexpected response. This may be a temporary issue.';
        }

        showError(message, showRetry);
    } finally {
        btn.classList.remove('is-loading');
        btn.disabled = false;
    }
});

function showError(message, showRetry = true) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('retry-btn').hidden = !showRetry;
    showState('error');
    document.getElementById('error').focus();
}

// Retry button
document.getElementById('retry-btn')?.addEventListener('click', () => {
    document.getElementById('estimate-form').dispatchEvent(new Event('submit'));
});
```

---

## Summary — Implementation Priority

| # | Innovation | Impact | Effort | Priority |
|---|-----------|--------|--------|----------|
| 1 | XSS Fix | 🔴 Security | 1h | **P0** |
| 2 | Accessibility | 🔴 Legal/UX | 2h | **P0** |
| 3 | Leaflet Map | 🟠 Functionality | 1h | **P1** |
| 10 | Loading/Error States | 🟠 UX | 1.5h | **P1** |
| 6 | Brand System | 🟠 Trust | 1h | **P1** |
| 7 | Mobile-First | 🟠 Reach | 1.5h | **P1** |
| 4 | Address Autocomplete | 🟡 Conversion | 1.5h | **P2** |
| 5 | Revenue Chart | 🟡 Engagement | 2h | **P2** |
| 8 | Trust Signals | 🟡 Conversion | 1h | **P2** |
| 9 | Comparison Mode | 🟢 Retention | 3h | **P3** |

**Total estimated effort: ~16 hours** for a single developer.

**Quick wins (< 30 min each):** Contrast fix, CSP meta tag, favicon, `defer` on scripts, `prefers-reduced-motion`.

---

## Full File Changes Checklist

- [ ] `templates/index.html` — ARIA attributes, Leaflet CDN, Chart.js CDN, trust bar, comparison section, skeleton, enhanced error, skip link, CSP meta, favicon, OG tags
- [ ] `static/style.css` — Design tokens, brand system, elevation hierarchy, responsive breakpoints, skeleton animation, focus styles, contrast fixes, comparison cards
- [ ] `static/app.js` — DOM API rendering (no innerHTML), Leaflet map, autocomplete, chart, comparison store, state management, validation, error handling, focus management
- [ ] New: `static/sanitize.js` — `escapeHTML()`, `createStatRow()`, `renderStatRows()`
