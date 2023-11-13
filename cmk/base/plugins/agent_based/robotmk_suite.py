#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import assert_never

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.robotmk_suite_execution_report import (
    AttemptOutcome,
    AttemptOutcomeOtherError,
    ExecutionReport,
    ExecutionReportAlreadyRunning,
)


def discover(
    section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning]
) -> DiscoveryResult:
    yield from (Service(item=suite_name) for suite_name in section)


def check(
    item: str, section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning]
) -> CheckResult:
    if not (execution_report := section.get(item)):
        return
    yield from _check_suite_execution_report(execution_report)


def _check_suite_execution_report(
    report: ExecutionReport | ExecutionReportAlreadyRunning,
) -> CheckResult:
    if isinstance(report, ExecutionReportAlreadyRunning):
        yield Result(state=State.CRIT, summary="Suite already running, execution skipped")
        return

    for attempt in report.Executed.attempts:
        yield _attempt_result(attempt)


def _attempt_result(
    attempt_outcome: AttemptOutcome | AttemptOutcomeOtherError,
) -> Result:
    state = State.OK if attempt_outcome is AttemptOutcome.AllTestsPassed else State.CRIT

    match attempt_outcome:
        case AttemptOutcome.AllTestsPassed:
            summary = "All tests passed"
        case AttemptOutcome.TestFailures:
            summary = "Test failures"
        case AttemptOutcome.RobotFrameworkFailure:
            summary = "Robot Framework failure"
        case AttemptOutcome.EnvironmentFailure:
            summary = "Environment failure"
        case AttemptOutcome.TimedOut:
            summary = "Timeout"
        case AttemptOutcomeOtherError():
            summary = "Unexpected error"
        case _:
            assert_never(attempt_outcome)

    return (
        Result(state=state, summary=summary, details=attempt_outcome.OtherError)
        if isinstance(attempt_outcome, AttemptOutcomeOtherError)
        else Result(
            state=state,
            summary=summary,
        )
    )


register.check_plugin(
    name="robotmk_suite",
    sections=["robotmk_suite_execution_report"],
    service_name="RMK Suite %s",
    discovery_function=discover,
    check_function=check,
)
