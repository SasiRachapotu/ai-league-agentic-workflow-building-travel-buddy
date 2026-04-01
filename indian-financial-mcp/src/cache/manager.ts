// ============================================================
// 3-Tier Cache Manager — L1 In-Memory → L2 SQLite → L3 API
// ============================================================

import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// TTL presets by data type (in seconds)
export const CACHE_TTL = {
    QUOTE: 60,
    PRICE_HISTORY: 3600,
    INDEX: 120,
    TECHNICALS: 1800,
    FINANCIALS: 86400,
    MF_NAV: 3600,
    MF_SEARCH: 86400,
    NEWS: 1800,
    SENTIMENT: 3600,
    MACRO: 43200,
    FILINGS: 604800,
    SHAREHOLDING: 86400,
} as const;

// L1: In-Memory Cache
const memoryCache = new Map<string, { data: unknown; expiresAt: number; cachedAt: number }>();

// L2: SQLite Cache
let db: Database.Database;

function getDb(): Database.Database {
    if (!db) {
        const dataDir = path.join(__dirname, '../../data');
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
        }
        const dbPath = path.join(dataDir, 'cache.db');
        db = new Database(dbPath);
        db.pragma('journal_mode = WAL');
        db.exec(`
      CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        cached_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL
      )
    `);
        db.exec(`
      CREATE TABLE IF NOT EXISTS watchlists (
        user_id TEXT NOT NULL,
        ticker TEXT NOT NULL,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, ticker)
      )
    `);
        db.exec(`
      CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        user_id TEXT NOT NULL,
        username TEXT,
        tier TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        args TEXT,
        sources_used TEXT,
        cache_hit INTEGER DEFAULT 0,
        latency_ms INTEGER,
        status TEXT DEFAULT 'success',
        error_message TEXT
      )
    `);
        db.exec(`
      CREATE TABLE IF NOT EXISTS research_briefs (
        ticker TEXT PRIMARY KEY,
        brief TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        sources TEXT NOT NULL
      )
    `);
    }
    return db;
}

export interface CacheEntry<T = unknown> {
    data: T;
    freshness: {
        source: 'memory' | 'sqlite' | 'api';
        cached_at: string;
        ttl_remaining_seconds: number;
        is_stale: boolean;
    };
}

export async function cacheGet<T>(key: string): Promise<CacheEntry<T> | null> {
    const now = Date.now();

    // L1: Memory
    const memEntry = memoryCache.get(key);
    if (memEntry && now < memEntry.expiresAt) {
        return {
            data: memEntry.data as T,
            freshness: {
                source: 'memory',
                cached_at: new Date(memEntry.cachedAt).toISOString(),
                ttl_remaining_seconds: Math.ceil((memEntry.expiresAt - now) / 1000),
                is_stale: false,
            },
        };
    }

    // L2: SQLite
    try {
        const database = getDb();
        const row = database.prepare('SELECT data, cached_at, expires_at FROM cache WHERE key = ?').get(key) as
            | { data: string; cached_at: number; expires_at: number }
            | undefined;

        if (row && now < row.expires_at) {
            const data = JSON.parse(row.data) as T;
            memoryCache.set(key, { data, expiresAt: row.expires_at, cachedAt: row.cached_at });
            return {
                data,
                freshness: {
                    source: 'sqlite',
                    cached_at: new Date(row.cached_at).toISOString(),
                    ttl_remaining_seconds: Math.ceil((row.expires_at - now) / 1000),
                    is_stale: false,
                },
            };
        }

        // Stale data for graceful degradation
        if (row) {
            const data = JSON.parse(row.data) as T;
            return {
                data,
                freshness: {
                    source: 'sqlite',
                    cached_at: new Date(row.cached_at).toISOString(),
                    ttl_remaining_seconds: 0,
                    is_stale: true,
                },
            };
        }
    } catch (error) {
        console.warn('[Cache] SQLite read error:', error);
    }

    return null;
}

