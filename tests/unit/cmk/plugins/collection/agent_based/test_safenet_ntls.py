#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v1 import GetRateError
from cmk.agent_based.v2 import (
    Metric,
    Result,
    State,
)
from cmk.plugins.safenet.agent_based.safenet_ntls import (
    check_safenet_ntls,
    check_safenet_ntls_clients,
    check_safenet_ntls_connrate,
    check_safenet_ntls_expiration,
    check_safenet_ntls_links,
    parse_safenet_ntls,
    Section,
)

STRING_TABLE = [["1", "0", "0", "50599", "2", "Nov 17 11:38:50 2100 GMT"]]


def test_parse_safenet_ntls() -> None:
    assert parse_safenet_ntls(STRING_TABLE) == {
        "operation_status": "1",
        "connected_clients": 0,
        "links": 0,
        "successful_connections": 50599,
        "failed_connections": 2,
        "expiration_date": "Nov 17 11:38:50 2100 GMT",
    }


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section | None:
    return parse_safenet_ntls(STRING_TABLE)


@pytest.mark.usefixtures("initialised_item_state")
def test_check_safenet_ntls_connrate(section: Section) -> None:
    with pytest.raises(GetRateError):
        list(check_safenet_ntls_connrate("successful", section))

    assert list(check_safenet_ntls_connrate("successful", section)) == [
        Metric("connections_rate", 0.0),
        Result(state=State.OK, summary="0.00 connections/s"),
    ]

    with pytest.raises(GetRateError):
        list(check_safenet_ntls_connrate("failed", section))

    assert list(check_safenet_ntls_connrate("failed", section)) == [
        Metric("connections_rate", 0.0),
        Result(state=State.OK, summary="0.00 connections/s"),
    ]


def test_check_safenet_ntls_expiration(section: Section) -> None:
    assert list(check_safenet_ntls_expiration(section)) == [
        Result(
            state=State.OK,
            summary="The NTLS server certificate expires on Nov 17 11:38:50 2100 GMT",
        )
    ]


def test_check_safenet_ntls_links(section: Section) -> None:
    assert list(check_safenet_ntls_links({"levels": ("fixed", (0, 10))}, section)) == [
        Result(state=State.WARN, summary="Connections: 0 links (warn/crit at 0 links/10 links)"),
        Metric("connections", 0.0, levels=(0, 10)),
    ]


def test_check_safenet_ntls_clients(section: Section) -> None:
    assert list(check_safenet_ntls_clients({"levels": ("fixed", (1, 10))}, section)) == [
        Result(state=State.OK, summary="Connections: 0 connected clients"),
        Metric("connections", 0.0, levels=(1, 10)),
    ]


def test_check_safenet_ntls_op_stats(section: Section) -> None:
    assert list(check_safenet_ntls(section)) == [
        Result(state=State.OK, summary="Running"),
    ]
