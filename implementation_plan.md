# AutoBug AI — Implementation Plan

## Overview

AutoBug AI is an autonomous software engineering platform that autonomously detects bugs, performs root cause analysis, generates validated code fixes, and opens GitHub Pull Requests. This plan covers the full-stack implementation: a **Python/FastAPI** backend with **LangGraph** multi-agent orchestration, a **Next.js + Tailwind CSS** frontend, and all supporting infrastructure.

---

## User Review Required

> [!IMPORTANT]
> This is a very large system. The plan below proposes building a **production-quality MVP** covering the core workflow end-to-end. Some enterprise-grade features (enterprise SSO, Kubernetes autoscaling, self-learning repair engine) are deferred to Phase 2 per the PRD's "Out of Scope V1" list.

> [!WARNING]
> The plan requires the following API keys to be configured via `.env` before the system can function:
> - `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`)
> - `GITHUB_TOKEN` (PAT with `repo` + `pull_requests` scopes)
> - `QDRANT_URL` + `QDRANT_API_KEY` (or local Qdrant Docker)
> - `DATABASE_URL` (PostgreSQL)
> - `REDIS_URL`

> [!CAUTION]
> Bug reproduction runs untrusted code. The sandbox uses Docker with resource limits and network isolation. Ensure Docker is installed on the host before running the backend.

---

## Open Questions

> [!IMPORTANT]
> **Q1**: Should the initial build target a **local Docker Compose** setup (all services in one `docker-compose.yml`) or a cloud-native deployment (AWS/GCP)?
> → *Plan assumes Docker Compose for local dev + production-ready config files included.*

