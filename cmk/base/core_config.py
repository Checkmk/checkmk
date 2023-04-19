#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import dataclasses
import os
import shlex
import shutil
import socket
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Literal, NamedTuple, Union

import cmk.utils.config_path
import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.labels import Labels
from cmk.utils.log import console
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.store import load_object_from_file, lock_checkmk_configuration, save_object_to_file
from cmk.utils.type_defs import HostAddress, HostName, HostsToUpdate, Item, ServiceName

from cmk.checkers.check_table import ConfiguredService, ServiceID
from cmk.checkers.checking import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.obsolete_output as out
from cmk.base.config import ConfigCache, ObjectAttributes
from cmk.base.nagios_utils import do_check_nagiosconfig

CoreCommandName = str
CoreCommand = str
CheckCommandArguments = Iterable[Union[int, float, str, tuple[str, str, str]]]


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


ActiveServiceID = tuple[str, Item]  # TODO: I hope the str someday (tm) becomes "CheckPluginName",
AbstractServiceID = ActiveServiceID | ServiceID


def duplicate_service_warning(
    *,
    checktype: str,
    description: str,
    host_name: HostName,
    first_occurrence: AbstractServiceID,
    second_occurrence: AbstractServiceID,
) -> None:
    return config_warnings.warn(
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
    family: socket.AddressFamily | None = None,
) -> str:
    levels = config_cache.ping_levels(hostname)
    if not add_defaults and not levels:
        return ""

    if family is None:
        family = config_cache.default_address_family(hostname)

    args = []

    if family is socket.AF_INET6:
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
    skip_config_locking_for_bakery: bool = False,
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

    if config.bake_agents_on_restart and not config.is_wato_slave_site:
        _bake_on_restart(config_cache, skip_config_locking_for_bakery)


def _bake_on_restart(config_cache: config.ConfigCache, skip_locking: bool) -> None:
    try:
        # Local import is needed, because this is not available in all environments
        import cmk.base.cee.bakery.agent_bakery as agent_bakery  # pylint: disable=redefined-outer-name,import-outside-toplevel
    except ImportError:
        return

    assert isinstance(config_cache, config.CEEConfigCache)

    with nullcontext() if skip_locking else lock_checkmk_configuration():
        target_configs = agent_bakery.BakeryTargetConfigs.from_config_cache(
            config_cache, selected_hosts=None
        )

    agent_bakery.bake_on_restart(target_configs)


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
            broken_config_path = cmk.utils.paths.tmp_dir / "check_mk_objects.cfg.broken"
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
) -> None:
    config_warnings.initialize()

    _verify_non_duplicate_hosts(duplicates)
    _verify_non_deprecated_checkgroups()

    config_path = next(VersionedConfigPath.current())
    with config_path.create(is_cmc=core.is_cmc()), _backup_objects_file(core):
        core.create_config(config_path, config_cache, hosts_to_update=hosts_to_update)

    cmk.utils.password_store.save_for_helpers(config_path)


def _verify_non_deprecated_checkgroups() -> None:
    """Verify that the user has no deprecated check groups configured."""
    # 'check_plugin.check_ruleset_name' is of type RuleSetName, which is an PluginName (good),
    # but config.checkgroup_parameters contains strings (todo)
    check_ruleset_names_with_plugin = {
        str(plugin.check_ruleset_name)
        for plugin in agent_based_register.iter_all_check_plugins()
        if plugin.check_ruleset_name
    }

    for checkgroup in config.checkgroup_parameters:
        if checkgroup not in check_ruleset_names_with_plugin:
            config_warnings.warn(
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
        config_warnings.warn(
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
    params: Mapping[str, object],
) -> str:
    """
    Raises:
        KeyError if the special agent is deactivated.

    """

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
    )
    return f"{path} {args}"


def make_special_agent_stdin(
    hostname: HostName,
    ipaddress: HostAddress | None,
    agentname: str,
    params: Mapping[str, object],
) -> str | None:
    info_func = config.special_agent_info[agentname]
    # TODO: We call a user supplied function here.
    # If this crashes during config generation, it can get quite ugly.
    # We should really wrap this and implement proper sanitation and exception handling.
    # Deal with this when modernizing the API (CMK-3812).
    agent_configuration = info_func(params, hostname, ipaddress)
    return getattr(agent_configuration, "stdin", None)


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
    attrs.update(
        ConfigCache._get_tag_attributes(config_cache.tags_of_service(hostname, description), "TAG")
    )

    attrs.update(
        ConfigCache._get_tag_attributes(
            config_cache.ruleset_matcher.labels_of_service(hostname, description), "LABEL"
        )
    )
    attrs.update(
        ConfigCache._get_tag_attributes(
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
