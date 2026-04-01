// ============================================================
// MFapi.in — Mutual Fund NAV, Search, Scheme Data
// ============================================================

import { upstreamFetch } from './client.js';
import { cacheGet, cacheSet, CACHE_TTL } from '../cache/manager.js';

const MFAPI_BASE = 'https://api.mfapi.in/mf';

export async function searchMutualFunds(query: string) {
    const cacheKey = `mf:search:${query.toLowerCase()}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    // MFapi doesn't have a direct search, so we fetch the full list and filter
    const data = await upstreamFetch<any[]>('MFapi.in', {
        url: MFAPI_BASE,
    });

    const results = (data || [])
        .filter((fund: any) =>
            fund.schemeName?.toLowerCase().includes(query.toLowerCase()) ||
            fund.schemeCode?.toString().includes(query)
        )
        .slice(0, 20)
        .map((fund: any) => ({
            scheme_code: fund.schemeCode,
            scheme_name: fund.schemeName,
        }));

    const response = {
        query,
        total_results: results.length,
        funds: results,
        _source: 'MFapi.in (AMFI)',
        _disclaimer: 'Mutual fund data for informational purposes only. Not financial advice.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.MF_SEARCH);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.MF_SEARCH, is_stale: false } };
}

export async function getFundNav(schemeCode: string | number) {
    const cacheKey = `mf:nav:${schemeCode}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const data = await upstreamFetch<any>('MFapi.in', {
        url: `${MFAPI_BASE}/${schemeCode}`,
    });

    if (!data || !data.data) throw new Error(`No NAV data for scheme ${schemeCode}`);

    const latest = data.data[0];
    const history = data.data.slice(0, 30); // Last 30 data points

    const response = {
        scheme_code: schemeCode,
        scheme_name: data.meta?.scheme_name || '',
        fund_house: data.meta?.fund_house || '',
        scheme_type: data.meta?.scheme_type || '',
        scheme_category: data.meta?.scheme_category || '',
        latest_nav: {
            date: latest?.date,
            nav: parseFloat(latest?.nav),
        },
        nav_history: history.map((d: any) => ({
            date: d.date,
            nav: parseFloat(d.nav),
        })),
        _source: `MFapi.in scheme ${schemeCode}`,
        _disclaimer: 'Mutual fund data for informational purposes only. Past performance does not guarantee future results.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.MF_NAV);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.MF_NAV, is_stale: false } };
}

export async function compareFunds(schemeCodes: (string | number)[]) {
    const funds = await Promise.all(schemeCodes.map(code => getFundNav(code)));

    const comparison = funds.map((fund: any) => {
        const navs = fund.nav_history || [];
        const latest = navs[0]?.nav || 0;
        const weekAgo = navs[6]?.nav || navs[navs.length - 1]?.nav || latest;
        const monthAgo = navs[navs.length - 1]?.nav || latest;

        return {
            scheme_code: fund.scheme_code,
            scheme_name: fund.scheme_name,
            fund_house: fund.fund_house,
            category: fund.scheme_category,
            latest_nav: latest,
            nav_date: fund.latest_nav?.date,
            returns_1w: weekAgo ? ((latest - weekAgo) / weekAgo * 100).toFixed(2) + '%' : 'N/A',
            returns_1m: monthAgo ? ((latest - monthAgo) / monthAgo * 100).toFixed(2) + '%' : 'N/A',
        };
    });

    return {
        comparison,
        funds_compared: comparison.length,
        _source: 'MFapi.in (AMFI)',
        _disclaimer: 'Comparison for informational purposes only. Past performance does not guarantee future results.',
    };
}
