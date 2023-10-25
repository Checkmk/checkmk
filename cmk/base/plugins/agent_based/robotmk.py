#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import assert_never, Generator, Literal, TypedDict

from cmk.utils.paths import robotmk_html_log_dir  # pylint: disable=cmk-module-layer-violation

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import robotmk_api  # Should be replaced by external package
from cmk.base.plugins.agent_based.utils.robotmk_parse_xml import extract_tests_from_suites

from cmk.agent_based.v1_backend.plugin_contexts import (  # pylint: disable=cmk-module-layer-violation
    host_name,
    service_description,
)


class Params(TypedDict):
    test_runtime: tuple[int, int] | None


DEFAULT: Params = {"test_runtime": None}


LivestatusFile = Literal["suite_last_log.html", "suite_last_error_log.html"]


def _transmit_to_livestatus(
    content: str,
    filename: LivestatusFile,
) -> None:
    file_path = Path(robotmk_html_log_dir) / host_name() / service_description() / filename
    file_path.parent.absolute().mkdir(exist_ok=True, parents=True)
    # I'm sure there are no race conditions between livestatus and the checkengine here.
    file_path.write_text(content)


def _remap_state(status: robotmk_api.Outcome) -> State:
    match status:
        case robotmk_api.Outcome.PASS:
            return State.OK
        case robotmk_api.Outcome.FAIL:
            return State.CRIT
        case robotmk_api.Outcome.NOT_RUN | robotmk_api.Outcome.SKIP:
            return State.WARN
        case _:
            assert_never(status)


def _remap_attempt_state(status: robotmk_api.AttemptOutcome) -> State:
    match status:
        case robotmk_api.AttemptOutcome.AllTestsPassed:
            return State.OK
        case _:
            return State.CRIT


def parse(string_table: StringTable) -> robotmk_api.Section:
    return robotmk_api.parse(string_table)


register.agent_section(
    name="robotmk_v2",
    parse_function=parse,
)


def _item(result: robotmk_api.Result, test: robotmk_api.Test) -> str:
    return f"{result.suite_name} {test.id_}"


def _discover_tests(result: robotmk_api.SuiteExecutionReport) -> Generator[Service, None, None]:
    if not result.outcome.Executed.rebot.Ok:
        return

    for test_name in extract_tests_from_suites(result.outcome.Executed.rebot.Ok.xml.robot.suite):
        yield Service(item=test_name)


def discover(section: robotmk_api.Section) -> DiscoveryResult:
    for result in section:
        if isinstance(result, robotmk_api.Result):
            for test in result.tests:
                yield Service(
                    item=_item(result, test),
                    labels=[
                        ServiceLabel("robotmk", "true"),
                        ServiceLabel("robotmk/html_last_error_log", "yes"),
                        ServiceLabel("robotmk/html_last_log", "yes"),
                    ],
                )
        if isinstance(result, robotmk_api.ConfigFileContent):
            for suite in result.config_file_content.suites:
                yield Service(item=suite)

        if isinstance(result, robotmk_api.SuiteExecutionReport):
            yield Service(item=f"Suite {result.suite_name}")
            yield from _discover_tests(result)


def _check_test(params: Params, test: robotmk_api.Test) -> CheckResult:
    yield Result(state=State.OK, summary=test.name)
    yield Result(state=_remap_state(test.status), summary=f"{test.status.value}")
    runtime = (test.endtime - test.starttime).total_seconds()
    yield from check_levels(
        runtime,
        label="Test runtime",
        levels_upper=params["test_runtime"],
        metric_name="test_runtime",
        render_func=render.timespan,
    )


def _check_suite_execution_result(
    result: robotmk_api.SuiteExecutionReport, item: str
) -> CheckResult:
    if f"Suite {result.suite_name}" != item:
        return

    if result.outcome.AlreadyRunning is not None:
        yield Result(state=State.OK, summary="It is already running")
    if isinstance(result.outcome.Executed, robotmk_api.AttemptsOutcome):
        for attempt in result.outcome.Executed.attempts:
            yield Result(
                state=_remap_attempt_state(attempt), summary=f"Attempt state: {attempt.value}"
            )


def _check_config_file_content(result: robotmk_api.ConfigFileContent, item: str) -> CheckResult:
    for suite in result.config_file_content.suites:
        if suite == item:
            yield Result(state=State.OK, summary="This Suite was discovered!")


def _check_result(params: Params, result: robotmk_api.Result, item: str) -> CheckResult:
    for test in result.tests:
        if _item(result, test) == item:
            html = result.decode_html()
            _transmit_to_livestatus(html, "suite_last_log.html")
            if test.status is robotmk_api.Outcome.FAIL:
                _transmit_to_livestatus(html, "suite_last_error_log.html")
                yield from _check_test(params, test)


def check(item: str, params: Params, section: robotmk_api.Section) -> CheckResult:
    for result in section:
        if isinstance(result, robotmk_api.ConfigFileContent):
            yield from _check_config_file_content(result, item)
        elif isinstance(result, robotmk_api.Result):
            yield from _check_result(params, result, item)
        elif isinstance(result, robotmk_api.SuiteExecutionReport):
            yield from _check_suite_execution_result(result, item)


register.check_plugin(
    name="robotmk",
    sections=["robotmk_v2"],
    service_name="%s",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="robotmk",
    check_default_parameters=DEFAULT,
)
