// Airbnb Map — Coral Coast design
// California & Florida listings explorer

// ─── Map setup ────────────────────────────────────────────────────────────────
// Start centered on California coast — most listings live here.
// maxBounds keeps users from panning into invalid lat/lng territory (which the
// API correctly rejects with 400) or off into empty ocean/space.
const WORLD_BOUNDS = [[-85, -220], [85, 220]];
const map = L.map('map', {
    zoomControl: false,
    maxBounds: WORLD_BOUNDS,
    maxBoundsViscosity: 1.0,
    minZoom: 3,
}).setView([36.5, -119.5], 6);

// Zoom controls — top-right to not clash with sidebar
L.control.zoom({ position: 'topright' }).addTo(map);

// CartoDB light tile — cleaner than OSM default
L.tileLayer(
    'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
    }
).addTo(map);

// ─── Cluster group with coral icon ────────────────────────────────────────────
const markers = L.markerClusterGroup({
    maxClusterRadius: 70,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true,
    iconCreateFunction(cluster) {
        const count = cluster.getChildCount();
        const label = count >= 1000 ? Math.round(count / 1000) + 'k' : count;
        const size = count > 500 ? 52 : count > 100 ? 44 : 36;
        return L.divIcon({
            html: `<div class="coral-cluster" style="width:${size}px;height:${size}px;font-size:${size < 44 ? 12 : 13}px">${label}</div>`,
            className: '',
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
        });
    },
});
map.addLayer(markers);

// ─── State ────────────────────────────────────────────────────────────────────
let debounceTimer = null;
let currentController = null;
let lastRequestId = 0;
let activeRoomType = '';

// ─── Room type colors ─────────────────────────────────────────────────────────
const roomColors = {
    'Entire home/apt': '#FF385C',
    'Private room':    '#059669',
    'Hotel room':      '#f59e0b',
    'Shared room':     '#6b7280',
};

