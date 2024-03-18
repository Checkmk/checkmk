#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ipaddress import IPv4Address, IPv6Address
from typing import Literal

from pydantic import BaseModel, Field

from livestatus import SiteId

from cmk.utils.config_validation_layer.type_defs import OMITTED_FIELD
from cmk.utils.site import omd_site


class SocketVerify(BaseModel):
    verify: bool


class EmptyDict(BaseModel): ...


PLAIN_TEXT = tuple[Literal["plain_text"], EmptyDict]
ENCRYPTED = tuple[Literal["encrypted"], SocketVerify]
TLS = PLAIN_TEXT | ENCRYPTED


class _Socket(BaseModel):
    tls: TLS


class _SocketTCP4(_Socket):
    address: tuple[IPv4Address, int]


class _SocketTCP6(_Socket):
    address: tuple[IPv6Address, int]


class _Path(BaseModel):
    path: str


USER_SYNC_LDAP_LIST = tuple[Literal["list"], list[str]]
USER_SYNC = USER_SYNC_LDAP_LIST | Literal["all"] | None
TCP4 = tuple[Literal["tcp"], _SocketTCP4]
TCP6 = tuple[Literal["tcp6"], _SocketTCP6]
UNIX = tuple[Literal["unix"], _Path]


class _ProxyParams(BaseModel):
    channels: int = OMITTED_FIELD
    heartbeat: tuple[int, float] = OMITTED_FIELD
    channel_timeout: float = OMITTED_FIELD
    query_timeout: float = OMITTED_FIELD
    connect_retry: float = OMITTED_FIELD
    cache: bool = OMITTED_FIELD


class _ProxyTcp(BaseModel):
    port: int
    only_from: list[str] = OMITTED_FIELD
    tls: bool = OMITTED_FIELD


class _Proxy(BaseModel):
    params: _ProxyParams | None
    tcp: _ProxyTcp = OMITTED_FIELD


class SiteModel(BaseModel):
    id: str = OMITTED_FIELD
    url_prefix: str
    replication: Literal["slave"] | None
    proxy: _Proxy | None
    user_login: bool
    disable_wato: bool
    disabled: bool
    insecure: bool
    multisiteurl: str
    persist: bool
    replicate_ec: bool
    replicate_mkps: bool = OMITTED_FIELD
    ca_file_path: str = OMITTED_FIELD

    class Config:
        validate_assignment = True


class CentralSiteModel(SiteModel):
    alias: str = Field(default="The central site", min_length=1)
    socket: tuple[Literal["local"], None]
    multisiteurl: str
    replication: None
    timeout: int = Field(ge=0, default=10)
    proxy: _Proxy | None
    secret: str = OMITTED_FIELD


class RemoteSiteModel(SiteModel):
    alias: str = Field(min_length=1)
    socket: TCP4 | TCP6 | UNIX
    timeout: int = Field(ge=0, default=2)
    status_host: tuple[str, str] | None
    user_sync: USER_SYNC
    customer: str = OMITTED_FIELD


def validate_sites(sites: dict) -> dict[SiteId, CentralSiteModel | RemoteSiteModel]:
    return {site_id: validate_site(site_id, site) for site_id, site in sites.items()}


def validate_site(site_id: SiteId, site: dict) -> CentralSiteModel | RemoteSiteModel:
    if site_id == omd_site() or site["socket"] == ("local", None):
        return CentralSiteModel(**site)
    return RemoteSiteModel(**site)