export async function cacheSet<T>(key: string, data: T, ttlSeconds: number): Promise<void> {
    const now = Date.now();
    const expiresAt = now + ttlSeconds * 1000;

    memoryCache.set(key, { data, expiresAt, cachedAt: now });

    try {
        const database = getDb();
        database.prepare(
            'INSERT OR REPLACE INTO cache (key, data, cached_at, expires_at) VALUES (?, ?, ?, ?)'
        ).run(key, JSON.stringify(data), now, expiresAt);
    } catch (error) {
        console.warn('[Cache] SQLite write error:', error);
    }
}

// ============================================================
// Watchlist CRUD
// ============================================================

export function getWatchlist(userId: string): string[] {
    const database = getDb();
    const rows = database.prepare('SELECT ticker FROM watchlists WHERE user_id = ? ORDER BY added_at').all(userId) as { ticker: string }[];
    return rows.map(r => r.ticker);
}

export function addToWatchlist(userId: string, ticker: string): void {
    const database = getDb();
    database.prepare('INSERT OR IGNORE INTO watchlists (user_id, ticker) VALUES (?, ?)').run(userId, ticker.toUpperCase());
}

export function removeFromWatchlist(userId: string, ticker: string): void {
    const database = getDb();
    database.prepare('DELETE FROM watchlists WHERE user_id = ? AND ticker = ?').run(userId, ticker.toUpperCase());
}

// ============================================================
// Research Brief Storage
// ============================================================

export function saveResearchBrief(ticker: string, brief: object, sources: string[]): void {
    const database = getDb();
    database.prepare(
        'INSERT OR REPLACE INTO research_briefs (ticker, brief, generated_at, sources) VALUES (?, ?, ?, ?)'
    ).run(ticker.toUpperCase(), JSON.stringify(brief), new Date().toISOString(), JSON.stringify(sources));
}

export function getResearchBrief(ticker: string): { brief: object; generated_at: string; sources: string[] } | null {
    const database = getDb();
    const row = database.prepare('SELECT brief, generated_at, sources FROM research_briefs WHERE ticker = ?').get(ticker.toUpperCase()) as
        | { brief: string; generated_at: string; sources: string } | undefined;
    if (!row) return null;
    return {
        brief: JSON.parse(row.brief),
        generated_at: row.generated_at,
        sources: JSON.parse(row.sources),
    };
}

// ============================================================
// Audit Logging
// ============================================================

export interface AuditEntry {
    user_id: string;
    username: string;
    tier: string;
    tool_name: string;
    args?: Record<string, unknown>;
    sources_used?: string[];
    cache_hit?: boolean;
    latency_ms?: number;
    status?: 'success' | 'error';
    error_message?: string;
}

export function logAudit(entry: AuditEntry): void {
    try {
        const database = getDb();
        database.prepare(`
      INSERT INTO audit_log (timestamp, user_id, username, tier, tool_name, args, sources_used, cache_hit, latency_ms, status, error_message)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
            new Date().toISOString(),
            entry.user_id,
            entry.username,
            entry.tier,
            entry.tool_name,
            entry.args ? JSON.stringify(entry.args) : null,
            entry.sources_used ? JSON.stringify(entry.sources_used) : null,
            entry.cache_hit ? 1 : 0,
            entry.latency_ms || null,
            entry.status || 'success',
            entry.error_message || null,
        );
    } catch (error) {
        console.warn('[Audit] Logging error:', error);
    }
}

export function getAuditHistory(userId: string, limit: number = 50): unknown[] {
    try {
        const database = getDb();
        return database.prepare(
            'SELECT * FROM audit_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?'
        ).all(userId, limit);
    } catch {
        return [];
    }
}

// Initialize DB on import
try {
    getDb();
} catch (e) {
    console.warn('[Cache] DB init deferred:', e);
}
