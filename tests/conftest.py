#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This file initializes the py.test environment
# pylint: disable=redefined-outer-name,wrong-import-order

from __future__ import print_function

import pytest  # type: ignore[import]
# TODO: Can we somehow push some of the registrations below to the subdirectories?
pytest.register_assert_rewrite(
    "testlib",  #
    "unit.checks.checktestlib",  #
    "unit.checks.generictests.run")

import collections

from pathlib2 import Path

from testlib import skip_unwanted_test_types
from testlib.utils import add_python_paths, cmc_path, is_running_as_site_user, repo_path, virtualenv_path

#TODO Hack: Exclude cee tests in cre repo
if not Path(cmc_path()).exists():
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

EXECUTE_IN_SITE, EXECUTE_IN_VENV = True, False

test_types = collections.OrderedDict([
    ("unit", EXECUTE_IN_VENV),
    ("pylint", EXECUTE_IN_VENV),
    ("docker", EXECUTE_IN_VENV),
    ("agent-integration", EXECUTE_IN_VENV),
    ("integration", EXECUTE_IN_SITE),
    ("gui_crawl", EXECUTE_IN_VENV),
    ("packaging", EXECUTE_IN_VENV),
    ("composition", EXECUTE_IN_VENV),
])


def pytest_addoption(parser):
    """Register the -T option to pytest"""
    options = [name for opt in parser._anonymous.options for name in opt.names()]
    # conftest.py is symlinked from enterprise/tests/conftest.py which makes it being executed
    # twice. Only register this option once.
    if "-T" in options:
        return

    parser.addoption("-T",
                     action="store",
                     metavar="TYPE",
                     default=None,
                     help="Run tests of the given TYPE. Available types are: %s" %
                     ", ".join(test_types.keys()))


def pytest_configure(config):
    """Register the type marker to pytest"""
    config.addinivalue_line(
        "markers", "type(TYPE): Mark TYPE of test. Available: %s" % ", ".join(test_types.keys()))


def pytest_collection_modifyitems(items):
    """Mark collected test types based on their location"""
    for item in items:
        type_marker = item.get_closest_marker("type")
        if type_marker and type_marker.args:
            continue  # Do not modify manually set marks
        file_path = Path("%s" % item.reportinfo()[0])
        repo_rel_path = file_path.relative_to(repo_path())
        ty = repo_rel_path.parts[1]
        if ty not in test_types:
            raise Exception("Test in %s not TYPE marked: %r (%r)" % (repo_rel_path, item, ty))
        item.add_marker(pytest.mark.type.with_args(ty))


def pytest_runtest_setup(item):
    """Skip tests of unwanted types"""
    skip_unwanted_test_types(item)


def pytest_cmdline_main(config):
    """There are 2 environments for testing:

    * A real Check_MK site environment (e.g. integration tests)
    * Python virtual environment (e.g. for unit tests)

    Depending on the selected "type" marker the environment is ensured
    or switched here."""
    if not config.getoption("-T"):
        return  # missing option is handled later

    context = test_types[config.getoption("-T")]
    if context == EXECUTE_IN_SITE and not is_running_as_site_user():
        raise Exception()
    else:
        verify_virtualenv()


def verify_virtualenv():
    if not virtualenv_path():
        raise SystemExit("ERROR: Please load virtual environment first "
                         "(Use \"pipenv shell\" or configure direnv)")


#
# MAIN
#

add_python_paths()
