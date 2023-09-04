#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never, TypedDict

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import robotmk_api  # Should be replaced by external package


class Params(TypedDict):
    test_runtime: tuple[int, int] | None


DEFAULT: Params = {"test_runtime": None}


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


def parse(string_table: StringTable) -> robotmk_api.Section:
    return robotmk_api.parse(string_table)


register.agent_section(
    name="robotmk_v2",
    parse_function=parse,
)


def _item(result: robotmk_api.Result, test: robotmk_api.Test) -> str:
    return f"{result.suite_name} {test.id_}"


def discover(section: robotmk_api.Section) -> DiscoveryResult:
    for result in section:
        for test in result.tests:
            yield Service(item=_item(result, test))


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


def check(item: str, params: Params, section: robotmk_api.Section) -> CheckResult:
    for result in section:
        for test in result.tests:
            if _item(result, test) == item:
                yield from _check_test(params, test)


register.check_plugin(
    name="robotmk",
    sections=["robotmk_v2"],
    service_name="%s",
    discovery_function=discover,
    check_function=check,
    check_ruleset_name="robotmk",
    check_default_parameters=DEFAULT,
)
