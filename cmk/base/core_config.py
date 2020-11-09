#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import numbers
import os
import sys
import shutil
from typing import AnyStr, Callable, Dict, List, Optional, Tuple, Union, Iterator, Final, Iterable
from contextlib import contextmanager, suppress
from pathlib import Path

import cmk.utils.version as cmk_version
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.password_store
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import (
    CheckPluginName,
    HostAddress,
    HostName,
    Labels,
    LabelSources,
    ServiceName,
    ConfigSerial,
    LATEST_SERIAL,
)

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.obsolete_output as out
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
from cmk.base.config import (
    HostConfig,
    ConfigCache,
    HostCheckCommand,
    Tags,
    ObjectAttributes,
)
from cmk.base.check_utils import Service, LegacyCheckParameters
from cmk.base.nagios_utils import do_check_nagiosconfig

ConfigurationWarnings = List[str]
ObjectMacros = Dict[str, AnyStr]
CoreCommandName = str
CoreCommand = str
CheckCommandArguments = Iterable[Union[int, float, str, Tuple[str, str, str]]]


class HelperConfig:
    """Managing the helper core config generations below var/check_mk/core/helper-config/[serial]

    The context manager ensures that the directory for the config serial is created and the "latest"
    link is only created in case the context is left without exception.
    """
    def __init__(self, serial: ConfigSerial) -> None:
        self.serial: Final[ConfigSerial] = serial
        self.serial_path: Final[Path] = config.make_helper_config_path(serial)
        self.latest_path: Final[Path] = config.make_helper_config_path(LATEST_SERIAL)

    @contextmanager
    def create(self) -> Iterator["HelperConfig"]:
        self._cleanup()

        self.serial_path.mkdir(parents=True, exist_ok=True)
        yield self
        self._create_latest_link()

    def _create_latest_link(self) -> None:
        with suppress(FileNotFoundError):
            self.latest_path.unlink()
        self.latest_path.symlink_to(self.serial_path.name)

    def _cleanup(self) -> None:
        """Cleanup old helper configs

        This is only used when using the Nagios core. The Microcore cares about the cleanup on it's
        own, because the Microcore holds the information which configs are still needed."""
        if config.monitoring_core == "cmc":
            return

        if not cmk.utils.paths.core_helper_config_dir.exists():
            return

        latest_config_path = self.latest_path.resolve()
        for config_path in cmk.utils.paths.core_helper_config_dir.iterdir():
            if config_path.is_symlink() or not config_path.is_dir():
                continue

            if config_path == latest_config_path:
                continue

            shutil.rmtree(config_path)


def new_helper_config_serial() -> ConfigSerial:
    """Acquire and return the next helper config serial

    This ID is used to identify a core helper configuration generation. It is used to store the
    helper config on the file system below var/check_mk/core/helper_config/[serial]. It needs to
    be unique compared to all currently known serials (the ones that exist in the directory
    mentioned above).
    """
    serial_file = cmk.utils.paths.core_helper_config_dir / "serial.mk"

    serial: int = store.load_object_from_file(serial_file, default=0, lock=True)
    serial += 1

    store.save_object_to_file(serial_file, serial)
    return ConfigSerial(str(serial))


class MonitoringCore(metaclass=abc.ABCMeta):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    def create_config(self, serial: ConfigSerial) -> None:
        raise NotImplementedError


_ignore_ip_lookup_failures = False
_failed_ip_lookups: List[HostName] = []

#.
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
    num_warnings = len(g_configuration_warnings)

    if num_warnings > 10:
        warnings = (g_configuration_warnings[:10] +
                    ["%d further warnings have been omitted" % (num_warnings - 10)])
    else:
        warnings = g_configuration_warnings

    return warnings


def duplicate_service_warning(
    *,
    checktype: str,
    description: str,
    host_name: HostName,
    first_occurrence: Tuple[Union[str, CheckPluginName], Optional[str]],
    second_occurrence: Tuple[Union[str, CheckPluginName], Optional[str]],
) -> None:
    return warning("ERROR: Duplicate service description (%s check) '%s' for host '%s'!\n"
                   " - 1st occurrence: check plugin / item: %s / %r\n"
                   " - 2nd occurrence: check plugin / item: %s / %r\n" %
                   (checktype, description, host_name, *first_occurrence, *second_occurrence))


# TODO: Just for documentation purposes for now, add typing_extensions and use this.
#
# HostCheckCommand = NewType('HostCheckCommand',
#                            Union[Literal["smart"],
#                                  Literal["ping"],
#                                  Literal["ok"],
#                                  Literal["agent"],
#                                  Tuple[Literal["service"], TextUnicode],
#                                  Tuple[Literal["tcp"], Integer],
#                                  Tuple[Literal["custom"], TextAscii]])


