#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest import MonkeyPatch

from cmk.agent_based.v2 import Attributes, Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based import lparstat_aix as la


def _parse(string_table: StringTable) -> la.Section:
    assert (section := la.parse_lparstat_aix(string_table)) is not None
    return section


def _get_section() -> la.Section:
    return _parse(
        [
            [
                "System",
                "configuration:",
                "type=Dedicated",
                "mode=Capped",
                "smt=4",
                "lcpu=4",
                "mem=16384MB",
            ],
            ["%user", "%sys", "%wait", "%idle"],
            ["-----", "-----", "------", "------"],
            ["0.1", "58.8", "0.0", "41.1"],
        ]
    )


def test_inventory_lparstat_aix() -> None:
    assert list(la.inventory_lparstat_aix(_get_section())) == [
        Attributes(
            path=["hardware", "cpu"],
            inventory_attributes={
                "sharing_mode": "Dedicated-Capped",
                "smt_threads": "4",
                "logical_cpus": "4",
            },
        ),
    ]


STRING_TABLE_REGRESSION_1 = [
    ["System", "Config", "type=Dedicated", "ent=7.0", "what=ever"],
    [
        "%user",
        "%sys",
        "%wait",
        "%idle",
        "physc",
        "%entc",
        "lbusy",
        "vcsw",
        "phint",
        "%nsp",
        "%utcyc",
    ],
    [
        "#",
        "-----",
        "-----",
        "------",
        "------",
        "-----",
        "-----",
        "------",
        "-----",
        "-----",
        "-----",
        "------",
    ],
    ["0.2", "0.4", "0.0", "99.3", "0.02", "1.7", "0.0", "215", "3", "101", "0.64"],
]


def test_discover_lparstat_aix_regression_1() -> None:
    assert list(la.discover_lparstat(_parse(STRING_TABLE_REGRESSION_1))) == [
        Service(),
    ]


def test_discover_lparstat_aix_cpu_regression_1() -> None:
    assert list(la.discover_lparstat_aix_cpu(_parse(STRING_TABLE_REGRESSION_1))) == [
        Service(),
    ]


def test_check_lparstat_aix_regression_1() -> None:
    assert list(la.check_lparstat(_parse(STRING_TABLE_REGRESSION_1))) == [
        Result(state=State.OK, summary="Physc: 0.02"),
        Metric("physc", 0.02),
        Result(state=State.OK, summary="Entc: 1.7%"),
        Metric("entc", 1.7),
        Result(state=State.OK, summary="Lbusy: 0.0"),
        Metric("lbusy", 0.0),
        Result(state=State.OK, summary="Vcsw: 215.0"),
        Metric("vcsw", 215.0),
        Result(state=State.OK, summary="Phint: 3.0"),
        Metric("phint", 3.0),
        Result(state=State.OK, summary="Nsp: 101.0%"),
        Metric("nsp", 101.0),
        Result(state=State.OK, summary="Utcyc: 0.64%"),
        Metric("utcyc", 0.64),
    ]


