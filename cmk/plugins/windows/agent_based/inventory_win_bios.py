#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from contextlib import suppress
from datetime import datetime, timedelta, timezone

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
)


def _parse_release_date_as_unix_seconds(value: str) -> int:
    """Seconds since the epoch of a CIM_DATETIME, honouring its UTC offset.

    The timestamp is not local time, so it must not be read as such: a BIOS released at
    `20061201000000.000000+000` is 2006-12-01 00:00:00 UTC on every monitoring server,
    whatever timezone the server itself runs in.

    `yyyymmddHHMMSS.mmmmmmsooo` is a fixed width contract, and anything else is rejected
    rather than guessed at. A firmware reports what it does not know as `*`, and since
    the fields run from most to least significant, only trailing ones can be unspecified:
    dropping them and padding with zeros reads Microsoft's own `19980416******.000000+***`
    as midnight UTC on that day, while a `*` with a digit behind it stays rejected instead
    of being resolved into a date nobody reported. Microseconds say nothing about a
    release date, so they are not parsed.
    """
    if len(value) != 25 or value[14] != "." or value[21] not in "+-":
        raise ValueError(f"Invalid CIM_DATETIME: {value!r}")

    date_time = value[:14].rstrip("*").ljust(14, "0")
    # Three digits, so the timedelta below cannot overflow however absurd they are.
    offset_minutes = 0 if value[22:] == "***" else int(value[21:])

    return int(
        datetime.strptime(date_time, "%Y%m%d%H%M%S")
        .replace(tzinfo=timezone(timedelta(minutes=offset_minutes)))
        .timestamp()
    )


def parse_win_bios(string_table: StringTable) -> Mapping[str, int | str]:
    section: dict[str, str | int] = {}
    for line in string_table:
        varname = line[0].strip()
        # Separator : seams not ideal. Some systems have : in the BIOS version
        value = ":".join(line[1:]).lstrip()

        if varname == "BIOSVersion":
            section["version"] = value
        elif varname == "SMBIOSBIOSVersion":
            section["smbios_version"] = value
        elif varname == "SMBIOSMajorVersion":
            section["major_version"] = value
        elif varname == "SMBIOSMinorVersion":
            section["minor_version"] = value
        elif varname == "ReleaseDate":
            # Firmware that does not populate the date at all reports an empty value.
            if value:
                section["date"] = _parse_release_date_as_unix_seconds(value)
        elif varname == "Manufacturer":
            section["vendor"] = value
        elif varname == "Name":
            section["model"] = value

    return section


agent_section_win_bios = AgentSection(
    name="win_bios",
    parse_function=parse_win_bios,
)


def inventory_win_bios(section: Mapping[str, str | int]) -> InventoryResult:
    attr = {k: section[k] for k in ("date", "model", "vendor", "version") if k in section}
    with suppress(KeyError):
        attr["version"] = (
            f"{section['smbios_version']} {section['major_version']}.{section['minor_version']}"
        )

    yield Attributes(
        path=["software", "bios"],
        inventory_attributes=attr,
    )


inventory_plugin_win_bios = InventoryPlugin(
    name="win_bios",
    inventory_function=inventory_win_bios,
)
