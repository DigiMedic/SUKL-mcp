# Deployment Guide

## Overview

The SÚKL MCP Server supports three deployment modes:

1. **Local Development** (stdio transport) - For Claude Desktop integration
2. **FastMCP Cloud** (stdio transport) - Managed cloud deployment
3. **Smithery** (HTTP transport) - Docker-based containerized deployment

## Local Development Deployment

### Prerequisites

- Python 3.10+
- Virtual environment
- Claude Desktop (optional)

### Setup

```bash
# Clone and install
git clone https://github.com/your-org/fastmcp-boilerplate.git
cd fastmcp-boilerplate
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run server
python -m sukl_mcp
```

### Claude Desktop Integration

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": [
        "-m",
        "sukl_mcp.server"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/fastmcp-boilerplate/src",
        "SUKL_CACHE_DIR": "/tmp/sukl_dlp_cache",
        "SUKL_DATA_DIR": "/tmp/sukl_dlp_data",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: `~/.config/Claude/claude_desktop_config.json`

### Restart Claude Desktop

After configuration changes, restart Claude Desktop app.

### Verify Connection

In Claude Desktop, ask:
```
Can you search for ibuprofen in the SÚKL database?
```

---

## FastMCP Cloud Deployment

### Prerequisites

- FastMCP CLI: `pip install fastmcp`
- FastMCP Cloud account: https://gofastmcp.com
- GitHub repository

### Configuration

The project includes `fastmcp.yaml`:

```yaml
server:
  module: sukl_mcp.server  # Absolute import
  instance: mcp

runtime:
  python: "3.10"

dependencies:
  - fastmcp>=2.14.0,<3.0.0
  - httpx>=0.27.0
  - pydantic>=2.0.0
  - pandas>=2.0.0

environment:
  SUKL_CACHE_DIR: /tmp/sukl_dlp_cache
  SUKL_DATA_DIR: /tmp/sukl_dlp_data
  SUKL_DOWNLOAD_TIMEOUT: "120.0"

metadata:
  name: SÚKL MCP Server
  version: 2.1.0
  description: Production-ready MCP server for Czech pharmaceutical database
  author: FastMCP Community
  license: MIT
```

### Deployment Steps

```bash
# 1. Login to FastMCP Cloud
fastmcp login

# 2. Deploy from repository root
fastmcp deploy

# 3. View deployment status
fastmcp status

# 4. View logs
fastmcp logs --follow
```

### Automatic Deployments

FastMCP Cloud auto-deploys on Git push to main branch:

```bash
# Commit changes
git add .
git commit -m "feat: update medicine search"
git push origin main

# FastMCP automatically redeploys
```

### Monitoring

```bash
# View logs
fastmcp logs --tail 200

# Check health
fastmcp status

# View metrics
fastmcp metrics
```

### Troubleshooting

**Issue**: "attempted relative import with no known parent package"

**Solution**: Ensure all imports are absolute:
```python
# ✅ Correct
from sukl_mcp.server import mcp
from sukl_mcp.client_csv import get_sukl_client

# ❌ Wrong
from .server import mcp
from .client_csv import get_sukl_client
```

**Issue**: "Module not found"

**Solution**: Check `fastmcp.yaml`:
- Verify `module: sukl_mcp.server` matches directory structure
- Ensure all dependencies listed
- Verify `src/sukl_mcp/__init__.py` exists

**Issue**: Slow initialization

**Solution**: Increase timeout:
```yaml
environment:
  SUKL_DOWNLOAD_TIMEOUT: "300.0"  # 5 minutes
```

---

## Smithery Deployment

### Prerequisites

- Docker installed
- Smithery account: https://smithery.ai
- `smithery.yaml` configuration

### Configuration

The project includes `smithery.yaml`:

```yaml
runtime: "container"

startCommand:
  type: "http"

  configSchema:
    type: "object"
    properties:
      cacheDir:
        type: "string"
        title: "Cache Directory"
        default: "/tmp/sukl_dlp_cache"
      dataDir:
        type: "string"
        title: "Data Directory"
        default: "/tmp/sukl_dlp_data"
      downloadTimeout:
        type: "number"
        title: "Download Timeout (seconds)"
        default: 120.0
      logLevel:
        type: "string"
        enum: ["DEBUG", "INFO", "WARNING", "ERROR"]
        default: "INFO"

build:
  context: "."
  dockerfile: "Dockerfile"

environment:
  SUKL_CACHE_DIR: "{{ config.cacheDir }}"
  SUKL_DATA_DIR: "{{ config.dataDir }}"
  SUKL_DOWNLOAD_TIMEOUT: "{{ config.downloadTimeout }}"
  LOG_LEVEL: "{{ config.logLevel }}"
  MCP_TRANSPORT: "http"
  MCP_HOST: "0.0.0.0"
  MCP_PORT: "8000"

resources:
  memory: "512Mi"
  cpu: "500m"

healthCheck:
  path: "/health"
  port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 10
```

### Docker Build

```bash
# Build image
docker build -t sukl-mcp:latest .

# Test locally
docker run -p 8000:8000 sukl-mcp:latest

# Check health
curl http://localhost:8000/health
```

### Dockerfile Details

Multi-stage build for minimal image size:

```dockerfile
# Stage 1: Builder
FROM python:3.10-slim as builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --user -e .

# Stage 2: Runtime
FROM python:3.10-slim

# Non-root user
RUN useradd -m -u 1000 sukl && \
    mkdir -p /tmp/sukl_dlp_cache /tmp/sukl_dlp_data && \
    chown -R sukl:sukl /tmp/sukl_dlp_cache /tmp/sukl_dlp_data

# Copy from builder
COPY --from=builder /root/.local /home/sukl/.local
COPY --from=builder /build /app

WORKDIR /app
USER sukl

ENV PATH=/home/sukl/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "sukl_mcp"]
```

