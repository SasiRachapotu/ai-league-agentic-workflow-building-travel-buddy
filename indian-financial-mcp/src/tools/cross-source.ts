// ============================================================
// Cross-Source Reasoning Tools — The Confidence Mesh ⭐
// ============================================================

import { getStockQuote, getPriceHistory, getKeyRatios, getFinancialStatements } from '../upstream/yfinance.js';
import { getIndexData, getShareholdingPattern, getTopGainersLosers } from '../upstream/nse.js';
import { getCompanyNews, getNewsSentiment, getMarketNews } from '../upstream/news.js';
import { getTechnicalIndicators } from '../upstream/alpha-vantage.js';
import { searchMutualFunds, getFundNav, compareFunds } from '../upstream/mfapi.js';
import { getRbiRates, getInflationData, getMacroSnapshot, getCorporateFilings } from '../upstream/macro.js';
import { saveResearchBrief } from '../cache/manager.js';

// ============================================================
// Confidence Mesh — Quantified cross-source agreement
// ============================================================

interface Signal {
    source: string;
    data_point: string;
    interpretation: 'CONFIRMS' | 'CONTRADICTS' | 'NEUTRAL';
    confidence: number; // 0-1
    detail: string;
}

function computeAggregateConfidence(signals: Signal[]): { score: number; label: string; direction: string } {
    const confirms = signals.filter(s => s.interpretation === 'CONFIRMS');
    const contradicts = signals.filter(s => s.interpretation === 'CONTRADICTS');

    const confirmWeight = confirms.reduce((sum, s) => sum + s.confidence, 0);
    const contradictWeight = contradicts.reduce((sum, s) => sum + s.confidence, 0);
    const totalWeight = signals.reduce((sum, s) => sum + s.confidence, 0) || 1;

    const netScore = (confirmWeight - contradictWeight) / totalWeight;
    const absScore = Math.abs(netScore);

    let label: string;
    if (absScore > 0.6) label = 'Strong';
    else if (absScore > 0.3) label = 'Moderate';
    else label = 'Weak / Mixed';

    const direction = netScore > 0.1 ? 'Bullish' : netScore < -0.1 ? 'Bearish' : 'Neutral';

    return {
        score: parseFloat(((netScore + 1) / 2).toFixed(2)), // Normalize to 0-1
        label: `${label} ${direction}`,
        direction,
    };
}

// ============================================================
// cross_reference_signals
// ============================================================

