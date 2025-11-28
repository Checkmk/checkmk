#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import dataclasses
import os
import shutil
import socket
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Literal

import cmk.utils.config_path
import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.password_store
import cmk.utils.paths
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.labels import Labels
from cmk.utils.licensing.handler import LicensingHandler
from cmk.utils.licensing.helper import get_licensed_state_file_path
from cmk.utils.paths import core_helper_config_dir
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.store import (
    load_object_from_file,
    lock_checkmk_configuration,
    save_object_to_file,
)

from cmk.checkengine.checking import CheckPluginName, ConfiguredService, ServiceID
from cmk.checkengine.parameters import TimespecificParameters

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
import cmk.base.obsolete_output as out
from cmk.base.config import ConfigCache, ObjectAttributes
from cmk.base.nagios_utils import do_check_nagiosconfig

CoreCommandName = str
CoreCommand = str


@dataclasses.dataclass(frozen=True)
class CollectedHostLabels:
    host_labels: Labels
    service_labels: dict[ServiceName, Labels]


class MonitoringCore(abc.ABC):
    def __init__(self, licensing_handler_type: type[LicensingHandler]):
        self._licensing_handler_type = licensing_handler_type

    @classmethod
    @abc.abstractmethod
    def name(cls) -> Literal["nagios", "cmc"]:
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def is_cmc() -> bool:
        raise NotImplementedError

    def create_config(
        self,
        config_path: VersionedConfigPath,
        config_cache: ConfigCache,
        passwords: Mapping[str, str],
        hosts_to_update: set[HostName] | None = None,
    ) -> None:
        licensing_handler = self._licensing_handler_type.make()
        licensing_handler.persist_licensed_state(get_licensed_state_file_path())
        self._create_config(
            config_path, config_cache, licensing_handler, passwords, hosts_to_update
        )

    @abc.abstractmethod
    def _create_config(
        self,
        config_path: VersionedConfigPath,
        config_cache: ConfigCache,
        licensing_handler: LicensingHandler,
        passwords: Mapping[str, str],
        hosts_to_update: set[HostName] | None = None,
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
        " - 1st occurrence: check plug-in / item: %s / %r\n"
        " - 2nd occurrence: check plug-in / item: %s / %r\n"
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
    all_hosts: Iterable[HostName],
    hosts_to_update: set[HostName] | None = None,
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
        _bake_on_restart(config_cache, all_hosts, skip_config_locking_for_bakery)


def _bake_on_restart(
    config_cache: config.ConfigCache, all_hosts: Iterable[HostName], skip_locking: bool
) -> None:
    try:
        # Local import is needed, because this is not available in all environments
        import cmk.base.cee.bakery.agent_bakery as agent_bakery  # pylint: disable=redefined-outer-name,import-outside-toplevel

        from cmk.cee.bakery.type_defs import (  # pylint: disable=redefined-outer-name,import-outside-toplevel
            BakeRevisionMode,
        )

    except ImportError:
        return

    assert isinstance(config_cache, config.CEEConfigCache)

    with nullcontext() if skip_locking else lock_checkmk_configuration():
        target_configs = agent_bakery.BakeryTargetConfigs.from_config_cache(
            config_cache, all_hosts=all_hosts, selected_hosts=None
        )

    agent_bakery.bake_agents(
        target_configs,
        bake_revision_mode=(
            BakeRevisionMode.INACTIVE if config.apply_bake_revision else BakeRevisionMode.DISABLED
        ),
        logging_level=config.agent_bakery_logging,
        call_site="config creation",
    )


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
    hosts_to_update: set[HostName] | None = None,
    *,
    duplicates: Sequence[HostName],
) -> None:
    config_warnings.initialize()

    _verify_non_duplicate_hosts(duplicates)
    _verify_non_deprecated_checkgroups()

    # recompute and save passwords, to ensure consistency:
    passwords = config_cache.collect_passwords()
    cmk.utils.password_store.save(passwords, cmk.utils.password_store.pending_password_store_path())

    config_path = next(VersionedConfigPath.current())
    with config_path.create(is_cmc=core.is_cmc()), _backup_objects_file(core):
        core.create_config(
            config_path,
            config_cache,
            hosts_to_update=hosts_to_update,
            passwords=passwords,
        )
        cmk.utils.password_store.save(
            passwords, cmk.utils.password_store.core_password_store_path(config_path)
        )


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
                "by any check plug-in. Maybe this check group has been renamed during an update, "
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
            config_cache.ruleset_matcher.labels_of_service(hostname, description),
            "LABEL",
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
    labels_per_host: Mapping[HostName, CollectedHostLabels],
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
