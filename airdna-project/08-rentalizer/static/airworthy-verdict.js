/**
 * AIRWORTHY — Verdict badge + score gauge
 * -----------------------------------------------------------------------
 * The one shared instrument for "is this property AIRWORTHY": a
 * color-coded verdict pill (CLEARED / CONDITIONAL / EXPOSED / GROUNDED), a
 * 0-100 score gauge, and a one-line reason — rendered consistently
 * wherever an estimate is shown.
 *
 * Usage (after including airworthy-verdict.css + this script):
 *
 *   AirworthyVerdict.render(document.getElementById('verdict-slot'), {
 *     score: data.airworthy_score,
 *     verdict: data.airworthy_verdict,     // 'CLEARED' | 'CONDITIONAL' | 'EXPOSED' | 'GROUNDED'
 *     reason: data.airworthy_reason,
 *     lowData: data.comps.length < 8,      // optional — flags thin evidence
 *   });
 *
 *   AirworthyVerdict.render(slot, { loading: true });  // while a fetch is in flight
 *
 * `computeScore` mirrors src/scoring.py's model exactly (same thresholds
 * and point bands) for the rare client-only surface that has revenue,
 * confidence, and comp signals but no /v1/estimate round trip to read the
 * fields from directly (e.g. the map's client-derived inspector preview).
 */
(function (global) {
    'use strict';

    var CLEARED_MIN = 75;
    var CONDITIONAL_MIN = 55;
    var EXPOSED_MIN = 35;

    var VERDICT_MEANINGS = {
        CLEARED: 'Strong projected performance',
        CONDITIONAL: 'Viable performance under current assumptions',
        EXPOSED: 'Financially sensitive projection',
        GROUNDED: 'Insufficient earnings potential',
    };

    function clamp(v, lo, hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    function verdictFor(score) {
        if (score >= CLEARED_MIN) return 'CLEARED';
        if (score >= CONDITIONAL_MIN) return 'CONDITIONAL';
        if (score >= EXPOSED_MIN) return 'EXPOSED';
        return 'GROUNDED';
    }

    /** Mirrors scoring.py's compute_airworthy — see that file for the model. */
    function computeScore(opts) {
        opts = opts || {};
        var revenue = opts.revenue || 0;
        var benchmarkRevenue = opts.benchmarkRevenue || 0;
        var cv = Math.max(0, opts.cv || 0);
        var nComps = Math.max(0, opts.nComps || 0);

        var ratio = 1.0;
        var earningsPts;
        if (!benchmarkRevenue || benchmarkRevenue <= 0) {
            earningsPts = 30.0;
        } else {
            ratio = revenue / benchmarkRevenue;
            earningsPts = clamp(30.0 + (ratio - 1.0) * 50.0, 0, 60);
        }

        var cvScore = clamp(28.0 * (1.0 - Math.min(cv, 1.0)), 0, 28);
        var nScore = clamp(12.0 * (Math.min(nComps, 20) / 20.0), 0, 12);
        var reliabilityPts = cvScore + nScore;

        var score = Math.round(clamp(earningsPts + reliabilityPts, 0, 100));
        var verdict = verdictFor(score);

        var pct = Math.round((ratio - 1.0) * 100);
        var earningsBit;
        if (pct >= 5) earningsBit = 'projects ' + Math.abs(pct) + '% above the local market benchmark';
        else if (pct <= -5) earningsBit = 'projects ' + Math.abs(pct) + '% below the local market benchmark';
        else earningsBit = 'projects in line with the local market benchmark';

        var reliabilityBit;
        if (cv < 0.25 && nComps >= 15) reliabilityBit = 'backed by a tight, well-supported comparable set';
        else if (cv < 0.5 && nComps >= 8) reliabilityBit = 'backed by a reasonably consistent comparable set';
        else reliabilityBit = 'supported by a thinner or more scattered comparable set';

        var reason = VERDICT_MEANINGS[verdict] + ' — ' + earningsBit + ', ' + reliabilityBit + '.';

        return { score: score, verdict: verdict, reason: reason };
    }

    function render(container, data) {
        if (!container) {
            throw new Error('AirworthyVerdict.render: container element is required');
        }
        data = data || {};
        container.innerHTML = '';
        container.className = (container.className ? container.className.replace(/\baw-verdict\S*/g, '').trim() + ' ' : '') + 'aw-verdict';

        if (data.loading) {
            container.classList.add('loading');
        } else {
            var verdict = String(data.verdict || 'GROUNDED').toLowerCase();
            container.classList.add(verdict);
            if (data.lowData) container.classList.add('low-data');
        }

        var score = typeof data.score === 'number' ? clamp(Math.round(data.score), 0, 100) : 0;
        var radius = 30;
        var circumference = 2 * Math.PI * radius;
        var offset = data.loading ? circumference * 0.75 : circumference * (1 - score / 100);

        var gauge = document.createElement('div');
        gauge.className = 'aw-verdict-gauge';
        gauge.innerHTML =
            '<svg viewBox="0 0 72 72" class="aw-verdict-gauge-svg" aria-hidden="true">' +
            '<circle class="aw-verdict-gauge-track" cx="36" cy="36" r="' + radius + '"></circle>' +
            '<circle class="aw-verdict-gauge-fill" cx="36" cy="36" r="' + radius + '" ' +
            'stroke-dasharray="' + circumference + '" stroke-dashoffset="' + offset + '"></circle>' +
            '</svg>' +
            '<div class="aw-verdict-gauge-center">' +
            '<span class="aw-verdict-gauge-score">' + (data.loading ? '' : score) + '</span>' +
            '<span class="aw-verdict-gauge-of">' + (data.loading ? '' : '/ 100') + '</span>' +
            '</div>';
        container.appendChild(gauge);

        var body = document.createElement('div');
        body.className = 'aw-verdict-body';

        var pill = document.createElement('span');
        pill.className = 'aw-verdict-pill';
        pill.textContent = data.loading ? 'Evaluating…' : (data.verdict || 'GROUNDED');
        body.appendChild(pill);

        var reason = document.createElement('p');
        reason.className = 'aw-verdict-reason';
        reason.textContent = data.loading ? 'Computing the AIRWORTHY verdict…' : (data.reason || '');
        body.appendChild(reason);

        container.appendChild(body);

        var sr = document.createElement('span');
        sr.className = 'sr-only';
        sr.setAttribute('role', 'status');
        sr.textContent = data.loading
            ? 'AIRWORTHY verdict loading'
            : 'AIRWORTHY score ' + score + ' out of 100. Verdict: ' + (data.verdict || 'GROUNDED') + '. ' + (data.reason || '');
        container.appendChild(sr);

        return container;
    }

    global.AirworthyVerdict = { render: render, computeScore: computeScore };
})(window);