export async function crossReferenceSignals(ticker: string) {
    const signals: Signal[] = [];
    const sourcesUsed: string[] = [];
    const errors: string[] = [];

    // 1. Price Data (NSE/Yahoo)
    try {
        const quote = await getStockQuote(ticker);
        const q = quote as any;
        const changePercent = parseFloat(q.change_percent || '0');

        signals.push({
            source: 'Yahoo Finance (NSE)',
            data_point: `LTP: ₹${q.ltp}, Change: ${changePercent >= 0 ? '+' : ''}${q.change_percent}%`,
            interpretation: changePercent > 1 ? 'CONFIRMS' : changePercent < -1 ? 'CONTRADICTS' : 'NEUTRAL',
            confidence: Math.min(0.9, 0.5 + Math.abs(changePercent) / 10),
            detail: `${ticker} is trading at ₹${q.ltp} (${changePercent >= 0 ? 'up' : 'down'} ${q.change_percent}% from previous close of ₹${q.previous_close})`,
        });
        sourcesUsed.push('Yahoo Finance (NSE)');
    } catch (e) {
        errors.push(`Price data: ${e}`);
    }

    // 2. Key Ratios (Yahoo Finance)
    try {
        const ratios = await getKeyRatios(ticker);
        const r = ratios as any;
        const pe = r.pe_ratio;
        const roe = parseFloat(r.roe || '0');

        if (pe) {
            signals.push({
                source: 'Yahoo Finance (Fundamentals)',
                data_point: `P/E: ${pe}, ROE: ${r.roe}, Debt/Equity: ${r.debt_to_equity}`,
                interpretation: pe < 25 && roe > 15 ? 'CONFIRMS' : pe > 40 ? 'CONTRADICTS' : 'NEUTRAL',
                confidence: 0.7,
                detail: `Valuation: P/E of ${pe} ${pe < 25 ? 'suggests reasonable valuation' : pe > 40 ? 'suggests expensive valuation' : 'is in line with sector'}`,
            });
        }
        sourcesUsed.push('Yahoo Finance (Fundamentals)');
    } catch (e) {
        errors.push(`Ratios: ${e}`);
    }

    // 3. Shareholding Pattern (NSE)
    try {
        const shareholding = await getShareholdingPattern(ticker);
        const sh = shareholding as any;

        if (sh.fii_holding !== null) {
            signals.push({
                source: 'NSE India (Shareholding)',
                data_point: `Promoter: ${sh.promoter_holding}%, FII: ${sh.fii_holding}%, DII: ${sh.dii_holding}%`,
                interpretation: 'NEUTRAL',
                confidence: 0.65,
                detail: `Shareholding: Promoter ${sh.promoter_holding}%, FII ${sh.fii_holding}%, DII ${sh.dii_holding}%`,
            });
            sourcesUsed.push('NSE India (Shareholding)');
        }
    } catch (e) {
        errors.push(`Shareholding: ${e}`);
    }

    // 4. News Sentiment (NewsAPI / Finnhub)
    try {
        const sentiment = await getNewsSentiment(ticker);
        const s = sentiment as any;
        const overall = s.overall_sentiment;

        signals.push({
            source: (s as any)._source || 'NewsAPI',
            data_point: `Sentiment: ${overall} (Bullish: ${s.bullish_percent}%, Bearish: ${s.bearish_percent}%)`,
            interpretation: overall === 'Bullish' ? 'CONFIRMS' : overall === 'Bearish' ? 'CONTRADICTS' : 'NEUTRAL',
            confidence: 0.6 + (s.articles_analyzed || 0) * 0.02,
            detail: `News sentiment is ${overall} based on ${s.articles_analyzed || 'N/A'} articles analyzed`,
        });
        sourcesUsed.push((s as any)._source || 'NewsAPI');
    } catch (e) {
        errors.push(`Sentiment: ${e}`);
    }

    // 5. Macro Context (RBI)
    try {
        const macro = await getRbiRates();
        const m = macro as any;

        signals.push({
            source: 'RBI DBIE',
            data_point: `Repo Rate: ${m.repo_rate}%, Last Action: ${m.last_updated}`,
            interpretation: 'NEUTRAL',
            confidence: 0.5,
            detail: `RBI repo rate at ${m.repo_rate}%. Monetary policy ${m.repo_rate <= 6.25 ? 'accommodative' : 'neutral to tight'}`,
        });
        sourcesUsed.push('RBI DBIE');
    } catch (e) {
        errors.push(`Macro: ${e}`);
    }

    // 6. MF Exposure (MFapi)
    try {
        const mfResults = await searchMutualFunds(ticker);
        const mf = mfResults as any;
        const mfCount = mf.total_results || 0;

        if (mfCount > 0) {
            signals.push({
                source: 'MFapi.in (AMFI)',
                data_point: `Found in ${mfCount} mutual fund schemes`,
                interpretation: mfCount > 5 ? 'CONFIRMS' : 'NEUTRAL',
                confidence: 0.55,
                detail: `${ticker} appears in ${mfCount} mutual fund scheme names — ${mfCount > 10 ? 'widely held by institutional funds' : 'moderate MF presence'}`,
            });
            sourcesUsed.push('MFapi.in (AMFI)');
        }
    } catch (e) {
        errors.push(`MF lookup: ${e}`);
    }

    // Compute aggregate
    const aggregate = computeAggregateConfidence(signals);

    // Identify contradictions
    const contradictions = signals.filter(s => s.interpretation !== signals[0]?.interpretation && s.interpretation !== 'NEUTRAL');

    return {
        ticker: ticker.toUpperCase(),
        analysis_timestamp: new Date().toISOString(),
        aggregate_confidence: aggregate,
        signals,
        sources_used: sourcesUsed,
        contradictions: contradictions.length > 0 ? {
            count: contradictions.length,
            details: contradictions.map(c => `${c.source}: ${c.detail}`),
            alert: 'CONTRADICTION DETECTED — signals from different sources diverge. Investigate further.',
        } : { count: 0, details: [], alert: null },
        errors: errors.length > 0 ? errors : undefined,
        _sources: sourcesUsed,
        _disclaimer: 'Cross-source analysis for informational purposes only. Not financial advice. Always do your own research.',
    };
}

// ============================================================
// generate_research_brief
// ============================================================

