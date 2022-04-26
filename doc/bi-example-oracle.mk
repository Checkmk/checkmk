#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[name-defined]
# pylint: disable=undefined-variable

aggregation_rules["oracle_log"] = (
    "Logfiles",
    ["HOST", "DB"],
    "worst",
    [
        # LOG /OraBase/Logfiles/Archive/rman-nbu.sh.archive_MP18
        ("$HOST$", "LOG /OraBase.*archive_$DB$.log."),
    ],
)

aggregation_rules["oracle_tbs"] = (
    "Tablespaces",
    ["HOST", "DB"],
    "worst",
    [
        ("$HOST$", "Tablespace $DB$_"),
    ],
)

# Filesystems and IO relevant for DB
aggregation_rules["db_filesystems"] = (
    "Filesystems",
    ["HOST", "DB"],
    "worst",
    [
        ("$HOST$", "fs_/OraBase"),
        ("$HOST$", "Mount|Disk"),
    ],
)
# State of host that is relevant for a certain ORACLE DB
aggregation_rules["db_host_state"] = (
    "$HOST$",
    ["HOST"],
    "worst",
    [
        ("$HOST$", HOST_STATE),
        ("performance", ["$HOST$"]),
        ("db_filesystems", ["$HOST$", "$DB$"]),
        ("nic", ["$HOST$", "userlan"]),
        ("nic", ["$HOST$", "cluster"]),
    ],
)

aggregation_rules["cluster_db_hosts"] = (
    "Hoststates",
    ["HOSTA", "HOSTB"],
    "worst",
    [
        ("db_host_state", ["$HOSTA$:$HOSTB$"]),
        ("db_host_state", ["$HOSTA$"]),
        ("db_host_state", ["$HOSTB$"]),
    ],
)

aggregation_rules["noncluster_db"] = (
    "$DB$",
    ["HOST", "DB"],
    "worst",
    [
        ("$HOST$", "DB_$DB$"),
        ("oracle_log", ["$HOST$", "$DB$"]),
        ("oracle_tbs", ["$HOST$", "$DB$"]),
        ("db_host_state", ["$HOST$"]),
    ],
)
aggregation_rules["cluster_db"] = (
    "$DB$",
    ["HOSTA", "HOSTB", "DB"],
    "worst",
    [
        ("$HOSTA$:$HOSTB$", "DB_$DB$"),
        ("oracle_log", ["$HOSTA$:$HOSTB$", "$DB$"]),
        ("oracle_tbs", ["$HOSTA$:$HOSTB$", "$DB$"]),
        ("cluster_db_hosts", ["$HOSTA$", "$HOSTB$"]),
    ],
)

aggregations += [
    ("ORACLE", FOREACH_SERVICE, "([^:]*)", "DB_(.*)", "noncluster_db", ["$1$", "$2$"]),
    ("ORACLE", FOREACH_SERVICE, "(.*):(.*)", "DB_(.*)", "cluster_db", ["$1$", "$2$", "$3$"]),
]
