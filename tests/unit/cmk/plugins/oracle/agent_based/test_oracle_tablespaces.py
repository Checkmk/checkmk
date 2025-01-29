#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Mapping

import pytest

from tests.unit.cmk.plugins.oracle.agent_based.utils_inventory import sort_inventory_result

from cmk.agent_based.v2 import (
    CheckResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    TableRow,
)
from cmk.plugins.lib.oracle import OraErrors, SectionTableSpaces
from cmk.plugins.oracle.agent_based import oracle_tablespaces
from cmk.plugins.oracle.agent_based.oracle_tablespaces import inventory_oracle_tablespaces

STRING_TABLE = [
    ["line", "too", "short"],
    ["line", "too", "l", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o", "ong!"],
    ["ORA-bar", "some", "data"],
    [
        "PRD",
        "",
        "PSAPTEMP",
        "ONLINE",
        "NO",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "TEMP",
        "8192",
        "ONLINE",
        "944000",
        "TEMPORARY",
    ],
    [
        "PRD",
        "/oracle/PRD/sapdata/sapdata2/temp_2/temp.data2",
        "PSAPTEMP",
        "ONLINE",
        "YES",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "TEMP",
        "8192",
        "ONLINE",
        "946688",
        "TEMPORARY",
    ],
    [
        "PRD",
        "/oracle/PRD/sapdata/sapdata3/temp_3/temp.data3",
        "PSAPTEMP",
        "ONLINE",
        "YES",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "TEMP",
        "8192",
        "ONLINE",
        "944640",
        "TEMPORARY",
    ],
    [
        "CLUSTER",
        "/oracle/PRD/sapdata/sapdata3/temp_3/temp.data3",
        "FOO",
        "ONLINE",
        "YES",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "TEMP",
        "8192",
        "ONLINE",
        "944640",
        "TEMPORARY",
    ],
    [
        "CLUSTER",
        "/oracle/PRD/sapdata/sapdata3/temp_4/temp.data5",
        "FOO",
        "ONLINE",
        "YES",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "TEMP",
        "8192",
        "ONLINE",
        "944640",
        "TEMPORARY",
    ],
    [
        "PIMSWA",
        "+DATA/PIMSWA/TEMPFILE/temp.307.1025296289",
        "TEMP",
        "ONLINE",
        "YES",
        "90496",
        "4194302",
        "90368",
        "80",
        "ONLINE",
        "8192",
        "ONLINE",
        "68992",
        "TEMPORARY",
        "12.2.0.1.0",
    ],
    [
        "PIMSWA2",
        "+DATA/PIMSWA/TEMPFILE/temp.307.1025296289",
        "FOO",
        "ONLINE",
        "NO",
        "90496",
        "4194302",
        "90368",
        "80",
        "ONLINE",
        "8192",
        "ONLINE",
        "68992",
        "TEMPORARY",
        "12.2.0.1.0",
    ],
    [
        "PRD",
        "/oracle/PRD/sapdata/sapdata4/temp_4/temp.data4",
        "PSAPTEMP",
        "ONLINE",
        "YES",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "TEMP",
        "8192",
        "ONLINE",
        "944000",
        "TEMPORARY",
    ],
    [
        "PPD",
        "/oracle/PPD/sapdata/sapdata4/temp_5/temp.data5",
        "FOO",
        "ONLINE",
        "YES",
        "2304000",
        "2560000",
        "2303872",
        "25600",
        "OFFLINE",
        "8192",
        "ONLINE",
        "944000",
        "TEMPORARY",
    ],
]

Section: SectionTableSpaces = {
    "error_sids": {"ORA-bar": OraErrors(["ORA-bar", "some", "data"])},
    "tablespaces": {
        ("CLUSTER", "FOO"): {
            "amount_missing_filenames": 0,
            "autoextensible": True,
            "datafiles": [
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7738490880,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata3/temp_3/temp.data3",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7738490880,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata3/temp_4/temp.data5",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
            ],
            "db_version": 0,
            "status": "ONLINE",
            "type": "TEMPORARY",
        },
        ("PRD", "PSAPTEMP"): {
            "amount_missing_filenames": 1,
            "autoextensible": True,
            "datafiles": [
                {
                    "autoextensible": False,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7733248000,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7755268096,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata2/temp_2/temp.data2",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7738490880,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata3/temp_3/temp.data3",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7733248000,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata4/temp_4/temp.data4",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
            ],
            "db_version": 0,
            "status": "ONLINE",
            "type": "TEMPORARY",
        },
        ("PPD", "FOO"): {
            "amount_missing_filenames": 0,
            "autoextensible": True,
            "datafiles": [
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "OFFLINE",
                    "free_space": 7733248000,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PPD/sapdata/sapdata4/temp_5/temp.data5",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                }
            ],
            "db_version": 0,
            "status": "ONLINE",
            "type": "TEMPORARY",
        },
        ("PIMSWA", "TEMP"): {
            "amount_missing_filenames": 0,
            "autoextensible": True,
            "datafiles": [
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "ONLINE",
                    "free_space": 565182464,
                    "increment_size": 655360,
                    "max_size": 34359721984,
                    "name": "+DATA/PIMSWA/TEMPFILE/temp.307.1025296289",
                    "size": 741343232,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 740294656,
                }
            ],
            "db_version": 12,
            "status": "ONLINE",
            "type": "TEMPORARY",
        },
        ("PIMSWA2", "FOO"): {
            "amount_missing_filenames": 0,
            "autoextensible": False,
            "datafiles": [
                {
                    "autoextensible": False,
                    "block_size": 8192,
                    "file_online_status": "ONLINE",
                    "free_space": 565182464,
                    "increment_size": 655360,
                    "max_size": 34359721984,
                    "name": "+DATA/PIMSWA/TEMPFILE/temp.307.1025296289",
                    "size": 741343232,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 740294656,
                }
            ],
            "db_version": 12,
            "status": "ONLINE",
            "type": "TEMPORARY",
        },
    },
}


def test_parse() -> None:
    actual_section = oracle_tablespaces.parse_oracle_tablespaces(STRING_TABLE)
    actual_tablespaces = actual_section["tablespaces"]
    actual_error_sid = actual_section["error_sids"]["ORA-bar"]
    expected_error_sids = Section["error_sids"]["ORA-bar"]
    assert actual_tablespaces == Section["tablespaces"]
    assert actual_error_sid.error_text == expected_error_sids.error_text
    assert actual_error_sid.error_severity == expected_error_sids.error_severity


def test_discovery() -> None:
    assert [
        Service(item="CLUSTER.FOO", parameters={"autoextend": True}, labels=[]),
        Service(item="PRD.PSAPTEMP", parameters={"autoextend": True}, labels=[]),
        Service(item="PPD.FOO", parameters={"autoextend": True}, labels=[]),
        Service(item="PIMSWA.TEMP", parameters={"autoextend": True}, labels=[]),
        Service(item="PIMSWA2.FOO", parameters={"autoextend": False}, labels=[]),
    ] == list(oracle_tablespaces.discovery_oracle_tablespaces(Section))


@pytest.mark.parametrize(
    "item, params, expected",
    [
        (
            "invalid-oracle-item",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Invalid check item (must be <SID>.<tablespace>)",
                    details="Invalid check item (must be <SID>.<tablespace>)",
                )
            ],
        ),
        (
            "PRD.PSAPTEMP",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            [
                Result(
                    state=State.CRIT,
                    summary="1 files with missing filename in TEMPORARY Tablespace, space calculation not possible",
                    details="1 files with missing filename in TEMPORARY Tablespace, space calculation not possible",
                )
            ],
        ),
        (
            "PIMSWA.TEMP",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            [
                Result(
                    state=State.OK,
                    summary="ONLINE (TEMPORARY), Size: 707 MiB, 0.51% used (168 MiB of max. 32.0 GiB), Free: 31.8 GiB",
                    details="ONLINE (TEMPORARY), Size: 707 MiB, 0.51% used (168 MiB of max. 32.0 GiB), Free: 31.8 GiB",
                ),
                Metric(
                    "size",
                    741343232.0,
                    levels=(30923749785.6, 32641735884.8),
                    boundaries=(0.0, 34359721984.0),
                ),
                Metric("used", 176160768.0),
                Metric("max_size", 34359721984.0),
                Result(state=State.OK, summary="autoextend"),
            ],
        ),
        (
            "PIMSWA.TEMP",
            {
                "temptablespace": True,
                "levels": (99.7, 80.0),
            },
            [
                Result(
                    state=State.OK,
                    summary="ONLINE (TEMPORARY), Size: 707 MiB, 0.51% used (168 MiB of max. 32.0 GiB), Free: 31.8 GiB",
                    details="ONLINE (TEMPORARY), Size: 707 MiB, 0.51% used (168 MiB of max. 32.0 GiB), Free: 31.8 GiB",
                ),
                Metric(
                    "size",
                    741343232.0,
                    levels=(103079165.95199585, 6871944396.799999),
                    boundaries=(0.0, 34359721984.0),
                ),
                Metric("used", 176160768.0),
                Metric("max_size", 34359721984.0),
                Result(state=State.OK, summary="autoextend"),
                Result(
                    state=State.WARN,
                    summary="Space left: 31.8 GiB (warn/crit below 31.9 GiB/25.6 GiB)",
                    details="Space left: 31.8 GiB (warn/crit below 31.9 GiB/25.6 GiB)",
                ),
            ],
        ),
        (
            "PIMSWA2.FOO",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            [
                Result(
                    state=State.OK,
                    summary="ONLINE (TEMPORARY), Size: 707 MiB, 23.76% used (168 MiB of max. 707 MiB), Free: 539 MiB",
                    details="ONLINE (TEMPORARY), Size: 707 MiB, 23.76% used (168 MiB of max. 707 MiB), Free: 539 MiB",
                ),
                Metric(
                    "size",
                    741343232.0,
                    levels=(667208908.8, 704276070.4),
                    boundaries=(0.0, 741343232.0),
                ),
                Metric("used", 176160768.0),
                Metric("max_size", 741343232.0),
                Result(state=State.OK, summary="no autoextend"),
                Result(
                    state=State.OK,
                    summary="1 data files (1 avail, 0 autoext)",
                    details="1 data files (1 avail, 0 autoext)",
                ),
            ],
        ),
        (
            "PPD.FOO",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            [
                Result(
                    state=State.OK,
                    summary="ONLINE (TEMPORARY), Size: 17.6 GiB, 53.12% used (10.4 GiB of max. 19.5 GiB), Free: 9.16 GiB",
                ),
                Result(state=State.OK, summary="10 increments (1.95 GiB)"),
                Metric(
                    "size",
                    18874368000.0,
                    levels=(18874368000.0, 19922944000.0),
                    boundaries=(0.0, 20971520000.0),
                ),
                Metric("used", 11141120000.0),
                Metric("max_size", 20971520000.0),
                Result(state=State.OK, summary="autoextend"),
                Result(
                    state=State.CRIT,
                    summary="Datafiles OFFLINE: PPD",
                    details="OFFLINE datafiles for PPD:\n/oracle/PPD/sapdata/sapdata4/temp_5/temp.data5",
                ),
            ],
        ),
        (
            "PPD.FOO",
            {"levels": (10.0, 5.0), "map_file_online_states": [("OFFLINE", 2)]},
            [
                Result(
                    state=State.OK,
                    summary="ONLINE (TEMPORARY), Size: 17.6 GiB, 53.12% used (10.4 GiB of max. 19.5 GiB), Free: 9.16 GiB",
                    details="ONLINE (TEMPORARY), Size: 17.6 GiB, 53.12% used (10.4 GiB of max. 19.5 GiB), Free: 9.16 GiB",
                ),
                Result(state=State.OK, summary="10 increments (1.95 GiB)"),
                Metric(
                    "size",
                    18874368000.0,
                    levels=(18874368000.0, 19922944000.0),
                    boundaries=(0.0, 20971520000.0),
                ),
                Metric("used", 11141120000.0),
                Metric("max_size", 20971520000.0),
                Result(state=State.OK, summary="autoextend"),
                Result(
                    state=State.CRIT,
                    summary="Datafiles OFFLINE: PPD",
                    details="OFFLINE datafiles for PPD:\n/oracle/PPD/sapdata/sapdata4/temp_5/temp.data5",
                ),
            ],
        ),
        (
            "CLUSTER.FOO",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            [
                Result(
                    state=State.OK,
                    summary="ONLINE (TEMPORARY), Size: 35.2 GiB, 53.10% used (20.7 GiB of max. 39.1 GiB), Free: 20.3 GiB",
                    details="ONLINE (TEMPORARY), Size: 35.2 GiB, 53.10% used (20.7 GiB of max. 39.1 GiB), Free: 20.3 GiB",
                ),
                Result(state=State.OK, summary="20 increments (3.91 GiB)"),
                Metric(
                    "size",
                    37748736000.0,
                    levels=(37748736000.0, 39845888000.0),
                    boundaries=(0.0, 41943040000.0),
                ),
                Metric("used", 22271754240.0),
                Metric("max_size", 41943040000.0),
                Result(state=State.OK, summary="autoextend"),
                Result(
                    state=State.OK,
                    summary="2 data files (2 avail, 2 autoext)",
                    details="2 data files (2 avail, 2 autoext)",
                ),
            ],
        ),
    ],
)
def test_check(item: str, params: Mapping[str, object], expected: CheckResult) -> None:
    assert expected == list(
        oracle_tablespaces.check_oracle_tablespaces(
            item,
            (params),
            Section,
        )
    )


