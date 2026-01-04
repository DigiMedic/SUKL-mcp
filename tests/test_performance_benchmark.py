"""
Performance Benchmark Test Suite pro SÚKL MCP v4.0.0.

Měří a porovnává výkon REST API vs CSV fallback pro hybridní operace.

Spuštění:
    pytest tests/test_performance_benchmark.py -v -s

Export výsledků:
    pytest tests/test_performance_benchmark.py -v -s > benchmark_results.txt
"""

import asyncio
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any
from unittest.mock import patch

import pytest

from sukl_mcp.api import get_api_client
from sukl_mcp.client_csv import get_sukl_client
from sukl_mcp.server import _try_rest_search, _try_rest_get_detail, mcp, server_lifespan
from sukl_mcp.exceptions import SUKLAPIError


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BenchmarkResult:
    """Výsledky jednoho benchmark testu."""

    # Identifikace
    operation: str        # "search_medicine" | "get_medicine_details" | "check_availability"
    mode: str            # "rest_api" | "csv_fallback" | "hybrid_workflow"
    scenario: str        # "cold_start" | "warm_cache" | "batch" | "fallback"

    # Základní metriky
    total_runs: int
    successful_runs: int
    failed_runs: int

    # Latence (ms) - raw data
    latencies: list[float] = field(default_factory=list)

    # Latence percentily
    p50_latency: float = 0.0   # Median
    p95_latency: float = 0.0   # 95th percentile
    p99_latency: float = 0.0   # 99th percentile
    mean_latency: float = 0.0
    min_latency: float = 0.0
    max_latency: float = 0.0

    # Throughput
    duration_seconds: float = 0.0
    throughput_ops_per_sec: float = 0.0

    # Cache & Error metrics
    cache_hit_rate: float | None = None  # % (pouze pro REST API)
    error_rate: float = 0.0               # % failed runs

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    notes: str | None = None


# ============================================================================
# Benchmark Runner
# ============================================================================

