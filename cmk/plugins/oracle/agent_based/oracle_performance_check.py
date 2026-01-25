#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import time
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    State,
)
from cmk.plugins.oracle import constants
from cmk.plugins.oracle.agent_based.liboracle import InstancePerformance, SectionPerformance

# In cooperation with Thorsten Bruhns from OPITZ Consulting

# <<oracle_performance:sep(124)>>>
# TUX12C|DB CPU|64
# TUX12C|DB time|86

# server-linux-oracle-12:
# <<<oracle_performance:sep(124)>>>
# ENLT1|sys_time_model|DB CPU|223408
# ENLT1|sys_time_model|DB time|630525
# ENLT1|buffer_pool_statistics|DEFAULT|207456769|194044148|3075188333|126417048|10935918|0|419514
# ENLT1|librarycache|SQL AREA|84972008|84406451|196493113|193867707|791310|39140
# ENLT1|librarycache|TABLE/PROCEDURE|13196582|12937687|120405491|118546232|869542|0
# ENLT1|librarycache|BODY|8682469|8666221|11047659|11025730|3932|0
# ENLT1|librarycache|TRIGGER|21238|19599|21238|19599|0|0
# ENLT1|librarycache|INDEX|192359|171580|173880|112887|22742|0
# ENLT1|librarycache|CLUSTER|287523|284618|297990|294967|118|0
# ENLT1|librarycache|DIRECTORY|647|118|1297|232|0|0
# ENLT1|librarycache|QUEUE|6916850|6916397|14069290|14068271|367|0
# ENLT1|librarycache|APP CONTEXT|32|15|63|35|11|0
# ENLT1|librarycache|RULESET|2|1|15|9|4|0
# ENLT1|librarycache|SUBSCRIPTION|63|59|123|84|31|0
# ENLT1|librarycache|LOCATION|388|277|388|277|0|0
# ENLT1|librarycache|TRANSFORMATION|3452154|3451741|3452154|3451741|0|0
# ENLT1|librarycache|USER AGENT|24|15|12|2|1|0
# ENLT1|librarycache|TEMPORARY TABLE|45298|33939|45298|0|33939|0
# ENLT1|librarycache|TEMPORARY INDEX|18399|3046|18399|0|3046|0
# ENLT1|librarycache|EDITION|4054576|4054369|7846832|7846023|366|0


def _get_item_data(item: str, section: SectionPerformance) -> InstancePerformance:
    data = section.get(item)

    # In case of missing information we assume that the login into
    # the database has failed and we simply skip this check. It won't
    # switch to UNKNOWN, but will get stale.
    if not data:
        raise IgnoreResultsError("Login into database failed")

    return data


#
# ORACLE Performance Main Check
#


def discover_oracle_performance(
    params: Mapping[str, Any], section: SectionPerformance
) -> DiscoveryResult:
    discovered_params = {
        "check_dbtime": params.get("dbtime") is None,
        "check_memory": params.get("memory") is None,
    }
    yield from (Service(item=item, parameters=discovered_params.copy()) for item in section)