def test_check_raises() -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            oracle_tablespaces.check_oracle_tablespaces(
                "item.not.sent",
                {},
                Section,
            )
        )


def test_check_cluster() -> None:
    section2 = copy.deepcopy(Section)
    # Throw away one datafile in order for the cluster check to choose the node
    # with the longer datafile list
    section2["tablespaces"][("CLUSTER", "FOO")]["datafiles"].pop()

    node_section = {"node1": section2, "node2": Section}

    assert [
        Result(
            state=State.OK,
            summary="ONLINE (TEMPORARY), Size: 35.2 GiB, 53.10% used (20.7 GiB of max. 39.1 GiB), Free: 20.3 GiB",
            details="ONLINE (TEMPORARY), Size: 35.2 GiB, 53.10% used (20.7 GiB of max. 39.1 GiB), Free: 20.3 GiB",
        ),
        Result(
            state=State.OK, summary="20 increments (3.91 GiB)", details="20 increments (3.91 GiB)"
        ),
        Metric(
            "size",
            37748736000.0,
            levels=(37748736000.0, 39845888000.0),
            boundaries=(0.0, 41943040000.0),
        ),
        Metric("used", 22271754240.0),
        Metric("max_size", 41943040000.0),
        Result(state=State.OK, summary="autoextend"),
        Result(
            state=State.OK,
            summary="2 data files (2 avail, 2 autoext)",
            details="2 data files (2 avail, 2 autoext)",
        ),
    ] == list(
        oracle_tablespaces.cluster_check_oracle_tablespaces(
            "CLUSTER.FOO",
            oracle_tablespaces.ORACLE_TABLESPACES_DEFAULTS,
            node_section,
        )
    )


