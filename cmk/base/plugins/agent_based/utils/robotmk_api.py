#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Should be replaced by external package

import enum
from base64 import b64decode
from collections.abc import Sequence
from datetime import datetime

from pydantic import BaseModel, TypeAdapter


class JSON(BaseModel, frozen=True):
    pass


class Outcome(enum.Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Test(JSON, frozen=True):
    name: str
    id_: str
    status: Outcome
    starttime: datetime
    endtime: datetime


class Result(JSON, frozen=True):
    suite_name: str
    tests: list[Test]
    xml: str
    html: bytes

    def decode_html(self) -> str:
        return b64decode(self.html).decode("utf-8")


class ConfigReadingError(JSON, frozen=True):
    config_reading_error: str


class ConfigFileContent(JSON, frozen=True):
    config_file_content: str


Section = list[Result]

SubSection = Result | ConfigReadingError | ConfigFileContent


def _parse_line(line: str) -> SubSection:
    adapter = TypeAdapter(SubSection)
    return adapter.validate_json(line)  # type: ignore[return-value]


def parse(string_table: Sequence[Sequence[str]]) -> Section:
    subsections = [_parse_line(line[0]) for line in string_table]
    results = [s for s in subsections if isinstance(s, Result)]
    return Section(results)
