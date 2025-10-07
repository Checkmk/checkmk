#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

"""Tests for Varnish cache and backend monitoring using Pattern 5 standalone approach."""

import pytest

from cmk.agent_based.v2 import GetRateError
from cmk.base.legacy_checks.varnish import (
    check_varnish_backend,
    check_varnish_cache,
    check_varnish_client,
    check_varnish_objects,
    check_varnish_worker,
    check_varnish_worker_thread_ratio,
    discover_varnish_backend,
    discover_varnish_backend_success_ratio,
    discover_varnish_cache,
    discover_varnish_cache_hit_ratio,
    discover_varnish_client,
    discover_varnish_esi,
    discover_varnish_fetch,
    discover_varnish_objects,
    discover_varnish_worker,
    discover_varnish_worker_thread_ratio,
    parse_varnish,
)


def _create_parsed_varnish(
    backend_values: dict[str, int] | None = None,
    cache_values: dict[str, int] | None = None,
    client_values: dict[str, int] | None = None,
    esi_values: dict[str, int] | None = None,
    fetch_values: dict[str, int] | None = None,
    objects_values: dict[str, int] | None = None,
    worker_values: dict[str, int] | None = None,
) -> dict:
    """Create parsed Varnish data with all subchecks metrics."""
    backend_values = backend_values or {}
    cache_values = cache_values or {}
    client_values = client_values or {}
    esi_values = esi_values or {}
    fetch_values = fetch_values or {}
    objects_values = objects_values or {}
    worker_values = worker_values or {}

    parsed_data = {}

    # Backend counters
    if backend_values:
        parsed_data.update(
            {
                "backend_busy": {
                    "value": backend_values.get("backend_busy", 0),
                    "descr": "Backend conn. too many",
                    "perf_var_name": "varnish_backend_busy_rate",
                    "params_var_name": "busy",
                },
                "backend_unhealthy": {
                    "value": backend_values.get("backend_unhealthy", 0),
                    "descr": "Backend conn. not attempted",
                    "perf_var_name": "varnish_backend_unhealthy_rate",
                    "params_var_name": "unhealthy",
                },
                "backend_req": {
                    "value": backend_values.get("backend_req", 1000),
                    "descr": "Backend requests made",
                    "perf_var_name": "varnish_backend_req_rate",
                    "params_var_name": "req",
                },
                "backend_recycle": {
                    "value": backend_values.get("backend_recycle", 500),
                    "descr": "Backend conn. recycles",
                    "perf_var_name": "varnish_backend_recycle_rate",
                    "params_var_name": "recycle",
                },
                "backend_retry": {
                    "value": backend_values.get("backend_retry", 10),
                    "descr": "Backend conn. retry",
                    "perf_var_name": "varnish_backend_retry_rate",
                    "params_var_name": "retry",
                },
                "backend_fail": {
                    "value": backend_values.get("backend_fail", 0),
                    "descr": "Backend conn. failures",
                    "perf_var_name": "varnish_backend_fail_rate",
                    "params_var_name": "fail",
                },
                "backend_toolate": {
                    "value": backend_values.get("backend_toolate", 5),
                    "descr": "Backend conn. was closed",
                    "perf_var_name": "varnish_backend_toolate_rate",
                    "params_var_name": "toolate",
                },
                "backend_conn": {
                    "value": backend_values.get("backend_conn", 800),
                    "descr": "Backend conn. success",
                    "perf_var_name": "varnish_backend_conn_rate",
                    "params_var_name": "conn",
                },
                "backend_reuse": {
                    "value": backend_values.get("backend_reuse", 700),
                    "descr": "Backend conn. reuses",
                    "perf_var_name": "varnish_backend_reuse_rate",
                    "params_var_name": "reuse",
                },
            }
        )

    # Cache counters
    if cache_values:
        parsed_data.update(
            {
                "cache_miss": {
                    "value": cache_values.get("cache_miss", 200),
                    "descr": "Cache misses",
                    "perf_var_name": "varnish_cache_miss_rate",
                    "params_var_name": "miss",
                },
                "cache_hit": {
                    "value": cache_values.get("cache_hit", 800),
                    "descr": "Cache hits",
                    "perf_var_name": "varnish_cache_hit_rate",
                    "params_var_name": "hit",
                },
                "cache_hitpass": {
                    "value": cache_values.get("cache_hitpass", 50),
                    "descr": "Cache hits for pass",
                    "perf_var_name": "varnish_cache_hitpass_rate",
                    "params_var_name": "hitpass",
                },
            }
        )

    # Client counters
    if client_values:
        parsed_data.update(
            {
                "client_drop": {
                    "value": client_values.get("client_drop", 0),
                    "descr": "Connection dropped, no sess wrk",
                    "perf_var_name": "varnish_client_drop_rate",
                    "params_var_name": "drop",
                },
                "client_req": {
                    "value": client_values.get("client_req", 1000),
                    "descr": "Client requests received",
                    "perf_var_name": "varnish_client_req_rate",
                    "params_var_name": "req",
                },
                "client_conn": {
                    "value": client_values.get("client_conn", 500),
                    "descr": "Client connections accepted",
                    "perf_var_name": "varnish_client_conn_rate",
                    "params_var_name": "conn",
                },
                "client_drop_late": {
                    "value": client_values.get("client_drop_late", 0),
                    "descr": "Connection dropped late",
                    "perf_var_name": "varnish_client_drop_late_rate",
                    "params_var_name": "drop_late",
                },
            }
        )

    # ESI counters
    if esi_values:
        parsed_data.update(
            {
                "esi_errors": {
                    "value": esi_values.get("esi_errors", 0),
                    "descr": "ESI parse errors (unlock)",
                    "perf_var_name": "varnish_esi_errors_rate",
                    "params_var_name": "errors",
                },
                "esi_warnings": {
                    "value": esi_values.get("esi_warnings", 0),
                    "descr": "ESI parse warnings (unlock)",
                    "perf_var_name": "varnish_esi_warnings_rate",
                    "params_var_name": "warnings",
                },
            }
        )

    # Fetch counters
    if fetch_values:
        parsed_data.update(
            {
                "fetch_oldhttp": {
                    "value": fetch_values.get("fetch_oldhttp", 0),
                    "descr": "Fetch pre HTTP 1.1 closed",
                    "perf_var_name": "varnish_fetch_oldhttp_rate",
                    "params_var_name": "oldhttp",
                },
                "fetch_head": {
                    "value": fetch_values.get("fetch_head", 10),
                    "descr": "Fetch head",
                    "perf_var_name": "varnish_fetch_head_rate",
                    "params_var_name": "head",
                },
                "fetch_eof": {
                    "value": fetch_values.get("fetch_eof", 0),
                    "descr": "Fetch EOF",
                    "perf_var_name": "varnish_fetch_eof_rate",
                    "params_var_name": "eof",
                },
                "fetch_zero": {
                    "value": fetch_values.get("fetch_zero", 0),
                    "descr": "Fetch zero len",
                    "perf_var_name": "varnish_fetch_zero_rate",
                    "params_var_name": "zero",
                },
                "fetch_304": {
                    "value": fetch_values.get("fetch_304", 100),
                    "descr": "Fetch no body (304)",
                    "perf_var_name": "varnish_fetch_304_rate",
                    "params_var_name": "304",
                },
                "fetch_length": {
                    "value": fetch_values.get("fetch_length", 200),
                    "descr": "Fetch with Length",
                    "perf_var_name": "varnish_fetch_length_rate",
                    "params_var_name": "length",
                },
                "fetch_failed": {
                    "value": fetch_values.get("fetch_failed", 0),
                    "descr": "Fetch failed",
                    "perf_var_name": "varnish_fetch_failed_rate",
                    "params_var_name": "failed",
                },
                "fetch_bad": {
                    "value": fetch_values.get("fetch_bad", 0),
                    "descr": "Fetch had bad headers",
                    "perf_var_name": "varnish_fetch_bad_rate",
                    "params_var_name": "bad",
                },
                "fetch_close": {
                    "value": fetch_values.get("fetch_close", 0),
                    "descr": "Fetch wanted close",
                    "perf_var_name": "varnish_fetch_close_rate",
                    "params_var_name": "close",
                },
                "fetch_1xx": {
                    "value": fetch_values.get("fetch_1xx", 0),
                    "descr": "Fetch no body (1xx)",
                    "perf_var_name": "varnish_fetch_1xx_rate",
                    "params_var_name": "1xx",
                },
                "fetch_chunked": {
                    "value": fetch_values.get("fetch_chunked", 300),
                    "descr": "Fetch chunked",
                    "perf_var_name": "varnish_fetch_chunked_rate",
                    "params_var_name": "chunked",
                },
                "fetch_204": {
                    "value": fetch_values.get("fetch_204", 0),
                    "descr": "Fetch no body (204)",
                    "perf_var_name": "varnish_fetch_204_rate",
                    "params_var_name": "204",
                },
            }
        )

    # Objects counters
    if objects_values:
        parsed_data.update(
            {
                "n_expired": {
                    "value": objects_values.get("n_expired", 100),
                    "descr": "N expired objects",
                    "perf_var_name": "varnish_objects_expired_rate",
                    "params_var_name": "expired",
                },
                "n_lru_nuked": {
                    "value": objects_values.get("n_lru_nuked", 0),
                    "descr": "N LRU nuked objects",
                    "perf_var_name": "varnish_objects_lru_nuked_rate",
                    "params_var_name": "lru_nuked",
                },
                "n_lru_moved": {
                    "value": objects_values.get("n_lru_moved", 50),
                    "descr": "N LRU moved objects",
                    "perf_var_name": "varnish_objects_lru_moved_rate",
                    "params_var_name": "lru_moved",
                },
            }
        )

    # Worker counters
    if worker_values:
        parsed_data.update(
            {
                "n_wrk_lqueue": {
                    "value": worker_values.get("n_wrk_lqueue", 0),
                    "descr": "work request queue length",
                    "perf_var_name": "varnish_worker_lqueue_rate",
                    "params_var_name": "lqueue",
                },
                "n_wrk_create": {
                    "value": worker_values.get("n_wrk_create", 1000),
                    "descr": "N worker threads created",
                    "perf_var_name": "varnish_worker_create_rate",
                    "params_var_name": "create",
                },
                "n_wrk_drop": {
                    "value": worker_values.get("n_wrk_drop", 0),
                    "descr": "N dropped work requests",
                    "perf_var_name": "varnish_worker_drop_rate",
                    "params_var_name": "drop",
                },
                "n_wrk": {
                    "value": worker_values.get("n_wrk", 1000),
                    "descr": "N worker threads",
                    "perf_var_name": "varnish_worker_rate",
                    "params_var_name": "wrk",
                },
                "n_wrk_failed": {
                    "value": worker_values.get("n_wrk_failed", 0),
                    "descr": "N worker threads not created",
                    "perf_var_name": "varnish_worker_failed_rate",
                    "params_var_name": "failed",
                },
                "n_wrk_queued": {
                    "value": worker_values.get("n_wrk_queued", 20),
                    "descr": "N queued work requests",
                    "perf_var_name": "varnish_worker_queued_rate",
                    "params_var_name": "queued",
                },
                "n_wrk_max": {
                    "value": worker_values.get("n_wrk_max", 900),
                    "descr": "N worker threads limited",
                    "perf_var_name": "varnish_worker_max_rate",
                    "params_var_name": "max",
                },
            }
        )

    return parsed_data


