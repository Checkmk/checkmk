#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

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

Section = Mapping[str, object]
Params = Mapping[str, tuple[float, float]]


def parse_varnish(string_table: StringTable) -> Section:
    parsed: dict[str, Any] = {}
    for line in string_table:
        parsed_path = _parse_path(line[0])
        instance = _create_hierarchy(parsed_path, parsed)
        try:
            value = int(line[1])
        except ValueError:
            value = None
        if line[3].lower() in line[0]:
            descr = " ".join(line[4:])
        else:
            descr = " ".join(line[3:])
        perf_var_name = "varnish_%s_rate" % parsed_path[-1]
        if perf_var_name.startswith("varnish_n_wrk"):
            perf_var_name = perf_var_name.replace("n_wrk", "worker")
        elif perf_var_name.startswith("varnish_n_"):
            perf_var_name = perf_var_name.replace("n_", "objects_")
        instance.update(
            {
                "value": value,
                "descr": descr.replace("/", " "),
                "perf_var_name": perf_var_name,
                "params_var_name": parsed_path[-1].split("_", 1)[-1],
            }
        )
    # Newer output has MAIN or MGT prefix keys,
    # see above in 'agent output'
    for key in ["MAIN", "MGT"]:
        values = parsed.pop(key, {})
        parsed.update(values)
    return parsed


def _parse_path(raw_path: str) -> list[str]:
    # Split raw path on ".". We have to deal with different paths:
    # - 'client_conn'
    #   => ['client_conn']
    # - 'LCK.sms.creat'
    #   => ['LCK', 'sms', 'creat']
    # - 'VBE.default(127.0.0.1,,81).happy'
    #   => ['VBE', 'default(127.0.0.1,,81)', 'happy']
    if "(" not in raw_path:
        return raw_path.split(".")
    head_str, middle = raw_path.split("(", 1)
    address, tail = middle.split(")", 1)
    head = head_str.strip(".").split(".")
    return head[:-1] + [f"{head[-1]}({address})"] + tail.strip(".").split(".")


def _create_hierarchy(path: list[str], instance: dict[str, Any]) -> dict[str, Any]:
    if not path:
        return instance
    head, tail = path[0], path[1:]
    child = instance.setdefault(head, {})
    return _create_hierarchy(tail, child)


def check_varnish_stats(params: Params, section: Section, expected_keys: list[str]) -> CheckResult:
    this_time = time.time()
    for key in expected_keys:
        if not (data := section.get(key)):
            continue
        assert isinstance(data, dict)
        descr_per_sec = f"{data['descr']}/s"
        yield from check_levels(
            get_rate(
                get_value_store(), "varnish.%s" % key, this_time, data["value"], raise_overflow=True
            ),
            data["perf_var_name"],
            params.get(data["params_var_name"], (None, None)),
            human_readable_func=lambda r, d=descr_per_sec: f"{r:.1f} {d}",
        )


def check_varnish_ratio(
    params: Params, section: Section, ratio_keys: tuple[str, str, str]
) -> CheckResult:
    reference_key, additional_key, perf_key = ratio_keys
    reference = section[reference_key]
    assert isinstance(reference, dict)
    reference_value = reference["value"]
    ratio = 0.0
    additional = section[additional_key]
    assert isinstance(additional, dict)
    total = reference_value + additional["value"]
    if total > 0:
        ratio = 100.0 * reference_value / total
    warn, crit = params["levels_lower"]
    yield from check_levels(
        ratio, perf_key, (None, None, warn, crit), human_readable_func=render.percent
    )


def discover_varnish_uptime(section: Section) -> DiscoveryResult:
    if "uptime" in section:
        yield Service()


def check_varnish_uptime(section: Section) -> CheckResult:
    if "uptime" not in section:
        return
    uptime = section["uptime"]
    assert isinstance(uptime, dict)
    uptime_sec = uptime["value"]
    try:
        yield from check_levels(
            uptime_sec,
            "uptime",
            None,
            human_readable_func=lambda x: timedelta(seconds=int(x)),
            infoname="Up since %s, uptime"
            % time.strftime("%c", time.localtime(time.time() - uptime_sec)),
        )
    except OverflowError:  # is this in the right place?
        yield Result(
            state=State.UNKNOWN,
            summary=f"Could not handle uptime value {uptime['value']!r}. "
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
    ratio = 0.0
    n_wrk_create = section["n_wrk_create"]
    assert isinstance(n_wrk_create, dict)
    worker_create = n_wrk_create["value"]

    n_wrk = section["n_wrk"]
    assert isinstance(n_wrk, dict)
    worker_create = n_wrk["value"]

    if worker_create > 0:
        ratio = 100.0 * n_wrk["value"] / worker_create
    warn, crit = params["levels_lower"]
    yield from check_levels(
        ratio,
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
