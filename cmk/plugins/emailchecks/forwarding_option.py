#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from pydantic import BaseModel

ECForwarding = (
    tuple[Literal["local"], Literal[""]]
    | tuple[Literal["socket"], str]
    | tuple[Literal["spool_local"], Literal[""]]
    | tuple[Literal["spool"], str]
)


class SyslogForwarding(BaseModel):
    protocol: Literal["udp", "tcp"]
    address: str
    port: int


Method = tuple[Literal["ec"], ECForwarding] | tuple[Literal["syslog"], SyslogForwarding]


class ForwardingOptions(BaseModel):
    method: Method | None = None
    match_subject: str | None = None
    facility: tuple[str, int] | None = None
    application: tuple[Literal["subject"], None] | tuple[Literal["spec"], str] | None = None
    host: str | None = None
    body_limit: int | None = None
    cleanup: tuple[Literal["delete"], Literal["delete"]] | tuple[Literal["move"], str] | None = None
