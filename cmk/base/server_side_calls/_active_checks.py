#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import cmk.ccc.debug

import cmk.utils.paths
from cmk.utils import config_warnings, password_store
from cmk.utils.hostaddress import HostName
from cmk.utils.servicename import ServiceName

from cmk.discover_plugins import discover_executable, family_libexec_dir, PluginLocation
from cmk.server_side_calls.v1 import ActiveCheckConfig, HostConfig
from cmk.server_side_calls_backend.config_processing import (
    process_configuration_to_parameters,
    ProxyConfig,
)

from ._commons import replace_passwords


# This class can probably be consolidated to have fewer fields.
# But it's close to the release and I don't dare to touch it.
@dataclass(frozen=True)
class ActiveServiceData:
    plugin_name: str
    description: ServiceName
    command: str
    command_display: str
    command_line: str
    params: object
    expanded_args: str
    detected_executable: str


@dataclass(frozen=True)
class ActiveServiceDescription:
    plugin_name: str
    description: ServiceName
    params: Mapping[str, object] | object


def _ensure_mapping_str_object(values: Sequence[object]) -> Sequence[Mapping[str, object]]:
    # for the new API, we can be sure that there are only Mappings.
    for value in values:
        if not isinstance(value, dict):
            raise TypeError(value)
    return values  # type: ignore[return-value]


class ActiveCheck:
    def __init__(
        self,
        plugins: Mapping[PluginLocation, ActiveCheckConfig],
        host_name: HostName,
        host_config: HostConfig,
        host_attrs: Mapping[str, str],
        http_proxies: Mapping[str, Mapping[str, str]],
        service_name_finalizer: Callable[[ServiceName], ServiceName],
        stored_passwords: Mapping[str, str],
        password_store_file: Path,
        escape_func: Callable[[str], str] = lambda a: a.replace("!", "\\!"),
    ):
        self._plugins = {p.name: p for p in plugins.values()}
        self._modules = {p.name: l.module for l, p in plugins.items()}
        self.host_name = host_name
        self.host_config = host_config
        self.host_alias = host_attrs["alias"]
        self.host_attrs = host_attrs
        self._http_proxies = http_proxies
        self._service_name_finalizer = service_name_finalizer
        self.stored_passwords = stored_passwords or {}
        self.password_store_file = password_store_file
        self.escape_func = escape_func

    def get_active_service_data(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object] | object]]]
    ) -> Iterator[ActiveServiceData]:
        for plugin_name, plugin_params in active_checks_rules:
            plugin_params = _ensure_mapping_str_object(plugin_params)

            service_iterator = self._iterate_services(plugin_name, plugin_params)

            try:
                yield from self._get_service_data(plugin_name, service_iterator)
            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )

    def _iterate_services(
        self, plugin_name: str, plugin_params: Sequence[Mapping[str, object]]
    ) -> Iterator[tuple[str, str, str, Mapping[str, object]]]:
        if (active_check := self._plugins.get(plugin_name)) is None:
            return
        for conf_dict in plugin_params:
            # actually these ^- are configuration sets.
            proxy_config = ProxyConfig(self.host_name, self._http_proxies)
            processed = process_configuration_to_parameters(conf_dict, proxy_config)

            for service in active_check(processed.value, self.host_config):
                arguments = replace_passwords(
                    self.host_name,
                    service.command_arguments,
                    self.stored_passwords,
                    self.password_store_file,
                    processed.surrogates,
                    apply_password_store_hack=password_store.hack.HACK_CHECKS.get(
                        active_check.name, False
                    ),
                )
                command_line = f"check_{active_check.name} {arguments}"
                yield service.service_description, arguments, command_line, conf_dict

    def _get_service_data(
        self,
        plugin_name: str,
        service_iterator: Iterator[tuple[str, str, str, object]],
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

            command, detected_exectutable, exec_command_line = self._get_command(
                plugin_name, command_line
            )

            yield ActiveServiceData(
                plugin_name=plugin_name,
                description=description,
                command=command,
                command_display=f"{command}!{self.escape_func(args)}",
                command_line=exec_command_line,
                params=params,
                expanded_args=self.escape_func(args),
                detected_executable=detected_exectutable,
            )

    def _get_command(self, plugin_name: str, command_line: str) -> tuple[str, str, str]:
        # TODO: check why/if we need this. Couldn't we have for example an active check that
        # queries some RestAPI?
        # This may be a leftover from a time where we would try to replace these in a macro?
        if self.host_attrs["address"] in ["0.0.0.0", "::"]:
            command = "check-mk-custom"
            command_line = 'echo "CRIT - Failed to lookup IP address and no explicit IP address configured"; exit 2'

            return command, "echo", command_line

        command = f"check_mk_active-{plugin_name}"
        executable, *args = command_line.split(None, 1)
        detected_executable = _autodetect_plugin(
            executable, self._modules.get(plugin_name.removeprefix("check_"))
        )
        return command, detected_executable, " ".join((detected_executable, *args))

    def get_active_service_descriptions(
        self, active_checks_rules: Sequence[tuple[str, Sequence[Mapping[str, object] | object]]]
    ) -> Iterator[ActiveServiceDescription]:
        for plugin_name, plugin_params in active_checks_rules:
            plugin_params = _ensure_mapping_str_object(plugin_params)

            try:
                for desc, _args, _command_line, params in self._iterate_services(
                    plugin_name, plugin_params
                ):
                    yield ActiveServiceDescription(plugin_name, desc, params)

            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {self.host_name}: {e}"
                )


def _autodetect_plugin(command: str, module_name: str | None) -> str:
    # This condition can only be true in the legacy case.
    # Remove it when possible!
    if command.startswith(("$", "/")):
        return command

    libexec_paths = (family_libexec_dir(module_name),) if module_name else ()
    nagios_paths = (
        cmk.utils.paths.local_lib_dir / "nagios/plugins",
        Path(cmk.utils.paths.lib_dir, "nagios/plugins"),
    )
    if (full_path := discover_executable(command, *libexec_paths, *nagios_paths)) is None:
        return command

    return str(full_path)
