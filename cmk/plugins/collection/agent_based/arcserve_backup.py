#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<arcserve_backup>>>
#
# Job:
# 3960
# Beschreibung: Tagessicherung staging. (27.01.2014)
# 255.154 Verzeichnis(se) 1.400.060 Datei(en) (388,38 GB) auf Datentr�ger gesichert.
# Vorgang Sichern erfolgreich
#
# Job:
# 3954
# Beschreibung: Wochensicherung staging. (24.01.2014)
# 340.611 Verzeichnis(se) 1.726.321 Datei(en) (446,52 GB) auf Datentr�ger gesichert.
# Vorgang Sichern erfolgreich
#
# <<<arcserve_backup>>>
# Job:
# 3972
# Beschreibung: Tagessicherung staging. (30.01.2014)
# 255.641 Verzeichnis(se) 1.405.125 Datei(en) (389,27 GB) auf Datentr�ger gesichert.
# Vorgang Sichern unvollst�ndig.Anzahl an Fehlern/Warnungen: 0/1
#
# Job:
# 3954
# Beschreibung: Wochensicherung staging. (24.01.2014)
# 340.611 Verzeichnis(se) 1.726.321 Datei(en) (446,52 GB) auf Datentr�ger gesichert.
# Vorgang Sichern erfolgreich
#
# <<<arcserve_backup>>>
# Job:
# 3976
# Beschreibung: Wochensicherung staging. (31.01.2014)
# 341.092 Verzeichnis(se) 1.731.713 Datei(en) (447,42 GB) auf Datentr�ger gesichert.
# Vorgang Sichern konnte nicht durchgef�hrt werden.Anzahl an Fehlern/Warnungen: 1/0
#
# Job:
# 3972
# Beschreibung: Tagessicherung staging. (30.01.2014)
# 255.641 Verzeichnis(se) 1.405.125 Datei(en) (389,27 GB) auf Datentr�ger gesichert.
# Vorgang Sichern unvollst�ndig.Anzahl an Fehlern/Warnungen: 0/1

# parses info in a structure like
# parsed = {
#     'Tagessicherung staging': { 'dirs'  : 255641,
#                                 'files' : 1405125,
#                                 'result': 'Sichern unvollst\xc3\xa4ndig.Anzahl an Fehlern/Warnungen: 0/1',
#                                 'size'  : 417975479828},
#     'Wochensicherung staging': {'dirs'  : 341092,
#                                 'files' : 1731713,
#                                 'result': 'Sichern konnte nicht durchgef\xc3\xbchrt werden.Anzahl an Fehlern/Warnungen: 1/0',
#                                 'size'  : 480413566894}}


# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)


class Backup(TypedDict):
    dirs: NotRequired[int]
    files: NotRequired[int]
    size: NotRequired[int]
    result: NotRequired[str]


Section = Mapping[str, Backup]


def parse_arcserve_backup(string_table: StringTable) -> Section:
    unit_factor = {"kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}
    parsed: dict[str, Backup] = {}
    for line in string_table:
        if line[0] == "Beschreibung:":
            backup_id = " ".join(line[1:-1])
            if backup_id[-1] == ".":
                backup_id = backup_id[0:-1]
                backup = Backup()
                parsed[backup_id] = backup
        elif (
            len(line) > 5
            and line[1] == "Verzeichnis(se)"
            and line[3] == "Datei(en)"
            and line[5][-1] == ")"
        ):
            dirs = int(line[0].replace(".", ""))
            files = int(line[2].replace(".", ""))
            unit = line[5].replace(")", "").lower()
            size = int(float(line[4].replace("(", "").replace(",", ".")) * unit_factor[unit])
            backup["dirs"] = dirs
            backup["files"] = files
            backup["size"] = size
        elif len(line) > 1 and line[0] == "Vorgang":
            result = " ".join(line[1:])
            backup["result"] = result
    return parsed


def inventory_arcserve_backup(section: Any) -> DiscoveryResult:
    inventory = []
    for backup in section:
        inventory.append((backup, None))
    yield from [Service(item=item, parameters=parameters) for (item, parameters) in inventory]


def check_arcserve_backup(item: str, section: Any) -> CheckResult:
    if (backup := section.get(item)) is None:
        return

    if "dirs" in backup:
        yield from check_levels(
            backup["dirs"],
            metric_name="dirs",
            render_func=lambda x: f"{x}",
            label="Directories",
        )

    if "files" in section[item]:
        yield from check_levels(
            backup["files"],
            metric_name="files",
            render_func=lambda x: f"{x}",
            label="Files",
        )

    if "size" in section[item]:
        yield from check_levels(
            backup["size"],
            metric_name="size",
            render_func=render.bytes,
            label="Size",
        )

    if (result := backup["result"]).startswith("Sichern erfolgreich"):
        status = State.OK
    elif result.startswith("Sichern unvollst"):
        status = State.WARN
    elif result.startswith("Sichern konnte nicht durchgef"):
        status = State.CRIT
    else:
        yield Result(state=State.UNKNOWN, summary="Unknown result: {result}")
        return

    yield Result(state=status, summary="Result: {result}")


agent_section_arcserve_backup = AgentSection(
    name="arcserve_backup",
    parse_function=parse_arcserve_backup,
)

check_plugin_arcserve_backup = CheckPlugin(
    name="arcserve_backup",
    service_name="Arcserve Backup %s",
    discovery_function=inventory_arcserve_backup,
    check_function=check_arcserve_backup,
)
