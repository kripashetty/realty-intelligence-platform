# Realty Intelligence Platform

Berlin rental market intelligence tool — recommends listing prices for landlords based on real comparable data.

## Architecture

- **Backend**: FastAPI (Python 3.11) + PostgreSQL + Ollama (llama3.1:8b)
- **Frontend**: React 18 + TypeScript + TanStack Query
- **Infrastructure**: Azure Container Apps + Azure Static Web Apps + Azure PostgreSQL Flexible Server (Bicep IaC)

---

## Running the Full Application with Docker Compose

This is the recommended way to run everything locally. All services — database, Ollama, backend, and frontend — start with a single command.

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)

### First-time setup

```bash
docker compose up
```

This will:
1. Start PostgreSQL and wait until it is healthy
2. Start Ollama and wait until it is healthy
3. **Download `llama3.1:8b`** (~5GB) via the `ollama-init` service — this only runs on first start; subsequent starts skip the download if the model is already cached in the `ollama_data` volume
4. Build and start the FastAPI backend
5. Build and start the React frontend (served by nginx)

> The model download can take several minutes depending on your connection. Watch the `ollama-init` container logs to track progress:
> ```bash
> docker compose logs -f ollama-init
> ```

### Run database migrations

Once the backend container is up, run Alembic migrations (first time only):

```bash
docker compose exec backend uv run alembic upgrade head
```

### Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8000/api/v1/docs |
| Health check | http://localhost:8000/health |

### Subsequent starts

The model is cached in the `ollama_data` Docker volume, so subsequent starts are fast:

```bash
docker compose up
```

### Stopping

```bash
docker compose down          # stop containers, keep volumes (data preserved)
docker compose down -v       # stop containers and delete all data
```

---

## Local Development (without Docker for backend/frontend)

Faster iteration — only the database and Ollama run in Docker.

### Prerequisites

- Docker Desktop
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Node.js 20+

### 1. Start database and Ollama

```bash
docker compose up db ollama ollama-init
```

### 2. Run database migrations

```bash
cd backend
uv run alembic upgrade head
```

### 3. Start the backend

```bash
cd backend
uv run uvicorn src.main:app --reload
```

API docs: http://localhost:8000/api/v1/docs

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

---

## Uploading Listing Data

Export a CSV from [Fredy](https://github.com/orangetux/fredy) and upload via the UI, or:

```bash
curl -X POST http://localhost:8000/api/v1/listings/import \
  -F "file=@your-listings.csv"
```

Use the included sample fixture to test:

```bash
curl -X POST http://localhost:8000/api/v1/listings/import \
  -F "file=@specs/001-rental-market-intelligence/fixtures/sample-listings.csv"
```

## CSV Schema

| Column | Required | Notes |
|--------|----------|-------|
| `title` | No | Listing headline |
| `address` | Yes | Full Berlin address |
| `price` | Yes | EUR/month — supports German format `1.250,00` |
| `size` | Yes | m² — supports `72,5` |
| `rooms` | Yes | e.g. `2.5` |
| `floor` | No | Ground floor = 0 |
| `url` | Yes | Source URL (deduplication key with date) |
| `date` | Yes | `YYYY-MM-DD` or `DD.MM.YYYY` |
| `provider` | Yes | e.g. `immobilienscout24` |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://realty:realty@localhost:5432/realty` | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend URL used by the frontend build |

See `.env.example` for a complete reference.

---

## Running Tests

**Backend** (requires running PostgreSQL):

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://realty:realty@localhost:5432/realty_test \
  uv run pytest -v
```

**Frontend**:

```bash
cd frontend
npm test
```

---

## Infrastructure Deployment

```bash
# Deploy to dev
az deployment group create \
  --resource-group realty-dev-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam \
  --parameters postgresAdminPassword=<secret>
```
