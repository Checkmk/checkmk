#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Let an attached debugger stop on a failing test.

Set `_PYTEST_RAISE` to anything but "0" in the IDE's run configuration and the
exception of a failing test (or a pytest internal error) is re-raised instead
of being turned into a report.

Register from a conftest's `pytest_addoption` via `tests.testlib.pytest_helpers.register`.
"""

import os

import pytest

PYTEST_RAISE = os.getenv("_PYTEST_RAISE", "0") != "0"


@pytest.hookimpl  # plain: runs after the tryfirst hooks that add notes to the exception
def pytest_exception_interact(call: pytest.CallInfo[object]) -> None:
    if PYTEST_RAISE and call.excinfo:
        raise call.excinfo.value


@pytest.hookimpl(tryfirst=True)
def pytest_internalerror(excinfo: pytest.ExceptionInfo[BaseException]) -> None:
    if PYTEST_RAISE:
        raise excinfo.value