def _get_host_check_command(host_config: HostConfig,
                            default_host_check_command: str) -> HostCheckCommand:
    explicit_command = host_config.explicit_check_command
    if explicit_command is not None:
        return explicit_command
    if host_config.is_no_ip_host:
        return "ok"
    return default_host_check_command


def _cluster_ping_command(config_cache: ConfigCache, host_config: HostConfig,
                          ip: HostAddress) -> Optional[CoreCommand]:
    ping_args = check_icmp_arguments_of(config_cache, host_config.hostname)
    if ip:  # Do check cluster IP address if one is there
        return "check-mk-host-ping!%s" % ping_args
    if ping_args:  # use check_icmp in cluster mode
        return "check-mk-host-ping-cluster!%s" % ping_args
    return None


def host_check_command(config_cache: ConfigCache, host_config: HostConfig, ip: HostAddress,
                       is_clust: bool, default_host_check_command: str,
                       host_check_via_service_status: Callable,
                       host_check_via_custom_check: Callable) -> Optional[CoreCommand]:
    value = _get_host_check_command(host_config, default_host_check_command)

    if value == "smart":
        if is_clust:
            return _cluster_ping_command(config_cache, host_config, ip)
        return "check-mk-host-smart"

    if value == "ping":
        if is_clust:
            return _cluster_ping_command(config_cache, host_config, ip)
        ping_args = check_icmp_arguments_of(config_cache, host_config.hostname)
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
        return host_check_via_custom_check("check-mk-custom",
                                           "check-mk-custom!" + autodetect_plugin(value[1]))

    raise MKGeneralException("Invalid value %r for host_check_command of host %s." %
                             (value, host_config.hostname))


def autodetect_plugin(command_line: str) -> str:
    plugin_name = command_line.split()[0]
    if command_line[0] in ['$', '/']:
        return command_line

    for directory in ["/local", ""]:
        path = cmk.utils.paths.omd_root + directory + "/lib/nagios/plugins/"
        if os.path.exists(path + plugin_name):
            command_line = str(path + command_line)
            break

    return command_line


def check_icmp_arguments_of(config_cache: ConfigCache,
                            hostname: HostName,
                            add_defaults: bool = True,
                            family: Optional[int] = None) -> str:
    host_config = config_cache.get_host_config(hostname)
    levels = host_config.ping_levels

    if not add_defaults and not levels:
        return ""

    if family is None:
        family = 6 if host_config.is_ipv6_primary else 4

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
    args.append("-w %.2f,%.2f%%" % (rta[0], loss[0]))
    args.append("-c %.2f,%.2f%%" % (rta[1], loss[1]))
    return " ".join(args)


#.
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


def do_create_config(core: MonitoringCore) -> None:
    """Creating the monitoring core configuration and additional files

    Ensures that everything needed by the monitoring core and it's helper processes is up-to-date
    and available for starting the monitoring.
    """
    out.output("Generating configuration for core (type %s)..." % core.name())
    try:
        _create_core_config(core)
        out.output(tty.ok + "\n")
    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKGeneralException("Error creating configuration: %s" % e)

    _bake_on_restart()


def _bake_on_restart():
    try:
        # Local import is needed, because this is not available in all environments
        import cmk.base.cee.bakery.agent_bakery as agent_bakery  # pylint: disable=redefined-outer-name,import-outside-toplevel
        agent_bakery.bake_on_restart()
    except ImportError:
        pass


@contextmanager
def _backup_objects_file(core: MonitoringCore) -> Iterator[None]:
    if config.monitoring_core == "nagios":
        objects_file = cmk.utils.paths.nagios_objects_file
    else:
        objects_file = cmk.utils.paths.var_dir + "/core/config"

    backup_path = None
    if os.path.exists(objects_file):
        backup_path = objects_file + ".save"
        os.rename(objects_file, backup_path)

    try:
        try:
            yield None
        except Exception:
            if backup_path:
                os.rename(backup_path, objects_file)
            raise

        if (config.monitoring_core == "nagios" and
                Path(cmk.utils.paths.nagios_config_file).exists() and not do_check_nagiosconfig()):
            broken_config_path = Path(cmk.utils.paths.tmp_dir) / "check_mk_objects.cfg.broken"
            shutil.move(cmk.utils.paths.nagios_objects_file, broken_config_path)

            if backup_path:
                os.rename(backup_path, objects_file)
            elif os.path.exists(objects_file):
                os.remove(objects_file)

            raise MKGeneralException("Configuration for monitoring core is invalid. Rolling back. "
                                     "The broken file has been copied to \"%s\" for analysis." %
                                     broken_config_path)
    finally:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)


