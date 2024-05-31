#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file initializes the pytest environment
# pylint: disable=redefined-outer-name,wrong-import-order

import logging
import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest
import pytest_check  # type: ignore[import-untyped]
from pytest_metadata.plugin import metadata_key  # type: ignore[import-untyped]


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


if os.getenv("_PYTEST_RAISE", "0") != "0":
    # This allows exceptions to be handled by IDEs (rather than just printing the results)
    # when pytest based tests are being run from inside the IDE
    # To enable this, set `_PYTEST_RAISE` to some value != '0' in your IDE
    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value


# TODO: Can we somehow push some of the registrations below to the subdirectories?
pytest.register_assert_rewrite(
    "tests.testlib", "tests.unit.checks.checktestlib", "tests.unit.checks.generictests.run"
)

pytest_plugins = ("tests.testlib.playwright.plugin",)

from tests.testlib.utils import (
    add_python_paths,
    current_base_branch_name,
    is_cloud_repo,
    is_enterprise_repo,
    is_managed_repo,
    is_saas_repo,
    repo_path,
)

collect_ignore: list[str] = []

# Faker creates a bunch of annoying DEBUG level log entries, which clutter the output of test
# runs and prevent us from spot the important messages easily. Reduce the Reduce the log level
# selectively.
# See also https://github.com/joke2k/faker/issues/753
logging.getLogger("faker").setLevel(logging.ERROR)

#
# Each test is of one of the following types.
#
# The tests are marked using the marker pytest.marker.type("TYPE")
# which is added to the test automatically according to their location.
#
# With each call to pytest one type of tests needs to be selected using
# the "-T TYPE" option. Only these tests will then be executed. Tests of
# the other type will be skipped.
#

test_types = [
    "unit",
    "pylint",
    "docker",
    "agent-integration",
    "agent-plugin-unit",
    "integration",
    "gui_crawl",
    "gui_e2e",
    "packaging",
    "composition",
    "code_quality",
    "update",
    "schemathesis_openapi",
    "plugins_integration",
    "extension_compatibility",
]


def pytest_addoption(parser):
    """Register the -T option to pytest"""
    parser.addoption(
        "-T",
        action="store",
        metavar="TYPE",
        default="unit",
        help="Run tests of the given TYPE. Available types are: %s" % ", ".join(test_types),
    )
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


def pytest_configure(config):
    """Add important environment variables to the report and register custom pytest markers"""
    env_vars = {
        "BRANCH": current_base_branch_name(),
        "EDITION": "cee",
        "VERSION": "daily",
        "DISTRO": "",
        "TZ": "",
        "REUSE": "0",
        "CLEANUP": "1",
    }
    env_lines = [f"{key}={os.getenv(key, val)}" for key, val in env_vars.items() if val]
    config.stash[metadata_key]["Variables"] = (
        "<ul><li>\n" + ("</li><li>\n".join(env_lines)) + "</li></ul>"
    )

    config.addinivalue_line(
        "markers", "type(TYPE): Mark TYPE of test. Available: %s" % ", ".join(test_types)
    )
    config.addinivalue_line(
        "markers",
        "non_resilient:"
        " Tests marked as non-resilient are allowed to fail when run in resilience test.",
    )

    if not config.getoption("-T") == "schemathesis_openapi":
        # Exclude schemathesis_openapi tests from global collection
        global collect_ignore
        collect_ignore = ["schemathesis_openapi"]


