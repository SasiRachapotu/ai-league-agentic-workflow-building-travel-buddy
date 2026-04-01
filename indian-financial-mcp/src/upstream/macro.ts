// ============================================================
// RBI / Macro Data — Hardcoded recent data + BSE Filings
// ============================================================

import { cacheGet, cacheSet, CACHE_TTL } from '../cache/manager.js';

// Hardcoded macro data (latest as of early 2026 — update for demo)
const MACRO_DATA = {
    rbi_rates: {
        repo_rate: 6.00,
        reverse_repo: 3.35,
        standing_deposit_facility: 5.75,
        marginal_standing_facility: 6.25,
        crr: 4.00,
        slr: 18.00,
        bank_rate: 6.25,
        last_updated: '2026-02-07',
        next_policy_date: '2026-04-09',
        _source: 'RBI DBIE',
    },
    rbi_rate_history: [
        { date: '2026-02-07', repo_rate: 6.00, action: 'Cut 25bps' },
        { date: '2025-12-06', repo_rate: 6.25, action: 'Cut 25bps' },
        { date: '2025-10-09', repo_rate: 6.50, action: 'Hold' },
        { date: '2025-08-08', repo_rate: 6.50, action: 'Hold' },
        { date: '2025-06-06', repo_rate: 6.50, action: 'Hold' },
        { date: '2025-04-09', repo_rate: 6.50, action: 'Cut 25bps' },
        { date: '2025-02-07', repo_rate: 6.50, action: 'Cut 25bps' },
        { date: '2024-12-06', repo_rate: 6.50, action: 'Hold' },
        { date: '2024-10-09', repo_rate: 6.50, action: 'Hold' },
        { date: '2024-06-07', repo_rate: 6.50, action: 'Hold' },
    ],
    inflation: {
        cpi_latest: { value: 3.61, month: 'Feb 2026', _source: 'RBI DBIE' },
        wpi_latest: { value: 0.53, month: 'Jan 2026', _source: 'RBI DBIE' },
        cpi_history: [
            { month: 'Feb 2026', cpi: 3.61 },
            { month: 'Jan 2026', cpi: 4.26 },
            { month: 'Dec 2025', cpi: 5.22 },
            { month: 'Nov 2025', cpi: 5.48 },
            { month: 'Oct 2025', cpi: 6.21 },
            { month: 'Sep 2025', cpi: 5.49 },
            { month: 'Aug 2025', cpi: 3.65 },
            { month: 'Jul 2025', cpi: 3.54 },
            { month: 'Jun 2025', cpi: 5.08 },
            { month: 'May 2025', cpi: 4.75 },
            { month: 'Apr 2025', cpi: 3.16 },
            { month: 'Mar 2025', cpi: 3.34 },
        ],
        _source: 'RBI DBIE',
    },
    gdp: {
        latest_growth: 6.20,
        quarter: 'Q3 FY26 (Oct-Dec 2025)',
        fiscal_year_estimate: 6.50,
        _source: 'RBI DBIE / MoSPI',
    },
    forex_reserves: {
        total_usd_billion: 640.2,
        as_of: '2026-03-21',
        _source: 'RBI DBIE',
    },
    usd_inr: {
        rate: 86.45,
        change_1m_percent: -0.8,
        change_ytd_percent: 1.2,
        _source: 'RBI Reference Rate',
    },
};

export async function getRbiRates() {
    const cacheKey = 'macro:rbi_rates';
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const response = {
        ...MACRO_DATA.rbi_rates,
        _disclaimer: 'Macro data for informational purposes only.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.MACRO);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.MACRO, is_stale: false } };
}

export async function getRbiRateHistory() {
    return {
        history: MACRO_DATA.rbi_rate_history,
        _source: 'RBI DBIE',
        _disclaimer: 'Historical rate data for informational purposes only.',
    };
}

export async function getInflationData() {
    const cacheKey = 'macro:inflation';
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const response = {
        ...MACRO_DATA.inflation,
        _disclaimer: 'Inflation data for informational purposes only.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.MACRO);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.MACRO, is_stale: false } };
}

export async function getMacroSnapshot() {
    return {
        rbi_rates: {
            repo_rate: MACRO_DATA.rbi_rates.repo_rate,
            crr: MACRO_DATA.rbi_rates.crr,
            slr: MACRO_DATA.rbi_rates.slr,
            next_policy: MACRO_DATA.rbi_rates.next_policy_date,
        },
        inflation: {
            cpi: MACRO_DATA.inflation.cpi_latest,
            wpi: MACRO_DATA.inflation.wpi_latest,
        },
        gdp: MACRO_DATA.gdp,
        forex_reserves: MACRO_DATA.forex_reserves,
        usd_inr: MACRO_DATA.usd_inr,
        _sources: ['RBI DBIE', 'MoSPI'],
        _disclaimer: 'Macro snapshot for informational purposes only.',
        _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.MACRO, is_stale: false },
    };
}

// ---- BSE Corporate Filings (simplified) ----
export async function getCorporateFilings(ticker: string) {
    const cacheKey = `filings:${ticker}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    // For the hackathon, return sample filings
    const sampleFilings = {
        ticker: ticker.toUpperCase(),
        filings: [
            {
                filing_id: `BSE-${ticker}-2026-Q3`,
                type: 'Quarterly Results',
                date: '2026-01-25',
                subject: `${ticker} Q3 FY26 Quarterly Financial Results`,
                exchange: 'BSE',
            },
            {
                filing_id: `BSE-${ticker}-2025-AGM`,
                type: 'AGM Notice',
                date: '2025-08-15',
                subject: `${ticker} Annual General Meeting Notice FY25`,
                exchange: 'BSE',
            },
            {
                filing_id: `BSE-${ticker}-2025-Q2`,
                type: 'Quarterly Results',
                date: '2025-10-28',
                subject: `${ticker} Q2 FY26 Quarterly Financial Results`,
                exchange: 'BSE',
            },
            {
                filing_id: `NSE-${ticker}-2025-BM`,
                type: 'Board Meeting',
                date: '2025-10-15',
                subject: `${ticker} Board Meeting Outcome - Dividend Declaration`,
                exchange: 'NSE',
            },
        ],
        total_filings: 4,
        _source: 'BSE India',
        _disclaimer: 'Filing data for informational purposes only.',
    };

    await cacheSet(cacheKey, sampleFilings, CACHE_TTL.FILINGS);
    return { ...sampleFilings, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.FILINGS, is_stale: false } };
}
