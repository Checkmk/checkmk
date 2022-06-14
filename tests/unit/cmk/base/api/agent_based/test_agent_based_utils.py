#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

import pytest

import cmk.base.api.agent_based.utils as utils
from cmk.base.api.agent_based.register.section_plugins import _validate_detect_spec
from cmk.base.api.agent_based.section_classes import SNMPDetectSpecification


def _test_atomic_relation(relation_name, value, testcases):
    spec = getattr(utils, relation_name)(".1.2.3", value)
    _validate_detect_spec(spec)
    assert len(spec) == 1
    assert len(spec[0]) == 1
    expr = spec[0][0][1]

    inv_spec = getattr(utils, "not_%s" % relation_name)(".1.2.3", value)
    _validate_detect_spec(inv_spec)
    assert len(inv_spec) == 1
    assert len(inv_spec[0]) == 1
    assert inv_spec[0][0] == (spec[0][0][0], spec[0][0][1], not spec[0][0][2])

    for test, result in testcases:
        assert result is bool(re.fullmatch(expr, test))


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
def test_contains(value, testcases) -> None:
    _test_atomic_relation("contains", value, testcases)


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
def test_startswith(value, testcases) -> None:
    _test_atomic_relation("startswith", value, testcases)


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
def test_endswith(value, testcases) -> None:
    _test_atomic_relation("endswith", value, testcases)


@pytest.mark.parametrize(
    "testcases",
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
def test_exists(testcases) -> None:
    spec = utils.exists(".1.2.3")
    _validate_detect_spec(spec)
    assert len(spec) == 1
    assert len(spec[0]) == 1
    expr = spec[0][0][1]
    test, result = testcases
    assert result is bool(re.match(expr, test))


def test_all_of() -> None:

    spec1 = SNMPDetectSpecification([[(".1", "1?", True)]])
    spec2 = SNMPDetectSpecification([[(".2", "2?", True)]])
    spec3 = SNMPDetectSpecification([[(".3", "3?", True)]])

    assert utils.all_of(spec1, spec2, spec3) == SNMPDetectSpecification(
        [
            [
                (".1", "1?", True),
                (".2", "2?", True),
                (".3", "3?", True),
            ]
        ]
    )

    spec12 = utils.all_of(spec1, spec2)
    assert utils.all_of(spec1, spec2, spec3) == utils.all_of(spec12, spec3)


def test_any_of() -> None:

    spec1 = SNMPDetectSpecification([[(".1", "1?", True)]])
    spec2 = SNMPDetectSpecification([[(".2", "2?", True)]])
    spec3 = SNMPDetectSpecification([[(".3", "3?", True)]])

    spec123 = utils.any_of(spec1, spec2, spec3)

    _validate_detect_spec(spec123)
    assert spec123 == [
        [(".1", "1?", True)],
        [(".2", "2?", True)],
        [(".3", "3?", True)],
    ]

    spec12 = utils.any_of(spec1, spec2)

    assert spec123 == utils.any_of(spec12, spec3)


def test_any_of_all_of() -> None:

    spec1 = SNMPDetectSpecification([[(".1", "1?", True)]])
    spec2 = SNMPDetectSpecification([[(".2", "2?", True)]])
    spec3 = SNMPDetectSpecification([[(".3", "3?", True)]])
    spec4 = SNMPDetectSpecification([[(".4", "4?", True)]])

    spec12 = utils.all_of(spec1, spec2)
    spec34 = utils.all_of(spec3, spec4)

    _validate_detect_spec(spec12)
    _validate_detect_spec(spec34)

    spec1234 = utils.any_of(spec12, spec34)
    _validate_detect_spec(spec1234)

    assert spec1234 == SNMPDetectSpecification(
        [
            [(".1", "1?", True), (".2", "2?", True)],
            [(".3", "3?", True), (".4", "4?", True)],
        ]
    )


def test_all_of_any_of() -> None:

    spec1 = SNMPDetectSpecification([[(".1", "1?", True)]])
    spec2 = SNMPDetectSpecification([[(".2", "2?", True)]])
    spec3 = SNMPDetectSpecification([[(".3", "3?", True)]])
    spec4 = SNMPDetectSpecification([[(".4", "4?", True)]])

    spec12 = utils.any_of(spec1, spec2)
    spec34 = utils.any_of(spec3, spec4)

    assert utils.all_of(spec12, spec34) == SNMPDetectSpecification(
        [
            [(".1", "1?", True), (".3", "3?", True)],
            [(".1", "1?", True), (".4", "4?", True)],
            [(".2", "2?", True), (".3", "3?", True)],
            [(".2", "2?", True), (".4", "4?", True)],
        ]
    )
