#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class IPAddressFamily(StrEnum):
    IPv4 = "ipv4"
    IPv6 = "ipv6"


@dataclass(frozen=True)
class HostConfig:
    name: str
    address: str
    alias: str
    ip_family: IPAddressFamily
    ipv4address: str | None
    ipv6address: str | None
    additional_ipv4addresses: Sequence[str]
    additional_ipv6addresses: Sequence[str]

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
    id: str
    name: str
    url: str


class SecretType(StrEnum):
    STORE = "store"
    PASSWORD = "password"


@dataclass(frozen=True)
class Secret:
    value: str
    format: str = "%s"


@dataclass(frozen=True)
class StoredSecret(Secret):
    pass


@dataclass(frozen=True)
class PlainTextSecret(Secret):
    pass


def get_secret_from_params(secret_type: str, secret_value: str) -> Secret:
    if secret_type == SecretType.STORE:
        return StoredSecret(secret_value)

    if secret_type == SecretType.PASSWORD:
        return PlainTextSecret(secret_value)

    raise ValueError(f"{secret_type} is not a valid secret type")
