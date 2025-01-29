#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping
from typing import NamedTuple

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
from cmk.plugins.lib import megaraid


class StorcliPDisk(NamedTuple):
    state: str
    size: tuple[float, str]


Section = Mapping[str, StorcliPDisk]


class Table(NamedTuple):
    name: str
    header: list[str]
    body: StringTable


def is_table_marker(line: list[str]) -> bool:
    return _is_marker("-", line)


def is_section_marker(line: list[str]) -> bool:
    return _is_marker("=", line)


def _is_marker(marker: str, line: list[str]) -> bool:
    if len(line) == 1 and (string := line[0]):
        return string.count(marker) == len(string)
    return False


def parse_table(lines: Iterator[list[str]], name: str) -> Table:
    table_marker = next(lines)
    assert is_table_marker(table_marker)

    table_header = next(lines)

    table_marker = next(lines)
    assert is_table_marker(table_marker)

    table_body = []
    for line in lines:
        if is_table_marker(line):
            break
        table_body.append(line)
    return Table(name, table_header, table_body)


def parse_tables(string_table: StringTable) -> list[Table]:
    tables = []
    current_section = None

    lines = iter(string_table)
    prev_line = [""]

    for line in lines:
        if is_section_marker(line):
            current_section = " ".join(prev_line).rstrip(": ")
            tables.append(parse_table(lines, current_section))
        prev_line = line

    return tables


def parse_storcli_pdisks(string_table: StringTable) -> Section:
    tables = parse_tables(string_table)

    controller_num = 0
    section = {}
    for table in tables:
        if table.name != "Drive Information":
            continue
        if table.header[:6] == ["EID:Slt", "PID", "State", "Status", "DG", "Size"]:
            for line in table.body:
                # size is split into two elements:
                eid_and_slot, device_id, state, _status, _driver_group, size, size_unit = line[:7]
                item_name = "C%i.%s-%s" % (controller_num, eid_and_slot, device_id)
                section[item_name] = StorcliPDisk(
                    state=megaraid.expand_abbreviation(state),
                    size=(float(size), size_unit),
                )
        else:
            for line in table.body:
                eid_and_slot, device, state, _drivegroup, size, size_unit = line[:6]
                item_name = "C%i.%s-%s" % (controller_num, eid_and_slot, device)
                section[item_name] = StorcliPDisk(
                    state=megaraid.expand_abbreviation(state),
                    size=(float(size), size_unit),
                )
        controller_num += 1
    return section


agent_section_storcli_pdisks = AgentSection(
    name="storcli_pdisks",
    parse_function=parse_storcli_pdisks,
)


def discover_storcli_pdisks(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_storcli_pdisks(
    item: str,
    params: Mapping[str, int],
    section: Section,
) -> CheckResult:
    if item not in section:
        return

    size = section[item].size
    infotext = f"Size: {size[0]} {size[1]}"

    diskstate = section[item].state
    infotext += ", Disk State: %s" % diskstate

    status = params.get(diskstate, 3)

    yield Result(state=State(status), summary=infotext)


check_plugin_storcli_pdisks = CheckPlugin(
    name="storcli_pdisks",
    service_name="RAID PDisk EID:Slot-Device %s",
    discovery_function=discover_storcli_pdisks,
    check_function=check_storcli_pdisks,
    check_default_parameters=megaraid.PDISKS_DEFAULTS,
    check_ruleset_name="storcli_pdisks",
)
