#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from datetime import datetime
from typing import Mapping, NamedTuple, Optional, Sequence

from pyasn1.type.useful import GeneralizedTime  # type: ignore[import]
from pydantic import BaseModel, validator

CheckmkSection = Mapping[str, Optional[str]]
CmkUpdateAgentStatus = Mapping[str, str]


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


class CertInfo(BaseModel):
    corrupt: bool
    # if the cert is corrupt these will be None
    not_after: datetime | None
    signature_algorithm: str | None
    common_name: str | None

    @validator("not_after", pre=True)
    @classmethod
    def _asn1_generalizedtime_to_datetime(cls, value: str | datetime | None) -> datetime | None:
        """convert not_after from ASN.1 GENERALIZEDTIME to datetime

        >>> CertInfo._asn1_generalizedtime_to_datetime(None)
        >>> CertInfo._asn1_generalizedtime_to_datetime("20521211091126Z").isoformat()
        '2052-12-11T09:11:26+00:00'
        >>> CertInfo._asn1_generalizedtime_to_datetime("20150131143554.230Z").isoformat()
        '2015-01-31T14:35:54.230000+00:00'
        >>> CertInfo._asn1_generalizedtime_to_datetime("2015013114-0130").isoformat()
        '2015-01-31T14:00:00-01:30'
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value

        asn_time = GeneralizedTime(value).asDateTime
        # We __might__ get an aware or naive datetime object. That makes it
        # hard to compare later on, so lets make all aware. We probably only
        # get aware datetime objects, but who knows for sure? So in the
        # unlikely event of no timezone information, we use the local timezone.

        if asn_time.tzinfo is None:
            return asn_time.astimezone()
        return asn_time


class CMKAgentUpdateSection(BaseModel):
    """The data of the cmk_update_agent"""

    aghash: str | None
    error: str | None
    last_check: float | None
    last_update: float | None
    pending_hash: str | None
    update_url: str | None

    # Added with 2.2
    trusted_certs: dict[int, CertInfo] | None = None

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
