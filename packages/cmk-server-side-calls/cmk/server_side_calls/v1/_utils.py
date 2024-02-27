#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar


class ResolvedIPAddressFamily(StrEnum):
    """Defines a resolved IP address family"""

    IPV4 = "ipv4"
    """IPv4 address family"""
    IPV6 = "ipv6"
    """IPv6 address family"""


class IPAddressFamily(StrEnum):
    """Defines an IP address family from the host configuration"""

    IPV4 = "ipv4"
    """IPv4 address family"""
    IPV6 = "ipv6"
    """IPv6 address family"""
    DUAL_STACK = "dual_stack"
    """Dual stack address family"""
    NO_IP = "no_ip"
    """No IP address family"""


@dataclass(frozen=True, kw_only=True)
class NetworkAddressConfig:
    """
    Defines a network configuration of the host

    All arguments are exactly defined as in the host configuration, no resolution of IP addresses
    or family has been done.

    Args:
        ip_family: IP family of the host
        ipv4_address: IPv4 address. Will be None if not defined in the configuration
        ipv6_address: IPv6 address. Will be None if not defined in the configuration
        additional_ipv4_addresses: Additional IPv4 addresses
        additional_ipv6_addresses: Additional IPv6 addresses

    """

    ip_family: IPAddressFamily
    ipv4_address: str | None = None
    ipv6_address: str | None = None
    additional_ipv4_addresses: Sequence[str] = field(default_factory=list)
    additional_ipv6_addresses: Sequence[str] = field(default_factory=list)

    @property
    def all_ipv4_addresses(self) -> Sequence[str]:
        """
        Sequence containing the IPv4 address and the additional IPv4 addresses
        """
        if self.ipv4_address:
            return [self.ipv4_address, *self.additional_ipv4_addresses]
        return self.additional_ipv4_addresses

    @property
    def all_ipv6_addresses(self) -> Sequence[str]:
        """
        Sequence containing the IPv6 address and the additional IPv6 addresses
        """
        if self.ipv6_address:
            return [self.ipv6_address, *self.additional_ipv6_addresses]
        return self.additional_ipv6_addresses


@dataclass(frozen=True, kw_only=True)
class HostConfig:  # pylint: disable=too-many-instance-attributes
    """
    Defines a host configuration

    This object encapsulates configuration parameters of the Checkmk host
    the active check or special agent is associated with.
    It will be created by the backend and passed to the `commands_function`.

    Address config holds the data collected from the host setup configuration.
    Resolved address can be the same as ipv4_address or ipv6_address from the address config,
    resolved from the host name or host name if dynamic DNS is configured.

    If the IP family is configured as IPv4/IPv6 dual-stack in address config,
    resolved IP family will be resolved using the `Primary IP address family of dual-stack hosts`
    rule.

    Resolved address can be None in case `No IP` has been configured as host's IP
    address family or if resolution wasn't successful.

    Args:
        name: Host name
        alias: Host alias
        resolved_ip_family: Resolved IP address family
        address_config: Address settings defined in the host configuration
        resolved_ipv4_address: If IPv4 address isn't configured in the host config,
            it will be resolved from the host name. Present if host has IPv4 or dual-stack
            family configured.
        resolved_ipv6_address: If IPv6 address isn't configured in the host config,
            it will be resolved from the host name. Present if host has IPv6 or dual-stack
            family configured.
        macros: Macro mapping that are being replaced for the host
        custom_attributes: Custom attributes of the host
        tags: Tags of the host
        labels: Labels of the host


    Example:

        >>> from collections.abc import Iterable, Mapping

        >>> from cmk.server_side_calls.v1 import HostConfig, HTTPProxy, SpecialAgentCommand


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = ["--hostname", host_config.name, "--address", host_config.address]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """

    name: str
    alias: str
    address_config: NetworkAddressConfig
    resolved_ipv4_address: str | None = None
    resolved_ipv6_address: str | None = None
    resolved_ip_family: ResolvedIPAddressFamily | None = None
    macros: Mapping[str, str] = field(default_factory=dict)
    custom_attributes: Mapping[str, str] = field(default_factory=dict)
    tags: Mapping[str, str] = field(default_factory=dict)
    labels: Mapping[str, str] = field(default_factory=dict)

    # TODO: Nuke this property? It is actually redundant, as can be seen below.
    # It can be computed from 3 other fields.
    @property
    def resolved_address(self) -> str | None:
        """
        Will be equal to resolved_ipv4_address or resolved_ipv6_address depending on the field
        resolved_ip_family.
        """
        return (
            self.resolved_ipv4_address
            if self.resolved_ip_family == ResolvedIPAddressFamily.IPV4
            else self.resolved_ipv6_address
        )


@dataclass(frozen=True, kw_only=True)
class HTTPProxy:
    """
    Defines a HTTP proxy

    This object represents a HTTP proxy configured in the global settings.
    A mapping of HTTPProxy objects will be created by the backend and passed to
    the `commands_function`.
    The mapping consists of a proxy ids as keys and HTTPProxy objects as values.

    Args:
        id: Id of the proxy
        name: Name of the proxy
        url: Url of the proxy

    Example:

        >>> from collections.abc import Iterable, Mapping
        >>> from typing import Literal

        >>> from pydantic import BaseModel

        >>> from cmk.server_side_calls.v1 import (
        ...     HostConfig,
        ...     HTTPProxy,
        ...     SpecialAgentCommand,
        ...     parse_http_proxy
        ... )

        >>> class ExampleParams(BaseModel):
        ...     proxy: tuple[Literal["global", "environment", "url", "no_proxy"], str | None]

        >>> def generate_example_commands(
        ...     params: ExampleParams,
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = [
        ...         "--proxy",
        ...         parse_http_proxy(params.proxy, http_proxies)
        ...     ]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """

    id: str
    name: str
    url: str