InvSection: SectionTableSpaces = {
    "error_sids": {"ORA-bar": OraErrors(["ORA-bar", "some", "data"])},
    "tablespaces": {
        ("CLUSTER", "FOO"): {
            "amount_missing_filenames": 0,
            "autoextensible": True,
            "datafiles": [
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7738490880,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata3/temp_3/temp.data3",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
                {
                    "autoextensible": True,
                    "block_size": 8192,
                    "file_online_status": "TEMP",
                    "free_space": 7738490880,
                    "increment_size": 209715200,
                    "max_size": 20971520000,
                    "name": "/oracle/PRD/sapdata/sapdata3/temp_4/temp.data5",
                    "size": 18874368000,
                    "status": "ONLINE",
                    "ts_status": "ONLINE",
                    "ts_type": "TEMPORARY",
                    "used_size": 18873319424,
                },
            ],
            "db_version": 0,
            "status": "ONLINE",
            "type": "TEMPORARY",
        },
    },
}


def test_inventory() -> None:
    assert sort_inventory_result(inventory_oracle_tablespaces(InvSection)) == sort_inventory_result(
        [
            TableRow(
                path=["software", "applications", "oracle", "tablespaces"],
                key_columns={"sid": "CLUSTER", "name": "FOO"},
                inventory_columns={"version": "", "type": "TEMPORARY", "autoextensible": "YES"},
                status_columns={
                    "current_size": 37748736000,
                    "max_size": 41943040000,
                    "used_size": 22271754240,
                    "num_increments": 20,
                    "increment_size": 4194304000,
                    "free_space": 21768437760,
                },
            )
        ]
    )


