#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.exceptions import MKAgentError, MKGeneralException, MKTimeout
from cmk.utils.type_defs import ExitSpec, HostName

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.checkers import error_handling
from cmk.checkers.checkresults import ActiveCheckResult


def test_no_error_keeps_returns_status_from_callee() -> None:
    state, text = error_handling._handle_success(
        ActiveCheckResult(
            0,
            "summary",
            ("details", "lots of"),
            ("metrics", "x"),
        )
    )
    assert state == 0
    assert text == "summary | metrics x\ndetails\nlots of\n"


def test_MKTimeout_exception_returns_2() -> None:
    hostname = HostName("host_name")
    state, text = error_handling._handle_failure(
        MKTimeout("oops!"),
        ExitSpec(),
        host_name=hostname,
        service_name="service_name",
        plugin_name="pluging_name",
        is_cluster=False,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        rtc_package=None,
        keepalive=False,
    )
    assert state == 2
    assert text == "Timed out\n"


def test_MKAgentError_exception_returns_2() -> None:
    hostname = "host_name"
    state, text = error_handling._handle_failure(
        MKAgentError("oops!"),
        ExitSpec(),
        host_name=hostname,
        service_name="service_name",
        plugin_name="pluging_name",
        is_cluster=False,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        rtc_package=None,
        keepalive=False,
    )
    assert state == 2
    assert text == "oops!\n"


def test_MKGeneralException_returns_3() -> None:
    hostname = "host_name"
    state, text = error_handling._handle_failure(
        MKGeneralException("kaputt!"),
        ExitSpec(),
        host_name=hostname,
        service_name="service_name",
        plugin_name="pluging_name",
        is_cluster=False,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        rtc_package=None,
        keepalive=False,
    )
    assert state == 3
    assert text == "kaputt!\n"


@pytest.mark.usefixtures("disable_debug")
def test_unhandled_exception_returns_3() -> None:
    hostname = "host_name"
    state, text = error_handling._handle_failure(
        ValueError("unexpected :/"),
        ExitSpec(),
        host_name=hostname,
        service_name="service_name",
        plugin_name="pluging_name",
        is_cluster=False,
        snmp_backend=SNMPBackendEnum.CLASSIC,
        rtc_package=None,
        keepalive=False,
    )
    assert state == 3
    assert text.startswith("check failed - please submit a crash report!")
