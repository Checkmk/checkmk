#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import abstractmethod
from collections.abc import Mapping, Sequence
from enum import auto, Enum
from typing import Final, Literal, NamedTuple, override, Self


class IPAddressFamily(Enum):
    """Defines an IP address family"""

    IPV4 = auto()
    IPV6 = auto()


class _IPConfig:
    """
    Defines an IP configuration of the host
    """

    def __init__(self, *, address: str | None, additional_addresses: Sequence[str] = ()):
        self._address = address
        self.additional_addresses: Final = additional_addresses

    @property
    @abstractmethod
    def family(self) -> IPAddressFamily: ...

    @property
    def address(self) -> str:
        """The host address (ip address or host name)

        Raises a RuntimeError if the lookup failed.
        The exact nature of the problem is reported during config generation.
        """
        if not self._address:
            raise RuntimeError("Host address lookup failed")
        return self._address

    @override
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"address={self._address!r}, "
            f"additional_addresses={self.additional_addresses!r})"
        )

    @override
    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, self.__class__):
            return NotImplemented
        return (
            self._address == __value._address
            and self.additional_addresses == __value.additional_addresses
        )


class IPv4Config(_IPConfig):
    """
    Defines an IPv4 configuration of the host
    """

    @property
    @override
    def family(self) -> Literal[IPAddressFamily.IPV4]:
        return IPAddressFamily.IPV4


class IPv6Config(_IPConfig):
    """
    Defines an IPv6 configuration of the host
    """

    @property
    @override
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

        >>> from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand


        >>> def generate_example_commands(
        ...     params: Mapping[str, object],
        ...     host_config: HostConfig,
        ... ) -> Iterable[SpecialAgentCommand]:
        ...     args = ["--hostname", host_config.name, "--address", host_config.address]
        ...     yield SpecialAgentCommand(command_arguments=args)
    """

    def __init__(
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
    def primary_ip_config(self) -> IPv4Config | IPv6Config:
        """Points to the primary address config"""
        if self._primary_ip_config is None:
            raise ValueError("Host has no IP stack configured")
        return self._primary_ip_config

    @override
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

    @override
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


class URLProxy(NamedTuple):
    """
    Surrogate for a HTTP proxy defined by the user

    This is a surrogate for a HTTP proxy defined globally or explicitly in the setup.

    Example:

        >>> proxy = URLProxy('proxy.com')  # don't create it, it's passed by the backend
        >>> if isinstance(proxy, URLProxy):
        ...     argv = ["--proxy", proxy.url]

    """

    type: Literal["url_proxy"] = "url_proxy"
    url: str = ""


class EnvProxy(NamedTuple):
    """
    Surrogate for a HTTP proxy defined in the process environment

    Example:

        >>> proxy = EnvProxy()  # don't create it, it's passed by the backend
        >>> if isinstance(proxy, EnvProxy):
        ...     argv = ["--use-environment-proxy"]

    """

    type: Literal["env_proxy"] = "env_proxy"


class NoProxy(NamedTuple):
    """
    Surrogate for a connection without proxy

    Example:

        >>> proxy = NoProxy()  # don't create it, it's passed by the backend
        >>> if isinstance(proxy, NoProxy):
        ...     argv = ["--no-proxy"]

    """

    type: Literal["no_proxy"] = "no_proxy"


class Secret(NamedTuple):
    # it seems that NamedTuple is the most reasonable way to create a pydantic compatible class
    # without adding a dependency on pydantic
    """
    Surrogate for a secret defined by the user

    This is a surrogate for a secret defined in the setup.
    You, the developer of the plug-in, can use it to define

     * where in the argv list the password will be
     * how it might have to be formatted
     * whether to pass the secret itself, or preferable, only the
       name of the secret in the password store

    If you pass the name of the secret to the special agents / active check,
    it needs to look up the corresponding secret from the password store using
    :func:`cmk.utils.password_store.lookup`.
    There is no API for the password store (yet) that provides the desirable
    stability, so the above might change location and name in the future.

    Neither the passord itself nor the name of the password is contained
    in this object.

    Example:

        >>> my_secret = Secret(42)  # don't create it, it is passed by the backend
        >>> # ideally, you just pass the reference for the password store
        >>> argv = ["--secret-from-store",  my_secret]
        >>> # plug-ins might not support the password store, and have special formatting needs:
        >>> argv = ["--basicauth", my_secret.unsafe("user:%s")]

    """

    id: int
    format: str = "%s"
    pass_safely: bool = True

    def unsafe(self, /, template: str = "%s") -> Self:
        """
        Returns a new :class:`Secret` that will be passed along as plain text.

        Args:
            template: The new formatting template

        Example:

            If include the the secret like this in the command line:

                >>> my_secret = Secret(42)  # don't create it, it is passed by the backend
                >>> args = ["--basicauth", my_secret.unsafe("user:%s")]

            What the plug-in will receive as argv is `[`'--basicauth', 'user:myS3cret!123']``


        """
        try:
            # we don't have this validation upon creation, but at least prevent errors here.
            _ = template % "test"
        except TypeError as e:
            raise ValueError(f"Invalid formatting template: {template}") from e

        return self.__class__(id=self.id, pass_safely=False, format=template)


def noop_parser(params: Mapping[str, object]) -> Mapping[str, object]:
    # NOTE: please do not add a TypeVar here. The only intended use case is Mapping[str, object],
    # and using a TypeVar in the return type hinders mypy's type inference at the callsites.
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
        macros: Mapping of host macros names and values. In the plug-ins, host macros are
                provided through the host_config.macros attribute.

    Example:

    >>> ["--hostname", replace_macros("$HOST_NAME$", {"$HOST_NAME$": "Test Host"})]
    ['--hostname', 'Test Host']

    """

    for macro_name, macro_value in macros.items():
        value = value.replace(macro_name, macro_value)

    return value
