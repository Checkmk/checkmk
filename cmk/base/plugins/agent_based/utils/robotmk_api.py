#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Should be replaced by external package

import enum
from collections.abc import Sequence

from pydantic import BaseModel


class Outcome(enum.Enum):
    FAIL = "FAIL"
    PASS = "PASS"
    SKIP = "SKIP"
    NOT_RUN = "NOT RUN"


class Test(BaseModel, frozen=True):
    name: str
    id_: str
    status: Outcome


class Result(BaseModel, frozen=True):
    suite_name: str
    tests: list[Test]
    xml: str


Section = list[Result]


def parse(string_table: Sequence[Sequence[str]]) -> Section:
    return [Result.parse_raw(file) for file in string_table[0]]