function getColor(roomType) {
    return roomColors[roomType] || '#FF385C';
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatCurrency(n) {
    if (!n) return 'N/A';
    return '$' + Math.round(n).toLocaleString();
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function buildPopup(props) {
    // All data-derived text is escaped before interpolation — city/state/name
    // and room_type ultimately come from the DB (sourced from InsideAirbnb CSVs),
    // and must be treated as untrusted when injected into innerHTML.
    const cityRaw = (props.city || '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    const city = escapeHtml(cityRaw);
    const state = escapeHtml((props.state || '').toUpperCase());
    const color = getColor(props.room_type);
    const roomLabel = props.room_type || 'Listing';
    const beds = props.bedrooms || 0;
    const guests = props.accommodates || 0;
    const baths = props.bathrooms ? parseFloat(props.bathrooms).toFixed(1).replace(/\.0$/, '') : '–';
    const reviews = props.number_of_reviews || 0;
    const price = formatCurrency(props.price_numeric);
    const revenue = props.estimated_revenue_l365d
        ? formatCurrency(props.estimated_revenue_l365d)
        : null;
    return `
        <div class="popup-header">
            <div class="popup-type-dot" style="background:${color}"></div>
            <div class="popup-name">${escapeHtml(props.name || 'Unnamed listing')}</div>
        </div>
        <div class="popup-content">
            <div class="popup-meta">
                <span class="popup-meta-item"><strong>${escapeHtml(roomLabel)}</strong></span>
                <span class="popup-meta-item">${city}, ${state}</span>
                <span class="popup-meta-item">${beds} bed · ${baths} bath · ${guests} guests</span>
                ${reviews > 0 ? `<span class="popup-meta-item">★ ${reviews} review${reviews !== 1 ? 's' : ''}</span>` : ''}
            </div>
            <div class="popup-stats">
                <div class="popup-stat">
                    <div class="popup-stat-label">Nightly rate</div>
                    <div class="popup-stat-value">${price}</div>
                </div>
                <div class="popup-stat ${revenue ? 'highlight' : ''}">
                    <div class="popup-stat-label">Est. annual rev</div>
                    <div class="popup-stat-value">${revenue || '–'}</div>
                </div>
            </div>
        </div>
    `;
}

// ─── Price-label markers ──────────────────────────────────────────────────────
function priceIcon(listing) {
    const price = listing.price_numeric ? '$' + Math.round(listing.price_numeric) : '?';
    const color = getColor(listing.room_type);
    return L.divIcon({
        html: `<div class="price-marker" style="border-color:${color}20">${price}</div>`,
        className: '',
        iconSize: null,
        iconAnchor: [0, 0],
    });
}

// ─── Load listings from API ───────────────────────────────────────────────────
function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
}

async function loadListings() {
    const bounds = map.getBounds();
    // Defensive clamp — belt-and-suspenders alongside maxBounds above.
    // Leaflet can still report out-of-range values transiently during
    // fitBounds/inertial pan animations before maxBounds settles.
    const north = clamp(bounds.getNorth(), -90, 90);
    const south = clamp(bounds.getSouth(), -90, 90);
    const east  = clamp(bounds.getEast(), -180, 180);
    const west  = clamp(bounds.getWest(), -180, 180);

    const params = new URLSearchParams({
        north: north,
        south: south,
        east:  east,
        west:  west,
        limit: '1000',
    });

    const state    = document.getElementById('state-filter').value;
    const city     = document.getElementById('city-filter').value;
    const minPrice = document.getElementById('min-price').value;
    const maxPrice = document.getElementById('max-price').value;
    const guestFavorites = document.getElementById('toggle-guest-fav').checked;
    const instantBook    = document.getElementById('toggle-instant').checked;

    if (state)       params.set('state', state);
    if (city)        params.set('city', city);
    if (activeRoomType) params.set('room_type', activeRoomType);
    if (minPrice)    params.set('min_price', minPrice);
    if (maxPrice)    params.set('max_price', maxPrice);
    if (guestFavorites) params.set('guest_favorites', 'true');
    if (instantBook)    params.set('instant_book', 'true');

    // Cancel stale request
    if (currentController) currentController.abort();
    const controller = new AbortController();
    currentController = controller;
    const requestId = ++lastRequestId;

    try {
        const resp = await fetch(`/api/listings?${params.toString()}`, { signal: controller.signal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        if (requestId !== lastRequestId) return;
        renderMarkers(data.listings);
        const countEl = document.getElementById('visible-count');
        const n = data.listings.length;
        if (countEl) countEl.textContent = n.toLocaleString() + ' listings shown';

        // Update "Show results" button
        const applyBtn = document.getElementById('apply-filters');
        if (applyBtn) applyBtn.textContent = `Show ${n.toLocaleString()} results`;
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

// ─── Filter badge count ───────────────────────────────────────────────────────
function updateFilterBadge() {
    let count = 0;
    if (document.getElementById('state-filter').value)   count++;
    if (document.getElementById('city-filter').value)    count++;
    if (activeRoomType)                                  count++;
    if (document.getElementById('min-price').value)      count++;
    if (document.getElementById('max-price').value)      count++;
    if (document.getElementById('toggle-guest-fav').checked) count++;
    if (document.getElementById('toggle-instant').checked)   count++;

    const badge = document.getElementById('filter-badge');
    if (count > 0) {
        badge.textContent = count;
        badge.removeAttribute('hidden');
    } else {
        badge.setAttribute('hidden', '');
    }
}

// ─── Price histogram from data ────────────────────────────────────────────────
function updateHistogram(listings) {
    const bars = document.querySelectorAll('.price-histogram-bar');
    const prices = listings.map(l => l.price_numeric).filter(p => p && p > 0 && p < 2000);

    // No valid price data — explicitly flatten bars rather than leaving stale state
    if (prices.length === 0) {
        bars.forEach(bar => {
            bar.style.height = '2%';
            bar.classList.remove('active');
        });
        return;
    }

    const bins = bars.length || 18;
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const counts = Array(bins).fill(0);

    if (max === min) {
        // All listings share one price — put everything in the middle bin
        counts[Math.floor(bins / 2)] = prices.length;
    } else {
        const step = (max - min) / bins;
        for (const p of prices) {
            const i = Math.min(Math.floor((p - min) / step), bins - 1);
            counts[i]++;
        }
    }

    const peak = Math.max(...counts);
    bars.forEach((bar, i) => {
        const pct = peak > 0 ? Math.round((counts[i] / peak) * 100) : 2;
        bar.style.height = Math.max(pct, 2) + '%';
        bar.classList.toggle('active', counts[i] > 0);
    });
}

function renderMarkers(listings) {
    markers.clearLayers();
    updateHistogram(listings);
    const zoom = map.getZoom();
    const usePriceLabels = zoom >= 12;
    const batch = [];

    for (const listing of listings) {
        if (!listing.latitude || !listing.longitude) continue;

        let marker;
        if (usePriceLabels) {
            marker = L.marker([listing.latitude, listing.longitude], { icon: priceIcon(listing) });
        } else {
            const color = getColor(listing.room_type);
            const icon = L.divIcon({
                html: `<div style="width:12px;height:12px;border-radius:50%;background:${color};border:2.5px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,0.35);cursor:pointer;transition:transform .15s;"></div>`,
                className: '',
                iconSize: [12, 12],
                iconAnchor: [6, 6],
            });
            marker = L.marker([listing.latitude, listing.longitude], { icon });
        }

        marker.bindPopup(buildPopup(listing), { maxWidth: 300, className: 'coral-popup' });
        batch.push(marker);
    }

    markers.addLayers(batch);
}

function scheduleLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadListings, 280);
}

// ─── Short display labels for city slugs ──────────────────────────────────────
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

// City bounding boxes stored from last API fetch
let cityData = [];
let activeChipSlug = null;
// Grand total across all cities (latest snapshot) — computed once on first
// full load so the default searchbar subtitle never hardcodes/drifts.
let totalListings = 0;
// Real data freshness (latest snapshot date) reported by /api/cities.
let dataFreshness = null;

function formatFreshness(iso) {
    if (!iso) return 'Latest snapshot';
    const d = new Date(iso + 'T00:00:00');
    if (isNaN(d)) return 'Latest snapshot';
    return 'Data through ' + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ─── City chips ───────────────────────────────────────────────────────────────
function renderChips(cities) {
    const container = document.getElementById('map-chips');
    container.innerHTML = '';
    // Show top 6 by count
    cities.slice(0, 6).forEach(city => {
        const label = CITY_LABELS[city.slug] || city.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const count = city.count >= 1000 ? (city.count / 1000).toFixed(0) + 'k' : city.count;
        const chip = document.createElement('button');
        chip.className = 'map-chip';
        chip.dataset.slug = city.slug;
        chip.setAttribute('aria-pressed', 'false');
        // Built with DOM nodes (not innerHTML) — city.slug/label ultimately
        // come from the DB and must not be trusted as safe HTML.
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

    // Deselect all chips
    document.querySelectorAll('.map-chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });

    if (isActive) {
        // Toggle off — reset city filter, title, and repopulate the dropdown
        // with the full (all-states) city list so the UI stays in sync.
        activeChipSlug = null;
        document.getElementById('state-filter').value = '';
        await loadCityDropdown('');
        document.getElementById('city-filter').value = '';
        updateSearchbarTitle(null);
        loadListings();
        return;
    }

    // Activate chip
    chipEl.classList.add('active');
    chipEl.setAttribute('aria-pressed', 'true');
    activeChipSlug = city.slug;

    // Sync dropdown filters — await dropdown population BEFORE selecting the
    // city value and firing the single authoritative loadListings() call.
    // (Previously this raced: loadListings() ran before the city value was set,
    // so the first fetch after a chip click was state-only, not city-scoped.)
    document.getElementById('state-filter').value = city.state;
    await loadCityDropdown(city.state);
    document.getElementById('city-filter').value = city.slug;

    // Fly to city bounds
    // bounds from API: [[min_lat, max_lat], [min_lng, max_lng]]
    const [[minLat, maxLat], [minLng, maxLng]] = city.bounds;
    map.fitBounds([[minLat, minLng], [maxLat, maxLng]], { padding: [60, 60], maxZoom: 13 });

    // Update searchbar title
    const label = CITY_LABELS[city.slug] || city.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    updateSearchbarTitle(label, city.count);
    loadListings();
}

function updateSearchbarTitle(cityLabel, count) {
    const titleEl = document.getElementById('searchbar-title');
    const subEl   = document.getElementById('searchbar-sub');
    if (cityLabel) {
        titleEl.textContent = cityLabel;
        subEl.textContent   = `${(count || 0).toLocaleString()} listings · Latest snapshot`;
    } else {
        titleEl.textContent = 'California & Florida';
        // No hardcoded total — show the computed grand total once it's loaded,
        // otherwise a neutral placeholder (never a stale/bogus number).
        subEl.textContent = totalListings
            ? `${totalListings.toLocaleString()} listings · ${formatFreshness(dataFreshness)}`
            : formatFreshness(dataFreshness);
    }
}

// ─── City dropdown ────────────────────────────────────────────────────────────
// Never throws — callers (onChipClick, the state-filter handler) `await`
// this and must be able to continue safely even if the network request
// fails, or an unhandled rejection would abort mid-flow and leave chip/filter
// state half-applied (e.g. chip marked active but city-filter never set).
async function loadCityDropdown(stateFilter) {
    const select = document.getElementById('city-filter');
    try {
        const params = new URLSearchParams();
        if (stateFilter) params.set('state', stateFilter);
        const resp = await fetch(`/api/cities?${params.toString()}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        select.innerHTML = '<option value="">All Cities</option>';
        for (const city of data.cities) {
            const label = CITY_LABELS[city.slug] || city.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
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

        // Render chips + cache the grand total only on the full (all-states) load
        if (!state) {
            renderChips(cityData);
            totalListings = cityData.reduce((sum, c) => sum + (c.count || 0), 0);
            dataFreshness = data.data_freshness || null;
            // Refresh the default subtitle if nothing is currently selected
            if (!activeChipSlug && !document.getElementById('city-filter').value) {
                updateSearchbarTitle(null);
            }
        }

        // Populate dropdown
        const select = document.getElementById('city-filter');
        select.innerHTML = '<option value="">All Cities</option>';
        for (const city of data.cities) {
            const label = CITY_LABELS[city.slug] || city.slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const opt = document.createElement('option');
            opt.value = city.slug;
            opt.textContent = label;
            select.appendChild(opt);
        }
    } catch (err) {
        console.error('Failed to load cities:', err);
    }
}

// ─── Room type pills ──────────────────────────────────────────────────────────
document.querySelectorAll('.room-pill').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.room-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeRoomType = btn.dataset.value || '';
        // Sync hidden select (not needed for API but for reset logic)
        document.getElementById('room-filter').value = activeRoomType;
        loadListings();
    });
});

// ─── Filter events ────────────────────────────────────────────────────────────
document.getElementById('state-filter').addEventListener('change', async () => {
    // Changing state manually deactivates any active chip
    activeChipSlug = null;
    document.querySelectorAll('.map-chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });
    updateSearchbarTitle(null);
    // Await the city dropdown reset before loading listings — otherwise the
    // city-filter select still holds a value from the previous state and the
    // first listings fetch after switching states can be filtered incorrectly.
    document.getElementById('city-filter').value = '';
    await loadCities();
    loadListings();
});

['toggle-guest-fav', 'toggle-instant'].forEach(id => {
    document.getElementById(id).addEventListener('change', () => {
        updateFilterBadge();
        loadListings();
    });
});

document.getElementById('city-filter').addEventListener('change', () => {
    // If the manually selected city no longer matches the active chip,
    // deactivate the chip so the UI doesn't show a stale "active" state.
    const val = document.getElementById('city-filter').value;
    if (val !== activeChipSlug) {
        activeChipSlug = null;
        document.querySelectorAll('.map-chip').forEach(c => {
            c.classList.remove('active');
            c.setAttribute('aria-pressed', 'false');
        });
    }
    // Keep the searchbar title in sync with the manually chosen city (or reset
    // to the regional default when "All Cities" is selected) — matches the
    // behavior of clicking a city chip.
    if (val) {
        const city = cityData.find(c => c.slug === val);
        const label = CITY_LABELS[val] || val.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        updateSearchbarTitle(label, city ? city.count : 0);
    } else {
        updateSearchbarTitle(null);
    }
    loadListings();
});

document.getElementById('apply-filters').addEventListener('click', loadListings);

document.getElementById('reset-filters').addEventListener('click', () => {
    document.getElementById('state-filter').value = '';
    document.getElementById('city-filter').value = '';
    document.getElementById('min-price').value = '';
    document.getElementById('max-price').value = '';
    document.getElementById('toggle-guest-fav').checked = false;
    document.getElementById('toggle-instant').checked = false;
    updateFilterBadge();
    activeRoomType = '';
    activeChipSlug = null;
    document.getElementById('room-filter').value = '';
    document.querySelectorAll('.room-pill').forEach(b => b.classList.remove('active'));
    document.querySelector('.room-pill[data-value=""]').classList.add('active');
    document.querySelectorAll('.map-chip').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });
    updateSearchbarTitle(null);
    loadCities();
    loadListings();
});

// ─── Sidebar toggle (search bar filter button) ────────────────────────────────
const sidebar = document.getElementById('map-sidebar');
const chips   = document.getElementById('map-chips');
const searchbar = document.getElementById('map-searchbar');

document.getElementById('toggle-sidebar').addEventListener('click', () => {
    const collapsed = sidebar.classList.toggle('collapsed');
    const btn = document.getElementById('toggle-sidebar');
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    chips.style.left = collapsed ? '24px' : `calc(var(--sidebar-w) + 24px)`;
    searchbar.style.marginLeft = collapsed ? '0' : `calc(var(--sidebar-w) / 2)`;
    // Let Leaflet recalculate after transition
    setTimeout(() => map.invalidateSize(), 320);
});

// ─── Map events ───────────────────────────────────────────────────────────────
map.on('moveend zoomend', scheduleLoad);

// ─── Boot ─────────────────────────────────────────────────────────────────────
(async function init() {
    await loadCities();
    loadListings();
})();
