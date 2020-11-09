#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<chrony>>>
# Reference ID    : 212.18.3.18 (ntp1.m-online.net)
# Stratum         : 3
# Ref time (UTC)  : Tue Aug 19 16:56:21 2014
# System time     : 0.000000353 seconds fast of NTP time
# Frequency       : 10.725 ppm slow
# Residual freq   : 195.475 ppm
# Skew            : 10.639 ppm
# Root delay      : 0.027455 seconds
# Root dispersion : 0.024512 seconds

# <<<chrony>>>
# 506 Cannot talk to daemon
from typing import Any, Dict

from .agent_based_api.v1 import check_levels, register, Result, Service, State as state


def parse_chrony(string_table):
    """
    parse info list into dictionary

    >>> import pprint
    >>> pprint.pprint(parse_chrony([
    ...     ['Reference', 'ID', ':', '0.0.0.0', '()'],
    ...     ['Stratum', ':', '0'],
    ...     ['Ref', 'time', '(UTC)', ':', 'Thu', 'Jan', '1', '00:00:00', '1970'],
    ... ]))
    {'Reference ID': '0.0.0.0 ()', 'Stratum': 0, 'address': '()'}

    :param string_table: chrony output as lists
    :return: dictionary
    """
    if is_error_message(string_table):
        return {"error": " ".join(string_table[0])}

    parsed: Dict[str, Any] = {}
    for line in string_table:
        if ":" in line:
            key, value = [e.strip() for e in " ".join(line).split(":", 1)]
            if key == "Reference ID":
                parsed[key] = value
                try:
                    parsed['address'] = value.split(' ')[1]
                except IndexError:
                    pass
            elif key == "System time":
                try:
                    parsed[key] = float(value.split(' ')[0]) * 1000
                except ValueError:
                    pass
            elif key == "Stratum":
                try:
                    parsed[key] = int(value)
                except ValueError:
                    pass

    return parsed or None


def is_error_message(info):
    return len(info) == 1 and isinstance(info[0], list) and ":" not in info[0][0]


register.agent_section(
    name="chrony",
    parse_function=parse_chrony,
)


def discover_chrony(section_chrony, section_ntp):
    if not section_chrony:
        return
    if section_ntp and "error" in section_chrony:
        # an error is OK if npt sync is present
        return
    yield Service()


def check_chrony(params, section_chrony, section_ntp):
    """
    check if agent returned error message
    check if chrony can reach NTP servers
    check if sys_time_offset_offset is in range
    check if stratum is too high
    """
    if "error" in section_chrony:
        yield Result(state=state.CRIT, summary="%s" % section_chrony["error"])
        return

    if isinstance(params, tuple):
        params = {
            "ntp_levels": params,
            "alert_delay": (300, 3600),
        }
    crit_stratum, warn, crit = params["ntp_levels"]

    ref_id = section_chrony.get("Reference ID")
    address = section_chrony.get("address")
    sys_time_offset = section_chrony.get("System time")
    stratum = section_chrony.get("Stratum")

    if address in (None, "", "()"):
        # if brackets are empty, NTP servers are unreachable
        address = "unreachable"

    yield Result(
        state=state.WARN if address == "unreachable" else state.OK,
        notice=f"NTP servers: {address}\nReference ID: {ref_id}",
    )

    if sys_time_offset is not None:
        yield from check_levels(
            abs(sys_time_offset),
            levels_upper=(warn, crit),
            metric_name="offset",
            render_func=lambda x: "%.4f ms" % x,
            label="Offset",
        )

    if stratum is not None:
        yield from check_levels(
            stratum,
            levels_upper=(crit_stratum, crit_stratum),
            render_func=lambda v: "%d" % v,
            label="Stratum",
        )


register.check_plugin(
    name="chrony",
    service_name="NTP Time",
    sections=["chrony", "ntp"],
    discovery_function=discover_chrony,
    check_function=check_chrony,
    check_default_parameters={
        "ntp_levels": (10, 200.0, 500.0),
        "alert_delay": (300, 3600),
    },
    check_ruleset_name="ntp_time",
)
