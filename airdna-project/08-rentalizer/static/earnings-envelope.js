/**
 * AIRWORTHY — Earnings Envelope
 * -----------------------------------------------------------------------
 * Reusable, dependency-free revenue-range visualization. Renders a modeled
 * earnings field (downside / likely range / most-likely / upside) plus a
 * confidence readout — not a single falsely-precise revenue number.
 *
 * Usage (any page, after including earnings-envelope.css + this script):
 *
 *   AirworthyEnvelope.render(document.getElementById('envelope-slot'), {
 *     downside: 42000,        // low end of the modeled range
 *     upside: 78000,          // high end of the modeled range
 *     likelyLow: 52000,       // inner "likely" band, optional — defaults
 *     likelyHigh: 68000,      //   to the middle 50% of downside..upside
 *     mostLikely: 59000,      // point estimate / annual_revenue
 *     confidenceLevel: 'medium',   // 'high' | 'medium' | 'low'
 *     label: 'Estimated Annual Revenue',
 *   });
 *
 * The confidence/upside/downside inputs map directly onto the
 * /v1/estimate response: downside = confidence.revenue_lower,
 * upside = confidence.revenue_upper, mostLikely = annual_revenue,
 * confidenceLevel = confidence.level.
 *
 * Returns the container element for chaining/testing.
 */
(function (global) {
    'use strict';

    function formatCurrency(n) {
        n = Math.round(n);
        return '$' + Math.abs(n).toLocaleString('en-US');
    }

    function clampPct(v) {
        return Math.max(0, Math.min(100, v));
    }

    function render(container, data) {
        if (!container) {
            throw new Error('AirworthyEnvelope.render: container element is required');
        }
        const {
            downside,
            upside,
            mostLikely,
            likelyLow,
            likelyHigh,
            confidenceLevel = 'medium',
            label = 'Estimated Annual Revenue',
        } = data || {};

        if (typeof downside !== 'number' || typeof upside !== 'number' || typeof mostLikely !== 'number') {
            throw new Error('AirworthyEnvelope.render: downside, upside, and mostLikely are required numbers');
        }

        const span = Math.max(upside - downside, 1);
        const innerLow = typeof likelyLow === 'number' ? likelyLow : downside + span * 0.25;
        const innerHigh = typeof likelyHigh === 'number' ? likelyHigh : downside + span * 0.75;

        const pct = (v) => clampPct(((v - downside) / span) * 100);

        container.innerHTML = '';
        container.className = (container.className ? container.className + ' ' : '') + 'aw-envelope';

        // Headline figure
        const figure = document.createElement('div');
        figure.className = 'aw-envelope-figure';

        const value = document.createElement('span');
        value.className = 'aw-envelope-figure-value';
        value.textContent = formatCurrency(mostLikely);
        figure.appendChild(value);

        const lbl = document.createElement('span');
        lbl.className = 'aw-envelope-figure-label';
        lbl.textContent = label;
        figure.appendChild(lbl);

        const badge = document.createElement('span');
        badge.className = `aw-envelope-confidence ${confidenceLevel}`;
        badge.textContent = `${confidenceLevel} confidence`;
        figure.appendChild(badge);

        container.appendChild(figure);

        // Band
        const bandWrap = document.createElement('div');
        bandWrap.className = 'aw-envelope-band-wrap';

        const band = document.createElement('div');
        band.className = 'aw-envelope-band';
        band.style.setProperty('--aw-downside-pct', '0%');
        band.style.setProperty('--aw-upside-pct', '100%');

        const likelyRange = document.createElement('div');
        likelyRange.className = 'aw-envelope-likely-range';
        likelyRange.style.left = pct(innerLow) + '%';
        likelyRange.style.width = Math.max(pct(innerHigh) - pct(innerLow), 0) + '%';
        band.appendChild(likelyRange);

        const marker = document.createElement('div');
        marker.className = 'aw-envelope-marker';
        marker.style.left = pct(mostLikely) + '%';
        marker.setAttribute('data-label', 'Most likely');
        band.appendChild(marker);

        bandWrap.appendChild(band);
        container.appendChild(bandWrap);

        // Scale
        const scale = document.createElement('div');
        scale.className = 'aw-envelope-scale';
        const scaleLow = document.createElement('span');
        scaleLow.textContent = formatCurrency(downside) + ' downside';
        const scaleMid = document.createElement('span');
        scaleMid.className = 'aw-envelope-scale-mid';
        scaleMid.textContent = formatCurrency(innerLow) + ' – ' + formatCurrency(innerHigh) + ' likely range';
        const scaleHigh = document.createElement('span');
        scaleHigh.textContent = formatCurrency(upside) + ' upside';
        scale.appendChild(scaleLow);
        scale.appendChild(scaleMid);
        scale.appendChild(scaleHigh);
        container.appendChild(scale);

        // Legend
        const legend = document.createElement('div');
        legend.className = 'aw-envelope-legend';
        [
            ['var(--aw-coral)', 'Downside / upside tails'],
            ['var(--aw-blue)', 'Likely range'],
            ['var(--aw-ink)', 'Most-likely estimate'],
        ].forEach(([color, text]) => {
            const item = document.createElement('span');
            item.className = 'aw-envelope-legend-item';
            const dot = document.createElement('span');
            dot.className = 'aw-envelope-legend-dot';
            dot.style.background = color;
            item.appendChild(dot);
            const t = document.createElement('span');
            t.textContent = text;
            item.appendChild(t);
            legend.appendChild(item);
        });
        container.appendChild(legend);

        return container;
    }

    global.AirworthyEnvelope = { render };
})(window);
