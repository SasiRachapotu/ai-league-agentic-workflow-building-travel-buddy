// ============================================================
// Redis-backed Rate Limiter — Per-user, per-tier
// ============================================================

import { TIER_RATE_LIMITS, type UserTier } from './scopes.js';

// In-memory fallback rate limiter (no Redis dependency required)
const rateLimitStore = new Map<string, { count: number; resetAt: number }>();

export interface RateLimitResult {
    allowed: boolean;
    remaining: number;
    limit: number;
    resetAt: Date;
    retryAfterSeconds?: number;
}

export async function checkRateLimit(userId: string, tier: UserTier): Promise<RateLimitResult> {
    const limits = TIER_RATE_LIMITS[tier];
    const key = `ratelimit:${userId}`;
    const now = Date.now();

    let entry = rateLimitStore.get(key);

    // Reset window if expired
    if (!entry || now >= entry.resetAt) {
        entry = {
            count: 0,
            resetAt: now + limits.windowSeconds * 1000,
        };
    }

    entry.count += 1;
    rateLimitStore.set(key, entry);

    const allowed = entry.count <= limits.maxCalls;
    const remaining = Math.max(0, limits.maxCalls - entry.count);
    const resetAt = new Date(entry.resetAt);

    if (!allowed) {
        const retryAfterSeconds = Math.ceil((entry.resetAt - now) / 1000);
        return { allowed, remaining, limit: limits.maxCalls, resetAt, retryAfterSeconds };
    }

    return { allowed, remaining, limit: limits.maxCalls, resetAt };
}

export function get429Response(result: RateLimitResult) {
    return {
        status: 429,
        headers: {
            'Retry-After': String(result.retryAfterSeconds || 60),
            'X-RateLimit-Limit': String(result.limit),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': result.resetAt.toISOString(),
        },
        body: {
            error: 'rate_limit_exceeded',
            error_description: `Rate limit of ${result.limit} calls/hour exceeded. Retry after ${result.retryAfterSeconds} seconds.`,
            retry_after_seconds: result.retryAfterSeconds,
            limit: result.limit,
            reset_at: result.resetAt.toISOString(),
        },
    };
}
