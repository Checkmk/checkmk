#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for :mod:`tests.testlib.system.shard_planning`.

A wrong split does not fail loudly, it silently stops running tests, so the
properties that matter are covered here: every test in exactly one shard, whole
modules only, and the same result no matter which shard computes it.
"""

import random
from typing import override

import pytest

from tests.testlib.system.shard_planning import (
    assign_modules,
    Durations,
    durations_from_report,
    estimate,
    JenkinsTestReport,
    module_from_class_name,
    module_of,
    nodeid_from_case,
    parse_reference,
    plan,
    select_for_shard,
)


class Item:
    """Stand-in for pytest.Function, which only needs a nodeid here."""

    def __init__(self, nodeid: str) -> None:
        # https://docs.pytest.org/en/stable/reference/reference.html#pytest.nodes.Node.nodeid
        # e.g. "tests/fake/slowest/test_slowest.py::test_start"
        self.nodeid = nodeid

    @override
    def __repr__(self) -> str:
        return f"Item({self.nodeid})"


def _items(spec: dict[str, int]) -> list[Item]:
    return [
        Item(f"{module}::test_{index}") for module, count in spec.items() for index in range(count)
    ]


# Fictional stuff to make sure noone thinks this is real config
SUITE = {
    "tests/fake/slowest/test_slowest.py": 40,
    "tests/fake/heavy/test_heavy.py": 4,
    "tests/fake/medium/test_medium.py": 6,
    "tests/fake/light/test_light.py": 12,
    "tests/fake/quick/test_many_quick.py": 300,
    "tests/fake/unmeasured/test_unmeasured.py": 30,
}
# test_unmeasured.py is deliberately missing, it has to be estimated
DURATIONS = Durations(
    per_module={
        "tests/fake/slowest/test_slowest.py": 436.0,
        "tests/fake/heavy/test_heavy.py": 371.0,
        "tests/fake/medium/test_medium.py": 177.0,
        "tests/fake/light/test_light.py": 106.0,
        "tests/fake/quick/test_many_quick.py": 30.0,
    },
    # Only test_heavy.py gets per-test granularity here, to cover both lookup
    # paths: a module with partial per-test data (marker-filter scenario) and
    # one estimated purely from its per_module total (test_slowest.py etc.).
    # test_0 carries most of the module's weight, mirroring a real module-scoped
    # fixture: pytest ran it first, and its JUnit duration bundles that fixture's
    # setup cost together with its own (comparatively small) test time.
    per_test={
        "tests/fake/heavy/test_heavy.py::test_0": 300.0,
        "tests/fake/heavy/test_heavy.py::test_1": 50.0,
        "tests/fake/heavy/test_heavy.py::test_2": 15.0,
        "tests/fake/heavy/test_heavy.py::test_3": 6.0,
    },
    pivot_test={"tests/fake/heavy/test_heavy.py": "tests/fake/heavy/test_heavy.py::test_0"},
    test_count=362,
)


def test_module_of_strips_the_test_and_parameters() -> None:
    assert module_of("tests/fake/slowest/test_slowest.py::test_x[a-b]") == (
        "tests/fake/slowest/test_slowest.py"
    )


@pytest.mark.parametrize("shard_count", [1, 2, 3, 6, 12])
def test_every_test_runs_exactly_once(shard_count: int) -> None:
    items = _items(SUITE)
    seen: list[str] = []
    for shard_index in range(shard_count):
        selected, deselected = select_for_shard(items, shard_index, shard_count, DURATIONS)
        assert len(selected) + len(deselected) == len(items)
        seen += [item.nodeid for item in selected]
    assert sorted(seen) == sorted(item.nodeid for item in items)


@pytest.mark.parametrize("shard_count", [2, 6])
def test_a_module_is_never_split(shard_count: int) -> None:
    assignment = assign_modules(_items(SUITE), shard_count, DURATIONS)
    for shard_index in range(shard_count):
        selected, _ = select_for_shard(_items(SUITE), shard_index, shard_count, DURATIONS)
        for item in selected:
            assert assignment[module_of(item.nodeid)] == shard_index


def test_collection_order_does_not_change_the_split() -> None:
    items = _items(SUITE)
    shuffled = items[:]
    random.Random(4).shuffle(shuffled)

    reference, _ = select_for_shard(items, 3, 6, DURATIONS)
    other, _ = select_for_shard(shuffled, 3, 6, DURATIONS)
    assert sorted(item.nodeid for item in reference) == sorted(item.nodeid for item in other)


def test_order_within_a_module_is_preserved() -> None:
    items = _items(SUITE)
    for shard_index in range(6):
        selected, _ = select_for_shard(items, shard_index, 6, DURATIONS)
        assert selected == [item for item in items if item in selected]


def test_unknown_module_is_estimated_from_its_test_count() -> None:
    """A test file this change adds has no recorded runtime, so it is priced at
    its own number of tests times the mean runtime per test."""
    seconds = estimate(_items(SUITE), DURATIONS)
    mean_per_test = sum(DURATIONS.per_module.values()) / DURATIONS.test_count
    assert seconds["tests/fake/unmeasured/test_unmeasured.py"] == 30 * mean_per_test
    # a module we do know keeps its recorded value, same as before per-test data existed
    assert seconds["tests/fake/slowest/test_slowest.py"] == 436.0


def test_estimating_without_any_recorded_runtimes_does_not_divide_by_zero() -> None:
    seconds = estimate(
        _items({"a/test_x.py": 3}),
        Durations(per_module={}, per_test={}, pivot_test={}, test_count=0),
    )
    assert seconds == {"a/test_x.py": 3.0}


def test_a_marker_filtered_module_is_priced_for_only_its_selected_tests() -> None:
    """The scenario per-test data exists for: a marker leaves only some of a
    module's tests selected. Pricing it at the whole file's historical total
    (371.0, all four tests) would overcharge the shard it lands on; selecting
    just the pivot test (which already carries the fixture cost, see below)
    must be priced at that test's own recorded duration, nothing more."""
    selected = [Item("tests/fake/heavy/test_heavy.py::test_0")]
    seconds = estimate(selected, DURATIONS)
    assert seconds["tests/fake/heavy/test_heavy.py"] == 300.0


