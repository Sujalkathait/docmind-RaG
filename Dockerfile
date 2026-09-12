# ==============================================================================
# DocMind RAG + Second Brain — Multi-Stage Production Dockerfile
# Builds the React frontend, packages Python backend, and serves both on port 8000.
# ==============================================================================

# STAGE 1: Frontend Build
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# STAGE 2: Python Runtime & Backend
FROM python:3.11-slim AS runtime

# Install system utilities and build dependencies for llama.cpp / SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY backend/ ./backend/
COPY raw/ ./raw/
COPY wiki/ ./wiki/
COPY ctx/ ./ctx/
COPY mem/ ./mem/
COPY output/ ./output/
COPY config.py run_server.py download_model.py ./

# Download lightweight model during build so container is ready out-of-the-box
RUN python download_model.py -m smollm2-360m

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Run unified server
CMD ["python", "-m", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
