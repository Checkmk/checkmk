#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.mysql.agent_based.mysql_replica_slave import (
    check_mysql_replica_slave,
    discover_mysql_replica_slave,
    parse_mysql_replica_slave,
)

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

SERVER_LINUX_MYSQL_REPLICA_1 = [
    # from generictests
    ["***************************", "1.", "row", "***************************"],
    ["Replica_IO_State:", "Waiting", "for", "source", "to", "send", "event"],
    ["Source_Host:", "10.1.27.6"],
    ["Source_User:", "repl"],
    ["Source_Port:", "3306"],
    ["Connect_Retry:", "60"],
    ["Source_Log_File:", "repl-log-bin.002158"],
    ["Read_Source_Log_Pos:", "142181744"],
    ["Relay_Log_File:", "repl-relay-bin.003953"],
    ["Relay_Log_Pos:", "8161786"],
    ["Relay_Source_Log_File:", "repl-log-bin.002158"],
    ["Replica_IO_Running:", "Yes"],
    ["Replica_SQL_Running:", "Yes"],
    ["Replicate_Do_DB:"],
    ["Replicate_Ignore_DB:"],
    ["Replicate_Do_Table:"],
    ["Replicate_Ignore_Table:"],
    ["Replicate_Wild_Do_Table:"],
    ["Replicate_Wild_Ignore_Table:"],
    ["Last_Errno:", "0"],
    ["Last_Error:"],
    ["Skip_Counter:", "0"],
    ["Exec_Source_Log_Pos:", "142181744"],
    ["Relay_Log_Space:", "93709799"],
    ["Until_Condition:", "None"],
    ["Until_Log_File:"],
    ["Until_Log_Pos:", "0"],
    ["Source_SSL_Allowed:", "No"],
    ["Source_SSL_CA_File:"],
    ["Source_SSL_CA_Path:"],
    ["Source_SSL_Cert:"],
    ["Source_SSL_Cipher:"],
    ["Source_SSL_Key:"],
    ["Seconds_Behind_Source:", "0"],
    ["Source_SSL_Verify_Server_Cert:", "No"],
    ["Last_IO_Errno:", "0"],
    ["Last_IO_Error:"],
    ["Last_SQL_Errno:", "0"],
    ["Last_SQL_Error:"],
    ["Replicate_Ignore_Server_Ids:"],
    ["Source_Server_Id:", "12"],
]


def test_mysql_slave_simple() -> None:
    section = parse_mysql_replica_slave(SERVER_LINUX_MYSQL_SLAVE_1)

    assert list(discover_mysql_replica_slave(section)) == [
        Service(item="mysql"),
    ]
    assert list(
        check_mysql_replica_slave(
            item="mysql",
            section=section,
            params={"seconds_behind_master": None},
        )
    ) == [
        Result(state=State.OK, summary="Slave-IO: running"),
        Result(state=State.OK, summary="Relay log: 89.4 MiB"),
        Metric("relay_log_space", 93709799.0),
        Result(state=State.OK, summary="Slave-SQL: running"),
        Result(state=State.OK, summary="Time behind master: 0 seconds"),
        Metric("sync_latency", 0.0),
    ]


def test_mysql_slave_error() -> None:
    section = parse_mysql_replica_slave(MYSQL_ERROR)

    assert list(discover_mysql_replica_slave(section)) == [
        Service(item="mysql"),
    ]
    assert list(
        check_mysql_replica_slave(
            item="mysql",
            section=section,
            params={"seconds_behind_master": None},
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="ERROR 1227 (42000) at line 1: Access denied; you need (at least one of) the SUPER, SLAVE MONITOR privilege(s) for this operation",
        ),
    ]


def test_mysql_replica_simple() -> None:
    section = parse_mysql_replica_slave(SERVER_LINUX_MYSQL_REPLICA_1)

    assert list(discover_mysql_replica_slave(section)) == [
        Service(item="mysql"),
    ]
    assert list(
        check_mysql_replica_slave(
            item="mysql",
            section=section,
            params={"seconds_behind_master": None},
        )
    ) == [
        Result(state=State.OK, summary="Replica-IO: running"),
        Result(state=State.OK, summary="Relay log: 89.4 MiB"),
        Metric("relay_log_space", 93709799.0),
        Result(state=State.OK, summary="Replica-SQL: running"),
        Result(state=State.OK, summary="Time behind source: 0 seconds"),
        Metric("sync_latency", 0.0),
    ]
