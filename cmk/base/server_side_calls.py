#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Protocol

import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.servicename import ServiceName
from cmk.utils.translations import TranslationOptions

import cmk.base.config as base_config
import cmk.base.core_config as core_config
from cmk.base import plugin_contexts

from cmk.server_side_calls.v1 import (
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
    PlainTextSecret,
    Secret,
    SpecialAgentConfig,
    StoredSecret,
)

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


class InvalidPluginInfoError(Exception):
    pass


class ActiveCheckError(Exception):
    pass


@dataclass(frozen=True)
class ActiveServiceData:
    plugin_name: str
    description: ServiceName
    command: str
    command_display: str
    command_line: str
    params: Mapping[str, object]
    expanded_args: str


@dataclass(frozen=True)
class ActiveServiceDescription:
    plugin_name: str
    description: ServiceName
    params: Mapping[str, object]


@dataclass(frozen=True)
class HostAddressConfiguration:
    hostname: str
    host_address: str
    alias: str
    ipv4address: str | None
    ipv6address: str | None
    indexed_ipv4addresses: dict[str, str]
    indexed_ipv6addresses: dict[str, str]


@dataclass(frozen=True)
class PluginInfo:
    command_line: str
    argument_function: Callable[[Mapping[str, object]], Sequence[str]] | None = None
    service_description: Callable[[Mapping[str, object]], str] | None = None
    service_generator: Callable[
        [HostAddressConfiguration, Mapping[str, object]], Iterator[tuple[str, str]]
    ] | None = None


@dataclass(frozen=True)
class SpecialAgentCommandLine:
    cmdline: str
    stdin: str | None = None


class SpecialAgentLegacyConfiguration(Protocol):
    args: Sequence[str]
    # None makes the stdin of subprocess /dev/null
    stdin: str | None


SpecialAgentInfoFunctionResult = (
    str | Sequence[str | int | float | tuple[str, str, str]] | SpecialAgentLegacyConfiguration
)
InfoFunc = Callable[
    [Mapping[str, object], HostName, HostAddress | None], SpecialAgentInfoFunctionResult
]


def _get_host_address_config(
    host_name: str, host_attrs: Mapping[str, str]
) -> HostAddressConfiguration:
    def _get_indexed_addresses(
        host_attrs: Mapping[str, str], address_family: Literal["4", "6"]
    ) -> Iterator[tuple[str, str]]:
        for name, address in host_attrs.items():
            address_template = f"_ADDRESSES_{address_family}_"
            if address_template in name:
                index = name.removeprefix(address_template)
                yield f"$_HOSTADDRESSES_{address_family}_{index}$", address

    return HostAddressConfiguration(
        hostname=host_name,
        host_address=host_attrs["address"],
        alias=host_attrs["alias"],
        ipv4address=host_attrs.get("_ADDRESS_4"),
        ipv6address=host_attrs.get("_ADDRESS_6"),
        indexed_ipv4addresses=dict(_get_indexed_addresses(host_attrs, "4")),
        indexed_ipv6addresses=dict(_get_indexed_addresses(host_attrs, "6")),
    )


def _get_host_config(host_name: str, host_attrs: Mapping[str, str]) -> HostConfig:
    ip_family = (
        IPAddressFamily.IPV4 if host_attrs["_ADDRESS_FAMILY"] == "4" else IPAddressFamily.IPV6
    )

    return HostConfig(
        name=host_name,
        address=host_attrs["address"],
        alias=host_attrs["alias"],
        ip_family=ip_family,
        ipv4address=host_attrs.get("_ADDRESS_4"),
        ipv6address=host_attrs.get("_ADDRESS_6"),
        additional_ipv4addresses=[a for a in host_attrs["_ADDRESSES_4"].split(" ") if a],
        additional_ipv6addresses=[a for a in host_attrs["_ADDRESSES_6"].split(" ") if a],
    )