> [!IMPORTANT]
> **Q2**: Which LLM should be the **primary model**? The PRD lists GPT-5.5, Claude, and Gemini.
> → *Plan defaults to **Claude Sonnet** as primary (matching user's selected model) with OpenAI as fallback, configurable via env var.*

> [!IMPORTANT]
> **Q3**: Should the frontend have **real-time streaming** of agent progress (WebSocket / SSE)?
> → *Plan uses **Server-Sent Events (SSE)** for live agent step streaming to the UI.*

---

## Proposed Changes

### Project Structure

```
AutoBug/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/               # REST API routes
│   │   ├── agents/            # LangGraph agent definitions (17 agents)
│   │   ├── core/              # Config, DB, security
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic services
│   │   ├── rag/               # RAG / Qdrant integration
│   │   └── sandbox/           # Docker sandbox manager
│   ├── alembic/               # DB migrations
│   ├── tests/                 # Backend tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                  # Next.js 14 App Router frontend
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   ├── components/        # React components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # API client, utils
│   │   └── types/             # TypeScript types
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml         # Full stack orchestration
├── docker-compose.dev.yml     # Dev overrides
└── README.md
```

---

### Component 1: Project Scaffolding & Infrastructure

#### [NEW] `docker-compose.yml`
Full stack: PostgreSQL, Redis, Qdrant, backend API, Celery worker, frontend.

#### [NEW] `docker-compose.dev.yml`
Dev overrides with hot-reload volumes.

#### [NEW] `backend/.env.example`
All required environment variables documented with descriptions.

#### [NEW] `README.md`
Comprehensive setup guide with quickstart instructions.

---

### Component 2: Backend — Core & Config

#### [NEW] `backend/app/core/config.py`
Pydantic `Settings` class loading all env vars (LLM keys, DB URLs, GitHub token, etc.)

#### [NEW] `backend/app/core/database.py`
SQLAlchemy async engine + session factory.

#### [NEW] `backend/app/core/security.py`
JWT creation/validation, OAuth helpers.

#### [NEW] `backend/app/core/celery_app.py`
Celery app with Redis broker configuration.

---

### Component 3: Backend — Data Models

#### [NEW] `backend/app/models/`
SQLAlchemy ORM models:
- `Repository` — connected repos, index status, metadata
- `Issue` — bug reports with extracted fields (stack trace, severity, env)
- `Job` — async job tracking (status, steps, logs)
- `Patch` — generated patches with diff, validation results
- `PullRequest` — PR metadata, GitHub URL
- `User` — auth user with GitHub OAuth

---

### Component 4: Backend — RAG Engine

#### [NEW] `backend/app/rag/indexer.py`
- Clone repo via `gitpython`
- Language detection (file extensions + `pygments`)
- Chunk source files (recursive text splitter, 512 tokens, 50 overlap)
- Generate embeddings via `text-embedding-3-small`
- Upsert to Qdrant collection per repo

#### [NEW] `backend/app/rag/retriever.py`
- Semantic search: embed query → Qdrant similarity search
- Symbol search: AST-based grep + semantic re-ranking
- File search: fuzzy path matching
- Returns ranked code chunks with file paths & line numbers

#### [NEW] `backend/app/rag/ast_parser.py`
- `tree-sitter` based AST extraction for Python, JS, TS, Go, Java, Rust
- Extracts functions, classes, imports, call graphs

---

### Component 5: Backend — Sandbox Manager

#### [NEW] `backend/app/sandbox/manager.py`
- Create isolated Docker containers per job
- Resource limits: 2 CPU, 4GB RAM, 10min timeout
- Network isolation (`--network none` for untrusted code)
- Mount repo as read-only volume, write-layer for patches
- Execute shell commands, capture stdout/stderr
- Auto-cleanup on completion or timeout

---

### Component 6: Backend — AI Agents (LangGraph)

All 17 agents implemented as LangGraph nodes in a directed graph with shared state.

#### [NEW] `backend/app/agents/graph.py`
Master LangGraph `StateGraph` wiring all agents sequentially with conditional branching.

**Agent State Schema:**
```python
class AutoBugState(TypedDict):
    repo_url: str
    issue_text: str
    repo_path: str
    issue_structured: dict
    retrieved_chunks: list
    reproduction_result: dict
    root_cause: dict
    patch: dict
    validation_result: dict
    pr_url: str
    report: str
    error: str | None
```

#### [NEW] `backend/app/agents/` (one file per agent):

| File | Agent | Responsibility |
|------|-------|---------------|
| `repository_agent.py` | Repository Agent | Clone repo, detect languages, build file tree |
| `issue_agent.py` | Issue Agent | Parse issue text, extract error type, stack trace, severity |
| `planner_agent.py` | Planner Agent | Decompose bug into search queries and execution plan |
| `retrieval_agent.py` | Retrieval Agent | RAG search for relevant code chunks |
| `environment_agent.py` | Environment Agent | Detect runtime (Python/Node/etc.), create Docker env |
| `build_agent.py` | Build Agent | Install dependencies, compile project |
| `reproduction_agent.py` | Reproduction Agent | Execute steps to reproduce bug, capture failure |
| `localization_agent.py` | Localization Agent | Narrow down faulty file/function using AST + RAG |
| `root_cause_agent.py` | Root Cause Agent | LLM analysis of evidence → root cause + confidence |
| `patch_agent.py` | Patch Agent | Generate minimal unified diff patch |
| `static_analysis_agent.py` | Static Analysis Agent | Run ruff/eslint/mypy on patch |
| `test_generator_agent.py` | Test Generator Agent | Write regression + unit tests for the bug |
| `test_runner_agent.py` | Test Runner Agent | Execute tests in sandbox, capture results |
| `reviewer_agent.py` | Reviewer Agent | LLM code review: quality, security, style |
| `git_agent.py` | Git Agent | Create branch, commit patch + tests |
| `pr_agent.py` | PR Agent | Push branch, open GitHub PR via API |
| `report_agent.py` | Report Agent | Generate comprehensive Markdown/HTML report |

---

### Component 7: Backend — API Layer

#### [NEW] `backend/app/api/v1/repositories.py`
`POST /repositories` — connect repo  
`GET /repositories/{id}` — status + metadata  
`DELETE /repositories/{id}` — remove + cleanup  
`POST /repositories/{id}/sync` — re-index

#### [NEW] `backend/app/api/v1/issues.py`
`POST /issues` — submit bug report → triggers async job  
`GET /issues/{id}` — status + results  
`GET /issues/{id}/stream` — SSE stream of agent progress

#### [NEW] `backend/app/api/v1/search.py`
`POST /search/semantic` — semantic code search  
`POST /search/symbol` — symbol lookup  
`GET /search/files` — file path search

#### [NEW] `backend/app/api/v1/patches.py`
`GET /patches/{id}` — patch diff + validation results  
`POST /patches/{id}/validate` — re-run validation

#### [NEW] `backend/app/api/v1/auth.py`
`GET /auth/github` — OAuth redirect  
`GET /auth/github/callback` — OAuth callback + JWT

---

### Component 8: Backend — Services

#### [NEW] `backend/app/services/github_service.py`
- GitHub REST API client (`PyGithub`)
- Create branch, commit files, push, open PR
- Attach structured bug report as PR body
- Request review from repo maintainers

#### [NEW] `backend/app/services/job_service.py`
- Celery task: `run_autobug_pipeline(issue_id)`
- SSE event emitter for real-time progress
- State checkpointing to Redis

#### [NEW] `backend/app/services/report_service.py`
- Render Markdown report from agent state
- Generate HTML + PDF via `weasyprint`
- Export JSON structured report

---

### Component 9: Frontend — Next.js App

#### [NEW] `frontend/src/app/layout.tsx`
Root layout with dark theme, Inter font, global nav.

#### [NEW] `frontend/src/app/page.tsx`
**Landing page** — Hero section, feature highlights, live demo CTA, KPI stats.

#### [NEW] `frontend/src/app/dashboard/page.tsx`
**Dashboard** — Connected repos grid, recent jobs, system health widgets.

#### [NEW] `frontend/src/app/repositories/page.tsx`
Repository list with search + index status badges.

#### [NEW] `frontend/src/app/repositories/[id]/page.tsx`
Repository detail: file tree, index progress, semantic search.

#### [NEW] `frontend/src/app/issues/new/page.tsx`
**Submit Bug** — Multi-step form: repo selection → issue input → submit.

#### [NEW] `frontend/src/app/issues/[id]/page.tsx`
**Job Monitor** — Real-time agent progress timeline, live logs, results.

#### [NEW] `frontend/src/app/issues/[id]/report/page.tsx`
**Bug Report Viewer** — Root cause, diff viewer, validation results, PR link.

#### [NEW] `frontend/src/components/`
Reusable components:
- `AgentTimeline` — Animated step-by-step agent execution visual
- `DiffViewer` — Side-by-side code diff with syntax highlighting
- `CodeSearchBar` — Semantic search input with results panel
- `RepoCard` — Repository card with status indicators
- `IssueForm` — Rich bug submission form
- `LiveLogs` — Scrolling terminal-style log viewer
- `StatsCard` — KPI metric display

---

### Component 10: Configuration & DevOps

#### [NEW] `backend/requirements.txt`
All Python dependencies pinned.

#### [NEW] `backend/Dockerfile`
Multi-stage Python build.

#### [NEW] `frontend/Dockerfile`
Next.js production build.

#### [NEW] `backend/alembic/` 
DB migration scripts for all models.

---

## Verification Plan

### Automated Tests
```bash
# Backend unit tests
cd backend && pytest tests/ -v --cov=app

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend lint
cd frontend && npm run lint
```

### Manual Verification
1. Start full stack: `docker-compose up`
2. Open `http://localhost:3000` — verify landing page renders
3. Connect a GitHub repo — verify indexing completes
4. Submit a test bug issue — verify all 17 agents execute in sequence
5. Verify PR is opened on GitHub with report attached
6. Verify SSE stream shows live agent progress in UI

---

## Implementation Order

1. **Infrastructure** — docker-compose, env files, README
2. **Backend core** — config, DB, models, migrations
3. **RAG engine** — indexer, retriever, AST parser
4. **Sandbox** — Docker manager
5. **Agents** — LangGraph graph + all 17 agents
6. **API layer** — all REST endpoints + SSE
7. **Services** — GitHub service, job service, report service
8. **Frontend** — Next.js app, all pages and components
9. **Integration** — wire frontend ↔ backend
10. **Testing** — unit tests, smoke tests