def check_oracle_performance(
    item: str, params: Mapping[str, Any], section: SectionPerformance
) -> CheckResult:
    data = _get_item_data(item, section)

    value_store = get_value_store()
    now = time.time()
    perfdata = []
    infotexts = []

    if params["check_dbtime"]:
        yield from _check_oracle_db_time(value_store, item, data, now, {})

    if params["check_memory"]:
        # old agents deliver not the needed data...
        sga_info = data.get("SGA_info")
        if sga_info:
            for sga_field in constants.ORACLE_SGA_FIELDS:
                if sga_field.name not in sga_info:
                    continue
                value = sga_info[sga_field.name]
                yield Result(
                    state=State.OK,
                    summary=f"{sga_field.name}: {render.bytes(value)}",
                )
                perfdata.append(Metric(sga_field.metric, value))

    # PDB is <SID>.<PDB>
    # ignore more perf-data for PDBs except CDBROOT!
    if "." in item and ".CDB$ROOT" not in item:
        # PDB does not support more performance data at the moment...
        infotexts.append("limited performance data for PDBSEED and non CDBROOT")
        yield Result(state=State.OK, summary=", ".join(infotexts))
        yield from perfdata
        return

    if "buffer_pool_statistics" in data and "DEFAULT" in data["buffer_pool_statistics"]:
        buffer_pool_stats = data["buffer_pool_statistics"]
        (
            db_block_gets,
            db_block_change,
            consistent_gets,
            physical_reads,
            physical_writes,
            free_buffer_wait,
            buffer_busy_wait,
        ) = buffer_pool_stats["DEFAULT"]

        for what, val in [
            ("oracle_db_block_gets", db_block_gets),
            ("oracle_db_block_change", db_block_change),
            ("oracle_consistent_gets", consistent_gets),
            ("oracle_physical_reads", physical_reads),
            ("oracle_physical_writes", physical_writes),
            ("oracle_free_buffer_wait", free_buffer_wait),
            ("oracle_buffer_busy_wait", buffer_busy_wait),
        ]:
            rate = get_rate(value_store, f"{item}.buffer_pool_statistics.{what}", now, val)
            perfdata.append(Metric(what, rate))

        if db_block_gets + consistent_gets > 0:
            hit_ratio = (
                1 - (float(physical_reads) / (float(db_block_gets) + float(consistent_gets)))
            ) * 100
            yield Result(state=State.OK, summary="Buffer hit ratio: %.1f%%" % hit_ratio)
            yield Metric("oracle_buffer_hit_ratio", hit_ratio)

    if "librarycache" in data:
        pins_sum = 0
        pin_hits_sum = 0
        for what, vals in data["librarycache"].items():
            _gets, _gethits, pins, pin_hits, _reloads, _invalidations = vals
            pins_sum += pins
            pin_hits_sum += pin_hits

        for what, val in [("oracle_pins_sum", pins_sum), ("oracle_pin_hits_sum", pin_hits_sum)]:
            rate = get_rate(value_store, f"{item}.librarycache.{what}", now, val)
            perfdata.append(Metric(what, rate))

        if pins_sum > 0:
            pin_ratio = float(pin_hits_sum) / pins_sum * 100
            yield Result(state=State.OK, summary="Library cache hit ratio: %.1f%%" % pin_ratio)
            yield Metric("oracle_library_cache_hit_ratio", pin_ratio)

    yield from (Result(state=State.OK, summary=s) for s in sorted(infotexts))
    yield from sorted(perfdata, key=lambda m: m.name)


check_plugin_oracle_performance = CheckPlugin(
    name="oracle_performance",
    service_name="ORA %s Performance",
    discovery_function=discover_oracle_performance,
    discovery_ruleset_name="oracle_performance_discovery",
    discovery_default_parameters={},
    check_function=check_oracle_performance,
    check_default_parameters={
        "check_dbtime": True,
        "check_memory": True,
    },
)

# ======================================
# ORACLE PERFORMANCE SUBCHECKS
# ======================================


def discover_oracle_performance_subcheck(
    subcheck_settings_name: str,
) -> Callable[[Mapping[str, Any], SectionPerformance], DiscoveryResult]:
    """Subchecks are activated optionally via discovery configuration"""

    def inventory_func(params: Mapping[str, Any], section: SectionPerformance) -> DiscoveryResult:
        if params.get(subcheck_settings_name) is None:
            return
        yield from (Service(item=sid) for sid in section)

    return inventory_func


def _get_subcheck_params(full_params: Mapping[str, Any], subcheck_name: str) -> Mapping:
    params_list = full_params.get(subcheck_name, [])
    return {p[0]: p[1] for p in params_list}


def _unit_formatter(unit: str) -> Callable[[float], str]:
    def _fmt(f: float) -> str:
        return f"{f:.2f}{unit}"

    return _fmt


#
# ORACLE Performance DB-Time
#


def _check_oracle_db_time(
    value_store: MutableMapping[str, Any],
    item: str,
    item_data: InstancePerformance,
    now: float,
    params: Mapping[str, Any],
) -> CheckResult:
    def get_db_time_rate(perfvar: str, val: int) -> float:
        return get_rate(value_store, f"{item}.sys_time_model.{perfvar}", now, val)

    # old agents deliver no data for sys_time_model!
    sys_time_model = item_data.get("sys_time_model")
    if sys_time_model is None:
        return

    # sys_time_model: only DB_CPU and DB_Time!
    cpu_time = sys_time_model["DB CPU"]
    db_time = sys_time_model["DB time"]
    # db_time is the sum of cpu time and wait time (non-idle)
    wait_time = db_time - cpu_time

    cpu_time_rate = get_db_time_rate("oracle_db_cpu", cpu_time)
    db_time_rate = get_db_time_rate("oracle_db_time", db_time)
    wait_time_rate = get_db_time_rate("oracle_db_wait_time", wait_time)

    for metric, infoname, rate in [
        ("oracle_db_time", "DB Time", db_time_rate),
        ("oracle_db_cpu", "DB CPU", cpu_time_rate),
        ("oracle_db_wait_time", "DB Non-Idle Wait", wait_time_rate),
    ]:
        yield from check_levels(
            rate,
            metric_name=metric,
            levels_upper=params.get(metric),
            render_func=_unit_formatter("/s"),
            label=infoname,
        )


