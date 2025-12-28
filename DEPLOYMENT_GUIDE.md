# FastMCP Cloud Deployment Guide

## ✅ Příprava (Hotovo)

Projekt je připraven pro deployment:
- ✅ `pyproject.toml` v root repozitáře
- ✅ `fastmcp.yaml` s konfigurací
- ✅ Všechny dependencies specifikované
- ✅ Správná struktura projektu

## 🚀 Deployment Steps

### 1. Push do GitHubu

```bash
# Commit změny
git add -A
git commit -m "refactor: restructure project for FastMCP Cloud deployment

- Move all files from sukl_mcp/ to repository root
- Fix pyproject.toml location for dependency detection
- Update all documentation references
- Ready for FastMCP Cloud deployment"

# Push na GitHub
git push origin start

# Merge do main branch (nebo vytvoř PR)
git checkout main
git merge start
git push origin main
```

### 2. Připojení na FastMCP Cloud

1. **Přihlaš se**: https://fastmcp.cloud/
   - Sign in with GitHub
   
2. **Vytvoř projekt**:
   - "Create New Project"
   - Select repository: `fastmcp-boilerplate`
   - Branch: `main`
   
3. **Automatický build**:
   - FastMCP Cloud detekuje `pyproject.toml`
   - Nainstaluje dependencies
   - Build a deploy serveru

### 3. Výsledek

Server bude dostupný na:
```
https://your-project-name.fastmcp.app/mcp
```

## 🔄 Automatické redeploy

- **Push do main** → automatický redeploy
- **Pull Request** → preview deployment na unikátní URL
- **Monitoring** přes FastMCP Cloud dashboard

## 📝 Environment Variables

Pokud potřebuješ nastavit ENV proměnné:
1. FastMCP Cloud dashboard
2. Project Settings
3. Environment Variables
4. Přidej:
   - `SUKL_CACHE_DIR`
   - `SUKL_DATA_DIR`
   - `SUKL_DOWNLOAD_TIMEOUT`

## 🆘 Troubleshooting

**Problem**: Build selhal  
**Solution**: Zkontroluj build logs v FastMCP Cloud dashboard

**Problem**: Import error  
**Solution**: Ověř, že `pyproject.toml` obsahuje všechny dependencies

**Problem**: Server neodpovídá  
**Solution**: Zkontroluj logs - možná timeout při stahování SÚKL dat

## 📚 Zdroje

- [FastMCP Cloud Docs](https://gofastmcp.com/deployment/fastmcp-cloud)
- [Deployment Tutorial](https://www.deeplearningnerds.com/how-to-deploy-your-fastmcp-server-on-fastmcp-cloud/)
- [FastMCP Cloud Dashboard](https://fastmcp.cloud/)

---

**Status**: ✅ Projekt je připraven pro deployment
**Next Step**: Push do GitHub a připojení na FastMCP Cloud
