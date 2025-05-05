#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file initializes the pytest environment
# pylint: disable=redefined-outer-name,wrong-import-order

import logging
import os
import subprocess
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest
import pytest_check
from playwright.sync_api import TimeoutError as PWTimeoutError
from pytest_metadata.plugin import metadata_key  # type: ignore[import-untyped]

# TODO: Can we somehow push some of the registrations below to the subdirectories?
# Needs to be executed before the import of those modules
pytest.register_assert_rewrite(
    "tests.testlib", "tests.unit.checks.checktestlib", "tests.unit.checks.generictests.run"
)

from tests.testlib.common.repo import (  # noqa: E402
    add_python_paths,
    current_base_branch_name,
)
from tests.testlib.pytest_helpers.timeouts import MonitorTimeout, SessionTimeoutError  # noqa: E402
from tests.testlib.utils import (  # noqa: E402
    is_containerized,
    run,
    verbose_called_process_error,
)

logger = logging.getLogger(__name__)

pytest_plugins = ("tests.gui_e2e.testlib.playwright.plugin",)

# This allows exceptions to be handled by IDEs (rather than just printing the results)
# when pytest based tests are being run from inside the IDE
# To enable this, set `_PYTEST_RAISE` to some value != '0' in your IDE
PYTEST_RAISE = os.getenv("_PYTEST_RAISE", "0") != "0"


def get_test_type(test_path: Path) -> str:
    testdir_path = Path(__file__).parent.resolve()
    test_path_relative = test_path.resolve().relative_to(testdir_path)
    return test_path_relative.parts[0]


@pytest.fixture(scope="session", autouse=True)
def _session_timeout(pytestconfig: pytest.Config) -> Iterator[None]:
    session_timeout_cli = "--session-timeout"
    timeout_duration = (
        _session_timeout_option
        if isinstance(_session_timeout_option := pytestconfig.getoption(session_timeout_cli), int)
        else 0
    )
    with MonitorTimeout(timeout=timeout_duration):
        yield


@pytest.fixture(scope="function", autouse=True)
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
    call: pytest.CallInfo,
    report: pytest.CollectReport | pytest.TestReport,
) -> None:
    if not (excinfo := call.excinfo):
        return

    sudo_run_in_container = is_containerized()

    excp_ = excinfo.value
    if get_test_type(node.path) in ("composition"):
        excp_.add_note("-" * 80)
        excp_.add_note(
            _render_command_output(
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
                _render_command_output(
                    "lslocks --output-all --notruncate",
                    sudo=False,
                )
            )

    if excinfo.type == SessionTimeoutError:
        # Prevents execution of the next test and exits the pytest-run, and
        # leads to clean termination of the affected test run.
        node.session.shouldstop = True
    elif excinfo.type in (TimeoutError, PWTimeoutError):
        excp_.add_note("-" * 80)
        excp_.add_note(
            _render_command_output(
                "top -b -n 1",
                sudo=sudo_run_in_container,
            )
        )
    elif isinstance(excp_, subprocess.CalledProcessError):
        excp_.add_note(verbose_called_process_error(excp_))
        logger.exception(excp_)

    report.longrepr = node.repr_failure(excinfo)
    if PYTEST_RAISE:
        raise excp_


def _render_command_output(cmd: str, sudo: bool, substitute_user: str | None = None) -> str:
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


def _currently_existing_omd_site_names() -> Generator[str]:
    """Yield the names of all currently existing OMD sites"""
    yield from (site_path.name for site_path in Path("/omd/sites").iterdir())


def _rendered_command_outputs_for_site(site_name: str) -> Generator[str]:
    """Yield rendered output for OMD site command-by-command"""
    yield _render_command_output(
        "lslocks --output-all --notruncate",
        sudo=True,
        substitute_user=site_name,
    )
    yield _render_command_output(
        "cmk-ui-job-scheduler-health",
        sudo=True,
        substitute_user=site_name,
    )
    yield _render_command_output(
        "omd status",
        sudo=True,
        substitute_user=site_name,
    )
    yield _render_command_output(
        'lq "GET hosts\\nColumns: name"',
        sudo=True,
        substitute_user=site_name,
    )


@pytest.hookimpl(tryfirst=True)
def pytest_internalerror(excinfo: pytest.ExceptionInfo) -> None:
    if PYTEST_RAISE:
        raise excinfo.value


collect_ignore: list[str] = []

# Faker creates a bunch of annoying DEBUG level log entries, which clutter the output of test
# runs and prevent us from spot the important messages easily. Reduce the Reduce the log level
# selectively.
# See also https://github.com/joke2k/faker/issues/753
logging.getLogger("faker").setLevel(logging.ERROR)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register options to pytest"""
    parser.addoption(
        "--fail-on-log-exception",
        action="store_true",
        default=False,
        help="Fail test run if any exception was logged.",
    )
    parser.addoption(
        "--no-skip",
        action="store_true",
        default=False,
        help="Disable any skip or skipif markers.",
    )
    parser.addoption(
        "--limit",
        action="store",
        default=None,
        type=int,
        help="Select only the first N tests from the collection list.",
    )
    parser.addoption(
        "--session-timeout",
        action="store",
        metavar="TIMEOUT",
        default=0,
        type=int,
        help="Terminate testsuite run cleanly after TIMEOUT seconds. By default, 0 (disabled).",
    )
    parser.addoption(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simulate test execution. XFail all tests that would be executed.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Add important environment variables to the report and register custom pytest markers"""
    env_vars = {
        "BRANCH": current_base_branch_name(),
        "EDITION": "cee",
        "VERSION": "daily",
        "DISTRO": "",
        "TZ": "UTC",
        "REUSE": "0",
        "CLEANUP": "1",
    }
    env_lines = [f"{key}={os.getenv(key, val)}" for key, val in env_vars.items() if val]
    config.stash[metadata_key]["Variables"] = (
        "<ul><li>\n" + ("</li><li>\n".join(env_lines)) + "</li></ul>"
    )

    # Exclude schemathesis_openapi tests from global collection
    global collect_ignore
    collect_ignore = ["schemathesis_openapi"]


def pytest_collection_modifyitems(items: list[pytest.Item], config: pytest.Config) -> None:
    """Mark collected test types based on their location"""
    items[:] = items[0 : config.getoption("--limit")]
    for item in items:
        if config.getoption("--no-skip"):
            item.own_markers = [_ for _ in item.own_markers if _.name not in ("skip", "skipif")]


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Modify the setup phase for a test item"""
    if item.config.getoption("--dry-run"):
        pytest.xfail("*** DRY-RUN ***")


#
# MAIN
#
add_python_paths()
