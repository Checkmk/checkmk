#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import timedelta

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    render,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(frozen=True)
class Counter:
    value: int
    descr: str


Section = Mapping[str, Counter]
Params = Mapping[str, tuple[float, float]]

# Newer output has MAIN and MGT prefixed keys, MGT takes precedence
_PREFIX_PRECEDENCE = {"MAIN": 1, "MGT": 2}


def parse_varnish(string_table: StringTable) -> Section:
    return {
        _strip_prefix(line[0]): Counter(value, _descr(line[0], line[3:]))
        for line in sorted(
            string_table, key=lambda line: _PREFIX_PRECEDENCE.get(line[0].split(".", 1)[0], 0)
        )
        if (value := _parse_int(line[1])) is not None
    }


def _strip_prefix(key: str) -> str:
    head, _, tail = key.partition(".")
    return tail if head in _PREFIX_PRECEDENCE else key


def _parse_int(raw: str) -> int | None:
    try:
        return int(raw)
    except ValueError:
        return None


def _descr(key: str, words: Sequence[str]) -> str:
    # skip the first word if it repeats the key, e.g. 'client_conn ... Client connections'
    return " ".join(words[1:] if words and words[0].lower() in key else words).replace("/", " ")


def _metric_name(key: str) -> str:
    name = (
        key.replace("n_wrk", "worker", 1)
        if key.startswith("n_wrk")
        else key.replace("n_", "objects_", 1)
        if key.startswith("n_")
        else key
    )
    return f"varnish_{name}_rate"


def check_varnish_stats(params: Params, section: Section, keys: Sequence[str]) -> CheckResult:
    yield from check_varnish_rates(params, section, keys, get_value_store(), time.time())


def check_varnish_rates(
    params: Params,
    section: Section,
    keys: Sequence[str],
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    for key in (k for k in keys if k in section):
        counter = section[key]
        yield from check_levels(
            get_rate(value_store, f"varnish.{key}", now, counter.value, raise_overflow=True),
            _metric_name(key),
            params.get(key.split("_", 1)[-1], (None, None)),
            human_readable_func=lambda r, d=f"{counter.descr}/s": f"{r:.1f} {d}",
        )


def check_varnish_ratio(
    params: Params, section: Section, ratio_keys: tuple[str, str, str]
) -> CheckResult:
    reference_key, additional_key, metric_name = ratio_keys
    reference = section[reference_key].value
    total = reference + section[additional_key].value
    warn, crit = params["levels_lower"]
    yield from check_levels(
        100.0 * reference / total if total > 0 else 0.0,
        metric_name,
        (None, None, warn, crit),
        human_readable_func=render.percent,
    )


def discover_varnish_uptime(section: Section) -> DiscoveryResult:
    if "uptime" in section:
        yield Service()


def check_varnish_uptime(section: Section) -> CheckResult:
    if (uptime := section.get("uptime")) is None:
        return
    try:
        yield from check_levels(
            uptime.value,
            "uptime",
            None,
            human_readable_func=lambda x: timedelta(seconds=int(x)),
            infoname="Up since %s, uptime"
            % time.strftime("%c", time.localtime(time.time() - uptime.value)),
        )
    except OverflowError:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Could not handle uptime value {uptime.value!r}. "
            "Output of `varnishstats` seems to be faulty.",
        )


agent_section_varnish = AgentSection(
    name="varnish",
    parse_function=parse_varnish,
)


check_plugin_varnish = CheckPlugin(
    name="varnish",
    service_name="Varnish Uptime",
    discovery_function=discover_varnish_uptime,
    check_function=check_varnish_uptime,
)


def discover_varnish_cache(section: Section) -> DiscoveryResult:
    if "cache_miss" in section:
        yield Service()


def check_varnish_cache(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "cache_miss",
            "cache_hit",
            "cache_hitpass",
        ],
    )


check_plugin_varnish_cache = CheckPlugin(
    name="varnish_cache",
    service_name="Varnish Cache",
    sections=["varnish"],
    discovery_function=discover_varnish_cache,
    check_function=check_varnish_cache,
    check_ruleset_name="varnish_cache",
    check_default_parameters={},
)


def discover_varnish_client(section: Section) -> DiscoveryResult:
    if "client_req" in section:
        yield Service()


def check_varnish_client(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "client_drop",
            "client_req",
            "client_conn",
            "client_drop_late",
        ],
    )


check_plugin_varnish_client = CheckPlugin(
    name="varnish_client",
    service_name="Varnish Client",
    sections=["varnish"],
    discovery_function=discover_varnish_client,
    check_function=check_varnish_client,
    check_ruleset_name="varnish_client",
    check_default_parameters={},
)


def discover_varnish_backend(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["backend_fail", "backend_unhealthy", "backend_busy"]):
        yield Service()


def check_varnish_backend(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "backend_busy",
            "backend_unhealthy",
            "backend_req",
            "backend_recycle",
            "backend_retry",
            "backend_fail",
            "backend_toolate",
            "backend_conn",
            "backend_reuse",
        ],
    )


check_plugin_varnish_backend = CheckPlugin(
    name="varnish_backend",
    service_name="Varnish Backend",
    sections=["varnish"],
    discovery_function=discover_varnish_backend,
    check_function=check_varnish_backend,
    check_ruleset_name="varnish_backend",
    check_default_parameters={},
)


