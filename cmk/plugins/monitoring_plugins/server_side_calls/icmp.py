#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Mapping, Sequence
from enum import StrEnum
from ipaddress import IPv4Address, IPv6Address
from typing import assert_never, NamedTuple

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    replace_macros,
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
    address_index: int
    explicit_address: str | None
    min_pings: int = 0
    timeout: int | None = None
    packets: int | None = None
    rta: tuple[float, float] = (200, 500)
    loss: tuple[float, float] = (80, 100)


class AddressCmdArgs(NamedTuple):
    ip_family: IPAddressFamily | None
    address_args: Sequence[str | IPv4Address | IPv6Address]

    def to_list(self) -> list[str]:
        addresses = [str(a) for a in self.address_args]
        if self.ip_family == IPAddressFamily.IPV6:
            return ["-6", *addresses]
        return addresses


def parse_address(raw_params: Mapping[str, object]) -> tuple[AddressType, int, str | None]:
    address = raw_params.get("address", "address")
    if isinstance(address, str):
        return AddressType(address), 0, None
    if isinstance(address, tuple) and address[0] in ("indexed_ipv4address", "indexed_ipv6address"):
        return AddressType(address[0]), int(address[1]), None
    if isinstance(address, tuple) and address[0] == "explicit":
        return AddressType(address[0]), 0, str(address[1])
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


def _all_addresses(ip_config: IPv4Config | IPv6Config | None) -> Sequence[str]:
    if ip_config is None:
        return []
    try:
        return [ip_config.address, *ip_config.additional_addresses]
    except RuntimeError:
        return ip_config.additional_addresses


def get_address_arguments(params: ICMPParams, host_config: HostConfig) -> AddressCmdArgs:
    match params.address:
        case AddressType.ADDRESS:
            return AddressCmdArgs(
                host_config.primary_ip_config.family, [host_config.primary_ip_config.address]
            )
        case AddressType.ALIAS:
            return AddressCmdArgs(host_config.primary_ip_config.family, [host_config.alias])
        case AddressType.ALL_IP4vADDRESSES:
            return AddressCmdArgs(IPAddressFamily.IPV4, _all_addresses(host_config.ipv4_config))
        case AddressType.ALL_IP6vADDRESSES:
            return AddressCmdArgs(IPAddressFamily.IPV6, _all_addresses(host_config.ipv6_config))
        case AddressType.ADDITIONAL_IP4vADDRESSES:
            return AddressCmdArgs(
                IPAddressFamily.IPV4,
                () if not (ipv4 := host_config.ipv4_config) else ipv4.additional_addresses,
            )
        case AddressType.ADDITIONAL_IP6vADDRESSES:
            return AddressCmdArgs(
                IPAddressFamily.IPV6,
                () if not (ipv6 := host_config.ipv6_config) else ipv6.additional_addresses,
            )
        case AddressType.INDEXED_IPv4ADDRESS:
            if (ipv4 := host_config.ipv4_config) is None:
                raise ValueError("Host has no IPv4 addresses")
            try:
                return AddressCmdArgs(
                    IPAddressFamily.IPV4, [ipv4.additional_addresses[params.address_index - 1]]
                )
            except IndexError as exc:
                raise ValueError(f"Invalid address index: {params.address_index!r}") from exc

        case AddressType.INDEXED_IPv6ADDRESS:
            if (ipv6 := host_config.ipv6_config) is None:
                raise ValueError("Host has no IPv6 addresses")
            try:
                return AddressCmdArgs(
                    IPAddressFamily.IPV6, [ipv6.additional_addresses[params.address_index - 1]]
                )
            except IndexError as exc:
                raise ValueError(f"Invalid address index: {params.address_index!r}") from exc

        case AddressType.EXPLICIT:
            if not params.explicit_address:
                raise ValueError("Explicit address is required")
            return AddressCmdArgs(IPAddressFamily.IPV4, [params.explicit_address])

        case other:
            assert_never(other)


def get_icmp_description_all_ips(params: ICMPParams, host_config: HostConfig) -> str:
    if params.description:
        return replace_macros(params.description, host_config.macros)
    description = "PING"
    for v in ("4", "6"):
        if params.address.value == f"all_ipv{v}addresses":
            description += f" all IPv{v} Addresses"
        if params.address.value == f"indexed_ipv{v}address":
            description += f" IPv{v}/{params.address_index}"
    return description


def generate_single_address_services(
    address_args: AddressCmdArgs,
) -> Iterator[tuple[str, AddressCmdArgs]]:
    for address in address_args.address_args:
        yield str(address), AddressCmdArgs(address_args.ip_family, [address])


def generate_icmp_services(
    params: ICMPParams,
    host_config: HostConfig,
) -> Iterator[ActiveCheckCommand]:
    multiple_services = params.multiple_services
    common_args = get_common_arguments(params)
    address_args = get_address_arguments(params, host_config)
    if not multiple_services:
        description = get_icmp_description_all_ips(params, host_config)
        arguments = common_args + address_args.to_list()
        yield ActiveCheckCommand(service_description=description, command_arguments=arguments)
    else:
        desc_template = replace_macros(params.description or "PING", host_config.macros)
        for ip_address, single_address_args in generate_single_address_services(address_args):
            arguments = common_args + single_address_args.to_list()
            yield ActiveCheckCommand(
                service_description=f"{desc_template} {ip_address}", command_arguments=arguments
            )


active_check_icmp = ActiveCheckConfig(
    name="icmp", parameter_parser=parse_icmp_params, commands_function=generate_icmp_services
)
