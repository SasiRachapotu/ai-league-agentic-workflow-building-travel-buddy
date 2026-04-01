// ============================================================
// Scope Definitions & Tier → Scope Mapping
// ============================================================

export type Scope =
    | 'market:read'
    | 'fundamentals:read'
    | 'technicals:read'
    | 'mf:read'
    | 'news:read'
    | 'filings:read'
    | 'filings:deep'
    | 'macro:read'
    | 'macro:historical'
    | 'research:generate'
    | 'watchlist:read'
    | 'watchlist:write';

export type UserTier = 'free' | 'premium' | 'analyst';

export const TIER_SCOPES: Record<UserTier, Scope[]> = {
    free: [
        'market:read',
        'mf:read',
        'news:read',
        'watchlist:read',
        'watchlist:write',
    ],
    premium: [
        'market:read',
        'fundamentals:read',
        'technicals:read',
        'mf:read',
        'news:read',
        'macro:read',
        'watchlist:read',
        'watchlist:write',
    ],
    analyst: [
        'market:read',
        'fundamentals:read',
        'technicals:read',
        'mf:read',
        'news:read',
        'filings:read',
        'filings:deep',
        'macro:read',
        'macro:historical',
        'research:generate',
        'watchlist:read',
        'watchlist:write',
    ],
};

export const TIER_RATE_LIMITS: Record<UserTier, { maxCalls: number; windowSeconds: number }> = {
    free: { maxCalls: 30, windowSeconds: 3600 },
    premium: { maxCalls: 150, windowSeconds: 3600 },
    analyst: { maxCalls: 500, windowSeconds: 3600 },
};

export function getTierFromRoles(roles: string[]): UserTier {
    if (roles.includes('analyst')) return 'analyst';
    if (roles.includes('premium_user')) return 'premium';
    return 'free';
}

export function hasScope(userScopes: Scope[], required: Scope): boolean {
    return userScopes.includes(required);
}

export function tierHasScope(tier: UserTier, scope: Scope): boolean {
    return TIER_SCOPES[tier].includes(scope);
}

// Map of tool names to required scopes
export const TOOL_SCOPE_MAP: Record<string, Scope> = {
    // Market Data
    get_stock_quote: 'market:read',
    get_price_history: 'market:read',
    get_index_data: 'market:read',
    get_top_gainers_losers: 'market:read',
    get_technical_indicators: 'technicals:read',

    // Fundamentals
    get_financial_statements: 'fundamentals:read',
    get_key_ratios: 'fundamentals:read',
    get_shareholding_pattern: 'fundamentals:read',
    get_quarterly_results: 'fundamentals:read',

    // Mutual Funds
    search_mutual_funds: 'mf:read',
    get_fund_nav: 'mf:read',
    compare_funds: 'mf:read',

    // News
    get_company_news: 'news:read',
    get_news_sentiment: 'news:read',
    get_market_news: 'news:read',

    // Macro / Regulatory
    get_rbi_rates: 'macro:read',
    get_inflation_data: 'macro:read',
    get_corporate_filings: 'filings:read',

    // Cross-Source Reasoning
    cross_reference_signals: 'research:generate',
    generate_research_brief: 'research:generate',
    compare_companies: 'research:generate',
};
