// AIRWORTHY — Homepage instant-estimate flow
// Entry (address) -> live sequence (locate/comps/resolve) -> result preview.
// All DOM writes use textContent/DOM APIs (XSS-safe). Sequence text reflects
// real response data, not decorative filler.

(function () {
    'use strict';

    const form = document.getElementById('estimate-form');
    const detailsToggle = document.getElementById('details-toggle');
    const detailsPanel = document.getElementById('details-panel');
    const entrySection = document.getElementById('entry');
    const sequenceSection = document.getElementById('sequence');
    const errorSection = document.getElementById('error');
    const resultsSection = document.getElementById('results');
    const submitBtn = document.getElementById('submit-btn');

    let lastRequest = null; // remembers the last submitted property for "Save" / links

    // ---- Adjust-details disclosure ----
    detailsToggle.addEventListener('click', () => {
        const expanded = detailsToggle.getAttribute('aria-expanded') === 'true';
        detailsToggle.setAttribute('aria-expanded', String(!expanded));
        detailsPanel.classList.toggle('hidden', expanded);
    });

    function openDetails() {
        detailsToggle.setAttribute('aria-expanded', 'true');
        detailsPanel.classList.remove('hidden');
    }

    // ---- Step helpers ----
    function resetSequence() {
        sequenceSection.querySelectorAll('.sequence-step').forEach((el) => {
            el.classList.remove('active', 'done');
        });
    }

    function setStep(step, state, text) {
        const el = sequenceSection.querySelector(`.sequence-step[data-step="${step}"]`);
        if (!el) return;
        el.classList.remove('active', 'done');
        el.classList.add(state);
        if (text) {
            const textEl = el.querySelector('.sequence-text');
            textEl.textContent = text;
        }
    }

    function sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    function showOnly(section) {
        [sequenceSection, errorSection, resultsSection].forEach((s) => {
            s.classList.toggle('hidden', s !== section);
        });
    }

    function clearInputError() {
        document.getElementById('address').classList.remove('input-invalid');
    }

    // ---- Submit flow ----
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        clearInputError();

        const address = form.address.value.trim();
        if (!address) {
            document.getElementById('address').classList.add('input-invalid');
            document.getElementById('address').focus();
            return;
        }

        const requestBody = {
            address,
            bedrooms: parseInt(form.bedrooms.value, 10),
            bathrooms: parseFloat(form.bathrooms.value),
            accommodates: parseInt(form.accommodates.value, 10),
            nightly_rate: parseFloat(form.nightly_rate.value),
        };
        lastRequest = requestBody;

        submitBtn.disabled = true;
        resetSequence();
        showOnly(sequenceSection);
        setStep('locate', 'active', `Locating "${address}"…`);

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);

        try {
            const resp = await fetch('/v1/estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
                signal: controller.signal,
            });
            clearTimeout(timeout);

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                await revealError(err, resp.status);
                return;
            }

            const data = await resp.json();

            // Step through the sequence using real values from the response —
            // brief pauses keep each step legible instead of a flash.
            setStep('locate', 'done', `Located near ${data.market.borough}.`);
            setStep('comps', 'active', 'Gathering comparable listings…');
            await sleep(420);

            setStep('comps', 'done', `Found ${data.comps.length} comparable ${data.comps.length === 1 ? 'listing' : 'listings'} nearby.`);
            setStep('resolve', 'active', 'Resolving the earnings range…');
            await sleep(420);

            setStep('resolve', 'done', `Range resolved with ${data.confidence.level} confidence.`);
            await sleep(280);

            renderResults(data, requestBody);
            showOnly(resultsSection);
            resultsSection.focus();
        } catch (err) {
            clearTimeout(timeout);
            const message = err.name === 'AbortError'
                ? 'The request timed out. Please try again.'
                : 'Something went wrong while reaching AIRWORTHY. Please try again.';
            await revealError({ error: 'request_failed', detail: message }, 0);
        } finally {
            submitBtn.disabled = false;
        }
    });

    async function revealError(err, status) {
        const title = document.getElementById('error-title');
        const message = document.getElementById('error-message');
        const suggestion = document.getElementById('error-suggestion');

        const titles = {
            geocoding_failed: "We couldn't locate that address",
            outside_coverage_area: 'This address is outside current coverage',
            invalid_input: "That doesn't look right",
            request_failed: 'Request failed',
        };
        title.textContent = titles[err.error] || 'Something went wrong';
        message.textContent = err.detail || 'Please try again.';
        suggestion.textContent = err.suggestion || '';
        suggestion.classList.toggle('hidden', !err.suggestion);

        showOnly(errorSection);
        errorSection.focus?.();
    }

    // ---- Rendering the result preview ----
    function renderResults(data, requestBody) {
        // Earnings Envelope (shared component)
        const slot = document.getElementById('envelope-slot');
        AirworthyEnvelope.render(slot, {
            downside: data.confidence.revenue_lower,
            upside: data.confidence.revenue_upper,
            mostLikely: data.annual_revenue,
            confidenceLevel: data.confidence.level,
            label: 'Estimated Annual Revenue',
        });

        document.getElementById('metric-adr').textContent = formatCurrency(data.market.adr) + '/night';
        document.getElementById('metric-occupancy').textContent = formatPercent(data.market.occupancy_rate);
        document.getElementById('metric-comps').textContent = data.comps.length.toLocaleString();
        document.getElementById('metric-confidence').textContent = capitalize(data.confidence.level);

        document.getElementById('disclaimer').textContent = data.disclaimer;

        // Primary action: full property report, carrying the entered facts.
        const reportParams = new URLSearchParams({
            address: data.address,
            bedrooms: String(requestBody.bedrooms),
            bathrooms: String(requestBody.bathrooms),
            accommodates: String(requestBody.accommodates),
            nightly_rate: String(requestBody.nightly_rate),
        });
        document.getElementById('view-report-link').href = `/property?${reportParams.toString()}`;
        document.getElementById('compare-link').href = `/compare?${reportParams.toString()}`;

        // Save property (shared module)
        const saveBtn = document.getElementById('save-btn');
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
            bedrooms: requestBody.bedrooms,
            accommodates: requestBody.accommodates,
            nightlyRate: requestBody.nightly_rate,
        };
        const savedId = AirworthySaved.makeId(snapshot);
        updateSaveButton(saveBtn, AirworthySaved.has(savedId));
        saveBtn.onclick = () => {
            if (AirworthySaved.has(savedId)) {
                AirworthySaved.remove(savedId);
                updateSaveButton(saveBtn, false);
            } else {
                AirworthySaved.save(snapshot);
                updateSaveButton(saveBtn, true);
            }
        };
    }

    function updateSaveButton(btn, saved) {
        btn.textContent = saved ? 'Saved ✓' : 'Save property';
        btn.classList.toggle('is-saved', saved);
    }

    // "Adjust details & re-run" scrolls back up, opens the details panel,
    // and focuses the first editable field — the address stays populated.
    document.getElementById('adjust-btn').addEventListener('click', () => {
        showOnly(sequenceSection); // hidden below until re-submit; effectively reset view
        sequenceSection.classList.add('hidden');
        entrySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        openDetails();
        document.getElementById('bedrooms').focus();
    });

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
})();
