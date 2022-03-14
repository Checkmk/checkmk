#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Dict, NamedTuple, Optional

from .agent_based_api.v1 import check_levels, IgnoreResultsError, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .utils import sap_hana


class Backup(NamedTuple):
    sys_end_time: Optional[int] = None
    backup_time_readable: Optional[str] = None
    state_name: Optional[str] = None
    comment: Optional[str] = None
    message: Optional[str] = None


def _get_sap_hana_backup_timestamp(backup_time_readable):
    try:
        t_struct = time.strptime(backup_time_readable, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return time.mktime(t_struct)


def parse_sap_hana_backup(string_table):
    parsed: Dict[str, Backup] = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        if len(lines) == 0:
            parsed[sid_instance] = Backup()
        for line in lines:
            if len(line) < 5:
                continue

            backup_time_readable = line[1].rsplit(".", 1)[0]
            backup_time_stamp = _get_sap_hana_backup_timestamp(backup_time_readable)
            parsed.setdefault(
                "%s - %s" % (sid_instance, line[0]),
                Backup(
                    sys_end_time=backup_time_stamp,
                    backup_time_readable=backup_time_readable,
                    state_name=line[2],
                    comment=line[3],
                    message=line[4],
                ),
            )
    return parsed


register.agent_section(
    name="sap_hana_backup",
    parse_function=parse_sap_hana_backup,
)


def discovery_sap_hana_backup(section):
    for sid in section:
        yield Service(item=sid)


def check_sap_hana_backup(item, params, section):
    now = time.time()

    data = section.get(item)
    if not data:
        raise IgnoreResultsError("Login into database failed.")

    if not data.state_name:
        yield Result(state=state.WARN, summary="No backup found")
        return

    state_name = data.state_name
    if state_name == "failed":
        cur_state = state.CRIT
    elif state_name in ["cancel pending", "canceled"]:
        cur_state = state.WARN
    elif state_name in ["ok", "successful", "running"]:
        cur_state = state.OK
    else:
        cur_state = state.UNKNOWN
    yield Result(state=cur_state, summary="Status: %s" % state_name)

    sys_end_time = data.sys_end_time
    if sys_end_time is not None:
        yield Result(state=state.OK, summary="Last: %s" % data.backup_time_readable)
        yield from check_levels(
            now - sys_end_time,
            metric_name="backup_age",
            levels_upper=params["backup_age"],
            render_func=render.timespan,
            label="Age",
        )

    comment = data.comment
    if comment:
        yield Result(state=state.OK, summary="Comment: %s" % comment)

    message = data.message
    if message:
        yield Result(state=state.OK, summary="Message: %s" % message)


def cluster_check_sap_hana_backup(
    item,
    params,
    section,
):
    # TODO: This is *not* a real cluster check. We do not evaluate the different node results with
    # each other, but this was the behaviour before the migration to the new Check API.
    yield Result(state=state.OK, summary="Nodes: %s" % ", ".join(section.keys()))
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
