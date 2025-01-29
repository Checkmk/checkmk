#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Final

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.lib.oracle_instance import GeneralError, Instance, InvalidData, Section

# <<<oracle_instance:sep(124)>>>
# XE|11.2.0.2.0|OPEN|ALLOWED|STOPPED|3524|2752243048|NOARCHIVELOG|PRIMARY|NO|XE|080220151025
# last entry: db creation time 'ddmmyyyyhh24mi'


_OUTPUT_HEADERS: Final[Mapping[tuple[int, bool], Sequence[str]]] = {
    (6, False): ("sid", "version", "openmode", "logins"),  # rest is ignored
    (11, True): (
        "sid",
        "version",
        "openmode",
        "logins",
        "archiver",
        "up_seconds",
        "_dbid",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
    ),
    (12, True): (
        "sid",
        "version",
        "openmode",
        "logins",
        "archiver",
        "up_seconds",
        "_dbid",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
        "host_name",
    ),
    (12, False): (
        "sid",
        "version",
        "openmode",
        "logins",
        "archiver",
        "up_seconds",
        "_dbid",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
        "db_creation_time",
    ),
    (13, False): (
        "sid",
        "version",
        "openmode",
        "logins",
        "archiver",
        "up_seconds",
        "_dbid",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
        "db_creation_time",
        "host_name",
    ),
    (22, False): (
        "sid",
        "version",
        "openmode",
        "logins",
        "archiver",
        "up_seconds",
        "_dbid",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
        "db_creation_time",
        "pluggable",
        "con_id",
        "pname",
        "_pdbid",
        "popenmode",
        "prestricted",
        "ptotal_size",
        "_prerecovery_status",
        "pup_seconds",
        "_pblock_size",
    ),
    (23, False): (
        "sid",
        "version",
        "openmode",
        "logins",
        "archiver",
        "up_seconds",
        "_dbid",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
        "db_creation_time",
        "pluggable",
        "con_id",
        "pname",
        "_pdbid",
        "popenmode",
        "prestricted",
        "ptotal_size",
        "_prerecovery_status",
        "pup_seconds",
        "_pblock_size",
        "host_name",
    ),
}


def _parse_agent_line(line: Sequence[str]) -> InvalidData | GeneralError | Instance:
    sid = line[0]

    # In case of a general error (e.g. authentication failed), the second
    # column contains the word "FAILURE"
    if general_error := " ".join(line[2:]) if line[1] == "FAILURE" else None:
        return GeneralError(
            sid=sid,
            error=general_error,
        )

    length = len(line)
    is_asm = length in (11, 12) and line[8] == "ASM"

    try:
        header = _OUTPUT_HEADERS[(length, is_asm)]
    except KeyError:
        return InvalidData(sid=sid, error="Invalid data from agent")

    raw = ((k, v) for k, v in zip(header, line) if not k.startswith("_"))
    instance = Instance.model_validate(dict(raw, old_agent=length == 6))

    if instance.pdb:
        assert instance.popenmode is not None
        instance.logins = "RESTRICTED" if str(instance.prestricted).lower() == "no" else "ALLOWED"
        instance.openmode = instance.popenmode
        instance.up_seconds = instance.pup_seconds

    return instance


def parse_oracle_instance(string_table: StringTable) -> Section:
    return {
        data.item_name: data
        for line in string_table
        if (
            line
            # Skip ORA- error messages from broken old oracle agent
            # <<<oracle_instance:sep(124)>>>
            # ORA-99999 tnsping failed for +ASM1
            and not (line[0].startswith("ORA-") and line[0][4].isdigit() and len(line[0]) < 16)
            and not len(line) == 1
        )
        for data in [_parse_agent_line(line)]
    }


agent_section_oracle_instance = AgentSection(
    name="oracle_instance",
    parse_function=parse_oracle_instance,
)
