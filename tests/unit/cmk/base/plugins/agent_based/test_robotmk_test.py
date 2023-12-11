#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResults,
    Metric,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult
from cmk.base.plugins.agent_based.robotmk_test import (
    _check_test_and_keywords,
    check,
    discover,
    Params,
)

from cmk.plugins.lib.robotmk_rebot_xml import Keyword, KeywordStatus, Outcome, RFTest, StatusV6
from cmk.plugins.lib.robotmk_suite_execution_report import AttemptsConfig, Section, TestReport

_Section = Section(
    suites={},
    tests={
        "ok_passed": TestReport(
            test=RFTest.model_construct(
                id="s1-t1",
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
            test=RFTest.model_construct(
                id="s1-t2",
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
            test=RFTest.model_construct(
                id="s1-t3",
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
            test=RFTest.model_construct(
                id="s1-t4",
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
            test=RFTest.model_construct(
                id="s1-t5",
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
        "skipped_test": TestReport(
            test=RFTest.model_construct(
                id="s1-t6",
                name="Skipped Test",
                status=StatusV6.model_construct(
                    status=Outcome.FAIL,
                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                    elapsed=None,
                ),
                robot_exit=True,
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
            rebot_timestamp=1701098145,
        ),
        "test_result_too_old": TestReport(
            test=RFTest.model_construct(
                id="s1-t7",
                name="Test Result Too Old",
                status=StatusV6.model_construct(
                    status=Outcome.FAIL,
                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                    elapsed=None,
                ),
                robot_exit=False,
            ),
            html=b"irrelevant",
            attempts_config=AttemptsConfig(interval=15, timeout=5, n_attempts_max=1),
            rebot_timestamp=1701088000,
        ),
        "test_with_keyword": TestReport(
            test=RFTest.model_construct(
                id="s1-t8",
                name="Test with keyword",
                status=StatusV6.model_construct(
                    status=Outcome.PASS,
                    starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                    endtime=datetime(2023, 11, 27, 7, 15, 45, 518000),
                    elapsed=None,
                ),
                robot_exit=False,
                keywords=[
                    Keyword(
                        id="s1-t8-k1",
                        name="MyLogKeyword",
                        status=KeywordStatus.model_construct(
                            status=StatusV6.model_construct(
                                status=Outcome.PASS,
                                starttime=datetime(2023, 11, 27, 7, 15, 45, 515000),
                                endtime=datetime(2023, 11, 27, 7, 15, 46, 518000),
                            )
                        ),
                    )
                ],
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
        Service(
            item="skipped_test",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
        Service(
            item="test_result_too_old",
            labels=[
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        ),
        Service(
            item="test_with_keyword",
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
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [
                Result(state=State.OK, summary="Count My Veggies"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 35 seconds"),
                Metric("robotmk_test_runtime", 34.774),
            ],
            id="Test passed and no params available",
        ),
        pytest.param(
            "warn_passed_with_long_runtime",
            Params(test_runtime=(30, 60), runtime_thresholds_keywords=[]),
            [
                Result(state=State.OK, summary="Count My Veggies"),
                Result(state=State.OK, summary="PASS"),
                Result(
                    state=State.WARN,
                    summary="Test runtime: 35 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
                ),
                Metric("robotmk_test_runtime", 34.774, levels=(30.0, 60.0)),
            ],
            id="Test passed, but runtime was too long",
        ),
        pytest.param(
            "warn_not_run",
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [
                Result(
                    state=State.OK,
                    summary="Execute Google image search and store the first result image",
                ),
                Result(state=State.WARN, summary="NOT RUN"),
            ],
            id="Test was not run",
        ),
        pytest.param(
            "warn_skip",
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [
                Result(state=State.OK, summary="Addition 1"),
                Result(state=State.WARN, summary="SKIP"),
            ],
            id="Test was skipped",
        ),
        pytest.param(
            "crit_fail",
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [
                Result(state=State.OK, summary="Addition 2"),
                Result(state=State.CRIT, summary="FAIL"),
            ],
            id="Test failed",
        ),
        pytest.param(
            "skipped_test",
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [IgnoreResults("Test has `robot:exit` tag")],
            id="Skipped test with robot:exit tag",
        ),
        pytest.param(
            "test_result_too_old",
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [
                IgnoreResults(
                    "Data is too old (age: 2 hours 49 minutes, execution interval: 8 minutes 20 seconds)"
                )
            ],
            id="Rebot age too old",
        ),
        pytest.param(
            "test_with_keyword",
            Params(test_runtime=None, runtime_thresholds_keywords=[]),
            [
                Result(state=State.OK, summary="Test with keyword"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 3 milliseconds"),
                Metric("robotmk_test_runtime", 0.003),
            ],
            id="Test with a keyword but no pattern and threshold set",
        ),
        pytest.param(
            "test_with_keyword",
            Params(test_runtime=None, runtime_thresholds_keywords=[("MyLogKey*", None)]),
            [
                Result(state=State.OK, summary="Test with keyword"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 3 milliseconds"),
                Metric("robotmk_test_runtime", 0.003),
                Metric("robotmk_s1-t8-k1-mylogkeyword_runtime", 1.003),
            ],
            id="Test with a keyword but no thresholds set",
        ),
        pytest.param(
            "test_with_keyword",
            Params(test_runtime=None, runtime_thresholds_keywords=[("MyLogKey*", (30, 60))]),
            [
                Result(state=State.OK, summary="Test with keyword"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 3 milliseconds"),
                Metric("robotmk_test_runtime", 0.003),
                Result(state=State.OK, summary="Keyword MyLogKeyword runtime: 1 second"),
                Metric("robotmk_s1-t8-k1-mylogkeyword_runtime", 1.003, levels=(30.0, 60.0)),
            ],
            id="Test with a keyword and thresholds set",
        ),
        pytest.param(
            "test_with_keyword",
            Params(
                test_runtime=None,
                runtime_thresholds_keywords=[("NoMatchRegex.*", None), ("MyLogKey*", (30, 60))],
            ),
            [
                Result(state=State.OK, summary="Test with keyword"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 3 milliseconds"),
                Metric("robotmk_test_runtime", 0.003),
                Result(state=State.OK, summary="Keyword MyLogKeyword runtime: 1 second"),
                Metric("robotmk_s1-t8-k1-mylogkeyword_runtime", 1.003, levels=(30.0, 60.0)),
            ],
            id="Test with a keyword and second pattern is matching",
        ),
        pytest.param(
            "test_with_keyword",
            Params(
                test_runtime=None,
                runtime_thresholds_keywords=[("MyLogKey*", (20, 40)), ("MyL*", (30, 60))],
            ),
            [
                Result(state=State.OK, summary="Test with keyword"),
                Result(state=State.OK, summary="PASS"),
                Result(state=State.OK, summary="Test runtime: 3 milliseconds"),
                Metric("robotmk_test_runtime", 0.003),
                Result(state=State.OK, summary="Keyword MyLogKeyword runtime: 1 second"),
                Metric("robotmk_s1-t8-k1-mylogkeyword_runtime", 1.003, levels=(20.0, 40.0)),
            ],
            id="Multiple keyword patterns match, but only first is considered",
        ),
    ],
)
def test_check_test_and_keywords(
    item: str,
    params: Params,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            _check_test_and_keywords(
                params=params,
                test=_Section.tests[item].test,
                rebot_timestamp=_Section.tests[item].rebot_timestamp,
                execution_interval=500,
                now=1701098145,
            )
        )
        == expected_result
    )


def test_check_robotmk_test_item_not_found() -> None:
    assert not list(
        check(
            item="unexpected-item",
            params=Params(test_runtime=None, runtime_thresholds_keywords=[]),
            section=_Section,
        )
    )
