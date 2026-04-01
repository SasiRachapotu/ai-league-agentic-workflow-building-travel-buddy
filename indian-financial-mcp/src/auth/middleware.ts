// ============================================================
// JWT Auth Middleware — Validates Bearer tokens from Keycloak
// ============================================================

import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';
import { getTierFromRoles, TIER_SCOPES, type UserTier, type Scope } from './scopes.js';

export interface AuthenticatedUser {
    sub: string;
    preferred_username: string;
    email: string;
    tier: UserTier;
    scopes: Scope[];
    roles: string[];
    raw_token: string;
}

const KEYCLOAK_URL = process.env.KEYCLOAK_URL || 'http://localhost:8080';
const KEYCLOAK_REALM = process.env.KEYCLOAK_REALM || 'indian-financial';

const jwks = jwksClient({
    jwksUri: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/certs`,
    cache: true,
    cacheMaxAge: 600000, // 10 minutes
    rateLimit: true,
});

function getSigningKey(header: jwt.JwtHeader): Promise<string> {
    return new Promise((resolve, reject) => {
        jwks.getSigningKey(header.kid, (err, key) => {
            if (err) return reject(err);
            const signingKey = key?.getPublicKey();
            if (!signingKey) return reject(new Error('No signing key found'));
            resolve(signingKey);
        });
    });
}

export async function validateToken(authHeader: string | undefined): Promise<AuthenticatedUser | null> {
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return null;
    }

    const token = authHeader.slice(7);

    try {
        const decoded = jwt.decode(token, { complete: true });
        if (!decoded || !decoded.header) {
            return null;
        }

        const signingKey = await getSigningKey(decoded.header);

        const payload = jwt.verify(token, signingKey, {
            algorithms: ['RS256'],
            issuer: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}`,
        }) as jwt.JwtPayload;

        // Extract realm roles
        const realmRoles: string[] = payload.realm_access?.roles || [];

        // Determine tier from roles
        const tier = getTierFromRoles(realmRoles);
        const scopes = TIER_SCOPES[tier];

        return {
            sub: payload.sub || '',
            preferred_username: payload.preferred_username || '',
            email: payload.email || '',
            tier,
            scopes,
            roles: realmRoles,
            raw_token: token,
        };
    } catch (error) {
        console.error('[Auth] Token validation failed:', error);
        return null;
    }
}

export function getProtectedResourceMetadata() {
    return {
        resource: `http://localhost:${process.env.MCP_SERVER_PORT || 3000}`,
        authorization_servers: [`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}`],
        scopes_supported: [
            'market:read', 'fundamentals:read', 'technicals:read',
            'mf:read', 'news:read', 'filings:read', 'filings:deep',
            'macro:read', 'macro:historical', 'research:generate',
            'watchlist:read', 'watchlist:write',
        ],
        bearer_methods_supported: ['header'],
        resource_documentation: 'https://github.com/your-team/indian-financial-mcp',
    };
}

export function get401Response() {
    return {
        status: 401,
        headers: {
            'WWW-Authenticate': `Bearer realm="indian-financial", resource_metadata="http://localhost:${process.env.MCP_SERVER_PORT || 3000}/.well-known/oauth-protected-resource"`,
        },
        body: {
            error: 'unauthorized',
            error_description: 'Authentication required. Obtain a token from the authorization server.',
            resource_metadata: `http://localhost:${process.env.MCP_SERVER_PORT || 3000}/.well-known/oauth-protected-resource`,
        },
    };
}

export function get403Response(requiredScope: string) {
    return {
        status: 403,
        headers: {
            'WWW-Authenticate': `Bearer realm="indian-financial", error="insufficient_scope", scope="${requiredScope}"`,
        },
        body: {
            error: 'insufficient_scope',
            error_description: `This operation requires the '${requiredScope}' scope. Please upgrade your tier or request additional permissions.`,
            required_scope: requiredScope,
        },
    };
}