def pytest_collection_modifyitems(items: list[pytest.Item], config: pytest.Config) -> None:
    """Mark collected test types based on their location"""
    items[:] = items[0 : config.getoption("--limit")]
    for item in items:
        type_marker = item.get_closest_marker("type")
        if type_marker and type_marker.args:
            continue  # Do not modify manually set marks
        file_path = Path("%s" % item.reportinfo()[0])
        repo_rel_path = file_path.relative_to(repo_path())
        ty = repo_rel_path.parts[1]
        if ty not in test_types:
            if not isinstance(item, pytest.DoctestItem):
                raise Exception(f"Test in {repo_rel_path} not TYPE marked: {item!r} ({ty!r})")

        item.add_marker(pytest.mark.type.with_args(ty))

        if config.getoption("--no-skip"):
            item.own_markers = [_ for _ in item.own_markers if _.name not in ("skip", "skipif")]


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests of unwanted types"""
    _skip_unwanted_test_types(item)


def _skip_unwanted_test_types(item: pytest.Item) -> None:
    test_type = item.get_closest_marker("type")
    if test_type is None:
        raise Exception("Test is not TYPE marked: %s" % item)

    if not item.config.getoption("-T"):
        raise SystemExit("Please specify type of tests to be executed (py.test -T TYPE)")

    test_type_name = test_type.args[0]
    if test_type_name != item.config.getoption("-T"):
        pytest.skip("Not testing type %r" % test_type_name)


# Cleanup temporary directory created above
@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk():
    yield

    import cmk.utils.paths

    if "pytest_cmk_" not in str(cmk.utils.paths.tmp_dir):
        return

    try:
        shutil.rmtree(str(cmk.utils.paths.tmp_dir))
    except FileNotFoundError:
        pass


def pytest_cmdline_main(config):
    if not config.getoption("-T"):
        return  # missing option is handled later
    verify_virtualenv()


def verify_virtualenv():
    if not sys.prefix.endswith("/.venv"):
        raise SystemExit(
            "ERROR: Please load virtual environment first "
            f'(Use "pipenv shell" or configure direnv) ({sys.prefix})'
        )


_UNPATCHED_PATHS: Final = {
    # FIXME :-(
    # dropping these makes tests/unit/cmk/gui/watolib/test_config_sync.py fail.
    "local_dashboards_dir",
    "local_views_dir",
    "local_reports_dir",
}


# Some cmk.* code is calling things like cmk_version.is_raw_edition() at import time
# (e.g. cmk/base/default_config/notify.py) for edition specific variable
# defaults. In integration tests we want to use the exact version of the
# site. For unit tests we assume we are in Enterprise Edition context.
def fake_version_and_paths() -> None:
    from pytest import MonkeyPatch  # pylint: disable=import-outside-toplevel

    monkeypatch = MonkeyPatch()
    tmp_dir = tempfile.mkdtemp(prefix="pytest_cmk_")

    import cmk.utils.paths  # pylint: disable=import-outside-toplevel
    import cmk.utils.version as cmk_version  # pylint: disable=import-outside-toplevel

    if is_managed_repo():
        edition_short = "cme"
    elif is_cloud_repo():
        edition_short = "cce"
    elif is_saas_repo():
        edition_short = "cse"
    elif is_enterprise_repo():
        edition_short = "cee"
    else:
        edition_short = "cre"

    monkeypatch.setattr(cmk_version, "orig_omd_version", cmk_version.omd_version, raising=False)
    monkeypatch.setattr(
        cmk_version, "omd_version", lambda: f"{cmk_version.__version__}.{edition_short}"
    )

    # Unit test context: load all available modules
    original_omd_root = Path(cmk.utils.paths.omd_root)
    for name, value in vars(cmk.utils.paths).items():
        if name.startswith("_") or not isinstance(value, (str, Path)) or name in _UNPATCHED_PATHS:
            continue

        try:
            monkeypatch.setattr(
                f"cmk.utils.paths.{name}",
                type(value)(tmp_dir / Path(value).relative_to(original_omd_root)),
            )
        except ValueError:
            pass  # path is outside of omd_root

    # these use repo_path
    monkeypatch.setattr("cmk.utils.paths.agents_dir", "%s/agents" % repo_path())
    monkeypatch.setattr("cmk.utils.paths.checks_dir", "%s/checks" % repo_path())
    monkeypatch.setattr("cmk.utils.paths.notifications_dir", repo_path() / "notifications")
    monkeypatch.setattr("cmk.utils.paths.inventory_dir", "%s/inventory" % repo_path())
    monkeypatch.setattr("cmk.utils.paths.legacy_check_manpages_dir", "%s/checkman" % repo_path())


#
# MAIN
#

add_python_paths()
fake_version_and_paths()
