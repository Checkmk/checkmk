#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.lib.robotmk_parse_xml import (
    extract_tests_with_full_names,
    Outcome,
    StatusV6,
    Suite,
    Test,
)


class StatusV6Factory(ModelFactory[StatusV6]):
    __model__ = StatusV6


class SuiteFactory(ModelFactory[Suite]):
    __model__ = Suite

    status = StatusV6Factory.build(
        factory_use_construct=True,
        status=Outcome.PASS,
        starttime=datetime(2023, 11, 14, 13, 27, 40),
        endtime=datetime(2023, 11, 14, 13, 45, 56),
    )


class TestFactory(ModelFactory[Test]):
    __model__ = Test

    status = StatusV6Factory.build(
        factory_use_construct=True,
        status=Outcome.PASS,
        starttime=datetime(2023, 11, 14, 13, 29, 33),
        endtime=datetime(2023, 11, 14, 13, 31, 34),
    )


def test_empty_suite() -> None:
    assert not extract_tests_with_full_names(
        SuiteFactory.build(factory_use_construct=True, name="EmptySuite", test=[], suite=[])
    )


def test_single_test() -> None:
    single_test_suite = SuiteFactory.build(
        factory_use_construct=True,
        name="SingleTestSuite",
        test=[TestFactory.build(factory_use_construct=True, name="Test1")],
        suite=[],
    )
    assert extract_tests_with_full_names(single_test_suite) == {
        "SingleTestSuite-Test1": TestFactory.build(factory_use_construct=True, name="Test1")
    }


def test_multiple_tests() -> None:
    multiple_tests_suite = SuiteFactory.build(
        factory_use_construct=True,
        name="MultipleTestsSuite",
        test=[
            TestFactory.build(factory_use_construct=True, name="Test1"),
            TestFactory.build(factory_use_construct=True, name="Test2"),
        ],
        suite=[],
    )
    assert extract_tests_with_full_names(multiple_tests_suite) == {
        "MultipleTestsSuite-Test1": TestFactory.build(factory_use_construct=True, name="Test1"),
        "MultipleTestsSuite-Test2": TestFactory.build(factory_use_construct=True, name="Test2"),
    }


def test_nested_suites() -> None:
    nested_suites = SuiteFactory.build(
        factory_use_construct=True,
        name="TopSuite",
        test=[TestFactory.build(factory_use_construct=True, name="Test4")],
        suite=[
            SuiteFactory.build(
                factory_use_construct=True,
                name="SubSuite1",
                test=[TestFactory.build(factory_use_construct=True, name="Test1")],
                suite=[
                    SuiteFactory.build(
                        factory_use_construct=True,
                        name="SubSubSuite",
                        test=[TestFactory.build(factory_use_construct=True, name="Test2")],
                        suite=[],
                    )
                ],
            ),
            SuiteFactory.build(
                factory_use_construct=True,
                name="SubSuite2",
                test=[TestFactory.build(factory_use_construct=True, name="Test3")],
                suite=[],
            ),
        ],
    )
    assert extract_tests_with_full_names(nested_suites) == {
        "TopSuite-Test4": TestFactory.build(factory_use_construct=True, name="Test4"),
        "TopSuite-SubSuite1-Test1": TestFactory.build(factory_use_construct=True, name="Test1"),
        "TopSuite-SubSuite1-SubSubSuite-Test2": TestFactory.build(
            factory_use_construct=True, name="Test2"
        ),
        "TopSuite-SubSuite2-Test3": TestFactory.build(factory_use_construct=True, name="Test3"),
    }
