#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import assert_never, Literal, TypedDict

from cmk.utils.paths import robotmk_html_log_dir  # pylint: disable=cmk-module-layer-violation

from cmk.agent_based.v1_backend.plugin_contexts import (  # pylint: disable=cmk-module-layer-violation
    host_name,
    service_description,
)

from .agent_based_api.v1 import check_levels, register, render, Result, Service, ServiceLabel, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import robotmk_api
from .utils.robotmk_parse_xml import extract_tests_from_suites, Outcome, Test


def parse(string_table: StringTable) -> robotmk_api.Section:
    return robotmk_api.parse(string_table)


register.agent_section(
    name="robotmk_v2",
    parse_function=parse,
)


class Params(TypedDict):
    test_runtime: tuple[int, int] | None


def discover(section: robotmk_api.Section) -> DiscoveryResult:
    for suite_execution_report in section.suite_execution_reports:
        yield from _discover_tests(suite_execution_report)


def _discover_tests(result: robotmk_api.SuiteExecutionReport) -> DiscoveryResult:
    if not isinstance(execution_report := result.outcome, robotmk_api.ExecutionReport):
        return
    if not isinstance(
        rebot_result := execution_report.Executed.rebot, robotmk_api.RebotOutcomeResult
    ):
        return

    for test_name in extract_tests_from_suites(rebot_result.Ok.xml.robot.suite):
        yield Service(
            item=test_name,
            labels=[
                ServiceLabel("robotmk", "true"),
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        )


def check(item: str, params: Params, section: robotmk_api.Section) -> CheckResult:
    for suite_execution_report in section.suite_execution_reports:
        if not isinstance(
            execution_report := suite_execution_report.outcome, robotmk_api.ExecutionReport
        ):
            continue
        if not isinstance(
            rebot_result := execution_report.Executed.rebot, robotmk_api.RebotOutcomeResult
        ):
            continue

        if not (test := extract_tests_from_suites(rebot_result.Ok.xml.robot.suite).get(item)):
            continue

        _transmit_to_livestatus(rebot_result.Ok.html_base64, "suite_last_log.html")
        if test.status.status is Outcome.FAIL:
            _transmit_to_livestatus(rebot_result.Ok.html_base64, "suite_last_error_log.html")
            yield from _check_test(params, test)


def _check_test(params: Params, test: Test) -> CheckResult:
    yield Result(state=State.OK, summary=test.name)
    yield Result(state=_remap_state(test.status.status), summary=f"{test.status.status.value}")
    yield from check_levels(
        (test.status.endtime - test.status.starttime).total_seconds(),
        label="Test runtime",
        levels_upper=params["test_runtime"],
        metric_name="test_runtime",
        render_func=render.timespan,
    )


def _transmit_to_livestatus(
    content: str,
    filename: Literal["suite_last_log.html", "suite_last_error_log.html"],
) -> None:
    file_path = Path(robotmk_html_log_dir) / host_name() / service_description() / filename
    file_path.parent.absolute().mkdir(exist_ok=True, parents=True)
    # I'm sure there are no race conditions between livestatus and the checkengine here.
    file_path.write_text(content)


def _remap_state(status: Outcome) -> State:
    match status:
        case Outcome.PASS:
            return State.OK
        case Outcome.FAIL:
            return State.CRIT
        case Outcome.NOT_RUN | Outcome.SKIP:
            return State.WARN
        case _:
            assert_never(status)


register.check_plugin(
    name="robotmk",
    sections=["robotmk_v2"],
    service_name="%s",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="robotmk",
    check_default_parameters=Params(test_runtime=None),
)