def test_a_marker_filtered_module_without_the_pivot_still_charges_its_fixture_cost() -> None:
    """The bug this guards against: selecting test_1 and test_2 but not the
    pivot test_0 must not drop test_0's bundled fixture-setup cost just because
    no selected test happens to be the one the reference run charged it to. A
    fresh session only running test_1 and test_2 still pays that setup once,
    so the naive sum of the two selected tests' own durations (50.0 + 15.0 =
    65.0) would understate the module by exactly the pivot's 300.0 - the
    opposite failure from overcharging a marker-filtered module at its whole
    historical total."""
    selected = [
        Item("tests/fake/heavy/test_heavy.py::test_1"),
        Item("tests/fake/heavy/test_heavy.py::test_2"),
    ]
    seconds = estimate(selected, DURATIONS)
    assert seconds["tests/fake/heavy/test_heavy.py"] == 50.0 + 15.0 + 300.0


def test_a_marker_filtered_modules_unknown_test_falls_back_to_the_mean() -> None:
    """A selected test with no recorded duration at all - not even in
    per_test - is estimated at the mean, same as a brand new module is."""
    selected = [
        Item("tests/fake/heavy/test_heavy.py::test_0"),
        Item("tests/fake/heavy/test_heavy.py::test_new_one"),
    ]
    seconds = estimate(selected, DURATIONS)
    mean_per_test = sum(DURATIONS.per_module.values()) / DURATIONS.test_count
    # test_0 is this module's pivot and is already selected, so no top-up applies.
    assert seconds["tests/fake/heavy/test_heavy.py"] == 300.0 + mean_per_test


def test_a_marker_filtered_module_with_no_known_pivot_just_sums_the_selection() -> None:
    """Historical data built without pivot tracking (pivot_test missing the
    module entirely) degrades gracefully to the plain per-test sum, rather
    than erroring or guessing at a fixture cost it has no data for."""
    no_pivot_data = DURATIONS._replace(pivot_test={})
    selected = [Item("tests/fake/heavy/test_heavy.py::test_1")]
    seconds = estimate(selected, no_pivot_data)
    assert seconds["tests/fake/heavy/test_heavy.py"] == 50.0


def test_running_the_whole_module_ignores_per_test_data() -> None:
    """Selecting as many of a module's tests as the reference build recorded
    is "the whole module" even if collection order differs from the historical
    run - it is priced at the reliable per_module total, not a per-test sum
    that would depend on every nodeid having matched back up correctly."""
    all_four = [Item(f"tests/fake/heavy/test_heavy.py::test_{i}") for i in range(4)]
    seconds = estimate(all_four, DURATIONS)
    assert seconds["tests/fake/heavy/test_heavy.py"] == 371.0


def test_balancing_keeps_shards_within_a_reasonable_spread() -> None:
    shard_plan = plan(_items(SUITE), 3, DURATIONS)
    assert min(shard_plan.seconds) > 0, "no shard may end up empty for this suite"
    assert shard_plan.makespan <= max(DURATIONS.per_module.values()) * 1.2


def test_plan_reports_the_floor_more_shards_cannot_beat() -> None:
    # Modules are never split, so the heaviest one bounds every shard count.
    shard_plan = plan(_items(SUITE), 12, DURATIONS)
    assert shard_plan.floor == max(DURATIONS.per_module.values())
    assert shard_plan.makespan >= shard_plan.floor


