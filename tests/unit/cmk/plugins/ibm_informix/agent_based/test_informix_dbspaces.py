#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.ibm_informix.agent_based.informix_dbspaces import (
    check_informix_dbspaces,
    discovery_informix_dbspaces,
    parse_informix_dbspaces,
)

SAMPLE_STRINGTABLE = [
    ["[[[ol_informix15/0]]]"],
    ["(expression)", "foo", "DBSPACE"],
    ["dbsnum", "13"],
    ["is_temp", "0"],
    ["flags", "131089"],
    ["(constant)", "CHUNK"],
    ["fname", "/opt/informix/foo"],
    ["system_pagesize", "2048"],
    ["pagesize", "6144"],
    ["chksize", "1536000"],
    ["nfree", "511323"],
    ["chunk_flags", "580"],
    ["(expression)"],
    ["mflags"],
]


def test_discovery() -> None:
    discovered = list(discovery_informix_dbspaces(parse_informix_dbspaces(SAMPLE_STRINGTABLE)))
    assert discovered == [Service(item="ol_informix15/0 foo")]


def test_parse() -> None:
    parsed = parse_informix_dbspaces(SAMPLE_STRINGTABLE)
    assert parsed == {
        "ol_informix15/0 foo": [
            {
                "dbsnum": "13",
                "is_temp": "0",
                "flags": "131089",
                "(constant)": "CHUNK",
                "fname": "/opt/informix/foo",
                "system_pagesize": "2048",
                "pagesize": "6144",
                "chksize": "1536000",
                "nfree": "511323",
                "chunk_flags": "580",
                "(expression)": "",
                "mflags": "",
            }
        ]
    }


@pytest.mark.parametrize(
    ["item", "params", "expected"],
    [
        pytest.param(
            "no-such-service",
            {},
            [],
            id="unknown item",
        ),
        pytest.param(
            "ol_informix15/0 foo",
            {},
            [
                Result(state=State.OK, summary="Data files: 1"),
                Result(state=State.OK, summary="Size: 3.15 GB"),
                Metric("tablespace_size", 3145728000.0),
                Result(state=State.OK, summary="Used: 4.16 MB"),
                Metric("tablespace_used", 4159488.0),
            ],
            id="no params",
        ),
        pytest.param(
            "ol_informix15/0 foo",
            {"levels": (1, 4 * 1000**3)},
            [
                Result(state=State.OK, summary="Data files: 1"),
                Result(
                    state=State.WARN, summary="Size: 3.15 GB (warn/crit at Size: 1 B/Size: 4.00 GB)"
                ),
                Metric("tablespace_size", 3145728000.0, levels=(1, 4 * 1000**3)),
                Result(state=State.OK, summary="Used: 4.16 MB"),
                Metric("tablespace_used", 4159488.0),
            ],
            id="levels param",
        ),
        pytest.param(
            "ol_informix15/0 foo",
            {"levels_perc": (0, 0)},
            [
                Result(state=State.OK, summary="Data files: 1"),
                Result(state=State.OK, summary="Size: 3.15 GB"),
                Metric("tablespace_size", 3145728000.0),
                Result(
                    state=State.CRIT, summary="Used: 4.16 MB (warn/crit at Used: 0 B/Used: 0 B)"
                ),
                Metric("tablespace_used", 4159488.0, levels=(0, 0)),
            ],
            id="levels_perc param",
        ),
    ],
)
def test_check(item: str, params: Mapping[str, object], expected: list[Result | Metric]) -> None:
    results = list(
        check_informix_dbspaces(
            item=item,
            params=params,  # type: ignore[arg-type]
            section=parse_informix_dbspaces(SAMPLE_STRINGTABLE),
        )
    )
    assert results == expected
