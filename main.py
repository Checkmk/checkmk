# mypy: disallow-any-expr
import enum
import typing

import pydantic


class Outcome(enum.Enum):
    passed = "passed"
    failed = "failed"
    skipped = "skipped"


class TestReport(pydantic.BaseModel, extra=pydantic.Extra.allow):
    report_type: typing.Literal["TestReport"] = pydantic.Field(
        "TestReport", alias="$report_type", const=True
    )
    location: tuple[str, int, str]
    outcome: Outcome


class SessionStart(pydantic.BaseModel, extra=pydantic.Extra.allow):
    report_type: typing.Literal["SessionStart"] = pydantic.Field(
        "SessionStart", alias="$report_type", const=True
    )


class CollectReport(pydantic.BaseModel, extra=pydantic.Extra.allow):
    report_type: typing.Literal["CollectReport"] = pydantic.Field(
        "CollectReport", alias="$report_type", const=True
    )


class SessionFinish(pydantic.BaseModel, extra=pydantic.Extra.allow):
    report_type: typing.Literal["SessionFinish"] = pydantic.Field(
        "SessionFinish", alias="$report_type", const=True
    )


Report = TestReport | SessionStart | CollectReport | SessionFinish


def parse_report(report_json: str | bytes) -> Report:
    return pydantic.parse_raw_as(Report, report_json)  # type: ignore[arg-type]


def filter_failed_tests(reports: list[Report]) -> list[TestReport]:
    return [r for r in reports if isinstance(r, TestReport) and r.outcome == Outcome.failed]


def insert(path: str, index: int) -> None:
    with open(path, "r") as file:
        content = file.readlines()
    content.insert(index, '@pytest.mark.usefixtures("initialised_item_state")\n')
    with open(path, "w") as file:
        file.writelines(content)


def main():
    with open("/tmp/test", "r", encoding="utf-8") as file:
        report_content = file.readlines()
    reports = [parse_report(report_json) for report_json in report_content]
    failed_tests = filter_failed_tests(reports)
    path_to_index: dict[str, list[int]] = {}
    for t in failed_tests:
        (path, index, _test_name) = t.location
        path_to_index.setdefault(path, []).append(index)
    for path, indices in path_to_index.items():
        insert(path, indices[0])


main()
