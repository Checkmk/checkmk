#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from pathlib import Path
from typing import Literal

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.render
import cmk.utils.tty as tty
from cmk.utils.hostaddress import HostAddress, HostName, Hosts
from cmk.utils.paths import tmp_dir
from cmk.utils.tags import ComputedDataSources
from cmk.utils.timeperiod import timeperiod_active

from cmk.snmplib import SNMPBackendEnum, SNMPVersion

from cmk.fetchers import (
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    TCPFetcher,
    TLSConfig,
)
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkengine.fetcher import SourceType
from cmk.checkengine.parameters import TimespecificParameters

import cmk.base.config as config
import cmk.base.core
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
import cmk.base.sources as sources
from cmk.base.config import ConfigCache
from cmk.base.ip_lookup import IPStackConfig
from cmk.base.sources import Source


def dump_source(source: Source) -> str:  # pylint: disable=too-many-branches
    fetcher = source.fetcher()
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
        return f"Process piggyback data from {tmp_dir / 'piggyback' / str(fetcher.hostname)}"

    if isinstance(fetcher, ProgramFetcher):
        response = [f"Program: {fetcher.cmdline}"]
        if fetcher.stdin:
            response.extend(["  Program stdin:", fetcher.stdin])
        return "\n".join(response)

    if isinstance(fetcher, SNMPFetcher):
        snmp_config = fetcher.snmp_config
        if snmp_config.snmp_backend is SNMPBackendEnum.STORED_WALK:
            return "SNMP (use stored walk)"

        if snmp_config.snmp_version is SNMPVersion.V3:
            credentials_text = "Credentials: '%s'" % ", ".join(snmp_config.credentials)
        else:
            credentials_text = "Community: %r" % snmp_config.credentials

        bulk = "yes" if snmp_config.use_bulkwalk else "no"

        return "%s%s (%s, Bulkwalk: %s, Port: %d, Backend: %s)" % (
            (
                "SNMP"
                if source.source_info().source_type is SourceType.HOST
                else "Management board - SNMP"
            ),
            snmp_config.snmp_version.name.lower(),
            credentials_text,
            bulk,
            snmp_config.port,
            snmp_config.snmp_backend.value,
        )

    if isinstance(fetcher, TCPFetcher):
        return "TCP: %s:%d" % fetcher.address

    # Fallback for non-raw stuff.
    return type(fetcher).__name__


def _agent_description(cds: ComputedDataSources) -> str:
    if cds.is_all_agents_host:
        return "Normal Checkmk agent, all configured special agents"

    if cds.is_all_special_agents_host:
        return "No Checkmk agent, all configured special agents"

    if cds.is_tcp:
        return "Normal Checkmk agent, or special agent if configured"

    return "No agent"


def dump_host(config_cache: ConfigCache, hostname: HostName) -> None:
    # pylint: disable=too-many-branches
    out.output("\n")
    hosts_config = config_cache.hosts_config
    if hostname in hosts_config.clusters:
        assert config_cache.nodes(hostname)
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(config_cache.nodes(hostname))) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    out.output("%s%s%s%-78s %s\n" % (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ip_stack_config = ConfigCache.ip_stack_config(hostname)
    ipaddress = (
        None
        if ip_stack_config is IPStackConfig.NO_IP
        else _ip_address_for_dump_host(
            config_cache,
            hosts_config,
            hostname,
            family=config_cache.default_address_family(hostname),
        )
    )

    addresses: str | None = ""
    if ip_stack_config is not IPStackConfig.DUAL_STACK:
        addresses = ipaddress
    else:
        try:
            secondary = str(
                _ip_address_for_dump_host(
                    config_cache,
                    hosts_config,
                    hostname,
                    family=config_cache.default_address_family(hostname),
                )
            )
        except Exception:
            secondary = "X.X.X.X"

        addresses = f"{ipaddress}, {secondary}"
        if config_cache.default_address_family(hostname) is socket.AF_INET6:
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

    if hostname in hosts_config.clusters:
        parents_list = config_cache.nodes(hostname)
    else:
        parents_list = config_cache.parents(hostname)

    if parents_list:
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

    oid_cache_dir = Path(cmk.utils.paths.snmp_scan_cache_dir)
    stored_walk_path = Path(cmk.utils.paths.snmpwalks_dir)
    walk_cache_path = Path(cmk.utils.paths.var_dir) / "snmp_cache"
    file_cache_path = Path(cmk.utils.paths.data_source_cache_dir)
    tcp_cache_path = Path(cmk.utils.paths.tcp_cache_dir)
    tls_config = TLSConfig(
        cas_dir=Path(cmk.utils.paths.agent_cas_dir),
        ca_store=Path(cmk.utils.paths.agent_cert_store),
        site_crt=Path(cmk.utils.paths.site_cert_file),
    )
    used_password_store = cmk.utils.password_store.pending_password_store_path()
    agenttypes = [
        dump_source(source)
        for source in sources.make_sources(
            hostname,
            ipaddress,
            ConfigCache.ip_stack_config(hostname),
            is_cluster=hostname in hosts_config.clusters,
            file_cache_options=FileCacheOptions(),
            config_cache=config_cache,
            simulation_mode=config.simulation_mode,
            file_cache_max_age=MaxAge.zero(),
            snmp_backend_override=None,
            oid_cache_dir=oid_cache_dir,
            stored_walk_path=stored_walk_path,
            walk_cache_path=walk_cache_path,
            file_cache_path=file_cache_path,
            tcp_cache_path=tcp_cache_path,
            tls_config=tls_config,
            password_store_file=used_password_store,
            passwords=cmk.utils.password_store.load(used_password_store),
        )
    ]

    if config_cache.is_ping_host(hostname):
        agenttypes.append("PING only")

    out.output(tty.yellow + "Agent mode:             " + tty.normal)
    out.output(_agent_description(config_cache.computed_datasources(hostname)) + "\n")

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
    for service in sorted(config_cache.check_table(hostname).values(), key=lambda s: s.description):
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


def _evaluate_params(params: TimespecificParameters) -> str:
    return (
        repr(params.evaluate(timeperiod_active))
        if params.is_constant()
        else "Timespecific parameters at {}: {!r}".format(
            cmk.utils.render.date_and_time(time.time()),
            params.evaluate(timeperiod_active),
        )
    )


def _ip_address_for_dump_host(
    config_cache: ConfigCache,
    hosts_config: Hosts,
    host_name: HostName,
    *,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
) -> HostAddress | None:
    try:
        return config.lookup_ip_address(config_cache, host_name, family=family)
    except Exception:
        return (
            HostAddress("")
            if host_name in hosts_config.clusters
            else ip_lookup.fallback_ip_for(family)
        )
