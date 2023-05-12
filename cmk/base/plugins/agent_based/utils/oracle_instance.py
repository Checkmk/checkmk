#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from typing import Mapping, Optional, Union

from pydantic import BaseModel


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
