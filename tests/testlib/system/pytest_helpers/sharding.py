#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Apply a shard plan to a pytest session.

Registered by tests/system/conftest.py: adds the `--shard-*` options and
deselects everything outside this shard. The planning itself, which the CI stage
also runs without pytest, lives in tests.testlib.system.shard_planning.
"""

import logging
import os

import pytest

from tests.testlib.system.shard_planning import (
    Durations,
    fetch_durations,
    plan,
    select_for_shard,
)

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--shard-index",
        action="store",
        default=None,
        type=int,
        help="Run only the tests of this shard, counting from 0. Needs --shard-count.",
    )
    parser.addoption(
        "--shard-count",
        action="store",
        default=None,
        type=int,
        help="Number of shards the suite is split into. Needs --shard-index.",
    )
    parser.addoption(
        "--shard-durations-build",
        action="store",
        default=os.environ.get("SHARD_BUILD_BASED_ON"),
        type=str,
        help=(
            "Finished build to take the balancing runtimes from, as '<job>#<number>' "
            "with the full job path, e.g. "
            "'checkmk/master/heavy/test-system-singlesite-ultimatemt#1234'. Defaults to "
            "the SHARD_BUILD_BASED_ON environment variable, which is how the job "
            "parameter of that name reaches pytest."
        ),
    )


@pytest.hookimpl(trylast=True)  # sharding applies to whatever the other plugins left over
def pytest_collection_modifyitems(items: list[pytest.Function], config: pytest.Config) -> None:
    """Keep only the items belonging to this shard, if sharding is requested."""
    shard_index = config.getoption("--shard-index")
    shard_count = config.getoption("--shard-count")
    # An empty SHARD_BUILD_BASED_ON counts as unset, not as a value.
    shard_durations_build = config.getoption("--shard-durations-build") or None
    if all(v is None for v in [shard_index, shard_count, shard_durations_build]):
        return
    if any(v is None for v in [shard_index, shard_count, shard_durations_build]):
        raise pytest.UsageError(
            "--shard-index, --shard-count and --shard-durations-build must be given together"
        )
    if not items:
        return

    durations = _shard_durations(config)
    shard_plan = plan(items, shard_count, durations)
    for index in range(shard_count):
        logger.info(
            "shard %d/%d: %d modules, %d tests, ~%.1f min%s",
            index,
            shard_count,
            shard_plan.modules[index],
            shard_plan.tests[index],
            shard_plan.seconds[index] / 60,
            " <-- this shard" if index == shard_index else "",
        )
    logger.info(
        "expected test time %.1f min, heaviest module %.1f min",
        shard_plan.makespan / 60,
        shard_plan.floor / 60,
    )
    if shard_count > 1 and shard_plan.makespan <= shard_plan.floor:
        logger.warning(
            "The split is down to its heaviest module, more than %d shards would "
            "only add pods without getting faster.",
            shard_count,
        )

    selected, deselected = select_for_shard(items, shard_index, shard_count, durations)
    config.hook.pytest_deselected(items=deselected)
    items[:] = list(selected)


def _shard_durations(config: pytest.Config) -> Durations:
    """Runtimes used for balancing. Fails rather than guessing.

    No fallback and no default on purpose: a shard balancing against something
    its siblings do not have splits the suite differently, and the tests between
    the two splits are not reported as skipped, they simply never run.
    """
    if not (reference := config.getoption("--shard-durations-build")):
        raise pytest.UsageError("Sharding needs --shard-durations-build")

    try:
        durations = fetch_durations(reference)
    except (RuntimeError, ValueError) as exc:
        raise pytest.UsageError(str(exc)) from exc
    logger.info("Shard durations: %d modules from %s", len(durations.per_module), reference)
    return durations
