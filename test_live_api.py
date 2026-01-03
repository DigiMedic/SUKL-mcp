"""
Testovací skript pro ověření živého volání SÚKL REST API.

Spustit: python test_live_api.py
"""

import asyncio
from sukl_mcp.api import SUKLAPIClient


async def main():
    print("🔍 Test SÚKL REST API klienta\n")
    print("=" * 60)

    async with SUKLAPIClient() as client:
        # Health check
        print("\n1️⃣ Health Check:")
        health = await client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Latency: {health.get('latency_ms', 'N/A')}ms")
        print(f"   Sample: {health.get('sample_medicine', 'N/A')}")

        # Search
        print("\n2️⃣ Vyhledávání léčiv (PARALEN):")
        search = await client.search_medicines("PARALEN", limit=3)
        print(f"   Nalezeno: {search.total} výsledků")
        print(f"   Kódy: {', '.join(search.codes[:3])}")

        # Get detail
        if search.codes:
            print(f"\n3️⃣ Detail léčiva ({search.codes[0]}):")
            medicine = await client.get_medicine(search.codes[0])
            if medicine:
                print(f"   Název: {medicine.nazev}")
                print(f"   Síla: {medicine.sila}")
                print(f"   Forma: {medicine.lekovaFormaKod}")
                print(f"   ATC: {medicine.ATCkod}")
                print(f"   Dostupné: {'✅ Ano' if medicine.jeDodavka else '❌ Ne'}")

        # Batch fetch
        print("\n4️⃣ Batch fetch (3 léčiv):")
        batch_codes = search.codes[:3] if len(search.codes) >= 3 else search.codes
        batch = await client.get_medicines_batch(batch_codes, max_concurrent=2)
        print(f"   Načteno: {len(batch)} léčiv")
        for med in batch:
            print(f"   - {med.nazev} ({med.kodSUKL})")

        # Cache stats
        print("\n5️⃣ Cache statistiky:")
        stats = client.get_cache_stats()
        print(f"   Celkem entries: {stats['total_entries']}")
        print(f"   Platné: {stats['valid_entries']}")
        print(f"   Expirované: {stats['stale_entries']}")

    print("\n" + "=" * 60)
    print("✅ Všechny testy úspěšně dokončeny!")


if __name__ == "__main__":
    asyncio.run(main())
