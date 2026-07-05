# syntax=docker/dockerfile:1

# --- Stage 1: build the Vite frontend into static assets ---------------------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# VITE_MOCK stays 0: the built app talks to the real backend on the same origin.
ENV VITE_MOCK=0
RUN npm run build

# --- Stage 2: python runtime that also serves the built frontend -------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST=/app/backend/static

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./backend/static

WORKDIR /app/backend

# Render provides $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
