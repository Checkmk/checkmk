#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from ipaddress import ip_network, IPv4Address, IPv6Address
from pathlib import Path
from re import Pattern
from typing import Protocol

from cmk.ccc.version import Edition

Config = dict[str, str]


class Error(str): ...


class ConfigChoiceHasError(Protocol):
    def __call__(self, value: str) -> None | Error: ...


ConfigHookChoiceItem = tuple[str, str]
ConfigHookChoices = Pattern[str] | list[ConfigHookChoiceItem] | ConfigChoiceHasError


class _NamedSiteActivation(Protocol):
    def __call__(self, site_name: str, site_home: Path, config: Config) -> None: ...


class _UnusedSiteActivation(Protocol):
    def __call__(self, _site_name: str, site_home: Path, config: Config) -> None: ...


Activation = _NamedSiteActivation | _UnusedSiteActivation


def ip_address_list_has_error(value: str) -> None | Error:
    ip_addresses = value.split()
    if not ip_addresses:
        return Error("Specify at least one IP address.")
    for ip_address in ip_addresses:
        try:
            ip_network(ip_address)
        except ValueError:
            return Error(f"The IP address {ip_address} does match the expected format.")
    return None


def ip_listen_address_has_error(value: str) -> None | Error:
    if not value:
        return Error("Empty address")

    if value.startswith("[") and value.endswith("]"):
        try:
            IPv6Address(value[1:-1])
            return None
        except ValueError:
            return Error("Invalid IPv6 address")

    try:
        IPv4Address(value)
    except ValueError:
        return Error("Invalid IPv4 address")

    return None


def network_port_has_error(value: str) -> None | Error:
    try:
        port = int(value)
    except ValueError:
        return Error("Invalid port number")

    if port < 1024 or port > 65535:
        return Error("Invalid port number")

    return None


def null_action(_site_name: str, site_home: Path, config: Config) -> None:
    pass


@dataclass(frozen=True)
class PortHook:
    name: str
    display_name: str
    default_port: int
    activation: Activation
    choices: ConfigHookChoices
    depends: Callable[[Config], bool] = lambda _: True


@dataclass(frozen=True)
class Hook:
    name: str
    default: Callable[[Edition], str]
    activation: Activation
    choices: ConfigHookChoices
    depends: Callable[[Config], bool] = lambda _: True
