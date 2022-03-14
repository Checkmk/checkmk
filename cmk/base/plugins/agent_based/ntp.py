#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<ntp>>>
# - 42.202.61.100   .INIT.          16 u    - 1024    0    0.000    0.000   0.000
# * 42.202.62.100   .PPS.            1 u  143  256  377    0.763   -1.424   0.404
# % 42.202.61.14    42.202.62.100    2 u  160  256  357    0.058   -1.532   1.181
# % 42.202.62.14    42.202.62.100    2 u  194  256  357    0.131   -1.364   0.598
# % 42.202.61.10    .INIT.          16 u    - 1024    0    0.000    0.000   0.000

# % 42.202.62.10    .INIT.          16 u    - 1024    0    0.000    0.000   0.000
# + 42.202.61.15    42.202.62.100    2 u  196  256  356    0.058    0.574   0.204
# + 42.202.62.15    42.202.62.100    2 u  186  256  276    0.088    0.716   0.165
# % 127.127.1.0     .LOCL.          10 l   40   64  377    0.000    0.000   0.001
import time
from typing import Any, Dict, Final, Mapping, NamedTuple, Optional

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.timesync import tolerance_check


class Peer(NamedTuple):
    statecode: str
    name: str
    refid: str
    stratum: int
    when: int
    reach: str
    offset: float
    jitter: float


Section = Dict[Optional[str], Peer]
NTP_STATE_CODES: Final[Mapping[str, str]] = {
    "x": "falsetick",
    ".": "excess",
    "-": "outlyer",
    "+": "candidat",
    "#": "selected",
    "*": "sys.peer",
    "o": "pps.peer",
    "%": "discarded",
}


def _ntp_fmt_time(raw: str) -> int:
    if raw == "-":
        return 0
    if raw[-1] == "m":
        return int(raw[:-1]) * 60
    if raw[-1] == "h":
        return int(raw[:-1]) * 60 * 60
    if raw[-1] == "d":
        return int(raw[:-1]) * 60 * 60 * 24
    return int(raw)


def parse_ntp(string_table: StringTable) -> Section:
    """
    >>> parse_ntp([])
    {}
    >>> parse_ntp(["- 42.202.61.100 .INIT. 16 u - 1024 0 0.000 0.000 0.000".split(' ')])
    {'42.202.61.100': Peer(statecode='-', name='42.202.61.100', refid='.INIT.', stratum=16, when=0, reach='0', offset=0.0, jitter=0.0)}
    """
    section: Section = {}
    for line in string_table:
        if len(line) != 11 or line == [
            "%",
            "remote",
            "refid",
            "st",
            "t",
            "when",
            "poll",
            "reach",
            "delay",
            "offset",
            "jitter",
        ]:
            #  sometimes we get a header in the agent section:
            #  %     remote           refid      st t when poll reach   delay   offset  jitter
            #  = =============================================================================
            continue
        peer = Peer(
            statecode=line[0],
            name=line[1],
            refid=line[2],
            stratum=int(line[3]),
            when=_ntp_fmt_time(line[5]),
            reach=line[7],
            offset=float(line[9]),
            jitter=float(line[10]),
        )
        section[peer.name] = peer
        if None not in section and peer.statecode in "*o":  # keep first one!
            section[None] = peer

    return section


register.agent_section(
    name="ntp",
    parse_function=parse_ntp,
)


# We monitor all servers we have reached at least once
def discover_ntp(
    params: Mapping[str, Any],
    section: Section,
) -> DiscoveryResult:
    """
    >>> list(discover_ntp({}, {}))
    []
    >>> section = {'42.202.62.100': Peer(statecode='*', name='42.202.62.100', refid='.PPS.', stratum=1, when=143, reach='377', offset=-1.424, jitter=0.404), None: Peer(statecode='*', name='42.202.62.100', refid='.PPS.', stratum=1, when=143, reach='377', offset=-1.424, jitter=0.404)}
    >>> list(discover_ntp({"mode": "detailed"}, section))
    [Service(item='42.202.62.100'), Service(item='42.202.62.100')]
    """
    if params.get("mode", "summary") not in ("detailed", "both"):
        return

    for peer in section.values():
        if peer.reach != "0" and peer.refid != ".LOCL.":
            yield Service(item=peer.name)


def discover_ntp_summary(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    if params.get("mode", "summary") in ("summary", "both") and section:
        yield Service()


def check_ntp(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    peer = section.get(item)
    if peer is None:
        return
    if peer.reach == "0":
        yield Result(state=State.UNKNOWN, summary=f"Peer {peer.name} is unreachable")
        return

    crit_stratum, warn, crit = params["ntp_levels"]
    yield from check_levels(
        value=peer.offset,
        levels_upper=(warn, crit),
        levels_lower=(-warn, -crit),
        metric_name="offset",
        render_func=lambda f: "%.4f ms" % f,
        label="Offset",
    )
    yield from check_levels(
        value=peer.stratum,
        levels_upper=(crit_stratum, crit_stratum),
        render_func=lambda d: str(int(d)),
        label="Stratum",
    )
    yield from check_levels(
        value=peer.jitter,
        metric_name="jitter",
        render_func=lambda f: "%.4f ms" % f,
        label="Jitter",
    )

    if peer.when > 0:
        yield Result(
            state=State.OK, summary="Time since last sync: %s" % render.timespan(peer.when)
        )

    state = NTP_STATE_CODES.get(peer.statecode, "unknown")
    if state == "falsetick":
        yield Result(state=State.CRIT, summary="")
    else:
        yield Result(state=State.OK, notice=f"State: {state}")


def check_ntp_summary(
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    # We only are interested in our system peer or pulse per second source (pps)
    peer = section.get(None)
    if peer is None:
        if section:
            yield Result(
                state=State.OK, summary=f"Found {len(section)} peers, but none is suitable"
            )
        yield from tolerance_check(
            set_sync_time=None,
            levels_upper=params.get("alert_delay"),
            notice_only=False,
            now=time.time(),
            value_store=get_value_store(),
        )
        return

    if isinstance(params, tuple):
        params = {
            "ntp_levels": params,
            "alert_delay": (300, 3600),
        }

    yield from check_ntp(peer.name, params, section)
    yield from tolerance_check(
        set_sync_time=time.time(),
        levels_upper=params.get("alert_delay"),
        notice_only=True,
        now=time.time(),
        value_store=get_value_store(),
    )
    yield Result(state=State.OK, notice=f"Synchronized on {peer.name}")


DEFAULT_PARAMETERS: Final[Dict[str, Any]] = {
    "ntp_levels": (10, 200.0, 500.0),  # stratum, ms offset
    "alert_delay": (300, 3600),
}

register.check_plugin(
    name="ntp",
    service_name="NTP Peer %s",
    discovery_function=discover_ntp,
    check_function=check_ntp,
    check_default_parameters=DEFAULT_PARAMETERS,
    check_ruleset_name="ntp_peer",
    discovery_default_parameters={},
    discovery_ruleset_name="ntp_discovery",
)

register.check_plugin(
    name="ntp_time",
    sections=["ntp"],
    service_name="NTP Time",
    discovery_function=discover_ntp_summary,
    check_function=check_ntp_summary,
    check_default_parameters=DEFAULT_PARAMETERS,
    check_ruleset_name="ntp_time",
    discovery_default_parameters={},
    discovery_ruleset_name="ntp_discovery",
)
