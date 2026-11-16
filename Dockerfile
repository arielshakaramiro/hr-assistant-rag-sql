# One image: build the frontend, then serve it from the FastAPI backend (ADR-10).
# Stage 1 — build the React/Vite static bundle.
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2 — the Python backend, with the built frontend copied in.
FROM python:3.12-slim AS app
WORKDIR /app

# System deps kept minimal; psycopg uses the binary wheel.
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=180 PIP_RETRIES=5

COPY backend/ ./backend/
# Install CPU-only torch first (the CUDA build pulled by sentence-transformers would add
# several GB of GPU libraries that are useless on a CPU host), then the app.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install ./backend
COPY --from=frontend /frontend/dist ./frontend/dist

WORKDIR /app/backend
EXPOSE 8000

# Run migrations, then the server. The DB URL and LLM settings come from the environment.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
