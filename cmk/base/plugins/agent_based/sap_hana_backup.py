#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, Dict, Mapping, Optional, Union

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import sap_hana

Section = Mapping[str, Mapping[str, Union[float, str]]]


def _get_sap_hana_backup_timestamp(backup_time_readable: str) -> Optional[float]:
    try:
        t_struct = time.strptime(backup_time_readable, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return time.mktime(t_struct)


def parse_sap_hana_backup(string_table: StringTable) -> Section:
    parsed: Dict[str, Dict] = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        for line in lines:
            if len(line) < 5:
                continue

            parsed.setdefault(
                "%s - %s" % (sid_instance, line[0]), {
                    "end_time": _get_sap_hana_backup_timestamp(line[1].rsplit(".", 1)[0]),
                    "state_name": line[2],
                    "comment": line[3],
                    "message": line[4],
                })
    return parsed


register.agent_section(
    name="sap_hana_backup",
    parse_function=parse_sap_hana_backup,
)


def discovery_sap_hana_backup(section: Section) -> DiscoveryResult:
    for sid in section:
        yield Service(item=sid)


def check_sap_hana_backup(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    now = time.time()

    data = section.get(item)
    if data is None:
        return

    state_name = data['state_name']
    if state_name == 'failed':
        cur_state = State.CRIT
    elif state_name in ['cancel pending', 'canceled']:
        cur_state = State.WARN
    elif state_name in ['ok', 'successful', 'running']:
        cur_state = State.OK
    else:
        cur_state = State.UNKNOWN
    yield Result(state=cur_state, summary="Status: %s" % state_name)

    if (end_time := data.get('end_time')) is not None:
        assert isinstance(end_time, float)
        yield Result(state=State.OK, summary="Last: %s" % render.datetime(end_time))
        yield from check_levels(now - end_time,
                                metric_name="backup_age",
                                levels_upper=params['backup_age'],
                                render_func=render.timespan,
                                label="Age")

    comment = data["comment"]
    if comment:
        yield Result(state=State.OK, summary="Comment: %s" % comment)

    message = data["message"]
    if message:
        yield Result(state=State.OK, summary="Message: %s" % message)


def cluster_check_sap_hana_backup(
    item: str,
    params: Mapping[str, Any],
    section,
):
    # TODO: This is *not* a real cluster check. We do not evaluate the different node results with
    # each other, but this was the behaviour before the migration to the new Check API.
    yield Result(state=State.OK, summary='Nodes: %s' % ', '.join(section.keys()))
    for node_section in section.values():
        if item in node_section:
            yield from check_sap_hana_backup(item, params, node_section)
            return


register.check_plugin(
    name="sap_hana_backup",
    service_name="SAP HANA Backup %s",
    discovery_function=discovery_sap_hana_backup,
    check_default_parameters={"backup_age": (24 * 60 * 60, 2 * 24 * 60 * 60)},
    check_ruleset_name="sap_hana_backup",
    check_function=check_sap_hana_backup,
    cluster_check_function=cluster_check_sap_hana_backup,
)
