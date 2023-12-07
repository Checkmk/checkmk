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


def _parse_datetime_v6(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y%m%d %H:%M:%S.%f")
    except ValueError:
        return None


DateTimeFormatV6 = Annotated[datetime | None, PlainValidator(_parse_datetime_v6)]


def _is_robot_exit(value: str) -> bool:
    return value == "robot:exit"


class Outcome(enum.Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class StatusV6(BaseModel, frozen=True):
    status: Outcome = Field(alias="@status")
    starttime: DateTimeFormatV6 = Field(default=None, alias="@starttime")
    endtime: DateTimeFormatV6 = Field(default=None, alias="@endtime")
    elapsed: float | None = Field(default=None, alias="@elapsed")

    @property
    def runtime(self) -> float | None:
        return (
            self.elapsed
            if self.starttime is None or self.endtime is None
            else (self.endtime - self.starttime).total_seconds()
        )


class StatusV7(BaseModel, frozen=True):
    status: Outcome = Field(alias="@status")
    runtime: float | None = Field(default=None, alias="@elapsed")


class Test(BaseModel, frozen=True):
    name: str = Field(alias="@name")
    status: StatusV6 | StatusV7
    robot_exit: Annotated[bool, BeforeValidator(_is_robot_exit)] = Field(alias="tag", default=False)


def _ensure_sequence(
    raw_value: Union[Mapping[str, object], Sequence[Mapping[str, object]]]
) -> Sequence[Mapping[str, object]]:
    return [raw_value] if isinstance(raw_value, Mapping) else raw_value


class Suite(BaseModel, frozen=True):
    name: str = Field(alias="@name")
    suite: Annotated[Sequence["Suite"], BeforeValidator(_ensure_sequence)] = Field(default=[])
    test: Annotated[Sequence[Test], BeforeValidator(_ensure_sequence)] = Field(default=[])
    status: StatusV6 | StatusV7


class Generator(BaseModel, frozen=True):
    suite: Suite


class Rebot(BaseModel, frozen=True):
    robot: Generator
