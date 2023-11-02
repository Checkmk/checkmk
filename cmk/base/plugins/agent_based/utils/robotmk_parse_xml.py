#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Should be replaced by external package


import enum
from datetime import datetime

from pydantic import BaseModel, BeforeValidator, Field, PlainValidator
from typing_extensions import Annotated, TypeVar


def _parse_datetime(value: str) -> datetime:
    date_format = "%Y%m%d %H:%M:%S.%f"
    return datetime.strptime(value, date_format)


DateTimeFormat = Annotated[datetime, PlainValidator(_parse_datetime)]

T = TypeVar("T")


def _make_tests_and_suites_lists(input_value: T | list[T]) -> list[T]:
    return input_value if isinstance(input_value, list) else [input_value]


class Outcome(enum.Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Status(BaseModel, frozen=True):
    status: Outcome = Field(alias="@status")
    starttime: DateTimeFormat = Field(alias="@starttime")
    endtime: DateTimeFormat = Field(alias="@endtime")


class Test(BaseModel, frozen=True):
    id: str = Field(alias="@id")
    name: str = Field(alias="@name")
    line: int = Field(alias="@line")
    status: Status


class Suite(BaseModel, frozen=True):
    id: str = Field(alias="@id")
    name: str = Field(alias="@name")
    suite: Annotated[list["Suite"], BeforeValidator(_make_tests_and_suites_lists)] = Field(
        default=[]
    )
    test: Annotated[list[Test], BeforeValidator(_make_tests_and_suites_lists)] = Field(default=[])


class Generator(BaseModel, frozen=True):
    generator: str = Field(alias="@generator")
    generated: DateTimeFormat = Field(alias="@generated")
    rpa: bool = Field(alias="@rpa")
    schemaversion: int = Field(alias="@schemaversion")
    suite: Annotated[list[Suite], BeforeValidator(_make_tests_and_suites_lists)] = Field(default=[])
    errors: dict | None = Field(default=None)


class Rebot(BaseModel, frozen=True):
    robot: Generator


def extract_tests_from_suites(suites: list[Suite]) -> dict[str, Test]:
    tests_with_full_names: dict[str, Test] = {}

    for suite in suites:
        tests_with_full_names |= extract_tests_with_full_names(suite)

    return tests_with_full_names


def extract_tests_with_full_names(
    suite: Suite, parent_names: list[str] | None = None
) -> dict[str, Test]:
    if parent_names is None:
        parent_names = []

    tests_with_full_names = {}

    for test in suite.test:
        test_name = "-".join([*parent_names, suite.name, test.name])
        tests_with_full_names[test_name] = test

    for sub_suite in suite.suite:
        tests_with_full_names |= extract_tests_with_full_names(
            sub_suite, parent_names + [suite.name]
        )

    return tests_with_full_names
