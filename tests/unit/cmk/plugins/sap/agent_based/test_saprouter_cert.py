#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.sap.agent_based import saprouter_cert

_VALID_STRING_TABLE: StringTable = [
    ["SSO", "for", "USER", '"prdadm"'],
    ["with", "PSE", "file", '"/usr/users/prdadm/saprouter/local.pse"'],
    ["Validity", "-", "NotBefore:", "Wed", "Mar", "30", "11:21:33", "2016", "(160330102133Z)"],
    ["NotAfter:", "Thu", "Mar", "30", "11:21:33", "2017", "(170330102133Z)"],
]

_FAILED_STRING_TABLE: StringTable = [
    ["get_my_name:", "no", "PSE", "name", "supplied,", "no", "SSO", "credentials", "found!"],
]

_PARAMS = {"validity_age": (30 * 86400, 7 * 86400)}


def test_parse_saprouter_cert_valid() -> None:
    parsed = saprouter_cert.parse_saprouter_cert(_VALID_STRING_TABLE)
    assert parsed["sso_user"] == "prdadm"
    assert parsed["pse_file"] == "/usr/users/prdadm/saprouter/local.pse"
    assert parsed["valid"]["not_before"][1] == "2016-3-30"
    assert parsed["valid"]["not_after"][1] == "2017-3-30"


def test_parse_saprouter_cert_failed() -> None:
    parsed = saprouter_cert.parse_saprouter_cert(_FAILED_STRING_TABLE)
    assert "valid" not in parsed
    assert parsed["failed"] == ["get_my_name: no PSE name supplied, no SSO credentials found!"]


@pytest.mark.parametrize(
    "section, expected",
    [
        (saprouter_cert.parse_saprouter_cert(_VALID_STRING_TABLE), [Service()]),
        ({}, []),
    ],
)
def test_discover_saprouter_cert(section: saprouter_cert.Section, expected: list[Service]) -> None:
    assert list(saprouter_cert.discover_saprouter_cert(section)) == expected


@pytest.mark.parametrize(
    "days_to_expiry, expected_state, expect_threshold_text",
    [
        (3, State.CRIT, True),
        (15, State.WARN, True),
        (100, State.OK, False),
    ],
)
def test_check_saprouter_cert(
    monkeypatch: pytest.MonkeyPatch,
    days_to_expiry: int,
    expected_state: State,
    expect_threshold_text: bool,
) -> None:
    parsed = saprouter_cert.parse_saprouter_cert(_VALID_STRING_TABLE)
    not_after = parsed["valid"]["not_after"][0]
    monkeypatch.setattr(time, "time", lambda: not_after - days_to_expiry * 86400)
    (result,) = saprouter_cert.check_saprouter_cert(_PARAMS, parsed)
    assert isinstance(result, Result)
    assert result.state is expected_state
    assert "Valid from 2016-3-30 to 2017-3-30" in result.summary
    assert ("warn/crit below" in result.summary) is expect_threshold_text


def test_check_saprouter_cert_failed() -> None:
    parsed = saprouter_cert.parse_saprouter_cert(_FAILED_STRING_TABLE)
    (result,) = saprouter_cert.check_saprouter_cert(_PARAMS, parsed)
    assert isinstance(result, Result)
    assert result.state is State.UNKNOWN
    assert result.summary == "get_my_name: no PSE name supplied, no SSO credentials found!"
