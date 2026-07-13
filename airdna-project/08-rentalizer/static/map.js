// AIRWORTHY — Market Map
// The map is the interface: a compact top rail replaces the old sidebar,
// one analytical layer is active at a time, and markers are colored on a
// continuous coral→blue→lime scale instead of clustered black bubbles.

// ─── Map setup ────────────────────────────────────────────────────────────
const WORLD_BOUNDS = [[-85, -220], [85, 220]];
const map = L.map('map', {
    zoomControl: false,
    maxBounds: WORLD_BOUNDS,
    maxBoundsViscosity: 1.0,
    minZoom: 3,
}).setView([36.5, -119.5], 6);

L.control.zoom({ position: 'topright' }).addTo(map);

// Light basemap with dark charcoal price-pill badges, matching the
// reference's map panel (light tiles, $-badges with a colored indicator).
L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png',
    {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
    }
).addTo(map);

// A plain LayerGroup — no clustering. At low zoom we render aggregated
// "market field" cells; at high zoom we render individual property dots.
const markerLayer = L.layerGroup().addTo(map);
const markerById = new Map(); // listing id -> {marker, listing}

// ─── State ────────────────────────────────────────────────────────────────
let debounceTimer = null;
let currentController = null;
let lastRequestId = 0;
let currentListings = [];
let activeLayer = 'revenue';
let selectedId = null;
// null = full-year average; 0-11 = a specific calendar month (Jan..Dec).
let activeMonth = null;

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// ─── Color scale: coral (low) → blue (mid) → lime (high) ──────────────────
function hexToRgb(hex) {
    const n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
const CORAL = hexToRgb('#FF6350');
const BLUE  = hexToRgb('#2A55FF');
const LIME  = hexToRgb('#C6F135');

function lerp(a, b, t) { return a + (b - a) * t; }

function colorForT(t) {
    t = Math.max(0, Math.min(1, t));
    const [c1, c2] = t < 0.5 ? [CORAL, BLUE] : [BLUE, LIME];
    const localT = t < 0.5 ? t / 0.5 : (t - 0.5) / 0.5;
    const r = Math.round(lerp(c1[0], c2[0], localT));
    const g = Math.round(lerp(c1[1], c2[1], localT));
    const b = Math.round(lerp(c1[2], c2[2], localT));
    return `rgb(${r},${g},${b})`;
}

// ─── Derived per-listing metrics ───────────────────────────────────────────
// The /api/listings payload carries price_numeric (nightly rate — used
// directly as the ADR figure) and estimated_revenue_l365d. Occupancy and
// demand are derived from those existing fields rather than requiring a
// new API contract.
function metricRevenue(l) { return l.estimated_revenue_l365d || 0; }
function metricAdr(l) { return l.price_numeric || 0; }
function metricOccupancy(l) {
    if (!l.price_numeric || !l.estimated_revenue_l365d) return 0;
    return Math.max(0, Math.min(1, l.estimated_revenue_l365d / (l.price_numeric * 365)));
}
// Real seasonal demand: a 12-value booked-share curve per listing, derived from
// each listing's forward availability calendar (see scripts/load_demand_curves.py)
// and delivered on the demand_curve field. Index 0 = Jan ... 11 = Dec; each value
// is the share of scheduled nights that are booked/blocked in that calendar month.
// This replaces the old lifetime-review-count proxy with a genuine seasonality
// signal that the JAN…DEC timeline can scrub through.
function parseDemandCurve(l) {
    if (l.__demandCurve !== undefined) return l.__demandCurve;
    let curve = null;
    if (l.demand_curve) {
        try {
            const arr = JSON.parse(l.demand_curve);
            if (Array.isArray(arr) && arr.length === 12) curve = arr;
        } catch (e) { curve = null; }
    }
    l.__demandCurve = curve;
    return curve;
}

function demandAnnual(curve) {
    const vals = curve.filter(v => typeof v === 'number');
    if (!vals.length) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function metricDemand(l) {
    const curve = parseDemandCurve(l);
    if (!curve) return 0;
    let v;
    if (activeMonth == null) {
        v = demandAnnual(curve);
    } else {
        v = curve[activeMonth];
        // Fall back to the annual average if this specific month has no data.
        if (typeof v !== 'number') v = demandAnnual(curve);
    }
    return typeof v === 'number' ? v : 0;
}

function compactCurrency(v) {
    const n = Math.round(v);
    if (Math.abs(n) >= 1000) { return '$' + Math.round(n / 1000) + 'K'; }
    return '$' + n;
}

const LAYER_DEFS = {
    revenue:   { get: metricRevenue,   label: 'Revenue',      fmt: v => '$' + Math.round(v).toLocaleString(), badge: compactCurrency, low: 'Low', high: 'High' },
    adr:       { get: metricAdr,       label: 'ADR',          fmt: v => '$' + Math.round(v).toLocaleString(), badge: compactCurrency, low: 'Low', high: 'High' },
    occupancy: { get: metricOccupancy, label: 'Occupancy',    fmt: v => Math.round(v * 100) + '%', badge: v => Math.round(v * 100) + '%', low: 'Low', high: 'High' },
    demand:    { get: metricDemand,    label: 'Demand · forward bookings', fmt: v => Math.round(v * 100) + '% booked', badge: v => Math.round(v * 100) + '%', low: 'Quiet', high: 'Booked' },
    density:   { get: null,            label: 'Comparable density', fmt: v => Math.round(v) + ' nearby', badge: v => Math.round(v), low: 'Sparse', high: 'Dense' },
};

// Compute a robust [p10, p90] scale for the active layer across the
// currently loaded listings, so color intensity is relative to what's on
// screen rather than a hardcoded global range.
function computeScale(listings, layerKey) {
    const def = LAYER_DEFS[layerKey];
    let values;
    if (layerKey === 'density') {
        values = listings.map(l => densityAt(l, listings));
    } else {
        values = listings.map(def.get).filter(v => v > 0);
    }
    if (values.length === 0) return { lo: 0, hi: 1 };
    values.sort((a, b) => a - b);
    const p = (q) => values[Math.min(values.length - 1, Math.floor(q * (values.length - 1)))];
    const lo = p(0.1);
    const hi = Math.max(p(0.9), lo + 1);
    return { lo, hi };
}

// Comparable density: how many other listings of the same room type sit
// within a small radius. Reused both for the "density" layer and for
// finding comps when a property is selected.
function haversine(lat1, lon1, lat2, lon2) {
    const R = 3958.8; // miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
}

function findComps(listing, listings, radiusMiles = 1.5) {
    return listings.filter(l =>
        l.id !== listing.id &&
        l.room_type === listing.room_type &&
        l.latitude && l.longitude &&
        haversine(listing.latitude, listing.longitude, l.latitude, l.longitude) <= radiusMiles
    );
}

function densityAt(listing, listings) {
    return findComps(listing, listings, 1.5).length;
}

// ─── Helpers ────────────────────────────────────────────────────────────
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function titleCase(s) {
    return (s || '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// ─── Load listings from API ────────────────────────────────────────────
async function loadListings() {
    const bounds = map.getBounds();
    const north = clamp(bounds.getNorth(), -90, 90);
    const south = clamp(bounds.getSouth(), -90, 90);
    const east  = clamp(bounds.getEast(), -180, 180);
    const west  = clamp(bounds.getWest(), -180, 180);

    const params = new URLSearchParams({ north, south, east, west, limit: '1500' });

    const state    = document.getElementById('state-filter').value;
    const city     = document.getElementById('city-filter').value;
    const roomType = document.getElementById('room-filter').value;
    const minPrice = document.getElementById('min-price').value;
    const maxPrice = document.getElementById('max-price').value;
    const guestFavorites = document.getElementById('toggle-guest-fav').checked;
    const instantBook    = document.getElementById('toggle-instant').checked;

    if (state)       params.set('state', state);
    if (city)        params.set('city', city);
    if (roomType)     params.set('room_type', roomType);
    if (minPrice)    params.set('min_price', minPrice);
    if (maxPrice)    params.set('max_price', maxPrice);
    if (guestFavorites) params.set('guest_favorites', 'true');
    if (instantBook)    params.set('instant_book', 'true');

    if (currentController) currentController.abort();
    const controller = new AbortController();
    currentController = controller;
    const requestId = ++lastRequestId;

    try {
        const resp = await fetch(`/api/listings?${params.toString()}`, { signal: controller.signal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (requestId !== lastRequestId) return;

        currentListings = applyClientFilters(data.listings);
        renderLayer();

        const countEl = document.getElementById('visible-count');
        const n = currentListings.length;
        if (countEl) countEl.textContent = n.toLocaleString() + ' listings shown';
        document.getElementById('visible-count-pill').style.display = 'flex';
        updateFilterBadge();
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load listings:', err);
        const countEl = document.getElementById('visible-count');
        if (countEl) countEl.textContent = 'Error loading listings';
    } finally {
        if (currentController === controller) currentController = null;
    }
}

// Bedrooms / guests / revenue-range filters are not part of the
// /api/listings query contract, so they're applied client-side against the
// already-fetched bounding-box result. This keeps the API surface unchanged
// while still exposing the filters the product brief calls for.
function applyClientFilters(listings) {
    const bedrooms  = document.getElementById('bedrooms-filter').value;
    const bathrooms = document.getElementById('bathrooms-filter').value;
    const guests    = document.getElementById('guests-filter').value;
    const minRev    = document.getElementById('min-revenue').value;
    const maxRev    = document.getElementById('max-revenue').value;

    return listings.filter(l => {
        if (bedrooms !== '' && (l.bedrooms || 0) < Number(bedrooms)) return false;
        if (bathrooms !== '' && (l.bathrooms || 0) < Number(bathrooms)) return false;
        if (guests !== '' && (l.accommodates || 0) < Number(guests)) return false;
        if (minRev !== '' && (l.estimated_revenue_l365d || 0) < Number(minRev)) return false;
        if (maxRev !== '' && (l.estimated_revenue_l365d || 0) > Number(maxRev)) return false;
        return true;
    });
}

// ─── Filter badge count ────────────────────────────────────────────────
function updateFilterBadge() {
    const ids = ['state-filter', 'city-filter', 'room-filter', 'min-price', 'max-price',
                 'bedrooms-filter', 'bathrooms-filter', 'guests-filter', 'min-revenue', 'max-revenue'];
    let count = ids.filter(id => document.getElementById(id).value).length;
    if (document.getElementById('toggle-guest-fav').checked) count++;
    if (document.getElementById('toggle-instant').checked) count++;

    const badge = document.getElementById('filter-badge');
    if (count > 0) {
        badge.textContent = count;
        badge.removeAttribute('hidden');
    } else {
        badge.setAttribute('hidden', '');
    }
}

// ─── Grid binning for market-level aggregation (zoomed out) ────────────
function gridBin(listings, cellDeg) {
    const cells = new Map();
    for (const l of listings) {
        if (!l.latitude || !l.longitude) continue;
        const key = Math.round(l.latitude / cellDeg) + ':' + Math.round(l.longitude / cellDeg);
        if (!cells.has(key)) cells.set(key, []);
        cells.get(key).push(l);
    }
    return cells;
}

function cellDegForZoom(zoom) {
    // Coarser cells when zoomed further out.
    if (zoom <= 6) return 0.9;
    if (zoom <= 8) return 0.4;
    if (zoom <= 10) return 0.15;
    return 0.06;
}

// ─── Rendering ───────────────────────────────────────────────────────────
function renderLayer() {
    markerLayer.clearLayers();
    markerById.clear();
    const zoom = map.getZoom();
    const detailZoom = zoom >= 11;
    const def = LAYER_DEFS[activeLayer];

    if (activeLayer === 'density') {
        // Precompute density once per render — expensive but bounded by the
        // per-request listing cap.
        currentListings.forEach(l => { l.__density = densityAt(l, currentListings); });
    }

    const getValue = activeLayer === 'density' ? (l => l.__density) : def.get;
    const scale = computeScale(currentListings, activeLayer);
    updateLegend(def, scale);

    if (!detailZoom) {
        renderMarketField(currentListings, getValue, scale, zoom);
    } else {
        renderPropertyDots(currentListings, getValue, scale);
    }
}

function renderMarketField(listings, getValue, scale, zoom) {
    const cellDeg = cellDegForZoom(zoom);
    const cells = gridBin(listings, cellDeg);
    for (const group of cells.values()) {
        if (group.length === 0) continue;
        let sum = 0, lat = 0, lng = 0;
        for (const l of group) {
            sum += getValue(l) || 0;
            lat += l.latitude;
            lng += l.longitude;
        }
        const avg = sum / group.length;
        lat /= group.length;
        lng /= group.length;
        const t = (avg - scale.lo) / (scale.hi - scale.lo || 1);
        const radius = 10 + Math.min(26, Math.sqrt(group.length) * 4);
        const marker = L.circleMarker([lat, lng], {
            radius,
            className: 'aw-market-cell',
            color: 'transparent',
            fillColor: colorForT(t),
            fillOpacity: 0.42,
            weight: 0,
        });
        marker.bindTooltip(
            `${group.length.toLocaleString()} listings &middot; ${LAYER_DEFS[activeLayer].fmt(avg)} avg`,
            { className: 'aw-tooltip', sticky: true }
        );
        marker.on('click', () => map.setView([lat, lng], Math.min(map.getZoom() + 3, 13)));
        markerLayer.addLayer(marker);
    }
}

function renderPropertyDots(listings, getValue, scale) {
    const def = LAYER_DEFS[activeLayer];
    const showBadges = listings.length <= 60;
    for (const listing of listings) {
        if (!listing.latitude || !listing.longitude) continue;
        const value = getValue(listing) || 0;
        const t = (value - scale.lo) / (scale.hi - scale.lo || 1);
        const color = colorForT(t);
        let icon;
        if (showBadges && def.badge) {
            icon = L.divIcon({
                html: `<div class="aw-marker-badge"><span class="aw-marker-dot-mini" style="background:${color}"></span>${def.badge(value)}</div>`,
                className: '',
                iconSize: null,
                iconAnchor: [24, 14],
            });
        } else {
            icon = L.divIcon({
                html: `<div class="aw-marker-dot" style="width:14px;height:14px;background:${color}"></div>`,
                className: '',
                iconSize: [14, 14],
                iconAnchor: [7, 7],
            });
        }
        const marker = L.marker([listing.latitude, listing.longitude], { icon });
        marker.on('click', () => selectListing(listing));
        markerLayer.addLayer(marker);
        markerById.set(listing.id, { marker, listing });
    }
    if (selectedId != null) applySelectionVisuals();
}

function layerTitle(def) {
    if (activeLayer === 'demand') {
        return activeMonth == null
            ? 'Demand · full-year bookings'
            : `Demand · ${MONTH_ABBR[activeMonth]} bookings`;
    }
    return def.label;
}

function updateLegend(def, scale) {
    document.getElementById('legend-title').textContent = layerTitle(def);
    document.getElementById('legend-low').textContent = def.low + ' ' + (def.fmt ? def.fmt(scale.lo) : '');
    document.getElementById('legend-high').textContent = def.high + ' ' + (def.fmt ? def.fmt(scale.hi) : '');
}

// ─── Property selection + inspection panel ─────────────────────────────
function selectListing(listing) {
    selectedId = listing.id;
    applySelectionVisuals();
    showInspector(listing);
}

function applySelectionVisuals() {
    const selected = markerById.get(selectedId);
    if (!selected) return;
    const comps = findComps(selected.listing, currentListings, 1.5);
    const compIds = new Set(comps.map(c => c.id));

    for (const [id, entry] of markerById) {
        const el = entry.marker.getElement();
        if (!el) continue;
        const dot = el.querySelector('.aw-marker-dot, .aw-marker-badge') || el;
        dot.classList.remove('aw-dimmed', 'aw-comp', 'aw-selected');
        if (id === selectedId) {
            dot.classList.add('aw-selected');
        } else if (compIds.has(id)) {
            dot.classList.add('aw-comp');
        } else {
            dot.classList.add('aw-dimmed');
        }
    }
}

function clearSelectionVisuals() {
    for (const [, entry] of markerById) {
        const el = entry.marker.getElement();
        if (!el) continue;
        const dot = el.querySelector('.aw-marker-dot, .aw-marker-badge') || el;
        dot.classList.remove('aw-dimmed', 'aw-comp', 'aw-selected');
    }
}

function percentile(sorted, q) {
    if (sorted.length === 0) return 0;
    return sorted[Math.min(sorted.length - 1, Math.floor(q * (sorted.length - 1)))];
}

function showInspector(listing) {
    const comps = findComps(listing, currentListings, 1.5);
    const revenues = comps.map(c => c.estimated_revenue_l365d).filter(v => v > 0).sort((a, b) => a - b);
    const ownRevenue = listing.estimated_revenue_l365d || (revenues.length ? revenues[Math.floor(revenues.length / 2)] : 0);

    let downside, upside, mostLikely, confidence;
    if (revenues.length >= 4) {
        downside = percentile(revenues, 0.1);
        upside = percentile(revenues, 0.9);
        mostLikely = ownRevenue || percentile(revenues, 0.5);
        confidence = comps.length >= 20 ? 'high' : comps.length >= 8 ? 'medium' : 'low';
    } else {
        // Too few nearby comps for a data-driven band — fall back to a
        // narrow band around the listing's own modeled revenue rather than
        // fabricating precision the data doesn't support.
        mostLikely = ownRevenue || 0;
        downside = mostLikely * 0.8;
        upside = mostLikely * 1.2;
        confidence = 'low';
    }

    const cityLabel = titleCase(listing.city);
    const stateLabel = (listing.state || '').toUpperCase();

    renderInspectorPhoto(listing);

    document.getElementById('inspector-name').textContent = listing.name || 'Unnamed listing';
    document.getElementById('inspector-meta').textContent =
        `${listing.room_type || 'Listing'} \u00b7 ${cityLabel}, ${stateLabel} \u00b7 ${listing.bedrooms || 0} bed \u00b7 ${listing.accommodates || 0} guests`;
    document.getElementById('inspector-dot').style.background = colorForT(0.5);

    // AIRWORTHY verdict + score — computed client-side from the same
    // signals the backend uses (revenue vs. local benchmark, comp spread,
    // comp count) since this inspector renders from map data without a
    // /v1/estimate round trip. Mirrors src/scoring.py exactly.
    const verdictSlot = document.getElementById('inspector-verdict');
    verdictSlot.innerHTML = '';
    if (mostLikely > 0) {
        const cityRevenues = currentListings
            .filter(l => l.city === listing.city && l.state === listing.state && l.estimated_revenue_l365d > 0)
            .map(l => l.estimated_revenue_l365d);
        const benchmarkRevenue = cityRevenues.length ? percentile(cityRevenues.slice().sort((a, b) => a - b), 0.5) : mostLikely;
        const mean = revenues.length ? revenues.reduce((s, v) => s + v, 0) / revenues.length : mostLikely;
        const variance = revenues.length ? revenues.reduce((s, v) => s + (v - mean) ** 2, 0) / revenues.length : 0;
        const cv = mean > 0 ? Math.sqrt(variance) / mean : 1.0;
        const verdictResult = AirworthyVerdict.computeScore({
            revenue: mostLikely,
            benchmarkRevenue,
            cv,
            nComps: comps.length,
        });
        AirworthyVerdict.render(verdictSlot, {
            score: verdictResult.score,
            verdict: verdictResult.verdict,
            reason: verdictResult.reason,
            lowData: comps.length < 8,
        });
    }

    const envelopeSlot = document.getElementById('inspector-envelope');
    envelopeSlot.innerHTML = '';
    if (mostLikely > 0) {
        AirworthyEnvelope.render(envelopeSlot, {
            downside: Math.max(0, downside),
            upside: Math.max(upside, downside + 1),
            mostLikely,
            confidenceLevel: confidence,
            label: 'Modeled annual revenue',
        });
    } else {
        envelopeSlot.textContent = 'No modeled revenue available for this listing.';
    }

    document.getElementById('inspector-adr').textContent = listing.price_numeric ? '$' + Math.round(listing.price_numeric) + '/night' : '\u2014';
    const occ = metricOccupancy(listing);
    document.getElementById('inspector-occupancy').textContent = occ > 0 ? Math.round(occ * 100) + '%' : '\u2014';
    document.getElementById('inspector-comps').textContent = comps.length.toLocaleString();

    renderInspectorSeason(listing);

    const cta = document.getElementById('inspector-cta');
    const ctaParams = new URLSearchParams();
    if (listing.name) ctaParams.set('address', listing.name);
    if (listing.bedrooms != null) ctaParams.set('bedrooms', listing.bedrooms);
    if (listing.bathrooms != null) ctaParams.set('bathrooms', listing.bathrooms);
    if (listing.accommodates != null) ctaParams.set('accommodates', listing.accommodates);
    if (listing.price_numeric != null) ctaParams.set('nightly_rate', listing.price_numeric);
    cta.href = `/property?${ctaParams.toString()}`;

    document.getElementById('inspector').hidden = false;
    updateTimelineVisibility();
    // The inspector is a flex sibling of the map canvas (not an overlay), so
    // opening it changes the canvas width — Leaflet caches its container
    // size and needs an explicit nudge to redraw correctly.
    requestAnimationFrame(() => map.invalidateSize());
}

// Show the selected listing's real photo with a link to its Airbnb source.
// Fails cleanly when a listing has no photo, or the image URL 404s.
function renderInspectorPhoto(listing) {
    const link = document.getElementById('inspector-photo-link');
    const img = document.getElementById('inspector-photo');
    const photo = listing.picture_url;
    if (!photo) {
        link.hidden = true;
        img.removeAttribute('src');
        return;
    }
    img.onerror = () => { link.hidden = true; };
    img.alt = listing.name || 'Listing photo';
    img.src = photo;
    if (listing.listing_url) {
        link.href = listing.listing_url;
        link.style.pointerEvents = '';
    } else {
        link.removeAttribute('href');
        link.style.pointerEvents = 'none';
    }
    link.hidden = false;
}

// Compact 12-point booked-share sparkline for the selected listing, using the
// same demand_curve field that powers the Demand map layer — so the number a
// user sees per-property here always matches what the layer/timeline show.
function renderInspectorSeason(listing) {
    const chart = document.getElementById('inspector-season-chart');
    chart.innerHTML = '';
    const curve = parseDemandCurve(listing);
    if (!curve) {
        const empty = document.createElement('div');
        empty.className = 'inspector-season-empty';
        empty.textContent = 'No seasonal booking data for this listing yet.';
        chart.appendChild(empty);
        return;
    }
    const vals = curve.map(v => (typeof v === 'number' ? v : 0));
    const max = Math.max(...vals, 0.01);
    curve.forEach((v, i) => {
        // A real <button>, not a decorative bar: tapping a month jumps the
        // whole map's active layer + timeline to that month (absorbs #24).
        const bar = document.createElement('button');
        bar.type = 'button';
        bar.className = 'inspector-season-bar';
        const value = typeof v === 'number' ? v : 0;
        if (value >= max * 0.97 && value > 0) bar.classList.add('peak');
        if (activeLayer === 'demand' && activeMonth === i) bar.classList.add('active');
        bar.style.height = Math.max((value / max) * 100, typeof v === 'number' ? 8 : 3) + '%';
        const label = `${MONTH_ABBR[i]}: ${typeof v === 'number' ? Math.round(v * 100) + '% booked' : 'no data'}`;
        bar.title = label;
        bar.setAttribute('aria-label', `Jump map to ${label}`);
        bar.addEventListener('click', () => jumpMapToMonth(i));
        chart.appendChild(bar);
    });
}

// Tapping a month in the inspector's seasonal chart switches the map to the
// Demand layer, sets that month as the active month, updates the timeline
// UI to match, and refreshes the season chart's own active-bar highlight.
function jumpMapToMonth(monthIdx) {
    activeLayer = 'demand';
    activeMonth = monthIdx;

    document.querySelectorAll('.layer-btn').forEach(b => {
        const on = b.dataset.layer === 'demand';
        b.classList.toggle('active', on);
        b.setAttribute('aria-selected', String(on));
    });

    syncTimelineUI();
    updateTimelineVisibility();
    renderLayer();

    if (selectedId != null) {
        const entry = markerById.get(selectedId);
        if (entry) renderInspectorSeason(entry.listing);
    }
}

document.getElementById('inspector-close').addEventListener('click', () => {
    document.getElementById('inspector').hidden = true;
    selectedId = null;
    clearSelectionVisuals();
    updateTimelineVisibility();
    requestAnimationFrame(() => map.invalidateSize());
});

// ─── Layer selector ──────────────────────────────────────────────────────
document.querySelectorAll('.layer-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.layer-btn').forEach(b => {
            b.classList.remove('active');
            b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        activeLayer = btn.dataset.layer;
        updateTimelineVisibility();
        renderLayer();
    });
});

// ─── Seasonal demand timeline (JAN…DEC scrubber) ─────────────────────────────
// Only meaningful for the Demand layer, which now carries a real month-by-month
// booked-share curve per listing. Dragging months recolors the map by that
// month's demand instead of a single static value.
function buildTimeline() {
    const container = document.getElementById('timeline-months');
    if (!container) return;
    MONTH_ABBR.forEach((abbr, idx) => {
        const btn = document.createElement('button');
        btn.className = 'timeline-month';
        btn.dataset.month = String(idx);
        btn.textContent = abbr;
        btn.setAttribute('aria-pressed', 'false');
        btn.addEventListener('click', () => selectMonth(idx));
        container.appendChild(btn);
    });
}

function selectMonth(idx) {
    activeMonth = (activeMonth === idx) ? null : idx;
    syncTimelineUI();
    renderLayer();
}

function syncTimelineUI() {
    document.querySelectorAll('.timeline-month').forEach(b => {
        const on = Number(b.dataset.month) === activeMonth;
        b.classList.toggle('active', on);
        b.setAttribute('aria-pressed', String(on));
    });
    const sub = document.getElementById('timeline-sub');
    const clear = document.getElementById('timeline-clear');
    if (activeMonth == null) {
        if (sub) sub.textContent = 'Full year average';
        if (clear) clear.hidden = true;
    } else {
        if (sub) sub.textContent = MONTH_ABBR[activeMonth];
        if (clear) clear.hidden = false;
    }
}

function updateTimelineVisibility() {
    const tl = document.getElementById('map-timeline');
    if (!tl) return;
    // Hidden unless the Demand layer is active and the inspector isn't covering
    // the bottom of the screen.
    const inspectorOpen = !document.getElementById('inspector').hidden;
    tl.hidden = !(activeLayer === 'demand' && !inspectorOpen);
}

const timelineClearBtn = document.getElementById('timeline-clear');
if (timelineClearBtn) {
    timelineClearBtn.addEventListener('click', () => {
        activeMonth = null;
        syncTimelineUI();
        renderLayer();
    });
}

// ─── City labels ──────────────────────────────────────────────────────────
const CITY_LABELS = {
    'los-angeles':        'LA',
    'san-diego':          'San Diego',
    'san-francisco':      'SF',
    'santa-clara-county': 'Santa Clara',
    'san-mateo-county':   'San Mateo',
    'oakland':            'Oakland',
    'santa-cruz-county':  'Santa Cruz',
    'pacific-grove':      'Pacific Grove',
    'broward-county':     'Broward',
};

let cityData = [];
let activeChipSlug = null;
let totalListings = 0;
let dataFreshness = null;

function formatFreshness(iso) {
    if (!iso) return 'Latest snapshot';
    const d = new Date(iso + 'T00:00:00');
    if (isNaN(d)) return 'Latest snapshot';
    return 'Data through ' + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ─── City chips ────────────────────────────────────────────────────────────
function renderChips(cities) {
    const container = document.getElementById('map-chips');
    container.innerHTML = '';
    cities.slice(0, 6).forEach(city => {
        const label = CITY_LABELS[city.slug] || titleCase(city.slug);
        const count = city.count >= 1000 ? (city.count / 1000).toFixed(0) + 'k' : city.count;
        const chip = document.createElement('button');
        chip.className = 'map-chip';
        chip.dataset.slug = city.slug;
        chip.setAttribute('aria-pressed', 'false');
        const dot = document.createElement('span');
        dot.className = 'chip-dot';
        dot.setAttribute('aria-hidden', 'true');
        chip.appendChild(dot);
        chip.appendChild(document.createTextNode(`${count} ${label}`));
        chip.addEventListener('click', () => onChipClick(city, chip));
        container.appendChild(chip);
    });
}

async function onChipClick(city, chipEl) {
    const isActive = chipEl.classList.contains('active');
    document.querySelectorAll('.map-chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });

    if (isActive) {
        activeChipSlug = null;
        document.getElementById('state-filter').value = '';
        await loadCityDropdown('');
        document.getElementById('city-filter').value = '';
        updateRailTitle(null);
        loadListings();
        return;
    }

    chipEl.classList.add('active');
    chipEl.setAttribute('aria-pressed', 'true');
    activeChipSlug = city.slug;

    document.getElementById('state-filter').value = city.state;
    await loadCityDropdown(city.state);
    document.getElementById('city-filter').value = city.slug;

    const [[minLat, maxLat], [minLng, maxLng]] = city.bounds;
    map.fitBounds([[minLat, minLng], [maxLat, maxLng]], { padding: [80, 80], maxZoom: 13 });

    const label = CITY_LABELS[city.slug] || titleCase(city.slug);
    updateRailTitle(label, city.count);
    loadListings();
}

function updateRailTitle(cityLabel, count) {
    const titleEl = document.getElementById('rail-title');
    const subEl   = document.getElementById('rail-sub');
    if (cityLabel) {
        titleEl.textContent = cityLabel;
        subEl.textContent   = `${(count || 0).toLocaleString()} listings \u00b7 Latest snapshot`;
    } else {
        titleEl.textContent = 'California & Florida';
        subEl.textContent = totalListings
            ? `${totalListings.toLocaleString()} listings \u00b7 ${formatFreshness(dataFreshness)}`
            : formatFreshness(dataFreshness);
    }
}

// ─── City dropdown ─────────────────────────────────────────────────────────
async function loadCityDropdown(stateFilter) {
    const select = document.getElementById('city-filter');
    try {
        const params = new URLSearchParams();
        if (stateFilter) params.set('state', stateFilter);
        const resp = await fetch(`/api/cities?${params.toString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        select.innerHTML = '<option value="">All cities</option>';
        for (const city of data.cities) {
            const label = CITY_LABELS[city.slug] || titleCase(city.slug);
            const opt = document.createElement('option');
            opt.value = city.slug;
            opt.textContent = label;
            select.appendChild(opt);
        }
    } catch (err) {
        console.error('Failed to load city dropdown:', err);
    }
}

async function loadCities() {
    const state = document.getElementById('state-filter').value;
    try {
        const params = new URLSearchParams();
        if (state) params.set('state', state);
        const resp = await fetch(`/api/cities?${params.toString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        cityData = data.cities;

        if (!state) {
            renderChips(cityData);
            totalListings = cityData.reduce((sum, c) => sum + (c.count || 0), 0);
            dataFreshness = data.data_freshness || null;
            if (!activeChipSlug && !document.getElementById('city-filter').value) {
                updateRailTitle(null);
            }
        }

        const select = document.getElementById('city-filter');
        select.innerHTML = '<option value="">All cities</option>';
        for (const city of data.cities) {
            const label = CITY_LABELS[city.slug] || titleCase(city.slug);
            const opt = document.createElement('option');
            opt.value = city.slug;
            opt.textContent = label;
            select.appendChild(opt);
        }
    } catch (err) {
        console.error('Failed to load cities:', err);
    }
}

// ─── Filter events ─────────────────────────────────────────────────────────
function scheduleLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadListings, 280);
}

document.getElementById('room-filter').addEventListener('change', loadListings);

document.getElementById('state-filter').addEventListener('change', async () => {
    activeChipSlug = null;
    document.querySelectorAll('.map-chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });
    updateRailTitle(null);
    document.getElementById('city-filter').value = '';
    await loadCities();
    loadListings();
});

document.getElementById('city-filter').addEventListener('change', () => {
    const val = document.getElementById('city-filter').value;
    if (val !== activeChipSlug) {
        activeChipSlug = null;
        document.querySelectorAll('.map-chip').forEach(c => {
            c.classList.remove('active');
            c.setAttribute('aria-pressed', 'false');
        });
    }
    if (val) {
        const city = cityData.find(c => c.slug === val);
        const label = CITY_LABELS[val] || titleCase(val);
        updateRailTitle(label, city ? city.count : 0);
    } else {
        updateRailTitle(null);
    }
    loadListings();
});

['min-price', 'max-price', 'bedrooms-filter', 'bathrooms-filter', 'guests-filter', 'min-revenue', 'max-revenue'].forEach(id => {
    document.getElementById(id).addEventListener('change', loadListings);
});
['toggle-guest-fav', 'toggle-instant'].forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
        updateFilterBadge();
        loadListings();
    });
});

document.getElementById('reset-filters').addEventListener('click', () => {
    document.getElementById('state-filter').value = '';
    document.getElementById('city-filter').value = '';
    document.getElementById('room-filter').value = '';
    document.getElementById('min-price').value = '';
    document.getElementById('max-price').value = '';
    document.getElementById('bedrooms-filter').value = '';
    document.getElementById('bathrooms-filter').value = '';
    document.getElementById('guests-filter').value = '';
    document.getElementById('min-revenue').value = '';
    document.getElementById('max-revenue').value = '';
    document.getElementById('toggle-guest-fav').checked = false;
    document.getElementById('toggle-instant').checked = false;
    activeChipSlug = null;
    document.querySelectorAll('.map-chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });
    updateRailTitle(null);
    updateFilterBadge();
    loadCities();
    loadListings();
});

// ─── Command bar popovers (location + more filters) ─────────────────────
// Both popovers anchor under their trigger button and close when the other
// opens or when the user clicks outside — this is the narrow contextual
// disclosure surface the brief calls for, not a permanent filter column.
const moreFiltersPanel = document.getElementById('more-filters');
const toggleMoreBtn = document.getElementById('toggle-more-filters');
const locationPopover = document.getElementById('location-popover');
const locationTrigger = document.getElementById('location-trigger');

function setPopoverOpen(panel, trigger, open) {
    panel.hidden = !open;
    trigger.setAttribute('aria-expanded', String(open));
}

function closeAllPopovers(except) {
    if (moreFiltersPanel !== except) setPopoverOpen(moreFiltersPanel, toggleMoreBtn, false);
    if (locationPopover !== except) setPopoverOpen(locationPopover, locationTrigger, false);
}

toggleMoreBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const willOpen = moreFiltersPanel.hidden;
    closeAllPopovers();
    setPopoverOpen(moreFiltersPanel, toggleMoreBtn, willOpen);
});

locationTrigger.addEventListener('click', (e) => {
    e.stopPropagation();
    const willOpen = locationPopover.hidden;
    closeAllPopovers();
    setPopoverOpen(locationPopover, locationTrigger, willOpen);
});

document.addEventListener('click', (e) => {
    if (!moreFiltersPanel.hidden && !moreFiltersPanel.contains(e.target) && e.target !== toggleMoreBtn && !toggleMoreBtn.contains(e.target)) {
        setPopoverOpen(moreFiltersPanel, toggleMoreBtn, false);
    }
    if (!locationPopover.hidden && !locationPopover.contains(e.target) && e.target !== locationTrigger && !locationTrigger.contains(e.target)) {
        setPopoverOpen(locationPopover, locationTrigger, false);
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllPopovers();
});

// ─── Map events ────────────────────────────────────────────────────────────
map.on('moveend zoomend', scheduleLoad);

// ─── Boot ──────────────────────────────────────────────────────────────────
(async function init() {
    buildTimeline();
    syncTimelineUI();
    updateTimelineVisibility();
    await loadCities();
    loadListings();
})();
