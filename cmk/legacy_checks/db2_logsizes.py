#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs
from cmk.plugins.lib.df import df_check_filesystem_single

Section = Mapping[str, Mapping[str, list[str]]]

# <<<db2_logsizes>>>
# [[[db2taddm:CMDBS1]]]
# TIMESTAMP 1426495343
# usedspace 7250240
# logfilsiz 2048
# logprimary 6
# logsecond 100


def parse_db2_logsizes(string_table: StringTable) -> Section:
    pre_parsed = parse_db2_dbs(string_table)
    global_timestamp = pre_parsed[0]
    parsed: dict[str, dict[str, list[str]]] = {}
    for key, values in pre_parsed[1].items():
        instance_info: dict[str, list[str]] = {}
        for value in values:
            instance_info.setdefault(value[0], []).append(" ".join(map(str, (value[1:]))))
        # Some databases run in DPF mode. Means that the database is split over several nodes
        # Each node has its own logfile for the same database. We create one service for each logfile
        if "TIMESTAMP" not in instance_info and global_timestamp is not None:
            instance_info["TIMESTAMP"] = [str(global_timestamp)]

        if "node" in instance_info:
            for node in instance_info["node"]:
                parsed[f"{key} DPF {node}"] = instance_info
        else:
            parsed[key] = instance_info

    return parsed


def discover_db2_logsizes(section: Section) -> DiscoveryResult:
    for db, db_info in section.items():
        if "logfilsiz" in db_info:
            yield Service(item=db)


def _check_db2_logsizes(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    db = section.get(item)

    if not db:
        raise IgnoreResultsError("Login into database failed")

    # A DPF instance could look like
    # {'TIMESTAMP': ['1439976757'],
    #  u'logfilsiz': ['20480', '20480', '20480', '20480', '20480', '20480'],
    #  u'logprimary': ['13', '13', '13', '13', '13', '13'],
    #  u'logsecond': ['100', '100', '100', '100', '100', '100'],
    #  u'node': ['0 wasv091 0',
    #            '1 wasv091 1',
    #            '2 wasv091 2',
    #            '3 wasv091 3',
    #            '4 wasv091 4',
    #            '5 wasv091 5'],

    data_offset = 0
    if "node" in db:
        node_key = " ".join(item.split()[2:])
        for idx, node in enumerate(db["node"]):
            if node == node_key:
                data_offset = idx

    timestamp = int(db["TIMESTAMP"][0])

    if "logfilsiz" not in db:
        yield Result(state=State.UNKNOWN, summary="Invalid database info")
        return

    total = (
        int(db["logfilsiz"][data_offset])
        * (int(db["logprimary"][data_offset]) + int(db["logsecond"][data_offset]))
        * 4096
    )
    usedspace = db["usedspace"][data_offset]
    if usedspace == "-":
        yield Result(state=State.UNKNOWN, summary="Can not read usedspace")
        return
    free = total - int(usedspace)

    yield from df_check_filesystem_single(
        value_store=value_store,
        mountpoint=item,
        filesystem_size=total >> 20,
        free_space=free >> 20,
        reserved_space=0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
        this_time=timestamp,
    )


def check_db2_logsizes(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _check_db2_logsizes(get_value_store(), item, params, section)


agent_section_db2_logsizes = AgentSection(
    name="db2_logsizes",
    parse_function=parse_db2_logsizes,
)


check_plugin_db2_logsizes = CheckPlugin(
    name="db2_logsizes",
    service_name="DB2 Logsize %s",
    discovery_function=discover_db2_logsizes,
    check_function=check_db2_logsizes,
    check_ruleset_name="db2_logsize",
    check_default_parameters={
        "levels": (-20.0, -10.0),  # Interpreted as free space in df_check_filesystem_single
    },
)
