// ============================================================
// MCP Server — Indian Financial Intelligence
// Main server file: registers all tools, resources, prompts
// ============================================================

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import express from 'express';
import cors from 'cors';
import { z } from 'zod';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Auth
import { validateToken, getProtectedResourceMetadata, get401Response, get403Response, type AuthenticatedUser } from './auth/middleware.js';
import { TOOL_SCOPE_MAP, tierHasScope, type Scope, type UserTier, TIER_SCOPES } from './auth/scopes.js';
import { checkRateLimit, get429Response } from './auth/rate-limiter.js';

// Upstream
import { getStockQuote, getPriceHistory, getFinancialStatements, getKeyRatios } from './upstream/yfinance.js';
import { getIndexData, getTopGainersLosers, getShareholdingPattern } from './upstream/nse.js';
import { searchMutualFunds, getFundNav, compareFunds } from './upstream/mfapi.js';
import { getTechnicalIndicators } from './upstream/alpha-vantage.js';
import { getCompanyNews, getMarketNews, getNewsSentiment } from './upstream/news.js';
import { getRbiRates, getInflationData, getMacroSnapshot, getCorporateFilings } from './upstream/macro.js';
import { getAllUpstreamStatuses } from './upstream/client.js';

// Cross-Source
import { crossReferenceSignals, generateResearchBrief, compareCompanies } from './tools/cross-source.js';

// Cache / Data
import { getWatchlist, addToWatchlist, removeFromWatchlist, getResearchBrief, logAudit, getAuditHistory } from './cache/manager.js';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.MCP_SERVER_PORT || '3000');

// Ensure data directory exists
const dataDir = path.join(__dirname, '../data');
if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });

// ============================================================
// Per-session user context (set by auth middleware)
// ============================================================
let currentUser: AuthenticatedUser | null = null;

// ============================================================
// Helper: Execute a tool with auth + rate limit + audit
// ============================================================
async function executeWithAuth<T>(
    toolName: string,
    args: Record<string, unknown>,
    handler: () => Promise<T>
): Promise<T> {
    const user = currentUser;

    // Check auth
    if (!user) {
        const resp = get401Response();
        throw new Error(JSON.stringify(resp.body));
    }

    // Check scope
    const requiredScope = TOOL_SCOPE_MAP[toolName];
    if (requiredScope && !tierHasScope(user.tier, requiredScope as Scope)) {
        const resp = get403Response(requiredScope);
        throw new Error(JSON.stringify(resp.body));
    }

    // Check rate limit
    const rateResult = await checkRateLimit(user.sub, user.tier);
    if (!rateResult.allowed) {
        const resp = get429Response(rateResult);
        throw new Error(JSON.stringify(resp.body));
    }

    // Execute
    const start = Date.now();
    try {
        const result = await handler();
        const latency = Date.now() - start;

        // Audit log
        logAudit({
            user_id: user.sub,
            username: user.preferred_username,
            tier: user.tier,
            tool_name: toolName,
            args,
            latency_ms: latency,
            status: 'success',
        });

        return result;
    } catch (error) {
        const latency = Date.now() - start;
        logAudit({
            user_id: user?.sub || 'anonymous',
            username: user?.preferred_username || 'anonymous',
            tier: user?.tier || 'free',
            tool_name: toolName,
            args,
            latency_ms: latency,
            status: 'error',
            error_message: String(error),
        });
        throw error;
    }
}

// ============================================================
// Create MCP Server
// ============================================================
const server = new McpServer({
    name: 'Indian Financial Intelligence',
    version: '1.0.0',
    capabilities: {
        tools: {},
        resources: {},
        prompts: {},
    },
});

// ============================================================
// MARKET DATA TOOLS
// ============================================================

