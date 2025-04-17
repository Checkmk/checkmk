#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, UTC
from enum import StrEnum
from typing import NamedTuple

from pyasn1.error import PyAsn1Error
from pyasn1.type.useful import GeneralizedTime
from pydantic import BaseModel, Field, field_validator

CheckmkSection = Mapping[str, str | None]
CmkUpdateAgentStatus = Mapping[str, str]


class Plugin(NamedTuple):
    name: str
    version: str
    version_int: int | None
    cache_interval: int | None


class PluginSection(NamedTuple):
    plugins: Sequence[Plugin]
    local_checks: Sequence[Plugin]


class CachedPluginType(StrEnum):
    PLUGIN = "plugins"
    LOCAL = "local"
    ORACLE = "oracle"
    MRPE = "mrpe"


def render_plugin_type(plugin_type: CachedPluginType) -> str:
    match plugin_type:
        case CachedPluginType.MRPE:
            return "MRPE plug-in"
        case CachedPluginType.PLUGIN:
            return "Agent plug-in"
        case CachedPluginType.LOCAL:
            return "Local check"
        case CachedPluginType.ORACLE:
            return "mk_oracle plug-in"


class CachedPlugin(NamedTuple):
    plugin_type: CachedPluginType | None
    plugin_name: str
    timeout: int
    pid: int


class CachedPluginsSection(NamedTuple):
    timeout: list[CachedPlugin] | None
    # "killfailed" has been removed from the agent in 2.4
    # Currently it is still used by mk_oracle
    killfailed: list[CachedPlugin] | None


class CertInfoController(BaseModel):
    to: datetime
    issuer: str

    @field_validator("to", mode="before")
    def _parse_cert_validity(cls, value: str | datetime) -> datetime:
        return (
            value
            if isinstance(value, datetime)
            else datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z")
        )


class LocalConnectionStatus(BaseModel):
    cert_info: CertInfoController


class Connection(BaseModel):
    site_id: str | None = Field(None)
    coordinates: str | None = Field(None)  # legacy from 2.1
    local: LocalConnectionStatus

    def get_site_id(self) -> str | None:
        if self.site_id:
            return self.site_id
        if self.coordinates:
            return self._coordinates_to_site_id(self.coordinates)
        return None

    @staticmethod
    def _coordinates_to_site_id(coordinates: str) -> str:
        """
        >>> Connection._coordinates_to_site_id("localhost:8000/site")
        'localhost/site'
        """
        server_port, site = coordinates.split("/")
        server, _port = server_port.split(":")
        return f"{server}/{site}"


class ControllerSection(BaseModel):
    allow_legacy_pull: bool
    agent_socket_operational: bool = True
    ip_allowlist: Sequence[str] = []
    connections: Sequence[Connection]


class CertInfo(BaseModel):
    corrupt: bool
    # if the cert is corrupt these will be None
    not_after: datetime | None = Field(None)
    signature_algorithm: str | None = Field(None)
    common_name: str | None = Field(None)

    @field_validator("not_after", mode="before")
    def _validate_not_after(cls, value: str | datetime | None) -> datetime | None:
        """convert not_after from str to datetime

        the datetime might be encoded in isoformat or ASN.1 GENERALIZEDTIME
        >>> CertInfo._validate_not_after(None)
        >>> CertInfo._validate_not_after("20521211091126Z").isoformat()
        '2052-12-11T09:11:26+00:00'

        # fromisoformat is also "able" to parse that without error, but wrong...
        # This will ensure it is parsed correctly
        >>> CertInfo._validate_not_after("20010601111300Z").isoformat()
        '2001-06-01T11:13:00+00:00'

        # This is naive, so we set the local timezone. Testing is in whatever
        # timezone so elipsis it is
        >>> CertInfo._validate_not_after("2023-12-20T09:22:17").isoformat()
        '2023-12-20T09:22:17...'
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value

        # Order matters, fromisoformat will parse "20010601111300Z" to 11:30 o'clock which is wrong...
        try:
            dt = CertInfo._asn1_generalizedtime_to_datetime(value)
        except PyAsn1Error:
            dt = datetime.fromisoformat(value)

        # We _should_ only get timezone aware datetimes here. If it's naive anyway, assume UTC.
        if dt.tzinfo is None:
            dt.replace(tzinfo=UTC)

        return dt

    @classmethod
    def _asn1_generalizedtime_to_datetime(cls, value: str) -> datetime:
        """convert not_after from ASN.1 GENERALIZEDTIME to datetime

        >>> CertInfo._asn1_generalizedtime_to_datetime("20521211091126Z").isoformat()
        '2052-12-11T09:11:26+00:00'
        >>> CertInfo._asn1_generalizedtime_to_datetime("20150131143554.230Z").isoformat()
        '2015-01-31T14:35:54.230000+00:00'
        >>> CertInfo._asn1_generalizedtime_to_datetime("2015013114-0130").isoformat()
        '2015-01-31T14:00:00-01:30'
        """

        return GeneralizedTime(value).asDateTime


class CMKAgentUpdateSection(BaseModel):
    """The data of the cmk_update_agent"""

    aghash: str | None = Field(None)
    error: str | None = Field(None)
    last_check: float | None = Field(None)
    last_update: float | None = Field(None)
    pending_hash: str | None = Field(None)
    update_url: str | None = Field(None)

    # Added with 2.2
    trusted_certs: dict[int, CertInfo] | None = Field(None)

    # Added with 2.5
    host_name: str | None = Field(None)

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
        parsed = cls.model_validate({k: v if v != "None" else None for k, v in zip(parts, parts)})
        parsed.error = error.strip() if error is not None else None
        return parsed
