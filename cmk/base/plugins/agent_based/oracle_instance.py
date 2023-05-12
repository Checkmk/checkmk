#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Final, Mapping, Optional, Sequence, Union

from pydantic import BaseModel

from .agent_based_api.v1 import register, TableRow
from .agent_based_api.v1.type_defs import InventoryResult, StringTable

# <<<oracle_instance:sep(124)>>>
# XE|11.2.0.2.0|OPEN|ALLOWED|STOPPED|3524|2752243048|NOARCHIVELOG|PRIMARY|NO|XE|080220151025
# last entry: db creation time 'ddmmyyyyhh24mi'


@dataclasses.dataclass(frozen=True)
class InvalidData:
    sid: str
    error: str

    @property
    def item_name(self) -> str:
        return self.sid


@dataclasses.dataclass(frozen=True)
class GeneralError:
    sid: str
    error: str

    @property
    def item_name(self) -> str:
        return self.sid


class Instance(BaseModel):
    sid: str
    version: str
    openmode: str
    logins: str
    archiver: Optional[str] = None
    up_seconds: Optional[int] = None
    log_mode: Optional[str] = None
    database_role: Optional[str] = None
    force_logging: Optional[str] = None
    name: Optional[str] = None
    db_creation_time: Optional[str] = None
    pluggable: str = "FALSE"
    con_id: Optional[str] = None
    pname: Optional[str] = None
    popenmode: Optional[str] = None
    prestricted: Optional[str] = None
    ptotal_size: Optional[int] = None
    pup_seconds: Optional[int] = None
    host_name: Optional[str] = None
    old_agent: bool = False

    @property
    def pdb(self) -> bool:
        # possible multitenant entry?
        # every pdb has a con_id != 0
        return self.pluggable == "TRUE" and self.con_id != "0"

    @property
    def item_name(self) -> str:
        # Multitenant use DB_NAME.PDB_NAME as Service
        return f"{self.sid}.{self.pname}" if self.pdb else self.sid


Section = Mapping[str, Union[InvalidData, GeneralError, Instance]]


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


def _parse_agent_line(line: Sequence[str]) -> Union[InvalidData, GeneralError, Instance]:
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
    instance = Instance.parse_obj(dict(raw, old_agent=length == 6))

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
            and (data := _parse_agent_line(line))
        )
    }


register.agent_section(
    name="oracle_instance",
    parse_function=parse_oracle_instance,
)


def _parse_raw_db_creation_time(raw_str: Optional[str]) -> Optional[str]:
    """ "%d%m%Y%H%M%S" => "%Y-%m-%d %H:%M"

    >>> _parse_raw_db_creation_time("080220151025")
    '2015-02-08 10:25'

    """

    if not (isinstance(raw_str, str) and raw_str.isdigit() and len(raw_str) == 12):
        return None

    return f"{raw_str[4:8]}-{raw_str[2:4]}-{raw_str[:2]} {raw_str[8:10]}:{raw_str[10:]}"


def inventory_oracle_instance(section: Section) -> InventoryResult:
    path = ["software", "applications", "oracle", "instance"]

    for item_data in section.values():
        if isinstance(
            item_data,
            InvalidData,
        ):
            continue

        if isinstance(
            item_data,
            GeneralError,
        ):
            yield TableRow(
                path=path,
                key_columns={"sid": item_data.sid},
                inventory_columns={
                    "pname": None,
                    "version": None,
                    "openmode": None,
                    "logmode": None,
                    "logins": None,
                    "db_creation_time": None,
                },
            )
            continue

        yield TableRow(
            path=path,
            key_columns={"sid": item_data.sid},
            inventory_columns={
                "pname": item_data.pname,
                "version": item_data.version,
                "openmode": item_data.openmode,
                "logmode": item_data.log_mode,
                "logins": item_data.logins,
                "db_creation_time": _parse_raw_db_creation_time(item_data.db_creation_time),
            },
            status_columns={
                "db_uptime": item_data.up_seconds,
                "host": item_data.host_name,
            },
        )


register.inventory_plugin(
    name="oracle_instance",
    inventory_function=inventory_oracle_instance,
)
