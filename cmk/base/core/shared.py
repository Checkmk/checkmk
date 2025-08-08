#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Callable, Iterable, Sequence
from typing import Literal

import cmk.ccc.debug
import cmk.utils.paths
from cmk import trace
from cmk.base.config import ConfigCache, ObjectAttributes
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.plugins import ServiceID
from cmk.utils import config_warnings, ip_lookup
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import Labels
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.tags import TagGroupID, TagID

CoreCommandName = str
CoreCommand = str

tracer = trace.get_tracer()


ActiveServiceID = tuple[str, Item]
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
        "ERROR: Duplicate service name (%s check) '%s' for host '%s'!\n"
        " - 1st occurrence: check plug-in / item: %s / %r\n"
        " - 2nd occurrence: check plug-in / item: %s / %r\n"
        % (checktype, description, host_name, *first_occurrence, *second_occurrence)
    )


# TODO: Just for documentation purposes for now.
#
# HostCheckCommand = NewType(
#     "HostCheckCommand",
#     Literal["smart", "ping", "ok", "agent"]
#     | tuple[Literal["service"], TextInput]
#     | tuple[Literal["tcp"], Integer]
#     | tuple[Literal["custom"], TextInput],
# )


def _cluster_ping_command(
    config_cache: ConfigCache,
    host_name: HostName,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ip: HostAddress,
) -> CoreCommand | None:
    ping_args = check_icmp_arguments_of(config_cache, host_name, family)
    if ip:  # Do check cluster IP address if one is there
        return "check-mk-host-ping!%s" % ping_args
    if ping_args:  # use check_icmp in cluster mode
        return "check-mk-host-ping-cluster!%s" % ping_args
    return None


def host_check_command(
    config_cache: ConfigCache,
    host_name: HostName,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ip: HostAddress,
    is_clust: bool,
    default_host_check_command: str,
    host_check_via_service_status: Callable,
    host_check_via_custom_check: Callable,
) -> CoreCommand | None:
    value = config_cache.host_check_command(host_name, default_host_check_command)

    if value == "smart":
        if is_clust:
            return _cluster_ping_command(config_cache, host_name, family, ip)
        return "check-mk-host-smart"

    if value == "ping":
        if is_clust:
            return _cluster_ping_command(config_cache, host_name, family, ip)
        ping_args = check_icmp_arguments_of(config_cache, host_name, family)
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
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    add_defaults: bool = True,
) -> str:
    levels = config_cache.ping_levels(hostname)
    if not add_defaults and not levels:
        return ""

    args = []

    if family is socket.AddressFamily.AF_INET6:
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


def get_cmk_passive_service_attributes(
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    service_labels: Labels,
    check_mk_attrs: ObjectAttributes,
    extra_icon: str | None,
) -> ObjectAttributes:
    attrs = get_service_attributes(
        config_cache,
        host_name,
        service_name,
        service_labels,
        extra_icon,
    )

    attrs["check_interval"] = check_mk_attrs["check_interval"]

    return attrs


def get_service_attributes(
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    service_labels: Labels,
    extra_icon: str | None,
) -> ObjectAttributes:
    attrs: ObjectAttributes = _extra_service_attributes(
        config_cache, host_name, service_name, service_labels, extra_icon
    )
    attrs.update(
        ConfigCache._get_tag_attributes(
            config_cache.tags_of_service(host_name, service_name, service_labels), "TAG"
        )
    )
    attrs.update(ConfigCache._get_tag_attributes(service_labels, "LABEL"))
    attrs.update(ConfigCache._get_tag_attributes(service_labels, "LABELSOURCE"))
    return attrs


