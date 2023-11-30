#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.robotmk_test import _check_test, check, discover, Params

from cmk.plugins.lib.robotmk_rebot_xml import Outcome, StatusV6, Test
from cmk.plugins.lib.robotmk_suite_execution_report import AttemptsConfig, Section, TestReport

_Section = Section(
    suites={},
    tests={
        "ok_passed": TestReport(
            test=Test.model_construct(
                name="Count My Veggies",
                status=StatusV6.model_construct(
                    status=Outcome.PASS,
                    starttime=datetime(2023, 11, 27, 7, 14, 6, 658000),
                    endtime=datetime(2023, 11, 27, 7, 14, 41, 432000),
                    elapsed=None,
                ),
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
            rebot_timestamp=1701098081,
        ),
        "warn_passed_with_long_runtime": TestReport(
            test=Test.model_construct(
                name="Count My Veggies",
                status=StatusV6.model_construct(
                    status=Outcome.PASS,
                    starttime=datetime(2023, 11, 27, 7, 14, 6, 658000),
                    endtime=datetime(2023, 11, 27, 7, 14, 41, 432000),
                    elapsed=None,
                ),
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
            rebot_timestamp=1701098081,
        ),
        "warn_not_run": TestReport(
            test=Test.model_construct(
                name="Execute Google image search and store the first result image",
                status=StatusV6.model_construct(
                    status=Outcome.NOT_RUN,
                    starttime=datetime(2023, 11, 27, 7, 10, 4, 392000),
                    endtime=datetime(2023, 11, 27, 7, 10, 4, 392000),
                    elapsed=None,
                ),
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=120, timeout=90, n_attempts_max=1),
            rebot_timestamp=1701097844,
        ),
        "warn_skip": TestReport(
            test=Test.model_construct(
                name="Addition 1",
                status=StatusV6.model_construct(
                    status=Outcome.SKIP,
                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                    endtime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                    elapsed=None,
                ),
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
            rebot_timestamp=1701098145,
        ),
        "crit_fail": TestReport(
            test=Test.model_construct(
                name="Addition 2",
                status=StatusV6.model_construct(
                    status=Outcome.FAIL,
                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                    elapsed=None,
                ),
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
            rebot_timestamp=1701098145,
        ),
    },
)


def test_discover_robotmk_test() -> None:
    assert list(discover(section=_Section)) == [
        Service(
            item="ok_passed",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
        Service(
            item="warn_passed_with_long_runtime",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
        Service(
            item="warn_not_run",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
        Service(
            item="warn_skip",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
        Service(
            item="crit_fail",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "ok_passed",
            Params(test_runtime=None),
            [
                Result(state=State.OK, summary="Count My Veggies"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 35 seconds"),
                Metric("test_runtime", 34.774),
            ],
            id="Test passed and no params available",
        ),
        pytest.param(
            "warn_passed_with_long_runtime",
            Params(test_runtime=(30, 60)),
            [
                Result(state=State.OK, summary="Count My Veggies"),
                Result(state=State.OK, summary="PASS"),
                Result(
                    state=State.WARN,
                    summary="Test runtime: 35 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
                ),
                Metric("test_runtime", 34.774, levels=(30.0, 60.0)),
            ],
            id="Test passed, but runtime was too long",
        ),
        pytest.param(
            "warn_not_run",
            Params(test_runtime=None),
            [
                Result(
                    state=State.OK,
                    summary="Execute Google image search and store the first result image",
                ),
                Result(state=State.WARN, summary="NOT RUN"),
                Result(state=State.OK, summary="Test runtime: 0 seconds"),
                Metric("test_runtime", 0.0),
            ],
            id="Test was not run",
        ),
        pytest.param(
            "warn_skip",
            Params(test_runtime=None),
            [
                Result(state=State.OK, summary="Addition 1"),
                Result(state=State.WARN, summary="SKIP"),
                Result(state=State.OK, summary="Test runtime: 0 seconds"),
                Metric("test_runtime", 0.0),
            ],
            id="Test was skipped",
        ),
        pytest.param(
            "crit_fail",
            Params(test_runtime=None),
            [
                Result(state=State.OK, summary="Addition 2"),
                Result(state=State.CRIT, summary="FAIL"),
                Result(state=State.OK, summary="Test runtime: 3 milliseconds"),
                Metric("test_runtime", 0.003),
            ],
            id="Test failed",
        ),
    ],
)
def test_check_robotmk_test(
    item: str,
    params: Params,
    expected_result: CheckResult,
) -> None:
    assert list(_check_test(params=params, test=_Section.tests[item].test)) == expected_result


def test_check_robotmk_test_item_not_found() -> None:
    assert not list(
        check(
            item="unexpected-item",
            params=Params(test_runtime=None),
            section=_Section,
        )
    )
