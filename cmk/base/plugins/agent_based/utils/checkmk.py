#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import Mapping, NamedTuple, Optional, Sequence

from pydantic import BaseModel

CheckmkSection = Mapping[str, Optional[str]]


class Plugin(NamedTuple):
    name: str
    version: str
    version_int: Optional[int]
    cache_interval: Optional[int]


class PluginSection(NamedTuple):
    plugins: Sequence[Plugin]
    local_checks: Sequence[Plugin]


class Connection(NamedTuple):
    site_id: str
    valid_for_seconds: float


class ControllerSection(NamedTuple):
    # Currently this is all we need. Extend on demand...
    allow_legacy_pull: bool
    socket_ready: bool
    ip_allowlist: tuple[str, ...]
    connections: Sequence[Connection]


class CMKAgentUpdateSection(BaseModel):
    """The data of the cmk_update_agent"""

    aghash: str | None
    error: str | None
    last_check: float | None
    last_update: float | None
    pending_hash: str | None
    update_url: str

    @classmethod
    def parse_checkmk_section(cls, section: CheckmkSection | None) -> CMKAgentUpdateSection | None:
        if section is None or not (raw_string := section.get("agentupdate")):
            return None

        if "error" in raw_string:
            non_error_part, error = raw_string.split("error", 1)
        else:
            non_error_part = raw_string
            error = None

        parts = iter(non_error_part.split())
        parsed = cls.parse_obj({k: v if v != "None" else None for k, v in zip(parts, parts)})
        parsed.error = error.strip() if error is not None else None
        return parsed
