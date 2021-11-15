#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Mapping, NamedTuple, Sequence, Tuple, TypedDict

from .agent_based_api.v1 import check_levels, Metric, register, Result, Service, State
from .agent_based_api.v1.render import percent, timespan
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class Hop(NamedTuple):
    name: str
    pl: float
    response_time: float
    rta: float
    rtmin: float
    rtmax: float
    rtstddev: float


Section = Mapping[str, Sequence[Hop]]


def parse_mtr(string_table: StringTable) -> Section:
    return {
        hostname: [
            Hop(
                name=rest[0 + 8 * hopnum],
                pl=float(rest[1 + 8 * hopnum].replace("%", "").rstrip()),
                response_time=float(rest[3 + 8 * hopnum]) / 1000,
                rta=float(rest[4 + 8 * hopnum]) / 1000,
                rtmin=float(rest[5 + 8 * hopnum]) / 1000,
                rtmax=float(rest[6 + 8 * hopnum]) / 1000,
                rtstddev=float(rest[7 + 8 * hopnum]) / 1000,
            )
            for hopnum in range(hopcount)
        ]
        for line in string_table
        for hostname, hopcount, rest in [(line[0], int(float(line[2])), line[3:])]
        if line and not line[0].startswith("**ERROR**")
    }


register.agent_section(
    name="mtr",
    parse_function=parse_mtr,
)


class CheckParams(TypedDict):
    rta: Tuple[int, int]
    rtstddev: Tuple[int, int]
    pl: Tuple[int, int]


def discover_mtr(section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _metrics_nonlast_hops(hops: Iterable[Hop]) -> Iterable[Metric]:
    for idx, hop in enumerate(
        hops,
        start=1,
    ):
        yield Metric("hop_%d_rta" % idx, hop.rta)
        yield Metric("hop_%d_rtmin" % idx, hop.rtmin)
        yield Metric("hop_%d_rtmax" % idx, hop.rtmax)
        yield Metric("hop_%d_rtstddev" % idx, hop.rtstddev)
        yield Metric("hop_%d_response_time" % idx, hop.response_time)
        yield Metric("hop_%d_pl" % idx, hop.pl)


def _check_last_hop(
    params: CheckParams,
    last_hop: Hop,
    last_idx: int,
) -> CheckResult:

    yield from check_levels(
        last_hop.pl,
        levels_upper=params["pl"],
        metric_name="hop_%d_pl" % last_idx,
        render_func=percent,
        label="Packet loss",
    )

    yield from check_levels(
        last_hop.rta,
        levels_upper=(params["rta"][0] / 1000, params["rta"][1] / 1000),
        metric_name="hop_%d_rta" % last_idx,
        render_func=timespan,
        label="Round trip average",
    )

    yield from check_levels(
        last_hop.rtstddev,
        levels_upper=(params["rtstddev"][0] / 1000, params["rtstddev"][1] / 1000),
        metric_name="hop_%d_rtstddev" % last_idx,
        render_func=timespan,
        label="Standard deviation",
    )

    yield Metric("hop_%d_rtmin" % last_idx, last_hop.rtmin)
    yield Metric("hop_%d_rtmax" % last_idx, last_hop.rtmax)
    yield Metric("hop_%d_response_time" % last_idx, last_hop.response_time)


def check_mtr(
    item: str,
    params: CheckParams,
    section: Section,
) -> CheckResult:
    if (hops := section.get(item)) is None:
        return

    if not hops:
        yield Result(
            state=State.UNKNOWN,
            summary="Insufficient data: No hop information available",
        )
        return

    yield Result(
        state=State.OK,
        summary="Number of Hops: %d" % len(hops),
        details="\n".join(
            "Hop %d: %s"
            % (
                idx + 1,
                hop.name,
            )
            for idx, hop in enumerate(hops)
        ),
    )
    yield Metric("hops", len(hops))

    yield from _metrics_nonlast_hops(hops[:-1])
    yield from _check_last_hop(
        params,
        hops[-1],
        len(hops),
    )


register.check_plugin(
    name="mtr",
    service_name="Mtr to %s",
    discovery_function=discover_mtr,
    check_function=check_mtr,
    check_default_parameters={
        "pl": (10, 25),
        "rta": (150, 250),
        "rtstddev": (150, 250),
    },
    check_ruleset_name="mtr",
)