def _create_core_config(core: MonitoringCore) -> ConfigurationWarnings:
    initialize_warnings()

    _verify_non_duplicate_hosts()
    _verify_non_deprecated_checkgroups()

    with HelperConfig(
            new_helper_config_serial()).create() as helper_config, _backup_objects_file(core):
        core.create_config(helper_config.serial)

    cmk.utils.password_store.save(config.stored_passwords)

    return get_configuration_warnings()


def _verify_non_deprecated_checkgroups() -> None:
    """Verify that the user has no deprecated check groups configured.
    """
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
                "Found configured rules of deprecated check group \"%s\". These rules are not used "
                "by any check. Maybe this check group has been renamed during an update, "
                "in this case you will have to migrate your configuration to the new ruleset manually. "
                "Please check out the release notes of the involved versions. "
                "You may use the page \"Deprecated rules\" in WATO to view your rules and move them to "
                "the new rulesets." % checkgroup)


def _verify_non_duplicate_hosts() -> None:
    duplicates = config.duplicate_hosts()
    if duplicates:
        warning("The following host names have duplicates: %s. "
                "This might lead to invalid/incomplete monitoring for these hosts." %
                ", ".join(duplicates))


#.
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


def active_check_arguments(hostname: HostName, description: Optional[ServiceName],
                           args: config.SpecialAgentInfoFunctionResult) -> str:
    if isinstance(args, str):
        return args

    cmd_args: CheckCommandArguments = []
    if isinstance(args, config.SpecialAgentConfiguration):
        cmd_args = args.args
    else:
        cmd_args = args

    if not isinstance(cmd_args, list):
        raise MKGeneralException(
            "The check argument function needs to return either a list of arguments or a "
            "string of the concatenated arguments (Host: %s, Service: %s)." %
            (hostname, description))

    return _prepare_check_command(cmd_args, hostname, description)


def _prepare_check_command(command_spec: CheckCommandArguments, hostname: HostName,
                           description: Optional[ServiceName]) -> str:
    """Prepares a check command for execution by Checkmk

    In case a list is given it quotes the single elements. It also prepares password store entries
    for the command line. These entries will be completed by the executed program later to get the
    password from the password store.
    """
    passwords: List[Tuple[str, str, str]] = []
    formated: List[str] = []
    for arg in command_spec:
        if isinstance(arg, (int, float)):
            formated.append("%s" % arg)

        elif isinstance(arg, str):
            formated.append(cmk.utils.quote_shell_string(arg))

        elif isinstance(arg, tuple) and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
            try:
                password = config.stored_passwords[pw_ident]["password"]
            except KeyError:
                if hostname and description:
                    descr = " used by service \"%s\" on host \"%s\"" % (description, hostname)
                elif hostname:
                    descr = " used by host host \"%s\"" % (hostname)
                else:
                    descr = ""

                console.warning("The stored password \"%s\"%s does not exist (anymore)." %
                                (pw_ident, descr))
                password = "%%%"

            pw_start_index = str(preformated_arg.index("%s"))
            formated.append(cmk.utils.quote_shell_string(preformated_arg % ("*" * len(password))))
            passwords.append((str(len(formated)), pw_start_index, pw_ident))

        else:
            raise MKGeneralException("Invalid argument for command line: %r" % (arg,))

    if passwords:
        formated = ["--pwstore=%s" % ",".join(["@".join(p) for p in passwords])] + formated

    return " ".join(formated)


#.
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
    host_config: HostConfig,
    service: Service,
    check_mk_attrs: ObjectAttributes,
) -> ObjectAttributes:
    attrs = get_service_attributes(
        host_config.hostname,
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
    check_plugin_name: Optional[CheckPluginName] = None,
    params: LegacyCheckParameters = None,
) -> ObjectAttributes:
    attrs: ObjectAttributes = _extra_service_attributes(hostname, description, config_cache,
                                                        check_plugin_name, params)
    attrs.update(_get_tag_attributes(config_cache.tags_of_service(hostname, description), "TAG"))

    # TODO: Remove ignore once we are on Python 3
    attrs.update(_get_tag_attributes(config_cache.labels_of_service(hostname, description),
                                     "LABEL"))
    # TODO: Remove ignore once we are on Python 3
    attrs.update(
        _get_tag_attributes(config_cache.label_sources_of_service(hostname, description),
                            "LABELSOURCE"))
    return attrs


