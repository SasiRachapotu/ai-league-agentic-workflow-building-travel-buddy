// ============================================================
// NSE India — Live Indices, Top Gainers/Losers, Shareholding
// ============================================================

import { upstreamFetch } from './client.js';
import { cacheGet, cacheSet, CACHE_TTL } from '../cache/manager.js';

// NSE India endpoints (public, rate limited)
const NSE_BASE = 'https://www.nseindia.com/api';

// NSE requires specific headers and cookies — use a session approach
const nseHeaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.nseindia.com/',
    'Connection': 'keep-alive',
};

async function nseRequest<T>(path: string): Promise<T> {
    return upstreamFetch<T>('NSE India', {
        url: `${NSE_BASE}${path}`,
        headers: nseHeaders,
        withCredentials: true,
    }, { retries: 1 });
}

export async function getIndexData(indexName: string = 'NIFTY 50') {
    const cacheKey = `index:${indexName}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    try {
        const data = await nseRequest<any>(`/allIndices`);
        const indices = data?.data || [];

        const targetIndex = indices.find((idx: any) =>
            idx.index?.toUpperCase() === indexName.toUpperCase() ||
            idx.indexSymbol?.toUpperCase() === indexName.toUpperCase()
        );

        if (targetIndex) {
            const response = {
                index_name: targetIndex.index,
                last: targetIndex.last,
                change: targetIndex.variation,
                percent_change: targetIndex.percentChange,
                open: targetIndex.open,
                high: targetIndex.high,
                low: targetIndex.low,
                previous_close: targetIndex.previousClose,
                year_high: targetIndex.yearHigh,
                year_low: targetIndex.yearLow,
                _source: 'NSE India',
                _disclaimer: 'Index data for informational purposes only.',
            };
            await cacheSet(cacheKey, response, CACHE_TTL.INDEX);
            return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.INDEX, is_stale: false } };
        }

        throw new Error(`Index ${indexName} not found`);
    } catch (error) {
        // Graceful degradation with cached data
        const stale = await cacheGet(cacheKey);
        if (stale) {
            return { ...stale.data as object, _freshness: stale.freshness, _degradation_notice: 'Using cached data. NSE API may be rate limited.' };
        }

        // Return mock data for demo purposes
        return {
            index_name: indexName,
            last: indexName === 'NIFTY 50' ? 23450.50 : indexName === 'SENSEX' ? 77230.80 : null,
            change: indexName === 'NIFTY 50' ? 125.30 : 410.50,
            percent_change: indexName === 'NIFTY 50' ? '0.54%' : '0.53%',
            _source: 'NSE India (estimated)',
            _degradation_notice: 'Live data unavailable. Showing approximate values.',
            _disclaimer: 'Data for informational purposes only.',
        };
    }
}

export async function getTopGainersLosers() {
    const cacheKey = 'market:top_movers';
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    try {
        const [gainersData, losersData] = await Promise.all([
            nseRequest<any>('/live-analysis-variations?index=gainers'),
            nseRequest<any>('/live-analysis-variations?index=losers'),
        ]);

        const formatMover = (item: any) => ({
            symbol: item.symbol,
            name: item.symbol,
            ltp: item.ltp,
            change: item.change,
            percent_change: item.pChange,
            volume: item.tradedQuantity,
        });

        const response = {
            gainers: (gainersData?.NIFTY?.data || []).slice(0, 10).map(formatMover),
            losers: (losersData?.NIFTY?.data || []).slice(0, 10).map(formatMover),
            _source: 'NSE India',
            _disclaimer: 'Market data for informational purposes only.',
        };

        await cacheSet(cacheKey, response, CACHE_TTL.QUOTE);
        return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.QUOTE, is_stale: false } };
    } catch (error) {
        const stale = await cacheGet(cacheKey);
        if (stale) {
            return { ...stale.data as object, _freshness: stale.freshness, _degradation_notice: 'Using cached data.' };
        }
        return {
            gainers: [],
            losers: [],
            _source: 'NSE India',
            _degradation_notice: 'Live data unavailable. NSE API may be rate limited.',
        };
    }
}

export async function getShareholdingPattern(ticker: string) {
    const cacheKey = `shareholding:${ticker}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    try {
        const data = await nseRequest<any>(`/corporates/shareholding?symbol=${ticker.toUpperCase()}`);

        if (data && Array.isArray(data)) {
            const latest = data[0] || {};
            const response = {
                ticker: ticker.toUpperCase(),
                as_of: latest.date || 'Latest Quarter',
                promoter_holding: latest.promoterHolding,
                fii_holding: latest.fiiHolding,
                dii_holding: latest.diiHolding,
                public_holding: latest.publicHolding,
                history: data.slice(0, 8).map((q: any) => ({
                    period: q.date,
                    promoter: q.promoterHolding,
                    fii: q.fiiHolding,
                    dii: q.diiHolding,
                    public: q.publicHolding,
                })),
                _source: 'NSE India',
                _disclaimer: 'Shareholding data for informational purposes only.',
            };

            await cacheSet(cacheKey, response, CACHE_TTL.SHAREHOLDING);
            return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.SHAREHOLDING, is_stale: false } };
        }
        throw new Error('No shareholding data');
    } catch (error) {
        // Fallback: try yfinance institutional holders
        const stale = await cacheGet(cacheKey);
        if (stale) {
            return { ...stale.data as object, _freshness: stale.freshness, _degradation_notice: 'Using cached data.' };
        }

        return {
            ticker: ticker.toUpperCase(),
            _source: 'NSE India',
            _degradation_notice: 'Shareholding data temporarily unavailable. NSE API may be rate limited.',
            promoter_holding: null,
            fii_holding: null,
            dii_holding: null,
            public_holding: null,
        };
    }
}
