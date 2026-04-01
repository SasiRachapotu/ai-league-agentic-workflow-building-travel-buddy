// ============================================================
// Base Upstream Client — Circuit Breaker + Retry + Tracking
// ============================================================

import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios';

interface CircuitState {
    failures: number;
    lastFailure: number;
    state: 'closed' | 'open' | 'half-open';
    remainingQuota?: number;
    maxQuota?: number;
}

const circuitStates = new Map<string, CircuitState>();
const FAILURE_THRESHOLD = 5;
const RECOVERY_TIME_MS = 60000; // 1 minute

export interface UpstreamStatus {
    name: string;
    status: 'healthy' | 'degraded' | 'down';
    remaining_quota?: number;
    max_quota?: number;
    last_error?: string;
    last_failure_at?: string;
}

export function getUpstreamStatus(name: string): UpstreamStatus {
    const state = circuitStates.get(name);
    if (!state || state.state === 'closed') {
        return {
            name,
            status: 'healthy',
            remaining_quota: state?.remainingQuota,
            max_quota: state?.maxQuota,
        };
    }
    return {
        name,
        status: state.state === 'open' ? 'down' : 'degraded',
        remaining_quota: state.remainingQuota,
        max_quota: state.maxQuota,
        last_failure_at: new Date(state.lastFailure).toISOString(),
    };
}

export function getAllUpstreamStatuses(): UpstreamStatus[] {
    const providers = ['NSE India', 'yfinance', 'MFapi.in', 'Alpha Vantage', 'Finnhub', 'NewsAPI', 'BSE India', 'RBI DBIE'];
    return providers.map(name => getUpstreamStatus(name));
}

export async function upstreamFetch<T>(
    providerName: string,
    config: AxiosRequestConfig,
    options: { retries?: number; retryDelay?: number } = {}
): Promise<T> {
    const { retries = 2, retryDelay = 1000 } = options;

    // Check circuit breaker
    const state = circuitStates.get(providerName) || { failures: 0, lastFailure: 0, state: 'closed' as const };

    if (state.state === 'open') {
        if (Date.now() - state.lastFailure > RECOVERY_TIME_MS) {
            state.state = 'half-open';
        } else {
            throw new Error(`[${providerName}] Circuit breaker OPEN — upstream is down. Try again later.`);
        }
    }

    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const response: AxiosResponse<T> = await axios({
                timeout: 15000,
                ...config,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    Accept: 'application/json',
                    ...config.headers,
                },
            });

            // Success — reset circuit
            state.failures = 0;
            state.state = 'closed';
            circuitStates.set(providerName, state);

            return response.data;
        } catch (error) {
            lastError = error instanceof Error ? error : new Error(String(error));

            if (attempt < retries) {
                await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)));
            }
        }
    }

    // Record failure
    state.failures += 1;
    state.lastFailure = Date.now();
    if (state.failures >= FAILURE_THRESHOLD) {
        state.state = 'open';
        console.error(`[${providerName}] Circuit breaker OPENED after ${FAILURE_THRESHOLD} failures`);
    }
    circuitStates.set(providerName, state);

    throw lastError || new Error(`[${providerName}] Request failed after ${retries + 1} attempts`);
}

export function updateQuotaTracking(providerName: string, remaining: number, max: number) {
    const state = circuitStates.get(providerName) || { failures: 0, lastFailure: 0, state: 'closed' as const };
    state.remainingQuota = remaining;
    state.maxQuota = max;
    circuitStates.set(providerName, state);
}