def _extra_service_attributes(
    hostname: HostName,
    description: ServiceName,
    config_cache: ConfigCache,
    check_plugin_name: Optional[CheckPluginName],
    params: LegacyCheckParameters,
) -> ObjectAttributes:
    attrs = {}  # ObjectAttributes

    # Add service custom_variables. Name conflicts are prevented by the GUI, but just
    # to be sure, add them first. The other definitions will override the custom attributes.
    for varname, value in config_cache.custom_attributes_of_service(hostname, description).items():
        attrs["_%s" % varname.upper()] = value

    attrs.update(config_cache.extra_attributes_of_service(hostname, description))

    # Add explicit custom_variables
    for varname, value in config_cache.get_explicit_service_custom_variables(hostname,
                                                                             description).items():
        attrs["_%s" % varname.upper()] = value

    # Add custom user icons and actions
    actions = config_cache.icons_and_actions_of_service(hostname, description, check_plugin_name,
                                                        params)
    if actions:
        attrs["_ACTIONS"] = ','.join(actions)
    return attrs


#.
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


def get_host_attributes(hostname: HostName, config_cache: ConfigCache) -> ObjectAttributes:
    host_config = config_cache.get_host_config(hostname)
    attrs = host_config.extra_host_attributes

    # Pre 1.6 legacy attribute. We have changed our whole code to use the
    # livestatus column "tags" which is populated by all attributes starting with
    # "__TAG_" instead. We may deprecate this is one day.
    attrs["_TAGS"] = " ".join(sorted(config_cache.get_host_config(hostname).tags))

    attrs.update(_get_tag_attributes(host_config.tag_groups, "TAG"))
    attrs.update(_get_tag_attributes(host_config.labels, "LABEL"))
    attrs.update(_get_tag_attributes(host_config.label_sources, "LABELSOURCE"))

    if "alias" not in attrs:
        attrs["alias"] = host_config.alias

    # Now lookup configured IP addresses
    v4address: Optional[str] = None
    if host_config.is_ipv4_host:
        v4address = ip_address_of(host_config, 4)

    if v4address is None:
        v4address = ""
    attrs["_ADDRESS_4"] = v4address

    v6address: Optional[str] = None
    if host_config.is_ipv6_host:
        v6address = ip_address_of(host_config, 6)
    if v6address is None:
        v6address = ""
    attrs["_ADDRESS_6"] = v6address

    ipv6_primary = host_config.is_ipv6_primary
    if ipv6_primary:
        attrs["address"] = attrs["_ADDRESS_6"]
        attrs["_ADDRESS_FAMILY"] = "6"
    else:
        attrs["address"] = attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "4"

    add_ipv4addrs, add_ipv6addrs = host_config.additional_ipaddresses
    if add_ipv4addrs:
        attrs["_ADDRESSES_4"] = " ".join(add_ipv4addrs)
        for nr, ipv4_address in enumerate(add_ipv4addrs):
            key = "_ADDRESS_4_%s" % (nr + 1)
            attrs[key] = ipv4_address

    if add_ipv6addrs:
        attrs["_ADDRESSES_6"] = " ".join(add_ipv6addrs)
        for nr, ipv6_address in enumerate(add_ipv6addrs):
            key = "_ADDRESS_6_%s" % (nr + 1)
            attrs[key] = ipv6_address

    # Add the optional WATO folder path
    path = config.host_paths.get(hostname)
    if path:
        attrs["_FILENAME"] = path

    # Add custom user icons and actions
    actions = host_config.icons_and_actions
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)

    if cmk_version.is_managed_edition():
        attrs["_CUSTOMER"] = config.current_customer  # type: ignore[attr-defined]

    return attrs


def _get_tag_attributes(collection: Union[Tags, Labels, LabelSources],
                        prefix: str) -> ObjectAttributes:
    return {u"__%s_%s" % (prefix, k): str(v) for k, v in collection.items()}