def _prepare_check_command(
    command_spec: CheckCommandArguments,
    hostname: HostName,
    description: ServiceName | None,
    passwords_from_store: Mapping[str, str],
) -> str:
    """Prepares a check command for execution by Checkmk

    In case a list is given it quotes element if necessary. It also prepares password store entries
    for the command line. These entries will be completed by the executed program later to get the
    password from the password store.
    """
    passwords: list[tuple[str, str, str]] = []
    formatted: list[str] = []
    for arg in command_spec:
        if isinstance(arg, (int, float)):
            formatted.append(str(arg))

        elif isinstance(arg, str):
            formatted.append(shlex.quote(arg))

        elif isinstance(arg, tuple) and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
            try:
                password = passwords_from_store[pw_ident]
            except KeyError:
                if hostname and description:
                    descr = f' used by service "{description}" on host "{hostname}"'
                elif hostname:
                    descr = f' used by host host "{hostname}"'
                else:
                    descr = ""

                config_warnings.warn(
                    f'The stored password "{pw_ident}"{descr} does not exist (anymore).'
                )
                password = "%%%"

            pw_start_index = str(preformated_arg.index("%s"))
            formatted.append(shlex.quote(preformated_arg % ("*" * len(password))))
            passwords.append((str(len(formatted)), pw_start_index, pw_ident))

        else:
            raise ActiveCheckError(f"Invalid argument for command line: {arg!r}")

    if passwords:
        pw = ",".join(["@".join(p) for p in passwords])
        pw_store_arg = f"--pwstore={pw}"
        formatted = [shlex.quote(pw_store_arg)] + formatted

    return " ".join(formatted)


def commandline_arguments(
    hostname: HostName,
    description: ServiceName | None,
    commandline_args: SpecialAgentInfoFunctionResult,
    passwords_from_store: Mapping[str, str] | None = None,
) -> str:
    """Commandline arguments for special agents or active checks."""

    if isinstance(commandline_args, str):
        return commandline_args

    # Some special agents also have stdin configured
    args = getattr(commandline_args, "args", commandline_args)

    if not isinstance(args, list):
        raise ActiveCheckError(
            "The check argument function needs to return either a list of arguments or a "
            "string of the concatenated arguments (Service: %s)." % (description)
        )

    return _prepare_check_command(
        args,
        hostname,
        description,
        cmk.utils.password_store.load() if passwords_from_store is None else passwords_from_store,
    )


def _replace_passwords(
    host_name: str,
    stored_passwords: Mapping[str, str],
    arguments: Sequence[str | Secret],
) -> str:
    passwords: list[tuple[str, str, str]] = []
    formatted: list[str] = []

    for arg in arguments:
        if isinstance(arg, PlainTextSecret):
            formatted.append(shlex.quote(arg.format % arg.value))

        elif isinstance(arg, StoredSecret):
            try:
                password = stored_passwords[arg.value]
            except KeyError:
                config_warnings.warn(
                    f'The stored password "{arg.value}" used by host "{host_name}"'
                    " does not exist."
                )
                password = "%%%"

            pw_start_index = str(arg.format.index("%s"))
            formatted.append(shlex.quote(arg.format % ("*" * len(password))))
            passwords.append((str(len(formatted)), pw_start_index, arg.value))
        else:
            formatted.append(shlex.quote(str(arg)))

    if passwords:
        pw = ",".join(["@".join(p) for p in passwords])
        pw_store_arg = f"--pwstore={pw}"
        formatted = [shlex.quote(pw_store_arg)] + formatted

    return " ".join(formatted)


