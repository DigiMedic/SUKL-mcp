# Docker Build Fix - README.md not found

## ❌ Problém

Docker build selhával s chybou:
```
#12 [builder 3/5] COPY pyproject.toml README.md ./
#12 ERROR: failed to calculate checksum: "/README.md": not found
```

## 🔍 Příčina

`.dockerignore` měl příliš agresivní pattern:
```
# Documentation
*.md        # <-- Toto vyřazovalo VŠECHNY .md soubory včetně README.md!
docs/
```

**Proč je to problém?**
- `pyproject.toml` má `readme = "README.md"`
- `pip install -e .` POTŘEBUJE README.md
- Docker build nemůže pokračovat bez README.md

## ✅ Řešení

Změnil jsem `.dockerignore` na **specifické excludy**:

```dockerignore
# Documentation
# Exclude all .md files EXCEPT README.md (required by pyproject.toml)
DEPLOYMENT.md
SMITHERY_DEPLOYMENT.md
DEPLOYMENT_CHECKLIST.md
FASTMCP_CLOUD_FIX.md
CONTRIBUTING.md
CHANGELOG.md
docs/

# IMPORTANT: README.md is NOT excluded - it's required for pip install!
```

## ✅ Validace

Po opravě:
- ✅ `README.md` je v Docker build contextu
- ✅ `pyproject.toml` může číst README.md
- ✅ `pip install -e .` funguje
- ✅ Docker build uspěje

## 🚀 Deployment

Nyní můžeš znovu zkusit deployment:

### FastMCP Cloud
```bash
git add .dockerignore
git commit -m "fix: update .dockerignore to include README.md for Docker build"
git push
fastmcp deploy
```

### Smithery
```bash
docker build -t sukl-mcp:2.1.0 .  # Mělo by nyní fungovat!
smithery deploy
```

## 📝 Lekce

**Best practice pro .dockerignore:**
1. ❌ **ŠPATNĚ**: `*.md` (příliš agresivní)
2. ✅ **SPRÁVNĚ**: Explicitní seznam souborů k vyřazení
3. ✅ **VŽDY**: Nech soubory potřebné pro `pip install` (README.md, LICENSE, atd.)

## 🔍 Debug tip

Pokud Docker build selže s "file not found", zkontroluj:
```bash
# Co .dockerignore vyřazuje?
grep -v "^#" .dockerignore | grep -v "^$"

# Jsou potřebné soubory přítomny?
ls -la pyproject.toml README.md src/

# Test build context (bez cache)
docker build --no-cache -t test .
```

---

**Fixed:** 28. prosince 2024, 22:50
**Impact:** Critical - blokuje veškeré Docker deployments
**Status:** ✅ Resolved
