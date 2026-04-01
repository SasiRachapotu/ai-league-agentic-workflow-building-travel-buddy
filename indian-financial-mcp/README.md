# 🇮🇳 Indian Financial Intelligence — MCP Server

> Production-grade MCP Server wrapping Indian financial APIs into a unified intelligence layer with OAuth 2.1 auth and cross-source reasoning.

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Docker & Docker Compose (for Keycloak + Redis)

### 1. Clone & Install
```bash
cd indian-financial-mcp
cp .env.example .env
# Edit .env with your API keys (see below)
npm install
```

### 2. Start Infrastructure
```bash
docker-compose up -d  # Starts Keycloak + Redis
```

### 3. Run MCP Server
```bash
npm run dev
```

Server starts at `http://localhost:3000`

### 4. Connect Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "indian-financial": {
      "url": "http://localhost:3000/mcp",
      "headers": {
        "Authorization": "Bearer <your_token>"
      }
    }
  }
}
```

---

## 🔑 API Keys (Free Tier)

| API | Sign Up | Free Limit |
|-----|---------|-----------|
| [Alpha Vantage](https://www.alphavantage.co/support/#api-key) | Email only | 25 req/day |
| [Finnhub](https://finnhub.io/register) | Email only | 60 req/min |
| [NewsAPI](https://newsapi.org/register) | Email only | 100 req/day |
| NSE India | No key needed | Rate limited |
| Yahoo Finance | No key needed | Unofficial |
| MFapi.in | No key needed | Unlimited |

---

## 🔐 Authentication

### OAuth 2.1 + PKCE via Keycloak

**Auth Server:** `http://localhost:8080` (Keycloak)  
**Realm:** `indian-financial`

### Test Users

| User | Password | Tier | Scopes |
|------|----------|------|--------|
| `free_user` | `password` | Free | market:read, mf:read, news:read, watchlist:* |
| `premium_user` | `password` | Premium | All Free + fundamentals, technicals, macro:read |
| `analyst` | `password` | Analyst | All scopes including research:generate, filings:deep |

### Get a Token
```bash
# Direct grant (for testing)
curl -X POST http://localhost:8080/realms/indian-financial/protocol/openid-connect/token \
  -d "client_id=mcp-client" \
  -d "username=analyst" \
  -d "password=password" \
  -d "grant_type=password"
```

### Protected Resource Metadata (RFC 9728)
```
GET /.well-known/oauth-protected-resource
```

---

## 🛠️ MCP Tools (21)

### Market Data (market:read)
| Tool | Description |
|------|-------------|
| `get_stock_quote` | Live quote: LTP, change, volume, market cap, 52W range |
| `get_price_history` | Historical OHLCV for any date range |
| `get_index_data` | Nifty 50, Sensex, Bank Nifty, sectoral indices |
| `get_top_gainers_losers` | Today's top movers on NSE |
| `get_technical_indicators` | SMA, EMA, RSI, MACD, Bollinger Bands *(Premium+)* |

### Fundamentals (fundamentals:read) — *Premium+*
| Tool | Description |
|------|-------------|
| `get_financial_statements` | Income, balance sheet, cash flow |
| `get_key_ratios` | P/E, P/B, ROE, debt/equity, dividend yield |
| `get_shareholding_pattern` | Promoter, FII, DII holdings over time |
| `get_quarterly_results` | Latest quarterly with YoY/QoQ comparison |

### Mutual Funds (mf:read)
| Tool | Description |
|------|-------------|
| `search_mutual_funds` | Search by name, AMC, or category |
| `get_fund_nav` | Latest + historical NAV |
| `compare_funds` | Side-by-side comparison (2-5 funds) |

### News & Sentiment (news:read)
| Tool | Description |
|------|-------------|
| `get_company_news` | Latest company-specific news |
| `get_news_sentiment` | Aggregated sentiment with confidence |
| `get_market_news` | Broad Indian market headlines |

### Macro & Regulatory (macro:read)
| Tool | Description |
|------|-------------|
| `get_rbi_rates` | Repo, reverse repo, CRR, SLR, history |
| `get_inflation_data` | CPI/WPI time series |
| `get_corporate_filings` | BSE/NSE filings list |

### Cross-Source Reasoning (research:generate) — *Analyst only* ⭐
| Tool | Description |
|------|-------------|
| `cross_reference_signals` | Multi-source Confidence Mesh with CONFIRMS/CONTRADICTS |
| `generate_research_brief` | Full brief from 5+ sources, saved to resource |
| `compare_companies` | Side-by-side across price, fundamentals, sentiment |

---

## 📊 MCP Resources

| URI | Description |
|-----|-------------|
| `market://overview` | Live Nifty/Sensex + top movers |
| `macro://snapshot` | Repo rate, CPI, GDP, forex, USD-INR |
| `system://health` | Upstream API status + quotas |

---

## 📝 MCP Prompts

| Prompt | Description | Tier |
|--------|-------------|------|
| `quick_analysis` | Quote + ratios + news for a ticker | Free+ |
| `deep_dive` | Comprehensive research with cross-source | Analyst |
| `sector_scan` | Compare top companies in a sector | Analyst |
| `morning_brief` | Daily market + macro + news summary | Premium+ |

---

## ⭐ Unique Features

### 1. Confidence Mesh
Cross-source tools quantify agreement across APIs:
```
Signal: "RELIANCE bullish"
  ├─ NSE Price:    +3.2%          → CONFIRMS  (0.85)
  ├─ BSE Filing:   Revenue beat   → CONFIRMS  (0.92)
  ├─ FII Holding:  +1.8% QoQ     → CONFIRMS  (0.78)
  ├─ News:         Negative       → CONTRADICTS (0.65)
  └─ RBI:          Rate hold      → NEUTRAL   (0.50)
  AGGREGATE: 0.74 — Moderately Bullish
```

### 2. Graceful Degradation
When an upstream API is down, returns cached/partial data with explicit status.

### 3. System Health Dashboard
`system://health` shows live API status and remaining quotas.

### 4. Smart Caching
3-tier (Memory → SQLite → API) with freshness metadata on every response.

---

## 🏗️ Architecture

```
Client → (Bearer Token) → Express → Auth Middleware → MCP Server
                                         ↓
                                   Scope Enforcer
                                   Rate Limiter
                                   Cache Manager
                                         ↓
                               Upstream API Gateway
                          (NSE, Yahoo, MFapi, Alpha Vantage,
                           Finnhub, NewsAPI, BSE, RBI)
```

---

## 📁 Project Structure

```
src/
├── index.ts              # Main server + all tool/resource/prompt registrations
├── auth/
│   ├── middleware.ts      # JWT validation, 401/403 responses
│   ├── scopes.ts          # Scope definitions, tier mapping
│   └── rate-limiter.ts    # Per-tier rate limiting
├── cache/
│   └── manager.ts         # 3-tier cache, watchlists, audit log, research briefs
├── upstream/
│   ├── client.ts          # Base client with circuit breaker
│   ├── yfinance.ts        # Yahoo Finance (quotes, history, financials)
│   ├── nse.ts             # NSE India (indices, movers, shareholding)
│   ├── mfapi.ts           # MFapi.in (mutual funds)
│   ├── alpha-vantage.ts   # Alpha Vantage (technicals)
│   ├── news.ts            # NewsAPI + Finnhub (news, sentiment)
│   └── macro.ts           # RBI data, BSE filings
└── tools/
    └── cross-source.ts    # Confidence Mesh cross-source reasoning
```