def test_more_shards_than_modules_leaves_empty_shards() -> None:
    # Not an error, it just wastes a pod. The job should not crash on it.
    assignment = assign_modules(_items(SUITE), 20, DURATIONS)
    assert sorted(assignment.values()) == sorted(range(len(SUITE)))


@pytest.mark.parametrize(
    "shard_index, shard_count", [(-1, 6), (6, 6), (0, 0)], ids=["negative", "too_high", "zero"]
)
def test_invalid_shard_arguments_raise(shard_index: int, shard_count: int) -> None:
    with pytest.raises(ValueError):
        select_for_shard(_items(SUITE), shard_index, shard_count, DURATIONS)


@pytest.mark.parametrize(
    "class_name, expected",
    [
        ("pytest.tests.fake.slowest.test_slowest", "tests/fake/slowest/test_slowest.py"),
        (
            "pytest.tests.fake.slowest.test_slowest.TestSomething",
            "tests/fake/slowest/test_slowest.py",
        ),
        ("pytest.tests.fake.slowest", None),
    ],
    ids=["plain_module", "class_in_module", "no_module"],
)
def test_module_from_class_name(class_name: str, expected: str | None) -> None:
    assert module_from_class_name(class_name) == expected


def test_durations_from_report_sums_cases_per_module_and_per_test() -> None:
    report: JenkinsTestReport = {
        "suites": [
            {
                "cases": [
                    {"className": "pytest.tests.a.test_x", "name": "test_one", "duration": 1.5},
                    {
                        "className": "pytest.tests.a.test_x.TestY",
                        "name": "test_two[a]",
                        "duration": 2.0,
                    },
                    {"className": "pytest.tests.a.test_z", "name": "test_three", "duration": None},
                ]
            }
        ]
    }
    durations = durations_from_report(report)
    assert durations.per_module == {"tests/a/test_x.py": 3.5, "tests/a/test_z.py": 0.0}
    assert durations.per_test == {
        "tests/a/test_x.py::test_one": 1.5,
        "tests/a/test_x.py::TestY::test_two[a]": 2.0,
        "tests/a/test_z.py::test_three": 0.0,
    }
    # The first case the report lists for each module, not the alphabetically
    # first nodeid - test_x.py's first case here is test_one, even though
    # TestY::test_two[a] sorts before it in per_test above.
    assert durations.pivot_test == {
        "tests/a/test_x.py": "tests/a/test_x.py::test_one",
        "tests/a/test_z.py": "tests/a/test_z.py::test_three",
    }
    assert durations.test_count == 3


def test_durations_from_report_pivot_is_the_first_case_seen_not_the_cheapest() -> None:
    """Cases for one module can arrive interleaved with another's; the pivot is
    whichever came first in report order for its own module, regardless of its
    position in the overall report or its duration relative to later cases."""
    report: JenkinsTestReport = {
        "suites": [
            {
                "cases": [
                    {"className": "pytest.tests.a.test_x", "name": "test_cheap", "duration": 0.1},
                    {"className": "pytest.tests.b.test_y", "name": "test_other", "duration": 5.0},
                    {
                        "className": "pytest.tests.a.test_x",
                        "name": "test_expensive",
                        "duration": 99.0,
                    },
                ]
            }
        ]
    }
    durations = durations_from_report(report)
    assert durations.pivot_test["tests/a/test_x.py"] == "tests/a/test_x.py::test_cheap"


@pytest.mark.parametrize(
    "class_name, name, expected",
    [
        (
            "pytest.tests.fake.slowest.test_slowest",
            "test_x",
            "tests/fake/slowest/test_slowest.py::test_x",
        ),
        (
            "pytest.tests.fake.slowest.test_slowest.TestSomething",
            "test_y[1]",
            "tests/fake/slowest/test_slowest.py::TestSomething::test_y[1]",
        ),
        ("pytest.tests.fake.slowest", "test_x", None),
        ("pytest.tests.fake.slowest.test_slowest", "", None),
    ],
    ids=["plain_module", "class_and_params", "no_module", "no_name"],
)
def test_nodeid_from_case(class_name: str, name: str, expected: str | None) -> None:
    assert nodeid_from_case(class_name, name) == expected


@pytest.mark.parametrize(
    "reference, expected",
    [
        (
            "checkmk/master/heavy/test-system-singlesite-ultimatemt#200",
            ("checkmk/master/heavy/test-system-singlesite-ultimatemt", 200),
        ),
        ("job#1", ("job", 1)),
    ],
)
def test_parse_reference(reference: str, expected: tuple[str, int]) -> None:
    assert parse_reference(reference) == expected


@pytest.mark.parametrize(
    "reference", ["", "no-number", "job#", "#200", "job#abc"], ids=lambda r: r or "empty"
)
def test_unusable_reference_raises(reference: str) -> None:
    with pytest.raises(ValueError):
        parse_reference(reference)
