// Rentalizer Frontend — XSS-safe, Leaflet maps, request timeout

document.getElementById('estimate-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const form = e.target;
    const btn = document.getElementById('submit-btn');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');

    // Hide previous results
    error.classList.add('hidden');
    results.classList.add('hidden');
    loading.classList.remove('hidden');
    btn.disabled = true;

    const body = {
        address: form.address.value,
        bedrooms: parseInt(form.bedrooms.value),
        bathrooms: parseFloat(form.bathrooms.value),
        accommodates: parseInt(form.accommodates.value),
        nightly_rate: parseFloat(form.nightly_rate.value),
    };

    // FIX 15: Request timeout (15s)
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

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || err.error || 'Request failed');
        }

        const data = await resp.json();
        renderResults(data);
        results.classList.remove('hidden');
        results.focus(); // Accessibility: move focus to results
    } catch (err) {
        clearTimeout(timeout);
        let message = err.message;
        if (err.name === 'AbortError') {
            message = 'Request timed out. Please try again.';
        }
        document.getElementById('error-message').textContent = message;
        error.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
        btn.disabled = false;
    }
});

// FIX 5: All DOM manipulation uses textContent (XSS-safe)
function renderResults(data) {
    // Revenue range
    const lower = formatCurrency(data.confidence.revenue_lower);
    const upper = formatCurrency(data.confidence.revenue_upper);
    document.getElementById('revenue-range').textContent = `${lower} — ${upper}`;

    // Confidence badge
    const badge = document.getElementById('confidence-badge');
    badge.textContent = `${data.confidence.level.toUpperCase()} confidence`;
    badge.className = `confidence-badge ${data.confidence.level}`;

    // Confidence details — built safely with DOM APIs
    const confDetails = document.getElementById('confidence-details');
    confDetails.innerHTML = '';
    [
        ['Level', data.confidence.level],
        ['CV', data.confidence.cv.toFixed(2)],
        ['Range', `${lower} — ${upper}`],
    ].forEach(([label, value]) => {
        const row = document.createElement('div');
        row.className = 'stat-row';
        const lbl = document.createElement('span');
        lbl.className = 'stat-label';
        lbl.textContent = label;
        const val = document.createElement('span');
        val.className = 'stat-value';
        val.textContent = value;
        row.appendChild(lbl);
        row.appendChild(val);
        confDetails.appendChild(row);
    });

    // Market details — built safely with DOM APIs
    const marketDetails = document.getElementById('market-details');
    marketDetails.innerHTML = '';
    [
        ['Area', data.market.borough],
        ['Median Revenue', formatCurrency(data.market.median_revenue)],
        ['Median Price', `$${data.market.median_price}/night`],
        ['Active Listings', data.market.active_listings.toLocaleString()],
    ].forEach(([label, value]) => {
        const row = document.createElement('div');
        row.className = 'stat-row';
        const lbl = document.createElement('span');
        lbl.className = 'stat-label';
        lbl.textContent = label;
        const val = document.createElement('span');
        val.className = 'stat-value';
        val.textContent = value;
        row.appendChild(lbl);
        row.appendChild(val);
        marketDetails.appendChild(row);
    });

    // Comps — built safely with DOM APIs
    const compsList = document.getElementById('comps-list');
    compsList.innerHTML = '';

    // Header row
    const headerRow = document.createElement('div');
    headerRow.className = 'comp-item';
    ['Area', 'Beds', 'Revenue', 'Distance'].forEach(text => {
        const span = document.createElement('span');
        span.className = 'comp-header';
        span.textContent = text;
        headerRow.appendChild(span);
    });
    compsList.appendChild(headerRow);

    // Data rows
    for (const comp of data.comps) {
        const row = document.createElement('div');
        row.className = 'comp-item';
        [
            comp.borough,
            `${comp.bedrooms} BR`,
            formatCurrency(comp.revenue),
            `${comp.distance_km} km`,
        ].forEach(text => {
            const span = document.createElement('span');
            span.textContent = text;
            row.appendChild(span);
        });
        compsList.appendChild(row);
    }

    // Disclaimer
    document.getElementById('disclaimer').textContent = data.disclaimer;

    // FIX 6: Leaflet map (no Mapbox token needed)
    renderMap(data.lat, data.lng);
}

// FIX 6: Leaflet-based map (free, no API key required)
// Module-level reference so re-submitting the form doesn't try to
// initialize a second Leaflet instance on the same #map container —
// Leaflet throws "Map container is already initialized" if you do.
let propertyMap = null;

function renderMap(lat, lng) {
    const mapDiv = document.getElementById('map');

    if (propertyMap) {
        propertyMap.remove();
        propertyMap = null;
    }
    mapDiv.innerHTML = '';

    if (typeof L === 'undefined') {
        // Leaflet not loaded — fallback to OSM embed
        const bbox = `${lng-0.05},${lat-0.03},${lng+0.05},${lat+0.03}`;
        const iframe = document.createElement('iframe');
        iframe.style.cssText = 'width:100%;height:100%;border:0';
        iframe.src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat},${lng}`;
        mapDiv.appendChild(iframe);
        return;
    }

    const map = L.map('map').setView([lat, lng], 13);
    propertyMap = map;
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    // Property marker (red)
    const icon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background:#FF385C;width:14px;height:14px;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10],
    });

    L.marker([lat, lng], { icon })
        .bindPopup('<b>Your property</b>')
        .addTo(map);
}

function formatCurrency(n) {
    if (n >= 1000) {
        return '$' + Math.round(n).toLocaleString();
    }
    return '$' + Math.round(n);
}
