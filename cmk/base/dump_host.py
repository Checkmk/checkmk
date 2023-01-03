#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from pathlib import Path

import cmk.utils.render
import cmk.utils.tty as tty
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.paths import tmp_dir
from cmk.utils.type_defs import HostName

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.fetchers import (
    Fetcher,
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SourceInfo,
    SourceType,
    TCPFetcher,
)
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkers.check_table import LegacyCheckParameters

import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
import cmk.base.sources as sources
from cmk.base.config import ConfigCache


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
            description = "{} ({})".format(description, ", ".join(items))
        return description

    if isinstance(fetcher, PiggybackFetcher):
        return "Process piggyback data from %s" % (Path(tmp_dir) / "piggyback" / fetcher.hostname)

    if isinstance(fetcher, ProgramFetcher):
        response = [f"Program: {fetcher.cmdline}"]
        if fetcher.stdin:
            response.extend(["  Program stdin:", fetcher.stdin])
        return "\n".join(response)

    if isinstance(fetcher, SNMPFetcher):
        snmp_config = fetcher.snmp_config
        if snmp_config.snmp_backend is SNMPBackendEnum.STORED_WALK:
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


def _agent_description(config_cache: ConfigCache, host_name: HostName) -> str:
    if config_cache.is_all_agents_host(host_name):
        return "Normal Checkmk agent, all configured special agents"

    if config_cache.is_all_special_agents_host(host_name):
        return "No Checkmk agent, all configured special agents"

    if config_cache.is_tcp_host(host_name):
        return "Normal Checkmk agent, or special agent if configured"

    return "No agent"


def dump_host(hostname: HostName) -> None:  # pylint: disable=too-many-branches
    config_cache = config.get_config_cache()

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
        hostname, family=config_cache.default_address_family(hostname)
    )

    addresses: str | None = ""
    if not ConfigCache.is_ipv4v6_host(hostname):
        addresses = ipaddress
    else:
        try:
            secondary = _ip_address_for_dump_host(
                hostname,
                family=config_cache.default_address_family(hostname),
            )
        except Exception:
            secondary = "X.X.X.X"

        addresses = f"{ipaddress}, {secondary}"
        if config_cache.is_ipv6_primary(hostname):
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
    tags = [(tag_template % ":".join(t)) for t in sorted(config_cache.tags(hostname).items())]
    out.output(tty.yellow + "Tags:                   " + tty.normal + ", ".join(tags) + "\n")

    labels = [tag_template % ":".join(l) for l in sorted(config_cache.labels(hostname).items())]
    out.output(tty.yellow + "Labels:                 " + tty.normal + ", ".join(labels) + "\n")

    if config_cache.is_cluster(hostname):
        parents_list = config_cache.nodes_of(hostname)
        if parents_list is None:
            raise RuntimeError()
    else:
        parents_list = config_cache.parents(hostname)
    if len(parents_list) > 0:
        out.output(
            tty.yellow + "Parents:                " + tty.normal + ", ".join(parents_list) + "\n"
        )
    out.output(
        tty.yellow
        + "Host groups:            "
        + tty.normal
        + ", ".join(config_cache.hostgroups(hostname))
        + "\n"
    )
    out.output(
        tty.yellow
        + "Contact groups:         "
        + tty.normal
        + ", ".join(config_cache.contactgroups(hostname))
        + "\n"
    )

    agenttypes = [
        dump_source(source, fetcher)
        for source, _file_cache, fetcher in sources.make_sources(
            hostname,
            ipaddress,
            file_cache_options=FileCacheOptions(),
            config_cache=config_cache,
            simulation_mode=config.simulation_mode,
            file_cache_max_age=MaxAge.none(),
        )
    ]

    if config_cache.is_ping_host(hostname):
        agenttypes.append("PING only")

    out.output(tty.yellow + "Agent mode:             " + tty.normal)
    out.output(_agent_description(config_cache, hostname) + "\n")

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
        config.get_check_table(config_cache, hostname).values(), key=lambda s: s.description
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


def _evaluate_params(params: LegacyCheckParameters | TimespecificParameters) -> str:
    if not isinstance(params, TimespecificParameters):
        return repr(params)

    if params.is_constant():
        return repr(params.evaluate(cmk.base.core.timeperiod_active))
    return "Timespecific parameters at {}: {!r}".format(
        cmk.utils.render.date_and_time(time.time()),
        params.evaluate(cmk.base.core.timeperiod_active),
    )


def _ip_address_for_dump_host(
    host_name: HostName,
    *,
    family: socket.AddressFamily,
) -> str | None:
    config_cache = config.get_config_cache()
    try:
        return config.lookup_ip_address(config_cache, host_name, family=family)
    except Exception:
        return "" if config_cache.is_cluster(host_name) else ip_lookup.fallback_ip_for(family)
