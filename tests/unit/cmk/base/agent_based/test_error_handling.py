#!/usr/bin/env python3

# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKAgentError, MKGeneralException, MKTimeout
from cmk.utils.type_defs import HostName

import cmk.base.agent_based.error_handling as error_handling
from cmk.base.config import HostConfig


@pytest.fixture(name="hostname")
def hostname_fixture(monkeypatch) -> HostName:
    # Hide ugly Scenario hack.
    hostname = "hostname"
    ts = Scenario()
    ts.add_host(hostname)
    ts.apply(monkeypatch)
    return hostname


def test_no_error_keeps_returns_status_from_callee(hostname: HostName, capsys) -> None:
    state, text = error_handling._handle_success(
        ActiveCheckResult(
            0,
            "summary",
            ("details", "lots of"),
            ("metrics", "x"),
        )
    )
    error_handling._handle_output(text, hostname)

    assert state == 0
    assert capsys.readouterr().out == "summary | metrics x\ndetails\nlots of\n"


def test_MKTimeout_exception_returns_2(hostname: HostName, capsys) -> None:
    host_config = HostConfig.make_host_config(hostname)
    state, text = error_handling._handle_failure(
        MKTimeout("oops!"),
        host_config.exit_code_spec(),
        host_config=host_config,
        service_name="service_name",
        plugin_name="pluging_name",
    )
    error_handling._handle_output(text, hostname)

    assert state == 2
    assert capsys.readouterr().out == "Timed out\n"


def test_MKAgentError_exception_returns_2(hostname: HostName, capsys) -> None:
    host_config = HostConfig.make_host_config(hostname)
    state, text = error_handling._handle_failure(
        MKAgentError("oops!"),
        host_config.exit_code_spec(),
        host_config=host_config,
        service_name="service_name",
        plugin_name="pluging_name",
    )
    error_handling._handle_output(text, hostname)

    assert state == 2
    assert capsys.readouterr().out == "oops!\n"


def test_MKGeneralException_returns_3(hostname: HostName, capsys) -> None:
    host_config = HostConfig.make_host_config(hostname)
    state, text = error_handling._handle_failure(
        MKGeneralException("kaputt!"),
        host_config.exit_code_spec(),
        host_config=host_config,
        service_name="service_name",
        plugin_name="pluging_name",
    )
    error_handling._handle_output(text, hostname)

    assert state == 3
    assert capsys.readouterr().out == "kaputt!\n"


@pytest.mark.usefixtures("disable_debug")
def test_unhandled_exception_returns_3(hostname: HostName, capsys) -> None:
    host_config = HostConfig.make_host_config(hostname)
    state, text = error_handling._handle_failure(
        ValueError("unexpected :/"),
        host_config.exit_code_spec(),
        host_config=host_config,
        service_name="service_name",
        plugin_name="pluging_name",
    )
    error_handling._handle_output(text, hostname)

    assert state == 3
    assert capsys.readouterr().out.startswith("check failed - please submit a crash report!")
