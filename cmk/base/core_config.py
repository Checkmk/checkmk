#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import dataclasses
import numbers
import os
import shlex
import shutil
import socket
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, AnyStr, Literal, NamedTuple, Union

import cmk.utils.config_path
import cmk.utils.debug
import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.store import load_object_from_file, save_object_to_file
from cmk.utils.type_defs import (
    CheckPluginName,
    ConfigurationWarnings,
    HostAddress,
    HostName,
    HostsToUpdate,
    Item,
    Labels,
    LabelSources,
    ServiceID,
    ServiceName,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
from cmk.base.check_utils import ConfiguredService
from cmk.base.config import ConfigCache, ObjectAttributes, TaggroupIDToTagID
from cmk.base.nagios_utils import do_check_nagiosconfig

ObjectMacros = dict[str, AnyStr]
CoreCommandName = str
CoreCommand = str
CheckCommandArguments = Iterable[Union[int, float, str, tuple[str, str, str]]]

ActiveServiceID = tuple[str, Item]  # TODO: I hope the str someday (tm) becomes "CheckPluginName",
AbstractServiceID = Union[ActiveServiceID, ServiceID]


@dataclasses.dataclass(frozen=True)
class CollectedHostLabels:
    host_labels: Labels
    service_labels: dict[ServiceName, Labels]


class MonitoringCore(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> Literal["nagios", "cmc"]:
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def is_cmc() -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def create_config(
        self,
        config_path: VersionedConfigPath,
        config_cache: ConfigCache,
        hosts_to_update: HostsToUpdate = None,
    ) -> None:
        raise NotImplementedError


_ignore_ip_lookup_failures = False
_failed_ip_lookups: list[HostName] = []

# .
#   .--Warnings------------------------------------------------------------.
#   |            __        __               _                              |
#   |            \ \      / /_ _ _ __ _ __ (_)_ __   __ _ ___              |
#   |             \ \ /\ / / _` | '__| '_ \| | '_ \ / _` / __|             |
#   |              \ V  V / (_| | |  | | | | | | | | (_| \__ \             |
#   |               \_/\_/ \__,_|_|  |_| |_|_|_| |_|\__, |___/             |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Managing of warning messages occuring during configuration building  |
#   '----------------------------------------------------------------------'

g_configuration_warnings: ConfigurationWarnings = []


def initialize_warnings() -> None:
    global g_configuration_warnings
    g_configuration_warnings = []


def warning(text: str) -> None:
    g_configuration_warnings.append(text)
    console.warning("\n%s", text, stream=sys.stdout)


def get_configuration_warnings() -> ConfigurationWarnings:
    adjusted_warnings = list(set(g_configuration_warnings))

    if (num_warnings := len(adjusted_warnings)) > 10:
        warnings = adjusted_warnings[:10] + [
            "%d further warnings have been omitted" % (num_warnings - 10)
        ]
    else:
        warnings = adjusted_warnings

    return warnings


def duplicate_service_warning(
    *,
    checktype: str,
    description: str,
    host_name: HostName,
    first_occurrence: AbstractServiceID,
    second_occurrence: AbstractServiceID,
) -> None:
    return warning(
        "ERROR: Duplicate service description (%s check) '%s' for host '%s'!\n"
        " - 1st occurrence: check plugin / item: %s / %r\n"
        " - 2nd occurrence: check plugin / item: %s / %r\n"
        % (checktype, description, host_name, *first_occurrence, *second_occurrence)
    )


# TODO: Just for documentation purposes for now.
#
# HostCheckCommand = NewType('HostCheckCommand',
#                            Union[Literal["smart"],
#                                  Literal["ping"],
#                                  Literal["ok"],
#                                  Literal["agent"],
#                                  Tuple[Literal["service"], TextInput],
#                                  Tuple[Literal["tcp"], Integer],
#                                  Tuple[Literal["custom"], TextInput]])


def _cluster_ping_command(
    config_cache: ConfigCache, host_name: HostName, ip: HostAddress
) -> CoreCommand | None:
    ping_args = check_icmp_arguments_of(config_cache, host_name)
    if ip:  # Do check cluster IP address if one is there
        return "check-mk-host-ping!%s" % ping_args
    if ping_args:  # use check_icmp in cluster mode
        return "check-mk-host-ping-cluster!%s" % ping_args
    return None


def host_check_command(
    config_cache: ConfigCache,
    host_name: HostName,
    ip: HostAddress,
    is_clust: bool,
    default_host_check_command: str,
    host_check_via_service_status: Callable,
    host_check_via_custom_check: Callable,
) -> CoreCommand | None:
    value = config_cache.host_check_command(host_name, default_host_check_command)

    if value == "smart":
        if is_clust:
            return _cluster_ping_command(config_cache, host_name, ip)
        return "check-mk-host-smart"

    if value == "ping":
        if is_clust:
            return _cluster_ping_command(config_cache, host_name, ip)
        ping_args = check_icmp_arguments_of(config_cache, host_name)
        if ping_args:  # use special arguments
            return "check-mk-host-ping!%s" % ping_args
        return None

    if value == "ok":
        return "check-mk-host-ok"

    if value == "agent":
        return host_check_via_service_status("Check_MK")

    if isinstance(value, tuple) and value[0] == "service":
        return host_check_via_service_status(value[1])

    if isinstance(value, tuple) and value[0] == "tcp":
        if value[1] is None:
            raise TypeError()
        return "check-mk-host-tcp!" + str(value[1])

    if isinstance(value, tuple) and value[0] == "custom":
        if not isinstance(value[1], str):
            raise TypeError()
        return host_check_via_custom_check(
            "check-mk-custom", "check-mk-custom!" + autodetect_plugin(value[1])
        )

    raise MKGeneralException(f"Invalid value {value!r} for host_check_command of host {host_name}.")


def autodetect_plugin(command_line: str) -> str:
    plugin_name = command_line.split()[0]
    if command_line[0] in ["$", "/"]:
        return command_line

    for directory in ["local", ""]:
        path = cmk.utils.paths.omd_root / directory / "lib/nagios/plugins"
        if (path / plugin_name).exists():
            command_line = f"{path}/{command_line}"
            break

    return command_line


def check_icmp_arguments_of(
    config_cache: ConfigCache,
    hostname: HostName,
    add_defaults: bool = True,
    family: int | None = None,
) -> str:
    levels = config_cache.ping_levels(hostname)
    if not add_defaults and not levels:
        return ""

    if family is None:
        family = 6 if config_cache.is_ipv6_primary(hostname) else 4

    args = []

    if family == 6:
        args.append("-6")

    rta = 200.0, 500.0
    loss = 80.0, 100.0
    for key, value in levels.items():
        if key == "timeout":
            if not isinstance(value, int):
                raise TypeError()
            args.append("-t %d" % value)
        elif key == "packets":
            if not isinstance(value, int):
                raise TypeError()
            args.append("-n %d" % value)
        elif key == "rta":
            if not isinstance(value, tuple):
                raise TypeError()
            rta = value
        elif key == "loss":
            if not isinstance(value, tuple):
                raise TypeError()
            loss = value
    args.append(f"-w {rta[0]:.2f},{loss[0]:.2f}%")
    args.append(f"-c {rta[1]:.2f},{loss[1]:.2f}%")
    return " ".join(args)


# .
#   .--Core Config---------------------------------------------------------.
#   |          ____                  ____             __ _                 |
#   |         / ___|___  _ __ ___   / ___|___  _ __  / _(_) __ _           |
#   |        | |   / _ \| '__/ _ \ | |   / _ \| '_ \| |_| |/ _` |          |
#   |        | |__| (_) | | |  __/ | |__| (_) | | | |  _| | (_| |          |
#   |         \____\___/|_|  \___|  \____\___/|_| |_|_| |_|\__, |          |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   | Code for managing the core configuration creation.                   |
#   '----------------------------------------------------------------------'


def do_create_config(
    core: MonitoringCore,
    config_cache: ConfigCache,
    hosts_to_update: HostsToUpdate = None,
    *,
    duplicates: Sequence[HostName],
) -> None:
    """Creating the monitoring core configuration and additional files

    Ensures that everything needed by the monitoring core and it's helper processes is up-to-date
    and available for starting the monitoring.
    """
    out.output("Generating configuration for core (type %s)...\n" % core.name())

    try:
        _create_core_config(
            core, config_cache, hosts_to_update=hosts_to_update, duplicates=duplicates
        )
    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Error creating configuration: %s" % e)

    _bake_on_restart()


def _bake_on_restart() -> None:
    try:
        # Local import is needed, because this is not available in all environments
        import cmk.base.cee.bakery.agent_bakery as agent_bakery  # pylint: disable=redefined-outer-name,import-outside-toplevel

        agent_bakery.bake_on_restart()
    except ImportError:
        pass


@contextmanager
def _backup_objects_file(core: MonitoringCore) -> Iterator[None]:
    if core.name() == "nagios":
        objects_file = cmk.utils.paths.nagios_objects_file
    else:
        objects_file = cmk.utils.paths.var_dir + "/core/config"

    backup_path = None
    if os.path.exists(objects_file):
        backup_path = objects_file + ".save"
        shutil.copy2(objects_file, backup_path)

    try:
        try:
            yield None
        except Exception:
            if backup_path:
                os.rename(backup_path, objects_file)
            raise

        if (
            core.name() == "nagios"
            and Path(cmk.utils.paths.nagios_config_file).exists()
            and not do_check_nagiosconfig()
        ):
            broken_config_path = Path(cmk.utils.paths.tmp_dir) / "check_mk_objects.cfg.broken"
            shutil.move(cmk.utils.paths.nagios_objects_file, broken_config_path)

            if backup_path:
                os.rename(backup_path, objects_file)
            elif os.path.exists(objects_file):
                os.remove(objects_file)

            raise MKGeneralException(
                "Configuration for monitoring core is invalid. Rolling back. "
                'The broken file has been copied to "%s" for analysis.' % broken_config_path
            )
    finally:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)


def _create_core_config(
    core: MonitoringCore,
    config_cache: ConfigCache,
    hosts_to_update: HostsToUpdate = None,
    *,
    duplicates: Sequence[HostName],
) -> ConfigurationWarnings:
    initialize_warnings()

    _verify_non_duplicate_hosts(duplicates)
    _verify_non_deprecated_checkgroups()

    config_path = next(VersionedConfigPath.current())
    with config_path.create(is_cmc=core.is_cmc()), _backup_objects_file(core):
        core.create_config(config_path, config_cache, hosts_to_update=hosts_to_update)

    cmk.utils.password_store.save_for_helpers(config_path)

    return get_configuration_warnings()


def _verify_non_deprecated_checkgroups() -> None:
    """Verify that the user has no deprecated check groups configured."""
    # 'check_plugin.check_ruleset_name' is of type RuleSetName, which is an ABCName (good),
    # but config.checkgroup_parameters contains strings (todo)
    check_ruleset_names_with_plugin = {
        str(plugin.check_ruleset_name)
        for plugin in agent_based_register.iter_all_check_plugins()
        if plugin.check_ruleset_name
    }

    for checkgroup in config.checkgroup_parameters:
        if checkgroup not in check_ruleset_names_with_plugin:
            warning(
                'Found configured rules of deprecated check group "%s". These rules are not used '
                "by any check plugin. Maybe this check group has been renamed during an update, "
                "in this case you will have to migrate your configuration to the new ruleset manually. "
                "Please check out the release notes of the involved versions. "
                'You may use the page "Deprecated rules" in the "Rule search" to view your rules '
                "and move them to the new rulesets. "
                "If this is not the case, the rules could be related to a disabled or removed "
                "extension package (mkp). You would have to enable/upload the corresponding package "
                "and remove the related rules before disabling/removing the package again."
                % checkgroup
            )


def _verify_non_duplicate_hosts(duplicates: Iterable[HostName]) -> None:
    if duplicates:
        warning(
            "The following host names have duplicates: %s. "
            "This might lead to invalid/incomplete monitoring for these hosts."
            % ", ".join(duplicates)
        )


# .
#   .--Active Checks-------------------------------------------------------.
#   |       _        _   _              ____ _               _             |
#   |      / \   ___| |_(_)_   _____   / ___| |__   ___  ___| | _____      |
#   |     / _ \ / __| __| \ \ / / _ \ | |   | '_ \ / _ \/ __| |/ / __|     |
#   |    / ___ \ (__| |_| |\ V /  __/ | |___| | | |  __/ (__|   <\__ \     |
#   |   /_/   \_\___|\__|_| \_/ \___|  \____|_| |_|\___|\___|_|\_\___/     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Active check specific functions                                      |
#   '----------------------------------------------------------------------'


class HostAddressConfiguration(NamedTuple):
    """Host configuration for active checks

    This class is exposed to the active checks that implement a service_generator.
    However, it's NOT part of the official API and can change at any time.
    """

    hostname: str
    host_address: str
    alias: str
    ipv4address: str | None
    ipv6address: str | None
    indexed_ipv4addresses: dict[str, str]
    indexed_ipv6addresses: dict[str, str]


def _get_indexed_addresses(
    host_attrs: config.ObjectAttributes, address_family: Literal["4", "6"]
) -> Iterator[tuple[str, str]]:
    for name, address in host_attrs.items():
        address_template = f"_ADDRESSES_{address_family}_"
        if address_template in name:
            index = name.removeprefix(address_template)
            yield f"$_HOSTADDRESSES_{address_family}_{index}$", address


def _get_host_address_config(
    hostname: str, host_attrs: config.ObjectAttributes
) -> HostAddressConfiguration:
    return HostAddressConfiguration(
        hostname=hostname,
        host_address=host_attrs["address"],
        alias=host_attrs["alias"],
        ipv4address=host_attrs.get("_ADDRESS_4"),
        ipv6address=host_attrs.get("_ADDRESS_6"),
        indexed_ipv4addresses=dict(_get_indexed_addresses(host_attrs, "4")),
        indexed_ipv6addresses=dict(_get_indexed_addresses(host_attrs, "6")),
    )


def iter_active_check_services(
    check_name: str,
    active_info: Mapping[str, Any],
    hostname: str,
    host_attrs: config.ObjectAttributes,
    params: dict[Any, Any],
    stored_passwords: Mapping[str, str],
) -> Iterator[tuple[str, str]]:
    """Iterate active service descriptions and arguments

    This function is used to allow multiple active services per one WATO rule.
    This functionality is now used only in ICMP active check and it's NOT
    part of an official API. This function can be changed at any time.
    """
    host_config = _get_host_address_config(hostname, host_attrs)

    if "service_generator" in active_info:
        for desc, args in active_info["service_generator"](host_config, params):
            yield str(desc), str(args)
        return

    description = config.active_check_service_description(
        hostname, host_config.alias, check_name, params
    )
    arguments = commandline_arguments(
        hostname,
        description,
        active_info["argument_function"](params),
        stored_passwords,
    )

    yield description, arguments


def _prepare_check_command(
    command_spec: CheckCommandArguments,
    hostname: HostName,
    description: ServiceName | None,
    stored_passwords: Mapping[str, str],
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
            formatted.append("%s" % arg)

        elif isinstance(arg, str):
            formatted.append(shlex.quote(arg))

        elif isinstance(arg, tuple) and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
            try:
                password = stored_passwords[pw_ident]
            except KeyError:
                if hostname and description:
                    descr = f' used by service "{description}" on host "{hostname}"'
                elif hostname:
                    descr = ' used by host host "%s"' % (hostname)
                else:
                    descr = ""

                console.warning(
                    f'The stored password "{pw_ident}"{descr} does not exist (anymore).'
                )
                password = "%%%"

            pw_start_index = str(preformated_arg.index("%s"))
            formatted.append(shlex.quote(preformated_arg % ("*" * len(password))))
            passwords.append((str(len(formatted)), pw_start_index, pw_ident))

        else:
            raise MKGeneralException(f"Invalid argument for command line: {arg!r}")

    if passwords:
        formatted = ["--pwstore=%s" % ",".join(["@".join(p) for p in passwords])] + formatted

    return " ".join(formatted)


def get_active_check_descriptions(
    hostname: HostName,
    hostalias: str,
    host_attrs: ObjectAttributes,
    check_name: str,
    params: dict,
) -> Iterator[str]:
    host_config = _get_host_address_config(hostname, host_attrs)
    active_check_info = config.active_check_info[check_name]

    if "service_generator" in active_check_info:
        for description, _ in active_check_info["service_generator"](host_config, params):
            yield str(description)
        return

    yield config.active_check_service_description(hostname, hostalias, check_name, params)


# .
#   .--Argument Thingies---------------------------------------------------.
#   |    _                                         _                       |
#   |   / \   _ __ __ _ _   _ _ __ ___   ___ _ __ | |_                     |
#   |  / _ \ | '__/ _` | | | | '_ ` _ \ / _ \ '_ \| __|                    |
#   | / ___ \| | | (_| | |_| | | | | | |  __/ | | | |_                     |
#   |/_/   \_\_|  \__, |\__,_|_| |_| |_|\___|_| |_|\__|                    |
#   |             |___/                                                    |
#   | _____ _     _             _                                          |
#   ||_   _| |__ (_)_ __   __ _(_) ___  ___                                |
#   |  | | | '_ \| | '_ \ / _` | |/ _ \/ __|                               |
#   |  | | | | | | | | | | (_| | |  __/\__ \                               |
#   |  |_| |_| |_|_|_| |_|\__, |_|\___||___/                               |
#   |                     |___/                                            |
#   +----------------------------------------------------------------------+
#   | Command line arguments for special agents or active checks           |
#   '----------------------------------------------------------------------'


def commandline_arguments(
    hostname: HostName,
    description: ServiceName | None,
    commandline_args: config.SpecialAgentInfoFunctionResult,
    stored_passwords: Mapping[str, str] | None = None,
) -> str:
    """Commandline arguments for special agents or active checks."""
    if isinstance(commandline_args, str):
        return commandline_args

    # Some special agents also have stdin configured
    args = getattr(commandline_args, "args", commandline_args)

    if not isinstance(args, list):
        raise MKGeneralException(
            "The check argument function needs to return either a list of arguments or a "
            "string of the concatenated arguments (Host: %s, Service: %s)."
            % (hostname, description)
        )

    return _prepare_check_command(
        args,
        hostname,
        description,
        cmk.utils.password_store.load() if stored_passwords is None else stored_passwords,
    )


def make_special_agent_cmdline(
    hostname: HostName,
    ipaddress: HostAddress | None,
    agentname: str,
    params: dict,
) -> str:
    def _make_source_path(agentname: str) -> Path:
        file_name = "agent_%s" % agentname
        local_path = cmk.utils.paths.local_agents_dir / "special" / file_name
        if local_path.exists():
            return local_path
        return Path(cmk.utils.paths.agents_dir) / "special" / file_name

    def _make_source_args(
        hostname: HostName,
        ipaddress: HostAddress | None,
        agentname: str,
        params: dict,
    ) -> str:
        info_func = config.special_agent_info[agentname]
        # TODO: CMK-3812 (see above)
        agent_configuration = info_func(params, hostname, ipaddress)
        return commandline_arguments(hostname, None, agent_configuration)

    path = _make_source_path(agentname)
    args = _make_source_args(
        hostname,
        ipaddress,
        agentname,
        params,
    )
    return f"{path} {args}"


def make_special_agent_stdin(
    hostname: HostName,
    ipaddress: HostAddress | None,
    agentname: str,
    params: dict,
) -> str | None:
    info_func = config.special_agent_info[agentname]
    # TODO: We call a user supplied function here.
    # If this crashes during config generation, it can get quite ugly.
    # We should really wrap this and implement proper sanitation and exception handling.
    # Deal with this when modernizing the API (CMK-3812).
    agent_configuration = info_func(params, hostname, ipaddress)
    return getattr(agent_configuration, "stdin", None)


# .
#   .--ServiceAttrs.-------------------------------------------------------.
#   |     ____                  _             _   _   _                    |
#   |    / ___|  ___ _ ____   _(_) ___ ___   / \ | |_| |_ _ __ ___         |
#   |    \___ \ / _ \ '__\ \ / / |/ __/ _ \ / _ \| __| __| '__/ __|        |
#   |     ___) |  __/ |   \ V /| | (_|  __// ___ \ |_| |_| |  \__ \_       |
#   |    |____/ \___|_|    \_/ |_|\___\___/_/   \_\__|\__|_|  |___(_)      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Management of service attributes                                     |
#   '----------------------------------------------------------------------'


def get_cmk_passive_service_attributes(
    config_cache: ConfigCache,
    host_name: HostName,
    service: ConfiguredService,
    check_mk_attrs: ObjectAttributes,
) -> ObjectAttributes:
    attrs = get_service_attributes(
        host_name,
        service.description,
        config_cache,
        service.check_plugin_name,
        service.parameters,
    )

    attrs["check_interval"] = check_mk_attrs["check_interval"]

    return attrs


def get_service_attributes(
    hostname: HostName,
    description: ServiceName,
    config_cache: ConfigCache,
    check_plugin_name: CheckPluginName | None = None,
    params: TimespecificParameters | None = None,
) -> ObjectAttributes:
    attrs: ObjectAttributes = _extra_service_attributes(
        hostname, description, config_cache, check_plugin_name, params
    )
    attrs.update(_get_tag_attributes(config_cache.tags_of_service(hostname, description), "TAG"))

    attrs.update(
        _get_tag_attributes(
            config_cache.ruleset_matcher.labels_of_service(hostname, description), "LABEL"
        )
    )
    attrs.update(
        _get_tag_attributes(
            config_cache.ruleset_matcher.label_sources_of_service(hostname, description),
            "LABELSOURCE",
        )
    )
    return attrs


def _extra_service_attributes(
    hostname: HostName,
    description: ServiceName,
    config_cache: ConfigCache,
    check_plugin_name: CheckPluginName | None,
    params: TimespecificParameters | None,
) -> ObjectAttributes:
    attrs = {}  # ObjectAttributes

    # Add service custom_variables. Name conflicts are prevented by the GUI, but just
    # to be sure, add them first. The other definitions will override the custom attributes.
    for varname, value in config_cache.custom_attributes_of_service(hostname, description).items():
        attrs["_%s" % varname.upper()] = value

    attrs.update(config_cache.extra_attributes_of_service(hostname, description))

    # Add explicit custom_variables
    for varname, value in ConfigCache.get_explicit_service_custom_variables(
        hostname, description
    ).items():
        attrs["_%s" % varname.upper()] = value

    # Add custom user icons and actions
    actions = config_cache.icons_and_actions_of_service(
        hostname, description, check_plugin_name, params
    )
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)
    return attrs


# .
#   .--ObjectAttributes------------------------------------------------------.
#   | _   _           _      _   _   _        _ _           _              |
#   || | | | ___  ___| |_   / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___   |
#   || |_| |/ _ \/ __| __| / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|  |
#   ||  _  | (_) \__ \ |_ / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \  |
#   ||_| |_|\___/|___/\__/_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Managing of host attributes                                          |
#   '----------------------------------------------------------------------'
def _set_addresses(
    attrs: ObjectAttributes,
    addresses: list[HostAddress] | None,
    what: Literal["4", "6"],
) -> None:
    key_base = f"_ADDRESSES_{what}"
    if not addresses:
        # If other addresses are not available, set to empty string in order to avoid unresolved macros
        attrs[key_base] = ""
        return
    attrs[key_base] = " ".join(addresses)
    for nr, address in enumerate(addresses):
        key = f"{key_base}_{nr + 1}"
        attrs[key] = address


def get_host_attributes(hostname: HostName, config_cache: ConfigCache) -> ObjectAttributes:
    attrs = config_cache.extra_host_attributes(hostname)

    # Pre 1.6 legacy attribute. We have changed our whole code to use the
    # livestatus column "tags" which is populated by all attributes starting with
    # "__TAG_" instead. We may deprecate this is one day.
    attrs["_TAGS"] = " ".join(sorted(config_cache.tag_list(hostname)))
    attrs.update(_get_tag_attributes(config_cache.tags(hostname), "TAG"))
    attrs.update(_get_tag_attributes(config_cache.labels(hostname), "LABEL"))
    attrs.update(_get_tag_attributes(config_cache.label_sources(hostname), "LABELSOURCE"))

    if "alias" not in attrs:
        attrs["alias"] = config_cache.alias(hostname)

    # Now lookup configured IP addresses
    v4address: str | None = None
    if ConfigCache.is_ipv4_host(hostname):
        v4address = ip_address_of(config_cache, hostname, socket.AF_INET)

    if v4address is None:
        v4address = ""
    attrs["_ADDRESS_4"] = v4address

    v6address: str | None = None
    if ConfigCache.is_ipv6_host(hostname):
        v6address = ip_address_of(config_cache, hostname, socket.AF_INET6)
    if v6address is None:
        v6address = ""
    attrs["_ADDRESS_6"] = v6address

    ipv6_primary = config_cache.is_ipv6_primary(hostname)
    if ipv6_primary:
        attrs["address"] = attrs["_ADDRESS_6"]
        attrs["_ADDRESS_FAMILY"] = "6"
    else:
        attrs["address"] = attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "4"

    add_ipv4addrs, add_ipv6addrs = config_cache.additional_ipaddresses(hostname)
    _set_addresses(attrs, add_ipv4addrs, "4")
    _set_addresses(attrs, add_ipv6addrs, "6")

    # Add the optional WATO folder path
    path = config.host_paths.get(hostname)
    if path:
        attrs["_FILENAME"] = path

    # Add custom user icons and actions
    actions = config_cache.icons_and_actions(hostname)
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)

    if cmk_version.is_managed_edition():
        attrs["_CUSTOMER"] = config.current_customer  # type: ignore[attr-defined] # needed for CRE/CEE

    return attrs


