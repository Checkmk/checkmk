#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.lib.robotmk_parse_xml import (
    extract_tests_with_full_names,
    Outcome,
    Status,
    Suite,
    Test,
)


class StatusFactory(ModelFactory[Status]):
    __model__ = Status


class SuiteFactory(ModelFactory):
    __model__ = Suite


status_mock = StatusFactory.build(
    factory_use_construct=True,
    status=Outcome.PASS,
    starttime=datetime(1998, 9, 30, 0, 27, 40),
    endtime=datetime(1994, 3, 22, 15, 57, 14),
)


class TestFactory(ModelFactory):
    __model__ = Test

    status = status_mock


def _assert_all_tests(result: dict[str, Test], expected: dict[str, Test]) -> None:
    for test_name, test in result.items():
        assert test_name in expected
        assert test.name == expected[test_name].name
        assert test.status == expected[test_name].status
        assert test.line == expected[test_name].line


def test_empty_suite() -> None:
    empty_suite = SuiteFactory.build(
        factory_use_construct=True, name="EmptySuite", test=[], suite=[]
    )
    result = extract_tests_with_full_names(empty_suite)
    assert result == {}


def test_single_test() -> None:
    single_test_suite = SuiteFactory.build(
        factory_use_construct=True,
        name="SingleTestSuite",
        test=[TestFactory.build(factory_use_construct=True, name="Test1", line=5)],
        suite=[],
    )
    result = extract_tests_with_full_names(single_test_suite)
    expected = {
        "SingleTestSuite-Test1": TestFactory.build(factory_use_construct=True, name="Test1", line=5)
    }
    _assert_all_tests(result, expected)


def test_multiple_tests() -> None:
    multiple_tests_suite = SuiteFactory.build(
        factory_use_construct=True,
        name="MultipleTestsSuite",
        test=[
            TestFactory.build(factory_use_construct=True, name="Test1", line=5),
            TestFactory.build(factory_use_construct=True, name="Test2", line=5),
        ],
        suite=[],
    )
    result = extract_tests_with_full_names(multiple_tests_suite)
    expected = {
        "MultipleTestsSuite-Test1": TestFactory.build(
            factory_use_construct=True, name="Test1", line=5
        ),
        "MultipleTestsSuite-Test2": TestFactory.build(
            factory_use_construct=True, name="Test2", line=5
        ),
    }

    _assert_all_tests(result, expected)


def test_nested_suites() -> None:
    nested_suites = SuiteFactory.build(
        factory_use_construct=True,
        name="TopSuite",
        test=[TestFactory.build(factory_use_construct=True, name="Test4", line=42)],
        suite=[
            SuiteFactory.build(
                factory_use_construct=True,
                name="SubSuite1",
                test=[TestFactory.build(factory_use_construct=True, name="Test1", line=6)],
                suite=[
                    SuiteFactory.build(
                        factory_use_construct=True,
                        name="SubSubSuite",
                        test=[TestFactory.build(factory_use_construct=True, name="Test2", line=5)],
                        suite=[],
                    )
                ],
            ),
            SuiteFactory.build(
                factory_use_construct=True,
                name="SubSuite2",
                test=[TestFactory.build(factory_use_construct=True, name="Test3", line=221)],
                suite=[],
            ),
        ],
    )
    result = extract_tests_with_full_names(nested_suites)
    expected = {
        "TopSuite-Test4": TestFactory.build(factory_use_construct=True, name="Test4", line=42),
        "TopSuite-SubSuite1-Test1": TestFactory.build(
            factory_use_construct=True, name="Test1", line=6
        ),
        "TopSuite-SubSuite1-SubSubSuite-Test2": TestFactory.build(
            factory_use_construct=True, name="Test2", line=5
        ),
        "TopSuite-SubSuite2-Test3": TestFactory.build(
            factory_use_construct=True, name="Test3", line=221
        ),
    }

    _assert_all_tests(result, expected)
