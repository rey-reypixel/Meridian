# Meridian — Project Status & Handoff Summary

*Written 2026-08-09 as a handoff reference for continuing work in a new conversation.*

## What Meridian is

An LLM cost optimization engine that sits between an application and Claude's
API, automatically reducing spend via four mechanisms: semantic context
truncation, intelligent model routing, semantic response caching, and batch
processing. Built as a portfolio/learning project, not a company product —
GitHub repo: **https://github.com/rey-reypixel/Meridian**

## Tech stack (all actually implemented and tested, nothing aspirational)

- **Backend:** FastAPI (Python 3.10, async), Uvicorn
- **Database:** PostgreSQL, via SQLAlchemy ORM + Alembic migrations
- **Cache/queue:** Redis (embeddings, response cache, batch state), Celery
  (background batch-processing worker, separate container from the API)
- **ML:** FastEmbed (`BAAI/bge-small-en-v1.5`, local/on-device, no external
  API calls) for embeddings — used by context truncation, task
  classification, and semantic response caching
- **LLM:** Anthropic Claude API (`anthropic` Python SDK, both sync and
  `AsyncAnthropic` for streaming)
- **Auth:** Google OAuth 2.0 + JWT (`python-jose`), currently using
  placeholder credentials — real setup in progress (see "In progress" below)
- **Testing:** pytest, `fakeredis`, `unittest.mock` — 78 tests, all passing
- **Load testing:** Locust
- **Containerization:** Docker + Docker Compose (5 services: backend,
  worker, postgres, redis, dashboard)
