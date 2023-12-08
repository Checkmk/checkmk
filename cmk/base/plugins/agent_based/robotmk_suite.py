#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from itertools import chain
from time import time
from typing import TypedDict

from cmk.plugins.lib.robotmk_rebot_xml import Outcome, StatusV6, StatusV7
from cmk.plugins.lib.robotmk_suite_and_test_checking import message_if_rebot_is_too_old
from cmk.plugins.lib.robotmk_suite_execution_report import (
    AttemptOutcome,
    AttemptOutcomeOtherError,
    AttemptsConfig,
    RebotOutcomeError,
    Section,
    SuiteRebotReport,
    SuiteReport,
)

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult


def discover(section: Section) -> DiscoveryResult:
    yield from (Service(item=suite_id) for suite_id in section.suites)


class CheckParameters(TypedDict):
    upper_levels_runtime_percentage: tuple[float, float] | None


def check(
    item: str,
    params: CheckParameters,
    section: Section,
) -> CheckResult:
    if not (report := section.suites.get(item)):
        return
    yield from _check_suite_execution_report(report, params, time())


def _check_suite_execution_report(
    report: SuiteReport,
    params: CheckParameters,
    now: float,
) -> CheckResult:
    yield from _check_rebot(
        rebot=report.rebot,
        config=report.config,
        upper_levels_runtime_percentage=params["upper_levels_runtime_percentage"],
        now=now,
    )

    yield from chain.from_iterable(
        _check_attempt(attempt_number, attempt)
        for attempt_number, attempt in enumerate(report.attempts, start=1)
    )


def _check_rebot(
    *,
    rebot: SuiteRebotReport | RebotOutcomeError | None,
    config: AttemptsConfig,
    upper_levels_runtime_percentage: tuple[float, float] | None,
    now: float,
) -> CheckResult:
    match rebot:
        case SuiteRebotReport():
            if (
                rebot_too_old_message := message_if_rebot_is_too_old(
                    rebot_timestamp=rebot.timestamp,
                    execution_interval=config.interval,
                    now=now,
                )
            ) is not None:
                yield Result(
                    state=State.CRIT,
                    summary=rebot_too_old_message,
                )
            yield from _check_runtime(
                status=rebot.top_level_suite.status,
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


def _check_runtime(
    status: StatusV6 | StatusV7,
    config: AttemptsConfig,
    upper_levels_percentage: tuple[float, float] | None,
) -> CheckResult:
    if status.runtime is None:
        yield Result(
            state=State.OK,
            summary="Runtime not available",
        )
        return

    yield from check_levels(
        value=status.runtime,
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


def _check_attempt(
    attempt_number: int,
    attempt_outcome: AttemptOutcome | AttemptOutcomeOtherError,
) -> CheckResult:
    if isinstance(attempt_outcome, AttemptOutcome):
        match attempt_outcome:
            case AttemptOutcome.RobotFrameworkFailure:
                yield Result(
                    state=State.WARN,
                    summary=f"Attempt {attempt_number}: Robot Framework failure",
                )
            case AttemptOutcome.EnvironmentFailure:
                yield Result(
                    state=State.WARN,
                    summary=f"Attempt {attempt_number}: Environment failure",
                )
            case AttemptOutcome.TimedOut:
                yield Result(
                    state=State.WARN,
                    summary=f"Attempt {attempt_number}: Timeout",
                )
    else:
        yield Result(
            state=State.WARN,
            summary=f"Attempt {attempt_number}: Error, see service details",
            details=attempt_outcome.OtherError,
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
