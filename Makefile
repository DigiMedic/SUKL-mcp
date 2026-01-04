.PHONY: help install test lint format clean run api-test api-health

help:
	@echo "SÚKL MCP Server v4.0 - Makefile příkazy"
	@echo ""
	@echo "  make install    - Instalace projektu s dev závislostmi"
	@echo "  make test       - Spuštění testů"
	@echo "  make test-cov   - Spuštění testů s coverage"
	@echo "  make lint       - Kontrola kódu (ruff, mypy)"
	@echo "  make format     - Formátování kódu (black)"
	@echo "  make clean      - Vyčištění build artifacts"
	@echo "  make run        - Spuštění MCP serveru"
	@echo ""
	@echo "  API Development:"
	@echo "  make api-test   - Spuštění integračních testů REST API"
	@echo "  make api-health - Rychlá kontrola dostupnosti SÚKL API"
	@echo ""

install:
	@echo "📦 Instalace projektu..."
	pip install -e ".[dev]"
	@echo "✅ Instalace dokončena"

test:
	@echo "🧪 Spouštění testů..."
	pytest tests/ -v
	@echo "✅ Testy dokončeny"

test-cov:
	@echo "🧪 Spouštění testů s coverage..."
	pytest tests/ -v --cov=sukl_mcp --cov-report=term-missing
	@echo "✅ Testy s coverage dokončeny"

lint:
	@echo "🔍 Kontrola kódu..."
	@echo "  → ruff check..."
	ruff check src/
	@echo "  → mypy type checking..."
	mypy src/sukl_mcp/
	@echo "✅ Kontrola dokončena"

format:
	@echo "✨ Formátování kódu..."
	black src/ tests/
	@echo "✅ Formátování dokončeno"

clean:
	@echo "🧹 Čištění build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Čištění dokončeno"

run:
	@echo "🚀 Spouštění SÚKL MCP serveru..."
	python -m sukl_mcp

dev:
	@echo "🛠️  Vývojový režim - formátování + testy + lint..."
	@make format
	@make test
	@make lint
	@echo "✅ Vše hotovo!"
# === API Development ===

api-test:
	@echo "🌐 Spouštění integračních testů REST API..."
	pytest tests/test_api_client.py -v -m integration
	@echo "✅ Integrační testy dokončeny"

api-health:
	@echo "🏥 Kontrola dostupnosti SÚKL REST API..."
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\nLatency: %{time_total}s\n" \
		"https://prehledy.sukl.cz/dlp/v1/lecive-pripravky/0254045"
	@echo "✅ API je dostupné"