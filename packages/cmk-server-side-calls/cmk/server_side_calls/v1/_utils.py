#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from typing import Final, Literal, NamedTuple, Self, TypeVar


class IPAddressFamily(Enum):
    """Defines an IP address family"""

    IPV4 = auto()
    IPV6 = auto()


class IPConfig:
    """
    Defines an IP configuration of the host
    """

    def __init__(self, *, address: str | None, additional_addresses: Sequence[str] = ()):
        self._address = address
        self.additional_addresses: Final = additional_addresses

    @property
    @abstractmethod
    def family(self) -> IPAddressFamily:
        ...

    @property
    def address(self) -> str:
        """The host address (ip address or host name)

        Raises a RuntimeError if the lookup failed.
        The exact nature of the problem is reported during config generation.
        """
        if not self._address:
            raise RuntimeError("Host address lookup failed")
        return self._address

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"address={self._address!r}, "
            f"additional_addresses={self.additional_addresses!r})"
        )

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, self.__class__):
            return NotImplemented
        return (
            self._address == __value._address
            and self.additional_addresses == __value.additional_addresses
        )


class IPv4Config(IPConfig):
    """
    Defines an IPv4 configuration of the host
    """

    @property
    def family(self) -> Literal[IPAddressFamily.IPV4]:
        return IPAddressFamily.IPV4


class IPv6Config(IPConfig):
    """
    Defines an IPv6 configuration of the host
    """

    @property
    def family(self) -> Literal[IPAddressFamily.IPV6]:
        return IPAddressFamily.IPV6


class HostConfig:
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
        ipv4_config: The IPv4 network configuration of the host.
        ipv6_config: The IPv6 network configuration of the host.
        primary_family: Primary IP address family
        macros: Macro mapping that are being replaced for the host


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

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        name: str,
        alias: str = "",
        ipv4_config: IPv4Config | None = None,
        ipv6_config: IPv6Config | None = None,
        primary_family: IPAddressFamily = IPAddressFamily.IPV4,
        macros: Mapping[str, str] | None = None,
    ):
        if not name:
            raise ValueError("Host name has to be a non-empty string")

        self.name: Final = name
        self.alias: Final = alias or name
        self.ipv4_config: Final = ipv4_config
        self.ipv6_config: Final = ipv6_config
        self._primary_family: Final = primary_family
        self._primary_ip_config: Final = (
            self.ipv4_config if primary_family == IPAddressFamily.IPV4 else self.ipv6_config
        )
        self.macros: Final = macros or {}

    @property
    def primary_ip_config(self) -> IPConfig:
        """Points to the primary address config"""
        if self._primary_ip_config is None:
            raise ValueError("Host has no IP stack configured")
        return self._primary_ip_config

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"alias={self.alias!r}, "
            f"ipv4_config={self.ipv4_config!r}, "
            f"ipv6_config={self.ipv6_config!r}, "
            f"primary_family={self._primary_family!r}, "
            f"macros={self.macros!r})"
        )

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, self.__class__):
            return NotImplemented
        return (
            self.name == __value.name
            and self.alias == __value.alias
            and self.ipv4_config == __value.ipv4_config
            and self.ipv6_config == __value.ipv6_config
            and self._primary_family == __value._primary_family
            and self.macros == __value.macros
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


class Secret(NamedTuple):
    # it seems that NamedTuple is the most reasonable way to create a pydantic compatible class
    # without adding a dependency on pydantic
    """
    Surrogate for a secret defined by the user

    This is a surrogate for a secret defined in the setup.
    You, the developer if the plugin, can use it to define the place and formatting
    of the secrets usage.

    Example:

        >>> my_secret = Secret(id=42)  # don't create it, it is passed by the backend
        >>> argv = ["--basicauth",  my_secret.with_format("my_username:%s")]

    """
    id: int
    format: str = "%s"

    def with_format(self, /, template: str) -> Self:
        """
        Returns a new Secret with a different format

        Args:
            template: The new formatting template
        """
        try:
            # we don't have this validation upon creation, but at least prevent errors here.
            _ = template % "test"
        except TypeError as e:
            raise ValueError(f"Invalid formatting template: {template}") from e

        return self.__class__(self.id, template)


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
