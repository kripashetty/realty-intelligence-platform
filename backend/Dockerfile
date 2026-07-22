FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN addgroup --system app \
 && adduser --system --group app

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/
COPY alembic.ini .
COPY alembic/ ./alembic/

RUN uv pip install --system --no-cache -e .

USER app

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]