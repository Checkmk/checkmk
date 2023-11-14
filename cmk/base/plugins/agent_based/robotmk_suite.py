#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from time import time
from typing import assert_never, TypedDict

from cmk.plugins.lib.robotmk_parse_xml import Outcome, StatusV6, StatusV7
from cmk.plugins.lib.robotmk_suite_execution_report import (
    AttemptOutcome,
    AttemptOutcomeOtherError,
    AttemptsConfig,
    ExecutionReport,
    ExecutionReportAlreadyRunning,
    RebotOutcomeError,
    RebotOutcomeResult,
)

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


def discover(
    section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning]
) -> DiscoveryResult:
    yield from (Service(item=suite_name) for suite_name in section)


class CheckParameters(TypedDict):
    upper_levels_runtime_percentage: tuple[float, float] | None


def check(
    item: str,
    params: CheckParameters,
    section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning],
) -> CheckResult:
    if not (execution_report := section.get(item)):
        return
    yield from _check_suite_execution_report(execution_report, params, time())


def _check_suite_execution_report(
    report: ExecutionReport | ExecutionReportAlreadyRunning,
    params: CheckParameters,
    now: float,
) -> CheckResult:
    if isinstance(report, ExecutionReportAlreadyRunning):
        yield Result(state=State.CRIT, summary="Suite already running, execution skipped")
        return

    yield from _check_rebot(
        rebot=report.Executed.rebot,
        config=report.Executed.config,
        upper_levels_runtime_percentage=params["upper_levels_runtime_percentage"],
        now=now,
    )

    for attempt in report.Executed.attempts:
        yield _attempt_result(attempt)


def _check_rebot(
    *,
    rebot: RebotOutcomeResult | RebotOutcomeError | None,
    config: AttemptsConfig,
    upper_levels_runtime_percentage: tuple[float, float] | None,
    now: float,
) -> CheckResult:
    match rebot:
        case RebotOutcomeResult():
            yield from _check_rebot_age(
                rebot_timestamp=rebot.Ok.timestamp,
                execution_interval=config.interval,
                now=now,
            )
            yield from _check_runtime(
                status=rebot.Ok.xml.robot.suite.status,
                config=config,
                upper_levels_percentage=upper_levels_runtime_percentage,
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


def _check_runtime(
    status: StatusV6 | StatusV7,
    config: AttemptsConfig,
    upper_levels_percentage: tuple[float, float] | None,
) -> CheckResult:
    if (runtime := status.runtime()) is None:
        yield Result(
            state=State.OK,
            summary="Runtime not available",
        )
        return

    yield from check_levels(
        value=runtime,
        levels_upper=(
            config.timeout * config.n_attempts_max * upper_levels_percentage[0] / 100,
            config.timeout * config.n_attempts_max * upper_levels_percentage[1] / 100,
        )
        if upper_levels_percentage
        else None,
        metric_name="robotmk_suite_runtime" if status.status is Outcome.PASS else None,
        render_func=render.timespan,
        label="Runtime",
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
    check_default_parameters=CheckParameters(
        upper_levels_runtime_percentage=(80.0, 90.0),
    ),
    check_ruleset_name="robotmk_suite",
)
