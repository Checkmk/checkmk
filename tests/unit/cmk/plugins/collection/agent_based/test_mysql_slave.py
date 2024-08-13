#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.conftest import FixRegister

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName

from cmk.agent_based.v2 import Metric, Result, Service, State

SERVER_LINUX_MYSQL_SLAVE_1 = [
    # from generictests
    ["***************************", "1.", "row", "***************************"],
    ["Slave_IO_State:", "Waiting", "for", "master", "to", "send", "event"],
    ["Master_Host:", "10.1.27.6"],
    ["Master_User:", "repl"],
    ["Master_Port:", "3306"],
    ["Connect_Retry:", "60"],
    ["Master_Log_File:", "repl-log-bin.002158"],
    ["Read_Master_Log_Pos:", "142181744"],
    ["Relay_Log_File:", "repl-relay-bin.003953"],
    ["Relay_Log_Pos:", "8161786"],
    ["Relay_Master_Log_File:", "repl-log-bin.002158"],
    ["Slave_IO_Running:", "Yes"],
    ["Slave_SQL_Running:", "Yes"],
    ["Replicate_Do_DB:"],
    ["Replicate_Ignore_DB:"],
    ["Replicate_Do_Table:"],
    ["Replicate_Ignore_Table:"],
    ["Replicate_Wild_Do_Table:"],
    ["Replicate_Wild_Ignore_Table:"],
    ["Last_Errno:", "0"],
    ["Last_Error:"],
    ["Skip_Counter:", "0"],
    ["Exec_Master_Log_Pos:", "142181744"],
    ["Relay_Log_Space:", "93709799"],
    ["Until_Condition:", "None"],
    ["Until_Log_File:"],
    ["Until_Log_Pos:", "0"],
    ["Master_SSL_Allowed:", "No"],
    ["Master_SSL_CA_File:"],
    ["Master_SSL_CA_Path:"],
    ["Master_SSL_Cert:"],
    ["Master_SSL_Cipher:"],
    ["Master_SSL_Key:"],
    ["Seconds_Behind_Master:", "0"],
    ["Master_SSL_Verify_Server_Cert:", "No"],
    ["Last_IO_Errno:", "0"],
    ["Last_IO_Error:"],
    ["Last_SQL_Errno:", "0"],
    ["Last_SQL_Error:"],
    ["Replicate_Ignore_Server_Ids:"],
    ["Master_Server_Id:", "12"],
]

MYSQL_ERROR = [
    # from SUP-19868
    ["[[]]"],
    [
        "ERROR",
        "1227",
        "(42000)",
        "at",
        "line",
        "1:",
        "Access",
        "denied;",
        "you",
        "need",
        "(at",
        "least",
        "one",
        "of)",
        "the",
        "SUPER,",
        "SLAVE",
        "MONITOR",
        "privilege(s)",
        "for",
        "this",
        "operation",
    ],
]


def test_mysql_slave_simple(
    fix_register: FixRegister,
) -> None:
    section = fix_register.agent_sections[SectionName("mysql_slave")].parse_function(
        SERVER_LINUX_MYSQL_SLAVE_1
    )
    plugin = fix_register.check_plugins[CheckPluginName("mysql_slave")]

    assert list(plugin.discovery_function(section)) == [
        Service(item="mysql"),
    ]
    assert list(plugin.check_function(item="mysql", section=section, params={})) == [
        Result(state=State.OK, summary="Slave-IO: running"),
        Result(state=State.OK, summary="Relay log: 89.4 MiB"),
        Metric("relay_log_space", 93709799.0),
        Result(state=State.OK, summary="Slave-SQL: running"),
        Result(state=State.OK, summary="Time behind master: 0 seconds"),
        Metric("sync_latency", 0.0),
    ]


def test_mysql_slave_error(
    fix_register: FixRegister,
) -> None:
    section = fix_register.agent_sections[SectionName("mysql_slave")].parse_function(MYSQL_ERROR)
    plugin = fix_register.check_plugins[CheckPluginName("mysql_slave")]

    assert not (
        list(plugin.discovery_function(section))
    )  # TODO: this is a bug, it should be discovered
    assert not (
        list(plugin.check_function(item="mysql", section=section, params={}))
    )  # TODO: this is a bug, an error should be shown
