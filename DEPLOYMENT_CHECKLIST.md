# Deployment Checklist - SÚKL MCP Server v2.1.0

Tento checklist ti pomůže ověřit, že server je připraven pro nasazení na FastMCP Cloud i Smithery.

## ✅ Pre-deployment validace

### 1. Základní kontroly

- [ ] **Verze konzistence**
  ```bash
  # Zkontroluj, že všechny verze jsou 2.1.0
  grep -n "version" pyproject.toml src/sukl_mcp/__init__.py fastmcp.yaml smithery.yaml Dockerfile
  ```

- [ ] **Dependencies nainstalované**
  ```bash
  # Project is now in repository root
  pip install -e ".[dev]"
  ```

- [ ] **Testy procházejí**
  ```bash
  pytest tests/ -v
  # Očekáváno: 23 testů PASSED
  ```

- [ ] **Type checking**
  ```bash
  mypy src/sukl_mcp/ --ignore-missing-imports
  # Očekáváno: Success: no issues found
  ```

- [ ] **Linting**
  ```bash
  ruff check src/
  black --check src/
  ```

### 2. Server funkčnost

- [ ] **STDIO mode (FastMCP Cloud)**
  ```bash
  # Spuštění
  unset MCP_TRANSPORT
  python -m sukl_mcp &
  PID=$!
  sleep 3

  # Validace
  ps -p $PID > /dev/null && echo "✓ Server běží" || echo "✗ Server neběží"

  # Cleanup
  kill $PID
  ```

- [ ] **HTTP mode (Smithery)**
  ```bash
  # Spuštění
  export MCP_TRANSPORT=http
  export MCP_PORT=8000
  python -m sukl_mcp &
  PID=$!
  sleep 5

  # Health check
  curl -f http://localhost:8000/health && echo "✓ Health check OK" || echo "✗ Health check failed"

  # Cleanup
  kill $PID
  unset MCP_TRANSPORT MCP_PORT
  ```

### 3. Import validace

- [ ] **Python importy**
  ```bash
  python -c "from sukl_mcp.server import mcp; print(f'✓ Server version: {mcp.version}')"
  python -c "from sukl_mcp import __version__; print(f'✓ Package version: {__version__}')"
  python -c "from sukl_mcp.client_csv import SUKLClient; print('✓ Client import OK')"
  python -c "from sukl_mcp.exceptions import SUKLException; print('✓ Exceptions import OK')"
  ```

## 🐳 Docker validace (pro Smithery)

### 4. Docker build

- [ ] **Build image**
  ```bash
  # Project is now in repository root
  docker build -t sukl-mcp:2.1.0 .
  # Očekáváno: Build úspěšný
  ```

- [ ] **Image size check**
  ```bash
  docker images sukl-mcp:2.1.0
  # Očekáváno: ~200-350 MB
  ```

- [ ] **Multi-stage optimization**
  ```bash
  # Zkontroluj, že builder stage není v final image
  docker history sukl-mcp:2.1.0 | grep builder
  # Očekáváno: žádný výsledek (builder stage odstraněn)
  ```

### 5. Container runtime

- [ ] **Container spuštění**
  ```bash
  docker run -d -p 8000:8000 \
    -e MCP_TRANSPORT=http \
    --name sukl-test \
    sukl-mcp:2.1.0

  sleep 10
  ```

- [ ] **Health check**
  ```bash
  curl -f http://localhost:8000/health
  # Očekáváno: {"status":"healthy"}
  ```

- [ ] **Logs validation**
  ```bash
  docker logs sukl-test 2>&1 | grep "Starting SÚKL MCP Server"
  # Očekáváno: Vidíš startup message
  ```

- [ ] **Non-root user**
  ```bash
  docker exec sukl-test whoami
  # Očekáváno: sukl (ne root!)
  ```

- [ ] **Environment variables**
  ```bash
  docker exec sukl-test printenv | grep SUKL
  # Očekáváno: SUKL_CACHE_DIR, SUKL_DATA_DIR, atd.
  ```

- [ ] **Cleanup**
  ```bash
  docker stop sukl-test
  docker rm sukl-test
  ```

## ☁️ FastMCP Cloud validace

### 6. FastMCP konfigurace

- [ ] **fastmcp.yaml syntax**
  ```bash
  # Zkontroluj YAML syntax
  python -c "import yaml; yaml.safe_load(open('fastmcp.yaml'))" && echo "✓ YAML valid"
  ```