@dataclass(frozen=True, kw_only=True)
class StoredSecret:
    """
    Defines a password stored in the password store

    In order to avoid showing passwords in plain text in agent configuration and active
    check commands, store the password in the password store and use a StoredSecret object
    to represent an argument that contains a stored password.

    Args:
        value: Id of the password from the password store
        format: printf-style format of the created argument. Should be used if active check
                or special agent require a secret argument in a particular format

    Example:

        >>> StoredSecret(value="stored_password_id", format="example-user:%s")
        StoredSecret(value='stored_password_id', format='example-user:%s')
    """

    value: str
    format: str = "%s"


@dataclass(frozen=True, kw_only=True)
class PlainTextSecret:
    """
    Defines an explicit password

    Args:
        value: The password
        format: printf-style format of the created argument. Should be used if
                active check or special agent require a secret argument in a particular format

    Example:

        >>> PlainTextSecret(value="password1234")
        PlainTextSecret(value='password1234', format='%s')
    """

    value: str
    format: str = "%s"


Secret = StoredSecret | PlainTextSecret


def parse_secret(secret: object, display_format: str = "%s") -> Secret:
    """
    Parses a secret/password configuration into an instance of one of the two
    appropriate classes


    Args:
        secret_type: Type of the secret
        secret_value: Value of the secret. Can either be an id of the secret from
                the password store or an explicit value.
        display_format: Format of the argument containing the secret

    Returns:
        The class of the returned instance depends on the value of `secret_type`

    Example:

        >>> from collections.abc import Iterable, Mapping

        >>> from cmk.server_side_calls.v1 import (
        ...     SpecialAgentCommand,
        ...     HostConfig,
        ...     HTTPProxy,
        ...     parse_secret,
        ... )


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     secret = parse_secret(
        ...         ("store", "stored_secret_id"),
        ...         display_format="example-user:%s",
        ...     )
        ...     args = ["--auth", secret]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """
    if not isinstance(secret, tuple):
        raise ValueError("secret object has to be a tuple")

    secret_type, secret_value = secret

    if not isinstance(secret_value, str):
        raise ValueError("secret value has to be a string")

    match secret_type:
        case "store":
            return StoredSecret(value=secret_value, format=display_format)
        case "password":
            return PlainTextSecret(value=secret_value, format=display_format)
        case _:
            raise ValueError("secret type has as to be either 'store' or 'password'")


def parse_http_proxy(
    proxy: object,
    http_proxies: Mapping[str, HTTPProxy],
) -> str:
    """
    Parses a proxy configuration into a proxy string

    The function will check if proxy argument has the expected type.

    Args:
        proxy: An object created by the HTTPProxy form spec
        http_proxies: Mapping of globally defined HTTP proxies

    Returns:
        String representing a proxy configuration

    Example:

        >>> from collections.abc import Iterable, Mapping

        >>> from cmk.server_side_calls.v1 import (
        ...     SpecialAgentCommand,
        ...     HostConfig,
        ...     HTTPProxy,
        ...     parse_http_proxy
        ... )


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     proxy = parse_http_proxy(("global", "example_proxy"), http_proxies)
        ...     args = ["--proxy", proxy]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """
    if not isinstance(proxy, tuple):
        raise ValueError("proxy object has to be a tuple")

    proxy_type, proxy_value = proxy

    if not isinstance(proxy_type, str) or proxy_type not in (
        "global",
        "environment",
        "url",
        "no_proxy",
    ):
        raise ValueError(
            "proxy type has to be one of: 'global', 'environment', 'url' or 'no_proxy'"
        )

    if not isinstance(proxy_value, str) and proxy_value is not None:
        raise ValueError("proxy value has to be a string or None")

    if proxy_type == "url":
        return str(proxy_value)

    if proxy_type == "no_proxy":
        return "NO_PROXY"

    if proxy_type == "global":
        if (global_proxy := http_proxies.get(str(proxy_value))) is not None:
            return str(global_proxy.url)

    return "FROM_ENVIRONMENT"


_T_co = TypeVar("_T_co", covariant=True)


def noop_parser(params: Mapping[str, _T_co]) -> Mapping[str, _T_co]:
    """
    Parameter parser that doesn't perform a transformation

    Use it if you don't require parameter transformation in ActiveCheckConfig or SpecialAgentConfig.

    Args:
        params: Parameters from the configuration file

    Example:

        >>> from collections.abc import Iterable

        >>> from cmk.server_side_calls.v1 import (
        ...     noop_parser,
        ...     SpecialAgentCommand,
        ...     SpecialAgentConfig
        ... )


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = ["--service", str(params["service"])]
        ...     yield SpecialAgentCommand(command_arguments=args)


        >>> special_agent_example = SpecialAgentConfig(
        ...     name="example",
        ...     parameter_parser=noop_parser,
        ...     commands_function=generate_example_commands,
        ... )
    """
    return params


def replace_macros(value: str, macros: Mapping[str, str]) -> str:
    """
    Replaces host macros in a string

    Args:
        value: String in which macros are replaced
        macros: Mapping of host macros names and values. In the plugins, host macros are
                provided through the host_config.macros attribute.

    Example:

    >>> ["--hostname", replace_macros("$HOST_NAME$", {"$HOST_NAME$": "Test Host"})]
    ['--hostname', 'Test Host']

    """

    for macro_name, macro_value in macros.items():
        value = value.replace(macro_name, macro_value)

    return value
