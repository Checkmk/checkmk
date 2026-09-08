#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Options and markers that narrow down which tests of a suite run, and how.

Register from a conftest's `pytest_addoption` via `tests.testlib.pytest_helpers.register`.
"""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
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
        "--medium-chain",
        action="store_true",
        default=False,
        help=(
            "Mark this run as part of the gated medium chain, which skips tests "
            "carrying skip_if_medium_chain. A plain option and not a '-m' filter "
            "on purpose: the make targets in run_tests.sh set their own '-m' after "
            "TEST_FILTER, and pytest lets the last '-m' win."
        ),
    )
    parser.addoption(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simulate test execution. XFail all tests that would be executed.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "medium_test_chain: marks tests as part of the medium-test-chain CI job",
    )
    config.addinivalue_line(
        "markers",
        "skip_if_medium_chain: skip test when --medium-chain is set. For tests "
        "that cannot work pre-submit, not for tests that merely fail",
    )
    config.addinivalue_line(
        "markers",
        "requires_non_root_user: Tests that require a non-root user to be executed.",
    )


@pytest.hookimpl(tryfirst=True)  # the limit applies to the collection, before any sharding
def pytest_collection_modifyitems(items: list[pytest.Function], config: pytest.Config) -> None:
    items[:] = items[0 : config.getoption("--limit")]
    if config.getoption("--no-skip"):
        for item in items:
            item.own_markers = [_ for _ in item.own_markers if _.name not in ("skip", "skipif")]


@pytest.hookimpl  # plain, like pytest's runner: anything later would run the fixtures first
def pytest_runtest_setup(item: pytest.Item) -> None:
    if item.config.getoption("--dry-run"):
        pytest.xfail("*** DRY-RUN ***")

    if item.get_closest_marker("skip_if_medium_chain") and item.config.getoption("--medium-chain"):
        pytest.skip(f"{item.nodeid}: Not reachable in the gated medium chain!")