- **Deployment:** AWS EC2 (Ubuntu 26.04 LTS, `t3.micro`, `ap-south-1`
  Mumbai), Caddy (reverse proxy + automatic HTTPS via Let's Encrypt),
  DuckDNS (free dynamic DNS, since no paid domain was purchased). Chose
  AWS specifically over Railway/Vercel: Vercel doesn't fit this backend's
  shape at all (needs persistent processes — Postgres, Redis, and
  especially a Celery worker that must stay alive continuously; doesn't
  work in a serverless model no matter how it's configured). Railway
  would've been simpler to set up, but its real free tier in 2026 is
  ~$1/month non-rollover credit — nowhere near enough for a 4-service
  stack (Postgres + Redis + worker + backend), would hit the $5/month
  Hobby plan within days. AWS free tier genuinely covers this stack's
  actual resource needs. There was also a deliberate resume-driven
  reason: the user was specifically weighing whether lacking real AWS
  experience was a gap worth closing, and decided actually deploying
  there (not just claiming it) was the right fix.
- **Frontend:** Not built yet by this conversation — being planned/built
  in a **separate chat/tool**. Intended workflow: prototype the visual
  design in **Claude Design** (Anthropic Labs product, launched April
  2026 — describe/refine a design via chat, it can read an existing
  codebase to match a design system) using the brief below, then use its
  "handoff to code" feature to pass the finished design to a Claude Code
  session, which turns it into real files in `dashboard/`. Tech stack:
  React + Vite + TypeScript + Tailwind, Recharts for charts. Full design
  brief below.

## What was built, roughly in order

**Phase 1 — Foundation:** FastAPI app, Google OAuth + JWT auth scaffold,
SQLite→(later Postgres) models, cost predictor (tiktoken-based token
counting + hardcoded Claude pricing table), basic `/api/messages` endpoint
with no optimization yet, Docker setup.

**Phase 2 — Real infra + real optimizations:** Swapped SQLite for
PostgreSQL with Alembic migrations (verified zero schema drift). Swapped
in-memory caching for Redis. Built a real Celery+Redis batch queue
(previously the batch manager was imported but never actually called — a
Phase 1 bug). Implemented real FastEmbed-based semantic context truncation
(previously just "keep last N messages"). All verified live against real
Postgres/Redis/Celery using a `MOCK_ANTHROPIC=true` dev toggle (skips the
real paid Anthropic call, returns a deterministic fake completion, but
still computes real token counts via tiktoken — so cost/routing/truncation
math stays honest while testing at $0).

**Phase 2.5 — Fixed 3 previously-dead request parameters:** `cost_limit`
(accepted but never enforced), `optimize_for` (accepted but never
branched any behavior), `quality_threshold` per-request override
(accepted but ignored, always used the global default). Also found and
fixed: model routing was accidentally gated behind context truncation
having fired first (a real logic bug), and the quality threshold default
was on the wrong numeric scale vs. the internal 0-10 quality score table,
which made routing always pick the cheapest model regardless of task
complexity.

**Phase 2.6 — Four free high-impact additions** (chosen specifically
because they're fully buildable AND verifiable at $0, unlike e.g. real
Batch API integration or LLM-as-judge quality eval, which need paid API
calls):
1. **Embedding-based task classification** — replaced keyword matching
   with cosine-similarity comparison against example prompts per task
   type. Live-verified it correctly handles paraphrases, though it also
   revealed a real limitation: single strong keyword associations (e.g.
   "sort") can pull classification toward the wrong category with a
   small example set.
2. **Semantic response caching** — Redis-backed, near-duplicate prompts
   skip the LLM entirely. Similarity threshold deliberately conservative
   (0.97) since a wrong cache hit is worse than a miss. Live-verified: a
   real paraphrase ("world" vs "Earth") scored 0.9663 — genuinely close
   but correctly below threshold, confirming the mechanism works as
   designed rather than being a rubber stamp.
3. **Streaming responses** (SSE) — new `POST /api/messages/stream`
   endpoint, real `AsyncAnthropic` streaming client + a mock-mode
   equivalent. Uses a self-contained DB session (not `Depends(get_db)`)
   for the deferred post-stream write, specifically to avoid relying on
   FastAPI's dependency-cleanup timing for `StreamingResponse`.
4. **Real load testing** — Locust, run against the mock-mode live stack
   (correctly isolates Meridian's own pipeline overhead from Claude's
   response time). Real results: 692 requests, 0 failures, p50 17ms /
   p95 42ms / p99 86ms aggregate.

**Backend API additions (most recent before deployment):** `GET
/api/requests` (paginated list endpoint with model/date filters —
previously only single-request lookup by ID existed), aggregated
`total_tokens_processed`/`avg_latency_ms` into the dashboard summary
endpoint. Found and fixed 2 more real bugs during this: a `conftest.py`
test-session bug that broke any test making 2+ sequential authenticated
requests, and a SQLite timestamp-precision issue that made "most recent
first" ordering non-deterministic (fixed with a portable Python-side
`default=` alongside the existing `server_default=func.now()`).

**README cleanup:** Fixed a fabricated Quick Start (still not fully
fixed — see "Not done" below), replaced fake AWS/Railway deployment
instructions and a fabricated performance benchmarks table with real
data, fixed dead support links/credits/a stale dated roadmap.

**Live AWS deployment (this session, in detail):**
- EC2 instance "Meridian" (`i-08602a8a8909b7179`), Ubuntu 26.04 LTS,
  `t3.micro`, `ap-south-1` (Mumbai), free-tier eligible
- Hit and resolved a real disk-space-during-build failure (8GB root
  volume too small for two ~1GB Python images with FastEmbed/onnxruntime
  + Locust/gevent deps) — resized the EBS volume to 20GB
- Hit and resolved an SSH lockout after editing the security group to add
  the Caddy ports — editing inbound rules had invalidated/reset the SSH
  rule's source IP, not the new rules themselves. Fixed by re-selecting
  "My IP" fresh on the SSH rule. Full troubleshooting narrative in
  `bugs_debugs.txt`.
- Elastic IP allocated and associated: **13.234.145.240** (permanent,
  won't change on instance restart) — first association attempt appeared
  to succeed in the instance summary UI but hadn't actually happened
  (Elastic IPs list showed it unassociated); had to redo it properly via
  Actions → Associate Elastic IP address
- Free DNS via DuckDNS (no student verification needed, unlike GitHub
  Student Pack which the user couldn't use): **meridianpixelated.duckdns.org**
  pointed at the Elastic IP
- Caddy installed and configured as a reverse proxy in front of the
  backend (`localhost:8000`) — automatically obtained a real Let's
  Encrypt HTTPS certificate for the DuckDNS domain, verified working
  (no cert warnings, clean HTTPS response)
- Full stack running via `docker compose up -d postgres redis backend
  worker` (dashboard service skipped — no Dockerfile exists yet since
  frontend isn't built)
- Alembic migrations run against the live Postgres
- Verified end-to-end: `https://meridianpixelated.duckdns.org/health`
  returns the healthy response over real HTTPS

## In progress (mid-task when this conversation handed off)

**Setting up real Google OAuth**, since it requires HTTPS + a real domain
(Google rejects bare-IP HTTP redirect URIs) — which is *why* the whole
domain/HTTPS chain above happened. Was in the middle of:
1. Google Cloud Console: create project → OAuth consent screen (External
   user type, add self as a test user to stay in "Testing" mode and skip
   Google's verification review) → Credentials → OAuth Client ID (Web
   application) → redirect URI `https://meridianpixelated.duckdns.org/auth/callback`
2. Once Client ID + Secret exist: update `.env` on the EC2 server
   (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OAUTH_REDIRECT_URI`),
   restart the backend container, test the real login flow via
   `https://meridianpixelated.duckdns.org/auth/login`

The backend code for this (`app/oauth/google.py`, `app/api/auth.py`) has
existed since Phase 1 and was already tested via mocks — this remaining
work is purely credentials + config, not new code.

## Frontend — being built in a separate chat: full tech stack + design brief

Not started by this conversation. `dashboard/src` exists but is an empty
shell (Phase 1 scaffold, never touched — git doesn't track empty
directories, so it isn't even in the GitHub repo yet). Recorded here in
full so a fresh chat has everything needed without re-pasting the
original brief.

### Tools / libraries

- **React 18** + **Vite** + **TypeScript**
- **Tailwind CSS** — configured with the project's *own* custom design
  tokens (colors/spacing/radius below), not Tailwind's defaults
- **Recharts** for charts (thin-line, monospace-label styling is
  achievable without fighting the library's defaults)
- **Lucide** icons (small, technical, monochrome by default; color only
  when it communicates meaning — explicitly not a mixed icon set)
- Fonts: **IBM Plex Mono** / Space Mono / Geist Mono for headings and
  instrumentation (uppercase, slight letter-spacing); **Inter** / Geist /
  IBM Plex Sans for body/UI text
- Docker: `dashboard` service already stubbed in `docker-compose.yml`
  (Vite dev server, host port 3000 → container 5173, `VITE_API_URL`
  pointed at the backend) but has no Dockerfile yet — needs one once the
  frontend project exists

### Visual direction (the core constraint — read this before styling anything)

Explicitly **not** a generic AI-SaaS dashboard — no purple-gradient/
glassmorphism/oversized-rounded-card aesthetic, no floating glass blobs,
no giant AI-brain imagery, no excessive glow/shadow/animation. The
target is "dark futuristic infrastructure console × financial analytics
× cybersecurity/developer tooling × premium command center" — should
read as serious infrastructure software, not an AI startup landing page.
Corner radius restrained (4px small UI, 6px cards, 6-8px max for large
panels — not 16-24px "friendly SaaS" rounding). 4px-based spacing scale
(4/8/12/16/20/24/32/40/48).

### Color system

```
App background:      #030608
Primary surface:      #080C10
Secondary surface:    #0C1116
Elevated surface:     #10161C
Border:               #29313A
Strong border:        #46515C
Primary text:         #F2F4F5
Secondary text:       #9BA5AE
Muted text:           #626C75

Blue    #3EA6FF  — primary actions, links, Haiku, optimized cost
Green   #8BE34F  — savings, successful optimizations, system health
Purple  #9B6CFF  — semantic cache, Sonnet, secondary analytics
Gold    #FFD23F  — quality, warnings, batch processing
White/Silver #FFFFFF / #B8C0C7 — actual spend, Opus, major chart lines,
                                  treated as a core identity color, not
                                  just body text
```

### Layout

Desktop-first, responsive down to tablet (condensed sidebar, collapsed
secondary panels) and mobile (sidebar becomes a drawer, tables become
horizontally scrollable or collapse into stacked cards — never destroy
information hierarchy just to fit). Fixed left sidebar (~210-230px) +
main content area. Sidebar nav: Overview, Optimizations (expandable:
Routing/Context/Cache/Batching), Requests, Analytics (expandable:
Cost/Models/Quality), Settings.

### Page structure

- **Overview** — KPI row (total spend/saved/savings %/avg quality, each
  with a sparkline), main spend-vs-optimized-cost chart, model mix donut,
  "Optimization Impact" breakdown card, recent requests table, quality-
  over-time chart, persistent bottom status bar (cache hit rate, batch
  efficiency, context reduction, system status)
- **Requests** — dense filterable/sortable/paginated table; row click →
  **Request Detail** (designed as a step-by-step "forensic trace" of the
  optimization pipeline: classification → context analysis → truncation →
  model evaluation → routing → cache check → final cost/quality result)
- **Optimizations** — overview of all 4 mechanisms, then one dedicated
  page each (Routing, Context, Cache, Batching) with mechanism-specific
  metrics and recent activity
- **Analytics** — Cost (deep spend/savings breakdown + filters), Models
  (Haiku/Sonnet/Opus comparison table), Quality (cost-vs-quality tradeoff
  charts)
- **Settings** — account, model routing policy, quality thresholds,
  context rules, cache config, batch config — framed as an engineering
  control panel, not a typical SaaS settings page

### Component library to build (reusable, token-driven — no per-page hardcoded styles)

Button, IconButton, Card, Panel, MetricCard, Badge, ModelBadge,
StatusIndicator, ChartContainer, DataTable, Tooltip, Modal, Drawer, Tabs,
FilterBar, SearchInput, Timeline, EmptyState, LoadingState, ErrorState.

### Hard rule: reflect the real backend, don't invent data

Cross-reference the "FRONTEND/UX GAP ANALYSIS" section in
`bugs_debugs.txt` (dated 2026-08-09) before wiring any page — it maps
exactly which brief sections have real backend data available today
(Overview KPIs, model mix, requests table via the new `GET
/api/requests`) versus which need mock data clearly marked as such
(sparklines/time-series, per-mechanism $ savings attribution, cache/
batch stats, request-detail forensic trace, task-classification
confidence %). Two build tracks: Track A wires to real data now, Track B
scaffolds with marked mock data until the backend gaps close.

## Frontend (being built in a separate chat)

`dashboard/src` is currently an empty directory shell — no `package.json`,
no Dockerfile, nothing installed. This is a from-scratch build, not a
redesign. The user gave a very detailed, explicit design brief before any
code was written — summarized here so the intent isn't lost.

### Design direction

Explicitly **not** a generic AI-SaaS dashboard — no purple-gradient/
glassmorphism/oversized-rounded-card aesthetic. The brief describes the
target as:

> "DARK FUTURISTIC INFRASTRUCTURE CONSOLE × FINANCIAL ANALYTICS ×
> CYBERSECURITY/DEVELOPER TOOLING × PREMIUM COMMAND CENTER" — should feel
> like serious infrastructure software engineers use to control LLM
> spending, not an AI startup landing page.

Visual hierarchy, in priority order: **1)** how much was saved, **2)** how
(which optimization mechanism), **3)** whether quality held up, **4)**
raw request/infra data.

### Color system (exact values from the brief)

- Backgrounds: `#030608` (app), `#080C10` (primary surface), `#0C1116`
  (secondary), `#10161C` (elevated)
- Borders: `#29313A` (default), `#46515C` (strong)
- Text: `#F2F4F5` (primary), `#9BA5AE` (secondary), `#626C75` (muted)
- **Blue `#3EA6FF`** — primary actions, optimized cost, Haiku
- **Green `#8BE34F`** — savings, successful optimizations, system health
- **Purple `#9B6CFF`** — semantic cache, Sonnet
- **Gold `#FFD23F`** — quality, warnings, batch processing
- **White/Silver `#FFFFFF` / `#B8C0C7`** — actual spend, Opus, major chart
  lines — treated as a core brand color, not just body text

### Typography

Monospace (IBM Plex Mono / Space Mono / Geist Mono) for headings and all
data/numbers, uppercase with letter-spacing for section titles. Clean
sans-serif (Inter / Geist / IBM Plex Sans) for body text. Corner radius
kept small throughout (4-8px max) — explicitly not "friendly SaaS" 16-24px
rounding.

### Layout

Fixed left sidebar (~210-230px) + main content. Sidebar nav: Overview,
Optimizations (expandable: Routing / Context / Cache / Batching),
Requests, Analytics (expandable: Cost / Models / Quality), Settings.

### Planned pages

- **Overview** — KPI row (spend/saved/savings-rate/quality, each with a
  sparkline), spend-vs-optimized-cost chart, model mix donut, "Optimization
  Impact" breakdown by mechanism, recent requests table, quality-over-time
  chart, bottom status bar
- **Request Detail** — a "forensic trace" view of one request's journey
  through classification → truncation → routing → cache check → response
  → cost result. Called out in the brief as one of the most important pages.
- **Optimizations** — overview page for all 4 mechanisms, plus one
  dedicated page per mechanism (Routing, Context, Cache, Batching)
- **Analytics** — Cost, Models (comparison across Haiku/Sonnet/Opus),
  Quality (cost-vs-quality tradeoff visualization)
- **Settings** — account, model routing policy, quality thresholds,
  context rules, cache/batch config

Reusable component set the brief calls for: Button, Card, Panel,
MetricCard, Badge, ModelBadge, DataTable, ChartContainer, Tabs, FilterBar,
Timeline, EmptyState/LoadingState/ErrorState, centralized design tokens
(no per-page hardcoded styles).

### The critical constraint: backend data reality vs. the brief

Before any frontend code was written, the actual backend response shapes
were audited against what the brief assumes. Full detail is in
`bugs_debugs.txt` under "FRONTEND/UX GAP ANALYSIS," but the short version:

**Maps cleanly to real data today:** Overview KPIs (no sparklines yet),
Model Mix donut, Requests table (via the `GET /api/requests` endpoint
added specifically for this), basic Request Detail.

**Needs mock data or new backend work:** time-series/sparklines (summary
endpoint is all-time-totals only, no date filtering exists), request
preview text (prompt text is never stored in the DB at all — a real
privacy trade-off, not just a missing column), the "Optimization Impact"
$-by-mechanism breakdown (not attributable with the current data model —
savings is one combined number per request), the Request Detail
"forensic trace" (only final outcomes are stored, not intermediate
pipeline steps), task classification confidence %, Cache/Batching stats
(internal Redis state exists, zero API surface), per-model token/latency
in the Models analytics page.

**Decision made:** build in two tracks — wire directly to what's real
now, scaffold the rest with clearly-marked mock data rather than block
on closing every backend gap first.

## Not done yet (known, not forgotten)

- Frontend/dashboard (separate chat)
- README Quick Start still describes a fictional pip-installable SDK
  (`pip install meridian-llm`) that doesn't exist — the real interface is
  a REST API behind OAuth. Never fixed.
- README API reference section has wrong endpoint paths (shows `/api/v1/...`)
- README Security section still lists fabricated claims (SOC2, rate
  limiting, etc.)
- Never once called the real Anthropic API — `MOCK_ANTHROPIC=true` the
  entire project. No genuine end-to-end Claude completion has happened yet.
- Real Anthropic Batch API integration — current batching groups requests
  but doesn't get the actual 50% batch-pricing discount (explicitly
  flagged, deferred)
- Quality scores (`ModelRouter.QUALITY_SCORES`) are hand-set, not measured
  against real model outputs (would need LLM-as-judge eval, needs paid
  API calls)
- Multi-provider support (OpenAI etc.) — not built
- Dashboard data gaps documented in detail in `bugs_debugs.txt`: no
  time-series/sparkline data, no per-optimization-mechanism $ savings
  attribution (not just missing — not attributable with the current data
  model), no cache/batch stats API surface, no per-model token/latency
  breakdown
- `docs/architecture.md`, `strategies.md`, `monitoring.md`,
  `case-studies.md`, `faq.md`, `CONTRIBUTING.md` — all linked from the
  README, none exist
- No CI/CD (GitHub Actions)
- `dashboard` service in `docker-compose.yml` has no Dockerfile yet

## Where everything lives

- Full bug/decision log with dates and reasoning: `bugs_debugs.txt` (very
  detailed — read this for the "why" behind any design choice)
- Build plan with phase-by-phase detail:
  `C:\Users\rey27\.claude\plans\kind-drifting-hippo.md`
- Backend code: `backend/app/` (services/, api/, db/)
- Tests: `backend/tests/`
- Load test: `backend/loadtest/`
- Live server SSH: `ssh -i <path-to-meridian.pem> ubuntu@13.234.145.240`
  (key file is on the user's machine, in Downloads)

## User preferences worth knowing

- **Never add a `Co-Authored-By: Claude` trailer to git commits** — the
  user explicitly asked for this after seeing "claude" show up as a
  separate GitHub contributor. Commits should be attributed to them alone.
- User is a 4th-year college student, building this partly as a resume/
  portfolio piece — appreciates honest gap analysis over inflated claims
  ("does this make my resume less sexy" was answered: no, defensible
  trade-off reasoning is more impressive than fake completeness).
- Prefers real, live-verified results over claims — this whole project has
  a pattern of "build it, then actually prove it works via live HTTP
  calls / real load tests / real deployment," not just unit tests in
  isolation.