class BenchmarkRunner:
    """Orchestrator pro spouštění benchmark testů."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []
        self.api_client = None
        self.csv_client = None
        self._start_time: float = 0

    async def setup(self):
        """Initialize clients, clear caches."""
        self.api_client = await get_api_client()
        self.csv_client = await get_sukl_client()

        # Clear REST API cache for clean start
        if hasattr(self.api_client, '_cache'):
            self.api_client._cache.clear()

        self._start_time = time.perf_counter()

    async def teardown(self):
        """Cleanup resources."""
        if self.api_client:
            await self.api_client.close()

    async def run_benchmark(
        self,
        operation: str,
        mode: str,
        scenario: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict | None = None,
        iterations: int = 10,
    ) -> BenchmarkResult:
        """
        Spustí benchmark pro danou operaci.

        Process:
        1. Record cache stats before
        2. Run iterations with timing
        3. Calculate percentiles (p50, p95, p99)
        4. Calculate throughput
        5. Calculate cache hit rate & error rate
        6. Return BenchmarkResult
        """
        if kwargs is None:
            kwargs = {}

        latencies: list[float] = []
        successful_runs = 0
        failed_runs = 0

        # Cache stats BEFORE benchmark
        cache_before = None
        if self.api_client and hasattr(self.api_client, 'get_cache_stats'):
            cache_before = self.api_client.get_cache_stats()

        # === START BENCHMARK ===
        start_time = time.perf_counter()

        for i in range(iterations):
            run_start = time.perf_counter()

            try:
                # Execute async function
                result = await func(*args, **kwargs)

                run_end = time.perf_counter()
                latency_ms = (run_end - run_start) * 1000  # Convert to ms
                latencies.append(latency_ms)
                successful_runs += 1

            except Exception as e:
                print(f"  ⚠️  Run {i+1}/{iterations} failed: {e}")
                failed_runs += 1

        end_time = time.perf_counter()
        duration = end_time - start_time

        # === CALCULATE METRICS ===

        # Percentiles
        if latencies:
            p50 = self.calculate_percentile(latencies, 50)
            p95 = self.calculate_percentile(latencies, 95)
            p99 = self.calculate_percentile(latencies, 99)
            mean = statistics.mean(latencies)
            min_lat = min(latencies)
            max_lat = max(latencies)
        else:
            p50 = p95 = p99 = mean = min_lat = max_lat = 0.0

        # Throughput
        throughput = successful_runs / duration if duration > 0 else 0

        # Cache hit rate (only for REST API mode)
        cache_hit_rate = None
        if cache_before and self.api_client and mode == "rest_api":
            cache_after = self.api_client.get_cache_stats()
            # Simple heuristic: valid entries / total entries
            if cache_after['total_entries'] > 0:
                cache_hit_rate = (cache_after['valid_entries'] / cache_after['total_entries']) * 100

        # Error rate
        error_rate = (failed_runs / iterations * 100) if iterations > 0 else 0

        # === CREATE RESULT ===
        result = BenchmarkResult(
            operation=operation,
            mode=mode,
            scenario=scenario,
            total_runs=iterations,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            latencies=latencies,
            p50_latency=p50,
            p95_latency=p95,
            p99_latency=p99,
            mean_latency=mean,
            min_latency=min_lat,
            max_latency=max_lat,
            duration_seconds=duration,
            throughput_ops_per_sec=throughput,
            cache_hit_rate=cache_hit_rate,
            error_rate=error_rate,
        )

        # Log immediate feedback
        print(f"  ✅ {mode} ({scenario}): {p50:.0f}ms (p50), {successful_runs}/{iterations} success")

        return result

    def calculate_percentile(self, values: list[float], percentile: int) -> float:
        """Vypočítá percentil z hodnot (50, 95, 99)."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]

    def generate_report(self) -> str:
        """
        Generuje přehledný tabulkový report s ASCII art.
        """
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("SÚKL MCP Performance Benchmark v4.0.0".center(70))
        report_lines.append("=" * 70)
        report_lines.append(f"Run timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # Group results by operation
        operations = {}
        for result in self.results:
            if result.operation not in operations:
                operations[result.operation] = []
            operations[result.operation].append(result)

        # Generate operation sections
        for operation, results in operations.items():
            report_lines.append("┌" + "─" * 68 + "┐")
            report_lines.append(f"│ {operation.upper().ljust(66)} │")
            report_lines.append("├" + "─" * 68 + "┤")

            # Group by scenario
            scenarios = {}
            for result in results:
                if result.scenario not in scenarios:
                    scenarios[result.scenario] = []
                scenarios[result.scenario].append(result)

            for scenario, scenario_results in scenarios.items():
                scenario_title = scenario.replace('_', ' ').title()
                report_lines.append(f"│ Scenario: {scenario_title.ljust(59)} │")

                for result in scenario_results:
                    mode_label = result.mode.replace('_', ' ').title() + ":"
                    latency_str = f"{result.p50_latency:.0f}ms (p50), {result.p95_latency:.0f}ms (p95), {result.p99_latency:.0f}ms (p99)"
                    line = f"│   {mode_label.ljust(20)} {latency_str.ljust(44)} │"
                    report_lines.append(line)

                # Calculate winner (if comparing 2+ modes)
                if len(scenario_results) >= 2:
                    fastest = min(scenario_results, key=lambda r: r.p50_latency)
                    slowest = max(scenario_results, key=lambda r: r.p50_latency)
                    if slowest.p50_latency > 0:
                        speedup = slowest.p50_latency / fastest.p50_latency
                        winner_mode = fastest.mode.replace('_', ' ').title()
                        winner_line = f"│   Winner: {winner_mode} {speedup:.1f}x faster (p50)".ljust(69) + "│"
                        report_lines.append(winner_line)

                report_lines.append("│" + " " * 68 + "│")

            report_lines.append("└" + "─" * 68 + "┘")
            report_lines.append("")

        # Add cache statistics
        if self.api_client and hasattr(self.api_client, 'get_cache_stats'):
            cache_stats = self.api_client.get_cache_stats()
            report_lines.append("┌" + "─" * 68 + "┐")
            report_lines.append(f"│ CACHE STATISTICS".ljust(69) + "│")
            report_lines.append("├" + "─" * 68 + "┤")
            report_lines.append(f"│ Total Cache Entries: {cache_stats['total_entries']}".ljust(69) + "│")
            report_lines.append(f"│ Valid Entries: {cache_stats['valid_entries']}".ljust(69) + "│")
            report_lines.append(f"│ Stale Entries: {cache_stats['stale_entries']}".ljust(69) + "│")
            report_lines.append("└" + "─" * 68 + "┘")
            report_lines.append("")

        # Summary statistics
        total_ops = sum(r.total_runs for r in self.results)
        total_duration = sum(r.duration_seconds for r in self.results)
        avg_throughput = total_ops / total_duration if total_duration > 0 else 0

        report_lines.append("┌" + "─" * 68 + "┐")
        report_lines.append(f"│ SUMMARY".ljust(69) + "│")
        report_lines.append("├" + "─" * 68 + "┤")
        report_lines.append(f"│ Total Operations: {total_ops}".ljust(69) + "│")
        report_lines.append(f"│ Total Duration: {total_duration:.1f}s".ljust(69) + "│")
        report_lines.append(f"│ Average Throughput: {avg_throughput:.1f} ops/sec".ljust(69) + "│")
        report_lines.append("└" + "─" * 68 + "┘")

        return "\n".join(report_lines)


# ============================================================================
# Benchmark Tests
# ============================================================================

@pytest.mark.asyncio
async def test_benchmark_search_medicine():
    """Benchmark search_medicine: REST API vs CSV."""
    async with server_lifespan(mcp):
        runner = BenchmarkRunner()
        await runner.setup()

        test_query = "PARALEN"
        iterations = 10  # Zkráceno pro rychlejší běh

        print("\n" + "=" * 70)
        print("BENCHMARK: search_medicine")
        print("=" * 70)

        # === SCENARIO 1: Cold Start ===
        print("\n[1/2] Cold Start (prázdná cache)...")

        # 1a) REST API - cold cache
        if hasattr(runner.api_client, '_cache'):
            runner.api_client._cache.clear()
        result_rest_cold = await runner.run_benchmark(
            operation="search_medicine",
            mode="rest_api",
            scenario="cold_start",
            func=_try_rest_search,
            args=(test_query, 10),
            iterations=iterations
        )

        # 1b) CSV - cold
        result_csv_cold = await runner.run_benchmark(
            operation="search_medicine",
            mode="csv_fallback",
            scenario="cold_start",
            func=runner.csv_client.search_medicines,
            args=(test_query, 10),
            iterations=iterations
        )

        # === SCENARIO 2: Warm Cache ===
        print("\n[2/2] Warm Cache (opakované volání)...")

        # 2a) REST API - warm cache
        result_rest_warm = await runner.run_benchmark(
            operation="search_medicine",
            mode="rest_api",
            scenario="warm_cache",
            func=_try_rest_search,
            args=(test_query, 10),
            iterations=iterations
        )

        # 2b) CSV - warm cache
        result_csv_warm = await runner.run_benchmark(
            operation="search_medicine",
            mode="csv_fallback",
            scenario="warm_cache",
            func=runner.csv_client.search_medicines,
            args=(test_query, 10),
            iterations=iterations
        )

        # Store results
        runner.results.extend([
            result_rest_cold, result_csv_cold,
            result_rest_warm, result_csv_warm,
        ])

        # Print report
        print("\n" + runner.generate_report())

        await runner.teardown()


@pytest.mark.asyncio
async def test_benchmark_get_medicine_details():
    """Benchmark get_medicine_details: REST + CSV enrichment."""
    async with server_lifespan(mcp):
        runner = BenchmarkRunner()
        await runner.setup()

        test_code = "0254045"  # PARALEN
        iterations = 10

        print("\n" + "=" * 70)
        print("BENCHMARK: get_medicine_details")
        print("=" * 70)

        # === SCENARIO 1: REST Detail (cold) ===
        print("\n[1/3] REST API Detail (cold cache)...")
        if hasattr(runner.api_client, '_cache'):
            runner.api_client._cache.clear()

        result_rest_cold = await runner.run_benchmark(
            operation="get_medicine_details",
            mode="rest_api",
            scenario="cold_start",
            func=_try_rest_get_detail,
            args=(test_code,),
            iterations=iterations
        )

        # === SCENARIO 2: CSV Detail ===
        print("\n[2/3] CSV Detail (local cache)...")

        result_csv_cold = await runner.run_benchmark(
            operation="get_medicine_details",
            mode="csv_fallback",
            scenario="cold_start",
            func=runner.csv_client.get_medicine_detail,
            args=(test_code,),
            iterations=iterations
        )

        # === SCENARIO 3: Hybrid Workflow (REST + CSV price enrichment) ===
        print("\n[3/3] Hybrid Workflow (REST + CSV price)...")

        async def hybrid_get_detail():
            # Step 1: Try REST for basic data
            data = await _try_rest_get_detail(test_code)

            # Step 2: Fallback to CSV if REST fails
            if data is None:
                data = await runner.csv_client.get_medicine_detail(test_code)

            # Step 3: ALWAYS enrich with CSV price data
            price_info = await runner.csv_client.get_price_info(test_code)

            return data, price_info

        result_hybrid = await runner.run_benchmark(
            operation="get_medicine_details",
            mode="hybrid_workflow",
            scenario="rest_plus_csv_enrichment",
            func=hybrid_get_detail,
            args=(),
            iterations=iterations
        )

        # Store results
        runner.results.extend([
            result_rest_cold, result_csv_cold,
            result_hybrid
        ])

        # Print report
        print("\n" + runner.generate_report())

        await runner.teardown()


@pytest.mark.asyncio
async def test_benchmark_check_availability():
    """Benchmark check_availability: REST vs CSV + alternatives."""
    async with server_lifespan(mcp):
        runner = BenchmarkRunner()
        await runner.setup()

        test_code = "0254045"  # PARALEN
        iterations = 10

        print("\n" + "=" * 70)
        print("BENCHMARK: check_availability")
        print("=" * 70)

        # === SCENARIO 1: REST API Availability Check ===
        print("\n[1/3] REST API Availability Check...")

        async def rest_availability():
            detail = await _try_rest_get_detail(test_code)
            if detail:
                is_available = detail.get("DODAVKY") == "1"
                return is_available
            return None

        result_rest = await runner.run_benchmark(
            operation="check_availability",
            mode="rest_api",
            scenario="availability_check",
            func=rest_availability,
            args=(),
            iterations=iterations
        )

        # === SCENARIO 2: CSV Availability Check ===
        print("\n[2/3] CSV Availability Check...")

        async def csv_availability():
            detail = await runner.csv_client.get_medicine_detail(test_code)
            if detail:
                is_available = runner.csv_client._normalize_availability(detail.get("DODAVKY"))
                return is_available
            return None

        result_csv = await runner.run_benchmark(
            operation="check_availability",
            mode="csv_fallback",
            scenario="availability_check",
            func=csv_availability,
            args=(),
            iterations=iterations
        )

        # === SCENARIO 3: Full Workflow (with alternatives) ===
        print("\n[3/3] Full Availability Workflow (with alternatives)...")

        async def full_availability_workflow():
            # Step 1: Get availability
            detail = await _try_rest_get_detail(test_code)
            if detail is None:
                detail = await runner.csv_client.get_medicine_detail(test_code)

            # Step 2: Normalize availability
            from sukl_mcp.models import AvailabilityStatus
            is_available = runner.csv_client._normalize_availability(detail.get("DODAVKY"))

            # Step 3: If unavailable, find alternatives
            alternatives = []
            if is_available != AvailabilityStatus.AVAILABLE:
                alternatives = await runner.csv_client.find_generic_alternatives(test_code, limit=3)

            return is_available, alternatives

        result_full = await runner.run_benchmark(
            operation="check_availability",
            mode="hybrid_workflow",
            scenario="with_alternatives",
            func=full_availability_workflow,
            args=(),
            iterations=iterations
        )

        # Store results
        runner.results.extend([result_rest, result_csv, result_full])

        # Print report
        print("\n" + runner.generate_report())

        await runner.teardown()


if __name__ == "__main__":
    print("Run tests with: pytest tests/test_performance_benchmark.py -v -s")
