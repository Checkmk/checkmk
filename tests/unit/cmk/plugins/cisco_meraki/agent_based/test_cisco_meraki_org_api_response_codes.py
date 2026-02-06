#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from polyfactory.factories import TypedDictFactory

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.cisco_meraki.agent_based.cisco_meraki_org_api_response_codes import (
    check_api_response_codes,
    discover_api_response_codes,
    parse_api_response_codes,
)
from cmk.plugins.cisco_meraki.lib.schema import ApiResponseCodes


class _ApiResponseCodesFactory(TypedDictFactory[ApiResponseCodes]):
    __check_model__ = False


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_discover_api_response_codes_no_payload(string_table: StringTable) -> None:
    section = parse_api_response_codes(string_table)
    assert not list(discover_api_response_codes(section))


def test_discover_api_response_codes() -> None:
    overviews = [
        _ApiResponseCodesFactory.build(organization_name="Name1", organization_id="123"),
        _ApiResponseCodesFactory.build(organization_name="Name2", organization_id="456"),
    ]
    string_table = [[f"{json.dumps(overviews)}"]]
    section = parse_api_response_codes(string_table)

    value = list(discover_api_response_codes(section))
    expected = [
        Service(item="Name1/123"),
        Service(item="Name2/456"),
    ]

    assert value == expected


@pytest.mark.parametrize("string_table", [[], [[]], [[""]]])
def test_check_api_response_codes_no_payload(string_table: StringTable) -> None:
    section = parse_api_response_codes(string_table)
    assert not list(check_api_response_codes("", section))


def test_check_api_response_codes() -> None:
    overviews = _ApiResponseCodesFactory.build(
        organization_id="123",
        organization_name="Name1",
        counts=[
            {"code": 200, "count": 1},
            {"code": 201, "count": 1},
            {"code": 300, "count": 1},
            {"code": 301, "count": 1},
            {"code": 400, "count": 1},
            {"code": 401, "count": 1},
            {"code": 500, "count": 1},
            {"code": 501, "count": 1},
        ],
    )
    string_table = [[f"[{json.dumps(overviews)}]"]]
    section = parse_api_response_codes(string_table)

    value = list(check_api_response_codes("Name1/123", section))
    expected = [
        Result(state=State.OK, notice="Organization name: Name1"),
        Result(state=State.OK, notice="Organization ID: 123"),
        Result(state=State.OK, summary="Code 2xx: 2"),
        Metric("api_code_2xx", 2.0),
        Result(state=State.OK, summary="Code 3xx: 2"),
        Metric("api_code_3xx", 2.0),
        Result(state=State.OK, summary="Code 4xx: 2"),
        Metric("api_code_4xx", 2.0),
        Result(state=State.OK, summary="Code 5xx: 2"),
        Metric("api_code_5xx", 2.0),
    ]

    assert value == expected


def test_check_api_unsupported_response_code() -> None:
    overviews = _ApiResponseCodesFactory.build(
        organization_id="123",
        organization_name="Name1",
        counts=[{"code": 900, "count": 1}],
    )
    string_table = [[f"[{json.dumps(overviews)}]"]]
    section = parse_api_response_codes(string_table)

    value = list(check_api_response_codes("Name1/123", section))
    expected = [
        Result(state=State.OK, notice="Organization name: Name1"),
        Result(state=State.OK, notice="Organization ID: 123"),
    ]

    assert value == expected