### Deploy to Smithery

```bash
# Login
smithery login

# Deploy
smithery deploy

# View status
smithery status sukl-mcp

# View logs
smithery logs sukl-mcp --follow
```

### HTTP Client Configuration

Connect to Smithery deployment via HTTP:

```python
import httpx

# MCP over HTTP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://your-smithery-url.smithery.ai/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_medicine",
                "arguments": {"query": "ibuprofen", "limit": 10}
            }
        }
    )
    print(response.json())
```

---

## Environment Variables Reference

### Data Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SUKL_OPENDATA_URL` | `https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip` | Data source URL |
| `SUKL_CACHE_DIR` | `/tmp/sukl_dlp_cache` | ZIP cache directory |
| `SUKL_DATA_DIR` | `/tmp/sukl_dlp_data` | Extracted CSV directory |
| `SUKL_DOWNLOAD_TIMEOUT` | `120.0` | Download timeout (seconds) |

### Transport Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio`, `http`, `sse` |
| `MCP_HOST` | `0.0.0.0` | HTTP server host (HTTP mode only) |
| `MCP_PORT` | `8000` | HTTP server port (HTTP mode only) |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Performance Tuning

### Memory Optimization

```yaml
# Smithery resource limits
resources:
  memory: "512Mi"   # Minimum for pandas DataFrames
  cpu: "500m"       # 0.5 CPU cores
```

For larger datasets:
```yaml
resources:
  memory: "1Gi"     # 1 GB
  cpu: "1000m"      # 1 CPU core
```

### Cold Start Optimization

```python
# Lazy data loading
@asynccontextmanager
async def server_lifespan(server):
    # Initialize but don't block
    asyncio.create_task(get_sukl_client())
    yield
```

### Caching Strategy

```bash
# Persistent cache (Docker volumes)
docker run -v sukl-cache:/tmp/sukl_dlp_cache \
           -v sukl-data:/tmp/sukl_dlp_data \
           -p 8000:8000 sukl-mcp:latest
```

---

## Security Considerations

### HTTPS/TLS

**FastMCP Cloud**: Automatic HTTPS with managed certificates

**Smithery**: Configure reverse proxy:

```yaml
# Add nginx proxy
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - /etc/letsencrypt:/etc/letsencrypt
```

### Authentication

**Current**: No authentication (public server)

**Future Enhancement**:

```yaml
# smithery.yaml
environment:
  API_KEY: "{{ config.apiKey }}"
```

```python
# server.py
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
```

### Rate Limiting

Add rate limiting middleware:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@mcp.tool
@limiter.limit("100/minute")
async def search_medicine(...):
    ...
```

---

## Monitoring and Logging

### Log Aggregation

**FastMCP Cloud**: Built-in log viewer

```bash
fastmcp logs --follow --since 1h
```

**Smithery**: Integrate with logging service

```yaml
# Smithery logging
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Metrics Collection

Add Prometheus exporter:

```python
from prometheus_client import Counter, Histogram

search_counter = Counter('sukl_searches_total', 'Total searches')
search_duration = Histogram('sukl_search_duration_seconds', 'Search duration')

@mcp.tool
async def search_medicine(...):
    search_counter.inc()
    with search_duration.time():
        # ... implementation
```

### Health Checks

**HTTP endpoint** (`/health`):

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    client = await get_sukl_client()
    health_status = await client.health_check()
    return {
        "status": "healthy" if health_status["status"] == "ok" else "unhealthy",
        "version": "2.1.0",
        "data": health_status
    }
```

**Docker HEALTHCHECK**:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)" || exit 1
```

---

## Backup and Recovery

### Data Backup

```bash
# Backup cached ZIP
tar -czf sukl-backup-$(date +%Y%m%d).tar.gz \
    /tmp/sukl_dlp_cache \
    /tmp/sukl_dlp_data

# Upload to cloud storage
aws s3 cp sukl-backup-*.tar.gz s3://my-backups/
```

### Disaster Recovery

```bash
# Restore from backup
tar -xzf sukl-backup-20241229.tar.gz -C /

# Restart server
docker restart sukl-mcp
```

---

## Troubleshooting Guide

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Slow startup | Server takes >60s to start | Increase `SUKL_DOWNLOAD_TIMEOUT`, use cached data |
| Out of memory | Container killed | Increase memory limit to 1Gi |
| Import errors | Module not found | Check PYTHONPATH, ensure absolute imports |
| Connection refused | Cannot reach server | Check firewall, verify port 8000 exposed |
| Data outdated | Search returns old results | Delete cache, restart server |

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m sukl_mcp

# Or in Docker
docker run -e LOG_LEVEL=DEBUG -p 8000:8000 sukl-mcp:latest
```

### Validation Script

Create `validate-deployment.sh`:

```bash
#!/bin/bash
set -e

echo "=== Validating SÚKL MCP Server Deployment ==="

# 1. Check Python version
python --version | grep -E "3\.(10|11|12|13)" || {
    echo "❌ Python 3.10+ required"
    exit 1
}

# 2. Check imports
python -c "from sukl_mcp.server import mcp; print('✅ Imports OK')"

# 3. Check data loading
timeout 60 python -c "
import asyncio
from sukl_mcp.client_csv import get_sukl_client

async def test():
    client = await get_sukl_client()
    health = await client.health_check()
    assert health['status'] == 'ok'
    print('✅ Data loading OK')

asyncio.run(test())
"

# 4. Run tests
pytest tests/ -v || {
    echo "❌ Tests failed"
    exit 1
}

echo "✅ All validation checks passed"
```

---

**Last Updated**: December 29, 2024
**Version**: 2.1.0
