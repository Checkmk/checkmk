#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKAgentError, MKGeneralException, MKTimeout
from cmk.utils.type_defs import HostName

from cmk.base.agent_based.decorator import handle_check_mk_check_result


@pytest.fixture(name="hostname")
def hostname_fixture(monkeypatch) -> HostName:
    # Hide ugly Scenario hack.
    hostname = "hostname"
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)
    return hostname


def test_no_error_keeps_returns_status_from_callee(hostname: HostName, capsys) -> None:
    @handle_check_mk_check_result("test", "description")
    def fn(hostname: HostName) -> ActiveCheckResult:
        return ActiveCheckResult(
            0,
            "summary",
            ("details", "lots of"),
            ("metrics", "x"),
        )

    assert fn(hostname) == 0
    assert capsys.readouterr().out == "summary | metrics x\ndetails\nlots of\n"


def test_MKTimeout_exception_returns_2(hostname: HostName, capsys) -> None:
    @handle_check_mk_check_result("test", "description")
    def fn(hostname: HostName) -> ActiveCheckResult:
        raise MKTimeout("oops!")

    assert fn(hostname) == 2
    assert capsys.readouterr().out == "Timed out\n"


def test_MKAgentError_exception_returns_2(hostname: HostName, capsys) -> None:
    @handle_check_mk_check_result("test", "description")
    def fn(hostname: HostName) -> ActiveCheckResult:
        raise MKAgentError("oops!")

    assert fn(hostname) == 2
    assert capsys.readouterr().out == "oops!\n"


def test_MKGeneralException_returns_3(hostname: HostName, capsys) -> None:
    @handle_check_mk_check_result("test", "description")
    def fn(hostname: HostName) -> ActiveCheckResult:
        raise MKGeneralException("kaputt!")

    assert fn(hostname) == 3
    assert capsys.readouterr().out == "kaputt!\n"


@pytest.mark.usefixtures("disable_debug")
def test_unhandled_exception_returns_3(hostname: HostName, capsys) -> None:
    @handle_check_mk_check_result("test", "description")
    def fn(hostname: HostName) -> ActiveCheckResult:
        raise ValueError("unexpected :/")

    assert fn(hostname) == 3
    assert capsys.readouterr().out.startswith("check failed - please submit a crash report!")
