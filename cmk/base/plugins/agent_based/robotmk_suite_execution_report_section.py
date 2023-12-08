#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.plugins.lib.robotmk_rebot_xml import Suite, Test
from cmk.plugins.lib.robotmk_suite_execution_report import (
    RebotOutcomeResult,
    Section,
    SuiteExecutionReport,
    SuiteRebotReport,
    SuiteReport,
    TestReport,
)

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable


def parse(string_table: StringTable) -> Section:
    suites = {}
    tests = {}
    for line in string_table:
        suite_execution_report = SuiteExecutionReport.model_validate_json(line[0])
        (
            suites[suite_execution_report.suite_id],
            tests_of_suite,
        ) = _post_process_suite_execution_report(suite_execution_report)
        tests.update(tests_of_suite)
    return Section(
        suites=suites,
        tests=tests,
    )


def _post_process_suite_execution_report(
    suite_execution_report: SuiteExecutionReport,
) -> tuple[SuiteReport, dict[str, TestReport]]:
    if isinstance(rebot := suite_execution_report.rebot, RebotOutcomeResult):
        return (
            SuiteReport(
                attempts=suite_execution_report.attempts,
                config=suite_execution_report.config,
                rebot=SuiteRebotReport(
                    top_level_suite=rebot.Ok.xml.robot.suite,
                    timestamp=rebot.Ok.timestamp,
                ),
            ),
            {
                test_name: TestReport(
                    test=test,
                    html=rebot.Ok.html,
                    attempts_config=suite_execution_report.config,
                    rebot_timestamp=rebot.Ok.timestamp,
                )
                for test_name, test in _extract_tests_with_full_names(
                    rebot.Ok.xml.robot.suite,
                    parent_names=[suite_execution_report.suite_id],
                ).items()
            },
        )
    return (
        SuiteReport(
            attempts=suite_execution_report.attempts,
            config=suite_execution_report.config,
            rebot=rebot,
        ),
        {},
    )


def _extract_tests_with_full_names(
    suite: Suite,
    parent_names: Sequence[str] = (),
) -> dict[str, Test]:
    tests_with_full_names = {}

    for test in suite.test:
        test_name = "-".join([*parent_names, suite.name, test.name])
        tests_with_full_names[test_name] = test

    for sub_suite in suite.suite:
        tests_with_full_names |= _extract_tests_with_full_names(
            sub_suite, parent_names=[*parent_names, suite.name]
        )

    return tests_with_full_names


register.agent_section(
    name="robotmk_suite_execution_report",
    parse_function=parse,
)
