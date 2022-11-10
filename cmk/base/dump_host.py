#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from pathlib import Path
from typing import Optional, Union

import cmk.utils.render
import cmk.utils.tty as tty
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.paths import tmp_dir
from cmk.utils.type_defs import HostName, SourceType

import cmk.core_helpers.cache as file_cache
from cmk.core_helpers import (
    Fetcher,
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    TCPFetcher,
)
from cmk.core_helpers.type_defs import SourceInfo

import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
import cmk.base.sources as sources
from cmk.base.check_utils import LegacyCheckParameters
from cmk.base.config import HostConfig


def dump_source(source: SourceInfo, fetcher: Fetcher) -> str:
    # pylint: disable=too-many-branches
    if isinstance(fetcher, IPMIFetcher):
        description = "Management board - IPMI"
        items = []
        if fetcher.address:
            items.append("Address: %s" % fetcher.address)
        if fetcher.username:
            items.append("User: %s" % fetcher.username)
        if items:
            description = "%s (%s)" % (description, ", ".join(items))
        return description

    if isinstance(fetcher, PiggybackFetcher):
        return "Process piggyback data from %s" % (Path(tmp_dir) / "piggyback" / fetcher.hostname)

    if isinstance(fetcher, ProgramFetcher):
        response = [
            "Program: %s"
            % (
                fetcher.cmdline
                if isinstance(fetcher.cmdline, str)
                else fetcher.cmdline.decode("utf8")
            )
        ]
        if fetcher.stdin:
            response.extend(["  Program stdin:", fetcher.stdin])
        return "\n".join(response)

    if isinstance(fetcher, SNMPFetcher):
        snmp_config = fetcher.snmp_config
        if snmp_config.is_usewalk_host:
            return "SNMP (use stored walk)"

        if snmp_config.is_snmpv3_host:
            credentials_text = "Credentials: '%s'" % ", ".join(snmp_config.credentials)
        else:
            credentials_text = "Community: %r" % snmp_config.credentials

        if snmp_config.is_snmpv3_host or snmp_config.is_bulkwalk_host:
            bulk = "yes"
        else:
            bulk = "no"

        return "%s (%s, Bulk walk: %s, Port: %d, Backend: %s)" % (
            "SNMP" if source.source_type is SourceType.HOST else "Management board - SNMP",
            credentials_text,
            bulk,
            snmp_config.port,
            snmp_config.snmp_backend.value,
        )

    if isinstance(fetcher, TCPFetcher):
        return "TCP: %s:%d" % fetcher.address

    # Fallback for non-raw stuff.
    return type(fetcher).__name__


def dump_host(hostname: HostName) -> None:  # pylint: disable=too-many-branches
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    out.output("\n")
    if config_cache.is_cluster(hostname):
        nodes = config_cache.nodes_of(hostname)
        if nodes is None:
            raise RuntimeError()
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(nodes)) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    out.output("%s%s%s%-78s %s\n" % (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ipaddress = _ip_address_for_dump_host(
        hostname, host_config, family=host_config.default_address_family
    )

    addresses: Optional[str] = ""
    if not host_config.is_ipv4v6_host:
        addresses = ipaddress
    else:
        try:
            secondary = _ip_address_for_dump_host(
                hostname,
                host_config,
                family=socket.AF_INET if host_config.is_ipv6_primary else socket.AF_INET6,
            )
        except Exception:
            secondary = "X.X.X.X"

        addresses = "%s, %s" % (ipaddress, secondary)
        if host_config.is_ipv6_primary:
            addresses += " (Primary: IPv6)"
        else:
            addresses += " (Primary: IPv4)"

    out.output(
        tty.yellow
        + "Addresses:              "
        + tty.normal
        + (addresses if addresses is not None else "No IP")
        + "\n"
    )

    tag_template = tty.bold + "[" + tty.normal + "%s" + tty.bold + "]" + tty.normal
    tags = [(tag_template % ":".join(t)) for t in sorted(host_config.tag_groups.items())]
    out.output(tty.yellow + "Tags:                   " + tty.normal + ", ".join(tags) + "\n")

    labels = [tag_template % ":".join(l) for l in sorted(host_config.labels.items())]
    out.output(tty.yellow + "Labels:                 " + tty.normal + ", ".join(labels) + "\n")

    # TODO: Clean this up once cluster parent handling has been moved to HostConfig
    if config_cache.is_cluster(hostname):
        parents_list = config_cache.nodes_of(hostname)
        if parents_list is None:
            raise RuntimeError()
    else:
        parents_list = host_config.parents
    if len(parents_list) > 0:
        out.output(
            tty.yellow + "Parents:                " + tty.normal + ", ".join(parents_list) + "\n"
        )
    out.output(
        tty.yellow
        + "Host groups:            "
        + tty.normal
        + ", ".join(host_config.hostgroups)
        + "\n"
    )
    out.output(
        tty.yellow
        + "Contact groups:         "
        + tty.normal
        + ", ".join(host_config.contactgroups)
        + "\n"
    )

    agenttypes = [
        dump_source(source, fetcher)
        for source, _file_cache, fetcher in sources.make_non_cluster_sources(
            hostname,
            ipaddress,
            simulation_mode=config.simulation_mode,
            missing_sys_description=config.get_config_cache().in_binary_hostlist(
                hostname, config.snmp_without_sys_descr
            ),
            file_cache_max_age=file_cache.MaxAge.none(),
        )
    ]

    if host_config.is_ping_host:
        agenttypes.append("PING only")

    out.output(tty.yellow + "Agent mode:             " + tty.normal)
    out.output(host_config.agent_description + "\n")

    out.output(tty.yellow + "Type of agent:          " + tty.normal)
    if len(agenttypes) == 1:
        out.output(agenttypes[0] + "\n")
    else:
        out.output("\n  ")
        out.output("\n  ".join(agenttypes) + "\n")

    out.output(tty.yellow + "Services:" + tty.normal + "\n")

    headers = ["checktype", "item", "params", "description", "groups"]
    colors = [tty.normal, tty.blue, tty.normal, tty.green, tty.normal]

    table_data = []
    for service in sorted(
        check_table.get_check_table(hostname).values(), key=lambda s: s.description
    ):
        table_data.append(
            [
                str(service.check_plugin_name),
                str(service.item),
                _evaluate_params(service.parameters),
                service.description,
                ",".join(config_cache.servicegroups_of_service(hostname, service.description)),
            ]
        )

    tty.print_table(headers, colors, table_data, "  ")


def _evaluate_params(params: Union[LegacyCheckParameters, TimespecificParameters]) -> str:
    if not isinstance(params, TimespecificParameters):
        return repr(params)

    if params.is_constant():
        return repr(params.evaluate(cmk.base.core.timeperiod_active))
    return "Timespecific parameters at %s: %r" % (
        cmk.utils.render.date_and_time(time.time()),
        params.evaluate(cmk.base.core.timeperiod_active),
    )


def _ip_address_for_dump_host(
    host_name: HostName,
    host_config: HostConfig,
    *,
    family: socket.AddressFamily,
) -> Optional[str]:
    config_cache = config.get_config_cache()
    try:
        return config.lookup_ip_address(host_config, family=family)
    except Exception:
        return "" if config_cache.is_cluster(host_name) else ip_lookup.fallback_ip_for(family)
