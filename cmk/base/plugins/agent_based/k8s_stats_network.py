#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
from contextlib import suppress
from typing import Any, Mapping, MutableMapping, Optional

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
    Metric,
    register,
    render,
    Service,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.k8s import Interface, Section, to_interface

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def discover_k8s_stats_network(
    section_k8s_stats: Optional[Section],
    section_lnx_if: Optional[Section],
) -> DiscoveryResult:
    """
    >>> for service in discover_k8s_stats_network({
    ...     'filesystem': {"not": "needed"},
    ...     'interfaces': {'eth1': [{'rx_packets': 573200, 'tx_packets': 544397, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 371123972, 'tx_bytes': 1358359683, 'rx_dropped': 0, 'tx_dropped': 0}], 'eth0': [{'rx_packets': 465930, 'tx_packets': 184527, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 468641826, 'tx_bytes': 11076147, 'rx_dropped': 0, 'tx_dropped': 0}], 'sit0': [{'rx_packets': 0, 'tx_packets': 0, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 0, 'tx_bytes': 0, 'rx_dropped': 0, 'tx_dropped': 0}]},
    ...     'timestamp': 1553765630.0,
    ... }, None):
    ...   print(service)
    Service(item='eth1')
    Service(item='eth0')
    Service(item='sit0')
    """
    # don't use the k8s check if the check_mk_agent delivers interface data
    if section_lnx_if is not None:
        return

    assert section_k8s_stats is not None

    yield from (Service(item=interface) for interface in section_k8s_stats["interfaces"])


def _k8s_network_err_pac(
    value_store: MutableMapping[str, Any],
    interface: Interface,
    params: Mapping[str, Any],
    now: float,
) -> CheckResult:
    warn, crit = params.get("errors", (None, None))

    for name, pway in (("Input", "in"), ("Output", "out")):
        # Split error handling to ensure both rates get initialized on first run
        pac_rate, err_rate = None, None
        with suppress(GetRateError):
            pac_rate = get_rate(
                value_store,
                "if_%s_pkts" % pway,
                now,
                interface["rx_packets"] if name == "Input" else interface["tx_packets"],
            )
        with suppress(GetRateError):
            err_rate = get_rate(
                value_store,
                "if_%s_errors" % pway,
                now,
                interface["rx_errors"] if name == "Input" else interface["tx_errors"],
            )
        if pac_rate is None or err_rate is None:
            continue

        yield Metric("if_%s_pkts" % pway, pac_rate, boundaries=(0, None))
        yield Metric("if_%s_errors" % pway, err_rate, boundaries=(0, None))

        if isinstance(warn, float) and isinstance(crit, float):
            yield from check_levels(
                value=(100.0 * err_rate / (err_rate + pac_rate)) if (err_rate + pac_rate) else 0,
                levels_upper=(warn, crit),
                render_func=render.percent,
                label="%s errors" % name,
                boundaries=(0, None),
            )
        else:  # absolute levels or no levels
            yield from check_levels(
                value=err_rate,
                levels_upper=(warn, crit),
                render_func=lambda value: "%.2f/s" % value,
                label="%s error rate" % name,
                boundaries=(0, None),
            )


def _check__k8s_stats_network__core(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    now = section["timestamp"]

    empty: collections.Counter[str] = collections.Counter()
    interface = to_interface(
        sum(
            (collections.Counter(intf) for intf in section["interfaces"][item]),
            empty,
        )
    )

    # Bandwidth
    for name, dsname in (("In", "in"), ("Out", "out")):
        with suppress(GetRateError):
            yield from check_levels(
                value=get_rate(
                    value_store,
                    dsname,
                    now,
                    interface["rx_bytes"] if name == "In" else interface["tx_bytes"],
                ),
                metric_name=dsname,
                render_func=render.networkbandwidth,
                label=name,
            )

    # Errors / Packets
    yield from _k8s_network_err_pac(value_store, interface, params, now)

    # Discards
    for name, met, dsname in [
        ("Input Discards", "rx", "if_in_discards"),
        ("Output Discards", "tx", "if_out_discards"),
    ]:
        with suppress(GetRateError):
            yield from check_levels(
                value=get_rate(
                    value_store,
                    dsname,
                    now,
                    interface["rx_dropped"] if met == "rx" else interface["tx_dropped"],
                ),
                metric_name=dsname,
                levels_upper=params.get("discards"),
                render_func=lambda v: "%.2f/s" % v,
                label=name,
                boundaries=(0, None),
            )


def _check__k8s_stats_network__proxy_results(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    section_k8s_stats: Optional[Section],
    section_lnx_if: Optional[Section],
) -> CheckResult:
    """Call _check__k8s_stats_network__core() and handle empty or not yet valid input
    >>> vs = {}
    >>> for i in range(2):
    ...   print("run", i)
    ...   for result in _check__k8s_stats_network__proxy_results(vs, "eth1", {}, {
    ...       'interfaces': {'eth1': [{'rx_packets': 573200, 'tx_packets': 544397, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 371123972, 'tx_bytes': 1358359683, 'rx_dropped': 0, 'tx_dropped': 0}], 'eth0': [{'rx_packets': 465930, 'tx_packets': 184527, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 468641826, 'tx_bytes': 11076147, 'rx_dropped': 0, 'tx_dropped': 0}], 'sit0': [{'rx_packets': 0, 'tx_packets': 0, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 0, 'tx_bytes': 0, 'rx_dropped': 0, 'tx_dropped': 0}]},
    ...       'timestamp': 1600000000 + i,
    ...   }, None):
    ...     print(result)
    run 0
    Counters initialized
    run 1
    Result(state=<State.OK: 0>, summary='In: 0.00 Bit/s')
    Metric('in', 0.0)
    Result(state=<State.OK: 0>, summary='Out: 0.00 Bit/s')
    Metric('out', 0.0)
    Metric('if_in_pkts', 0.0, boundaries=(0.0, None))
    Metric('if_in_errors', 0.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Input error rate: 0.00/s')
    Metric('if_out_pkts', 0.0, boundaries=(0.0, None))
    Metric('if_out_errors', 0.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Output error rate: 0.00/s')
    Result(state=<State.OK: 0>, summary='Input Discards: 0.00/s')
    Metric('if_in_discards', 0.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Output Discards: 0.00/s')
    Metric('if_out_discards', 0.0, boundaries=(0.0, None))
    """
    if section_k8s_stats is None:
        return

    results = tuple(_check__k8s_stats_network__core(value_store, item, params, section_k8s_stats))

    if not results:
        yield IgnoreResults("Counters initialized")

    yield from results


def check_k8s_stats_network(
    item: str,
    params: Mapping[str, Any],
    section_k8s_stats: Optional[Section],
    section_lnx_if: Optional[Section],
) -> CheckResult:
    """This is an API conformant wrapper for the more functional base functions"""
    yield from _check__k8s_stats_network__proxy_results(
        get_value_store(),
        item,
        params,
        section_k8s_stats,
        section_lnx_if,
    )


register.check_plugin(
    name="k8s_stats_network",
    sections=["k8s_stats", "lnx_if"],
    service_name="Interface %s",
    discovery_function=discover_k8s_stats_network,
    check_default_parameters={},
    check_ruleset_name="k8s_if",
    check_function=check_k8s_stats_network,
)
