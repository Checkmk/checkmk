#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.robotmk_suite import (
    _check_suite_execution_report,
    check,
    CheckParameters,
    discover,
)

from cmk.plugins.lib.robotmk_parse_xml import Generator, Outcome, Rebot, StatusV6, Suite, Test
from cmk.plugins.lib.robotmk_suite_execution_report import (
    AttemptOutcome,
    AttemptsConfig,
    AttemptsOutcome,
    ExecutionReport,
    RebotOutcomeError,
    RebotOutcomeResult,
    RebotResult,
)

_SECTION = {
    "suite_1": ExecutionReport(
        Executed=AttemptsOutcome(
            attempts=[AttemptOutcome.AllTestsPassed],
            rebot=RebotOutcomeResult(
                Ok=RebotResult.model_construct(
                    xml=Rebot(
                        robot=Generator(
                            suite=Suite.model_construct(
                                name="Suite 1",
                                suite=[],
                                test=[],
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 15, 8, 27, 40),
                                    endtime=datetime(2023, 11, 15, 8, 27, 42),
                                ),
                            ),
                        )
                    ),
                    html_base64="irrelevant",
                    timestamp=100,
                )
            ),
            config=AttemptsConfig(
                interval=1200,
                timeout=10,
                n_attempts_max=1,
            ),
        )
    ),
    "suite_2": ExecutionReport(
        Executed=AttemptsOutcome(
            attempts=[AttemptOutcome.AllTestsPassed],
            rebot=RebotOutcomeResult(
                Ok=RebotResult.model_construct(
                    xml=Rebot(
                        robot=Generator(
                            suite=Suite.model_construct(
                                name="Suite 2",
                                suite=[],
                                test=[
                                    Test.model_construct(
                                        name="Some test",
                                        status=StatusV6.model_construct(
                                            status=Outcome.PASS,
                                            starttime=datetime(2023, 11, 15, 8, 27, 41),
                                            endtime=datetime(2023, 11, 15, 8, 37, 41),
                                        ),
                                    ),
                                ],
                                status=StatusV6.model_construct(
                                    status=Outcome.PASS,
                                    starttime=datetime(2023, 11, 15, 8, 27, 40),
                                    endtime=datetime(2023, 11, 15, 8, 37, 42),
                                ),
                            ),
                        )
                    ),
                    html_base64="irrelevant",
                    timestamp=100,
                )
            ),
            config=AttemptsConfig(
                interval=1200,
                timeout=800,
                n_attempts_max=1,
            ),
        )
    ),
    "suite_3": ExecutionReport(
        Executed=AttemptsOutcome(
            attempts=[AttemptOutcome.TestFailures, AttemptOutcome.TimedOut],
            rebot=RebotOutcomeResult(
                Ok=RebotResult.model_construct(
                    xml=Rebot(
                        robot=Generator(
                            suite=Suite.model_construct(
                                name="Suite 3",
                                suite=[],
                                test=[
                                    Test.model_construct(
                                        name="Some test",
                                        status=StatusV6.model_construct(
                                            status=Outcome.FAIL,
                                            starttime=datetime(2023, 11, 15, 8, 27, 41),
                                            endtime=datetime(2023, 11, 15, 8, 33, 45),
                                        ),
                                    ),
                                ],
                                status=StatusV6.model_construct(
                                    status=Outcome.FAIL,
                                    starttime=datetime(2023, 11, 15, 8, 27, 40),
                                    endtime=datetime(2023, 11, 15, 8, 40, 12),
                                ),
                            ),
                        )
                    ),
                    html_base64="irrelevant",
                    timestamp=100,
                )
            ),
            config=AttemptsConfig(
                interval=1200,
                timeout=400,
                n_attempts_max=2,
            ),
        )
    ),
    "suite_4": ExecutionReport(
        Executed=AttemptsOutcome(
            attempts=[AttemptOutcome.AllTestsPassed],
            rebot=RebotOutcomeError(Error="Some failure"),
            config=AttemptsConfig(
                interval=1200,
                timeout=800,
                n_attempts_max=1,
            ),
        )
    ),
    "suite_5": ExecutionReport(
        Executed=AttemptsOutcome(
            attempts=[AttemptOutcome.RobotFrameworkFailure],
            rebot=None,
            config=AttemptsConfig(
                interval=1200,
                timeout=800,
                n_attempts_max=1,
            ),
        )
    ),
}


def test_discover_datadog_monitors() -> None:
    assert list(discover(_SECTION)) == [
        Service(item="suite_1"),
        Service(item="suite_2"),
        Service(item="suite_3"),
        Service(item="suite_4"),
        Service(item="suite_5"),
    ]


def test_check_item_missing_no_output() -> None:
    assert not list(
        check(
            "missing",
            CheckParameters(upper_levels_runtime_percentage=None),
            {},
        )
    )


def test_check_suite_execution_report_ok() -> None:
    assert list(
        _check_suite_execution_report(
            _SECTION["suite_1"],
            CheckParameters(upper_levels_runtime_percentage=(80.0, 90.0)),
            now=123,
        )
    ) == [
        Result(state=State.OK, summary="Runtime: 2 seconds"),
        Metric("robotmk_suite_runtime", 2.0, levels=(8.0, 9.0)),
    ]


def test_check_suite_execution_report_too_old() -> None:
    assert list(
        _check_suite_execution_report(
            _SECTION["suite_1"],
            CheckParameters(upper_levels_runtime_percentage=(80.0, 90.0)),
            now=2734,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Data is too old (age: 43 minutes 54 seconds, execution interval: 20 minutes 0 seconds)",
        ),
        Result(state=State.OK, summary="Runtime: 2 seconds"),
        Metric("robotmk_suite_runtime", 2.0, levels=(8.0, 9.0)),
    ]


def test_check_suite_execution_report_runtime_too_high() -> None:
    assert list(
        _check_suite_execution_report(
            _SECTION["suite_2"],
            CheckParameters(upper_levels_runtime_percentage=(70.0, 80.0)),
            now=123,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Runtime: 10 minutes 2 seconds (warn/crit at 9 minutes 20 seconds/10 minutes 40 seconds)",
        ),
        Metric("robotmk_suite_runtime", 602.0, levels=(560.0, 640.0)),
    ]


def test_check_suite_execution_report_failure_no_metric() -> None:
    assert list(
        _check_suite_execution_report(
            _SECTION["suite_3"],
            CheckParameters(upper_levels_runtime_percentage=(70.0, 80.0)),
            now=123,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Runtime: 12 minutes 32 seconds (warn/crit at 9 minutes 20 seconds/10 minutes 40 seconds)",
        ),
        Result(state=State.WARN, summary="Attempt 2: Timeout"),
    ]


def test_check_suite_execution_report_rebot_error() -> None:
    assert list(
        _check_suite_execution_report(
            _SECTION["suite_4"],
            CheckParameters(upper_levels_runtime_percentage=(80.0, 90.0)),
            now=1,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Producing merged test results with Rebot failed, see details",
            details="Some failure",
        )
    ]


def test_check_suite_execution_report_no_rebot() -> None:
    assert list(
        _check_suite_execution_report(
            _SECTION["suite_5"],
            CheckParameters(upper_levels_runtime_percentage=(80.0, 90.0)),
            now=1,
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="No data available because none of the attempts produced any output",
        ),
        Result(state=State.WARN, summary="Attempt 1: Robot Framework failure"),
    ]
