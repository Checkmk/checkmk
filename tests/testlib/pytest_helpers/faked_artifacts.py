#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Skip tests that need real build artifacts when the package was built with faked ones."""

import argparse

import pytest

OPTION = "--package-contains-faked-artifacts"
MARKER = "skip_if_faked_artifacts"


def package_contains_faked_artifacts(config: pytest.Config) -> bool:
    # The default covers runs that did not register this plugin.
    return bool(config.getoption(OPTION, default=False))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        OPTION,
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Set this if you used faked artifacts during the package build. "
            "Some tests will then be skipped which rely on real built artifacts."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", f"{MARKER}: skip test when {OPTION} is set")


@pytest.hookimpl  # plain, like pytest's runner: anything later would build the site first
def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.get_closest_marker(MARKER) and package_contains_faked_artifacts(item.config):
        pytest.skip(f"{item.nodeid}: Package contains faked artifacts!")
