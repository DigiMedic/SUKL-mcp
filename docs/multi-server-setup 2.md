# Multi-Server Setup Guide

Tento návod ti ukáže, jak používat SÚKL MCP Server společně s dalšími MCP servery v Claude Desktop.

## 📋 Přehled

Claude Desktop podporuje současné používání více MCP serverů. Každý server poskytuje své vlastní tools a resources, které Claude může používat.

## 🚀 Quick Setup

### 1. Najdi konfigurační soubor

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

### 2. Zkopíruj příklad konfigurace

V kořenovém adresáři projektu najdeš `claude_desktop_config.example.json`. Tento soubor můžeš použít jako výchozí bod.

### 3. Uprav cesty a klíče

Otevři svůj `claude_desktop_config.json` a uprav:
- **YOURUSER** → tvoje uživatelské jméno
- **API klíče** → tvoje skutečné API klíče pro jednotlivé služby
- **Cesty** → správné cesty k adresářům

## 📦 Dostupné MCP Servery

### SÚKL MCP Server (tento projekt)

**Co poskytuje:**
- 🔍 Vyhledávání léčivých přípravků (68,248 záznamů)
- 📄 Parsování dokumentů (PIL/SPC)
- 💰 Cenové údaje a úhrady
- 🔄 Inteligentní alternativy při nedostupnosti

**Konfigurace:**
```json
{
  "sukl": {
    "command": "python",
    "args": ["-m", "sukl_mcp"],
    "env": {
      "PYTHONPATH": "/cesta/k/SUKL-mcp/src",
      "SUKL_LOG_LEVEL": "INFO"
    }
  }
}
```

**Poznámky:**
- Vyžaduje Python 3.10+
- Automaticky stahuje data ze SÚKL Open Data
- První spuštění trvá ~30s (stahování + inicializace)

---

### Filesystem Server

**Co poskytuje:**
- 📂 Čtení a zápis souborů
- 📁 Procházení adresářů
- 🔍 Vyhledávání souborů

**Instalace:**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**Konfigurace:**
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/cesta/k/adresari"],
    "env": {}
  }
}
```

**Bezpečnost:**
- ⚠️ Server má přístup POUZE k adresáři uvedenému v konfiguraci
- Doporučujeme omezit na konkrétní projektové adresáře
- Nikdy nepovoluj přístup k root adresáři nebo home složce!

---

### Brave Search Server

**Co poskytuje:**
- 🔍 Web search přes Brave Search API
- 📰 Aktuální informace z internetu
- 🔒 Privacy-focused vyhledávání

**Získání API klíče:**
1. Jdi na https://brave.com/search/api/
2. Zaregistruj se a vytvoř API klíč
3. Free tier: 2,000 dotazů/měsíc

**Konfigurace:**
```json
{
  "brave-search": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-brave-search"],
    "env": {
      "BRAVE_API_KEY": "tvůj-brave-api-klíč"
    }
  }
}
```

---

### GitHub Server

**Co poskytuje:**
- 📦 Práce s repositories
- 🔍 Vyhledávání v GitHub
- 📝 Issues a Pull Requests management
- 📊 Repository statistics

**Získání tokenu:**
1. Jdi na https://github.com/settings/tokens
2. Generate new token (classic)
3. Vyber scopes: `repo`, `read:org`, `read:user`
4. Zkopíruj token

**Konfigurace:**
```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_tvůj_token_zde"
    }
  }
}
```

---

### PostgreSQL Server

**Co poskytuje:**
- 🗄️ Dotazy do PostgreSQL databáze
- 📊 Schema inspection
- 📝 Query execution

**Konfigurace:**
```json
{
  "postgres": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-postgres",
      "postgresql://user:password@localhost:5432/database"
    ],
    "env": {}
  }
}
```

**Connection String format:**
```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Bezpečnost:**
- ⚠️ Nikdy necommituj connection string s hesly!
- Používej read-only uživatele pro dotazy
- Omezte přístup na konkrétní tabulky

---

### Slack Server

**Co poskytuje:**
- 💬 Čtení a psaní zpráv
- 📢 Channels management
- 👥 Users a teams info

**Získání tokenu:**
1. Jdi na https://api.slack.com/apps
2. Create New App → From scratch
3. Add Bot Token Scopes: `channels:read`, `chat:write`, `users:read`
4. Install to Workspace
5. Zkopíruj Bot User OAuth Token