def _extra_service_attributes(
    config_cache: ConfigCache,
    host_name: HostName,
    service_name: ServiceName,
    service_labels: Labels,
    extra_icon: str | None,
) -> ObjectAttributes:
    attrs = {}  # ObjectAttributes

    # Add service custom_variables. Name conflicts are prevented by the GUI, but just
    # to be sure, add them first. The other definitions will override the custom attributes.
    for varname, value in config_cache.custom_attributes_of_service(
        host_name, service_name, service_labels
    ).items():
        attrs["_%s" % varname.upper()] = value

    attrs.update(config_cache.extra_attributes_of_service(host_name, service_name, service_labels))

    # Add explicit custom_variables
    for varname, value in ConfigCache.get_explicit_service_custom_variables(
        host_name, service_name
    ).items():
        attrs["_%s" % varname.upper()] = value

    # Add custom user icons and actions
    actions = config_cache.icons_and_actions_of_service(
        host_name, service_name, service_labels, extra_icon
    )
    if actions:
        attrs["_ACTIONS"] = ",".join(actions)
    return attrs


def get_labels_from_attributes(key_value_pairs: list[tuple[str, str]]) -> Labels:
    return {key[8:]: value for key, value in key_value_pairs if key.startswith("__LABEL_")}


def get_tags_with_groups_from_attributes(
    key_value_pairs: list[tuple[str, str]],
) -> dict[TagGroupID, TagID]:
    return {
        TagGroupID(key[6:]): TagID(value)
        for key, value in key_value_pairs
        if key.startswith("__TAG_")
    }


def get_cluster_nodes_for_config(
    host_name: HostName,
    nodes: Sequence[HostName],
    ip_stack_config: ip_lookup.IPStackConfig,
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
    host_tags: cmk.utils.tags.HostTags,
    # these two argemnts and their usage are result of a refactoring.
    # I am not convinced if it really makes sense to call this callback on eveny host.
    all_existing_hosts: Iterable[HostName],
    is_monitored_host: Callable[[HostName], bool],
) -> Sequence[HostName]:
    _verify_cluster_address_family(host_name, ip_stack_config, nodes, default_address_family)
    _verify_cluster_datasource(host_name, nodes, host_tags)
    monitored_hosts = {h for h in all_existing_hosts if is_monitored_host(h)}
    nodes = list(nodes[:])
    for node in nodes:
        if node not in monitored_hosts:
            config_warnings.warn(
                f"Node '{node}' of cluster '{host_name}' is not a monitored host in this site."
            )
            nodes.remove(node)
    return nodes


def _verify_cluster_address_family(
    host_name: HostName,
    ip_stack_config: ip_lookup.IPStackConfig,
    nodes: Iterable[HostName],
    default_address_family: Callable[
        [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
) -> None:
    if ip_stack_config is IPStackConfig.NO_IP:
        cluster_host_family = None
        address_families = []
    else:
        cluster_host_family = (
            "IPv6" if default_address_family(host_name) is socket.AF_INET6 else "IPv4"
        )
        address_families = [
            f"{host_name}: {cluster_host_family}",
        ]

    address_family = cluster_host_family
    mixed = False
    for nodename in nodes:
        family = "IPv6" if default_address_family(nodename) is socket.AF_INET6 else "IPv4"
        address_families.append(f"{nodename}: {family}")
        if address_family is None:
            address_family = family
        elif address_family != family:
            mixed = True

    if mixed:
        config_warnings.warn(
            f"""Cluster '{host_name}' has different primary address families: {", ".join(address_families)}"""
        )


def _verify_cluster_datasource(
    host_name: HostName,
    nodes: Iterable[HostName],
    host_tags: cmk.utils.tags.HostTags,
) -> None:
    cluster_tg = host_tags.tags(host_name)
    cluster_agent_ds = cluster_tg.get(TagGroupID("agent"))
    cluster_snmp_ds = cluster_tg.get(TagGroupID("snmp_ds"))
    for nodename in nodes:
        node_tg = host_tags.tags(nodename)
        node_agent_ds = node_tg.get(TagGroupID("agent"))
        node_snmp_ds = node_tg.get(TagGroupID("snmp_ds"))
        warn_text = f"Cluster '{host_name}' has different datasources as its node"
        if node_agent_ds != cluster_agent_ds:
            config_warnings.warn(
                f"{warn_text} '{nodename}': {cluster_agent_ds} vs. {node_agent_ds}"
            )
        if node_snmp_ds != cluster_snmp_ds:
            config_warnings.warn(f"{warn_text} '{nodename}': {cluster_snmp_ds} vs. {node_snmp_ds}")
