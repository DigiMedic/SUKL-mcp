"""Testy async I/O a race conditions."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sukl_mcp.client_csv import SUKLClient, get_sukl_client
from sukl_mcp.exceptions import SUKLZipBombError


class TestRaceConditionPrevention:
    """Testy ochrany proti race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_get_sukl_client(self):
        """Paralelní volání get_sukl_client() by měla vrátit stejnou instanci."""
        # Reset globální klient
        import sukl_mcp.client_csv as module

        module._client = None

        # Mock initialize() aby nemusel stahovat data
        with patch.object(SUKLClient, "initialize", new_callable=AsyncMock):
            # Paralelní volání
            clients = await asyncio.gather(
                get_sukl_client(),
                get_sukl_client(),
                get_sukl_client(),
                get_sukl_client(),
                get_sukl_client(),
            )

            # Všechny by měly být stejná instance
            first_client = clients[0]
            for client in clients[1:]:
                assert (
                    client is first_client
                ), "get_sukl_client() by měl vracet stejnou instanci při paralelních voláních"

        # Cleanup
        module._client = None

    @pytest.mark.asyncio
    async def test_initialize_called_once(self):
        """initialize() by měl být zavolán pouze jednou i při paralelních voláních."""
        import sukl_mcp.client_csv as module

        module._client = None

        # Mock initialize() a počítej kolikrát je volán
        initialize_call_count = 0

        async def mock_initialize(self):
            nonlocal initialize_call_count
            initialize_call_count += 1
            await asyncio.sleep(0.01)  # Simulace async práce

        with patch.object(SUKLClient, "initialize", new=mock_initialize):
            # Paralelní volání
            await asyncio.gather(
                get_sukl_client(),
                get_sukl_client(),
                get_sukl_client(),
            )

            # initialize() by měl být zavolán pouze jednou díky asyncio.Lock
            assert (
                initialize_call_count == 1
            ), f"initialize() byl zavolán {initialize_call_count}x místo 1x"

        # Cleanup
        module._client = None


class TestAsyncIOBehavior:
    """Testy async I/O chování."""

    @pytest.mark.asyncio
    async def test_zip_extraction_is_async(self):
        """_extract_zip() by měl být async a neblokovat event loop."""
        from sukl_mcp.client_csv import SUKLDataLoader, SUKLConfig

        config = SUKLConfig()
        loader = SUKLDataLoader(config)

        # Mock zipfile.ZipFile aby nemusel existovat skutečný ZIP
        mock_zip = MagicMock()
        mock_zip.__enter__ = MagicMock(return_value=mock_zip)
        mock_zip.__exit__ = MagicMock(return_value=None)
        mock_zip.infolist.return_value = [
            MagicMock(file_size=1000),
            MagicMock(file_size=2000),
        ]
        mock_zip.extractall = MagicMock()

        with patch("zipfile.ZipFile", return_value=mock_zip):
            # Test že _extract_zip je async funkce
            result = loader._extract_zip(Path("/fake/path.zip"))
            assert asyncio.iscoroutine(
                result
            ), "_extract_zip() by měl vrátit coroutine"

            # Cleanup coroutine
            try:
                await result
            except:
                pass

    @pytest.mark.asyncio
    async def test_csv_loading_is_parallel(self):
        """_load_csvs() by měl načítat CSV soubory paralelně."""
        from sukl_mcp.client_csv import SUKLDataLoader, SUKLConfig

        config = SUKLConfig()
        loader = SUKLDataLoader(config)

        # Mock csv files existence
        with patch.object(Path, "exists", return_value=True):
            # Mock pd.read_csv aby sledoval pořadí volání
            import pandas as pd

            call_order = []

            def mock_read_csv(*args, **kwargs):
                table_name = args[0].stem if args else "unknown"
                call_order.append(table_name)
                # Simulace async práce
                import time

                time.sleep(0.01)
                return pd.DataFrame()

            with patch("pandas.read_csv", side_effect=mock_read_csv):
                # Mock executor to ensure it's being used
                original_gather = asyncio.gather

                gather_was_called = False

                async def mock_gather(*args, **kwargs):
                    nonlocal gather_was_called
                    gather_was_called = True
                    return await original_gather(*args, **kwargs)

                with patch("asyncio.gather", side_effect=mock_gather):
                    await loader._load_csvs()

                # Ověř že asyncio.gather byl použit (znamená paralelní loading)
                assert (
                    gather_was_called
                ), "_load_csvs() by měl používat asyncio.gather() pro paralelní načítání"


class TestZipBombProtection:
    """Testy ochrany proti ZIP bombs."""

    @pytest.mark.asyncio
    async def test_zip_bomb_detection(self):
        """Příliš velký ZIP by měl být odmítnut."""
        from sukl_mcp.client_csv import SUKLDataLoader, SUKLConfig

        config = SUKLConfig()
        loader = SUKLDataLoader(config)

        # Mock velmi velký ZIP (6 GB)
        mock_zip = MagicMock()
        mock_zip.__enter__ = MagicMock(return_value=mock_zip)
        mock_zip.__exit__ = MagicMock(return_value=None)
        mock_zip.infolist.return_value = [
            MagicMock(file_size=6 * 1024 * 1024 * 1024)  # 6 GB
        ]

        with patch("zipfile.ZipFile", return_value=mock_zip):
            with pytest.raises(SUKLZipBombError, match="ZIP příliš velký"):
                await loader._extract_zip(Path("/fake/bomb.zip"))

    @pytest.mark.asyncio
    async def test_acceptable_zip_size(self):
        """ZIP do 5 GB by měl projít."""
        from sukl_mcp.client_csv import SUKLDataLoader, SUKLConfig

        config = SUKLConfig()
        loader = SUKLDataLoader(config)

        # Mock přijatelně velký ZIP (200 MB)
        mock_zip = MagicMock()
        mock_zip.__enter__ = MagicMock(return_value=mock_zip)
        mock_zip.__exit__ = MagicMock(return_value=None)
        mock_zip.infolist.return_value = [
            MagicMock(file_size=200 * 1024 * 1024)  # 200 MB
        ]
        mock_zip.extractall = MagicMock()

        # Mock Path.mkdir aby netvořil skutečné adresáře
        with patch.object(Path, "mkdir"):
            with patch("zipfile.ZipFile", return_value=mock_zip):
                # Neměl by hodit SUKLZipBombError
                try:
                    await loader._extract_zip(Path("/fake/ok.zip"))
                except SUKLZipBombError:
                    pytest.fail(
                        "ZIP o velikosti 200 MB by neměl být odmítnut jako ZIP bomb"
                    )


class TestEnvironmentConfiguration:
    """Testy konfigurace přes ENV variables."""

    def test_env_override_cache_dir(self):
        """ENV proměnná SUKL_CACHE_DIR by měla přepsat default."""
        import os

        from sukl_mcp.client_csv import SUKLConfig

        # Set ENV variable
        os.environ["SUKL_CACHE_DIR"] = "/custom/cache"

        try:
            config = SUKLConfig()
            assert str(config.cache_dir) == "/custom/cache"
        finally:
            # Cleanup
            del os.environ["SUKL_CACHE_DIR"]

    def test_env_override_timeout(self):
        """ENV proměnná SUKL_DOWNLOAD_TIMEOUT by měla přepsat default."""
        import os

        from sukl_mcp.client_csv import SUKLConfig

        os.environ["SUKL_DOWNLOAD_TIMEOUT"] = "300.0"

        try:
            config = SUKLConfig()
            assert config.download_timeout == 300.0
        finally:
            del os.environ["SUKL_DOWNLOAD_TIMEOUT"]
