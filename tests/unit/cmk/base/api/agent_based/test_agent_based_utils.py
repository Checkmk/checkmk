#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Iterable, Sequence

import pytest

# not ideal, but for now access this member.
# TODO: find out if it's ok for the fetcher to have the API as
# a dependency, b/c that is where this function belongs.
from cmk.fetchers._snmpscan import _evaluate_snmp_detection

from cmk.agent_based.v1 import (
    all_of,
    any_of,
    contains,
    endswith,
    exists,
    matches,
    not_contains,
    not_endswith,
    not_exists,
    not_startswith,
    startswith,
)

_SpecCreator = Callable[[str, str], list[list[tuple[str, str, bool]]]]


def _make_oid_getter(return_value: str) -> Callable[[str], str]:
    def getter(_oid: str) -> str:
        return return_value

    return getter


def _test_atomic_relation(
    relation: _SpecCreator, inverse: _SpecCreator, value: str, testcases: Iterable[tuple[str, bool]]
) -> None:
    spec = relation(".1.2.3", value)
    inv_spec = inverse(".1.2.3", value)
    for test, result in testcases:
        assert (
            _evaluate_snmp_detection(detect_spec=spec, oid_value_getter=_make_oid_getter(test))
            is result
        )
        assert (
            _evaluate_snmp_detection(detect_spec=inv_spec, oid_value_getter=_make_oid_getter(test))
            is not result
        )


@pytest.mark.parametrize(
    "value, testcases",
    [
        (
            "foo",
            [
                ("", False),
                ("foo", True),
                ("foobar", True),
                ("foobarfoo", True),
                ("barfoo", True),
                ("barfoobar", True),
                ("fürwahr", False),
            ],
        ),
        (
            "bo?",
            [
                ("boo", False),
                ("bo?nee", True),
                ("hobo?nee", True),
                ("hallobo?", True),
            ],
        ),
    ],
)
def test_contains(value: str, testcases: Sequence[tuple[str, bool]]) -> None:
    _test_atomic_relation(contains, not_contains, value, testcases)


@pytest.mark.parametrize(
    "value, testcases",
    [
        (
            "foo",
            [
                ("", False),
                ("foo", True),
                ("foobar", True),
                ("foobarfoo", True),
                ("barfoo", False),
                ("barfoobar", False),
                ("fürwahr", False),
            ],
        ),
        (
            "bo?",
            [
                ("boo", False),
                ("bo?nee", True),
                ("hobo?nee", False),
                ("hallobo?", False),
            ],
        ),
    ],
)
def test_startswith(value: str, testcases: Sequence[tuple[str, bool]]) -> None:
    _test_atomic_relation(startswith, not_startswith, value, testcases)


@pytest.mark.parametrize(
    "value, testcases",
    [
        (
            "foo",
            [
                ("", False),
                ("foo", True),
                ("foobar", False),
                ("foobarfoo", True),
                ("barfoo", True),
                ("barfoobar", False),
                ("fürwahr", False),
            ],
        ),
        (
            "bo?",
            [
                ("boo", False),
                ("bo?nee", False),
                ("hobo?nee", False),
                ("hallobo?", True),
            ],
        ),
    ],
)
def test_endswith(value: str, testcases: Sequence[tuple[str, bool]]) -> None:
    _test_atomic_relation(endswith, not_endswith, value, testcases)


@pytest.mark.parametrize(
    "test, result",
    [
        ("", True),
        ("foo", True),
        ("foobar", True),
        ("foobarfoo", True),
        ("barfoo", True),
        ("barfoobar", True),
        ("fürwahr", True),
    ],
)
def test_exists(test: str, result: bool) -> None:
    assert (
        _evaluate_snmp_detection(
            detect_spec=exists(".1.2.3"), oid_value_getter=_make_oid_getter(test)
        )
        is result
    )
    assert (
        _evaluate_snmp_detection(
            detect_spec=not_exists(".1.2.3"), oid_value_getter=_make_oid_getter(test)
        )
        is not result
    )


def test_all_of_associative() -> None:
    spec1 = matches(".1", "1?")
    spec2 = matches(".2", "2?")
    spec3 = matches(".3", "3?")

    assert all_of(spec1, spec2, spec3) == all_of(all_of(spec1, spec2), spec3)


def test_any_of_assotiative() -> None:
    spec1 = matches(".1", "1?")
    spec2 = matches(".2", "2?")
    spec3 = matches(".3", "3?")

    assert any_of(spec1, spec2, spec3) == any_of(any_of(spec1, spec2), spec3)


def test_any_of_all_of_distibutive() -> None:
    spec1 = matches(".1", "1?")
    spec2 = matches(".2", "2?")
    spec3 = matches(".3", "3?")
    spec4 = matches(".4", "4?")

    assert all_of(
        any_of(spec1, spec2),
        any_of(spec3, spec4),
    ) == any_of(
        all_of(spec1, spec3),
        all_of(spec1, spec4),
        all_of(spec2, spec3),
        all_of(spec2, spec4),
    )
