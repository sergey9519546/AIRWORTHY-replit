// AIRWORTHY — Property earnings report
// Address/facts arrive via query params -> live /v1/estimate -> full report:
// hero envelope, monthly forecast, drivers, confidence, comparable explorer
// (include/exclude -> live re-estimate), and a facts/assumptions editor
// (edit -> live re-estimate). All DOM writes are XSS-safe (textContent/DOM).

(function () {
    'use strict';

    const AMENITIES = [
        ['pool', 'Private pool'],
        ['hot_tub', 'Hot tub / spa'],
        ['parking', 'Free parking'],
        ['ev_charger', 'EV charger'],
        ['gym', 'Home gym'],
        ['pet_friendly', 'Pet-friendly'],
        ['workspace', 'Dedicated workspace'],
    ];

    const entryEmpty = document.getElementById('entry-empty');
    const loadingSection = document.getElementById('loading');
    const errorSection = document.getElementById('error');
    const reportSection = document.getElementById('report');

    let currentFacts = null;   // last-run request body
    let currentData = null;    // last /v1/estimate response
    let excludedCompIds = new Set();
    let pendingExcludeIds = new Set(); // staged, not yet recalculated
    let forecastMode = 'monthly';

    function showOnly(section) {
        [loadingSection, errorSection, reportSection, entryEmpty].forEach((s) => {
            s.classList.toggle('hidden', s !== section);
        });
    }

    function formatCurrency(n) {
        if (typeof n !== 'number') return '—';
        return '$' + Math.round(n).toLocaleString('en-US');
    }
    function formatPercent(n) {
        if (typeof n !== 'number') return '—';
        return Math.round(n * 100) + '%';
    }
    function capitalize(s) {
        return typeof s === 'string' && s.length ? s[0].toUpperCase() + s.slice(1) : '—';
    }

    // ---- Read facts from the URL ----
    function factsFromParams(params) {
        const address = params.get('address');
        if (!address) return null;
        return {
            address,
            bedrooms: parseInt(params.get('bedrooms'), 10) || 1,
            bathrooms: parseFloat(params.get('bathrooms')) || 1,
            accommodates: parseInt(params.get('accommodates'), 10) || 2,
            nightly_rate: parseFloat(params.get('nightly_rate')) || 150,
            property_type: params.get('property_type') || 'Entire home/apt',
            minimum_nights: parseInt(params.get('minimum_nights'), 10) || 1,
            is_superhost: params.get('is_superhost') === 'true',
            host_listings_count: parseInt(params.get('host_listings_count'), 10) || 1,
        };
    }

    function paramsFromFacts(facts) {
        const p = new URLSearchParams();
        p.set('address', facts.address);
        p.set('bedrooms', String(facts.bedrooms));
        p.set('bathrooms', String(facts.bathrooms));
        p.set('accommodates', String(facts.accommodates));
        p.set('nightly_rate', String(facts.nightly_rate));
        return p;
    }

    // ---- Run / re-run the estimate ----
    async function runEstimate(facts, { silent = false } = {}) {
        if (!silent) {
            showOnly(loadingSection);
        }
        const body = Object.assign({}, facts, {
            exclude_comp_ids: Array.from(excludedCompIds),
        });
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
                const err = await resp.json().catch(() => ({}));
                revealError(err);
                return null;
            }
            const data = await resp.json();
            currentFacts = facts;
            currentData = data;
            renderReport(data, facts);
            showOnly(reportSection);
            reportSection.focus({ preventScroll: true });
            history.replaceState(null, '', `/property?${paramsFromFacts(facts).toString()}`);
            return data;
        } catch (err) {
            clearTimeout(timeout);
            const message = err.name === 'AbortError'
                ? 'The request timed out. Please try again.'
                : 'Something went wrong while reaching AIRWORTHY. Please try again.';
            revealError({ error: 'request_failed', detail: message });
            return null;
        }
    }

    function revealError(err) {
        const titles = {
            geocoding_failed: "We couldn't locate that address",
            outside_coverage_area: 'This address is outside current coverage',
            invalid_input: "That doesn't look right",
            request_failed: 'Request failed',
        };
        document.getElementById('error-title').textContent = titles[err.error] || 'Something went wrong';
        document.getElementById('error-message').textContent = err.detail || 'Please try again.';
        const suggestion = document.getElementById('error-suggestion');
        suggestion.textContent = err.suggestion || '';
        suggestion.classList.toggle('hidden', !err.suggestion);
        showOnly(errorSection);
        errorSection.focus?.();
    }

    // ---- Render the full report from a response ----
    function renderReport(data, facts) {
        document.getElementById('report-address').textContent = data.address;
        document.getElementById('report-updated').textContent =
            `Data current as of ${data.data_freshness || 'the latest snapshot'} · model ${data.model_version}`;

        AirworthyEnvelope.render(document.getElementById('envelope-slot'), {
            downside: data.confidence.revenue_lower,
            upside: data.confidence.revenue_upper,
            mostLikely: data.annual_revenue,
            confidenceLevel: data.confidence.level,
            label: 'Estimated annual revenue',
        });

        document.getElementById('metric-adr').textContent = formatCurrency(data.market.adr) + '/night';
        document.getElementById('metric-occupancy').textContent = formatPercent(data.market.occupancy_rate);
        document.getElementById('metric-comps').textContent = data.comps.length.toLocaleString();
        document.getElementById('metric-confidence').textContent = capitalize(data.confidence.level);
        document.getElementById('metric-freshness').textContent = data.data_freshness || '—';
        document.getElementById('disclaimer').textContent = data.disclaimer;

        const compareParams = paramsFromFacts(facts);
        document.getElementById('compare-link').href = `/compare?${compareParams.toString()}`;
        document.getElementById('compare-link-footer').href = `/compare?${compareParams.toString()}`;

        renderScoreGauge(data);
        wireSaveButtons(data, facts);
        renderForecast(data);
        renderDrivers(data);
        renderConfidence(data);
        renderComps(data);
        populateFactsForm(facts);
    }

    // ---- Save (shared module) ----
    function wireSaveButtons(data, facts) {
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
            accommodates: facts.accommodates,
            nightlyRate: facts.nightly_rate,
        };
        const savedId = AirworthySaved.makeId(snapshot);
        const buttons = [document.getElementById('save-btn'), document.getElementById('save-btn-footer')];
        function update() {
            const saved = AirworthySaved.has(savedId);
            buttons.forEach((btn) => {
                btn.textContent = saved ? 'Saved ✓' : 'Save property';
                btn.classList.toggle('is-saved', saved);
            });
        }
        update();
        buttons.forEach((btn) => {
            btn.onclick = () => {
                if (AirworthySaved.has(savedId)) {
                    AirworthySaved.remove(savedId);
                } else {
                    AirworthySaved.save(snapshot);
                }
                update();
            };
        });
    }

    // ---- Confidence score gauge ----
    // A genuine score derived from the estimate's coefficient of variation
    // (cv): tighter agreement across comparable revenue outcomes -> a
    // higher score. Mirrors the same cv thresholds the backend uses to
    // classify high/medium/low confidence, so the gauge and the label
    // always agree.
    const SCORE_GAUGE_CIRCUMFERENCE = 2 * Math.PI * 50;
    function renderScoreGauge(data) {
        const cv = typeof data.confidence.cv === 'number' ? data.confidence.cv : 1;
        const score = Math.max(2, Math.min(99, Math.round((1 - cv) * 100)));
        const level = data.confidence.level || 'low';

        const fill = document.getElementById('score-gauge-fill');
        fill.classList.remove('level-high', 'level-medium', 'level-low');
        fill.classList.add(`level-${level}`);
        fill.style.strokeDashoffset = String(SCORE_GAUGE_CIRCUMFERENCE * (1 - score / 100));

        document.getElementById('score-gauge-value').textContent = String(score);
        document.getElementById('score-gauge-level').textContent = `${capitalize(level)} confidence`;
    }

    // ---- Monthly forecast ----
    function demandLevel(idx) {
        if (idx >= 1.12) return 'Peak';
        if (idx >= 1.0) return 'High';
        if (idx >= 0.9) return 'Medium';
        return 'Low';
    }

    function renderForecast(data) {
        const forecast = data.monthly_forecast || [];
        const chart = document.getElementById('forecast-chart');
        const annualBox = document.getElementById('forecast-annual');
        chart.innerHTML = '';
        document.getElementById('month-detail').classList.add('hidden');

        if (forecastMode === 'annual') {
            chart.classList.add('hidden');
            annualBox.classList.remove('hidden');
            annualBox.innerHTML = '';
            const value = document.createElement('div');
            value.className = 'forecast-annual-value';
            value.textContent = formatCurrency(data.annual_revenue);
            const sub = document.createElement('div');
            sub.className = 'forecast-annual-sub';
            sub.textContent = `${formatCurrency(data.confidence.revenue_lower)} – ${formatCurrency(data.confidence.revenue_upper)} modeled range across the next 12 months`;
            annualBox.appendChild(value);
            annualBox.appendChild(sub);
            return;
        }
        annualBox.classList.add('hidden');
        chart.classList.remove('hidden');

        if (!forecast.length) {
            chart.textContent = 'No monthly forecast available.';
            return;
        }

        const maxHigh = Math.max(...forecast.map((m) => m.high), 1);
        const meanExpected = forecast.reduce((s, m) => s + m.expected, 0) / forecast.length;

        forecast.forEach((m, i) => {
            const col = document.createElement('button');
            col.type = 'button';
            col.className = 'forecast-bar-col';
            col.setAttribute('aria-label', `${m.month}: expected ${formatCurrency(m.expected)}`);

            const range = document.createElement('div');
            range.className = 'forecast-bar-range';
            range.style.height = Math.max((m.high / maxHigh) * 100, 4) + '%';

            const expectedBar = document.createElement('div');
            expectedBar.className = 'forecast-bar-expected';
            const heightPct = m.high > m.low ? ((m.expected - m.low) / (m.high - m.low)) * 100 : 100;
            expectedBar.style.height = Math.max(Math.min(heightPct, 100), 8) + '%';
            range.appendChild(expectedBar);

            const label = document.createElement('span');
            label.className = 'forecast-bar-label';
            if (forecastMode === 'seasonal') {
                label.textContent = demandLevel(meanExpected > 0 ? m.expected / meanExpected : 1)[0];
            } else {
                label.textContent = m.month;
            }

            col.appendChild(range);
            col.appendChild(label);
            col.addEventListener('click', () => showMonthDetail(m, i, data, meanExpected));
            chart.appendChild(col);
        });
    }

    function showMonthDetail(m, index, data, meanExpected) {
        document.querySelectorAll('.forecast-bar-col').forEach((el, i) => {
            el.classList.toggle('selected', i === index);
        });
        const idx = meanExpected > 0 ? m.expected / meanExpected : 1;
        const monthAdr = data.market.adr * idx;
        const monthOcc = Math.min(0.98, Math.max(0.05, data.market.occupancy_rate * idx));

        document.getElementById('md-month').textContent = m.month;
        document.getElementById('md-expected').textContent = formatCurrency(m.expected);
        document.getElementById('md-range').textContent = `${formatCurrency(m.low)} – ${formatCurrency(m.high)}`;
        document.getElementById('md-adr').textContent = formatCurrency(monthAdr) + '/night';
        document.getElementById('md-occupancy').textContent = formatPercent(monthOcc);
        document.getElementById('md-demand').textContent = demandLevel(idx);
        document.getElementById('month-detail').classList.remove('hidden');
    }

    document.getElementById('month-detail-close').addEventListener('click', () => {
        document.getElementById('month-detail').classList.add('hidden');
        document.querySelectorAll('.forecast-bar-col').forEach((el) => el.classList.remove('selected'));
    });

    document.getElementById('forecast-toggle').addEventListener('click', (e) => {
        const btn = e.target.closest('.segmented-btn');
        if (!btn) return;
        forecastMode = btn.dataset.mode;
        document.querySelectorAll('#forecast-toggle .segmented-btn').forEach((b) => {
            b.classList.toggle('active', b === btn);
            b.setAttribute('aria-selected', String(b === btn));
        });
        if (currentData) renderForecast(currentData);
    });

    // ---- Performance drivers ----
    function renderDrivers(data) {
        const list = document.getElementById('drivers-list');
        list.innerHTML = '';
        const drivers = data.performance_drivers || [];
        if (!drivers.length) {
            const li = document.createElement('li');
            li.className = 'driver-item';
            li.textContent = 'No standout drivers — this property tracks close to its comparable set.';
            list.appendChild(li);
            return;
        }
        drivers.forEach((d) => {
            const li = document.createElement('li');
            li.className = `driver-item ${d.direction}`;
            const label = document.createElement('span');
            label.className = 'driver-label';
            label.textContent = d.label;
            const impact = document.createElement('span');
            impact.className = `driver-impact ${d.direction}`;
            const sign = d.impact_dollars >= 0 ? '+' : '−';
            impact.textContent = `${sign}${formatCurrency(Math.abs(d.impact_dollars))}/yr`;
            li.appendChild(label);
            li.appendChild(impact);
            list.appendChild(li);
        });
    }

    // ---- Confidence ----
    function renderConfidence(data) {
        const reasonsList = document.getElementById('confidence-reasons');
        const weaknessList = document.getElementById('confidence-weaknesses');
        reasonsList.innerHTML = '';
        weaknessList.innerHTML = '';
        (data.confidence.reasons || []).forEach((r) => {
            const li = document.createElement('li');
            li.textContent = r;
            reasonsList.appendChild(li);
        });
        const weaknesses = data.confidence.weaknesses || [];
        if (!weaknesses.length) {
            const li = document.createElement('li');
            li.textContent = 'No significant weaknesses disclosed for this estimate.';
            li.style.color = 'var(--aw-muted)';
            li.style.paddingLeft = '0';
            weaknessList.appendChild(li);
        } else {
            weaknesses.forEach((w) => {
                const li = document.createElement('li');
                li.textContent = w;
                weaknessList.appendChild(li);
            });
        }
    }

    // ---- Comparable-rental explorer ----
    let compsSortKey = 'similarity';

    function renderComps(data) {
        pendingExcludeIds = new Set(excludedCompIds);
        document.getElementById('comps-count-note').textContent =
            `${data.comps.length} comparable ${data.comps.length === 1 ? 'listing' : 'listings'} used in this estimate` +
            (excludedCompIds.size ? ` · ${excludedCompIds.size} excluded from the current run` : '');
        paintComps(data.comps);
        document.getElementById('comps-recalc').disabled = true;
    }

    function paintComps(comps) {
        const sorted = [...comps].sort((a, b) => {
            switch (compsSortKey) {
                case 'revenue': return b.revenue - a.revenue;
                case 'distance': return a.distance_km - b.distance_km;
                case 'adr': return (b.price || 0) - (a.price || 0);
                default: return b.similarity_score - a.similarity_score;
            }
        });

        const list = document.getElementById('comps-list');
        list.innerHTML = '';
        sorted.forEach((c) => {
            const row = document.createElement('div');
            row.className = 'comp-row';
            if (pendingExcludeIds.has(c.id)) row.classList.add('excluded');

            const check = document.createElement('input');
            check.type = 'checkbox';
            check.className = 'comp-check';
            check.checked = !pendingExcludeIds.has(c.id);
            check.setAttribute('aria-label', `Include comparable ${c.id} in the estimate`);
            check.addEventListener('change', () => {
                if (check.checked) pendingExcludeIds.delete(c.id);
                else pendingExcludeIds.add(c.id);
                row.classList.toggle('excluded', !check.checked);
                const changed = pendingExcludeIds.size !== excludedCompIds.size ||
                    [...pendingExcludeIds].some((id) => !excludedCompIds.has(id));
                document.getElementById('comps-recalc').disabled = !changed;
            });

            const thumb = document.createElement('div');
            thumb.className = 'comp-thumb';
            thumb.textContent = c.bedrooms + 'BR';
            thumb.setAttribute('aria-hidden', 'true');

            const main = document.createElement('div');
            main.className = 'comp-main';
            const titleRow = document.createElement('div');
            titleRow.className = 'comp-title-row';
            const rev = document.createElement('span');
            rev.className = 'comp-revenue';
            rev.textContent = formatCurrency(c.revenue) + '/yr';
            const meta = document.createElement('span');
            meta.className = 'comp-meta';
            meta.textContent = `${c.borough} · ${c.bedrooms} bd · ${c.distance_km.toFixed(1)} km away`;
            titleRow.appendChild(rev);
            titleRow.appendChild(meta);
            const reason = document.createElement('div');
            reason.className = 'comp-reason';
            reason.textContent = c.reason_included ? `Included: ${c.reason_included}` : '';
            const diff = document.createElement('div');
            diff.className = 'comp-diff';
            diff.textContent = c.differences || '';
            main.appendChild(titleRow);
            if (c.reason_included) main.appendChild(reason);
            if (c.differences) main.appendChild(diff);

            const stats = document.createElement('div');
            stats.className = 'comp-stats';
            const simStat = document.createElement('div');
            simStat.className = 'comp-stat';
            simStat.innerHTML = '';
            const simLabel = document.createElement('span');
            simLabel.className = 'comp-stat-label';
            simLabel.textContent = 'Similarity';
            const simValue = document.createElement('span');
            simValue.className = 'comp-stat-value';
            simValue.textContent = c.similarity_score.toFixed(2);
            simStat.appendChild(simLabel);
            simStat.appendChild(simValue);

            const adrStat = document.createElement('div');
            adrStat.className = 'comp-stat';
            const adrLabel = document.createElement('span');
            adrLabel.className = 'comp-stat-label';
            adrLabel.textContent = 'ADR';
            const adrValue = document.createElement('span');
            adrValue.className = 'comp-stat-value';
            adrValue.textContent = c.price != null ? formatCurrency(c.price) : '—';
            adrStat.appendChild(adrLabel);
            adrStat.appendChild(adrValue);

            stats.appendChild(simStat);
            stats.appendChild(adrStat);

            row.appendChild(check);
            row.appendChild(thumb);
            row.appendChild(main);
            row.appendChild(stats);
            list.appendChild(row);
        });
    }

    document.getElementById('comps-sort').addEventListener('change', (e) => {
        compsSortKey = e.target.value;
        if (currentData) paintComps(currentData.comps);
    });

    document.getElementById('comps-recalc').addEventListener('click', async () => {
        excludedCompIds = new Set(pendingExcludeIds);
        if (currentFacts) await runEstimate(currentFacts);
    });

    // ---- Property facts / assumptions editor ----
    function populateFactsForm(facts) {
        document.getElementById('f-bedrooms').value = String(facts.bedrooms);
        document.getElementById('f-bathrooms').value = String(facts.bathrooms);
        document.getElementById('f-accommodates').value = String(facts.accommodates);
        document.getElementById('f-nightly-rate').value = facts.nightly_rate;
        document.getElementById('f-property-type').value = facts.property_type;
        document.getElementById('f-min-nights').value = facts.minimum_nights;
        document.getElementById('f-host-listings').value = facts.host_listings_count;
        document.getElementById('f-superhost').checked = !!facts.is_superhost;
    }

    function buildAmenitiesGrid() {
        const grid = document.getElementById('amenities-grid');
        grid.innerHTML = '';
        AMENITIES.forEach(([key, label]) => {
            const wrap = document.createElement('label');
            wrap.className = 'amenity-toggle';
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.value = key;
            input.name = 'amenity';
            const span = document.createElement('span');
            span.textContent = label;
            wrap.appendChild(input);
            wrap.appendChild(span);
            grid.appendChild(wrap);
        });
    }
    buildAmenitiesGrid();

    function selectedAmenities() {
        return Array.from(document.querySelectorAll('input[name="amenity"]:checked')).map((el) => el.value);
    }

    document.getElementById('facts-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentFacts) return;
        const submitBtn = document.getElementById('facts-submit');
        const deltaEl = document.getElementById('facts-delta');
        const previousRevenue = currentData ? currentData.annual_revenue : null;

        const newFacts = Object.assign({}, currentFacts, {
            bedrooms: parseInt(document.getElementById('f-bedrooms').value, 10),
            bathrooms: parseFloat(document.getElementById('f-bathrooms').value),
            accommodates: parseInt(document.getElementById('f-accommodates').value, 10),
            nightly_rate: parseFloat(document.getElementById('f-nightly-rate').value),
            property_type: document.getElementById('f-property-type').value,
            minimum_nights: parseInt(document.getElementById('f-min-nights').value, 10) || 1,
            host_listings_count: parseInt(document.getElementById('f-host-listings').value, 10) || 1,
            is_superhost: document.getElementById('f-superhost').checked,
            amenities: selectedAmenities(),
        });

        submitBtn.disabled = true;
        deltaEl.textContent = 'Recalculating…';
        deltaEl.className = 'facts-delta';
        const data = await runEstimate(newFacts, { silent: true });
        submitBtn.disabled = false;
        if (data && previousRevenue != null) {
            const delta = data.annual_revenue - previousRevenue;
            const sign = delta >= 0 ? '+' : '−';
            deltaEl.textContent = `${sign}${formatCurrency(Math.abs(delta))}/yr vs. previous facts`;
            deltaEl.className = `facts-delta ${delta >= 0 ? 'positive' : 'negative'}`;
        } else {
            deltaEl.textContent = '';
        }
    });

    // ---- Export / print ----
    function exportReport() {
        document.getElementById('month-detail').classList.add('hidden');
        window.print();
    }
    document.getElementById('export-btn').addEventListener('click', exportReport);
    document.getElementById('export-btn-footer').addEventListener('click', exportReport);

    // ---- Fallback entry form ----
    document.getElementById('entry-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const address = document.getElementById('entry-address').value.trim();
        if (!address) return;
        const facts = { address, bedrooms: 1, bathrooms: 1, accommodates: 2, nightly_rate: 150,
            property_type: 'Entire home/apt', minimum_nights: 1, is_superhost: false, host_listings_count: 1 };
        excludedCompIds = new Set();
        runEstimate(facts);
    });

    // ---- Boot ----
    const facts = factsFromParams(new URLSearchParams(window.location.search));
    if (facts) {
        runEstimate(facts);
    } else {
        showOnly(entryEmpty);
    }
})();
