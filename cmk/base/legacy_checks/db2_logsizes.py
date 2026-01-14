#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError
from cmk.base.check_legacy_includes.df import df_check_filesystem_single
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs

check_info = {}

# <<<db2_logsizes>>>
# [[[db2taddm:CMDBS1]]]
# TIMESTAMP 1426495343
# usedspace 7250240
# logfilsiz 2048
# logprimary 6
# logsecond 100


def parse_db2_logsizes(string_table):
    pre_parsed = parse_db2_dbs(string_table)
    global_timestamp = pre_parsed[0]
    parsed = {}
    for key, values in pre_parsed[1].items():
        instance_info = {}
        for value in values:
            instance_info.setdefault(value[0], []).append(" ".join(map(str, (value[1:]))))
        # Some databases run in DPF mode. Means that the database is split over several nodes
        # Each node has its own logfile for the same database. We create one service for each logfile
        if "TIMESTAMP" not in instance_info:
            instance_info["TIMESTAMP"] = [global_timestamp]

        if "node" in instance_info:
            for node in instance_info["node"]:
                parsed[f"{key} DPF {node}"] = instance_info
        else:
            parsed[key] = instance_info

    return parsed


def discover_db2_logsizes(parsed):
    for db, db_info in parsed.items():
        if "logfilsiz" in db_info:
            yield db, {}


def check_db2_logsizes(item, params, parsed):
    db = parsed.get(item)

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

    if "node" in db:
        node_key = " ".join(item.split()[2:])
        for idx, node in enumerate(db["node"]):
            if node == node_key:
                data_offset = idx
    else:
        data_offset = 0

    timestamp = int(db["TIMESTAMP"][0])

    if "logfilsiz" not in db:
        return 3, "Invalid database info"

    total = (
        int(db["logfilsiz"][data_offset])
        * (int(db["logprimary"][data_offset]) + int(db["logsecond"][data_offset]))
        * 4096
    )
    usedspace = db["usedspace"][data_offset]
    if usedspace == "-":
        return 3, "Can not read usedspace"
    free = total - int(usedspace)

    return df_check_filesystem_single(
        item, total >> 20, free >> 20, 0, None, None, params, this_time=timestamp
    )


check_info["db2_logsizes"] = LegacyCheckDefinition(
    name="db2_logsizes",
    parse_function=parse_db2_logsizes,
    service_name="DB2 Logsize %s",
    discovery_function=discover_db2_logsizes,
    check_function=check_db2_logsizes,
    check_ruleset_name="db2_logsize",
    check_default_parameters={
        "levels": (-20.0, -10.0),  # Interpreted as free space in df_check_filesystem_single
    },
)
