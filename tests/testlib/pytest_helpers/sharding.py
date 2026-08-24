#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Split a test session over several shards.

Each shard runs the same collection, computes the full assignment, and keeps
only its own slice. Every shard therefore has to reach the same result, which is
why the input is one pinned Jenkins build (a finished test report never changes)
and why the assignment below has no randomness and no dependency on collection
order.

Splitting happens per module, never inside one, because tests in a module share
module scoped fixtures and the order in which they change the site.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import NamedTuple, Protocol, TypedDict

import requests
from cmk_dev.jenkins_utils import AugmentedJenkinsClient, extract_credentials

REPORT_TREE = "suites[cases[className,duration]]"
FETCH_TIMEOUT_SECONDS = 120

#: Credentials come from the environment, so a test pod needs no ini file. The
#: keys are what extract_credentials() expects, "_env" means "read this variable".
JENKINS_CREDENTIALS_ENV = {
    "url_env": "JENKINS_URL",
    "username_env": "JENKINS_USERNAME",
    "password_env": "JENKINS_PASSWORD",
}


def jenkins_client(timeout: int = FETCH_TIMEOUT_SECONDS) -> AugmentedJenkinsClient:
    """Client for the CI, credentials taken from the environment."""
    return AugmentedJenkinsClient(**extract_credentials(JENKINS_CREDENTIALS_ENV), timeout=timeout)


class JenkinsTestCase(TypedDict, total=False):
    className: str
    duration: float | None


class JenkinsTestSuite(TypedDict, total=False):
    cases: list[JenkinsTestCase]


class JenkinsTestReport(TypedDict, total=False):
    suites: list[JenkinsTestSuite]


class Shardable(Protocol):
    """The bit of pytest.Item this module needs, kept narrow for testability."""

    @property
    def nodeid(self) -> str: ...


class Durations(NamedTuple):
    """Recorded runtime per module, plus what it took to get there."""

    per_module: dict[str, float]
    test_count: int

    @property
    def mean_per_test(self) -> float:
        """Estimate for a test we have never seen, e.g. one this change adds."""
        if not self.test_count:
            return 1.0
        return sum(sorted(self.per_module.values())) / self.test_count


def module_of(nodeid: str) -> str:
    """'tests/system/singlesite/omd/test_omd.py::test_x[1]' -> the file part."""
    return nodeid.split("::", 1)[0]


def module_from_class_name(class_name: str) -> str | None:
    """'pytest.tests.system.singlesite.omd.test_omd.TestX' -> the file path.

    Most of these tests are plain functions, some sit in a class, so walk back to
    the last "test_" part to land on the module either way.
    """
    parts = class_name.removeprefix("pytest.").split(".")
    while parts and not parts[-1].startswith("test_"):
        parts.pop()
    return "/".join(parts) + ".py" if parts else None


def durations_from_report(report: JenkinsTestReport) -> Durations:
    """Add up the case durations of a Jenkins test report per module."""
    per_module: dict[str, float] = {}
    test_count = 0
    for suite in report.get("suites", []):
        for case in suite.get("cases", []):
            module = module_from_class_name(case.get("className", ""))
            if module is None:
                continue
            per_module[module] = per_module.get(module, 0.0) + (case.get("duration") or 0.0)
            test_count += 1
    return Durations(dict(sorted(per_module.items())), test_count)


def parse_reference(reference: str) -> tuple[str, int]:
    """'checkmk/master/heavy/test-system-singlesite-ultimatemt#200' -> (job, number).

    The full job path, not a name below a fixed root: the same reference then
    works from the Testing folder and from any branch.
    """
    job, separator, number = reference.rpartition("#")
    if not separator or not number.isdigit() or not job:
        raise ValueError(f"Not a '<job>#<number>' reference: {reference!r}")
    return job, int(number)


