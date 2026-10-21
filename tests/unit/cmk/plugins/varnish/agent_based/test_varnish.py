#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    GetRateError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.varnish.agent_based import (
    lib,
    varnish,
    varnish_backend,
    varnish_cache,
    varnish_client,
    varnish_esi,
    varnish_fetch,
    varnish_objects,
    varnish_ratios,
    varnish_worker,
)

STRING_TABLE: StringTable = [
    ["MGT.uptime", "3600", "1.00", "Management", "process", "uptime"],
    ["MAIN.uptime", "1800", "1.00", "Child", "process", "uptime"],
    ["client_conn", "13687134", "4.41", "Client", "connections", "accepted"],
    ["client_drop", "0", "0.00", "Connection", "dropped,", "no", "sess/wrk"],
    ["client_req", "27309477", "8.80", "Client", "requests", "received"],
    ["cache_hit", "300", "0.00", "Cache", "hits"],
    ["cache_hitpass", "0", "0.00", "Cache", "hits", "for", "pass"],
    ["cache_miss", "100", "0.00", "Cache", "misses"],
    ["backend_conn", "90", "2.21", "Backend", "conn.", "success"],
    ["backend_unhealthy", "0", "0.00", "Backend", "conn.", "not", "attempted"],
    ["backend_busy", "0", "0.00", "Backend", "conn.", "too", "many"],
    ["backend_fail", "10", "0.00", "Backend", "conn.", "failures"],
    ["fetch_1xx", "0", "0.00", "Fetch", "no", "body", "(1xx)"],
    ["fetch_204", "0", "0.00", "Fetch", "no", "body", "(204)"],
    ["fetch_304", "0", "0.00", "Fetch", "no", "body", "(304)"],
    ["fetch_bad", "0", "0.00", "Fetch", "had", "bad", "headers"],
    ["fetch_eof", "0", "0.00", "Fetch", "EOF"],
    ["fetch_failed", "0", "0.00", "Fetch", "failed"],
    ["fetch_zero", "0", "0.00", "Fetch", "zero", "len"],
    ["esi_errors", "0", "0.00", "ESI", "parse", "errors", "(unlock)"],
    ["n_expired", "1", ".", "N", "expired", "objects"],
    ["n_lru_nuked", "0", ".", "N", "LRU", "nuked", "objects"],
    ["n_wrk", "60", ".", "N", "worker", "threads"],
    ["n_wrk_create", "100", "0.00", "N", "worker", "threads", "created"],
    ["n_wrk_failed", "0", "0.00", "N", "worker", "threads", "not", "created"],
    ["n_wrk_queued", "0", "0.00", "N", "queued", "work", "requests"],
    ["VBE.default(127.0.0.1,,81).happy", "0", ".", "Happy", "health", "probes"],
    ["SMA.s0.g_space", "nan", ".", "Bytes", "available"],
]


def test_parse_varnish() -> None:
    section = lib.parse_varnish(STRING_TABLE)
    assert section["uptime"] == lib.Counter(3600, "Management process uptime")
    assert section["client_conn"] == lib.Counter(13687134, "connections accepted")
    assert section["client_drop"] == lib.Counter(0, "Connection dropped, no sess wrk")
    assert section["VBE.default(127.0.0.1,,81).happy"] == lib.Counter(0, "health probes")
    assert "SMA.s0.g_space" not in section


@pytest.mark.parametrize(
    "discover",
    [
        varnish.discover_varnish_uptime,
        varnish_cache.discover_varnish_cache,
        varnish_client.discover_varnish_client,
        varnish_backend.discover_varnish_backend,
        varnish_fetch.discover_varnish_fetch,
        varnish_esi.discover_varnish_esi,
        varnish_objects.discover_varnish_objects,
        varnish_worker.discover_varnish_worker,
        varnish_ratios.discover_varnish_cache_hit_ratio,
        varnish_ratios.discover_varnish_backend_success_ratio,
        varnish_ratios.discover_varnish_worker_thread_ratio,
    ],
)
def test_discovery(discover: Callable[[lib.Section], DiscoveryResult]) -> None:
    assert list(discover(lib.parse_varnish(STRING_TABLE))) == [Service()]
    assert not list(discover({}))