def test_check_lparstat_aix_cpu_util_regression_1(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(la, "get_value_store", lambda: {})
    assert list(la.check_lparstat_aix_cpu({}, _parse(STRING_TABLE_REGRESSION_1))) == [
        Result(state=State.OK, notice="User: 0.20%"),
        Metric("user", 0.2),
        Result(state=State.OK, notice="System: 0.40%"),
        Metric("system", 0.4),
        Result(state=State.OK, notice="Wait: 0%"),
        Metric("wait", 0.0),
        Result(state=State.OK, summary="Total CPU: 0.60%"),
        Metric("util", 0.6000000000000001, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Physical CPU consumption: 0.02 CPUs"),
        Metric("cpu_entitlement_util", 0.02),
        Result(state=State.OK, summary="Entitlement: 7.0 CPUs"),
        Metric("cpu_entitlement", 7.0),
    ]


STRING_TABLE_REGRESSION_2 = [
    [
        "System",
        "configuration:",
        "type=Shared",
        "mode=Uncapped",
        "smt=4",
        "lcpu=8",
        "mem=16384MB",
        "psize=4",
        "ent=1.00",
    ],
    [
        "%user",
        "%sys",
        "%wait",
        "%idle",
        "physc",
        "%entc",
        "lbusy",
        "vcsw",
        "phint",
        "%nsp",
        "%utcyc",
    ],
    [
        "-----",
        "-----",
        "------",
        "------",
        "-----",
        "-----",
        "------",
        "-----",
        "-----",
        "-----",
        "------",
    ],
    ["0.2", "0.4", "0.0", "99.3", "0.02", "1.7", "0.0", "215", "3", "101", "0.64"],
]


def test_discover_lparstat_aix_regression_2() -> None:
    assert list(la.discover_lparstat(_parse(STRING_TABLE_REGRESSION_2))) == [
        Service(),
    ]


def test_discover_lparstat_aix_cpu_regression_2() -> None:
    assert list(la.discover_lparstat_aix_cpu(_parse(STRING_TABLE_REGRESSION_2))) == [Service()]


def test_check_lparstat_aix_regression_2() -> None:
    assert list(la.check_lparstat(_parse(STRING_TABLE_REGRESSION_2))) == [
        Result(state=State.OK, summary="Physc: 0.02"),
        Metric("physc", 0.02),
        Result(state=State.OK, summary="Entc: 1.7%"),
        Metric("entc", 1.7),
        Result(state=State.OK, summary="Lbusy: 0.0"),
        Metric("lbusy", 0.0),
        Result(state=State.OK, summary="Vcsw: 215.0"),
        Metric("vcsw", 215.0),
        Result(state=State.OK, summary="Phint: 3.0"),
        Metric("phint", 3.0),
        Result(state=State.OK, summary="Nsp: 101.0%"),
        Metric("nsp", 101.0),
        Result(state=State.OK, summary="Utcyc: 0.64%"),
        Metric("utcyc", 0.64),
    ]


def test_check_lparstat_aix_cpu_util_regression_2(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(la, "get_value_store", lambda: {})
    assert list(la.check_lparstat_aix_cpu({}, _parse(STRING_TABLE_REGRESSION_2))) == [
        Result(state=State.OK, notice="User: 0.20%"),
        Metric("user", 0.2),
        Result(state=State.OK, notice="System: 0.40%"),
        Metric("system", 0.4),
        Result(state=State.OK, notice="Wait: 0%"),
        Metric("wait", 0.0),
        Result(state=State.OK, summary="Total CPU: 0.60%"),
        Metric("util", 0.6000000000000001, boundaries=(0.0, None)),
        Result(state=State.OK, summary="Physical CPU consumption: 0.02 CPUs"),
        Metric("cpu_entitlement_util", 0.02),
        Result(state=State.OK, summary="Entitlement: 1.0 CPUs"),
        Metric("cpu_entitlement", 1.0),
    ]


STRING_TABLE_MISSING_INFO = [
    [
        "System",
        "configuration:",
        "type=Shared",
        "mode=Uncapped",
        "smt=4",
        "lcpu=8",
        "mem=16384MB",
        "psize=4",
        "ent=1.00",
    ],
    ["%user", "%wait", "%idle", "physc", "%entc", "lbusy", "vcsw", "phint", "%nsp", "%utcyc"],
    [
        "-----",
        "------",
        "------",
        "-----",
        "-----",
        "------",
        "-----",
        "-----",
        "-----",
        "------",
    ],
    ["0.4", "0.0", "99.3", "0.02", "1.7", "0.0", "215", "3", "101", "0.64"],
]


def test_discover_lparstat_aix_missing_info() -> None:
    assert list(la.discover_lparstat(_parse(STRING_TABLE_MISSING_INFO))) == [
        Service(),
    ]


def test_discover_lparstat_aix_cpu_missing_info() -> None:
    assert not list(la.discover_lparstat_aix_cpu(_parse(STRING_TABLE_MISSING_INFO)))


STRING_TABLE_REGRESSION_4 = [
    [
        "System",
        "configuration:",
        "type=Dedicated",
        "mode=Capped",
        "smt=4",
        "lcpu=4",
        "mem=16384MB",
    ],
    ["%user", "%sys", "%wait", "%idle"],
    ["-----", "-----", "------", "------"],
    ["0.1", "58.8", "0.0", "41.1"],
]


def test_discover_lparstat_aix_regression_4() -> None:
    assert not list(la.discover_lparstat(_parse(STRING_TABLE_REGRESSION_4)))


def test_discover_lparstat_aix_cpu_regression_4() -> None:
    assert list(la.discover_lparstat_aix_cpu(_parse(STRING_TABLE_REGRESSION_4))) == [Service()]


STRING_TABLE_REGRESSION_5 = [
    [
        "System",
        "configuration:",
        "type=Shared",
        "mode=Uncapped",
        "smt=4",
        "lcpu=8",
        "mem=16384MB",
        "psize=4",
        "ent=1.00",
    ],
    [
        "%user",
        "%sys",
        "%wait",
        "%idle",
        "physc",
        "%entc",
        "lbusy",
        "app",
        "vcsw",
        "phint",
        "%nsp",
    ],
    ["this line is ignored"],
    ["0.2", "1.2", "0.2", "98.6", "0.02", "9.3", "0.1", "519", "0", "101", "0.00"],
]


def test_check_lparstat_aix_regression_5(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(la, "get_value_store", lambda: {})
    assert list(
        la.check_lparstat_aix_cpu({"util": (0.5, 1.3)}, _parse(STRING_TABLE_REGRESSION_5))
    ) == [
        Result(state=State.OK, notice="User: 0.20%"),
        Metric("user", 0.2),
        Result(state=State.OK, notice="System: 1.20%"),
        Metric("system", 1.2),
        Result(state=State.OK, notice="Wait: 0.20%"),
        Metric("wait", 0.2),
        Result(state=State.CRIT, summary="Total CPU: 1.60% (warn/crit at 0.50%/1.30%)"),
        Metric("util", 1.5999999999999999, levels=(0.5, 1.3), boundaries=(0.0, None)),
        Result(state=State.OK, summary="Physical CPU consumption: 0.02 CPUs"),
        Metric("cpu_entitlement_util", 0.02),
        Result(state=State.OK, summary="Entitlement: 1.0 CPUs"),
        Metric("cpu_entitlement", 1.0),
    ]
