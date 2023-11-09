#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Union

from pydantic import BaseModel, BeforeValidator, Field, PlainValidator
from typing_extensions import Annotated


def _parse_datetime(value: str) -> datetime:
    date_format = "%Y%m%d %H:%M:%S.%f"
    return datetime.strptime(value, date_format)


DateTimeFormat = Annotated[datetime, PlainValidator(_parse_datetime)]


def _ensure_sequence(
    raw_value: Union[Mapping[str, object], Sequence[Mapping[str, object]]]
) -> Sequence[Mapping[str, object]]:
    return [raw_value] if isinstance(raw_value, Mapping) else raw_value


class Outcome(enum.Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Status(BaseModel, frozen=True):
    status: Outcome = Field(alias="@status")
    starttime: DateTimeFormat = Field(alias="@starttime")
    endtime: DateTimeFormat = Field(alias="@endtime")
    text: str | None = Field(default=None, alias="#text")


class Test(BaseModel, frozen=True):
    id: str = Field(alias="@id")
    name: str = Field(alias="@name")
    line: int = Field(alias="@line")
    status: Status
    tag: str | None = None


class Suite(BaseModel, frozen=True):
    id: str = Field(alias="@id")
    name: str = Field(alias="@name")
    suite: Annotated[Sequence["Suite"], BeforeValidator(_ensure_sequence)] = Field(default=[])
    test: Annotated[Sequence[Test], BeforeValidator(_ensure_sequence)] = Field(default=[])


class Generator(BaseModel, frozen=True):
    generator: str = Field(alias="@generator")
    generated: DateTimeFormat = Field(alias="@generated")
    rpa: bool = Field(alias="@rpa")
    schemaversion: int = Field(alias="@schemaversion")
    errors: Mapping[str, object] | None = Field(default=None)
    suite: Suite


class Rebot(BaseModel, frozen=True):
    robot: Generator


def extract_tests_with_full_names(
    suite: Suite,
    parent_names: Sequence[str] = (),
) -> dict[str, Test]:
    tests_with_full_names = {}

    for test in suite.test:
        test_name = "-".join([*parent_names, suite.name, test.name])
        tests_with_full_names[test_name] = test

    for sub_suite in suite.suite:
        tests_with_full_names |= extract_tests_with_full_names(
            sub_suite, parent_names=[*parent_names, suite.name]
        )

    return tests_with_full_names