def test_check_varnish_rates() -> None:
    value_store: dict[str, object] = {}
    keys = ["n_wrk_failed", "n_expired", "client_drop", "fetch_1xx", "missing"]
    params: lib.Params = {
        "wrk_failed": ("fixed", (1.0, 2.0)),
        "fetch_1xx": ("fixed", (0.5, 1.0)),
    }
    # each run initializes only the first uninitialized counter
    for now in (0.0, 1.0, 2.0, 3.0):
        with pytest.raises(GetRateError):
            list(
                lib.check_varnish_rates(
                    params, lib.parse_varnish(STRING_TABLE), keys, value_store, now
                )
            )
    assert list(
        lib.check_varnish_rates(
            params,
            lib.parse_varnish(
                [
                    ["n_wrk_failed", "15", "0.00", "N", "worker", "threads", "not", "created"],
                    ["n_expired", "1", ".", "N", "expired", "objects"],
                    ["client_drop", "60", "0.00", "Connection", "dropped,", "no", "sess/wrk"],
                    ["fetch_1xx", "20", "0.00", "Fetch", "no", "body", "(1xx)"],
                ]
            ),
            keys,
            value_store,
            13.0,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="worker threads not created: 1.5/s (warn/crit at 1.0/s/2.0/s)",
        ),
        Metric("varnish_worker_failed_rate", 1.5, levels=(1.0, 2.0)),
        Result(state=State.OK, summary="expired objects: 0.0/s"),
        Metric("varnish_objects_expired_rate", 0.0),
        Result(state=State.OK, summary="Connection dropped, no sess wrk: 6.0/s"),
        Metric("varnish_client_drop_rate", 6.0),
        Result(state=State.CRIT, summary="no body (1xx): 2.0/s (warn/crit at 0.5/s/1.0/s)"),
        Metric("varnish_fetch_1xx_rate", 2.0, levels=(0.5, 1.0)),
    ]


@pytest.mark.parametrize(
    "check, metric, ratio, state",
    [
        (
            varnish_ratios.check_varnish_cache_hit_ratio,
            "cache_hit_ratio",
            75.0,
            State.OK,
        ),
        (
            varnish_ratios.check_varnish_backend_success_ratio,
            "varnish_backend_success_ratio",
            90.0,
            State.OK,
        ),
        (
            varnish_ratios.check_varnish_worker_thread_ratio,
            "varnish_worker_thread_ratio",
            60.0,
            State.WARN,
        ),
    ],
)
def test_check_ratios(
    check: Callable[[lib.Params, lib.Section], CheckResult],
    metric: str,
    ratio: float,
    state: State,
) -> None:
    results = list(
        check({"levels_lower": ("fixed", (70.0, 60.0))}, lib.parse_varnish(STRING_TABLE))
    )
    assert [r.state for r in results if isinstance(r, Result)] == [state]
    assert [m for m in results if isinstance(m, Metric)] == [Metric(metric, ratio)]


def test_check_ratio_zero_total() -> None:
    assert list(
        varnish_ratios.check_varnish_cache_hit_ratio(
            {"levels_lower": ("fixed", (70.0, 60.0))},
            {"cache_hit": lib.Counter(0, ""), "cache_miss": lib.Counter(0, "")},
        )
    ) == [
        Result(state=State.CRIT, summary="0% (warn/crit below 70.00%/60.00%)"),
        Metric("cache_hit_ratio", 0.0),
    ]


def test_check_varnish_uptime() -> None:
    results = list(varnish.check_varnish_uptime(lib.parse_varnish(STRING_TABLE)))
    assert [r.state for r in results if isinstance(r, Result)] == [State.OK]
    assert [m for m in results if isinstance(m, Metric)] == [Metric("uptime", 3600)]
