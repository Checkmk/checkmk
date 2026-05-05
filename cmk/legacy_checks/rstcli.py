#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import Any

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

type Section = Mapping[str, Mapping[str, Any]]


def parse_rstcli_sections(
    info: StringTable,
) -> Generator[tuple[str, list[list[str]]] | None]:
    current_section: tuple[str, list[list[str]]] | None = None
    for line in info:
        if line[0].startswith("--"):
            if current_section is not None:
                yield current_section
            current_section = (":".join(line).strip("-").strip(), [])
        elif len(line) < 2:
            # On some systems, there are lines that only consist of
            # a contextless 0. Skip those to avoid parsing errors later.
            continue
        else:
            if current_section is None:
                raise ValueError(" ".join(line))
            current_section[1].append(line)

    yield current_section


# interpret the volumes section
def parse_rstcli_volumes(rows: list[list[str]]) -> dict[str, dict[str, Any]]:
    volumes: dict[str, dict[str, Any]] = {}
    current_volume: dict[str, Any] = {}

    for row in rows:
        if row[0] == "Name":
            current_volume = {}
            volumes[row[1].strip()] = current_volume
        else:
            current_volume[row[0]] = row[1].strip()

    return volumes


# interpret the disks section
def parse_rstcli_disks(rows: list[list[str]]) -> list[dict[str, str]]:
    disks: list[dict[str, str]] = []
    current_disk: dict[str, str] = {}

    for row in rows:
        if row[0] == "ID":
            current_disk = {}
            disks.append(current_disk)

        current_disk[row[0]] = row[1].strip()

    return disks


def parse_rstcli(string_table: StringTable) -> Section:
    if string_table == [["rstcli not found"]]:
        return {}

    volumes: dict[str, dict[str, Any]] = {}
    for section in parse_rstcli_sections(string_table):
        if section is None:
            continue
        if section[0] == "VOLUME INFORMATION":
            volumes.update(parse_rstcli_volumes(section[1]))
        elif section[0].startswith("DISKS IN VOLUME"):
            volume = section[0].split(":")[1].strip()
            volumes[volume]["Disks"] = parse_rstcli_disks(section[1])
        else:
            raise ValueError("invalid section in rstcli output: %s" % section[0])

    return volumes


def discover_rstcli(section: Section) -> DiscoveryResult:
    yield from [Service(item=name) for name in section]


# Help! There is no documentation, what are the possible values?
rstcli_states = {
    "Normal": State.OK,
}


def check_rstcli(item: str, section: Section) -> CheckResult:
    if not (volume := section.get(item)):
        return
    yield Result(
        state=rstcli_states.get(volume["State"], State.UNKNOWN),
        summary=(
            f"RAID {volume['Raid Level']}, "
            f"{int(volume['Num Disks'])} disks ({volume['Size']}), "
            f"state {volume['State']}"
        ),
    )


agent_section_rstcli = AgentSection(
    name="rstcli",
    parse_function=parse_rstcli,
)


check_plugin_rstcli = CheckPlugin(
    name="rstcli",
    service_name="RAID Volume %s",
    discovery_function=discover_rstcli,
    check_function=check_rstcli,
)


def discover_rstcli_pdisks(section: Section) -> DiscoveryResult:
    for key, volume in section.items():
        for disk in volume["Disks"]:
            yield Service(item="{}/{}".format(key, disk["ID"]))


def check_rstcli_pdisks(item: str, section: Section) -> CheckResult:
    volume, disk_id = item.rsplit("/", 1)

    disks = section.get(volume, {}).get("Disks", [])
    for disk in disks:
        if disk["ID"] == disk_id:
            infotext = (
                f"{disk['State']} (unit: {volume}, size: {disk['Size']}, "
                f"type: {disk['Disk Type']}, model: {disk['Model']}, "
                f"serial: {disk['Serial Number']})"
            )
            yield Result(state=rstcli_states.get(disk["State"], State.CRIT), summary=infotext)
            return


check_plugin_rstcli_pdisks = CheckPlugin(
    name="rstcli_pdisks",
    service_name="RAID Disk %s",
    sections=["rstcli"],
    discovery_function=discover_rstcli_pdisks,
    check_function=check_rstcli_pdisks,
)