def check_oracle_performance_dbtime(
    item: str, params: Mapping[str, Any], section: SectionPerformance
) -> CheckResult:
    params = _get_subcheck_params(params, "dbtime")
    data = _get_item_data(item, section)
    value_store = get_value_store()
    now = time.time()
    yield from _check_oracle_db_time(value_store, item, data, now, params)


check_plugin_oracle_performance_dbtime = CheckPlugin(
    name="oracle_performance_dbtime",
    service_name="ORA %s Performance DB-Time",
    sections=["oracle_performance"],
    discovery_function=discover_oracle_performance_subcheck("dbtime"),
    discovery_ruleset_name="oracle_performance_discovery",
    discovery_default_parameters={},
    check_function=check_oracle_performance_dbtime,
    check_ruleset_name="oracle_performance",
    check_default_parameters={},
)

#
# ORACLE Performance Memory
#


def _check_oracle_memory_info(
    data: Mapping[str, Any],
    params: Mapping[str, Any],
    sticky_fields: Sequence[str],
    fields: Sequence[constants.OracleSGA] | Sequence[constants.OraclePGA],
) -> CheckResult:
    for ga_field in fields:
        value = data.get(ga_field.name)
        if value is None:
            continue

        yield from check_levels(
            value,
            metric_name=ga_field.metric,
            levels_upper=params.get(ga_field.metric),
            render_func=render.bytes,
            label=ga_field.name,
            notice_only=ga_field.name not in sticky_fields,
        )


def check_oracle_performance_memory(
    item: str, params: Mapping[str, Any], section: SectionPerformance
) -> CheckResult:
    params = _get_subcheck_params(params, "memory")
    data = _get_item_data(item, section)
    sga_info = data.get("SGA_info", {})

    yield from _check_oracle_memory_info(
        sga_info, params, ["Maximum SGA Size"], constants.ORACLE_SGA_FIELDS
    )

    pga_info = {field: value[0] for field, value in data.get("PGA_info", {}).items()}
    yield from _check_oracle_memory_info(
        pga_info, params, ["total PGA allocated"], constants.ORACLE_PGA_FIELDS
    )


check_plugin_oracle_performance_memory = CheckPlugin(
    name="oracle_performance_memory",
    service_name="ORA %s Performance Memory",
    sections=["oracle_performance"],
    discovery_function=discover_oracle_performance_subcheck("memory"),
    discovery_ruleset_name="oracle_performance_discovery",
    discovery_default_parameters={},
    check_function=check_oracle_performance_memory,
    check_ruleset_name="oracle_performance",
    check_default_parameters={},
)


#
# ORACLE Performance IOStat Bytes + IOs
#


def _check_oracle_performance_iostat_file(
    value_store: MutableMapping[str, Any],
    now: float,
    item: str,
    params: Mapping[str, Any],
    data: InstancePerformance,
    unit: str,
    io_fields: Sequence[tuple[int, str, str]],
) -> CheckResult:
    totals = [0.0] * len(io_fields)

    iostat_info = data.get("iostat_file", {})
    for iofile in constants.ORACLE_IO_FILES:
        waitdata = iostat_info.get(iofile.name)
        if not waitdata:
            continue
        for i, field in enumerate(io_fields):
            data_index, metric_suffix, field_name = field
            metric_name = f"oracle_ios_f_{iofile.id}_{metric_suffix}"

            rate = get_rate(
                value_store,
                f"{item}.iostat_file.{metric_name}",
                now,
                waitdata[data_index],
            )

            totals[i] += rate

            yield from check_levels(
                rate,
                metric_name=metric_name,
                levels_upper=params.get(metric_name),
                render_func=_unit_formatter(unit),
                label=iofile.name + " " + field_name,
                notice_only=True,
            )

    # Output totals
    for i, field in enumerate(io_fields):
        _data_index, metric_suffix, field_name = field
        total = totals[i]

        if unit == "bytes/s":
            total_output = render.iobandwidth(total)
        else:
            total_readable = total
            total_output = f"{total_readable:.2f}{unit}"

        yield Result(state=State.OK, summary=f"{field_name}: {total_output}")
        yield Metric("oracle_ios_f_total_%s" % metric_suffix, total)


