#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import assert_never, Iterable, TypedDict

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.cisco_sma.agent_based.detect import DETECT_CISCO_SMA_SNMP


class MailTransferMemoryStatus(Enum):
    memory_available = 1
    memory_shortage = 2
    memory_full = 3


class Params(TypedDict):
    monitoring_status_memory_available: int
    monitoring_status_memory_shortage: int
    monitoring_status_memory_full: int


def _check_mail_transfer_memory(params: Params, section: MailTransferMemoryStatus) -> CheckResult:
    match section:
        case MailTransferMemoryStatus.memory_available:
            yield Result(
                state=State(params["monitoring_status_memory_available"]),
                summary="Memory available",
            )
        case MailTransferMemoryStatus.memory_shortage:
            yield Result(
                state=State(params["monitoring_status_memory_shortage"]), summary="Memory shortage"
            )
        case MailTransferMemoryStatus.memory_full:
            yield Result(
                state=State(params["monitoring_status_memory_full"]), summary="Memory full"
            )
        case _:
            assert_never(section)


def _discover_mail_transfer_memory(section: MailTransferMemoryStatus) -> Iterable[Service]:
    yield Service()


check_plugin_check_mail_transfer_memory = CheckPlugin(
    name="cisco_sma_mail_transfer_memory",
    service_name="Mail transfer memory",
    discovery_function=_discover_mail_transfer_memory,
    check_function=_check_mail_transfer_memory,
    check_ruleset_name="cisco_sma_mail_transfer_memory",
    check_default_parameters=Params(
        monitoring_status_memory_available=State.OK.value,
        monitoring_status_memory_shortage=State.WARN.value,
        monitoring_status_memory_full=State.CRIT.value,
    ),
)


def _parse_mail_transfer_memory(string_table: StringTable) -> MailTransferMemoryStatus | None:
    if not string_table or not string_table[0]:
        return None

    return MailTransferMemoryStatus(int(string_table[0][0]))


snmp_section_mail_transfer_memory = SimpleSNMPSection(
    parsed_section_name="cisco_sma_mail_transfer_memory",
    name="cisco_sma_mail_transfer_memory",
    detect=DETECT_CISCO_SMA_SNMP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.15497.1.1.1",
        oids=["7"],
    ),
    parse_function=_parse_mail_transfer_memory,
)
