#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.netapp.agent_based.netapp_ontap_agent_info import (
    check_netapp_ontap_agent_info,
    discover_netapp_ontap_agent_info,
    parse_netapp_ontap_agent_info,
    Section,
)
from cmk.plugins.netapp.models import AgentInfoModel


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [],
            [],
            id="empty section",
        ),
        pytest.param(
            [[('{"section": "disk", "info": "KeyError: \'uid\'", "is_error": true}')]],
            [AgentInfoModel(section="disk", info="KeyError: 'uid'", is_error=True)],
            id="single error",
        ),
        pytest.param(
            [
                [('{"section": "node", "info": "connection timeout", "is_error": true}')],
                [('{"section": "fan", "info": "Skipped: nodes fetch failed", "is_error": true}')],
            ],
            [
                AgentInfoModel(section="node", info="connection timeout", is_error=True),
                AgentInfoModel(section="fan", info="Skipped: nodes fetch failed", is_error=True),
            ],
            id="multiple errors",
        ),
    ],
)
def test_parse_netapp_ontap_errors(string_table: StringTable, expected: Section) -> None:
    assert parse_netapp_ontap_agent_info(string_table) == expected


def test_discover_netapp_ontap_errors() -> None:
    assert list(discover_netapp_ontap_agent_info([])) == [Service()]


@pytest.mark.parametrize(
    "section, expected",
    [
        pytest.param(
            [],
            [Result(state=State.OK, summary="No errors")],
            id="no errors",
        ),
        pytest.param(
            [AgentInfoModel(section="disk", info="KeyError: 'uid'", is_error=True)],
            [Result(state=State.WARN, summary="disk: KeyError: 'uid'")],
            id="single error",
        ),
        pytest.param(
            [
                AgentInfoModel(section="node", info="connection timeout", is_error=True),
                AgentInfoModel(section="fan", info="Skipped: nodes fetch failed", is_error=True),
            ],
            [
                Result(state=State.WARN, summary="node: connection timeout"),
                Result(state=State.WARN, summary="fan: Skipped: nodes fetch failed"),
            ],
            id="multiple errors",
        ),
    ],
)
def test_check_netapp_ontap_errors(section: Section, expected: Sequence[Result]) -> None:
    assert list(check_netapp_ontap_agent_info(section)) == expected
