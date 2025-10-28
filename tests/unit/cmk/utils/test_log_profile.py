#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="arg-type"

import logging
import re

import pytest

from cmk.utils.log.profile import log_duration


def test_log_duration_on_decorated_function(caplog: pytest.LogCaptureFixture) -> None:
    @log_duration(logger=logging.getLogger(), level="debug")
    def add(x: int, y: int) -> int:
        return x + y

    with caplog.at_level(logging.DEBUG):
        add(1, 1)

    assert re.search(r"CALLING .*\.add …", caplog.records[0].msg)
    assert re.search(r"FINISHED .*\.add \(\d.\d+s\)", caplog.records[1].msg)


def test_log_duration_on_decorated_method(caplog: pytest.LogCaptureFixture) -> None:
    class Arithmetic:
        @log_duration(logger=logging.getLogger(), level="debug")
        def add(self, x: int, y: int) -> int:
            return x + y

    with caplog.at_level(logging.DEBUG):
        Arithmetic().add(1, 1)

    assert re.search(r"CALLING .*Arithmetic\.add …", caplog.records[0].msg)
    assert re.search(r"FINISHED .*Arithmetic\.add \(\d.\d+s\)", caplog.records[1].msg)


def test_log_duration_wrapping_existing_function(caplog: pytest.LogCaptureFixture) -> None:
    debug_log_duration = log_duration(logger=logging.getLogger(), level="debug")

    with caplog.at_level(logging.DEBUG):
        debug_log_duration(sum)([1, 1])

    assert re.search(r"CALLING builtins\.sum …", caplog.records[0].msg)
    assert re.search(r"FINISHED builtins\.sum \(\d.\d+s\)", caplog.records[1].msg)


def test_log_duration_print_params_with_args(caplog: pytest.LogCaptureFixture) -> None:
    @log_duration(logger=logging.getLogger(), level="debug", print_params=True)
    def add(x: int, y: int) -> int:
        return x + y

    with caplog.at_level(logging.DEBUG):
        add(1, 1)

    assert re.search(r"CALLING .*\.add …", caplog.records[0].msg)
    assert re.search(r"ARGS .*\.add: \(1, 1\)", caplog.records[1].msg)
    assert re.search(r"FINISHED .*\.add \(\d.\d+s\)", caplog.records[2].msg)


def test_log_duration_print_params_with_kwargs(caplog: pytest.LogCaptureFixture) -> None:
    @log_duration(logger=logging.getLogger(), level="debug", print_params=True)
    def add(x: int, y: int) -> int:
        return x + y

    with caplog.at_level(logging.DEBUG):
        add(x=1, y=1)

    assert re.search(r"CALLING .*\.add …", caplog.records[0].msg)
    assert re.search(r"ARGS .*\.add: {'x': 1, 'y': 1}", caplog.records[1].msg)
    assert re.search(r"FINISHED .*\.add \(\d.\d+s\)", caplog.records[2].msg)


def test_log_duration_invalid_level_passed() -> None:
    with pytest.raises(ValueError, match="Invalid log level passed: 'foobar'"):
        log_duration(logger=logging.getLogger(), level="foobar")
