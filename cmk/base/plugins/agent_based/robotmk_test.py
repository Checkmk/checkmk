#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from typing import assert_never, Literal, TypedDict

from cmk.utils.paths import robotmk_html_log_dir  # pylint: disable=cmk-module-layer-violation

from cmk.agent_based.v1_backend.plugin_contexts import (  # pylint: disable=cmk-module-layer-violation
    host_name,
    service_description,
)

from .agent_based_api.v1 import check_levels, register, render, Result, Service, ServiceLabel, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.robotmk_parse_xml import extract_tests_with_full_names, Outcome, Test
from .utils.robotmk_suite_execution_report import (
    ExecutionReport,
    ExecutionReportAlreadyRunning,
    RebotOutcomeResult,
)


class Params(TypedDict):
    test_runtime: tuple[int, int] | None


def discover(
    section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning]
) -> DiscoveryResult:
    for execution_report in section.values():
        if isinstance(execution_report, ExecutionReport):
            yield from _discover_tests(execution_report)


def _discover_tests(report: ExecutionReport) -> DiscoveryResult:
    if not isinstance(rebot_result := report.Executed.rebot, RebotOutcomeResult):
        return

    for test_name in extract_tests_with_full_names(rebot_result.Ok.xml.robot.suite):
        yield Service(
            item=test_name,
            labels=[
                ServiceLabel("robotmk", "true"),
                ServiceLabel("robotmk/html_last_error_log", "yes"),
                ServiceLabel("robotmk/html_last_log", "yes"),
            ],
        )


def check(
    item: str,
    params: Params,
    section: Mapping[str, ExecutionReport | ExecutionReportAlreadyRunning],
) -> CheckResult:
    for execution_report in section.values():
        if not isinstance(execution_report, ExecutionReport):
            continue
        if not isinstance(rebot_result := execution_report.Executed.rebot, RebotOutcomeResult):
            continue

        if not (test := extract_tests_with_full_names(rebot_result.Ok.xml.robot.suite).get(item)):
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
    name="robotmk_test",
    sections=["robotmk_suite_execution_report"],
    service_name="RMK Test %s",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="robotmk",
    check_default_parameters=Params(test_runtime=None),
)
