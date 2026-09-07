#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<ibm_svc_eventlog:sep(58)>>>
# 588:120404112526:mdiskgrp:6:md07_sas10k::alert:no:989001::Managed Disk Group space warning
# 589:120404112851:mdiskgrp:7:md08_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 590:120404112931:mdiskgrp:8:md09_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 591:120404113001:mdiskgrp:9:md10_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 592:120404113026:mdiskgrp:10:md11_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 593:120404113111:mdiskgrp:11:md12_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 1690:130801070656:drive:59:::alert:no:981020::Managed Disk error count warning threshold met
# 2058:131030112416:drive:42:::alert:no:981020::Managed Disk error count warning threshold met

from collections.abc import Sequence
from dataclasses import dataclass

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


@dataclass(frozen=True)
class EventLogEntry:
    description: str


Section = Sequence[EventLogEntry]


def discover_ibm_svc_eventlog(section: Section) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_ibm_svc_eventlog(section: Section) -> CheckResult:
    if section:
        yield Result(
            state=State.WARN,
            summary=(
                f"{len(section)} messages not expired and not yet fixed found in event log, "
                f"last was: {section[-1].description}"
            ),
        )
        return

    yield Result(
        state=State.OK, summary="No messages not expired and not yet fixed found in event log"
    )


def parse_ibm_svc_eventlog(string_table: StringTable) -> Section:
    # Column layout: sequence_number, last_timestamp, object_type, object_id,
    # object_name, copy_id, status, fixed, event_id, error_code, description, ...
    return [EventLogEntry(description=line[10]) for line in string_table if len(line) > 10]


agent_section_ibm_svc_eventlog = AgentSection(
    name="ibm_svc_eventlog",
    parse_function=parse_ibm_svc_eventlog,
)


check_plugin_ibm_svc_eventlog = CheckPlugin(
    name="ibm_svc_eventlog",
    service_name="Eventlog",
    discovery_function=discover_ibm_svc_eventlog,
    check_function=check_ibm_svc_eventlog,
)
