# Přispívání do SÚKL MCP Server

Děkujeme za zájem o přispění do projektu! Tato příručka vám pomůže začít.

## 🚀 Jak začít

### 1. Fork a Clone

```bash
# Fork repozitář na GitHubu
# Pak naklonuj svůj fork
git clone https://github.com/your-username/fastmcp-boilerplate.git
cd fastmcp-boilerplate
```

### 2. Nastavení vývojového prostředí

```bash
# Vytvoř virtuální prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalace s dev závislostmi
pip install -e ".[dev]"
```

### 3. Vytvoř novou branch

```bash
git checkout -b feature/moje-nova-funkce
# nebo
git checkout -b fix/oprava-bugu
```

## 📝 Code Style

### Formátování

Projekt používá **black** s max line length 100:

```bash
black src/ tests/
```

### Linting

Používáme **ruff** pro kontrolu kvality kódu:

```bash
ruff check src/
```

### Type Checking

Všechen kód musí projít **mypy**:

```bash
mypy src/sukl_mcp/
```

### Pre-commit Hook

Doporučujeme použít Makefile příkaz před commitem:

```bash
make dev  # formátování + testy + linting
```

## 🧪 Testování

### Spuštění testů

```bash
# Všechny testy
pytest tests/ -v

# S coverage reportem
pytest tests/ -v --cov=src/sukl_mcp --cov-report=term-missing

# Konkrétní test
pytest tests/test_validation.py -v
```

### Psaní testů

Všechny nové funkce musí mít testy:

```python
import pytest
from sukl_mcp.exceptions import SUKLValidationError

@pytest.mark.asyncio
async def test_my_new_feature():
    """Test description."""
    # Arrange
    client = SUKLClient()

    # Act
    result = await client.my_method()

    # Assert
    assert result is not None
```

### Test Coverage

Minimální coverage je **80%**. Nové kódy by měly mít **90%+** coverage.

## 📖 Dokumentace

### Docstrings

Používej Google style docstrings:

```python
async def search_medicines(query: str, limit: int = 20) -> list[dict]:
    """Vyhledá léčivé přípravky podle názvu.

    Args:
        query: Hledaný text (název, účinná látka).
        limit: Maximální počet výsledků (default: 20).

    Returns:
        Seznam slovníků s léčivými přípravky.

    Raises:
        SUKLValidationError: Pokud je query neplatný.
    """
```

### README Updates

Pokud přidáváš novou funkci, aktualizuj:
- `README.md` - hlavní dokumentace
- `CLAUDE.md` - pokyny pro AI asistenty
- `CHANGELOG.md` - záznam změn

## ✅ Checklist před Pull Request

- [ ] Kód prošel `black` formátováním
- [ ] Kód prošel `ruff` lintingem
- [ ] Kód prošel `mypy` type checkingem
- [ ] Všechny testy prošly (`pytest tests/ -v`)
- [ ] Přidal/a jsi testy pro nový kód
- [ ] Coverage je ≥ 80%
- [ ] Aktualizoval/a jsi dokumentaci
- [ ] Přidal/a jsi záznam do CHANGELOG.md
- [ ] Commit messages jsou v konvenčním formátu

## 📋 Commit Message Format

Používáme [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types:
- `feat:` - Nová funkce
- `fix:` - Oprava bugu
- `docs:` - Změny v dokumentaci
- `test:` - Přidání nebo úprava testů
- `refactor:` - Refaktoring kódu
- `perf:` - Zlepšení výkonu
- `chore:` - Build, deps, config

### Příklady:

```bash
git commit -m "feat(client): add pagination support to search_medicines"

git commit -m "fix(validation): prevent regex injection in search query"

git commit -m "docs(readme): update installation instructions"
```

## 🔄 Pull Request Process

1. **Updatuj svou branch** s nejnovějším `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Push do svého forku**:
   ```bash
   git push origin feature/moje-nova-funkce
   ```

3. **Vytvoř Pull Request** na GitHubu:
   - Vyplň template (popis, motivace, testy)
   - Přilinkuj související issues
   - Přidej screenshots (pokud je to UI změna)

4. **Code Review**:
   - Odpovídej na komentáře
   - Dělej změny podle feedbacku
   - Označ reviewery když jsou změny hotové

5. **Merge**:
   - Po schválení bude PR mergnut
   - Tvoje branch bude smazána

## 🐛 Reporting Bugs

Pokud najdeš bug:

1. Zkontroluj, jestli už není [reported](https://github.com/your-org/fastmcp-boilerplate/issues)
2. Vytvoř nový issue s:
   - Popisem problému
   - Kroky k reprodukci
   - Očekávané vs. aktuální chování
   - Python verze, OS, environment
   - Traceback (pokud existuje)

## 💡 Feature Requests

Pro návrhy nových funkcí:

1. Vytvoř issue s tagem `enhancement`
2. Popiš:
   - Jakou funkci chceš
   - Proč je užitečná
   - Jak by mohla fungovat
   - Alternativní řešení

## 📜 Code of Conduct

- Buď respektující a inkluzivní
- Přijímej konstruktivní kritiku
- Zaměř se na to, co je nejlepší pro komunitu
- Ukazuj empatii vůči ostatním

## 🙏 Poděkování

Děkujeme všem přispěvatelům za pomoc s vylepšováním SÚKL MCP Server!

---

**Máš otázky?** Otevři [discussion](https://github.com/your-org/fastmcp-boilerplate/discussions) nebo se zeptej v issues.
