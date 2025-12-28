# Smithery Deployment Guide

Tento dokument poskytuje kompletní průvodce nasazením SÚKL MCP serveru na Smithery platform.

## 🚀 Rychlý start

```bash
# 1. Build Docker image lokálně
docker build -t sukl-mcp:2.0.0 .

# 2. Test lokálně
docker run -p 8000:8000 -e MCP_TRANSPORT=http sukl-mcp:2.0.0

# 3. Deploy na Smithery
smithery deploy
```

## 📋 Požadavky

- **Docker Desktop** - verze 20.10+ (pro lokální testování)
- **Smithery CLI** - nainstaluj přes `npm install -g smithery`
- **Smithery Account** - zaregistruj se na https://smithery.ai
- **Git** - pro verzování změn

## 🎯 Co je Smithery?

[Smithery](https://smithery.ai) je platforma pro nasazení a správu MCP (Model Context Protocol) serverů. Klíčové vlastnosti:

- **Container-based deployment** - používá Docker kontejnery
- **HTTP/SSE transport** - RESTful API pro MCP servery
- **Managed infrastructure** - automatické škálování a monitoring
- **Server registry** - publish serveru pro další uživatele
- **Configuration management** - uživatelská konfigurace přes UI

## 🏗️ Architektura deploymentu

```
┌─────────────────────────────────────┐
│     Smithery Platform               │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  SÚKL MCP Container          │  │
│  │                              │  │
│  │  python:3.10-slim            │  │
│  │  + FastMCP 2.14+             │  │
│  │  + HTTP Transport            │  │
│  │  + Health Checks             │  │
│  └──────────────────────────────┘  │
│           ↕ HTTP                   │
│  ┌──────────────────────────────┐  │
│  │  Smithery Gateway            │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
         ↕ MCP Protocol
┌─────────────────────────────────────┐
│     AI Client (Claude, atd.)        │
└─────────────────────────────────────┘
```

## 📦 Docker lokální testování

### Build image

```bash

# Build s taggem
docker build -t sukl-mcp:2.0.0 .

# Kontrola velikosti image (mělo by být ~200-350 MB)
docker images sukl-mcp:2.0.0
```

### Spuštění kontejneru

```bash
# Základní spuštění
docker run -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  sukl-mcp:2.0.0

# S custom konfigurací
docker run -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  -e SUKL_CACHE_DIR=/data/cache \
  -e SUKL_DATA_DIR=/data/csv \
  -e SUKL_DOWNLOAD_TIMEOUT=180.0 \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/data:/data \
  sukl-mcp:2.0.0

# Interaktivní režim (pro debugging)
docker run -it -p 8000:8000 \
  -e MCP_TRANSPORT=http \
  sukl-mcp:2.0.0 \
  /bin/bash
```

### Health check test

```bash
# Základní health check
curl http://localhost:8000/health

# Očekávaný výstup:
# {"status":"healthy"}

# Pokud health check selže, zkontroluj logy:
docker logs <container_id>
```

### Testování MCP tools

```bash
# Test vyhledávání léčiv
curl -X POST http://localhost:8000/mcp/search_medicine \
  -H "Content-Type: application/json" \
  -d '{"query": "ibuprofen", "limit": 5}'

# Test detailu léčiva
curl -X POST http://localhost:8000/mcp/get_medicine_details \
  -H "Content-Type: application/json" \
  -d '{"sukl_code": "0012345"}'
```

## 🔧 Smithery CLI Deployment

### 1. Instalace Smithery CLI

```bash
# NPM
npm install -g smithery

# Nebo Yarn
yarn global add smithery

# Ověření instalace
smithery --version
```

### 2. Přihlášení

```bash
# Přihlášení do Smithery
smithery login

# Zadej credentials z https://smithery.ai/account
```

### 3. Konfigurace projektu

Projekt už obsahuje `smithery.yaml` s kompletní konfigurací:

```yaml
runtime: "container"
startCommand:
  type: "http"
metadata:
  name: "SÚKL MCP Server"
  version: "2.0.0"
# ... další konfigurace
```

### 4. Deployment

```bash
# Deploy do Smithery
smithery deploy

# S konkrétní environment
smithery deploy --env production

# S dry-run (test bez deploymentu)
smithery deploy --dry-run
```

### 5. Monitoring

```bash
# Zobrazení logů
smithery logs --follow

# Status serveru
smithery status

# Metriky
smithery metrics

# Seznam deploymentů
smithery list
```

## ⚙️ Konfigurace

### Environment Variables

Server podporuje následující ENV proměnné (nastavitelné přes Smithery UI):

| Proměnná | Popis | Výchozí hodnota |
|----------|-------|----------------|
| `SUKL_CACHE_DIR` | Cache adresář pro stažené ZIP | `/tmp/sukl_dlp_cache` |
| `SUKL_DATA_DIR` | Data adresář pro CSV soubory | `/tmp/sukl_dlp_data` |
| `SUKL_DOWNLOAD_TIMEOUT` | Timeout pro stažení dat (sec) | `120.0` |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `MCP_TRANSPORT` | Transport typ (http/stdio/sse) | `http` |
| `MCP_HOST` | HTTP server host | `0.0.0.0` |
| `MCP_PORT` | HTTP server port | `8000` |

### Smithery Configuration Schema

Smithery UI automaticky generuje formulář podle `configSchema` v `smithery.yaml`:

```yaml
configSchema:
  type: "object"
  properties:
    cacheDir:
      type: "string"
      title: "Cache Directory"
      default: "/tmp/sukl_dlp_cache"
    # ... další properties
```

Uživatelé mohou hodnoty měnit přes webové rozhraní.

## 🔍 Troubleshooting

### Problém: Docker build selhává

**Příznaky:**
```
ERROR: failed to solve: process "/bin/sh -c pip install --no-cache-dir --user -e ." did not complete successfully
```

**Řešení:**
1. Zkontroluj, že máš správnou verzi Dockeru: `docker --version` (min. 20.10+)
2. Vymaž Docker cache: `docker system prune -a`
3. Build znovu: `docker build --no-cache -t sukl-mcp:2.0.0 .`

### Problém: Container se restartuje v loop

**Příznaky:**
```
docker ps -a
# Container má status "Restarting"
```

**Řešení:**
1. Zkontroluj logy: `docker logs <container_id>`
2. Zkontroluj health check: Je server schopen odpovídat na `http://localhost:8000/health`?
3. Zvýš `start-period` v Dockerfile (řádek 49): `--start-period=120s`
4. Zkontroluj, že pandas má dostatek paměti pro načtení CSV

### Problém: Health check selává

**Příznaky:**
```
curl http://localhost:8000/health
# curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Řešení:**
1. Zkontroluj, že container běží: `docker ps`
2. Zkontroluj port mapping: `docker port <container_id>`
3. Zkontroluj, že `MCP_TRANSPORT=http` je nastaveno
4. Zkontroluj firewall/antivirus

### Problém: Smithery deployment selává

**Příznaky:**
```
smithery deploy
# Error: Build failed
```

**Řešení:**
1. **Lokálně otestuj Docker build**: `docker build -t test .`
2. **Zkontroluj smithery.yaml syntax**: `smithery validate`
3. **Zkontroluj logy**: `smithery logs --tail 100`
4. **Zkontroluj resource limits**: Zvýš `memory` v `smithery.yaml`

### Problém: Data se nenačítají (SÚKL Open Data)

**Příznaky:**
```
# V logs:
ERROR: Failed to download SÚKL data: Timeout
```

**Řešení:**
1. Zvýš timeout: `-e SUKL_DOWNLOAD_TIMEOUT=300.0`
2. Zkontroluj network connectivity: `docker run --rm sukl-mcp:2.0.0 curl https://opendata.sukl.cz`
3. Použij volume pro persistent cache:
   ```bash
   docker run -v ./cache:/tmp/sukl_dlp_cache sukl-mcp:2.0.0
   ```

## 📊 Monitoring a Logs

### Docker logs

```bash
# Real-time logs
docker logs -f <container_id>

# Poslední 100 řádků
docker logs --tail 100 <container_id>

# Logs s timestamps
docker logs --timestamps <container_id>
```

### Smithery logs

```bash
# Real-time
smithery logs --follow

# S filtrem
smithery logs --level ERROR

# Exportovat do souboru
smithery logs --tail 1000 > logs.txt
```

### Health monitoring

```bash
# Automatický health check script
while true; do
  curl -f http://localhost:8000/health || echo "Health check failed!"
  sleep 30
done
```

## ⚖️ FastMCP Cloud vs Smithery

| Feature | FastMCP Cloud | Smithery |
|---------|---------------|----------|
| **Transport** | STDIO (standard I/O) | HTTP/SSE |
| **Deployment** | Serverless function | Docker container |
| **Configuration** | `fastmcp.yaml` | `smithery.yaml` |
| **Startup time** | ~2-5 seconds | ~30-60 seconds |
| **Memory** | Sdílená | Dedicated (512Mi) |
| **Scaling** | Automatické | Container-based |
| **Monitoring** | FastMCP logs | Smithery metrics |
| **Cost** | Free tier friendly | Pay-as-you-go |
| **Best for** | Lightweight, fast | Heavy workloads |

**Doporučení:**
- **FastMCP Cloud**: Pro rychlé dotazy, minimální latenci, development
- **Smithery**: Pro produkční workloady, heavy data processing, custom infrastructure

## 🎯 Best Practices

### 1. Optimalizace Docker image

```dockerfile
# ✅ SPRÁVNĚ - Multi-stage build
FROM python:3.10-slim as builder
RUN pip install --user -e .

FROM python:3.10-slim
COPY --from=builder /root/.local /home/user/.local

# ❌ ŠPATNĚ - Single-stage s velkým image
FROM python:3.10
RUN pip install -e .
```

### 2. Security

```dockerfile
# ✅ SPRÁVNĚ - Non-root user
USER sukl

# ❌ ŠPATNĚ - Root user
# USER root  # Nevyužívej!
```

### 3. Cache management

```bash
# ✅ SPRÁVNĚ - Persistent volume
docker run -v ./data:/tmp/sukl_dlp_cache sukl-mcp

# ❌ ŠPATNĚ - Efemérní storage (data se ztratí při restartu)
docker run sukl-mcp
```

### 4. Resource limits

```yaml
# ✅ SPRÁVNĚ - Rozumné limity
resources:
  memory: "512Mi"  # Dostatečné pro pandas
  cpu: "500m"

# ❌ ŠPATNĚ - Příliš nízké limity
resources:
  memory: "128Mi"  # Nedostatečné pro pandas!
```

### 5. Logging

```python
# ✅ SPRÁVNĚ - Structured logging
logger.info("Server started", extra={"transport": "http", "port": 8000})

# ❌ ŠPATNĚ - Print statements
print("Server started")  # Nebude v Smithery logs!
```

## 🔄 CI/CD Integrace

### GitHub Actions

```yaml
name: Deploy to Smithery

on:
  push:
    branches: [main]
    paths:
      - 'sukl_mcp/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build and test
        run: |
          # Project is now in repository root
          docker build -t sukl-mcp:test .
          docker run -d -p 8000:8000 -e MCP_TRANSPORT=http sukl-mcp:test
          sleep 10
          curl -f http://localhost:8000/health

      - name: Install Smithery CLI
        run: npm install -g smithery

      - name: Deploy to Smithery
        run: |
          # Project is now in repository root
          smithery deploy --token ${{ secrets.SMITHERY_TOKEN }}
        env:
          SMITHERY_TOKEN: ${{ secrets.SMITHERY_TOKEN }}
```

## 📚 Další zdroje

- [Smithery Documentation](https://smithery.ai/docs)
- [Smithery Registry](https://smithery.ai/registry)
- [FastMCP Documentation](https://gofastmcp.com)
- [SÚKL Open Data](https://opendata.sukl.cz)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🆘 Podpora

Máš problémy s deploymentem?

1. **Zkontroluj logy**: `smithery logs --tail 200` nebo `docker logs <container_id>`
2. **Validuj lokálně**: `docker build . && docker run -p 8000:8000 -e MCP_TRANSPORT=http <image>`
3. **Otevři issue**: https://github.com/your-org/fastmcp-boilerplate/issues
4. **Smithery Discord**: https://discord.gg/smithery

---

**Poslední aktualizace:** 28. prosince 2024
**Smithery CLI verze:** 1.0+
**Docker verze:** 20.10+
**Python verze:** 3.10+
