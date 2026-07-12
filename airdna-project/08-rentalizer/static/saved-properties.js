/**
 * AIRWORTHY — Saved Properties
 * -----------------------------------------------------------------------
 * Shared client-side module for saving, listing, and removing a property's
 * estimate snapshot. Backed by localStorage so "Save property" behaves
 * consistently across the homepage, map, report, and comparison pages
 * without a server-side account system.
 *
 * Stable data shape (one entry per saved property):
 * {
 *   id: string,              // stable key — see makeId()
 *   address: string,
 *   lat: number,
 *   lng: number,
 *   annualRevenue: number,
 *   revenueLower: number,
 *   revenueUpper: number,
 *   confidenceLevel: 'high'|'medium'|'low',
 *   adr: number,
 *   occupancyRate: number,
 *   bedrooms: number,
 *   accommodates: number,
 *   nightlyRate: number,
 *   savedAt: string,         // ISO timestamp
 * }
 *
 * Usage:
 *   AirworthySaved.save({ address, lat, lng, annualRevenue, ... });
 *   AirworthySaved.list();          // -> array, newest first
 *   AirworthySaved.remove(id);
 *   AirworthySaved.has(id);
 *   AirworthySaved.makeId({ address, lat, lng });
 */
(function (global) {
    'use strict';

    const STORAGE_KEY = 'airworthy:saved-properties:v1';

    function safeParse(json) {
        try {
            const parsed = JSON.parse(json);
            return Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            return [];
        }
    }

    function readAll() {
        if (typeof localStorage === 'undefined') return [];
        return safeParse(localStorage.getItem(STORAGE_KEY) || '[]');
    }

    function writeAll(items) {
        if (typeof localStorage === 'undefined') return;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    }

    /** Deterministic ID from address + coordinates, so the same property
     * saved twice updates in place rather than duplicating. */
    function makeId({ address, lat, lng }) {
        const norm = `${(address || '').trim().toLowerCase()}|${(lat ?? '').toFixed ? lat.toFixed(4) : lat}|${(lng ?? '').toFixed ? lng.toFixed(4) : lng}`;
        let hash = 0;
        for (let i = 0; i < norm.length; i++) {
            hash = (hash * 31 + norm.charCodeAt(i)) | 0;
        }
        return 'prop_' + Math.abs(hash).toString(36);
    }

    function list() {
        return readAll().sort((a, b) => (b.savedAt || '').localeCompare(a.savedAt || ''));
    }

    function has(id) {
        return readAll().some((p) => p.id === id);
    }

    function get(id) {
        return readAll().find((p) => p.id === id) || null;
    }

    function save(property) {
        if (!property || !property.address) {
            throw new Error('AirworthySaved.save: property.address is required');
        }
        const id = property.id || makeId(property);
        const entry = Object.assign({}, property, {
            id,
            savedAt: new Date().toISOString(),
        });
        const items = readAll().filter((p) => p.id !== id);
        items.push(entry);
        writeAll(items);
        return entry;
    }

    function remove(id) {
        const items = readAll().filter((p) => p.id !== id);
        writeAll(items);
        return items;
    }

    function clear() {
        writeAll([]);
    }

    global.AirworthySaved = { save, list, remove, has, get, clear, makeId };
})(window);
