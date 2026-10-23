#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Enrich test failures with diagnostics gathered from the test host.

As a pytest plugin (see `tests.testlib.pytest_helpers.register`) this adds the
output of failed subprocesses to the report and offers `--fail-on-log-exception`.
`add_process_snapshot` is for suite conftests to attach further context in their
own `pytest_exception_interact`; the site-level dumps live in
tests.testlib.system.pytest_helpers.cmk_package.
"""

import logging
import subprocess
from collections.abc import Iterator

import pytest
import pytest_check

from tests.testlib.common.utils2 import run, verbose_called_process_error

logger = logging.getLogger(__name__)


def render_command_output(cmd: str, sudo: bool, substitute_user: str | None = None) -> str:
    """Render stdout and stderr from command as string or exception if raised.

    Command execution can have non-zero exit-code.
    """
    try:
        completed_process = run(
            cmd.split(" "),
            sudo=sudo,
            check=False,
            substitute_user=substitute_user,
        )
    except BaseException as excp:
        return f"EXCEPTION '{cmd}':\n{excp}"
    return (
        f"STDOUT '{cmd}':\n{completed_process.stdout}\nSTDERR '{cmd}':\n{completed_process.stderr}"
    )


def add_process_snapshot(excp: BaseException, sudo: bool) -> None:
    """Attach a `top` snapshot to the exception, to see what kept the host busy on a timeout."""
    excp.add_note("-" * 80)
    excp.add_note(render_command_output("top -b -n 1", sudo=sudo))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--fail-on-log-exception",
        action="store_true",
        default=False,
        help="Fail test run if any exception was logged.",
    )


@pytest.fixture(scope="function", autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def fail_on_log_exception(
    caplog: pytest.LogCaptureFixture, pytestconfig: pytest.Config
) -> Iterator[None]:
    """Fail tests if exceptions are logged. Function scoped due to caplog fixture."""
    yield
    if not pytestconfig.getoption("--fail-on-log-exception"):
        return
    for record in caplog.get_records("call"):
        if record.levelno >= logging.ERROR and record.exc_info:
            pytest_check.fail(record.message)


@pytest.hookimpl(tryfirst=True)
def pytest_exception_interact(
    node: pytest.Item | pytest.Collector,
    call: pytest.CallInfo[object],
    report: pytest.CollectReport | pytest.TestReport,
) -> None:
    """Show the output of a failed subprocess, which the exception itself does not carry."""
    if not (excinfo := call.excinfo) or not isinstance(
        excinfo.value, subprocess.CalledProcessError
    ):
        return
    excinfo.value.add_note(verbose_called_process_error(excinfo.value))
    # NOTE: We are always called from within an exception handler (hopefully!), but ruff can't
    # determine this statically.
    logger.exception(excinfo.value)  # noqa: LOG004
    report.longrepr = node.repr_failure(excinfo)
