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
    suites: Sequence["TestSuite"]
    tests: Sequence[TestCase]

class Keyword(BodyItem):
    name: str | None
    elapsed_time: timedelta
    status: Literal["PASS", "FAIL", "SKIP", "NOT RUN", "NOT SET"]

class Result:
    def visit(self, visitor: "ResultVisitor") -> None: ...

class ResultVisitor: ...

def ExecutionResult(raw_xml: str) -> Result: ...
