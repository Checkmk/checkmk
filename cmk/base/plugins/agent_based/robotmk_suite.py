#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from time import time
from typing import assert_never

from cmk.plugins.lib.robotmk_suite_execution_report import (
    AttemptOutcome,
    AttemptOutcomeOtherError,
    AttemptsConfig,
    ExecutionReport,
    ExecutionReportAlreadyRunning,
    RebotOutcomeError,
    RebotOutcomeResult,
)

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


def discover(
    section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning]
) -> DiscoveryResult:
    yield from (Service(item=suite_name) for suite_name in section)


def check(
    item: str, section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning]
) -> CheckResult:
    if not (execution_report := section.get(item)):
        return
    yield from _check_suite_execution_report(execution_report, time())


def _check_suite_execution_report(
    report: ExecutionReport | ExecutionReportAlreadyRunning,
    now: float,
) -> CheckResult:
    if isinstance(report, ExecutionReportAlreadyRunning):
        yield Result(state=State.CRIT, summary="Suite already running, execution skipped")
        return

    yield from _check_rebot(
        rebot=report.Executed.rebot,
        config=report.Executed.config,
        now=now,
    )

    for attempt in report.Executed.attempts:
        yield _attempt_result(attempt)


def _check_rebot(
    *,
    rebot: RebotOutcomeResult | RebotOutcomeError | None,
    config: AttemptsConfig,
    now: float,
) -> CheckResult:
    match rebot:
        case RebotOutcomeResult():
            yield from _check_rebot_age(
                rebot_timestamp=rebot.Ok.timestamp,
                execution_interval=config.interval,
                now=now,
            )
        case RebotOutcomeError():
            yield Result(
                state=State.CRIT,
                summary="Producing merged test results with Rebot failed, see details",
                details=rebot.Error,
            )
        case None:
            yield Result(
                state=State.CRIT,
                summary="No data available because none of the attempts produced any output",
            )


def _check_rebot_age(
    *,
    rebot_timestamp: int,
    execution_interval: int,
    now: float,
) -> CheckResult:
    if (rebot_age := now - rebot_timestamp) > execution_interval:
        yield Result(
            state=State.CRIT,
            summary=(
                f"Data is too old (age: {render.timespan(rebot_age)}, "
                f"execution interval: {render.timespan(execution_interval)})"
            ),
        )


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
