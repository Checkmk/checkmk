#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class IPAddressFamily(StrEnum):
    """Defines an IP address family"""

    IPV4 = "ipv4"
    """IPv4 address family"""
    IPV6 = "ipv6"
    """IPv6 address family"""


@dataclass(frozen=True)
class HostConfig:  # pylint: disable=too-many-instance-attributes
    """
    Defines a host configuration

    This object encapsulates configuration parameters of the Checkmk host
    the active check or special agent is associated with.
    It will be created by the backend and passed to the `commands_function`.

    The data is collected from the host setup configuration. If IPv4 or IPv6 address
    isn't specified, it will be resolved using the host name.
    If the IP family is configured as IPv4/IPv6 dual-stack, it will be resolved using the
    `Primary IP address family of dual-stack hosts` rule.

    Address can be None only in case `No IP` has been configured as host's IP address family.

    Args:
        name: Host name
        address: Equal to the IPv4 or IPv6 address, depending on the IP family of the host
        alias: Host alias
        ip_family: Resolved IP address family
        ipv4address: Resolved IPv4 address, None if IP family is IPv6
        ipv6address: Resolved IPv6 address, None if IP family is IPv4
        additional_ipv4addresses: Additional IPv4 addresses
        additional_ipv6addresses: Additional IPv6 addresses

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
    address: str | None
    alias: str
    ip_family: IPAddressFamily
    ipv4address: str | None = None
    ipv6address: str | None = None
    additional_ipv4addresses: Sequence[str] = field(default_factory=list)
    additional_ipv6addresses: Sequence[str] = field(default_factory=list)

    @property
    def all_ipv4addresses(self) -> Sequence[str]:
        """
        Sequence containing the IPv4 address and the additional IPv4 addresses
        """
        if self.ipv4address:
            return [self.ipv4address, *self.additional_ipv4addresses]
        return self.additional_ipv4addresses

    @property
    def all_ipv6addresses(self) -> Sequence[str]:
        """
        Sequence containing the IPv6 address and the additional IPv6 addresses
        """
        if self.ipv6address:
            return [self.ipv6address, *self.additional_ipv6addresses]
        return self.additional_ipv6addresses


@dataclass(frozen=True)
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
        ...     get_http_proxy
        ... )

        >>> class ExampleParams(BaseModel):
        ...     proxy_type: Literal["global", "environment", "url", "no_proxy"]
        ...     proxy_value: str | None

        >>> def generate_example_commands(
        ...     params: ExampleParams,
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = [
        ...         "--proxy",
        ...         get_http_proxy(params.proxy_type, params.proxy_value, http_proxies)
        ...     ]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """

    id: str
    name: str
    url: str


@dataclass(frozen=True)
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

        >>> StoredSecret("stored_password_id", format="example-user:%s")
        StoredSecret(value='stored_password_id', format='example-user:%s')
    """

    value: str
    format: str = "%s"


@dataclass(frozen=True)
class PlainTextSecret:
    """
    Defines an explicit password

    Args:
        value: The password
        format: printf-style format of the created argument. Should be used if
                active check or special agent require a secret argument in a particular format

    Example:

        >>> PlainTextSecret("password1234")
        PlainTextSecret(value='password1234', format='%s')
    """

    value: str
    format: str = "%s"


Secret = StoredSecret | PlainTextSecret


def get_secret_from_params(
    secret_type: Literal["store", "password"], secret_value: str, display_format: str = "%s"
) -> Secret:
    # TODO: if we rename the valuespec in the new API, it should be changed here too
    """
    Parses values configured via the :class:`IndividualOrStoredPassword` into an instance
    of one of the two appropriate classes.

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
        ...     get_secret_from_params,
        ... )


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     secret = get_secret_from_params(
        ...         "store",
        ...         "stored_secret_id",
        ...         display_format="example-user:%s",
        ...     )
        ...     args = ["--auth", secret]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """
    match secret_type:
        case "store":
            return StoredSecret(secret_value, format=display_format)
        case "password":
            return PlainTextSecret(secret_value, format=display_format)
        case _:
            raise ValueError(f"{secret_type} is not a valid secret type")


def get_http_proxy(
    proxy_type: Literal["global", "environment", "url", "no_proxy"],
    proxy_value: str | None,
    http_proxies: Mapping[str, HTTPProxy],
) -> str:
    # TODO: if we provide some kind of an utility function to create HTTP proxy valuespecs
    # in the new API, it should be mentioned here too
    """
    Returns a proxy from parameters created by the HTTP proxy CascadingDropdown valuespec

    Args:
        proxy_type: Type of the proxy
        proxy_value: Value of the proxy
        http_proxies: Mapping of globally defined HTTP proxies

    Returns:
        String representing a proxy configuration

    Example:

        >>> from collections.abc import Iterable, Mapping

        >>> from cmk.server_side_calls.v1 import (
        ...     SpecialAgentCommand,
        ...     HostConfig,
        ...     HTTPProxy,
        ...     get_http_proxy
        ... )


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ...     http_proxies: Mapping[str, HTTPProxy]
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     proxy = get_http_proxy("global", "example_proxy", http_proxies)
        ...     args = ["--proxy", proxy]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """
    if proxy_type == "url":
        return str(proxy_value)

    if proxy_type == "no_proxy":
        return "NO_PROXY"

    if proxy_type == "global":
        if (global_proxy := http_proxies.get(str(proxy_value))) is not None:
            return str(global_proxy.url)

    return "FROM_ENVIRONMENT"


def noop_parser(params: Mapping[str, object]) -> Mapping[str, object]:
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
