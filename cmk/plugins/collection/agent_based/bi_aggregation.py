#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, TypedDict

from cmk.checkengine.checkresults import state_markers  # pylint: disable=cmk-module-layer-violation

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


class ErrorInfo(TypedDict, total=False):
    state: int
    output: str


class CustomInfo(TypedDict, total=False):
    output: str


class AggrInfos(TypedDict, total=False):
    error: ErrorInfo
    custom: CustomInfo


Infos = tuple[AggrInfos, Sequence["Infos"]]


@dataclass
class Aggregation:
    error_state: int | None = None
    error_output: str | None = None
    custom_output: str | None = None
    children: list["Aggregation"] = field(default_factory=list)


@dataclass
class AggregationError:
    output: str
    affects_state: bool


def parse_bi_aggregation(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        parsed.update(ast.literal_eval(line[0]))
    return parsed


agent_section_bi_aggregation = AgentSection(
    name="bi_aggregation",
    parse_function=parse_bi_aggregation,
)


def discover_bi_aggregation(section: Section) -> DiscoveryResult:
    for aggr_name in section:
        yield Service(item=aggr_name)


def get_aggregations(infos: Infos) -> Aggregation:
    own_infos, nested_infos = infos

    return Aggregation(
        error_state=own_infos.get("error", {}).get("state"),
        error_output=own_infos.get("error", {}).get("output"),
        custom_output=own_infos.get("custom", {}).get("output"),
        children=[get_aggregations(nested_info) for nested_info in nested_infos],
    )


def get_aggregation_errors(
    aggr: Aggregation, parent_affects_state: bool
) -> Iterator[AggregationError]:
    affects_state = aggr.error_state is not None and parent_affects_state

    if aggr.error_state is not None:
        yield AggregationError(
            output=f"{state_markers[aggr.error_state]} {aggr.error_output}",
            affects_state=affects_state,
        )

    if aggr.custom_output is not None:
        yield AggregationError(output=aggr.custom_output, affects_state=affects_state)

    for child in aggr.children:
        if errors := list(get_aggregation_errors(child, affects_state)):
            yield AggregationError(
                output=f"+-- {errors[0].output}", affects_state=errors[0].affects_state
            )

            for error in errors[1:]:
                yield AggregationError(
                    output=f"| {error.output}", affects_state=error.affects_state
                )


def check_bi_aggregation(item: str, section: Section) -> CheckResult:
    if not (bi_data := section.get(item)):
        return

    overall_state = bi_data["state_computed_by_agent"]
    # The state of an aggregation may be PENDING (-1). Map it to OK.
    bi_state_map = {
        0: "Ok",
        1: "Warning",
        2: "Critical",
        3: "Unknown",
        -1: "Pending",
    }
    yield Result(
        state=State(0 if overall_state == -1 else overall_state),
        summary="Aggregation state: %s" % bi_state_map[overall_state],
    )

    yield Result(
        state=State.OK,
        summary="In downtime: %s" % ("yes" if bi_data["in_downtime"] else "no"),
    )
    yield Result(
        state=State.OK,
        summary="Acknowledged: %s" % ("yes" if bi_data["acknowledged"] else "no"),
    )

    if bi_data["infos"]:
        aggregations = get_aggregations(bi_data["infos"])
        errors = list(get_aggregation_errors(aggregations, bool(overall_state)))

        errors_affecting_state = [error.output for error in errors if error.affects_state]
        other_errors = [error.output for error in errors if not error.affects_state]

        infos = []
        if errors_affecting_state:
            infos.extend(["", "Aggregation problems affecting the state:"])
            infos.extend(errors_affecting_state)

        if other_errors:
            infos.extend(["", "Aggregation problems not affecting the state:"])
            infos.extend(other_errors)

        yield Result(state=State.OK, notice="\n".join(infos))


check_plugin_bi_aggregation = CheckPlugin(
    name="bi_aggregation",
    service_name="Aggr %s",
    discovery_function=discover_bi_aggregation,
    check_function=check_bi_aggregation,
)
