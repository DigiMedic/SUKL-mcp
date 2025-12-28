# Multi-stage build pro minimální image size
FROM python:3.10-slim as builder

# Build dependencies
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir --user -e .

# Runtime stage
FROM python:3.10-slim

# Metadata
LABEL maintainer="SUKL MCP Server Team"
LABEL version="2.1.0"
LABEL description="Production-ready MCP server pro české farmaceutické databáze"

# Create non-root user
RUN useradd -m -u 1000 sukl && \
    mkdir -p /tmp/sukl_dlp_cache /tmp/sukl_dlp_data && \
    chown -R sukl:sukl /tmp/sukl_dlp_cache /tmp/sukl_dlp_data

# Copy Python packages from builder
COPY --from=builder /root/.local /home/sukl/.local
COPY --from=builder /build /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER sukl

# Environment variables
ENV PATH=/home/sukl/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    SUKL_CACHE_DIR=/tmp/sukl_dlp_cache \
    SUKL_DATA_DIR=/tmp/sukl_dlp_data \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)" || exit 1

# Expose port
EXPOSE 8000

# Entry point
CMD ["python", "-m", "sukl_mcp"]
