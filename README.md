# Realty Intelligence Platform

Berlin rental market intelligence tool — recommends listing prices for landlords based on real comparable data.

## Architecture

- **Backend**: FastAPI (Python 3.11) + PostgreSQL + Ollama (llama3.1:8b)
- **Frontend**: React 18 + TypeScript + TanStack Query
- **Infrastructure**: Azure Container Apps + Azure Static Web Apps + Azure PostgreSQL Flexible Server (Bicep IaC)

## Local Development

### Prerequisites

- Docker + Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+

### 1. Start local services

```bash
docker compose up db ollama
```

Pull the Ollama model (first run only — ~5GB):

```bash
docker compose exec ollama ollama pull llama3.1:8b
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

### 5. Upload listing data

Export a CSV from [Fredy](https://github.com/orangetux/fredy) and upload it via the UI or:

```bash
curl -X POST http://localhost:8000/api/v1/listings/import \
  -F "file=@your-listings.csv"
```

### 6. Get a pricing recommendation

Submit via the web UI, or:

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"address":"Invalidenstraße 50, 10115 Berlin","size_m2":72,"rooms":3,"floor":2}'
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://realty:realty@localhost:5432/realty` | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama API URL |

See `.env.example` for a complete reference.

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

## Infrastructure Deployment

```bash
# Deploy to dev
az deployment group create \
  --resource-group realty-dev-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters/dev.bicepparam \
  --parameters postgresAdminPassword=<secret>
```

## CSV Schema

The import endpoint accepts a CSV with these columns:

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
