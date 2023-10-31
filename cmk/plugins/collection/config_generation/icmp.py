#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from typing import Iterator, Mapping, NamedTuple, Sequence, Tuple

from pydantic import BaseModel

from cmk.config_generation.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
)


class AddressType(StrEnum):
    ADDRESS = "address"
    ALIAS = "alias"
    ALL_IP4vADDRESSES = "all_ipv4addresses"
    ALL_IP6vADDRESSES = "all_ipv6addresses"
    ADDITIONAL_IP4vADDRESSES = "additional_ipv4addresses"
    ADDITIONAL_IP6vADDRESSES = "additional_ipv6addresses"
    INDEXED_IPv4ADDRESS = "indexed_ipv4address"
    INDEXED_IPv6ADDRESS = "indexed_ipv6address"
    EXPLICIT = "explicit"


class ICMPParams(BaseModel):
    multiple_services: bool = False
    description: str | None = None
    address: AddressType = AddressType.ADDRESS
    address_index: int | None = None
    explicit_address: str | None = None
    min_pings: int = 0
    timeout: int | None = None
    packets: int | None = None
    rta: tuple[float, float] = (200, 500)
    loss: tuple[float, float] = (80, 100)


class AddressCmdArgs(NamedTuple):
    ip_family: IPAddressFamily
    address_args: Sequence[str | IPv4Address | IPv6Address]

    def to_list(self) -> list[str]:
        addresses = [str(a) for a in self.address_args]
        if self.ip_family == IPAddressFamily.IPv6:
            return ["-6", *addresses]
        return addresses


def parse_address(raw_params: Mapping[str, object]) -> tuple[AddressType, int | None, str | None]:
    address = raw_params.get("address", "address")
    if isinstance(address, str):
        return AddressType(address), None, None
    if isinstance(address, tuple) and address[0] in ("indexed_ipv4address", "indexed_ipv6address"):
        return AddressType(address[0]), int(address[1]), None
    if isinstance(address, tuple) and address[0] == "explicit":
        return AddressType(address[0]), None, str(address[1])
    raise ValueError("Invalid address parameters")


def parse_icmp_params(raw_params: Mapping[str, object]) -> ICMPParams:
    address, address_index, explicit_address = parse_address(raw_params)
    parsed_params = {
        "address": address,
        "address_index": address_index,
        "explicit_address": explicit_address,
        **{k: v for k, v in raw_params.items() if k != "address"},
    }
    return ICMPParams.model_validate(parsed_params)


def get_common_arguments(params: ICMPParams) -> list[str]:
    args = []
    if params.min_pings:
        args += ["-m", "%d" % params.min_pings]
    if params.timeout is not None:
        args += ["-t", str(params.timeout)]
    if params.packets is not None:
        args += ["-n", str(params.packets)]
    args += ["-w", "%.2f,%d%%" % (params.rta[0], params.loss[0])]
    args += ["-c", "%.2f,%d%%" % (params.rta[1], params.loss[1])]
    return args


def get_address_arguments(params: ICMPParams, host_config: HostConfig) -> AddressCmdArgs:
    match params.address:
        case AddressType.ADDRESS:
            return AddressCmdArgs(host_config.ip_family, [host_config.address])
        case AddressType.ALIAS:
            return AddressCmdArgs(host_config.ip_family, [host_config.alias])
        case AddressType.ALL_IP4vADDRESSES:
            return AddressCmdArgs(IPAddressFamily.IPv4, host_config.all_ipv4addresses)
        case AddressType.ALL_IP6vADDRESSES:
            return AddressCmdArgs(IPAddressFamily.IPv6, host_config.all_ipv6addresses)
        case AddressType.ADDITIONAL_IP4vADDRESSES:
            return AddressCmdArgs(IPAddressFamily.IPv4, host_config.additional_ipv4addresses)
        case AddressType.ADDITIONAL_IP6vADDRESSES:
            return AddressCmdArgs(IPAddressFamily.IPv6, host_config.additional_ipv6addresses)
    if params.address == AddressType.INDEXED_IPv4ADDRESS and params.address_index is not None:
        ipv4address = host_config.additional_ipv4addresses[params.address_index - 1]
        return AddressCmdArgs(IPAddressFamily.IPv4, [ipv4address])
    if params.address == AddressType.INDEXED_IPv6ADDRESS and params.address_index is not None:
        ipv6address = host_config.additional_ipv6addresses[params.address_index - 1]
        return AddressCmdArgs(IPAddressFamily.IPv6, [ipv6address])
    if params.address == AddressType.EXPLICIT and params.explicit_address:
        return AddressCmdArgs(IPAddressFamily.IPv4, [params.explicit_address])
    raise ValueError("Invalid address parameters")


def get_icmp_description_all_ips(params: ICMPParams) -> str:
    if params.description:
        return params.description
    description = "PING"
    for v in ("4", "6"):
        if params.address.value == f"all_ipv{v}addresses":
            description += f" all IPv{v} Addresses"
        if params.address.value == f"indexed_ipv{v}address":
            description += f" IPv{v}/{params.address_index}"
    return description


def generate_single_address_services(
    address_args: AddressCmdArgs,
) -> Iterator[Tuple[str, AddressCmdArgs]]:
    for address in address_args.address_args:
        yield str(address), AddressCmdArgs(address_args.ip_family, [address])


def generate_icmp_services(
    params: ICMPParams, host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    multiple_services = params.multiple_services
    common_args = get_common_arguments(params)
    address_args = get_address_arguments(params, host_config)
    if not multiple_services:
        description = get_icmp_description_all_ips(params)
        arguments = common_args + address_args.to_list()
        yield ActiveCheckCommand(service_description=description, command_arguments=arguments)
    else:
        desc_template = params.description or "PING"
        for ip_address, single_address_args in generate_single_address_services(address_args):
            arguments = common_args + single_address_args.to_list()
            yield ActiveCheckCommand(
                service_description=f"{desc_template} {ip_address}", command_arguments=arguments
            )


active_check_icmp = ActiveCheckConfig(
    name="icmp", parameter_parser=parse_icmp_params, commands_function=generate_icmp_services
)