- [ ] **Module path správný**
  ```bash
  grep "module: sukl_mcp.server" fastmcp.yaml
  # Očekáváno: Absolutní import path
  ```

- [ ] **Dependencies kompletní**
  ```bash
  # Zkontroluj, že všechny dependencies jsou v fastmcp.yaml
  grep -A 10 "dependencies:" fastmcp.yaml
  # Očekáváno: fastmcp, httpx, pydantic, pandas
  ```

### 7. FastMCP CLI validace

- [ ] **FastMCP CLI nainstalováno**
  ```bash
  fastmcp --version
  # Očekáváno: verze >= 2.14.0
  ```

- [ ] **Lokální test (pokud máš FastMCP CLI)**
  ```bash
  # Spuštění v dev módu
  # Project is now in repository root
  fastmcp dev
  # Zkontroluj, že server startuje bez chyb
  ```

## 🔨 Smithery validace

### 8. Smithery konfigurace

- [ ] **smithery.yaml syntax**
  ```bash
  python -c "import yaml; yaml.safe_load(open('smithery.yaml'))" && echo "✓ YAML valid"
  ```

- [ ] **Runtime je 'container'**
  ```bash
  grep "runtime: \"container\"" smithery.yaml
  # Očekáváno: runtime: "container"
  ```

- [ ] **ConfigSchema validní JSON Schema**
  ```bash
  python -c "
import yaml
config = yaml.safe_load(open('smithery.yaml'))
schema = config['startCommand']['configSchema']
assert schema['type'] == 'object'
assert 'properties' in schema
print('✓ ConfigSchema valid')
"
  ```

### 9. Smithery CLI validace (pokud máš)

- [ ] **Smithery CLI nainstalováno**
  ```bash
  smithery --version
  # Očekáváno: Smithery CLI verze
  ```

- [ ] **Smithery validate**
  ```bash
  # Project is now in repository root
  smithery validate
  # Očekáváno: Configuration is valid
  ```

## 📚 Dokumentace

### 10. Dokumentace kompletnost

- [ ] **README.md obsahuje oba deploymenty**
  ```bash
  grep -q "Nasazení na Smithery" README.md && echo "✓ Smithery v README"
  grep -q "FastMCP Cloud" README.md && echo "✓ FastMCP v README"
  ```

- [ ] **DEPLOYMENT.md aktuální**
  ```bash
  grep -q "Smithery Platform" DEPLOYMENT.md && echo "✓ Smithery v DEPLOYMENT"
  ```

- [ ] **SMITHERY_DEPLOYMENT.md existuje**
  ```bash
  test -f SMITHERY_DEPLOYMENT.md && echo "✓ SMITHERY_DEPLOYMENT.md existuje"
  ```

- [ ] **CHANGELOG.md verze 2.1.0**
  ```bash
  grep -q "\[2.1.0\]" ../CHANGELOG.md && echo "✓ CHANGELOG aktuální"
  ```

## 🚀 Deployment

### FastMCP Cloud

```bash
# 1. Přihlášení
fastmcp login

# 2. Deploy
fastmcp deploy

# 3. Verify
fastmcp status
fastmcp logs --tail 50
```

### Smithery

```bash
# 1. Build a test lokálně
docker build -t sukl-mcp:2.1.0 .
docker run -p 8000:8000 -e MCP_TRANSPORT=http sukl-mcp:2.1.0

# 2. Deploy na Smithery
smithery login
smithery deploy

# 3. Verify
smithery status
smithery logs --tail 50
```

## ✅ Final checklist

Po úspěšném nasazení zkontroluj:

- [ ] Server běží na obou platformách
- [ ] Health checks procházejí
- [ ] MCP tools jsou dostupné
- [ ] Logs neobsahují errors
- [ ] Data se načítají správně (SÚKL Open Data)
- [ ] Performance je přijatelný
- [ ] Dokumentace je aktuální

## 🆘 Troubleshooting

Pokud něco nefunguje:

1. **Zkontroluj logs**: `docker logs <container>` nebo `fastmcp logs`
2. **Validuj lokálně**: Vždy otestuj lokálně před cloud deploymentem
3. **Checklist výše**: Projdi všechny kroky znovu
4. **Dokumentace**:
   - FastMCP Cloud: `DEPLOYMENT.md`
   - Smithery: `SMITHERY_DEPLOYMENT.md`
5. **GitHub Issues**: Otevři issue s logs a popisem problému

---

**Verze:** 2.1.0
**Datum:** 28. prosince 2024
**Platformy:** FastMCP Cloud + Smithery