**Konfigurace:**
```json
{
  "slack": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "xoxb-tvůj-token",
      "SLACK_TEAM_ID": "T01234567"
    }
  }
}
```

---

## 🎯 Doporučené kombinace

### Pro vývoj softwaru:
```json
{
  "mcpServers": {
    "sukl": { /* farmaceutická data */ },
    "filesystem": { /* local files */ },
    "github": { /* code repositories */ },
    "postgres": { /* database access */ }
  }
}
```

### Pro výzkum a analýzu:
```json
{
  "mcpServers": {
    "sukl": { /* farmaceutická data */ },
    "brave-search": { /* web research */ },
    "filesystem": { /* local data */ }
  }
}
```

### Pro týmovou spolupráci:
```json
{
  "mcpServers": {
    "sukl": { /* farmaceutická data */ },
    "slack": { /* team communication */ },
    "github": { /* code collaboration */ }
  }
}
```

---

## 🔧 Troubleshooting

### Server se nespustí

**Kontrola logů:**
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp*.log

# Windows
type %APPDATA%\Claude\Logs\mcp*.log

# Linux
tail -f ~/.config/Claude/logs/mcp*.log
```

**Časté problémy:**

1. **Python not found**
   ```bash
   # Ověř Python instalaci
   python3 --version
   which python3
   ```

2. **Module not found**
   ```bash
   # Aktivuj virtual environment
   cd /cesta/k/SUKL-mcp
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Permission denied**
   ```bash
   # Oprav permissions
   chmod +x /cesta/k/skriptu
   ```

4. **API key invalid**
   - Ověř že klíč není expirovaný
   - Zkontroluj že má správné permissions
   - Restartuj Claude Desktop po změně

### Server běží, ale tools nefungují

**Kontrola:**
1. Restart Claude Desktop (kompletně zavřít aplikaci)
2. Ověř syntax JSON konfigurace (použij JSON validator)
3. Zkontroluj že všechny required ENV proměnné jsou nastavené
4. Zkus server spustit manuálně:
   ```bash
   python -m sukl_mcp  # Pro SÚKL server
   npx @modelcontextprotocol/server-github  # Pro GitHub server
   ```

---

## 📚 Další MCP servery

### Oficiální servery od Anthropic:
- **@modelcontextprotocol/server-sqlite** - SQLite databáze
- **@modelcontextprotocol/server-puppeteer** - Web scraping
- **@modelcontextprotocol/server-google-maps** - Google Maps API
- **@modelcontextprotocol/server-memory** - Persistent memory

### Community servery:
Najdeš je na:
- https://github.com/modelcontextprotocol
- https://www.npmjs.com/search?q=mcp-server
- https://pypi.org/search/?q=mcp-server

---

## 🔒 Best Practices

### Bezpečnost

1. **API klíče:**
   - ❌ Nikdy necommituj do Git
   - ✅ Používej `.env` soubory nebo secrets management
   - ✅ Rotuj klíče pravidelně

2. **Filesystem přístup:**
   - ❌ Nepovoluj přístup k root nebo home
   - ✅ Omezte na konkrétní projekty
   - ✅ Používej read-only režim kde možné

3. **Database přístup:**
   - ❌ Nepoužívej admin účty
   - ✅ Vytvoř read-only uživatele
   - ✅ Omezte přístup na potřebné tabulky

### Performance

1. **Počet serverů:**
   - Více serverů = delší startup Claude Desktop
   - Doporučujeme max 5-7 aktivních serverů
   - Deaktivuj nepoužívané servery

2. **Resource management:**
   - SÚKL server používá ~360 MB RAM
   - Každý server má svůj overhead
   - Monitoruj celkovou paměť

### Organizace

1. **Naming convention:**
   ```json
   {
     "project-filesystem": { /* Pro konkrétní projekt */ },
     "global-github": { /* Global GitHub access */ },
     "dev-postgres": { /* Development DB */ },
     "prod-postgres": { /* Production DB (read-only!) */ }
   }
   ```

2. **Komentáře:**
   - JSON nepodporuje komentáře natívně
   - Používej description fields kde možné
   - Udržuj separátní dokumentaci

---

## 📞 Support

- **SÚKL MCP Server issues:** https://github.com/your-org/SUKL-mcp/issues
- **FastMCP documentation:** https://gofastmcp.com
- **MCP Protocol spec:** https://modelcontextprotocol.io

---

**Příklad vytvořen:** 2026-01-01
**FastMCP verze:** 2.14+
**Claude Desktop:** 2024+
