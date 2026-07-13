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
    let originalFacts = null;  // facts as first loaded, for "reset to original"
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
                headers: apiHeaders(),
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

        AirworthyVerdict.render(document.getElementById('verdict-slot'), {
            score: data.airworthy_score,
            verdict: data.airworthy_verdict,
            reason: data.airworthy_reason,
            lowData: data.comps.length < 8,
        });

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

        renderPhoto(data);
        renderParcel(data);
        renderScoreGauge(data);
        wireSaveButtons(data, facts);
        renderDecisionSummary(data);
        renderForecast(data);
        renderDrivers(data);
        renderConfidence(data);
        renderComps(data);
        populateFactsForm(facts);
        renderFactsStatus();
        renderScenario(data);
        renderFooterVerdict(data);
    }

    // ---- Hero photo: a real scraped photo of the searched property ----
    // Degrades gracefully: hidden when no photo was found, and hidden again if
    // the source image URL fails to load (no broken-image icon).
    function renderPhoto(data) {
        const figure = document.getElementById('report-photo-figure');
        const img = document.getElementById('report-photo');
        const sourceLink = document.getElementById('report-photo-source');
        const photo = data.photo;
        if (!photo || !photo.photo_url) {
            figure.hidden = true;
            img.removeAttribute('src');
            return;
        }
        img.onerror = () => { figure.hidden = true; };
        img.alt = `Photo of ${data.address}`;
        img.src = photo.photo_url;
        if (photo.source_url) {
            sourceLink.href = photo.source_url;
            sourceLink.textContent = photo.source_site || 'source';
        } else {
            sourceLink.removeAttribute('href');
            sourceLink.textContent = photo.source_site || 'source';
        }
        figure.hidden = false;
    }

    // ---- Public-records property facts (Realie) ----
    function renderParcel(data) {
        const section = document.getElementById('parcel-section');
        const dl = document.getElementById('parcel-facts');
        const parcel = data.parcel;
        dl.innerHTML = '';
        if (!parcel) {
            section.hidden = true;
            return;
        }

        // Realie represents "not recorded for this parcel" as 0 for numeric
        // measurement fields, so a positive value is required before we show
        // one — otherwise we'd print misleading "0 sq ft" / "$0" facts.
        const pos = (n) => (typeof n === 'number' && n > 0 ? n : null);
        const fmtInt = (n) => Math.round(n).toLocaleString('en-US');
        const rows = [
            ['Year built', pos(parcel.year_built) ? String(parcel.year_built) : null],
            ['Lot size', pos(parcel.lot_acres) != null ? `${parcel.lot_acres.toLocaleString('en-US', { maximumFractionDigits: 2 })} acres` : null],
            ['Building area', pos(parcel.building_area_sqft) != null ? `${fmtInt(parcel.building_area_sqft)} sq ft` : null],
            ['Bedrooms', pos(parcel.bedrooms) != null ? String(parcel.bedrooms) : null],
            ['Bathrooms', pos(parcel.bathrooms) != null ? String(parcel.bathrooms) : null],
            ['Stories', pos(parcel.stories) != null ? String(parcel.stories) : null],
            ['Garage', parcel.has_garage == null ? null : (parcel.has_garage ? 'Yes' : 'No')],
            ['Pool', parcel.has_pool == null ? null : (parcel.has_pool ? 'Yes' : 'No')],
            ['Construction', parcel.construction_type || null],
            ['Roof', parcel.roof_type || null],
            ['Assessed value', pos(parcel.assessed_market_value) != null ? formatCurrency(parcel.assessed_market_value) : null],
            ['Estimated value (AVM)', pos(parcel.avm_value) != null ? formatCurrency(parcel.avm_value) : null],
            ['Last sale price', pos(parcel.last_sale_price) != null ? formatCurrency(parcel.last_sale_price) : null],
            ['Last sale date', parcel.last_sale_date || null],
            ['Owner', parcel.owner_name || null],
        ].filter(([, value]) => value != null && value !== '');

        if (!rows.length) {
            section.hidden = true;
            return;
        }

        rows.forEach(([label, value]) => {
            const dt = document.createElement('dt');
            dt.className = 'parcel-fact-label';
            dt.textContent = label;
            const dd = document.createElement('dd');
            dd.className = 'parcel-fact-value';
            dd.textContent = value;
            dl.appendChild(dt);
            dl.appendChild(dd);
        });
        section.hidden = false;
    }

    // ---- Decision summary: a plain-language paragraph explaining the verdict ----
    function renderDecisionSummary(data) {
        const verdict = data.airworthy_verdict || 'GROUNDED';
        const level = data.confidence.level || 'low';
        const compCount = data.comps.length;
        const drivers = data.performance_drivers || [];
        const topDriver = drivers.length ? drivers.slice().sort((a, b) => Math.abs(b.impact_dollars) - Math.abs(a.impact_dollars))[0] : null;

        const verdictOpeners = {
            CLEARED: 'This property clears the bar for strong short-term-rental performance.',
            CONDITIONAL: 'This property is viable, but its performance depends on the assumptions holding up.',
            EXPOSED: "This property's projection is financially sensitive — small changes in facts or comps move the outcome meaningfully.",
            GROUNDED: 'This property currently shows insufficient earnings potential to clear the bar.',
        };
        const opener = verdictOpeners[verdict] || verdictOpeners.GROUNDED;

        const rangeSentence = `The modeled range is ${formatCurrency(data.confidence.revenue_lower)} to ${formatCurrency(data.confidence.revenue_upper)} per year, with ${formatCurrency(data.annual_revenue)} as the most likely outcome at ${level} confidence.`;

        const evidenceSentence = compCount >= 8
            ? `That estimate is backed by ${compCount} comparable listings in the area.`
            : `That estimate rests on a thinner set of ${compCount} comparable listing${compCount === 1 ? '' : 's'}, so treat it as provisional.`;

        let driverSentence = '';
        if (topDriver) {
            const dir = topDriver.impact_dollars >= 0 ? 'pushing revenue up' : 'pulling revenue down';
            driverSentence = ` The single biggest factor is "${topDriver.label}," ${dir} by roughly ${formatCurrency(Math.abs(topDriver.impact_dollars))} a year.`;
        }

        document.getElementById('decision-summary').textContent =
            `${opener} ${rangeSentence} ${evidenceSentence}${driverSentence}`;
    }

    // ---- Decision footer: verdict recap above the actions ----
    function renderFooterVerdict(data) {
        const el = document.getElementById('footer-verdict');
        el.textContent = `Verdict: ${data.airworthy_verdict} — ${data.airworthy_reason}`;
        el.className = `footer-verdict footer-verdict-${String(data.airworthy_verdict || 'grounded').toLowerCase()}`;
    }

    // ---- Scenario laboratory: net revenue under real operating costs ----
    // Pure post-processing over the current estimate's revenue numbers — no
    // backend round-trip. Recomputes on every input change.
    const scenarioInputs = {
        cleaning: document.getElementById('s-cleaning-fee'),
        management: document.getElementById('s-management-fee'),
        platform: document.getElementById('s-platform-fee'),
        opex: document.getElementById('s-opex'),
    };

    function readScenarioAssumptions() {
        const pct = (el) => Math.max(0, Math.min(100, parseFloat(el.value) || 0)) / 100;
        return {
            cleaningPct: pct(scenarioInputs.cleaning),
            managementPct: pct(scenarioInputs.management),
            platformPct: pct(scenarioInputs.platform),
            monthlyOpex: Math.max(0, parseFloat(scenarioInputs.opex.value) || 0),
        };
    }

    function netForRevenue(revenue, assumptions) {
        const feePct = assumptions.cleaningPct + assumptions.managementPct + assumptions.platformPct;
        const variableCosts = revenue * feePct;
        const fixedCosts = assumptions.monthlyOpex * 12;
        const totalCosts = variableCosts + fixedCosts;
        return { net: revenue - totalCosts, totalCosts };
    }

    function renderScenario(data) {
        const assumptions = readScenarioAssumptions();
        const gross = netForRevenue(data.annual_revenue, assumptions);
        const lower = netForRevenue(data.confidence.revenue_lower, assumptions);
        const upper = netForRevenue(data.confidence.revenue_upper, assumptions);

        document.getElementById('scenario-gross').textContent = formatCurrency(data.annual_revenue) + '/yr';
        document.getElementById('scenario-costs').textContent = formatCurrency(gross.totalCosts) + '/yr';
        document.getElementById('scenario-net').textContent = formatCurrency(gross.net) + '/yr';
        document.getElementById('scenario-net-range').textContent =
            `${formatCurrency(lower.net)} – ${formatCurrency(upper.net)}`;

        const verdict = document.getElementById('scenario-verdict');
        if (gross.net >= 0) {
            verdict.textContent = 'Cash-flow positive';
            verdict.classList.remove('negative');
            verdict.classList.add('positive');
        } else {
            verdict.textContent = 'Cash-flow negative';
            verdict.classList.remove('positive');
            verdict.classList.add('negative');
        }
    }

    Object.values(scenarioInputs).forEach((input) => {
        input.addEventListener('input', () => {
            if (currentData) renderScenario(currentData);
        });
    });

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
            bathrooms: facts.bathrooms,
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
    function demandTierClass(idx) {
        return 'tier-' + demandLevel(idx).toLowerCase();
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

            const range = document.createElement('div');
            range.className = 'forecast-bar-range';
            range.style.height = Math.max((m.high / maxHigh) * 100, 4) + '%';

            const idxForTier = meanExpected > 0 ? m.expected / meanExpected : 1;
            const expectedBar = document.createElement('div');
            expectedBar.className = `forecast-bar-expected ${demandTierClass(idxForTier)}`;
            const heightPct = m.high > m.low ? ((m.expected - m.low) / (m.high - m.low)) * 100 : 100;
            expectedBar.style.height = Math.max(Math.min(heightPct, 100), 8) + '%';
            range.appendChild(expectedBar);
            col.setAttribute('aria-label', `${m.month}: expected ${formatCurrency(m.expected)}, range ${formatCurrency(m.low)} to ${formatCurrency(m.high)}, ${demandLevel(idxForTier)} demand`);

            const label = document.createElement('span');
            label.className = 'forecast-bar-label';
            if (forecastMode === 'seasonal') {
                label.textContent = demandLevel(idxForTier)[0];
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

    const SIMILARITY_TIERS = [
        { key: 'strong', label: 'Strong match', min: 0.8 },
        { key: 'reasonable', label: 'Reasonable match', min: 0.5 },
        { key: 'weak', label: 'Weak match', min: 0 },
    ];
    function tierFor(score) {
        return SIMILARITY_TIERS.find((t) => score >= t.min) || SIMILARITY_TIERS[SIMILARITY_TIERS.length - 1];
    }

    // A comp's real listing photo (with a link to its Airbnb source) when
    // available, falling back to the bedroom-count chip. Fails cleanly when a
    // listing has no photo or the image URL 404s.
    function buildCompThumb(c) {
        const hasPhoto = !!c.picture_url;
        const thumb = document.createElement(c.listing_url ? 'a' : 'div');
        thumb.className = 'comp-thumb' + (hasPhoto ? ' comp-thumb-photo' : '');
        if (c.listing_url) {
            thumb.href = c.listing_url;
            thumb.target = '_blank';
            thumb.rel = 'noopener noreferrer';
            thumb.title = 'View on Airbnb';
        }
        const fallback = document.createElement('span');
        fallback.className = 'comp-thumb-fallback';
        fallback.textContent = c.bedrooms + 'BR';
        thumb.appendChild(fallback);
        if (hasPhoto) {
            const img = document.createElement('img');
            img.className = 'comp-thumb-img';
            img.alt = '';
            img.loading = 'lazy';
            img.decoding = 'async';
            img.onerror = () => { img.remove(); thumb.classList.remove('comp-thumb-photo'); };
            img.src = c.picture_url;
            thumb.appendChild(img);
        } else {
            thumb.setAttribute('aria-hidden', 'true');
        }
        return thumb;
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

        // Positioned "by similarity" — a constellation of tiers, not a flat
        // distance-sorted table. Only grouped when sorted by similarity;
        // other sorts stay a flat list so the chosen order stays literal.
        let lastTierKey = null;
        const groupBySimilarity = compsSortKey === 'similarity';

        sorted.forEach((c) => {
            if (groupBySimilarity) {
                const tier = tierFor(c.similarity_score);
                if (tier.key !== lastTierKey) {
                    lastTierKey = tier.key;
                    const heading = document.createElement('div');
                    heading.className = `comp-tier-heading comp-tier-${tier.key}`;
                    heading.textContent = tier.label;
                    list.appendChild(heading);
                }
            }
            const row = document.createElement('div');
            row.className = `comp-row comp-tier-${tierFor(c.similarity_score).key}`;
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

            const thumb = buildCompThumb(c);

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
        (facts.amenities || []).forEach((key) => {
            const input = document.querySelector(`input[name="amenity"][value="${key}"]`);
            if (input) input.checked = true;
        });
    }

    function factsEqual(a, b) {
        if (!a || !b) return false;
        const keys = ['bedrooms', 'bathrooms', 'accommodates', 'nightly_rate', 'property_type', 'minimum_nights', 'host_listings_count', 'is_superhost'];
        if (keys.some((k) => a[k] !== b[k])) return false;
        const aAmen = (a.amenities || []).slice().sort().join(',');
        const bAmen = (b.amenities || []).slice().sort().join(',');
        return aAmen === bAmen;
    }

    // Verified-vs-edited distinction: shows whether the facts currently
    // driving the estimate still match the original entry, and reveals a
    // "reset to original" escape hatch once they diverge.
    function renderFactsStatus() {
        const status = document.getElementById('facts-status');
        const resetBtn = document.getElementById('facts-reset');
        const edited = !factsEqual(currentFacts, originalFacts);
        status.textContent = edited ? 'Edited from original entry' : 'Verified against original entry';
        status.className = `facts-status ${edited ? 'facts-status-edited' : 'facts-status-verified'}`;
        resetBtn.classList.toggle('hidden', !edited);
    }

    document.getElementById('facts-reset').addEventListener('click', async () => {
        if (!originalFacts) return;
        excludedCompIds = new Set();
        const deltaEl = document.getElementById('facts-delta');
        const previousRevenue = currentData ? currentData.annual_revenue : null;
        const data = await runEstimate(Object.assign({}, originalFacts), { silent: true });
        if (data && previousRevenue != null) {
            const delta = data.annual_revenue - previousRevenue;
            const sign = delta >= 0 ? '+' : '−';
            deltaEl.textContent = `${sign}${formatCurrency(Math.abs(delta))}/yr vs. previous edit — reset to original facts`;
            deltaEl.className = `facts-delta ${delta >= 0 ? 'positive' : 'negative'}`;
        } else {
            deltaEl.textContent = 'Reset to original facts.';
            deltaEl.className = 'facts-delta';
        }
    });

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
        renderFactsStatus();
        if (data && previousRevenue != null) {
            const delta = data.annual_revenue - previousRevenue;
            const sign = delta >= 0 ? '+' : '−';
            deltaEl.textContent = `${sign}${formatCurrency(Math.abs(delta))}/yr vs. previous facts`;
            deltaEl.className = `facts-delta ${delta >= 0 ? 'positive' : 'negative'}`;
        } else {
            deltaEl.textContent = '';
        }
    });

    // ---- Export: a genuine downloadable report artifact ----
    // Builds a self-contained, styled HTML document from the current
    // estimate and triggers a browser download — a real report artifact,
    // not just a bare window.print() of the interactive dashboard.
    function escapeHtml(s) {
        const div = document.createElement('div');
        div.textContent = String(s == null ? '' : s);
        return div.innerHTML;
    }

    function buildReportHtml(data, facts) {
        const drivers = (data.performance_drivers || []).map((d) => {
            const sign = d.impact_dollars >= 0 ? '+' : '−';
            const cls = d.impact_dollars >= 0 ? 'pos' : 'neg';
            return `<tr><td>${escapeHtml(d.label)}</td><td class="num ${cls}">${sign}${formatCurrency(Math.abs(d.impact_dollars))}/yr</td></tr>`;
        }).join('') || '<tr><td colspan="2">No standout drivers.</td></tr>';

        const comps = [...data.comps]
            .sort((a, b) => b.similarity_score - a.similarity_score)
            .slice(0, 15)
            .map((c) => `<tr><td>${escapeHtml(c.borough)} · ${c.bedrooms} bd</td><td class="num">${c.similarity_score.toFixed(2)}</td><td class="num">${formatCurrency(c.revenue)}/yr</td><td class="num">${c.distance_km.toFixed(1)} km</td></tr>`)
            .join('');

        const forecast = (data.monthly_forecast || [])
            .map((m) => `<tr><td>${escapeHtml(m.month)}</td><td class="num">${formatCurrency(m.expected)}</td><td class="num">${formatCurrency(m.low)} – ${formatCurrency(m.high)}</td></tr>`)
            .join('');

        const reasons = (data.confidence.reasons || []).map((r) => `<li>${escapeHtml(r)}</li>`).join('');
        const weaknesses = (data.confidence.weaknesses || []).map((w) => `<li>${escapeHtml(w)}</li>`).join('') || '<li>No significant weaknesses disclosed for this estimate.</li>';

        const decisionSummary = document.getElementById('decision-summary').textContent;

        return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>AIRWORTHY report — ${escapeHtml(data.address)}</title>
<style>
  body { font-family: Georgia, 'Times New Roman', serif; color: #1a1a1a; max-width: 760px; margin: 40px auto; padding: 0 24px; line-height: 1.55; }
  h1 { font-size: 22px; margin-bottom: 2px; }
  h2 { font-size: 15px; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid #ccc; padding-bottom: 6px; margin-top: 32px; }
  .eyebrow { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #666; }
  .meta { font-size: 12px; color: #666; margin-bottom: 18px; }
  .verdict { display: inline-block; font-weight: bold; padding: 4px 12px; border-radius: 20px; margin: 8px 0 16px; font-size: 13px; }
  .verdict.cleared { background: #dff6df; color: #1c5e1c; }
  .verdict.conditional { background: #fff4d6; color: #6b4e05; }
  .verdict.exposed { background: #ffe4d6; color: #8a3d10; }
  .verdict.grounded { background: #fde0e0; color: #8a1c1c; }
  .range { font-size: 26px; font-weight: bold; margin: 6px 0; }
  .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 14px 0; font-size: 13px; }
  .metrics div span { display: block; }
  .metrics .label { font-size: 10px; text-transform: uppercase; color: #666; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  td, th { padding: 5px 6px; border-bottom: 1px solid #e0e0e0; text-align: left; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.pos { color: #1c5e1c; }
  td.neg { color: #8a1c1c; }
  .disclaimer { font-size: 11px; color: #666; margin-top: 30px; border-top: 1px solid #ccc; padding-top: 10px; }
  @media print { body { margin: 0 auto; } }
</style>
</head><body>
  <p class="eyebrow">AIRWORTHY — property earnings report</p>
  <h1>${escapeHtml(data.address)}</h1>
  <p class="meta">Generated ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} · data current as of ${escapeHtml(data.data_freshness || 'the latest snapshot')} · model ${escapeHtml(data.model_version)}</p>
  <span class="verdict ${String(data.airworthy_verdict || '').toLowerCase()}">${escapeHtml(data.airworthy_verdict)} — score ${data.airworthy_score}/100</span>
  <div class="range">${formatCurrency(data.confidence.revenue_lower)} – ${formatCurrency(data.confidence.revenue_upper)} / yr</div>
  <p>Most likely: <strong>${formatCurrency(data.annual_revenue)}/yr</strong> at ${escapeHtml(data.confidence.level)} confidence.</p>
  <div class="metrics">
    <div><span class="label">Nightly rate</span><span>${formatCurrency(data.market.adr)}</span></div>
    <div><span class="label">Occupancy</span><span>${formatPercent(data.market.occupancy_rate)}</span></div>
    <div><span class="label">Comparables</span><span>${data.comps.length}</span></div>
  </div>

  <h2>Decision summary</h2>
  <p>${escapeHtml(decisionSummary)}</p>

  <h2>Performance drivers</h2>
  <table>${drivers}</table>

  <h2>Comparable evidence (top matches by similarity)</h2>
  <table><tr><th>Comp</th><th class="num">Similarity</th><th class="num">Revenue</th><th class="num">Distance</th></tr>${comps}</table>

  <h2>Monthly forecast</h2>
  <table><tr><th>Month</th><th class="num">Expected</th><th class="num">Range</th></tr>${forecast}</table>

  <h2>Why this confidence level</h2>
  <ul>${reasons}</ul>
  <ul>${weaknesses}</ul>

  <p class="disclaimer">${escapeHtml(data.disclaimer)}<br>Data source: InsideAirbnb, licensed under CC BY 4.0. Facts used: ${facts.bedrooms} bd / ${facts.bathrooms} ba / sleeps ${facts.accommodates} at ${formatCurrency(facts.nightly_rate)}/night.</p>
</body></html>`;
    }

    function exportReport() {
        if (!currentData || !currentFacts) return;
        const html = buildReportHtml(currentData, currentFacts);
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const slug = currentData.address.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '').slice(0, 60) || 'property';
        const a = document.createElement('a');
        a.href = url;
        a.download = `airworthy-report-${slug}.html`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 2000);
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
        originalFacts = Object.assign({}, facts);
        runEstimate(facts);
    });

    // ---- Boot ----
    const facts = factsFromParams(new URLSearchParams(window.location.search));
    if (facts) {
        originalFacts = Object.assign({}, facts);
        runEstimate(facts);
    } else {
        showOnly(entryEmpty);
    }
})();
