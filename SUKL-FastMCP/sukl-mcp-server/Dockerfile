# SÚKL MCP Server - Docker image
# Multi-stage build pro minimální velikost

# === Build stage ===
FROM python:3.11-slim as builder

WORKDIR /app

# Instalace build závislostí
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Kopírování pouze requirements pro lepší cache
COPY pyproject.toml .
COPY src/ src/

# Instalace závislostí do virtuálního prostředí
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[server]"


# === Production stage ===
FROM python:3.11-slim as production

WORKDIR /app

# Bezpečnostní nastavení
RUN groupadd -r sukl && useradd -r -g sukl sukl

# Kopírování virtuálního prostředí z build stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Kopírování zdrojového kódu
COPY --from=builder /app/src /app/src

# Nastavení vlastníka
RUN chown -R sukl:sukl /app

# Přepnutí na non-root uživatele
USER sukl

# Proměnné prostředí
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SUKL_CACHE_ENABLED=true \
    SUKL_CACHE_TTL_SECONDS=3600

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Port
EXPOSE 8000

# Spuštění serveru
CMD ["python", "-m", "sukl_mcp.server"]


# === Development stage ===
FROM python:3.11-slim as development

WORKDIR /app

# Instalace dev závislostí
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopírování virtuálního prostředí
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalace dev závislostí
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black ruff mypy

# Kopírování zdrojového kódu
COPY . .

# Mount point pro live reload
VOLUME ["/app/src"]

# Port
EXPOSE 8000

# Spuštění s reload
CMD ["uvicorn", "sukl_mcp.server:mcp.app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
