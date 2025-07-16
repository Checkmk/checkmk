#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, field_validator


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
    archiver: str | None = None
    up_seconds: int | None = None
    log_mode: str | None = None
    database_role: str | None = None
    force_logging: str | None = None
    name: str | None = None
    db_creation_time: str | None = None
    pluggable: str = "FALSE"
    con_id: str | None = None
    pname: str | None = None
    popenmode: str | None = None
    prestricted: str | None = None
    ptotal_size: int | None = None
    pup_seconds: int | None = None
    host_name: str | None = None
    old_agent: bool = False

    @field_validator(
        # all fields with `| None` ...
        "archiver",
        "up_seconds",
        "log_mode",
        "database_role",
        "force_logging",
        "name",
        "db_creation_time",
        "con_id",
        "pname",
        "popenmode",
        "prestricted",
        "ptotal_size",
        "pup_seconds",
        "host_name",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "":
            # ... should accept an empty string as None:
            return None
        return v

    @property
    def pdb(self) -> bool:
        # possible multitenant entry?
        # every pdb has a con_id != 0
        return self.pluggable == "TRUE" and self.con_id != "0"

    @property
    def item_name(self) -> str:
        # Multitenant use DB_NAME.PDB_NAME as Service
        return f"{self.sid}.{self.pname}" if self.pdb else self.sid

    @property
    def type(self) -> Literal["PDB", "CDB", "Database"]:
        if self.pdb:
            return "PDB"
        if self.pluggable.lower() == "true":
            return "CDB"
        return "Database"

    @property
    def display_name(self) -> str:
        return f"{self.name}.{self.pname}" if self.pdb else str(self.name)


Section = Mapping[str, InvalidData | GeneralError | Instance]
