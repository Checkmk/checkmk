#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file initializes the pytest environment
# pylint: disable=redefined-outer-name,wrong-import-order

import logging
import os
import shutil
from pathlib import Path

import pytest
from pytest_metadata.plugin import metadata_key  # type: ignore[import-untyped]

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

import tests.testlib as testlib
from tests.testlib.utils import current_base_branch_name

collect_ignore = []

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


def pytest_collection_modifyitems(items):
    """Mark collected test types based on their location"""
    for item in items:
        type_marker = item.get_closest_marker("type")
        if type_marker and type_marker.args:
            continue  # Do not modify manually set marks
        file_path = Path("%s" % item.reportinfo()[0])
        repo_rel_path = file_path.relative_to(testlib.repo_path())
        ty = repo_rel_path.parts[1]
        if ty not in test_types:
            if not isinstance(item, pytest.DoctestItem):
                raise Exception(f"Test in {repo_rel_path} not TYPE marked: {item!r} ({ty!r})")

        item.add_marker(pytest.mark.type.with_args(ty))


def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    testlib.skip_unwanted_test_types(item)


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
    if not testlib.virtualenv_path():
        raise SystemExit(
            "ERROR: Please load virtual environment first "
            '(Use "pipenv shell" or configure direnv)'
        )


#
# MAIN
#

testlib.add_python_paths()
testlib.fake_version_and_paths()