server.tool(
    'get_stock_quote',
    'Get live/latest quote for an NSE/BSE ticker including LTP, change, volume, market cap, P/E, 52W range',
    { ticker: z.string().describe('NSE/BSE ticker symbol, e.g. RELIANCE, INFY, TCS') },
    async ({ ticker }) => {
        const result = await executeWithAuth('get_stock_quote', { ticker }, () => getStockQuote(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_price_history',
    'Get historical OHLCV data for a ticker over a date range',
    {
        ticker: z.string().describe('NSE ticker symbol'),
        range: z.string().optional().default('1y').describe('Time range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max'),
        interval: z.string().optional().default('1d').describe('Data interval: 1d, 1wk, 1mo'),
    },
    async ({ ticker, range, interval }) => {
        const result = await executeWithAuth('get_price_history', { ticker, range, interval }, () => getPriceHistory(ticker, range, interval));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_index_data',
    'Get current value and details of Nifty 50, Sensex, Bank Nifty, or sectoral indices',
    { index_name: z.string().optional().default('NIFTY 50').describe('Index name: NIFTY 50, SENSEX, NIFTY BANK, etc.') },
    async ({ index_name }) => {
        const result = await executeWithAuth('get_index_data', { index_name }, () => getIndexData(index_name));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_top_gainers_losers',
    "Get today's top gaining and losing stocks on NSE",
    {},
    async () => {
        const result = await executeWithAuth('get_top_gainers_losers', {}, () => getTopGainersLosers());
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_technical_indicators',
    'Get technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands) for a ticker',
    {
        ticker: z.string().describe('NSE ticker symbol'),
        indicators: z.array(z.string()).optional().default(['SMA', 'RSI', 'MACD']).describe('Indicators to fetch'),
    },
    async ({ ticker, indicators }) => {
        const result = await executeWithAuth('get_technical_indicators', { ticker, indicators }, () => getTechnicalIndicators(ticker, indicators));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

// ============================================================
// FUNDAMENTAL ANALYSIS TOOLS
// ============================================================

server.tool(
    'get_financial_statements',
    'Get income statement, balance sheet, or cash flow (annual/quarterly)',
    {
        ticker: z.string().describe('NSE ticker symbol'),
        type: z.enum(['income', 'balance', 'cashflow']).optional().default('income').describe('Statement type'),
    },
    async ({ ticker, type }) => {
        const result = await executeWithAuth('get_financial_statements', { ticker, type }, () => getFinancialStatements(ticker, type));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_key_ratios',
    'Get key financial ratios: P/E, P/B, ROE, ROCE, debt/equity, current ratio, dividend yield',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        const result = await executeWithAuth('get_key_ratios', { ticker }, () => getKeyRatios(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_shareholding_pattern',
    'Get promoter, FII, DII, retail holdings over time',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        const result = await executeWithAuth('get_shareholding_pattern', { ticker }, () => getShareholdingPattern(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_quarterly_results',
    'Get latest quarterly results with YoY/QoQ comparison',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        const result = await executeWithAuth('get_quarterly_results', { ticker }, () =>
            getFinancialStatements(ticker, 'income')
        );
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

// ============================================================
// MUTUAL FUND TOOLS
// ============================================================

server.tool(
    'search_mutual_funds',
    'Search mutual fund schemes by name, fund house, or category',
    { query: z.string().describe('Search query: fund name, AMC, or category') },
    async ({ query }) => {
        const result = await executeWithAuth('search_mutual_funds', { query }, () => searchMutualFunds(query));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_fund_nav',
    'Get latest and historical NAV for a mutual fund scheme',
    { scheme_code: z.string().describe('AMFI scheme code (e.g. 119551)') },
    async ({ scheme_code }) => {
        const result = await executeWithAuth('get_fund_nav', { scheme_code }, () => getFundNav(scheme_code));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'compare_funds',
    'Side-by-side comparison of 2-5 mutual fund schemes',
    { scheme_codes: z.array(z.string()).min(2).max(5).describe('Array of AMFI scheme codes to compare') },
    async ({ scheme_codes }) => {
        const result = await executeWithAuth('compare_funds', { scheme_codes }, () => compareFunds(scheme_codes));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

// ============================================================
// NEWS & SENTIMENT TOOLS
// ============================================================

server.tool(
    'get_company_news',
    'Get latest news articles for a company',
    {
        ticker: z.string().describe('NSE ticker symbol'),
        company_name: z.string().optional().describe('Full company name for better search results'),
    },
    async ({ ticker, company_name }) => {
        const result = await executeWithAuth('get_company_news', { ticker }, () => getCompanyNews(ticker, company_name));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_news_sentiment',
    'Get aggregated sentiment analysis for a company over recent news',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        const result = await executeWithAuth('get_news_sentiment', { ticker }, () => getNewsSentiment(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_market_news',
    'Get broad Indian market and sector news',
    {},
    async () => {
        const result = await executeWithAuth('get_market_news', {}, () => getMarketNews());
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

// ============================================================
// MACRO & REGULATORY TOOLS
// ============================================================

server.tool(
    'get_rbi_rates',
    'Get current RBI repo rate, reverse repo, CRR, SLR, and historical rate changes',
    {},
    async () => {
        const result = await executeWithAuth('get_rbi_rates', {}, () => getRbiRates());
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_inflation_data',
    'Get CPI and WPI inflation time series',
    {},
    async () => {
        const result = await executeWithAuth('get_inflation_data', {}, () => getInflationData());
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'get_corporate_filings',
    'List recent BSE/NSE corporate filings for a company',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        const result = await executeWithAuth('get_corporate_filings', { ticker }, () => getCorporateFilings(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

// ============================================================
// CROSS-SOURCE REASONING TOOLS ⭐
// ============================================================

server.tool(
    'cross_reference_signals',
    'Pull signals from multiple sources (NSE, Yahoo, BSE, NewsAPI, RBI, MFapi) and identify confirmations or contradictions with confidence scoring. Requires Analyst tier.',
    { ticker: z.string().describe('NSE ticker symbol to cross-reference') },
    async ({ ticker }) => {
        const result = await executeWithAuth('cross_reference_signals', { ticker }, () => crossReferenceSignals(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'generate_research_brief',
    'Generate a comprehensive research brief combining price data, fundamentals, MF exposure, news, filings, and macro context. Saved to research://TICKER/latest. Requires Analyst tier.',
    { ticker: z.string().describe('NSE ticker symbol for research brief') },
    async ({ ticker }) => {
        const result = await executeWithAuth('generate_research_brief', { ticker }, () => generateResearchBrief(ticker));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

server.tool(
    'compare_companies',
    'Side-by-side comparison of 2-5 companies across price performance, fundamentals, and news sentiment. Requires Analyst tier.',
    { tickers: z.array(z.string()).min(2).max(5).describe('Array of NSE ticker symbols to compare') },
    async ({ tickers }) => {
        const result = await executeWithAuth('compare_companies', { tickers }, () => compareCompanies(tickers));
        return { content: [{ type: 'text' as const, text: JSON.stringify(result, null, 2) }] };
    }
);

// ============================================================
// WATCHLIST TOOLS
// ============================================================

server.tool(
    'add_to_watchlist',
    'Add a stock ticker to your personal watchlist',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        if (!currentUser) throw new Error('Authentication required');
        addToWatchlist(currentUser.sub, ticker);
        return { content: [{ type: 'text' as const, text: JSON.stringify({ success: true, ticker: ticker.toUpperCase(), message: `${ticker.toUpperCase()} added to watchlist` }) }] };
    }
);

server.tool(
    'remove_from_watchlist',
    'Remove a stock ticker from your personal watchlist',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => {
        if (!currentUser) throw new Error('Authentication required');
        removeFromWatchlist(currentUser.sub, ticker);
        return { content: [{ type: 'text' as const, text: JSON.stringify({ success: true, ticker: ticker.toUpperCase(), message: `${ticker.toUpperCase()} removed from watchlist` }) }] };
    }
);

// ============================================================
// MCP RESOURCES
// ============================================================

server.resource(
    'market_overview',
    'market://overview',
    { description: 'Live market overview: Nifty, Sensex, top movers' },
    async () => {
        const [nifty, sensex, movers] = await Promise.allSettled([
            getIndexData('NIFTY 50'),
            getIndexData('SENSEX'),
            getTopGainersLosers(),
        ]);
        return {
            contents: [{
                uri: 'market://overview',
                mimeType: 'application/json',
                text: JSON.stringify({
                    nifty_50: nifty.status === 'fulfilled' ? nifty.value : null,
                    sensex: sensex.status === 'fulfilled' ? sensex.value : null,
                    top_movers: movers.status === 'fulfilled' ? movers.value : null,
                    _source: 'NSE India / Yahoo Finance',
                }, null, 2),
            }],
        };
    }
);

server.resource(
    'macro_snapshot',
    'macro://snapshot',
    { description: 'Latest macro indicators: repo rate, CPI, GDP, forex reserves, USD-INR' },
    async () => {
        const snapshot = await getMacroSnapshot();
        return {
            contents: [{
                uri: 'macro://snapshot',
                mimeType: 'application/json',
                text: JSON.stringify(snapshot, null, 2),
            }],
        };
    }
);

server.resource(
    'system_health',
    'system://health',
    { description: 'Upstream API health status and remaining quotas' },
    async () => {
        const statuses = getAllUpstreamStatuses();
        return {
            contents: [{
                uri: 'system://health',
                mimeType: 'application/json',
                text: JSON.stringify({
                    server: 'Indian Financial Intelligence MCP',
                    status: 'operational',
                    upstream_apis: statuses,
                    current_user: currentUser ? {
                        username: currentUser.preferred_username,
                        tier: currentUser.tier,
                        scopes: currentUser.scopes,
                    } : null,
                    timestamp: new Date().toISOString(),
                }, null, 2),
            }],
        };
    }
);

// ============================================================
// MCP PROMPTS
// ============================================================

server.prompt(
    'quick_analysis',
    'Fast overview: quote + key ratios + recent news for a ticker',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => ({
        messages: [{
            role: 'user' as const,
            content: {
                type: 'text' as const,
                text: `Provide a quick analysis of ${ticker.toUpperCase()} on NSE. Use the following tools in sequence:
1. get_stock_quote for ${ticker} — current price, change, volume
2. get_key_ratios for ${ticker} — P/E, ROE, debt/equity (if available for your tier)
3. get_company_news for ${ticker} — latest headlines
4. get_news_sentiment for ${ticker} — overall sentiment

Synthesize into a concise brief: "Here's what's happening with ${ticker.toUpperCase()} right now" with key data points and any notable signals.`,
            },
        }],
    })
);

server.prompt(
    'deep_dive',
    'Comprehensive research: pulls all available data, cross-references, generates full research brief. Requires Analyst tier.',
    { ticker: z.string().describe('NSE ticker symbol') },
    async ({ ticker }) => ({
        messages: [{
            role: 'user' as const,
            content: {
                type: 'text' as const,
                text: `Conduct a comprehensive deep-dive analysis of ${ticker.toUpperCase()} on NSE. Execute:
1. get_stock_quote — current trading data
2. get_price_history (range: 6mo) — price trend
3. get_key_ratios — valuation and profitability
4. get_financial_statements (income) — revenue/profit trends
5. get_shareholding_pattern — institutional interest changes
6. get_company_news — recent developments
7. get_news_sentiment — market perception
8. get_corporate_filings — regulatory filings
9. cross_reference_signals — multi-source signal analysis with confidence mesh
10. generate_research_brief — save full brief

Present a structured research note with sections: Price Action, Fundamentals, Institutional Interest, Sentiment, Risk Factors, and Overall Assessment. Cite each source explicitly.`,
            },
        }],
    })
);

server.prompt(
    'sector_scan',
    'Compare top companies in a sector across fundamentals and sentiment',
    { sector: z.string().describe('Sector name, e.g. "IT", "Banking", "Pharma"') },
    async ({ sector }) => {
        const sectorTickers: Record<string, string[]> = {
            IT: ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM'],
            Banking: ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK'],
            Pharma: ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB', 'APOLLOHOSP'],
            Auto: ['TATAMOTORS', 'MARUTI', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO'],
            Energy: ['RELIANCE', 'ONGC', 'NTPC', 'POWERGRID', 'ADANIENT'],
        };
        const tickers = sectorTickers[sector] || ['RELIANCE', 'TCS', 'HDFCBANK'];
        return {
            messages: [{
                role: 'user' as const,
                content: {
                    type: 'text' as const,
                    text: `Scan the ${sector} sector. Compare these companies: ${tickers.join(', ')}.
1. Use compare_companies with tickers [${tickers.map(t => `"${t}"`).join(', ')}]
2. For the top 2 by market cap, run get_news_sentiment
3. Present a sector overview table with: ticker, LTP, change%, P/E, ROE, sentiment
4. Highlight the strongest and weakest performers with reasoning.`,
                },
            }],
        };
    }
);

server.prompt(
    'morning_brief',
    'Daily summary: market overview + watchlist updates + macro changes + key news',
    {},
    async () => ({
        messages: [{
            role: 'user' as const,
            content: {
                type: 'text' as const,
                text: `Generate a morning market brief for today:
1. get_index_data for NIFTY 50 and SENSEX — market status
2. get_top_gainers_losers — biggest movers
3. get_rbi_rates — any recent policy changes
4. get_market_news — top 5 headlines
5. Read macro://snapshot resource for macro context

Present as a structured morning brief with sections:
- Market Pulse (indices, direction)
- Top Movers (gainers/losers)
- Macro Backdrop (rates, inflation, forex)
- Key Headlines
- Outlook for the day`,
            },
        }],
    })
);

// ============================================================
// EXPRESS HTTP SERVER
// ============================================================

const app = express();
app.use(cors());
app.use(express.json());

// RFC 9728: Protected Resource Metadata
app.get('/.well-known/oauth-protected-resource', (_req, res) => {
    res.json(getProtectedResourceMetadata());
});

// Health check
app.get('/health', async (_req, res) => {
    const statuses = getAllUpstreamStatuses();
    res.json({
        status: 'healthy',
        server: 'Indian Financial Intelligence MCP',
        version: '1.0.0',
        upstream_apis: statuses,
        timestamp: new Date().toISOString(),
    });
});

// MCP Streamable HTTP Transport
const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });

// Auth middleware for MCP endpoints
app.use('/mcp', async (req, res, next) => {
    const authHeader = req.headers.authorization;
    const user = await validateToken(authHeader);

    if (!user) {
        // Allow unauthenticated for capability discovery (list tools/resources)
        // But tools themselves will enforce auth via executeWithAuth
        currentUser = null;
    } else {
        currentUser = user;
    }
    next();
});

app.all('/mcp', async (req, res) => {
    try {
        await transport.handleRequest(req, res, req.body);
    } catch (error) {
        console.error('[MCP] Transport error:', error);
        if (!res.headersSent) {
            res.status(500).json({ error: 'Internal server error' });
        }
    }
});

// Connect MCP server to transport
await server.connect(transport);

// Start
app.listen(PORT, () => {
    console.log(`
╔══════════════════════════════════════════════════════════╗
║    🇮🇳 Indian Financial Intelligence MCP Server          ║
║    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    ║
║    MCP Endpoint:  http://localhost:${PORT}/mcp             ║
║    Health:        http://localhost:${PORT}/health           ║
║    OAuth Meta:    http://localhost:${PORT}/.well-known/     ║
║                   oauth-protected-resource               ║
║    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    ║
║    Tools: 21 | Resources: 3 | Prompts: 4                ║
║    Auth: OAuth 2.1 + PKCE via Keycloak                   ║
╚══════════════════════════════════════════════════════════╝
  `);
});

export { server, app };
