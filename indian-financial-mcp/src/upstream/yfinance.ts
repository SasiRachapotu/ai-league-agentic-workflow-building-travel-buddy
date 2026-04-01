// ============================================================
// yfinance Proxy — Historical prices, financials via Yahoo Finance
// ============================================================

import { upstreamFetch } from './client.js';
import { cacheGet, cacheSet, CACHE_TTL } from '../cache/manager.js';

const YAHOO_BASE = 'https://query1.finance.yahoo.com';

function toYahooTicker(ticker: string): string {
    // Convert NSE ticker to Yahoo format: RELIANCE → RELIANCE.NS
    const t = ticker.toUpperCase().replace('.NS', '').replace('.BO', '');
    return `${t}.NS`;
}

export async function getStockQuote(ticker: string) {
    const cacheKey = `quote:${ticker}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness, _source: 'Yahoo Finance (NSE)' };
    }

    try {
        const yahooTicker = toYahooTicker(ticker);
        const data = await upstreamFetch<any>('yfinance', {
            url: `${YAHOO_BASE}/v8/finance/chart/${yahooTicker}`,
            params: { interval: '1d', range: '5d', includePrePost: false },
        });

        const result = data?.chart?.result?.[0];
        if (!result) throw new Error(`No data for ${ticker}`);

        const meta = result.meta;
        const quote = {
            ticker: ticker.toUpperCase(),
            name: meta.longName || meta.shortName || ticker,
            exchange: meta.exchangeName || 'NSE',
            ltp: meta.regularMarketPrice,
            previous_close: meta.previousClose || meta.chartPreviousClose,
            change: meta.regularMarketPrice - (meta.previousClose || meta.chartPreviousClose),
            change_percent: ((meta.regularMarketPrice - (meta.previousClose || meta.chartPreviousClose)) / (meta.previousClose || meta.chartPreviousClose) * 100).toFixed(2),
            day_high: meta.regularMarketDayHigh,
            day_low: meta.regularMarketDayLow,
            volume: meta.regularMarketVolume,
            market_cap: meta.marketCap,
            fifty_two_week_high: meta.fiftyTwoWeekHigh,
            fifty_two_week_low: meta.fiftyTwoWeekLow,
            currency: meta.currency || 'INR',
            _source: 'Yahoo Finance (NSE)',
            _disclaimer: 'Data for informational purposes only. Not financial advice.',
        };

        await cacheSet(cacheKey, quote, CACHE_TTL.QUOTE);
        return { ...quote, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.QUOTE, is_stale: false } };
    } catch (error) {
        // Graceful degradation: return stale cache if available
        if (cached) {
            return {
                ...cached.data as object,
                _freshness: cached.freshness,
                _source: 'Yahoo Finance (NSE)',
                _degradation_notice: 'Live data unavailable. Showing cached data.',
            };
        }
        throw error;
    }
}

export async function getPriceHistory(ticker: string, range: string = '1y', interval: string = '1d') {
    const cacheKey = `history:${ticker}:${range}:${interval}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const yahooTicker = toYahooTicker(ticker);
    const data = await upstreamFetch<any>('yfinance', {
        url: `${YAHOO_BASE}/v8/finance/chart/${yahooTicker}`,
        params: { interval, range, includePrePost: false },
    });

    const result = data?.chart?.result?.[0];
    if (!result) throw new Error(`No history for ${ticker}`);

    const timestamps = result.timestamp || [];
    const ohlcv = result.indicators?.quote?.[0] || {};

    const history = timestamps.map((ts: number, i: number) => ({
        date: new Date(ts * 1000).toISOString().split('T')[0],
        open: ohlcv.open?.[i],
        high: ohlcv.high?.[i],
        low: ohlcv.low?.[i],
        close: ohlcv.close?.[i],
        volume: ohlcv.volume?.[i],
    })).filter((d: any) => d.close !== null);

    const response = {
        ticker: ticker.toUpperCase(),
        range,
        interval,
        data_points: history.length,
        history,
        _source: 'Yahoo Finance (NSE)',
        _disclaimer: 'Historical data for informational purposes only.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.PRICE_HISTORY);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.PRICE_HISTORY, is_stale: false } };
}

export async function getFinancialStatements(ticker: string, type: 'income' | 'balance' | 'cashflow' = 'income') {
    const cacheKey = `financials:${ticker}:${type}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const yahooTicker = toYahooTicker(ticker);
    const modules: Record<string, string> = {
        income: 'incomeStatementHistory,incomeStatementHistoryQuarterly',
        balance: 'balanceSheetHistory,balanceSheetHistoryQuarterly',
        cashflow: 'cashflowStatementHistory,cashflowStatementHistoryQuarterly',
    };

    const data = await upstreamFetch<any>('yfinance', {
        url: `${YAHOO_BASE}/v10/finance/quoteSummary/${yahooTicker}`,
        params: { modules: modules[type] },
    });

    const result = data?.quoteSummary?.result?.[0];
    if (!result) throw new Error(`No financial data for ${ticker}`);

    const response = {
        ticker: ticker.toUpperCase(),
        statement_type: type,
        data: result,
        _source: 'Yahoo Finance (NSE)',
        _disclaimer: 'Financial data for informational purposes only. Not financial advice.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.FINANCIALS);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.FINANCIALS, is_stale: false } };
}

export async function getKeyRatios(ticker: string) {
    const cacheKey = `ratios:${ticker}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const yahooTicker = toYahooTicker(ticker);
    const data = await upstreamFetch<any>('yfinance', {
        url: `${YAHOO_BASE}/v10/finance/quoteSummary/${yahooTicker}`,
        params: { modules: 'defaultKeyStatistics,financialData,summaryDetail' },
    });

    const result = data?.quoteSummary?.result?.[0];
    if (!result) throw new Error(`No ratio data for ${ticker}`);

    const stats = result.defaultKeyStatistics || {};
    const fin = result.financialData || {};
    const detail = result.summaryDetail || {};

    const ratios = {
        ticker: ticker.toUpperCase(),
        pe_ratio: detail.trailingPE?.raw,
        forward_pe: detail.forwardPE?.raw,
        pb_ratio: stats.priceToBook?.raw,
        ps_ratio: stats.priceToSalesTrailing12Months?.raw,
        roe: fin.returnOnEquity?.raw ? (fin.returnOnEquity.raw * 100).toFixed(2) + '%' : null,
        roce: null, // Not directly available from Yahoo
        debt_to_equity: fin.debtToEquity?.raw,
        current_ratio: fin.currentRatio?.raw,
        dividend_yield: detail.dividendYield?.raw ? (detail.dividendYield.raw * 100).toFixed(2) + '%' : null,
        market_cap: detail.marketCap?.raw,
        enterprise_value: stats.enterpriseValue?.raw,
        beta: stats.beta?.raw,
        operating_margin: fin.operatingMargins?.raw ? (fin.operatingMargins.raw * 100).toFixed(2) + '%' : null,
        profit_margin: fin.profitMargins?.raw ? (fin.profitMargins.raw * 100).toFixed(2) + '%' : null,
        revenue_growth: fin.revenueGrowth?.raw ? (fin.revenueGrowth.raw * 100).toFixed(2) + '%' : null,
        earnings_growth: fin.earningsGrowth?.raw ? (fin.earningsGrowth.raw * 100).toFixed(2) + '%' : null,
        _source: 'Yahoo Finance (NSE)',
        _disclaimer: 'Financial ratios for informational purposes only. Not financial advice.',
    };

    await cacheSet(cacheKey, ratios, CACHE_TTL.FINANCIALS);
    return { ...ratios, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.FINANCIALS, is_stale: false } };
}
