#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from datetime import timedelta
from typing import Literal

from .model import BodyItem

class Tags:
    def robot(self, name: str) -> bool: ...

class TestCase:
    name: str
    id: str
    elapsed_time: timedelta
    status: Literal["PASS", "FAIL", "SKIP", "NOT RUN", "NOT SET"]
    tags: Tags
    body: Sequence[BodyItem]

class TestSuite:
    name: str
    suites: Sequence[TestSuite]
    tests: Sequence[TestCase]

class Message:
    message: str

class Keyword(BodyItem):
    name: str | None
    elapsed_time: timedelta
    status: Literal["PASS", "FAIL", "SKIP", "NOT RUN", "NOT SET"]
    messages: Sequence[Message]

class Result:
    def visit(self, visitor: ResultVisitor) -> None: ...

class ResultVisitor: ...

def ExecutionResult(raw_xml: str) -> Result: ...
