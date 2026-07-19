# AutoBug AI

> **WARNING:** Still all features are not working and the platform is being actively developed.

## Current Issues and Challenges

1. **Pipeline Summary Metrics Calculation**: Pipeline counters may show completed/skipped count discrepancies due to unexecuted nodes not being fully derived directly from downstream states.
2. **Environment and Runtime Execution Alignment**: Distinguishing local sandbox environment checks (e.g. pytest availability) from project imports (e.g. ModuleNotFoundErrors) during execution.
3. **Fault Location Verification**: Displaying specific file/line locations when validation is blocked (meaning application logic is never reached) can create conflicts.
4. **Validation Blocked Patches**: Generated patches must be labeled as "Proposed / Not Verified" rather than verified patches if validation test runner collection fails early.
5. **State-Machine Pipeline Gates**: Transitioning the pipeline orchestrator to a strict enum state-machine configuration to natively resolve step gating and prerequisites.

---

**Autonomous bug detection, root cause analysis, and code fix generation.**

AutoBug AI connects to your GitHub repository, runs a LangGraph pipeline to analyze bugs, generate validated patches with regression tests, and automatically opens Pull Requests.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.1-purple)](https://langchain-ai.github.io/langgraph/)

---

## Features

- **Specialized AI Agents** — orchestrated via LangGraph for autonomous bug fixing
- **RAG Code Search** — Qdrant-powered semantic search across entire codebases
- **Docker Sandbox** — isolated containers for safe bug reproduction and test execution
- **Real-Time SSE Streaming** — live agent progress streamed to the UI
- **Automated PRs** — generates patch + tests, pushes branch, opens GitHub PR
- **Multi-Language** — Python, JavaScript, TypeScript, Go, Rust, Java, and more

---

## Architecture

```
AutoBug/
├── backend/          # FastAPI + LangGraph + Celery
│   └── app/
│       ├── agents/   # LangGraph agent nodes
│       ├── rag/      # Qdrant vector search + AST parser
│       ├── sandbox/  # Docker container manager
│       ├── api/      # REST API + SSE endpoints
│       ├── services/ # GitHub, Job, Report services
│       └── models/   # SQLAlchemy ORM models
├── frontend/         # Next.js 14 + Tailwind CSS
│   └── src/
│       ├── app/      # App Router pages
│       ├── components/
│       ├── hooks/    # useSSE hook
│       └── lib/      # API client + SSE client
└── docker-compose.yml
```

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- Git

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd AutoBug
cp backend/.env.example backend/.env
```

Edit `backend/.env` and add your API keys:

```env
# Required — at least one LLM provider
MISTRAL_API_KEY=your_key_here      # Primary (free tier available)
OPENAI_API_KEY=your_key_here       # Optional fallback
ANTHROPIC_API_KEY=your_key_here    # Optional

# Required for GitHub PR creation
GITHUB_TOKEN=ghp_your_pat_here

# Optional — GitHub OAuth for UI login
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

# Security
SECRET_KEY=change_me_in_production
```

### 2. Configure AI model (optional)

Edit `config.yaml` to change the LLM provider/model:

```yaml
llm:
  provider: mistral        # mistral | openai | anthropic | google
  model: open-mistral-7b   # Model name for the provider
  temperature: 0.1
```

### 3. Start everything

```bash
docker-compose up --build
```

Services started:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Flower (Celery) | http://localhost:5555 |
| Qdrant | http://localhost:6333 |

### 4. Use AutoBug AI

1. **Open** http://localhost:3000
2. **Connect** a GitHub repository → indexing starts automatically
3. **Submit** a bug report with steps to reproduce
4. **Watch** the agents work in real-time on the Issue Monitor page
5. **Review** the generated patch, tests, and PR

---

## The Agent Pipeline

| # | Agent | What it does |
|---|-------|-------------|
| 1 | Repository Agent | Clones repo, detects languages, builds file tree |
| 2 | Issue Agent | Parses bug report, extracts error type, stack trace, severity |
| 3 | Planner Agent | Generates 5-8 search queries and investigation strategy |
| 4 | Retrieval Agent | RAG semantic search for relevant code chunks |
| 5 | Environment Agent | Detects runtime, creates Docker sandbox |
| 6 | Build Agent | Installs dependencies inside sandbox |
| 7 | Reproduction Agent | Generates and runs command to reproduce the bug |
| 8 | Localization Agent | Narrows fault to specific files and functions |
| 9 | Root Cause Agent | Deep LLM analysis → root cause + confidence score |
| 10 | Patch Agent | Generates minimal unified diff fix |
| 11 | Static Analysis Agent | Runs ruff/eslint on the patch |
| 12 | Test Generator Agent | Writes regression + unit tests |
| 13 | Test Runner Agent | Executes tests in sandbox, captures results |
| 14 | Reviewer Agent | LLM code review: correctness, security, quality |
| 15 | Git Agent | Creates branch, commits patch + tests |
| 16 | PR Agent | Pushes branch, opens GitHub PR |
| 17 | Report Agent | Generates comprehensive Markdown report |

---

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for the full list with descriptions.

Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `MISTRAL_API_KEY` | Yes (or another LLM key) | Primary LLM for agents |
| `GITHUB_TOKEN` | Yes (for PRs) | PAT with `repo` + `pull_requests` scopes |
| `DATABASE_URL` | Auto-set by Docker | PostgreSQL connection string |
| `REDIS_URL` | Auto-set by Docker | Redis for Celery broker + SSE |
| `QDRANT_URL` | Auto-set by Docker | Qdrant vector DB for RAG |

---

## Development

### Backend only

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

### Run database migrations

```bash
cd backend
alembic upgrade head
```

### Type-check frontend

```bash
cd frontend
npm run type-check
```

---

## License

MIT @ AutoBug AI Contributors