def discover_varnish_fetch(section: Section) -> DiscoveryResult:
    if all(
        key in section
        for key in [
            "fetch_1xx",
            "fetch_204",
            "fetch_304",
            "fetch_bad",
            "fetch_eof",
            "fetch_failed",
            "fetch_zero",
        ]
    ):
        yield Service()


def check_varnish_fetch(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "fetch_oldhttp",
            "fetch_head",
            "fetch_eof",
            "fetch_zero",
            "fetch_304",
            "fetch_length",
            "fetch_failed",
            "fetch_bad",
            "fetch_close",
            "fetch_1xx",
            "fetch_chunked",
            "fetch_204",
        ],
    )


check_plugin_varnish_fetch = CheckPlugin(
    name="varnish_fetch",
    service_name="Varnish Fetch",
    sections=["varnish"],
    discovery_function=discover_varnish_fetch,
    check_function=check_varnish_fetch,
    check_ruleset_name="varnish_fetch",
    check_default_parameters={},
)


def discover_varnish_esi(section: Section) -> DiscoveryResult:
    if "esi_errors" in section:
        yield Service()


def check_varnish_esi(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "esi_errors",
            "esi_warnings",
        ],
    )


check_plugin_varnish_esi = CheckPlugin(
    name="varnish_esi",
    service_name="Varnish ESI",
    sections=["varnish"],
    discovery_function=discover_varnish_esi,
    check_function=check_varnish_esi,
    check_ruleset_name="varnish_esi",
    check_default_parameters={"errors": (1.0, 2.0)},
)


def discover_varnish_objects(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["n_expired", "n_lru_nuked"]):
        yield Service()


def check_varnish_objects(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "n_expired",
            "n_lru_nuked",
            "n_lru_moved",
        ],
    )


check_plugin_varnish_objects = CheckPlugin(
    name="varnish_objects",
    service_name="Varnish Objects",
    sections=["varnish"],
    discovery_function=discover_varnish_objects,
    check_function=check_varnish_objects,
    check_ruleset_name="varnish_objects",
    check_default_parameters={},
)


def discover_varnish_worker(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["n_wrk_failed", "n_wrk_queued"]):
        yield Service()


def check_varnish_worker(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_stats(
        params,
        section,
        [
            "n_wrk_lqueue",
            "n_wrk_create",
            "n_wrk_drop",
            "n_wrk",
            "n_wrk_failed",
            "n_wrk_queued",
            "n_wrk_max",
        ],
    )


check_plugin_varnish_worker = CheckPlugin(
    name="varnish_worker",
    service_name="Varnish Worker",
    sections=["varnish"],
    discovery_function=discover_varnish_worker,
    check_function=check_varnish_worker,
    check_ruleset_name="varnish_worker",
    check_default_parameters={},
)


def discover_varnish_cache_hit_ratio(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["cache_miss", "cache_hit"]):
        yield Service()


def check_varnish_cache_hit_ratio(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_ratio(params, section, ("cache_hit", "cache_miss", "cache_hit_ratio"))


check_plugin_varnish_cache_hit_ratio = CheckPlugin(
    name="varnish_cache_hit_ratio",
    service_name="Varnish Cache Hit Ratio",
    sections=["varnish"],
    discovery_function=discover_varnish_cache_hit_ratio,
    check_function=check_varnish_cache_hit_ratio,
    check_ruleset_name="varnish_cache_hit_ratio",
    check_default_parameters={"levels_lower": (70.0, 60.0)},
)


def discover_varnish_backend_success_ratio(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["backend_fail", "backend_conn"]):
        yield Service()


def check_varnish_backend_success_ratio(params: Params, section: Section) -> CheckResult:
    yield from check_varnish_ratio(
        params, section, ("backend_conn", "backend_fail", "varnish_backend_success_ratio")
    )


check_plugin_varnish_backend_success_ratio = CheckPlugin(
    name="varnish_backend_success_ratio",
    service_name="Varnish Backend Success Ratio",
    sections=["varnish"],
    discovery_function=discover_varnish_backend_success_ratio,
    check_function=check_varnish_backend_success_ratio,
    check_ruleset_name="varnish_backend_success_ratio",
    check_default_parameters={"levels_lower": (70.0, 60.0)},
)


def check_varnish_worker_thread_ratio(params: Params, section: Section) -> CheckResult:
    worker_create = section["n_wrk_create"].value
    warn, crit = params["levels_lower"]
    yield from check_levels(
        100.0 * section["n_wrk"].value / worker_create if worker_create > 0 else 0.0,
        "varnish_worker_thread_ratio",
        (None, None, warn, crit),
        human_readable_func=render.percent,
    )


def discover_varnish_worker_thread_ratio(section: Section) -> DiscoveryResult:
    if all(key in section for key in ["n_wrk", "n_wrk_create"]):
        yield Service()


check_plugin_varnish_worker_thread_ratio = CheckPlugin(
    name="varnish_worker_thread_ratio",
    service_name="Varnish Worker Thread Ratio",
    sections=["varnish"],
    discovery_function=discover_varnish_worker_thread_ratio,
    check_function=check_varnish_worker_thread_ratio,
    check_ruleset_name="varnish_worker_thread_ratio",
    check_default_parameters={"levels_lower": (70.0, 60.0)},
)