def check_oracle_performance_iostat_bytes(
    item: str, params: Mapping[str, Any], section: SectionPerformance
) -> CheckResult:
    params = _get_subcheck_params(params, "iostat_bytes")
    data = _get_item_data(item, section)
    value_store = get_value_store()
    yield from _check_oracle_performance_iostat_file(
        value_store,
        time.time(),
        item,
        params,
        data,
        "bytes/s",
        [
            (8, "s_rb", "Small Read"),
            (9, "l_rb", "Large Read"),
            (10, "s_wb", "Small Write"),
            (11, "l_wb", "Large Write"),
        ],
    )


check_plugin_oracle_performance_iostat_bytes = CheckPlugin(
    name="oracle_performance_iostat_bytes",
    service_name="ORA %s Performance IO Stats Bytes",
    sections=["oracle_performance"],
    discovery_function=discover_oracle_performance_subcheck("iostat_bytes"),
    discovery_ruleset_name="oracle_performance_discovery",
    discovery_default_parameters={},
    check_function=check_oracle_performance_iostat_bytes,
    check_ruleset_name="oracle_performance",
    check_default_parameters={},
)


def check_oracle_performance_iostat_ios(
    item: str, params: Mapping[str, Any], section: SectionPerformance
) -> CheckResult:
    params = _get_subcheck_params(params, "iostat_ios")
    data = _get_item_data(item, section)
    value_store = get_value_store()
    yield from _check_oracle_performance_iostat_file(
        value_store,
        time.time(),
        item,
        params,
        data,
        "/s",
        [
            (0, "s_r", "Small Reads"),
            (1, "l_r", "Large Reads"),
            (2, "s_w", "Small Writes"),
            (3, "l_w", "Large Writes"),
        ],
    )


check_plugin_oracle_performance_iostat_ios = CheckPlugin(
    name="oracle_performance_iostat_ios",
    service_name="ORA %s Performance IO Stats Requests",
    sections=["oracle_performance"],
    discovery_function=discover_oracle_performance_subcheck("iostat_ios"),
    discovery_ruleset_name="oracle_performance_discovery",
    discovery_default_parameters={},
    check_function=check_oracle_performance_iostat_ios,
    check_ruleset_name="oracle_performance",
    check_default_parameters={},
)

#
# ORACLE Performance Waitclasses
#


def check_oracle_performance_waitclasses(
    item: str, params: Mapping[str, Any], section: SectionPerformance
) -> CheckResult:
    params = _get_subcheck_params(params, "waitclasses")
    data = _get_item_data(item, section)
    now = time.time()
    value_store = get_value_store()

    total_waited_sum = 0.0
    total_waited_sum_fg = 0.0

    # sys_wait_class -> wait_class
    waitclass_info = data.get("sys_wait_class", {})
    for waitclass in constants.ORACLE_WAITCLASSES:
        waitdata = waitclass_info.get(waitclass.name)
        if not waitdata:
            continue
        metric_start = "oracle_wait_class_%s" % waitclass.id
        for data_index, metric_suffix, infotext_suffix in [
            (1, "waited", "wait class"),
            (3, "waited_fg", "wait class (FG)"),
        ]:
            metric_name = f"{metric_start}_{metric_suffix}"
            rate = (
                get_rate(
                    value_store,
                    f"{item}.sys_wait_class.{metric_name}",
                    now,
                    waitdata[data_index],
                )
                / 100
            )

            if metric_suffix == "waited":
                total_waited_sum += rate
            else:
                total_waited_sum_fg += rate

            yield from check_levels(
                rate,
                metric_name=metric_name,
                levels_upper=params.get(metric_name),
                render_func=_unit_formatter("/s"),
                label=f"{waitclass.name} {infotext_suffix}",
                notice_only=True,
            )

    # Output totals
    for infoname, total_value, total_metric in [
        ("Total waited", total_waited_sum, "oracle_wait_class_total"),
        ("Total waited (FG)", total_waited_sum_fg, "oracle_wait_class_total_fg"),
    ]:
        yield from check_levels(
            total_value,
            metric_name=total_metric,
            levels_upper=params.get(total_metric),
            render_func=_unit_formatter("/s"),
            label=infoname,
        )


check_plugin_oracle_performance_waitclasses = CheckPlugin(
    name="oracle_performance_waitclasses",
    service_name="ORA %s Performance System Wait",
    sections=["oracle_performance"],
    discovery_function=discover_oracle_performance_subcheck("waitclasses"),
    discovery_ruleset_name="oracle_performance_discovery",
    discovery_default_parameters={},
    check_function=check_oracle_performance_waitclasses,
    check_ruleset_name="oracle_performance",
    check_default_parameters={},
)
