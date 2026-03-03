#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from ipaddress import ip_network, IPv4Address, IPv6Address
from typing import override

import pydantic

import cmk.ccc.resulttype as result


class ConfigChoiceHasError(ABC):
    @abstractmethod
    def __call__(self, value: str) -> result.Result[None, str]:
        raise NotImplementedError


class ApacheTCPAddrHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        url = f"http://{value}:80"
        try:
            pydantic.TypeAdapter(pydantic.HttpUrl).validate_python(url)
            return result.OK(None)
        except pydantic.ValidationError as e:
            message = f"""OMD uses APACHE_TCP_ADDR and APACHE_TCP_PORT to construct an Apache
Listen directive. For example, setting APACHE_TCP_PORT to 80 results in: {url}.
This is invalid because of: """
            message += ", ".join([error["ctx"]["error"] for error in e.errors()])
            return result.Error(message)


class IpAddressListHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        ip_addresses = value.split()
        if not ip_addresses:
            return result.Error("Specify at least one IP address.")
        for ip_address in ip_addresses:
            try:
                ip_network(ip_address)
            except ValueError:
                return result.Error(f"The IP address {ip_address} does match the expected format.")
        return result.OK(None)


class IpListenAddressHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        if not value:
            return result.Error("Empty address")

        if value.startswith("[") and value.endswith("]"):
            try:
                IPv6Address(value[1:-1])
                return result.OK(None)
            except ValueError:
                return result.Error("Invalid IPv6 address")

        try:
            IPv4Address(value)
        except ValueError:
            return result.Error("Invalid IPv4 address")

        return result.OK(None)


class NetworkPortHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        try:
            port = int(value)
        except ValueError:
            return result.Error("Invalid port number")

        if port < 1024 or port > 65535:
            return result.Error("Invalid port number")

        return result.OK(None)


class ApacheNetworkPortHasError(ConfigChoiceHasError):
    @override
    def __call__(self, value: str) -> result.Result[None, str]:
        try:
            port = int(value)
        except ValueError:
            return result.Error("Invalid port number")

        if port < 1 or port > 99999:
            return result.Error("Invalid port number")

        return result.OK(None)
