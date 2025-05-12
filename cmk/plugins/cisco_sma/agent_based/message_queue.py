#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass
from enum import Enum
from typing import assert_never, TypedDict

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

from .detect import DETECT_CISCO_SMA


class QueueAvailabilityStatus(Enum):
    queue_space_available = 1
    queue_space_shortage = 2
    queue_full = 3


@dataclass(frozen=True)
class Queue(BaseModel):
    utilization: float
    availability_status: QueueAvailabilityStatus
    length: int
    oldest_message_age: float


def _parse_message_queue(string_table: StringTable) -> Queue | None:
    if not string_table or not string_table[0]:
        return None

    data = string_table[0]

    return Queue(
        utilization=float(data[0]),
        availability_status=QueueAvailabilityStatus(int(data[1])),
        length=int(data[2]),
        oldest_message_age=float(data[3]),
    )


snmp_section_message_queue = SimpleSNMPSection(
    parsed_section_name="cisco_sma_message_queue",
    name="cisco_sma_message_queue",
    detect=DETECT_CISCO_SMA,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["4", "5", "11", "14"],
    ),
    parse_function=_parse_message_queue,
)


class Params(TypedDict):
    monitoring_status_memory_available: int
    monitoring_status_memory_shortage: int
    monitoring_status_queue_full: int
    levels_queue_utilization: SimpleLevelsConfigModel[float]
    levels_queue_length: SimpleLevelsConfigModel[int]
    levels_oldest_message_age: SimpleLevelsConfigModel[float]


def _check_message_queue(params: Params, section: Queue) -> CheckResult:
    match section.availability_status:
        case QueueAvailabilityStatus.queue_space_available:
            yield Result(
                state=State(params["monitoring_status_memory_available"]),
                summary="Memory available",
            )
        case QueueAvailabilityStatus.queue_space_shortage:
            yield Result(
                state=State(params["monitoring_status_memory_shortage"]),
                summary="Memory shortage",
            )
        case QueueAvailabilityStatus.queue_full:
            yield Result(state=State(params["monitoring_status_queue_full"]), summary="Memory full")
        case _:
            assert_never(section.availability_status)

    yield from check_levels(
        section.utilization,
        label="Utilization",
        render_func=render.percent,
        metric_name="cisco_sma_queue_utilization",
        levels_upper=params["levels_queue_utilization"],
    )

    yield from check_levels(
        section.length,
        label="Total messages",
        metric_name="cisco_sma_queue_length",
        levels_upper=params["levels_queue_length"],
        render_func=lambda x: str(int(x)),
    )

    yield from check_levels(
        section.oldest_message_age,
        label="Oldest message age",
        metric_name="cisco_sma_queue_oldest_message_age",
        levels_upper=params["levels_oldest_message_age"],
        render_func=render.timespan,
    )


def _discover_message_queue(section: Queue) -> DiscoveryResult:
    yield Service()


check_plugin_message_queue = CheckPlugin(
    name="cisco_sma_message_queue",
    service_name="Queue",
    discovery_function=_discover_message_queue,
    check_function=_check_message_queue,
    check_ruleset_name="cisco_sma_message_queue",
    check_default_parameters=Params(
        monitoring_status_memory_available=State.OK.value,
        monitoring_status_memory_shortage=State.WARN.value,
        monitoring_status_queue_full=State.CRIT.value,
        levels_queue_utilization=("fixed", (80.0, 90.0)),
        levels_queue_length=("fixed", (500, 1000)),
        levels_oldest_message_age=("no_levels", None),
    ),
)
