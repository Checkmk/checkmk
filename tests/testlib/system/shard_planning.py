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

Keep this module importable without pytest. tests/scripts/resolve_shard_durations.py
reads the durations from here in the "Resolve shard durations" CI stage, which runs
in a container that has no pytest installed. The pytest plugin that applies a plan
to a session lives in pytest_helpers/sharding.py.
"""

import logging
from collections.abc import Iterable, Sequence
from typing import NamedTuple, Protocol, TypedDict

import requests
from cmk_dev.jenkins_utils import AugmentedJenkinsClient, extract_credentials

logger = logging.getLogger(__name__)

REPORT_TREE = "suites[cases[className,name,duration]]"
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
    name: str
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
    """Recorded runtime per module and per test, plus what it took to get there.

    per_module is the whole file's historical total, used to size a run that
    collects everything in it. per_test is the same data at test granularity,
    used to size a run that only collects some of a module's tests (e.g. a
    marker filter) - estimate() sums exactly the selected tests instead of
    charging the whole file's weight for a fraction of its tests.

    pivot_test names, per module, the first test the reference build actually
    ran in it. A JUnit case's duration is setup+call+teardown (pytest's default
    junit_duration_report=total), so a module- or class-scoped fixture's setup
    cost - the site setup in a multisite module, say - is baked into whichever
    test happened to trigger it there, almost always the first one. Summing
    only a subset's own per_test durations silently drops that cost whenever
    the subset excludes the pivot; estimate() uses this field to charge it
    unconditionally instead.
    """

    per_module: dict[str, float]
    per_test: dict[str, float]
    pivot_test: dict[str, str]
    test_count: int

    @property
    def mean_per_test(self) -> float:
        """Estimate for a test we have never seen, e.g. one this change adds."""
        if not self.test_count:
            return 1.0
        return sum(sorted(self.per_module.values())) / self.test_count


def module_of(nodeid: str) -> str:
    """'tests/system/singlesite/site_management/test_omd.py::test_x[1]' -> the file part."""
    return nodeid.split("::", 1)[0]


def _split_class_name(class_name: str) -> tuple[str, str] | tuple[None, None]:
    """'pytest.tests.system.singlesite.site_management.test_omd.TestX' -> module path + class.

    The dotted name does not mark where the module ends and a class begins.
    Test modules are named test_*, classes Test*, so the last part starting
    with "test_" is the module; anything after it is the class.
    """
    parts = class_name.removeprefix("pytest.").split(".")
    tail: list[str] = []
    while parts and not parts[-1].startswith("test_"):
        tail.insert(0, parts.pop())
    if not parts:
        return None, None
    return "/".join(parts) + ".py", "::".join(tail)


def module_from_class_name(class_name: str) -> str | None:
    """'pytest.tests.system.singlesite.site_management.test_omd.TestX' -> the file path."""
    return _split_class_name(class_name)[0]


def nodeid_from_case(class_name: str, name: str) -> str | None:
    """Rebuild the pytest nodeid a Jenkins case was split into className + name.

    'pytest.tests.a.test_x.TestY' + 'test_z[1]' -> 'tests/a/test_x.py::TestY::test_z[1]'.
    None if className does not resolve to a module, same as module_from_class_name.
    """
    module, cls = _split_class_name(class_name)
    if module is None or not name:
        return None
    return f"{module}::{cls}::{name}" if cls else f"{module}::{name}"


def durations_from_report(report: JenkinsTestReport) -> Durations:
    """Add up the case durations of a Jenkins test report, per module and per test.

    Also records, per module, the first test actually executed in it - cases
    arrive in the report in the order pytest ran them, so this is the one that
    paid any module- or class-scoped fixture setup, see Durations.pivot_test.
    """
    per_module: dict[str, float] = {}
    per_test: dict[str, float] = {}
    pivot_test: dict[str, str] = {}
    test_count = 0
    for suite in report.get("suites", []):
        for case in suite.get("cases", []):
            class_name = case.get("className", "")
            module = module_from_class_name(class_name)
            if module is None:
                continue
            duration = case.get("duration") or 0.0
            per_module[module] = per_module.get(module, 0.0) + duration
            nodeid = nodeid_from_case(class_name, case.get("name", ""))
            if nodeid is not None:
                per_test[nodeid] = per_test.get(nodeid, 0.0) + duration
                pivot_test.setdefault(module, nodeid)
            test_count += 1
    return Durations(
        per_module=dict(sorted(per_module.items())),
        per_test=dict(sorted(per_test.items())),
        pivot_test=pivot_test,
        test_count=test_count,
    )


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
            url = jenkins.client._build_url(  # type: ignore[no-untyped-call, unused-ignore]  # noqa: SLF001
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


def estimate(items: Iterable[Shardable], durations: Durations) -> dict[str, float]:
    """Estimate each collected module's runtime from the reference build's durations.

    A module is priced at its recorded total (per_module) when it runs as
    many tests as the reference build did. When a filter such as a marker
    selects fewer tests, it is priced at the sum of the selected tests' own
    durations (per_test) instead.

    A JUnit case's duration includes the setup of module- and class-scoped
    fixtures, and that cost lands on the first test that used them
    (pivot_test). If the selection leaves out the pivot test, its duration
    is added anyway, so the module keeps its fixture cost. This overcharges
    by the pivot's own test time, which is acceptable for balancing.

    A test without recorded duration (new, or not matched to the report) is
    estimated at the mean runtime per test. A module without any recorded
    data (a new file) is estimated as its test count times that mean.
    """
    mean_per_test = durations.mean_per_test
    by_module: dict[str, list[Shardable]] = {}
    for item in items:
        by_module.setdefault(module_of(item.nodeid), []).append(item)

    historical_counts: dict[str, int] = {}
    for nodeid in durations.per_test:
        module = module_of(nodeid)
        historical_counts[module] = historical_counts.get(module, 0) + 1

    seconds: dict[str, float] = {}
    for module, module_items in by_module.items():
        if module not in durations.per_module:
            seconds[module] = len(module_items) * mean_per_test
        elif len(module_items) >= historical_counts.get(module, 0):
            seconds[module] = durations.per_module[module]
        else:
            total = sum(durations.per_test.get(item.nodeid, mean_per_test) for item in module_items)
            pivot = durations.pivot_test.get(module)
            if pivot is not None and pivot not in {item.nodeid for item in module_items}:
                total += durations.per_test.get(pivot, 0.0)
            seconds[module] = total
    return seconds


def assign_modules(
    items: Iterable[Shardable], shard_count: int, durations: Durations
) -> dict[str, int]:
    """Map every module to a shard index in [0, shard_count-1].

    Longest module first onto the shard with the least work so far, which is the
    standard greedy approximation and lands within a few percent of optimal on
    our data. Ties break by module path, so the result never depends on the order
    the modules were collected in.
    """
    if shard_count < 1:
        raise ValueError(f"shard_count must be >= 1, got {shard_count}")

    seconds = estimate(items, durations)
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

    assignment = assign_modules(items, shard_count, durations)
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
    seconds_per_module = estimate(items, durations)
    assignment = assign_modules(items, shard_count, durations)

    modules = [0] * shard_count
    tests = [0] * shard_count
    seconds = [0.0] * shard_count
    for module, shard in assignment.items():
        modules[shard] += 1
        tests[shard] += counts[module]
        seconds[shard] += seconds_per_module[module]

    floor = max(seconds_per_module.values()) if seconds_per_module else 0.0
    return ShardPlan(modules, tests, seconds, floor)
