#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from typing import Self


class IPAddressFamily(StrEnum):
    IPv4 = "ipv4"
    IPv6 = "ipv6"


@dataclass(frozen=True)
class HostConfig:
    name: str
    address: str
    alias: str
    ip_family: IPAddressFamily
    ipv4address: IPv4Address | None
    ipv6address: IPv6Address | None
    additional_ipv4addresses: Sequence[IPv4Address]
    additional_ipv6addresses: Sequence[IPv6Address]

    @property
    def all_ipv4addresses(self):
        if self.ipv4address:
            return [self.ipv4address, *self.additional_ipv4addresses]
        return self.additional_ipv4addresses

    @property
    def all_ipv6addresses(self):
        if self.ipv6address:
            return [self.ipv6address, *self.additional_ipv6addresses]
        return self.additional_ipv6addresses


@dataclass(frozen=True)
class HTTPProxy:
    name: str
    url: str


@dataclass(frozen=True)
class EnvironmentConfig:
    http_proxies: Mapping[str, HTTPProxy]


class SecretType(StrEnum):
    STORE = "store"
    PASSWORD = "password"


@dataclass(frozen=True)
class Secret:
    type: SecretType
    value: str
    format: str = "%s"

    @classmethod
    def from_config(cls, secret: tuple[str, str], secret_format: str = "%s") -> Self:
        return cls(type=SecretType(secret[0]), value=secret[1], format=secret_format)