def test_table_spaces__sup_10648() -> None:
    data = "sid|/some/path/to/a/file.dbf.c1|tablespace|AVAILABLE||||||OFFLINE|8192|OFFLINE|0|PERMANENT|12.3.4.5.6"

    string_table = [data.split("|")]
    parsed = oracle_tablespaces.parse_oracle_tablespaces(string_table)
    result = list(
        oracle_tablespaces.check_oracle_tablespaces(
            "sid.tablespace",
            {"levels": (10.0, 5.0), "map_file_online_states": [("OFFLINE", 0)]},
            parsed,
        )
    )
    assert result == [
        Result(
            state=State.OK,
            summary="Datafiles OFFLINE: sid",
            details="OFFLINE datafiles for sid:\n/some/path/to/a/file.dbf.c1",
        ),
    ]


def test_undo_table_spaces__sup_11158() -> None:
    data = (
        "GGGGGGGG-PPPPPPPP|+DATA_A_A_AAA/CCCCCCCC_DDDDDDDDDDD/22222222222222222222222222222222/DATAFILE/"
        "undo_2.222.1111111111|UNDO_2|AVAILABLE|YES|39322|1310720|39192|131072|ONLINE|8192|ONLINE|37176|"
        "UNDO|19.0.0.0.0"
    )
    string_table = [data.split("|")]
    parsed = oracle_tablespaces.parse_oracle_tablespaces(string_table)
    discovery_result = list(oracle_tablespaces.discovery_oracle_tablespaces(parsed))
    assert discovery_result == [
        Service(item="GGGGGGGG-PPPPPPPP.UNDO_2", parameters={"autoextend": True})
    ]

    check_result = list(
        oracle_tablespaces.check_oracle_tablespaces(
            "GGGGGGGG-PPPPPPPP.UNDO_2",
            # FYI: levels change meaning by datatype: float is percent, int is mb free space
            # we just want to see some warning, so we want to see 99.9999% free tablespace
            # this of course does not make sense in a real world scenario
            {
                "levels": (99.9999, 10.0),
            },
            parsed,
        )
    )
    assert [
        result for result in check_result if isinstance(result, Result) and result.state != State.OK
    ] == [], "should not have a warning element, because this feature is turned off by default"

    check_result = list(
        oracle_tablespaces.check_oracle_tablespaces(
            "GGGGGGGG-PPPPPPPP.UNDO_2",
            {
                "levels": (99.9999, 10.0),
                "monitor_undo_tablespace": True,
            },
            parsed,
        )
    )
    assert check_result == [
        Result(
            state=State.OK,
            summary="ONLINE (UNDO), Size: 307 MiB, 0.16% used (16.8 MiB of max. 10.0 GiB), Free: 9.98 GiB",
        ),
        Metric(
            "size",
            322125824.0,
            levels=(10737.418239593506, 9663676416.0),
            boundaries=(0.0, 10737418240.0),
        ),
        Metric("used", 17580032.0),
        Metric("max_size", 10737418240.0),
        Result(state=State.OK, summary="autoextend"),
        Result(
            state=State.WARN, summary="Space left: 9.98 GiB (warn/crit below 10.00 GiB/1.00 GiB)"
        ),
    ]
