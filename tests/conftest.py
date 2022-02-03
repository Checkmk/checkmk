#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file initializes the py.test environment
# pylint: disable=redefined-outer-name,wrong-import-order

import collections
import enum
import errno
import shutil
from pathlib import Path

import pytest
from _pytest.doctest import DoctestItem

# TODO: Can we somehow push some of the registrations below to the subdirectories?
pytest.register_assert_rewrite(
    "tests.testlib", "tests.unit.checks.checktestlib", "tests.unit.checks.generictests.run"
)

import tests.testlib as testlib

# TODO Hack: Exclude cee tests in cre repo
if not Path(testlib.utils.cmc_path()).exists():
    collect_ignore_glob = ["*/cee/*"]

#
# Each test is of one of the following types.
#
# The tests are marked using the marker pytest.marker.type("TYPE")
# which is added to the test automatically according to their location.
#
# With each call to py.test one type of tests needs to be selected using
# the "-T TYPE" option. Only these tests will then be executed. Tests of
# the other type will be skipped.
#


class ExecutionType(enum.Enum):
    Site = enum.auto()
    VirtualEnv = enum.auto()


test_types = collections.OrderedDict(
    [
        ("unit", ExecutionType.VirtualEnv),
        ("pylint", ExecutionType.VirtualEnv),
        ("docker", ExecutionType.VirtualEnv),
        ("agent-integration", ExecutionType.VirtualEnv),
        ("agent-plugin-unit", ExecutionType.VirtualEnv),
        ("integration", ExecutionType.Site),
        ("gui_crawl", ExecutionType.VirtualEnv),
        ("gui_e2e", ExecutionType.VirtualEnv),
        ("packaging", ExecutionType.VirtualEnv),
        ("composition", ExecutionType.VirtualEnv),
    ]
)


def pytest_addoption(parser):
    """Register the -T option to pytest"""
    options = [name for opt in parser._anonymous.options for name in opt.names()]
    # conftest.py is symlinked from enterprise/tests/conftest.py which makes it being executed
    # twice. Only register this option once.
    if "-T" in options:
        return

    parser.addoption(
        "-T",
        action="store",
        metavar="TYPE",
        default=None,
        help="Run tests of the given TYPE. Available types are: %s" % ", ".join(test_types.keys()),
    )


def pytest_configure(config):
    """Registers custom markers to pytest"""
    config.addinivalue_line(
        "markers", "type(TYPE): Mark TYPE of test. Available: %s" % ", ".join(test_types.keys())
    )
    config.addinivalue_line(
        "markers",
        "non_resilient:"
        " Tests marked as non-resilient are allowed to fail when run in resilience test.",
    )


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
            if not isinstance(item, DoctestItem):
                raise Exception("Test in %s not TYPE marked: %r (%r)" % (repo_rel_path, item, ty))

        item.add_marker(pytest.mark.type.with_args(ty))


def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    testlib.skip_unwanted_test_types(item)


# Cleanup temporary directory created above
@pytest.fixture(scope="session", autouse=True)
def cleanup_cmk():
    yield

    if testlib.is_running_as_site_user():
        return

    import cmk.utils.paths

    if "pytest_cmk_" not in cmk.utils.paths.tmp_dir:
        return

    try:
        shutil.rmtree(cmk.utils.paths.tmp_dir)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise  # re-raise exception


def pytest_cmdline_main(config):
    """There are 2 environments for testing:

    * A real Check_MK site environment (e.g. integration tests)
    * Python virtual environment (e.g. for unit tests)

    Depending on the selected "type" marker the environment is ensured
    or switched here."""
    if not config.getoption("-T"):
        return  # missing option is handled later

    context = test_types[config.getoption("-T")]
    if context == ExecutionType.VirtualEnv:
        verify_virtualenv()
    elif context == ExecutionType.Site:
        verify_site()


def verify_site():
    if not testlib.is_running_as_site_user():
        raise RuntimeError("Please run tests as site user.")


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
