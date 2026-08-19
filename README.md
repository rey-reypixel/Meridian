# Meridian — Intelligent LLM Cost Optimization Engine

**A self-hosted API that sits in front of Claude and automatically cuts cost per request** — via context truncation, model routing, semantic response caching, and batch processing.

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)

**Live:** [meridianpixelated.duckdns.org](https://meridianpixelated.duckdns.org) — real backend + real dashboard, deployed on AWS EC2 behind HTTPS. Google login isn't wired up with real credentials yet (see [Deployment](#-deployment)), so there's nothing to sign in with yet — but every endpoint and page renders honestly against whatever data actually exists (mostly none, right now).

---

## 🎯 The Problem

Teams calling LLM APIs directly tend to overspend in a few predictable ways:

- **Redundant context:** sending an entire conversation history when only the last few messages are relevant
- **Wrong model for the task:** using a frontier model for something a cheaper one handles fine
- **No batching:** processing requests one at a time instead of grouping them
- **No visibility:** not knowing what a request actually cost until the bill arrives

Meridian is a small FastAPI service that sits between your app and the Claude API, and applies four concrete optimizations to every request before it goes out.

---

## ✨ How It Works

```
Your App → POST /api/messages → Meridian → Claude API
                                  (context truncation, model routing,
                                   semantic cache, batching)
```

Every request through `/api/messages` runs through this pipeline:

#### 1. Context Truncation
Uses [FastEmbed](https://github.com/qdrant/fastembed) (`BAAI/bge-small-en-v1.5`) to embed each message in a conversation and drop ones below a relevance threshold, always preserving the most recent N messages. Skipped automatically when `optimize_for="speed"` (computing embeddings adds latency you may not want).

#### 2. Model Routing
Classifies the task type from the prompt, then checks whether a cheaper model in the Claude lineup (Haiku → Sonnet → Opus) can still clear the request's `quality_threshold` for that task type. Routes down when it can; never routes below what you asked for when `optimize_for="quality"`.

#### 3. Semantic Response Cache
Before calling Claude, checks whether a near-duplicate prompt has already been answered (cosine similarity against cached embeddings). Only consulted when `temperature` is low enough that reusing a prior response is defensible — reusing an old response instead of sampling a new one isn't obviously correct for highly stochastic requests, so it's skipped above `response_cache_max_temperature`.

#### 4. Batch Processing
When `batch=true`, groups the request into a Celery-managed queue instead of calling Claude immediately, processed with other similar requests.

#### 5. Cost Prediction & Budgeting
`GET /api/estimate` returns a cost estimate (via `tiktoken`) before you call anything. `POST /api/messages` accepts an optional `cost_limit` and returns `402 Payment Required` instead of spending anything if the optimized estimate exceeds it.

Every request's `optimizations_applied`, real cost before/after, and quality score are persisted and visible in [the dashboard](#-dashboard) or via `GET /api/requests`.

---

## 📊 Verified Results

Real output from this codebase — **not production client data** (there isn't any yet; see [Deployment](#-deployment)). This is a 459-request batch run locally against real token counts and real Anthropic pricing tables, with `MOCK_ANTHROPIC=true` so no actual Claude API spend was involved and the routing/cost math could be verified deterministically.

| Metric | Value |
|--------|-------|
| Requests processed | 459 |
| Total estimated cost (unoptimized) | $1.36 |
| Total estimated cost (optimized) | $0.17 |
| Savings | $1.20 (87.9%) |
| Avg quality score | 8.5 / 10 |
| Model mix | 458 → Sonnet, 1 → Haiku |

You can reproduce this yourself: run `docker compose up -d` with `MOCK_ANTHROPIC=true` (the default in `.env.example`), send requests through `/api/messages`, and check `GET /api/dashboard/summary` — every number there is computed live from whatever's actually in Postgres, never hardcoded.

---

## 🚀 Getting Started

Meridian is a Docker Compose stack: FastAPI backend, Celery worker, Postgres, Redis, and a React dashboard. There is no separate SDK to install — you call the API directly.

```bash
git clone https://github.com/rey-reypixel/Meridian.git
cd Meridian
cp backend/.env.example backend/.env
# fill in ANTHROPIC_API_KEY, or leave MOCK_ANTHROPIC=true to run everything
# for $0 with real token counts and fake completion text
docker compose up -d
```

- Backend: `http://localhost:8000` (interactive docs at `/docs`)
- Dashboard: `http://localhost:3000`

Real login requires a Google OAuth Client ID/Secret in `backend/.env` (see `.env.example`) — without one, `/auth/login` will return a URL that Google will reject.

### Calling the API directly

```bash
curl -X POST http://localhost:8000/api/messages \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-opus",
    "messages": [{"role": "user", "content": "Classify this support ticket: ..."}],
    "optimize_for": "cost",
    "quality_threshold": 8.0
  }'
```

```json
{
  "content": { "content": "...", "role": "assistant" },
  "metadata": {
    "cost": 0.000306,
    "original_cost": 0.003855,
    "savings": 0.003549,
    "model_used": "claude-sonnet",
    "model_original": "claude-opus",
    "optimizations_applied": ["model_routing"],
    "quality_score": 8.5,
    "latency_ms": 8
  }
}
```

---

## 🖥️ Dashboard

React 18 + TypeScript + Tailwind, talking to the real API — no hardcoded metrics anywhere. Currently covers:

- **Overview** — spend/savings KPIs, model mix, recent requests
- **Requests** — paginated, filterable (by model, date range) table of every processed request
- **Request Detail** — full breakdown of a single request: routing decision, cost before/after, which optimizations fired

Optimizations/Analytics/Settings pages exist in the nav but aren't built yet (they'd need backend data — like time-series history and per-mechanism $ attribution — that doesn't exist yet either). They render an honest "not built yet" placeholder rather than fake content.

---

## 🏗️ Architecture

```
┌──────────────┐      ┌──────────────────────────────────────────┐
│  Dashboard   │      │              FastAPI Backend              │
│ React+Vite   │◄────►│                                            │
└──────────────┘      │  /auth/*   Google OAuth + JWT              │
                       │  /api/messages(/stream)                   │
                       │      → cost estimate (tiktoken)            │
                       │      → context truncation (FastEmbed)      │
                       │      → model router (task classification)  │
                       │      → semantic cache (embedding similarity)│
                       │      → batch queue (Celery) or direct call  │
                       │  /api/dashboard/*, /api/requests            │
                       └──────────┬─────────────────┬───────────────┘
                                  │                 │
                          ┌───────▼──────┐   ┌──────▼──────┐
                          │  PostgreSQL  │   │    Redis    │
                          │ users, requests│  │Celery broker,│
                          │ (real records) │  │response cache│
                          └────────────────┘  └──────┬──────┘
                                                       │
                                                ┌──────▼──────┐
                                                │Celery Worker │
                                                │(batch queue) │
                                                └──────────────┘
                                                       │
                                                ┌──────▼──────┐
                                                │  Claude API  │
                                                └──────────────┘
```

---

## 📋 API Reference

Full interactive reference is auto-generated at `/docs` (Swagger UI) once the backend is running. Summary:

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET`  | `/auth/login` | — | Returns the Google OAuth consent URL |
| `GET`  | `/auth/google/callback` | — | Google's OAuth redirect target (not user-facing) |
| `GET`  | `/auth/me` | JWT | Resolve the current user from a token |
| `POST` | `/auth/logout` | — | No-op (JWTs are stateless; client discards the token) |
| `POST` | `/api/messages` | JWT | Send a message through the full optimization pipeline |
| `POST` | `/api/messages/stream` | JWT | Same, streamed via SSE |
| `GET`  | `/api/estimate` | JWT | Cost estimate for a prompt, no request actually sent |
| `GET`  | `/api/dashboard/summary` | JWT | Aggregate spend/savings/quality for the current user |
| `GET`  | `/api/dashboard/models` | JWT | Cost breakdown by model |
| `GET`  | `/api/requests` | JWT | Paginated request history (`page`, `page_size`, `model`, `start_date`, `end_date`) |
| `GET`  | `/api/requests/{id}` | JWT | Full detail for one request |
| `GET`  | `/health` | — | Health check |

`POST /api/messages` request body:

```python
{
  "model": str,                              # "claude-opus" | "claude-sonnet" | "claude-haiku"
  "messages": [{"role": str, "content": str}],
  "max_tokens": int = 1024,
  "temperature": float = 0.7,
  "optimize_for": "cost" | "speed" | "quality" = "cost",
  "cost_limit": float | None = None,         # 402 if the optimized estimate exceeds this
  "batch": bool = False,
  "quality_threshold": float = 8.5           # 0-10 scale
}
```

---

## ⚙️ Configuration

All configuration is environment variables, read from `backend/.env` (see `backend/.env.example` for the full list with defaults):

```bash
# Optimization toggles
CONTEXT_TRUNCATION_ENABLED=true
MODEL_ROUTING_ENABLED=true
BATCH_PROCESSING_ENABLED=true
QUALITY_THRESHOLD=8.5
CONTEXT_RELEVANCE_THRESHOLD=0.7
PRESERVE_RECENT_MESSAGES=5

# Dev/test only — skip the real Anthropic call, return a deterministic fake
# completion. Real token counts (and therefore real cost/routing math) are
# still computed for real via tiktoken. Never set true in production.
MOCK_ANTHROPIC=false
```

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -q                    # 74 tests, real Postgres + FastEmbed + tiktoken
pytest tests/ -q --cov=app          # with coverage

# Load test (isolates Meridian's own pipeline overhead — Anthropic calls
# mocked, so this measures routing/truncation/DB cost, not Claude's latency)
python loadtest/setup_test_user.py   # prints a JWT
export LOCUST_JWT=<token>
locust -f loadtest/locustfile.py --host http://localhost:8000 \
  --headless -u 20 -r 5 -t 60s --csv=loadtest_results
```

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend API** | FastAPI (Python 3.10+), async |
| **Auth** | Google OAuth 2.0 + JWT (`python-jose`) |
| **Embeddings** | FastEmbed (`BAAI/bge-small-en-v1.5`), local, no external embedding API |
| **Token Counting** | tiktoken |
| **Database** | PostgreSQL + SQLAlchemy + Alembic |
| **Cache / Broker** | Redis |
| **Task Queue** | Celery (batch processing) |
| **Load Testing** | Locust |
| **Containerization** | Docker + Docker Compose |
| **Dashboard** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts |
| **Live Reverse Proxy** | Caddy (automatic HTTPS via Let's Encrypt) |

---

## 📦 Deployment

### Docker Compose (what's actually tested)

Five services: `backend` (FastAPI), `worker` (Celery), `postgres`, `redis`, `dashboard`.

```bash
docker compose up -d
```

### Live deployment

Running on an AWS EC2 instance (Ubuntu, the same Docker Compose stack as above) behind Caddy with automatic HTTPS (Let's Encrypt), on a fixed address (AWS Elastic IP + free DNS via DuckDNS — a paid domain wasn't part of this project's budget). The dashboard is served as a static production build by Caddy; `/api/*` and the real backend auth endpoints are reverse-proxied to the FastAPI container on the same origin.

**Live now:** [meridianpixelated.duckdns.org](https://meridianpixelated.duckdns.org)

**Not live yet:** real Google OAuth login. `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` on the live server are still placeholders — that's the user's own Google Cloud Console setup, not a code change. Until that's done, `/auth/login` on the live URL will redirect to Google and get rejected. Everything else (the dashboard shell, empty states, health check, real API responses) is genuinely live and working.

---

## 🔐 Security

- Auth is JWT-based (`python-jose`), issued after a real Google OAuth code exchange, verified on every protected endpoint via a FastAPI dependency
- Secrets (`SECRET_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_SECRET`) are read from environment variables, never committed — `.env` is gitignored, only `.env.example` (with placeholder values) is tracked
- CORS is restricted to explicitly configured origins (`CORS_ORIGINS`), not wildcarded
- No prompt or message text is ever persisted to the database — only cost/routing/quality metadata per request (see `RequestDetail` in the API reference)

This is a small project's auth setup, not an audited enterprise security posture — there's no rate limiting, no WAF, and no compliance certification, and none of that is claimed here.

---

## 📊 Performance Benchmarks

Real numbers from a local load test (Locust, 20 concurrent users, 45s, Anthropic
calls mocked so this isolates Meridian's own routing/truncation/caching/DB
overhead — not Claude's response time):

```
682 requests, 0 failures, ~15.4 req/s aggregate

Endpoint                        p50    p95    p99
─────────────────────────────────────────────────
POST /api/messages              18ms   52ms   86ms
POST /api/messages (long ctx)   20ms   35ms   76ms
GET  /api/estimate               5ms   21ms   68ms
GET  /api/dashboard/summary     11ms   73ms  200ms
─────────────────────────────────────────────────
Aggregate                       17ms   42ms   86ms
```

Cost-reduction percentages are documented above in [Verified Results](#-verified-results),
from real routing/cost math, not this latency benchmark. Quality-loss numbers
per task type aren't included anywhere: that requires a real evaluation
pipeline (comparing actual model outputs against a golden set), which doesn't
exist yet — see [Roadmap](#-roadmap).

---

## 🤝 Contributing

Contributions welcome — open an issue or a PR. Areas of particular interest:

- More LLM provider support (currently Claude only)
- ML-based quality evaluation (replacing the current hand-set per-task-type quality scores with measured data)
- Real Anthropic Batch API integration (current batching groups requests but doesn't yet get the batch-API discount)
- The Optimizations/Analytics/Settings dashboard pages (blocked on backend data that doesn't exist yet — see the Dashboard section above)

---

## 📝 License

[Business Source License 1.1](LICENSE) — source-available, **not** open source.

Free for non-production use: personal projects, evaluation, research, and teaching.
**Any production or commercial use requires a paid commercial license.**
On **2030-08-19** this version converts automatically to Apache License 2.0.

Commercial and production licensing: **mahashreyaa@gmail.com**

---

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/rey-reypixel/Meridian/issues)
- **Discussions:** [GitHub Discussions](https://github.com/rey-reypixel/Meridian/discussions)
- **Email:** mahashreyaa@gmail.com
- **Discord:** doodle_is_glitched

---

## 🙏 Acknowledgments

- FastEmbed / Qdrant team for lightweight local embeddings
- Anthropic for the Claude API
- FastAPI community for the framework

---

## 📈 Roadmap

Not on a committed timeline — directions being considered, not scheduled releases:

- Multi-provider support (OpenAI, others)
- ML-based quality evaluation (replacing the current hand-set quality scores with measured data)
- Real Anthropic Batch API integration (current batching groups requests but doesn't yet get the batch-API discount)
- Self-optimizing routing that learns from historical outcomes
- Optimizations/Analytics/Settings dashboard pages, once there's real backend data (time-series history, per-mechanism cost attribution) to back them

---

<div align="center">

**Built by [Mahashreyaa Pathak](https://github.com/rey-reypixel)**

</div>
