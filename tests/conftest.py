#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file initializes the pytest environment

import logging
import os
import subprocess
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest
import pytest_check

from tests.testlib.common.utils2 import (
    is_containerized,
    verbose_called_process_error,
)
from tests.testlib.pytest_helpers.diagnostics import (
    render_command_output,
)

logger = logging.getLogger(__name__)

# This allows exceptions to be handled by IDEs (rather than just printing the results)
# when pytest based tests are being run from inside the IDE
# To enable this, set `_PYTEST_RAISE` to some value != '0' in your IDE
PYTEST_RAISE = os.getenv("_PYTEST_RAISE", "0") != "0"


def get_test_type(test_path: Path) -> str:
    testdir_path = Path(__file__).parent.resolve()
    test_path_relative = test_path.resolve().relative_to(testdir_path)
    return test_path_relative.parts[0]


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
    if not (excinfo := call.excinfo):
        return

    sudo_run_in_container = is_containerized()

    excp_ = excinfo.value
    if get_test_type(node.path) in ("composition"):
        excp_.add_note("-" * 80)
        excp_.add_note(
            render_command_output(
                "ps -ef",
                sudo=sudo_run_in_container,
            )
        )
        if sudo_run_in_container:
            for site_name in _currently_existing_omd_site_names():
                excp_.add_note("-" * 80)
                excp_.add_note(f"SITE: {site_name}")
                for command_output in _rendered_command_outputs_for_site(site_name):
                    excp_.add_note("-" * 80)
                    excp_.add_note(command_output)
        else:
            excp_.add_note("-" * 80)
            excp_.add_note(
                render_command_output(
                    "lslocks --output-all --notruncate",
                    sudo=False,
                )
            )

    if isinstance(excp_, subprocess.CalledProcessError):
        excp_.add_note(verbose_called_process_error(excp_))
        # NOTE: We are always called from within an exception handler (hopefully!), but ruff can't
        # determine this statically.
        logger.exception(excp_)  # noqa: LOG004

    report.longrepr = node.repr_failure(excinfo)
    if PYTEST_RAISE:
        raise excp_


def _currently_existing_omd_site_names() -> Generator[str]:
    """Yield the names of all currently existing OMD sites"""
    yield from (site_path.name for site_path in Path("/omd/sites").iterdir())


def _rendered_command_outputs_for_site(site_name: str) -> Generator[str]:
    """Yield rendered output for OMD site command-by-command"""
    yield render_command_output(
        "lslocks --output-all --notruncate",
        sudo=True,
        substitute_user=site_name,
    )
    yield render_command_output(
        "cmk-ui-job-scheduler-health",
        sudo=True,
        substitute_user=site_name,
    )
    yield render_command_output(
        "omd status",
        sudo=True,
        substitute_user=site_name,
    )
    yield render_command_output(
        'lq "GET hosts\\nColumns: name"',
        sudo=True,
        substitute_user=site_name,
    )


@pytest.hookimpl(tryfirst=True)
def pytest_internalerror(excinfo: pytest.ExceptionInfo[BaseException]) -> None:
    if PYTEST_RAISE:
        raise excinfo.value


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register options to pytest"""
    parser.addoption(
        "--fail-on-log-exception",
        action="store_true",
        default=False,
        help="Fail test run if any exception was logged.",
    )
