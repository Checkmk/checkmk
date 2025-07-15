#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_svc import parse_ibm_svc_with_header

check_info = {}

# Example output from agent:
# <<<ibm_svc_host:sep(58)>>>
# 0:h_esx01:2:4:degraded
# 1:host206:2:2:online
# 2:host105:2:2:online
# 3:host106:2:2:online

Section = Mapping


def parse_ibm_svc_host(string_table):
    dflt_header = [
        "id",
        "name",
        "port_count",
        "iogrp_count",
        "status",
        "site_id",
        "site_name",
        "host_cluster_id",
        "host_cluster_name",
    ]
    return parse_ibm_svc_with_header(string_table, dflt_header)


def discover_ibm_svc_host(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_ibm_svc_host(item, params, parsed):
    if params is None:
        # Old inventory rule until version 1.2.7
        # params were None instead of empty dictionary
        params = {"always_ok": False}

    degraded = 0
    offline = 0
    active = 0
    inactive = 0
    other = 0
    for rows in parsed.values():
        for data in rows:
            status = data["status"]
            if status == "degraded":
                degraded += 1
            elif status == "offline":
                offline += 1
            elif status in ["active", "online"]:
                active += 1
            elif status == "inactive":
                inactive += 1
            else:
                other += 1

    if "always_ok" in params:
        # Old configuration rule
        # This was used with only one parameter always_ok until version 1.2.7
        perfdata = [
            ("active", active),
            ("inactive", inactive),
            ("degraded", degraded),
            ("offline", offline),
            ("other", other),
        ]
        yield 0, f"{active} active, {inactive} inactive", perfdata

        if degraded > 0:
            yield (not params["always_ok"] and 1 or 0), "%s degraded" % degraded
        if offline > 0:
            yield (not params["always_ok"] and 2 or 0), "%s offline" % offline
        if other > 0:
            yield (not params["always_ok"] and 1 or 0), "%s in an unidentified state" % other
    else:
        warn, crit = params.get("active_hosts", (None, None))

        if crit is not None and active <= crit:
            yield 2, "%s active" % active
        elif warn is not None and active <= warn:
            yield 1, "%s active" % active
        else:
            yield 0, "%s active" % active

        for ident, value in [
            ("inactive", inactive),
            ("degraded", degraded),
            ("offline", offline),
            ("other", other),
        ]:
            warn, crit = params.get(ident + "_hosts", (None, None))

            if crit is not None and value >= crit:
                state = 2
            if warn is not None and value >= warn:
                state = 1
            else:
                state = 0
            yield state, f"{value} {ident}", [(ident, value, warn, crit)]


check_info["ibm_svc_host"] = LegacyCheckDefinition(
    name="ibm_svc_host",
    parse_function=parse_ibm_svc_host,
    service_name="Hosts",
    discovery_function=discover_ibm_svc_host,
    check_function=check_ibm_svc_host,
    check_ruleset_name="ibm_svc_host",
)
