#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Dict, List, Mapping, NamedTuple, Optional, Tuple, Union

from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

from .agent_based_api.v1 import (
    get_average,
    get_value_store,
    Metric,
    register,
    render,
    Result,
    Service,
    State as state,
)

from .utils import memory


class MemBytes(NamedTuple('MemBytes', [('bytes', int), ('kb', float), ('mb', float)])):
    def __new__(cls, value: Union[float, int]):
        return super(MemBytes, cls).__new__(cls, int(value * 1024), float(value), value / 1024.0)

    def render(self) -> str:
        return render.bytes(self.bytes)


def discover_mem_used(section: Dict[str, int]) -> DiscoveryResult:
    if ("MemTotal" in section and "PageTotal" not in section and
            not memory.is_linux_section(section)  # handled by more modern check
       ):
        yield Service()


def _get_total_usage(
    ramused: MemBytes,
    swapused: Optional[MemBytes],
    pagetables: Optional[MemBytes],
) -> Tuple[MemBytes, str]:
    """get total usage and a description how it was computed
    """
    totalused_kb = ramused.kb
    details = ["RAM"]

    if swapused:
        totalused_kb += swapused.kb
        details.append("Swap")

    if pagetables:
        totalused_kb += pagetables.kb
        details.append("Pagetables")

    totalused = MemBytes(totalused_kb)
    if len(details) == 1:
        return totalused, details[0]
    return totalused, "Total (%s)" % " + ".join(details)


def check_mem_used(params: Mapping, section: Dict[str, int]) -> CheckResult:
    # we have used a parse function that creates bytes, but this function
    # still expects kB:
    meminfo = {k: v / 1024.0 for k, v in section.items()}

    if isinstance(params, tuple):
        params = {"levels": params}

    memtotal = MemBytes(meminfo['MemTotal'])
    memused = MemBytes(memtotal.kb - meminfo['MemFree'])

    swaptotal: Optional[MemBytes] = None
    swapused: Optional[MemBytes] = None
    metrics: List[Metric] = []
    if "SwapFree" in meminfo:
        swaptotal = MemBytes(meminfo['SwapTotal'])
        swapused = MemBytes(swaptotal.kb - meminfo['SwapFree'])
        metrics = [Metric('swap_used', swapused.bytes, boundaries=(0, swaptotal.bytes))]

    # Size of Pagetable on Linux can be relevant e.g. on ORACLE
    # servers with much memory, that do not use HugeTables. We account
    # that for used
    pagetables: Optional[MemBytes] = None
    if 'PageTables' in meminfo:
        pagetables = MemBytes(meminfo['PageTables'])
        metrics.append(Metric('mem_lnx_page_tables', pagetables.bytes))

    # Buffers and Cached are optional. On Linux both mean basically the same.
    caches = MemBytes(meminfo.get('Buffers', 0) + meminfo.get('Cached', 0))

    ramused = MemBytes(memused.kb - caches.kb)
    metrics.append(Metric('mem_used', ramused.bytes, boundaries=(0, memtotal.bytes)))
    metrics.append(
        Metric('mem_used_percent', 100. * ramused.bytes / memtotal.bytes, boundaries=(0, 100.)))

    totalused, totalused_descr = _get_total_usage(ramused, swapused, pagetables)

    result, *_ = memory.check_element(
        totalused_descr,
        totalused.bytes,
        memtotal.bytes,
        ("ignore", (None, None)),
        label_total="RAM" if totalused_descr != "RAM" else "",
    )
    assert isinstance(result, Result)
    infotext = result.summary

    # Take into account averaging
    average_min = params.get("average")
    if average_min:
        totalused_mb_avg = get_average(
            get_value_store(),
            "mem.used.total",
            time.time(),
            totalused.mb,
            average_min,
        )
        totalused_perc_avg = totalused_mb_avg / memtotal.mb * 100
        infotext += ", %d min average %.1f%%" % (average_min, totalused_perc_avg)
        metrics.append(Metric('memusedavg', totalused_mb_avg))
        comp_mb = totalused_mb_avg
    else:
        comp_mb = totalused.mb

    # Normalize levels and check them
    totalvirt = MemBytes((swaptotal.kb if swaptotal is not None else 0) + memtotal.kb)
    warn, crit = params.get("levels", (None, None))
    mode = memory.get_levels_mode_from_value(warn)
    warn_mb, crit_mb, levels_text = memory.normalize_levels(
        mode,
        abs(warn),
        abs(crit),
        totalvirt.mb,
        _perc_total=memtotal.mb,
        render_unit=1024**2,
    )
    assert warn_mb is not None and crit_mb is not None
    metrics.append(
        Metric(
            'mem_lnx_total_used',
            totalused.bytes,
            levels=(warn_mb * 1024**2, crit_mb * 1024**2),
            boundaries=(0, totalvirt.bytes),
        ))

    # Check levels
    my_state = memory.compute_state(comp_mb, warn_mb, crit_mb)
    if my_state != state.OK and levels_text:
        infotext = "%s (%s)" % (infotext, levels_text)

    yield Result(state=my_state, summary=infotext)
    yield from metrics

    if totalused_descr != "RAM":
        yield from memory.check_element(
            "RAM",
            ramused.bytes,  # <- caches subtracted
            memtotal.bytes,
            ("ignore", (None, None)),
        )
        if swaptotal is not None and swaptotal.bytes:
            assert swapused is not None
            yield from memory.check_element(
                "Swap",
                swapused.bytes,
                swaptotal.bytes,
                ("ignore", (None, None)),
            )
        if pagetables:
            yield Result(state=state.OK, summary="Pagetables: %s" % pagetables.render())

    # Add additional metrics, provided by Linux.
    if meminfo.get('Mapped'):
        for key, label, metric in (
            ('Mapped', 'Mapped', 'mem_lnx_mapped'),
            ('Committed_AS', 'Committed', 'mem_lnx_committed_as'),
            ('Shmem', 'Shared', 'mem_lnx_shmem'),
        ):
            value = MemBytes(meminfo.get(key, 0))
            yield Result(state=state.OK, summary="%s: %s" % (label, value.render()))
            yield Metric(metric, value.bytes)


register.check_plugin(
    name="mem_used",
    service_name="Memory",
    sections=["mem"],
    discovery_function=discover_mem_used,
    check_function=check_mem_used,
    check_default_parameters={
        "levels": (150.0, 200.0),
    },
    check_ruleset_name="memory",
)
