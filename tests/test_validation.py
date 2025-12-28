"""Testy input validace."""

import pytest

from sukl_mcp.client_csv import SUKLClient
from sukl_mcp.exceptions import SUKLValidationError


class TestSearchMedicinesValidation:
    """Testy validace search_medicines."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Prázdný query by měl vyhodit SUKLValidationError."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="Query nesmí být prázdný"):
            await client.search_medicines("")

    @pytest.mark.asyncio
    async def test_whitespace_only_query(self):
        """Query obsahující pouze whitespace by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="Query nesmí být prázdný"):
            await client.search_medicines("   ")

    @pytest.mark.asyncio
    async def test_query_too_long(self):
        """Query delší než 200 znaků by měl vyhodit chybu."""
        client = SUKLClient()
        long_query = "a" * 201
        with pytest.raises(SUKLValidationError, match="Query příliš dlouhý"):
            await client.search_medicines(long_query)

    @pytest.mark.asyncio
    async def test_limit_too_low(self):
        """Limit < 1 by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="Limit musí být 1-100"):
            await client.search_medicines("aspirin", limit=0)

    @pytest.mark.asyncio
    async def test_limit_too_high(self):
        """Limit > 100 by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="Limit musí být 1-100"):
            await client.search_medicines("aspirin", limit=101)

    @pytest.mark.asyncio
    async def test_valid_query_with_whitespace(self):
        """Query s leading/trailing whitespace by měl být oříznut."""
        client = SUKLClient()
        # Nemělo by vyhodit chybu, jen ořízne whitespace
        # (Tohle testuje že validace prošla, ne že našla výsledky)
        try:
            await client.search_medicines("  aspirin  ", limit=5)
        except SUKLValidationError:
            pytest.fail("Validace by neměla selhat pro platný query s whitespace")


class TestGetMedicineDetailValidation:
    """Testy validace get_medicine_detail."""

    @pytest.mark.asyncio
    async def test_empty_sukl_code(self):
        """Prázdný SÚKL kód by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="SÚKL kód nesmí být prázdný"):
            await client.get_medicine_detail("")

    @pytest.mark.asyncio
    async def test_whitespace_only_sukl_code(self):
        """SÚKL kód obsahující pouze whitespace by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="SÚKL kód nesmí být prázdný"):
            await client.get_medicine_detail("   ")

    @pytest.mark.asyncio
    async def test_non_numeric_sukl_code(self):
        """Non-numeric SÚKL kód by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="SÚKL kód musí být číselný"):
            await client.get_medicine_detail("abc123")

    @pytest.mark.asyncio
    async def test_sukl_code_too_long(self):
        """SÚKL kód delší než 7 znaků by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="SÚKL kód příliš dlouhý"):
            await client.get_medicine_detail("12345678")

    @pytest.mark.asyncio
    async def test_valid_sukl_code(self):
        """Platný SÚKL kód by neměl vyhodit validační chybu."""
        client = SUKLClient()
        # Nemělo by vyhodit SUKLValidationError
        try:
            await client.get_medicine_detail("254045")
        except SUKLValidationError:
            pytest.fail("Validace by neměla selhat pro platný SÚKL kód")


class TestGetATCGroupsValidation:
    """Testy validace get_atc_groups."""

    @pytest.mark.asyncio
    async def test_atc_prefix_too_long(self):
        """ATC prefix delší než 7 znaků by měl vyhodit chybu."""
        client = SUKLClient()
        with pytest.raises(SUKLValidationError, match="ATC prefix příliš dlouhý"):
            await client.get_atc_groups("A01BC234")

    @pytest.mark.asyncio
    async def test_valid_atc_prefix(self):
        """Platný ATC prefix by neměl vyhodit chybu."""
        client = SUKLClient()
        try:
            await client.get_atc_groups("A01")
        except SUKLValidationError:
            pytest.fail("Validace by neměla selhat pro platný ATC prefix")

    @pytest.mark.asyncio
    async def test_none_atc_prefix(self):
        """None ATC prefix by měl být platný (vrátí všechny)."""
        client = SUKLClient()
        try:
            await client.get_atc_groups(None)
        except SUKLValidationError:
            pytest.fail("Validace by neměla selhat pro None ATC prefix")


class TestRegexInjectionPrevention:
    """Testy ochrany proti regex injection."""

    @pytest.mark.asyncio
    async def test_regex_special_characters(self):
        """Regex speciální znaky by neměly způsobit regex chybu."""
        client = SUKLClient()
        # Tyto znaky by normálně vyhodily regex chybu pokud by byly interpretovány jako regex
        special_queries = [
            ".*",  # Match anything
            "[abc",  # Unclosed bracket
            "(test",  # Unclosed paren
            "test|",  # OR operator
            "^test$",  # Anchors
        ]

        for query in special_queries:
            try:
                await client.search_medicines(query, limit=5)
                # Pokud to nehodí chybu, regex=False funguje
            except SUKLValidationError:
                # Validační chyba je OK (např. prázdný query)
                pass
            except Exception as e:
                # Jakákoliv jiná chyba (např. regex error) znamená že ochrana nefunguje
                pytest.fail(
                    f"Query '{query}' způsobil neočekávanou chybu: {e}. "
                    "Regex injection protection možná nefunguje."
                )