class ActiveCheck:
    def __init__(
        self,
        plugins: Mapping[str, ActiveCheckConfig],
        legacy_plugins: Mapping[str, Mapping[str, Any]],
        host_name: HostName,
        host_attrs: Mapping[str, str],
        translations: TranslationOptions,
        macros: Mapping[str, str] | None = None,
        stored_passwords: Mapping[str, str] | None = None,
        escape_func: Callable[[str], str] = lambda a: a.replace("!", "\\!"),
    ):
        self._plugins = plugins
        self._legacy_plugins = legacy_plugins
        self.host_name = host_name
        self.host_alias = host_attrs["alias"]
        self.host_attrs = host_attrs
        self.translations = translations
        self.macros = macros or {}
        self.stored_passwords = stored_passwords or {}
        self.escape_func = escape_func

    def get_active_service_data(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ) -> Iterator[ActiveServiceData]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        with plugin_contexts.current_host(self.host_name):
            for plugin_name, plugin_params in active_checks_rules:
                service_iterator = self._get_service_iterator(plugin_name, plugin_params)

                if not service_iterator:
                    continue

                try:
                    yield from self._get_service_data(plugin_name, service_iterator)
                except InvalidPluginInfoError:
                    config_warnings.warn(
                        f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                        f"active check plugin is missing an argument function or a service description"
                    )
                except Exception as e:
                    if cmk.utils.debug.enabled():
                        raise
                    config_warnings.warn(
                        f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                    )

    def _get_service_iterator(
        self,
        plugin_name: str,
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]] | None:
        if (plugin_info_dict := self._legacy_plugins.get(plugin_name)) is not None:
            plugin_info = PluginInfo(
                command_line=plugin_info_dict["command_line"],
                argument_function=plugin_info_dict.get("argument_function"),
                service_description=plugin_info_dict.get("service_description"),
                service_generator=plugin_info_dict.get("service_generator"),
            )
            return self._iterate_legacy_services(plugin_name, plugin_info, plugin_params)

        if (active_check := self._plugins.get(plugin_name)) is not None:
            return self._iterate_services(active_check, plugin_params)

        return None

    def _iterate_services(
        self, active_check: ActiveCheckConfig, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]]:
        host_config = _get_host_config(self.host_name, self.host_attrs)
        http_proxies = {
            id: HTTPProxy(id, proxy["title"], proxy["proxy_url"])
            for id, proxy in base_config.http_proxies.items()
        }

        for param_dict in plugin_params:
            params = active_check.parameter_parser(param_dict)
            for service in active_check.commands_function(params, host_config, http_proxies):
                arguments = _replace_passwords(
                    self.host_name,
                    self.stored_passwords,
                    service.command_arguments,
                )
                command_line = f"check_{active_check.name} {arguments}"
                yield service.service_description, arguments, command_line, param_dict

    def _iterate_legacy_services(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]]:
        for params in plugin_params:
            for desc, args in self._iter_active_check_services(plugin_name, plugin_info, params):
                args_without_macros = self._replace_macros(args)
                command_line = plugin_info.command_line.replace("$ARG1$", args_without_macros)
                yield desc, args_without_macros, command_line, params

    def _get_service_data(
        self,
        plugin_name: str,
        service_iterator: Iterator[tuple[str, str, str, Mapping[str, object]]],
    ) -> Iterator[ActiveServiceData]:
        existing_descriptions: dict[str, str] = {}

        for description, args, command_line, params in service_iterator:
            if not description:
                config_warnings.warn(
                    f"Skipping invalid service with empty description "
                    f"(active check: {plugin_name}) on host {self.host_name}"
                )
                continue

            if description in existing_descriptions:
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                continue

            existing_descriptions[description] = plugin_name

            command, exec_command_line = self._get_command(plugin_name, command_line)

            yield ActiveServiceData(
                plugin_name=plugin_name,
                description=description,
                command=command,
                command_display=f"{command}!{self.escape_func(args)}",
                command_line=exec_command_line,
                params=params,
                expanded_args=self.escape_func(args),
            )

    def _get_command(self, plugin_name: str, command_line: str) -> tuple[str, str]:
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            command = "check-mk-custom"
            command_line = 'echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2'

            return command, command_line

        command = f"check_mk_active-{plugin_name}"
        return command, core_config.autodetect_plugin(command_line)

    def _replace_macros(self, string: str) -> str:
        for macro, replacement in self.macros.items():
            string = string.replace(macro, str(replacement))
        return string

    @staticmethod
    def _old_active_http_check_service_description(params: Mapping[str, object]) -> str:
        name = str(params["name"])
        return name[1:] if name.startswith("^") else "HTTP %s" % name

    def _active_check_service_description(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: Mapping[str, object],
    ) -> ServiceName:
        if not plugin_info.service_description:
            raise InvalidPluginInfoError

        if plugin_name == "http" and plugin_name not in base_config.use_new_descriptions_for:
            description_with_macros = self._old_active_http_check_service_description(params)
        else:
            description_with_macros = plugin_info.service_description(params)

        description = description_with_macros.replace("$HOSTNAME$", self.host_name).replace(
            "$HOSTALIAS$", self.host_alias
        )

        return base_config.get_final_service_description(description, self.translations)

    def _iter_active_check_services(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        params: Mapping[str, object],
    ) -> Iterator[tuple[str, str]]:
        if plugin_info.service_generator:
            host_config = _get_host_address_config(self.host_name, self.host_attrs)

            for desc, args in plugin_info.service_generator(host_config, params):
                yield str(desc), str(args)
            return

        description = self._active_check_service_description(plugin_name, plugin_info, params)

        if not plugin_info.argument_function:
            raise InvalidPluginInfoError

        arguments = commandline_arguments(
            self.host_name,
            description,
            plugin_info.argument_function(params),
            self.stored_passwords,
        )
        yield description, arguments

    def get_active_service_descriptions(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object]]]]
    ) -> Iterator[ActiveServiceDescription]:
        # remove setting the host context when deleting the old API
        # the host name is passed as an argument in the new API
        with plugin_contexts.current_host(self.host_name):
            for plugin_name, plugin_params in active_checks_rules:
                service_iterator = self._get_service_description_iterator(
                    plugin_name, plugin_params
                )

                if not service_iterator:
                    continue

                try:
                    yield from service_iterator
                except InvalidPluginInfoError:
                    config_warnings.warn(
                        f"Invalid configuration (active check: {plugin_name}) on host {self.host_name}: "
                        f"active check plugin is missing an argument function or a service description"
                    )
                    continue

    def _get_service_description_iterator(
        self,
        plugin_name: str,
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[ActiveServiceDescription] | None:
        if (plugin_info_dict := self._legacy_plugins.get(plugin_name)) is not None:
            plugin_info = PluginInfo(
                command_line=plugin_info_dict["command_line"],
                argument_function=plugin_info_dict.get("argument_function"),
                service_description=plugin_info_dict.get("service_description"),
                service_generator=plugin_info_dict.get("service_generator"),
            )
            return self._iterate_legacy_service_descriptions(
                plugin_name, plugin_info, plugin_params
            )

        if (active_check := self._plugins.get(plugin_name)) is not None:
            return self._iterate_service_descriptions(active_check, plugin_params)

        return None

    def _iterate_legacy_service_descriptions(
        self,
        plugin_name: str,
        plugin_info: PluginInfo,
        plugin_params: Sequence[Mapping[str, object]],
    ) -> Iterator[ActiveServiceDescription]:
        for params in plugin_params:
            if plugin_info.service_generator:
                host_config = _get_host_address_config(self.host_name, self.host_attrs)

                for description, _ in plugin_info.service_generator(host_config, params):
                    yield ActiveServiceDescription(plugin_name, str(description), params)
                return

            description = self._active_check_service_description(plugin_name, plugin_info, params)
            yield ActiveServiceDescription(plugin_name, str(description), params)

    def _iterate_service_descriptions(
        self, active_check: ActiveCheckConfig, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[ActiveServiceDescription]:
        for desc, _args, _command_line, params in self._iterate_services(
            active_check, plugin_params
        ):
            yield ActiveServiceDescription(active_check.name, desc, params)


class SpecialAgent:
    def __init__(
        self,
        plugins: Mapping[str, SpecialAgentConfig],
        legacy_plugins: Mapping[str, InfoFunc],
        host_name: HostName,
        host_address: HostAddress | None,
        host_attrs: Mapping[str, str],
        stored_passwords: Mapping[str, str],
    ):
        self._plugins = plugins
        self._legacy_plugins = legacy_plugins
        self.host_name = host_name
        self.host_address = host_address
        self.host_attrs = host_attrs
        self.stored_passwords = stored_passwords

    def _make_source_path(self, agent_name: str) -> Path:
        file_name = f"agent_{agent_name}"
        local_path = cmk.utils.paths.local_agents_dir / "special" / file_name
        if local_path.exists():
            return local_path
        return Path(cmk.utils.paths.agents_dir) / "special" / file_name

    def _make_special_agent_cmdline(
        self,
        agent_name: str,
        agent_configuration: SpecialAgentInfoFunctionResult,
    ) -> str:
        path = self._make_source_path(agent_name)
        args = commandline_arguments(self.host_name, None, agent_configuration)
        return f"{path} {args}"

    def _iter_legacy_commands(
        self, agent_name: str, info_func: InfoFunc, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        agent_configuration = info_func(params, self.host_name, self.host_address)

        cmdline = self._make_special_agent_cmdline(
            agent_name,
            agent_configuration,
        )
        stdin = getattr(agent_configuration, "stdin", None)

        yield SpecialAgentCommandLine(cmdline, stdin)

    def _iter_commands(
        self, special_agent: SpecialAgentConfig, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        host_config = _get_host_config(self.host_name, self.host_attrs)
        http_proxies = {
            id: HTTPProxy(id, proxy["title"], proxy["proxy_url"])
            for id, proxy in base_config.http_proxies.items()
        }

        parsed_params = special_agent.parameter_parser(params)
        for command in special_agent.commands_function(parsed_params, host_config, http_proxies):
            path = self._make_source_path(special_agent.name)
            args = _replace_passwords(
                self.host_name, self.stored_passwords, command.command_arguments
            )
            yield SpecialAgentCommandLine(f"{path} {args}", command.stdin)

    def iter_special_agent_commands(
        self, agent_name: str, params: Mapping[str, object]
    ) -> Iterator[SpecialAgentCommandLine]:
        try:
            if (info_func := self._legacy_plugins.get(agent_name)) is not None:
                yield from self._iter_legacy_commands(agent_name, info_func, params)

            if (special_agent := self._plugins.get(agent_name.replace("agent_", ""))) is not None:
                yield from self._iter_commands(special_agent, params)
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            config_warnings.warn(
                f"Config creation for special agent {agent_name} failed on {self.host_name}: {e}"
            )
