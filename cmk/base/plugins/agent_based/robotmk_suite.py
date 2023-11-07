#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import assert_never

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import robotmk_api


def discover(section: Sequence[robotmk_api.SuiteExecutionReport]) -> DiscoveryResult:
    yield from (
        Service(item=f"Suite {suite_execution_report.suite_name}")
        for suite_execution_report in section
    )


def check(item: str, section: Sequence[robotmk_api.SuiteExecutionReport]) -> CheckResult:
    for suite_execution_report in section:
        yield from _check_suite_execution_result(suite_execution_report, item)


def _check_suite_execution_result(
    result: robotmk_api.SuiteExecutionReport, item: str
) -> CheckResult:
    if f"Suite {result.suite_name}" != item:
        return

    if isinstance(result.outcome, robotmk_api.ExecutionReportAlreadyRunning):
        yield Result(state=State.CRIT, summary="Suite already running, execution skipped")
        return

    if isinstance(result.outcome.Executed, robotmk_api.AttemptsOutcome):
        for attempt in result.outcome.Executed.attempts:
            yield _attempt_result(attempt)


def _attempt_result(
    attempt_outcome: robotmk_api.AttemptOutcome | robotmk_api.AttemptOutcomeOtherError,
) -> Result:
    state = State.OK if attempt_outcome is robotmk_api.AttemptOutcome.AllTestsPassed else State.CRIT

    match attempt_outcome:
        case robotmk_api.AttemptOutcome.AllTestsPassed:
            summary = "All tests passed"
        case robotmk_api.AttemptOutcome.TestFailures:
            summary = "Test failures"
        case robotmk_api.AttemptOutcome.RobotFrameworkFailure:
            summary = "Robot Framework failure"
        case robotmk_api.AttemptOutcome.EnvironmentFailure:
            summary = "Environment failure"
        case robotmk_api.AttemptOutcome.TimedOut:
            summary = "Timeout"
        case robotmk_api.AttemptOutcomeOtherError():
            summary = "Unexpected error"
        case _:
            assert_never(attempt_outcome)

    return (
        Result(state=state, summary=summary, details=attempt_outcome.OtherError)
        if isinstance(attempt_outcome, robotmk_api.AttemptOutcomeOtherError)
        else Result(
            state=state,
            summary=summary,
        )
    )


register.check_plugin(
    name="robotmk_suite",
    sections=["robotmk_v2"],
    service_name="%s",
    discovery_function=discover,
    check_function=check,
)
