// ============================================================
// NewsAPI + Finnhub — News Articles & Sentiment
// ============================================================

import { upstreamFetch } from './client.js';
import { cacheGet, cacheSet, CACHE_TTL } from '../cache/manager.js';

const NEWSAPI_BASE = 'https://newsapi.org/v2';
const FINNHUB_BASE = 'https://finnhub.io/api/v1';

// ---- NewsAPI ----
export async function getCompanyNews(ticker: string, companyName?: string) {
    const cacheKey = `news:company:${ticker}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const apiKey = process.env.NEWSAPI_API_KEY;
    if (!apiKey) {
        return {
            ticker: ticker.toUpperCase(),
            articles: [],
            error: 'NewsAPI key not configured',
            _source: 'NewsAPI',
            _degradation_notice: 'News unavailable — API key missing.',
        };
    }

    const query = companyName || ticker;
    const data = await upstreamFetch<any>('NewsAPI', {
        url: `${NEWSAPI_BASE}/everything`,
        params: {
            q: `${query} AND (India OR NSE OR BSE OR stock)`,
            language: 'en',
            sortBy: 'publishedAt',
            pageSize: 10,
            apiKey,
        },
    });

    const articles = (data.articles || []).map((a: any) => ({
        title: a.title,
        description: a.description,
        source: a.source?.name,
        url: a.url,
        published_at: a.publishedAt,
        image_url: a.urlToImage,
    }));

    const response = {
        ticker: ticker.toUpperCase(),
        total_results: data.totalResults || 0,
        articles,
        _source: 'NewsAPI',
        _disclaimer: 'News aggregation for informational purposes only.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.NEWS);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.NEWS, is_stale: false } };
}

export async function getMarketNews() {
    const cacheKey = 'news:market:india';
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const apiKey = process.env.NEWSAPI_API_KEY;
    if (!apiKey) {
        return { articles: [], error: 'NewsAPI key not configured', _source: 'NewsAPI' };
    }

    const data = await upstreamFetch<any>('NewsAPI', {
        url: `${NEWSAPI_BASE}/everything`,
        params: {
            q: '(Nifty OR Sensex OR NSE OR BSE OR "Indian stock market" OR RBI)',
            language: 'en',
            sortBy: 'publishedAt',
            pageSize: 15,
            apiKey,
        },
    });

    const articles = (data.articles || []).map((a: any) => ({
        title: a.title,
        description: a.description,
        source: a.source?.name,
        url: a.url,
        published_at: a.publishedAt,
    }));

    const response = {
        category: 'Indian Financial Markets',
        total_results: data.totalResults || 0,
        articles,
        _source: 'NewsAPI',
        _disclaimer: 'News aggregation for informational purposes only.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.NEWS);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.NEWS, is_stale: false } };
}

// ---- Finnhub Sentiment ----
export async function getNewsSentiment(ticker: string) {
    const cacheKey = `sentiment:${ticker}`;
    const cached = await cacheGet(cacheKey);
    if (cached && !cached.freshness.is_stale) {
        return { ...cached.data as object, _freshness: cached.freshness };
    }

    const apiKey = process.env.FINNHUB_API_KEY;

    // Try Finnhub first
    if (apiKey) {
        try {
            const data = await upstreamFetch<any>('Finnhub', {
                url: `${FINNHUB_BASE}/news-sentiment`,
                params: { symbol: `${ticker.toUpperCase()}.NS`, token: apiKey },
            });

            if (data && data.sentiment) {
                const response = {
                    ticker: ticker.toUpperCase(),
                    overall_sentiment: data.sentiment,
                    buzz: data.buzz,
                    company_news_score: data.companyNewsScore,
                    sector_average_sentiment: data.sectorAverageBullishPercent,
                    _source: 'Finnhub',
                    _disclaimer: 'Sentiment analysis for informational purposes only.',
                };
                await cacheSet(cacheKey, response, CACHE_TTL.SENTIMENT);
                return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.SENTIMENT, is_stale: false } };
            }
        } catch {
            // Fall through to simple sentiment
        }
    }

    // Fallback: derive sentiment from NewsAPI headlines
    const news = await getCompanyNews(ticker);
    const articles = (news as any).articles || [];

    // Simple keyword-based sentiment
    const positiveWords = ['surge', 'rally', 'gain', 'profit', 'growth', 'beat', 'upgrade', 'bullish', 'record', 'high', 'strong'];
    const negativeWords = ['fall', 'drop', 'loss', 'decline', 'crash', 'downgrade', 'bearish', 'weak', 'miss', 'cut', 'risk'];

    let positiveCount = 0;
    let negativeCount = 0;

    articles.forEach((article: any) => {
        const text = `${article.title} ${article.description}`.toLowerCase();
        positiveWords.forEach(w => { if (text.includes(w)) positiveCount++; });
        negativeWords.forEach(w => { if (text.includes(w)) negativeCount++; });
    });

    const total = positiveCount + negativeCount || 1;
    const bullish_percent = (positiveCount / total * 100).toFixed(1);
    const bearish_percent = (negativeCount / total * 100).toFixed(1);

    let overall: string;
    if (positiveCount > negativeCount * 1.5) overall = 'Bullish';
    else if (negativeCount > positiveCount * 1.5) overall = 'Bearish';
    else overall = 'Neutral';

    const response = {
        ticker: ticker.toUpperCase(),
        overall_sentiment: overall,
        bullish_percent: parseFloat(bullish_percent),
        bearish_percent: parseFloat(bearish_percent),
        articles_analyzed: articles.length,
        positive_signals: positiveCount,
        negative_signals: negativeCount,
        method: apiKey ? 'Finnhub + NewsAPI fallback' : 'NewsAPI keyword analysis',
        _source: 'NewsAPI (keyword sentiment)',
        _disclaimer: 'Sentiment is algorithmically derived and may not reflect actual market conditions.',
    };

    await cacheSet(cacheKey, response, CACHE_TTL.SENTIMENT);
    return { ...response, _freshness: { source: 'api', cached_at: new Date().toISOString(), ttl_remaining_seconds: CACHE_TTL.SENTIMENT, is_stale: false } };
}
