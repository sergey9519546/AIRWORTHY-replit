// AIRWORTHY — Property comparison
// Independent per-property /v1/estimate calls, rendered side by side.
// Each entry (initial-from-URL, manually-added, or picked from saved
// properties) tracks its own loading/ready/error state so adding or
// removing one card never disturbs the others. All DOM writes are
// XSS-safe (textContent/DOM), matching the rest of AIRWORTHY.

(function () {
    'use strict';

    const AMENITY_LABELS = {
        pool: 'Private pool',
        hot_tub: 'Hot tub / spa',
        parking: 'Free parking',
        ev_charger: 'EV charger',
        gym: 'Home gym',
        pet_friendly: 'Pet-friendly',
        workspace: 'Dedicated workspace',
    };

    const grid = document.getElementById('compare-grid');
    const emptySection = document.getElementById('compare-empty');
    const nudge = document.getElementById('compare-nudge');
    const cardTemplate = document.getElementById('card-template');

    let entries = []; // { key, facts, status: 'loading'|'ready'|'error', data, error }
    let seq = 0;

    function formatCurrency(n) {
        if (typeof n !== 'number' || Number.isNaN(n)) return '—';
        return '$' + Math.round(n).toLocaleString('en-US');
    }
    function formatPercent(n) {
        if (typeof n !== 'number' || Number.isNaN(n)) return '—';
        return Math.round(n * 100) + '%';
    }
    function capitalize(s) {
        return typeof s === 'string' && s.length ? s[0].toUpperCase() + s.slice(1) : '—';
    }
    function normalizeAddress(a) {
        return (a || '').trim().toLowerCase();
    }

    // ---- Shareable/bookmarkable URL ----
    // The full set of compared properties (address + facts) is packed into a
    // single `p` query param so reloading or sharing the link restores the
    // exact same comparison, not just the first property.
    function syncUrl() {
        const url = new URL(window.location.href);
        if (entries.length) {
            const packed = entries.map((e) => ([
                e.facts.address,
                e.facts.bedrooms,
                e.facts.bathrooms,
                e.facts.accommodates,
                e.facts.nightly_rate,
            ]));
            url.searchParams.set('p', encodeURIComponent(JSON.stringify(packed)));
        } else {
            url.searchParams.delete('p');
        }
        // Legacy single-property params are superseded by `p` once present.
        url.searchParams.delete('address');
        url.searchParams.delete('bedrooms');
        url.searchParams.delete('bathrooms');
        url.searchParams.delete('accommodates');
        url.searchParams.delete('nightly_rate');
        window.history.replaceState(null, '', url.toString());
    }

    function parseUrlEntries() {
        const params = new URLSearchParams(window.location.search);
        const packedParam = params.get('p');
        if (packedParam) {
            try {
                const packed = JSON.parse(decodeURIComponent(packedParam));
                if (Array.isArray(packed)) {
                    return packed
                        .filter((row) => Array.isArray(row) && row[0])
                        .map(([address, bedrooms, bathrooms, accommodates, nightly_rate]) => ({
                            address,
                            bedrooms: parseInt(bedrooms, 10) || 1,
                            bathrooms: parseFloat(bathrooms) || 1,
                            accommodates: parseInt(accommodates, 10) || 2,
                            nightly_rate: parseFloat(nightly_rate) || 150,
                        }));
                }
            } catch (e) {
                // Malformed/tampered link — fall through to legacy handling.
            }
        }
        // Legacy single-property link (e.g. from the homepage/report "Compare" link).
        const address = params.get('address');
        if (address) {
            return [{
                address,
                bedrooms: parseInt(params.get('bedrooms'), 10) || 1,
                bathrooms: parseFloat(params.get('bathrooms')) || 1,
                accommodates: parseInt(params.get('accommodates'), 10) || 2,
                nightly_rate: parseFloat(params.get('nightly_rate')) || 150,
            }];
        }
        return [];
    }

    // ---- Entry management ----
    function addEntry(facts) {
        if (!facts || !facts.address) return;
        // Avoid adding the exact same address twice.
        if (entries.some((e) => normalizeAddress(e.facts.address) === normalizeAddress(facts.address))) {
            return;
        }
        const entry = { key: 'cmp_' + (++seq), facts, status: 'loading', data: null, error: null };
        entries.push(entry);
        renderAll();
        runEstimate(entry);
        syncUrl();
        return entry;
    }

    function removeEntry(key) {
        entries = entries.filter((e) => e.key !== key);
        renderAll();
        refreshSavedOptions();
        syncUrl();
    }

    async function runEstimate(entry) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        try {
            const resp = await fetch('/v1/estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(entry.facts),
                signal: controller.signal,
            });
            clearTimeout(timeout);
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                entry.status = 'error';
                entry.error = err;
            } else {
                entry.data = await resp.json();
                entry.status = 'ready';
            }
        } catch (err) {
            clearTimeout(timeout);
            entry.status = 'error';
            entry.error = {
                error: 'request_failed',
                detail: err.name === 'AbortError'
                    ? 'The request timed out. Please try again.'
                    : 'Something went wrong while reaching AIRWORTHY. Please try again.',
            };
        }
        renderCard(entry);
        refreshSavedOptions();
    }

    // ---- Rendering ----
    function renderAll() {
        emptySection.classList.toggle('hidden', entries.length !== 0);
        nudge.classList.toggle('hidden', entries.length !== 1);
        grid.innerHTML = '';
        entries.forEach((entry) => {
            const card = buildCardShell(entry);
            grid.appendChild(card);
            paintCard(entry);
        });
    }

    function renderCard(entry) {
        nudge.classList.toggle('hidden', entries.length !== 1);
        paintCard(entry);
    }

    function buildCardShell(entry) {
        const node = cardTemplate.content.firstElementChild.cloneNode(true);
        node.dataset.key = entry.key;
        node.querySelector('.compare-card-address').textContent = entry.facts.address;
        node.querySelector('.compare-card-remove').addEventListener('click', () => removeEntry(entry.key));
        return node;
    }

    function findCard(key) {
        return grid.querySelector(`.compare-card[data-key="${CSS.escape(key)}"]`);
    }

    function paintCard(entry) {
        const card = findCard(entry.key);
        if (!card) return;
        const body = card.querySelector('.compare-card-body');
        body.innerHTML = '';

        if (entry.status === 'loading') {
            const loading = document.createElement('div');
            loading.className = 'compare-card-loading';
            const dot = document.createElement('span');
            dot.className = 'compare-card-loading-dot';
            const text = document.createElement('span');
            text.textContent = 'Resolving estimate…';
            loading.appendChild(dot);
            loading.appendChild(text);
            body.appendChild(loading);
            return;
        }

        if (entry.status === 'error') {
            const box = document.createElement('div');
            box.className = 'compare-card-error';
            const titles = {
                geocoding_failed: "Couldn't locate this address",
                outside_coverage_area: 'Outside current coverage',
                invalid_input: "That doesn't look right",
                request_failed: 'Request failed',
            };
            const title = document.createElement('div');
            title.className = 'compare-card-error-title';
            title.textContent = titles[entry.error && entry.error.error] || 'Something went wrong';
            const detail = document.createElement('div');
            detail.textContent = (entry.error && entry.error.detail) || 'Please try again.';
            box.appendChild(title);
            box.appendChild(detail);
            body.appendChild(box);

            const retry = document.createElement('button');
            retry.type = 'button';
            retry.className = 'btn-secondary compare-card-error-retry';
            retry.textContent = 'Retry';
            retry.addEventListener('click', () => {
                entry.status = 'loading';
                paintCard(entry);
                runEstimate(entry);
            });
            body.appendChild(retry);
            return;
        }

        const data = entry.data;
        const facts = entry.facts;

        // AIRWORTHY verdict + score (shared component)
        const verdictSlot = document.createElement('div');
        body.appendChild(verdictSlot);
        AirworthyVerdict.render(verdictSlot, {
            score: data.airworthy_score,
            verdict: data.airworthy_verdict,
            reason: data.airworthy_reason,
            lowData: data.comps.length < 8,
        });

        // Earnings Envelope (shared component, dialed down via compare.css)
        const envelopeSlot = document.createElement('div');
        body.appendChild(envelopeSlot);
        AirworthyEnvelope.render(envelopeSlot, {
            downside: data.confidence.revenue_lower,
            upside: data.confidence.revenue_upper,
            mostLikely: data.annual_revenue,
            confidenceLevel: data.confidence.level,
            label: 'Est. annual revenue',
        });

        // Metrics: ADR, occupancy, confidence, comp quality
        const avgSimilarity = data.comps.length
            ? data.comps.reduce((s, c) => s + c.similarity_score, 0) / data.comps.length
            : null;
        const metrics = document.createElement('div');
        metrics.className = 'compare-metrics';
        [
            ['ADR', formatCurrency(data.market.adr) + '/night'],
            ['Occupancy', formatPercent(data.market.occupancy_rate)],
            ['Confidence', capitalize(data.confidence.level)],
            ['Comp quality', data.comps.length ? `${data.comps.length} comps · ${avgSimilarity.toFixed(2)} sim` : 'No comps'],
        ].forEach(([label, value]) => {
            const cell = document.createElement('div');
            cell.className = 'compare-metric';
            const l = document.createElement('span');
            l.className = 'compare-metric-label';
            l.textContent = label;
            const v = document.createElement('span');
            v.className = 'compare-metric-value';
            v.textContent = value;
            cell.appendChild(l);
            cell.appendChild(v);
            metrics.appendChild(cell);
        });
        body.appendChild(metrics);

        // Seasonality / monthly pattern sparkline
        const forecast = data.monthly_forecast || [];
        if (forecast.length) {
            const seasonWrap = document.createElement('div');
            const label = document.createElement('div');
            label.className = 'compare-section-label';
            label.textContent = 'Monthly pattern';
            seasonWrap.appendChild(label);

            const spark = document.createElement('div');
            spark.className = 'compare-sparkline';
            const maxExpected = Math.max(...forecast.map((m) => m.expected), 1);
            forecast.forEach((m) => {
                const bar = document.createElement('div');
                bar.className = 'compare-sparkline-bar';
                if (m.expected >= maxExpected * 0.97) bar.classList.add('peak');
                bar.style.height = Math.max((m.expected / maxExpected) * 100, 6) + '%';
                bar.title = `${m.month}: ${formatCurrency(m.expected)}`;
                spark.appendChild(bar);
            });
            seasonWrap.appendChild(spark);
            body.appendChild(seasonWrap);
        }

        // Key property features
        const featuresWrap = document.createElement('div');
        const featuresLabel = document.createElement('div');
        featuresLabel.className = 'compare-section-label';
        featuresLabel.textContent = 'Property features';
        featuresWrap.appendChild(featuresLabel);

        const featuresList = document.createElement('ul');
        featuresList.className = 'compare-features';
        const featureRows = [
            ['Bedrooms', facts.bedrooms === 0 ? 'Studio' : String(facts.bedrooms)],
            ['Bathrooms', String(facts.bathrooms)],
            ['Guests', String(facts.accommodates)],
            ['Nightly rate', formatCurrency(facts.nightly_rate)],
        ];
        if (facts.property_type) featureRows.push(['Type', facts.property_type]);
        if (facts.is_superhost) featureRows.push(['Host status', 'Superhost']);
        if (facts.amenities && facts.amenities.length) {
            featureRows.push(['Amenities', facts.amenities.map((k) => AMENITY_LABELS[k] || k).join(', ')]);
        }
        featureRows.forEach(([label, value]) => {
            const li = document.createElement('li');
            const l = document.createElement('span');
            l.className = 'compare-feature-label';
            l.textContent = label;
            const v = document.createElement('span');
            v.className = 'compare-feature-value';
            v.textContent = value;
            li.appendChild(l);
            li.appendChild(v);
            featuresList.appendChild(li);
        });
        featuresWrap.appendChild(featuresList);
        body.appendChild(featuresWrap);

        // Footer actions: full report + save
        const footer = document.createElement('div');
        footer.className = 'compare-card-footer';

        const reportParams = new URLSearchParams({
            address: data.address,
            bedrooms: String(facts.bedrooms),
            bathrooms: String(facts.bathrooms),
            accommodates: String(facts.accommodates),
            nightly_rate: String(facts.nightly_rate),
        });
        const reportLink = document.createElement('a');
        reportLink.href = `/property?${reportParams.toString()}`;
        reportLink.className = 'btn-secondary';
        reportLink.textContent = 'View report';
        footer.appendChild(reportLink);

        const saveBtn = document.createElement('button');
        saveBtn.type = 'button';
        saveBtn.className = 'btn-secondary';
        const snapshot = {
            address: data.address,
            lat: data.lat,
            lng: data.lng,
            annualRevenue: data.annual_revenue,
            revenueLower: data.confidence.revenue_lower,
            revenueUpper: data.confidence.revenue_upper,
            confidenceLevel: data.confidence.level,
            adr: data.market.adr,
            occupancyRate: data.market.occupancy_rate,
            bedrooms: facts.bedrooms,
            bathrooms: facts.bathrooms,
            accommodates: facts.accommodates,
            nightlyRate: facts.nightly_rate,
        };
        const savedId = AirworthySaved.makeId(snapshot);
        function paintSaveBtn() {
            const saved = AirworthySaved.has(savedId);
            saveBtn.textContent = saved ? 'Saved ✓' : 'Save';
            saveBtn.classList.toggle('is-saved', saved);
        }
        paintSaveBtn();
        saveBtn.addEventListener('click', () => {
            if (AirworthySaved.has(savedId)) {
                AirworthySaved.remove(savedId);
            } else {
                AirworthySaved.save(snapshot);
            }
            paintSaveBtn();
            refreshSavedOptions();
        });
        footer.appendChild(saveBtn);

        body.appendChild(footer);
    }

    // ---- Add by address form ----
    const addForm = document.getElementById('add-form');
    const addDetailsToggle = document.getElementById('add-details-toggle');
    const addDetailsPanel = document.getElementById('add-details-panel');

    addDetailsToggle.addEventListener('click', () => {
        const expanded = addDetailsToggle.getAttribute('aria-expanded') === 'true';
        addDetailsToggle.setAttribute('aria-expanded', String(!expanded));
        addDetailsPanel.classList.toggle('hidden', expanded);
    });

    addForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = document.getElementById('add-address');
        const address = input.value.trim();
        if (!address) {
            input.classList.add('input-invalid');
            input.focus();
            return;
        }
        input.classList.remove('input-invalid');
        addEntry({
            address,
            bedrooms: parseInt(document.getElementById('add-bedrooms').value, 10),
            bathrooms: parseFloat(document.getElementById('add-bathrooms').value),
            accommodates: parseInt(document.getElementById('add-accommodates').value, 10),
            nightly_rate: parseFloat(document.getElementById('add-nightly-rate').value),
        });
        input.value = '';
    });

    // ---- Add from saved properties ----
    const savedSelect = document.getElementById('add-saved-select');

    function refreshSavedOptions() {
        const saved = AirworthySaved.list();
        const addedAddresses = new Set(entries.map((e) => normalizeAddress(e.facts.address)));
        savedSelect.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = saved.length ? 'Choose a saved property…' : 'No saved properties yet';
        savedSelect.appendChild(placeholder);
        saved.forEach((p) => {
            const opt = document.createElement('option');
            opt.value = p.id;
            const already = addedAddresses.has(normalizeAddress(p.address));
            opt.textContent = p.address + (already ? ' (already added)' : '');
            opt.disabled = already;
            savedSelect.appendChild(opt);
        });
    }

    savedSelect.addEventListener('change', () => {
        const id = savedSelect.value;
        if (!id) return;
        const p = AirworthySaved.get(id);
        savedSelect.value = '';
        if (!p) return;
        addEntry({
            address: p.address,
            bedrooms: typeof p.bedrooms === 'number' ? p.bedrooms : 1,
            bathrooms: typeof p.bathrooms === 'number' ? p.bathrooms : 1,
            accommodates: typeof p.accommodates === 'number' ? p.accommodates : 2,
            nightly_rate: typeof p.nightlyRate === 'number' ? p.nightlyRate : 150,
        });
    });

    // ---- Boot: seed from URL (shareable/bookmarkable comparison link) ----
    const initialEntries = parseUrlEntries();
    if (initialEntries.length) {
        initialEntries.forEach((facts) => addEntry(facts));
    } else {
        renderAll();
    }
    refreshSavedOptions();
})();