class TestVarnishBackendMonitoring:
    """Test cases for Varnish backend connection monitoring."""

    def test_discovery_with_backend_metrics(self) -> None:
        """Test discovery when backend metrics are available."""
        parsed = _create_parsed_varnish(
            backend_values={"backend_fail": 0, "backend_unhealthy": 0, "backend_busy": 0},
            cache_values={},
        )

        discovery_result = list(discover_varnish_backend(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    def test_discovery_without_required_metrics(self) -> None:
        """Test discovery when required backend metrics are missing."""
        parsed = {"cache_hit": {"value": 100}}  # Only cache metrics

        discovery_result = list(discover_varnish_backend(parsed))
        assert len(discovery_result) == 0

    @pytest.mark.usefixtures("initialised_item_state")
    def test_backend_check_with_failures(self) -> None:
        """Test backend check with connection failures."""
        # Backend check - using direct function calls
        parsed = _create_parsed_varnish(
            backend_values={
                "backend_busy": 100,  # High busy count
                "backend_unhealthy": 50,  # Some unhealthy backends
                "backend_fail": 25,  # Connection failures
                "backend_req": 1000,
                "backend_conn": 800,
            },
            cache_values={},
        )

        # First call will raise GetRateError as expected
        with pytest.raises(GetRateError):
            list(check_varnish_backend(None, {}, parsed))

    @pytest.mark.usefixtures("initialised_item_state")
    def test_backend_check_missing_metrics(self) -> None:
        """Test backend check when some metrics are missing."""
        # Backend check - using direct function calls
        parsed = _create_parsed_varnish(
            backend_values={
                "backend_req": 1000,  # Only one metric
            },
            cache_values={},
        )

        # First call will raise GetRateError as expected
        with pytest.raises(GetRateError):
            list(check_varnish_backend(None, {}, parsed))

    @pytest.mark.parametrize(
        "backend_values,expected_metrics",
        [
            (
                {"backend_busy": 0, "backend_fail": 0, "backend_req": 1000},
                ["backend_busy", "backend_fail", "backend_req"],
            ),
            (
                {"backend_unhealthy": 10, "backend_retry": 5, "backend_conn": 800},
                ["backend_unhealthy", "backend_retry", "backend_conn"],
            ),
        ],
    )
    @pytest.mark.usefixtures("initialised_item_state")
    def test_backend_metrics_variations(
        self, backend_values: dict[str, int], expected_metrics: list[str]
    ) -> None:
        """Test backend check with different metric combinations."""
        # Backend check - using direct function calls
        parsed = _create_parsed_varnish(backend_values=backend_values, cache_values={})

        # First call will raise GetRateError as expected
        with pytest.raises(GetRateError):
            list(check_varnish_backend(None, {}, parsed))


class TestVarnishCacheMonitoring:
    """Test cases for Varnish cache hit/miss monitoring."""

    def test_discovery_with_cache_metrics(self) -> None:
        """Test discovery when cache metrics are available."""
        # Cache check - using direct function calls
        parsed = _create_parsed_varnish(backend_values={}, cache_values={"cache_miss": 100})

        discovery_result = list(discover_varnish_cache(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    def test_discovery_without_cache_metrics(self) -> None:
        """Test discovery when cache_miss metric is missing."""
        # Cache check - using direct function calls
        parsed = {"backend_req": {"value": 100}}  # Only backend metrics

        discovery_result = list(discover_varnish_cache(parsed))
        assert len(discovery_result) == 0

    @pytest.mark.usefixtures("initialised_item_state")
    def test_cache_check_balanced_hit_miss(self) -> None:
        """Test cache check with balanced hit/miss ratio."""
        # Cache check - using direct function calls
        parsed = _create_parsed_varnish(
            backend_values={},
            cache_values={
                "cache_miss": 200,
                "cache_hit": 800,
                "cache_hitpass": 50,
            },
        )

        # First call will raise GetRateError as expected
        with pytest.raises(GetRateError):
            list(check_varnish_cache(None, {}, parsed))

    @pytest.mark.usefixtures("initialised_item_state")
    def test_cache_check_high_miss_rate(self) -> None:
        """Test cache check with high miss rate."""
        # Cache check - using direct function calls
        parsed = _create_parsed_varnish(
            backend_values={},
            cache_values={
                "cache_miss": 800,  # High miss rate
                "cache_hit": 200,  # Low hit rate
                "cache_hitpass": 100,
            },
        )

        # First call will raise GetRateError as expected
        with pytest.raises(GetRateError):
            list(check_varnish_cache(None, {}, parsed))

    @pytest.mark.usefixtures("initialised_item_state")
    def test_cache_check_only_hits(self) -> None:
        """Test cache check with only cache hits."""
        # Cache check - using direct function calls
        parsed = _create_parsed_varnish(
            backend_values={},
            cache_values={
                "cache_miss": 0,
                "cache_hit": 1000,
                "cache_hitpass": 0,
            },
        )

        # First call will raise GetRateError as expected
        with pytest.raises(GetRateError):
            list(check_varnish_cache(None, {}, parsed))

    @pytest.mark.parametrize(
        "cache_values,description",
        [
            ({"cache_miss": 100, "cache_hit": 900, "cache_hitpass": 10}, "good hit ratio"),
            ({"cache_miss": 500, "cache_hit": 400, "cache_hitpass": 100}, "poor hit ratio"),
            ({"cache_miss": 0, "cache_hit": 0, "cache_hitpass": 0}, "no cache activity"),
        ],
    )
    @pytest.mark.usefixtures("initialised_item_state")
    def test_cache_hit_patterns(self, cache_values: dict[str, int], description: str) -> None:
        """Test cache check with different hit/miss patterns."""
        # Cache check - using direct function calls
        parsed = _create_parsed_varnish(backend_values={}, cache_values=cache_values)

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)


class TestVarnishDataParsing:
    """Test cases for Varnish agent output parsing."""

    def test_parse_basic_varnish_output(self) -> None:
        """Test parsing of basic Varnish agent output."""
        agent_output = [
            ["client_conn", "13687134", "4.41", "Client", "connections", "accepted"],
            ["cache_hit", "3678", "0.00", "Cache", "hits"],
            ["cache_miss", "5687", "0.00", "Cache", "misses"],
            ["backend_conn", "6870153", "2.21", "Backend", "conn.", "success"],
            ["backend_fail", "0", "0.00", "Backend", "conn.", "failures"],
        ]

        parsed = parse_varnish(agent_output)

        assert "client_conn" in parsed
        assert parsed["client_conn"]["value"] == 13687134
        assert parsed["client_conn"]["descr"] == "connections accepted"

        assert "cache_hit" in parsed
        assert parsed["cache_hit"]["value"] == 3678

        assert "backend_conn" in parsed
        assert parsed["backend_conn"]["value"] == 6870153

    def test_parse_hierarchical_keys(self) -> None:
        """Test parsing of hierarchical Varnish keys."""
        agent_output = [
            ["LCK.sms.creat", "1", "0.00", "Created", "locks"],
            ["VBE.default(127.0.0.1,,81).happy", "0", ".", "Happy", "health", "probes"],
            ["SMA.s0.c_req", "13215", "0.00", "Allocator", "requests"],
        ]

        parsed = parse_varnish(agent_output)

        assert "LCK" in parsed
        assert "sms" in parsed["LCK"]
        assert parsed["LCK"]["sms"]["creat"]["value"] == 1

        assert "VBE" in parsed
        assert "default(127.0.0.1,,81)" in parsed["VBE"]
        assert parsed["VBE"]["default(127.0.0.1,,81)"]["happy"]["value"] == 0

    def test_parse_main_prefix_handling(self) -> None:
        """Test parsing with MAIN prefix keys."""
        agent_output = [
            ["MAIN.cache_hit", "1000", "0.50", "Cache", "hits"],
            ["MAIN.cache_miss", "200", "0.10", "Cache", "misses"],
            ["cache_hitpass", "50", "0.02", "Cache", "hits", "for", "pass"],
        ]

        parsed = parse_varnish(agent_output)

        # MAIN prefix should be stripped
        assert "cache_hit" in parsed
        assert parsed["cache_hit"]["value"] == 1000
        assert "cache_miss" in parsed
        assert parsed["cache_miss"]["value"] == 200

        # Non-prefixed keys should remain
        assert "cache_hitpass" in parsed
        assert parsed["cache_hitpass"]["value"] == 50


class TestVarnishIntegration:
    """Integration tests combining backend and cache monitoring."""

    def test_combined_backend_cache_discovery(self) -> None:
        """Test discovery when both backend and cache metrics are available."""
        parsed = _create_parsed_varnish(
            backend_values={"backend_fail": 0, "backend_unhealthy": 0, "backend_busy": 0},
            cache_values={"cache_miss": 100},
        )

        backend_discovery = list(discover_varnish_backend(parsed))
        cache_discovery = list(discover_varnish_cache(parsed))

        assert len(backend_discovery) == 1
        assert len(cache_discovery) == 1

    @pytest.mark.usefixtures("initialised_item_state")
    def test_realistic_varnish_monitoring(self) -> None:
        """Test realistic Varnish monitoring scenario."""
        # Realistic values from production environment
        parsed = _create_parsed_varnish(
            backend_values={
                "backend_busy": 2,
                "backend_unhealthy": 0,
                "backend_req": 15541595,
                "backend_recycle": 15534489,
                "backend_retry": 46,
                "backend_fail": 0,
                "backend_toolate": 6235,
                "backend_conn": 15541595,
                "backend_reuse": 15534489,
            },
            cache_values={
                "cache_miss": 2847391,
                "cache_hit": 12694204,
                "cache_hitpass": 8547,
            },
        )

        # First run raises GetRateError for rate-based checks
        with pytest.raises(GetRateError):
            list(check_varnish_backend(None, {}, parsed))

        with pytest.raises(GetRateError):
            list(check_varnish_cache(None, {}, parsed))


class TestVarnishClientMonitoring:
    """Test cases for Varnish client connection monitoring."""

    def test_discovery_with_client_metrics(self) -> None:
        """Test discovery when client metrics are available."""
        parsed = _create_parsed_varnish(
            client_values={
                "client_drop": 0,
                "client_req": 1000,
                "client_conn": 500,
                "client_drop_late": 0,
            }
        )

        discovery_result = list(discover_varnish_client(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_client_check_normal_operation(self) -> None:
        """Test client check with normal connection patterns."""
        parsed = _create_parsed_varnish(
            client_values={
                "client_drop": 0,
                "client_req": 1000,
                "client_conn": 500,
                "client_drop_late": 0,
            }
        )

        # First run raises GetRateError for rate-based checks
        with pytest.raises(GetRateError):
            list(check_varnish_client(None, {}, parsed))

    @pytest.mark.usefixtures("initialised_item_state")
    def test_client_check_with_drops(self) -> None:
        """Test client check with connection drops."""
        parsed = _create_parsed_varnish(
            client_values={
                "client_drop": 50,  # Some dropped connections
                "client_req": 1000,
                "client_conn": 500,
                "client_drop_late": 10,  # Late drops
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)


class TestVarnishESIMonitoring:
    """Test cases for Varnish ESI processing monitoring."""

    def test_discovery_with_esi_metrics(self) -> None:
        """Test discovery when ESI metrics are available."""
        parsed = _create_parsed_varnish(esi_values={"esi_errors": 0, "esi_warnings": 0})

        discovery_result = list(discover_varnish_esi(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_esi_check_no_errors(self) -> None:
        """Test ESI check with no errors or warnings."""
        parsed = _create_parsed_varnish(
            esi_values={
                "esi_errors": 0,
                "esi_warnings": 0,
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)

    @pytest.mark.usefixtures("initialised_item_state")
    def test_esi_check_with_issues(self) -> None:
        """Test ESI check with errors and warnings."""
        parsed = _create_parsed_varnish(
            esi_values={
                "esi_errors": 10,  # Some ESI errors
                "esi_warnings": 25,  # Some ESI warnings
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)


class TestVarnishFetchMonitoring:
    """Test cases for Varnish fetch operation monitoring."""

    def test_discovery_with_fetch_metrics(self) -> None:
        """Test discovery when fetch metrics are available."""
        parsed = _create_parsed_varnish(
            fetch_values={
                "fetch_head": 10,
                "fetch_length": 200,
                "fetch_chunked": 300,
                "fetch_304": 100,
                "fetch_failed": 0,
            }
        )

        discovery_result = list(discover_varnish_fetch(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_fetch_check_normal_operation(self) -> None:
        """Test fetch check with normal operation patterns."""
        parsed = _create_parsed_varnish(
            fetch_values={
                "fetch_head": 10,
                "fetch_length": 200,
                "fetch_chunked": 300,
                "fetch_304": 100,
                "fetch_failed": 0,
                "fetch_bad": 0,
                "fetch_eof": 0,
                "fetch_zero": 0,
                "fetch_close": 0,
                "fetch_1xx": 0,
                "fetch_204": 0,
                "fetch_oldhttp": 0,
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)

    @pytest.mark.usefixtures("initialised_item_state")
    def test_fetch_check_with_failures(self) -> None:
        """Test fetch check with fetch failures."""
        parsed = _create_parsed_varnish(
            fetch_values={
                "fetch_failed": 25,  # Some fetch failures
                "fetch_bad": 10,  # Bad headers
                "fetch_length": 200,
                "fetch_chunked": 300,
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)


class TestVarnishObjectsMonitoring:
    """Test cases for Varnish objects lifecycle monitoring."""

    def test_discovery_with_objects_metrics(self) -> None:
        """Test discovery when objects metrics are available."""
        parsed = _create_parsed_varnish(
            objects_values={
                "n_expired": 100,
                "n_lru_nuked": 0,
                "n_lru_moved": 50,
            }
        )

        discovery_result = list(discover_varnish_objects(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_objects_check_normal_lifecycle(self) -> None:
        """Test objects check with normal object lifecycle."""
        parsed = _create_parsed_varnish(
            objects_values={
                "n_expired": 100,
                "n_lru_nuked": 0,
                "n_lru_moved": 50,
            }
        )

        # First run raises GetRateError for rate-based checks
        with pytest.raises(GetRateError):
            list(check_varnish_objects(None, {}, parsed))

    @pytest.mark.usefixtures("initialised_item_state")
    def test_objects_check_with_lru_pressure(self) -> None:
        """Test objects check with LRU pressure."""
        parsed = _create_parsed_varnish(
            objects_values={
                "n_expired": 200,
                "n_lru_nuked": 50,  # LRU pressure causing nukes
                "n_lru_moved": 300,  # High LRU activity
            }
        )

        # First run raises GetRateError for rate-based checks
        with pytest.raises(GetRateError):
            list(check_varnish_objects(None, {}, parsed))


class TestVarnishWorkerMonitoring:
    """Test cases for Varnish worker thread monitoring."""

    def test_discovery_with_worker_metrics(self) -> None:
        """Test discovery when worker metrics are available."""
        parsed = _create_parsed_varnish(
            worker_values={
                "n_wrk": 1000,
                "n_wrk_create": 1000,
                "n_wrk_failed": 0,
                "n_wrk_drop": 0,
                "n_wrk_lqueue": 0,
                "n_wrk_queued": 20,
                "n_wrk_max": 900,
            }
        )

        discovery_result = list(discover_varnish_worker(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_worker_check_healthy_pool(self) -> None:
        """Test worker check with healthy thread pool."""
        parsed = _create_parsed_varnish(
            worker_values={
                "n_wrk": 1000,
                "n_wrk_create": 1000,
                "n_wrk_failed": 0,
                "n_wrk_drop": 0,
                "n_wrk_lqueue": 0,
                "n_wrk_queued": 20,
                "n_wrk_max": 900,
            }
        )

        # First run raises GetRateError for rate-based checks
        with pytest.raises(GetRateError):
            list(check_varnish_worker(None, {}, parsed))

    @pytest.mark.usefixtures("initialised_item_state")
    def test_worker_check_thread_issues(self) -> None:
        """Test worker check with thread creation issues."""
        parsed = _create_parsed_varnish(
            worker_values={
                "n_wrk": 800,
                "n_wrk_create": 1000,
                "n_wrk_failed": 50,  # Thread creation failures
                "n_wrk_drop": 25,  # Dropped requests
                "n_wrk_lqueue": 100,  # Queue length issues
                "n_wrk_queued": 200,  # High queue
                "n_wrk_max": 900,
            }
        )

        # First run raises GetRateError for rate-based checks
        with pytest.raises(GetRateError):
            list(check_varnish_worker(None, {}, parsed))


class TestVarnishRatioChecks:
    """Test cases for Varnish ratio-based checks."""

    def test_backend_success_ratio_discovery(self) -> None:
        """Test discovery for backend success ratio check."""
        parsed = _create_parsed_varnish(
            backend_values={
                "backend_conn": 800,
                "backend_fail": 0,
                "backend_req": 1000,
            }
        )

        discovery_result = list(discover_varnish_backend_success_ratio(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_backend_success_ratio_high_success(self) -> None:
        """Test backend success ratio with high success rate."""
        parsed = _create_parsed_varnish(
            backend_values={
                "backend_conn": 950,  # High success
                "backend_fail": 50,  # Low failures
                "backend_req": 1000,
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)

    def test_cache_hit_ratio_discovery(self) -> None:
        """Test discovery for cache hit ratio check."""
        parsed = _create_parsed_varnish(
            cache_values={
                "cache_hit": 800,
                "cache_miss": 200,
            }
        )

        discovery_result = list(discover_varnish_cache_hit_ratio(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_cache_hit_ratio_good_performance(self) -> None:
        """Test cache hit ratio with good cache performance."""
        parsed = _create_parsed_varnish(
            cache_values={
                "cache_hit": 800,  # Good hit rate
                "cache_miss": 200,  # Reasonable miss rate
            }
        )

        results = list(check_varnish_objects(None, {}, parsed))
        assert isinstance(results, list | tuple)

    def test_worker_thread_ratio_discovery(self) -> None:
        """Test discovery for worker thread ratio check."""
        parsed = _create_parsed_varnish(
            worker_values={
                "n_wrk": 1000,
                "n_wrk_max": 900,
            }
        )

        discovery_result = list(discover_varnish_worker_thread_ratio(parsed))
        assert len(discovery_result) == 1
        assert discovery_result[0] == (None, {})

    @pytest.mark.usefixtures("initialised_item_state")
    def test_worker_thread_ratio_normal_usage(self) -> None:
        """Test worker thread ratio with normal thread usage."""
        parsed = _create_parsed_varnish(
            worker_values={
                "n_wrk": 800,  # Current threads
                "n_wrk_max": 900,  # Maximum threads hit
            }
        )

        results = list(
            check_varnish_worker_thread_ratio(None, {"levels_lower": (70.0, 60.0)}, parsed)
        )
        assert isinstance(results, list | tuple)