def fetch_durations(reference: str, timeout: int = FETCH_TIMEOUT_SECONDS) -> Durations:
    """Read the per module runtimes of one finished build off the Jenkins API.

    The client retries on its own, which matters because there is no fallback:
    a shard that fails loudly beats one running a split none of its siblings
    are running. Raises RuntimeError if it cannot get a usable report.
    """
    job, number = parse_reference(reference)
    job_path = "/".join(f"job/{part}" for part in job.split("/"))
    try:
        with jenkins_client(timeout) as jenkins:
            # No typed wrapper for testReport in jenkins_utils, and python-jenkins
            # itself is untyped, hence the ignores rather than a hand-rolled request.
            url = jenkins.client._build_url(  # type: ignore[no-untyped-call, unused-ignore]
                f"/{job_path}/{number}/testReport/api/json?tree={REPORT_TREE}"
            )
            response = jenkins.client.jenkins_request(  # type: ignore[no-untyped-call, unused-ignore]
                requests.Request("GET", url)
            )
            response.raise_for_status()
            report: JenkinsTestReport = response.json()
    except Exception as exc:
        raise RuntimeError(f"Could not read shard durations from {reference}: {exc}") from exc

    durations = durations_from_report(report)
    if not durations.per_module:
        raise RuntimeError(f"No test cases in the report of {reference}")
    return durations


def estimate(modules: dict[str, int], durations: Durations) -> dict[str, float]:
    """Seconds to expect per module, for the modules actually collected.

    A module the reference build did not have, typically a test file this change
    adds, is estimated from its own test count times the mean runtime per test.
    """
    # Bound once: dict.get evaluates its default on every lookup, hit or miss.
    mean_per_test = durations.mean_per_test
    return {
        module: durations.per_module.get(module, test_count * mean_per_test)
        for module, test_count in modules.items()
    }


def assign_modules(
    modules: dict[str, int], shard_count: int, durations: Durations
) -> dict[str, int]:
    """Map every module to a shard index in [0, shard_count-1].

    Longest module first onto the shard with the least work so far, which is the
    standard greedy approximation and lands within a few percent of optimal on
    our data. Ties break by module path, so the result never depends on the order
    the modules were collected in.
    """
    if shard_count < 1:
        raise ValueError(f"shard_count must be >= 1, got {shard_count}")

    seconds = estimate(modules, durations)
    ordered = sorted(seconds, key=lambda module: (-seconds[module], module))

    load = [0.0] * shard_count
    assignment: dict[str, int] = {}
    for module in ordered:
        target = min(range(shard_count), key=lambda index: (load[index], index))
        assignment[module] = target
        load[target] += seconds[module]
    return assignment


def module_test_counts(items: Iterable[Shardable]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        module = module_of(item.nodeid)
        counts[module] = counts.get(module, 0) + 1
    return counts


def select_for_shard[T: Shardable](
    items: Sequence[T], shard_index: int, shard_count: int, durations: Durations
) -> tuple[list[T], list[T]]:
    """Split collected items into (selected, deselected) for this shard."""
    if not 0 <= shard_index < shard_count:
        raise ValueError(f"shard_index {shard_index} out of range for {shard_count} shards")

    assignment = assign_modules(module_test_counts(items), shard_count, durations)
    selected = [item for item in items if assignment[module_of(item.nodeid)] == shard_index]
    deselected = [item for item in items if assignment[module_of(item.nodeid)] != shard_index]
    return selected, deselected


class ShardPlan(NamedTuple):
    """What every shard will run, for logging and for sizing the shard count."""

    modules: list[int]
    tests: list[int]
    seconds: list[float]
    #: Runtime of the heaviest single module. Since modules are never split, no
    #: shard count can get the test time below this, more shards only add pods.
    floor: float

    @property
    def makespan(self) -> float:
        """Expected test time of the split, i.e. the busiest shard."""
        return max(self.seconds) if self.seconds else 0.0


def plan(items: Sequence[Shardable], shard_count: int, durations: Durations) -> ShardPlan:
    """Per shard totals, plus the floor more shards can never get below."""
    counts = module_test_counts(items)
    seconds_per_module = estimate(counts, durations)
    assignment = assign_modules(counts, shard_count, durations)

    modules = [0] * shard_count
    tests = [0] * shard_count
    seconds = [0.0] * shard_count
    for module, shard in assignment.items():
        modules[shard] += 1
        tests[shard] += counts[module]
        seconds[shard] += seconds_per_module[module]

    floor = max(seconds_per_module.values()) if seconds_per_module else 0.0
    return ShardPlan(modules, tests, seconds, floor)