def get_cluster_attributes(config_cache: config.ConfigCache, host_config: config.HostConfig,
                           nodes: List[str]) -> Dict:
    sorted_nodes = sorted(nodes)

    attrs = {
        "_NODENAMES": " ".join(sorted_nodes),
    }
    node_ips_4 = []
    if host_config.is_ipv4_host:
        for h in sorted_nodes:
            node_config = config_cache.get_host_config(h)
            addr = ip_address_of(node_config, 4)
            if addr is not None:
                node_ips_4.append(addr)
            else:
                node_ips_4.append(fallback_ip_for(node_config, 4))

    node_ips_6 = []
    if host_config.is_ipv6_host:
        for h in sorted_nodes:
            node_config = config_cache.get_host_config(h)
            addr = ip_address_of(node_config, 6)
            if addr is not None:
                node_ips_6.append(addr)
            else:
                node_ips_6.append(fallback_ip_for(node_config, 6))

    node_ips = node_ips_6 if host_config.is_ipv6_primary else node_ips_4

    for suffix, val in [("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6)]:
        attrs["_NODEIPS%s" % suffix] = " ".join(val)

    return attrs


def get_cluster_nodes_for_config(config_cache: ConfigCache,
                                 host_config: HostConfig) -> List[HostName]:

    if host_config.nodes is None:
        return []

    nodes = host_config.nodes[:]
    _verify_cluster_address_family(nodes, config_cache, host_config)
    _verify_cluster_datasource(nodes, config_cache, host_config)
    for node in nodes:
        if node not in config_cache.all_active_realhosts():
            warning("Node '%s' of cluster '%s' is not a monitored host in this site." %
                    (node, host_config.hostname))
            nodes.remove(node)
    return nodes


def _verify_cluster_address_family(nodes: List[str], config_cache: config.ConfigCache,
                                   host_config: config.HostConfig) -> None:
    cluster_host_family = "IPv6" if host_config.is_ipv6_primary else "IPv4"

    address_families = [
        "%s: %s" % (host_config.hostname, cluster_host_family),
    ]

    address_family = cluster_host_family
    mixed = False
    for nodename in nodes:
        node_config = config_cache.get_host_config(nodename)
        family = "IPv6" if node_config.is_ipv6_primary else "IPv4"
        address_families.append("%s: %s" % (nodename, family))
        if address_family is None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        warning("Cluster '%s' has different primary address families: %s" %
                (host_config.hostname, ", ".join(address_families)))


def _verify_cluster_datasource(nodes: List[str], config_cache: config.ConfigCache,
                               host_config: config.HostConfig) -> None:
    cluster_tg = host_config.tag_groups
    cluster_agent_ds = cluster_tg.get("agent")
    cluster_snmp_ds = cluster_tg.get("snmp_ds")

    for nodename in nodes:
        node_tg = config_cache.get_host_config(nodename).tag_groups
        node_agent_ds = node_tg.get("agent")
        node_snmp_ds = node_tg.get("snmp_ds")
        warn_text = "Cluster '%s' has different datasources as its node" % host_config.hostname
        if node_agent_ds != cluster_agent_ds:
            warning("%s '%s': %s vs. %s" % (warn_text, nodename, cluster_agent_ds, node_agent_ds))
        if node_snmp_ds != cluster_snmp_ds:
            warning("%s '%s': %s vs. %s" % (warn_text, nodename, cluster_snmp_ds, node_snmp_ds))


def ip_address_of(host_config: config.HostConfig, family: Optional[int] = None) -> Optional[str]:
    try:
        return ip_lookup.lookup_ip_address(host_config, family)
    except Exception as e:
        if host_config.is_cluster:
            return ""

        _failed_ip_lookups.append(host_config.hostname)
        if not _ignore_ip_lookup_failures:
            warning("Cannot lookup IP address of '%s' (%s). "
                    "The host will not be monitored correctly." % (host_config.hostname, e))
        return fallback_ip_for(host_config, family)


def ignore_ip_lookup_failures() -> None:
    global _ignore_ip_lookup_failures
    _ignore_ip_lookup_failures = True


def failed_ip_lookups() -> List[HostName]:
    return _failed_ip_lookups


def fallback_ip_for(host_config: HostConfig, family: Optional[int] = None) -> str:
    if family is None:
        family = 6 if host_config.is_ipv6_primary else 4

    if family == 4:
        return "0.0.0.0"

    return "::"


def get_host_macros_from_attributes(hostname: HostName, attrs: ObjectAttributes) -> ObjectMacros:
    macros = {
        "$HOSTNAME$": hostname,
        "$HOSTADDRESS$": attrs['address'],
        "$HOSTALIAS$": attrs['alias'],
    }

    # Add custom macros
    for macro_name, value in attrs.items():
        if macro_name[0] == '_':
            macros["$HOST" + macro_name + "$"] = value
            # Be compatible to nagios making $_HOST<VARNAME>$ out of the config _<VARNAME> configs
            macros["$_HOST" + macro_name[1:] + "$"] = value

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