export async function generateResearchBrief(ticker: string) {
    const sourcesUsed: string[] = [];

    // Gather all data in parallel
    const [quote, ratios, priceHistory, sentiment, news, filings, macro] = await Promise.allSettled([
        getStockQuote(ticker),
        getKeyRatios(ticker),
        getPriceHistory(ticker, '6mo', '1wk'),
        getNewsSentiment(ticker),
        getCompanyNews(ticker),
        getCorporateFilings(ticker),
        getMacroSnapshot(),
    ]);

    const brief: Record<string, any> = {
        ticker: ticker.toUpperCase(),
        generated_at: new Date().toISOString(),
        sections: {},
    };

    // Price Summary
    if (quote.status === 'fulfilled') {
        const q = quote.value as any;
        brief.sections.price_summary = {
            ltp: q.ltp,
            change: q.change,
            change_percent: q.change_percent,
            volume: q.volume,
            market_cap: q.market_cap,
            fifty_two_week_high: q.fifty_two_week_high,
            fifty_two_week_low: q.fifty_two_week_low,
        };
        sourcesUsed.push('Yahoo Finance (NSE)');
    }

    // Fundamentals
    if (ratios.status === 'fulfilled') {
        const r = ratios.value as any;
        brief.sections.fundamentals = {
            pe_ratio: r.pe_ratio,
            pb_ratio: r.pb_ratio,
            roe: r.roe,
            debt_to_equity: r.debt_to_equity,
            dividend_yield: r.dividend_yield,
            revenue_growth: r.revenue_growth,
            profit_margin: r.profit_margin,
        };
        sourcesUsed.push('Yahoo Finance (Fundamentals)');
    }

    // Price History (weekly summary)
    if (priceHistory.status === 'fulfilled') {
        const ph = priceHistory.value as any;
        brief.sections.price_trend = {
            period: ph.range,
            data_points: ph.data_points,
            first_close: ph.history?.[0]?.close,
            last_close: ph.history?.[ph.history.length - 1]?.close,
            period_return: ph.history?.length > 1
                ? ((ph.history[ph.history.length - 1].close - ph.history[0].close) / ph.history[0].close * 100).toFixed(2) + '%'
                : 'N/A',
        };
    }

    // Sentiment
    if (sentiment.status === 'fulfilled') {
        const s = sentiment.value as any;
        brief.sections.sentiment = {
            overall: s.overall_sentiment,
            bullish_percent: s.bullish_percent,
            bearish_percent: s.bearish_percent,
            articles_analyzed: s.articles_analyzed,
        };
        sourcesUsed.push(s._source || 'NewsAPI');
    }

    // Recent News Headlines
    if (news.status === 'fulfilled') {
        const n = news.value as any;
        brief.sections.recent_news = (n.articles || []).slice(0, 5).map((a: any) => ({
            title: a.title,
            source: a.source,
            date: a.published_at,
        }));
    }

    // Filings
    if (filings.status === 'fulfilled') {
        const f = filings.value as any;
        brief.sections.recent_filings = (f.filings || []).slice(0, 3);
        sourcesUsed.push('BSE India');
    }

    // Macro Context
    if (macro.status === 'fulfilled') {
        const m = macro.value as any;
        brief.sections.macro_context = {
            repo_rate: m.rbi_rates?.repo_rate,
            cpi_inflation: m.inflation?.cpi?.value,
            gdp_growth: m.gdp?.latest_growth,
            usd_inr: m.usd_inr?.rate,
        };
        sourcesUsed.push('RBI DBIE');
    }

    brief.sources = sourcesUsed;
    brief._disclaimer = 'Research brief for informational purposes only. Not financial advice. Always conduct independent research.';

    // Save to persistent storage
    saveResearchBrief(ticker, brief, sourcesUsed);

    return brief;
}

// ============================================================
// compare_companies
// ============================================================

export async function compareCompanies(tickers: string[]) {
    const comparisons = await Promise.all(
        tickers.map(async (ticker) => {
            const [quote, ratios, sentiment] = await Promise.allSettled([
                getStockQuote(ticker),
                getKeyRatios(ticker),
                getNewsSentiment(ticker),
            ]);

            const entry: Record<string, any> = { ticker: ticker.toUpperCase() };

            if (quote.status === 'fulfilled') {
                const q = quote.value as any;
                entry.price = { ltp: q.ltp, change_percent: q.change_percent, market_cap: q.market_cap };
            }
            if (ratios.status === 'fulfilled') {
                const r = ratios.value as any;
                entry.fundamentals = { pe_ratio: r.pe_ratio, roe: r.roe, debt_to_equity: r.debt_to_equity, dividend_yield: r.dividend_yield };
            }
            if (sentiment.status === 'fulfilled') {
                const s = sentiment.value as any;
                entry.sentiment = { overall: s.overall_sentiment, bullish_percent: s.bullish_percent };
            }

            return entry;
        })
    );

    return {
        comparison: comparisons,
        companies_compared: tickers.length,
        _sources: ['Yahoo Finance (NSE)', 'NewsAPI/Finnhub'],
        _disclaimer: 'Comparison for informational purposes only. Not financial advice.',
    };
}