def _get_tag_attributes(
    collection: TaggroupIDToTagID | Labels | LabelSources,
    prefix: str,
) -> ObjectAttributes:
    return {f"__{prefix}_{k}": str(v) for k, v in collection.items()}


def get_cluster_attributes(
    config_cache: ConfigCache,
    hostname: HostName,
    nodes: Sequence[HostName],
) -> dict:
    sorted_nodes = sorted(nodes)

    attrs = {
        "_NODENAMES": " ".join(sorted_nodes),
    }
    node_ips_4 = []
    if ConfigCache.is_ipv4_host(hostname):
        family = socket.AF_INET
        for h in sorted_nodes:
            addr = ip_address_of(config_cache, h, family)
            if addr is not None:
                node_ips_4.append(addr)
            else:
                node_ips_4.append(ip_lookup.fallback_ip_for(family))

    node_ips_6 = []
    if ConfigCache.is_ipv6_host(hostname):
        family = socket.AF_INET6
        for h in sorted_nodes:
            addr = ip_address_of(config_cache, h, family)
            if addr is not None:
                node_ips_6.append(addr)
            else:
                node_ips_6.append(ip_lookup.fallback_ip_for(family))

    node_ips = node_ips_6 if config_cache.is_ipv6_primary(hostname) else node_ips_4

    for suffix, val in [("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6)]:
        attrs["_NODEIPS%s" % suffix] = " ".join(val)

    return attrs


def get_cluster_nodes_for_config(config_cache: ConfigCache, host_name: HostName) -> list[HostName]:
    nodes = config_cache.nodes_of(host_name)
    if nodes is None:
        return []

    _verify_cluster_address_family(host_name, nodes, config_cache)
    _verify_cluster_datasource(host_name, nodes, config_cache)
    nodes = nodes[:]
    for node in nodes:
        if node not in config_cache.all_active_realhosts():
            warning(
                "Node '%s' of cluster '%s' is not a monitored host in this site."
                % (node, host_name)
            )
            nodes.remove(node)
    return nodes


def _verify_cluster_address_family(
    host_name: HostName,
    nodes: Iterable[HostName],
    config_cache: ConfigCache,
) -> None:
    cluster_host_family = "IPv6" if config_cache.is_ipv6_primary(host_name) else "IPv4"
    address_families = [
        f"{host_name}: {cluster_host_family}",
    ]

    address_family = cluster_host_family
    mixed = False
    for nodename in nodes:
        family = "IPv6" if config_cache.is_ipv6_primary(nodename) else "IPv4"
        address_families.append(f"{nodename}: {family}")
        if address_family is None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        warning(
            "Cluster '%s' has different primary address families: %s"
            % (host_name, ", ".join(address_families))
        )


def _verify_cluster_datasource(
    host_name: HostName,
    nodes: Iterable[HostName],
    config_cache: ConfigCache,
) -> None:
    cluster_tg = config_cache.tags(host_name)
    cluster_agent_ds = cluster_tg.get("agent")
    cluster_snmp_ds = cluster_tg.get("snmp_ds")
    for nodename in nodes:
        node_tg = config_cache.tags(nodename)
        node_agent_ds = node_tg.get("agent")
        node_snmp_ds = node_tg.get("snmp_ds")
        warn_text = "Cluster '%s' has different datasources as its node" % host_name
        if node_agent_ds != cluster_agent_ds:
            warning(f"{warn_text} '{nodename}': {cluster_agent_ds} vs. {node_agent_ds}")
        if node_snmp_ds != cluster_snmp_ds:
            warning(f"{warn_text} '{nodename}': {cluster_snmp_ds} vs. {node_snmp_ds}")


def ip_address_of(
    config_cache: ConfigCache, host_name: HostName, family: socket.AddressFamily
) -> str | None:
    try:
        return config.lookup_ip_address(config_cache, host_name, family=family)
    except Exception as e:
        if config_cache.is_cluster(host_name):
            return ""

        _failed_ip_lookups.append(host_name)
        if not _ignore_ip_lookup_failures:
            warning(
                "Cannot lookup IP address of '%s' (%s). "
                "The host will not be monitored correctly." % (host_name, e)
            )
        return ip_lookup.fallback_ip_for(family)


def ignore_ip_lookup_failures() -> None:
    global _ignore_ip_lookup_failures
    _ignore_ip_lookup_failures = True


def failed_ip_lookups() -> list[HostName]:
    return _failed_ip_lookups


def get_host_macros_from_attributes(hostname: HostName, attrs: ObjectAttributes) -> ObjectMacros:
    macros = {
        "$HOSTNAME$": hostname,
        "$HOSTADDRESS$": attrs["address"],
        "$HOSTALIAS$": attrs["alias"],
    }

    # Add custom macros
    for macro_name, value in attrs.items():
        if macro_name[0] == "_":
            macros["$HOST" + macro_name + "$"] = value
            # Be compatible to nagios making $_HOST<VARNAME>$ out of the config _<VARNAME> configs
            macros["$_HOST" + macro_name[1:] + "$"] = value

    return macros


def get_service_macros_from_attributes(attrs: ObjectAttributes) -> ObjectMacros:
    # We may want to implement a superset of Nagios' own macros, see
    # https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/3/en/macrolist.html
    macros = {}
    for macro_name, value in attrs.items():
        if macro_name[0] == "_":
            macros["$_SERVICE" + macro_name[1:] + "$"] = value
    return macros


def replace_macros(s: str, macros: ObjectMacros) -> str:
    for key, value in macros.items():
        if isinstance(value, (numbers.Integral, float)):
            value = str(value)  # e.g. in _EC_SL (service level)

        # TODO: Clean this up
        try:
            s = s.replace(key, value)
        except Exception:  # Might have failed due to binary UTF-8 encoding in value
            try:
                s = s.replace(key, value.decode("utf-8"))
            except Exception:
                # If this does not help, do not replace
                if cmk.utils.debug.enabled():
                    raise

    return s


def translate_ds_program_source_cmdline(
    config_cache: ConfigCache,
    template: str,
    host_name: HostName,
    ipaddress: HostAddress | None,
) -> str:
    def _translate_host_macros(cmd: str) -> str:
        attrs = get_host_attributes(host_name, config_cache)
        if config_cache.is_cluster(host_name):
            parents_list = get_cluster_nodes_for_config(config_cache, host_name)
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(
                get_cluster_attributes(
                    config_cache,
                    host_name,
                    parents_list,
                )
            )

        macros = get_host_macros_from_attributes(host_name, attrs)
        return replace_macros(cmd, macros)

    def _translate_legacy_macros(
        cmd: str,
        host_name: HostName,
        ipaddress: HostAddress | None,
    ) -> str:
        # Make "legacy" translation. The users should use the $...$ macros in future
        return replace_macros_in_str(
            cmd,
            {
                "<IP>": ipaddress or "",
                "<HOST>": host_name,
            },
        )

    return _translate_host_macros(_translate_legacy_macros(template, host_name, ipaddress))


def write_notify_host_file(
    config_path: VersionedConfigPath,
    labels_per_host: dict[HostName, CollectedHostLabels],
) -> None:
    notify_labels_path: Path = _get_host_file_path(config_path)
    for host, labels in labels_per_host.items():
        host_path = notify_labels_path / host
        save_object_to_file(
            host_path,
            dataclasses.asdict(
                CollectedHostLabels(
                    host_labels=labels.host_labels,
                    service_labels={k: v for k, v in labels.service_labels.items() if v.values()},
                )
            ),
        )


def read_notify_host_file(
    host_name: HostName,
) -> CollectedHostLabels:
    host_file_path: Path = _get_host_file_path(host_name=host_name)
    return CollectedHostLabels(
        **load_object_from_file(
            path=host_file_path,
            default={"host_labels": {}, "service_labels": {}},
        )
    )


def _get_host_file_path(
    config_path: VersionedConfigPath | None = None,
    host_name: HostName | None = None,
) -> Path:
    root_path = Path(config_path) if config_path else core_helper_config_dir / Path("latest")
    if host_name:
        return root_path / "notify" / "labels" / host_name
    return root_path / "notify" / "labels"


def get_labels_from_attributes(key_value_pairs: list[tuple[str, str]]) -> Labels:
    return {key[8:]: value for key, value in key_value_pairs if key.startswith("__LABEL_")}
