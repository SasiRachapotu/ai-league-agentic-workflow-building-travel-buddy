// ============================================================
// Alpha Vantage — Technical Indicators (SMA, RSI, MACD)
// ============================================================

import { upstreamFetch, updateQuotaTracking } from './client.js';
import { cacheGet, cacheSet, CACHE_TTL } from '../cache/manager.js';

const AV_BASE = 'https://www.alphavantage.co/query';

function getApiKey(): string {
    return process.env.ALPHA_VANTAGE_API_KEY || '';
}

export async function getTechnicalIndicators(ticker: string, indicators: string[] = ['SMA', 'RSI', 'MACD']) {
    const cacheKey = `technicals:${ticker}:${indicators.join(',')}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const apiKey = getApiKey();
    if (!apiKey) {
        return {
            ticker: ticker.toUpperCase(),
            error: 'Alpha Vantage API key not configured',
            _source: 'Alpha Vantage',
            _degradation_notice: 'Technical indicators unavailable — API key missing.',
            indicators: {},
        };
    }

    const bseTicker = `${ticker.toUpperCase()}.BSE`;
    const results: Record<string, unknown> = {};

    for (const indicator of indicators) {
        try {
            let params: Record<string, string> = {};

            switch (indicator.toUpperCase()) {
                case 'SMA':
                    params = { function: 'SMA', symbol: bseTicker, interval: 'daily', time_period: '20', series_type: 'close', apikey: apiKey };
                    break;
                case 'EMA':
                    params = { function: 'EMA', symbol: bseTicker, interval: 'daily', time_period: '20', series_type: 'close', apikey: apiKey };
                    break;
                case 'RSI':
                    params = { function: 'RSI', symbol: bseTicker, interval: 'daily', time_period: '14', series_type: 'close', apikey: apiKey };
                    break;
                case 'MACD':
                    params = { function: 'MACD', symbol: bseTicker, interval: 'daily', series_type: 'close', apikey: apiKey };
                    break;
                case 'BBANDS':
                    params = { function: 'BBANDS', symbol: bseTicker, interval: 'daily', time_period: '20', series_type: 'close', apikey: apiKey };
                    break;
                default:
                    continue;
            }

            const data = await upstreamFetch<any>('Alpha Vantage', { url: AV_BASE, params });

            // Parse the response (Alpha Vantage uses dynamic keys)
            const technicalKey = Object.keys(data).find(k => k.startsWith('Technical'));
            if (technicalKey) {
                const entries = Object.entries(data[technicalKey]).slice(0, 10);
                results[indicator] = entries.map(([date, values]: [string, any]) => ({
                    date,
                    ...values,
                }));
            }

            // Track quota (Alpha Vantage doesn't expose this, we estimate)
            updateQuotaTracking('Alpha Vantage', -1, 25);
        } catch (error) {
            results[indicator] = { error: `Failed to fetch ${indicator}`, message: String(error) };
        }
    }

    const response = {
        ticker: ticker.toUpperCase(),
        indicators: results,
        indicators_requested: indicators,
        _source: 'Alpha Vantage',
        _disclaimer: 'Technical indicators for informational purposes only. Not financial advice.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.TECHNICALS);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.TECHNICALS, is_stale: false } };
}
