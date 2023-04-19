#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.exceptions import MKAgentError, MKGeneralException, MKTimeout
from cmk.utils.type_defs import ExitSpec, HostName

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.checkers.checkresults import ActiveCheckResult
from cmk.checkers.error_handling import CheckResultErrorHandler


def _handler() -> CheckResultErrorHandler:
    return CheckResultErrorHandler(
        ExitSpec(),
        host_name=HostName("hello"),
        service_name="service_name",
        plugin_name="plugin_name",
        is_cluster=False,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        keepalive=False,
    )


def test_no_error_keeps_status_from_callee() -> None:
    handler = _handler()
    result = handler.result

    with handler:
        check_result = ActiveCheckResult(
            0,
            "summary",
            ("details", "lots of"),
            ("metrics", "x"),
        )
        result = check_result.state, check_result.as_text()

    assert result == (0, "summary | metrics x\ndetails\nlots of")
    assert handler.result is None


def test_MKTimeout_exception_returns_2() -> None:
    handler = _handler()
    with handler:
        raise MKTimeout("oops!")

    assert handler.result == (2, "Timed out\n")


def test_MKAgentError_exception_returns_2() -> None:
    handler = _handler()
    with handler:
        raise MKAgentError("oops!")

    assert handler.result == (2, "oops!\n")


def test_MKGeneralException_returns_3() -> None:
    handler = _handler()
    with handler:
        raise MKGeneralException("kaputt!")

    assert handler.result == (3, "kaputt!\n")


@pytest.mark.usefixtures("disable_debug")
def test_unhandled_exception_returns_3() -> None:
    handler = _handler()
    with handler:
        raise ValueError("unexpected :/")

    assert handler.result is not None

    state, text = handler.result
    assert state == 3
    assert text.startswith("check failed - please submit a crash report!")
