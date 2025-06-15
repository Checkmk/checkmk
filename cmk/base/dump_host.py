#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Literal

from cmk.ccc import tty
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostName

import cmk.utils.password_store
import cmk.utils.paths
import cmk.utils.render
from cmk.utils.ip_lookup import IPLookup, IPLookupOptional, IPStackConfig
from cmk.utils.paths import tmp_dir
from cmk.utils.tags import ComputedDataSources
from cmk.utils.timeperiod import timeperiod_active

from cmk.snmplib import SNMPBackendEnum, SNMPVersion

from cmk.fetchers import (
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SNMPScanConfig,
    TCPFetcher,
    TLSConfig,
)
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkengine.fetcher import SourceType
from cmk.checkengine.parameters import TimespecificParameters
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base import sources
from cmk.base.config import ConfigCache
from cmk.base.configlib.servicename import PassiveServiceNameConfig
from cmk.base.sources import SNMPFetcherConfig, Source


def dump_source(source: Source) -> str:
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
            credentials_text = f"Community: {snmp_config.credentials!r}"

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


def print_(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


def dump_host(
    config_cache: ConfigCache,
    service_name_config: PassiveServiceNameConfig,
    plugins: AgentBasedPlugins,
    hostname: HostName,
    ip_stack_config: IPStackConfig,
    primary_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    *,
    ip_address_of: IPLookup,
    ip_address_of_mgmt: IPLookupOptional,
    simulation_mode: bool,
) -> None:
    print_("\n")
    label_manager = config_cache.label_manager
    hosts_config = config_cache.hosts_config

    if hostname in hosts_config.clusters:
        assert config_cache.nodes(hostname)
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(config_cache.nodes(hostname))) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    print_("%s%s%s%-78s %s\n" % (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ipaddress = (
        None if ip_stack_config is IPStackConfig.NO_IP else ip_address_of(hostname, primary_family)
    )

    addresses: str | None = ""
    if ip_stack_config is not IPStackConfig.DUAL_STACK:
        addresses = ipaddress
    else:
        try:
            secondary = str(ip_address_of(hostname, _complementary_family(primary_family)))
        except Exception:
            secondary = "X.X.X.X"

        addresses = f"{ipaddress}, {secondary}"
        if primary_family is socket.AF_INET6:
            addresses += " (Primary: IPv6)"
        else:
            addresses += " (Primary: IPv4)"

    print_(
        tty.yellow
        + "Addresses:              "
        + tty.normal
        + (addresses if addresses is not None else "No IP")
        + "\n"
    )

    tag_template = tty.bold + "[" + tty.normal + "%s" + tty.bold + "]" + tty.normal
    tags = [
        (tag_template % ":".join(t)) for t in sorted(config_cache.host_tags.tags(hostname).items())
    ]
    print_(tty.yellow + "Tags:                   " + tty.normal + ", ".join(tags) + "\n")

    labels = [
        tag_template % ":".join(l) for l in sorted(label_manager.labels_of_host(hostname).items())
    ]
    print_(tty.yellow + "Labels:                 " + tty.normal + ", ".join(labels) + "\n")

    if hostname in hosts_config.clusters:
        parents_list = config_cache.nodes(hostname)
    else:
        parents_list = config_cache.parents(hostname)

    if parents_list:
        print_(
            tty.yellow + "Parents:                " + tty.normal + ", ".join(parents_list) + "\n"
        )
    print_(
        tty.yellow
        + "Host groups:            "
        + tty.normal
        + ", ".join(config_cache.hostgroups(hostname))
        + "\n"
    )
    print_(
        tty.yellow
        + "Contact groups:         "
        + tty.normal
        + ", ".join(config_cache.contactgroups(hostname))
        + "\n"
    )

    oid_cache_dir = cmk.utils.paths.snmp_scan_cache_dir
    stored_walk_path = cmk.utils.paths.snmpwalks_dir
    walk_cache_path = cmk.utils.paths.var_dir / "snmp_cache"
    file_cache_path = cmk.utils.paths.data_source_cache_dir
    tcp_cache_path = cmk.utils.paths.tcp_cache_dir
    tls_config = TLSConfig(
        cas_dir=Path(cmk.utils.paths.agent_cas_dir),
        ca_store=Path(cmk.utils.paths.agent_cert_store),
        site_crt=Path(cmk.utils.paths.site_cert_file),
    )
    used_password_store = cmk.utils.password_store.pending_password_store_path()
    passwords = cmk.utils.password_store.load(used_password_store)
    agenttypes = [
        dump_source(source)
        for source in sources.make_sources(
            plugins,
            hostname,
            primary_family,
            ipaddress,
            ip_stack_config,
            fetcher_factory=config_cache.fetcher_factory(
                config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
                ip_address_of,
            ),
            snmp_fetcher_config=SNMPFetcherConfig(
                scan_config=SNMPScanConfig(
                    on_error=OnError.RAISE,
                    missing_sys_description=config_cache.missing_sys_description(hostname),
                    oid_cache_dir=oid_cache_dir,
                ),
                selected_sections=NO_SELECTION,
                backend_override=None,
                stored_walk_path=stored_walk_path,
                walk_cache_path=walk_cache_path,
            ),
            is_cluster=hostname in hosts_config.clusters,
            file_cache_options=FileCacheOptions(),
            simulation_mode=simulation_mode,
            file_cache_max_age=MaxAge.zero(),
            snmp_backend=config_cache.get_snmp_backend(hostname),
            file_cache_path=file_cache_path,
            tcp_cache_path=tcp_cache_path,
            tls_config=tls_config,
            computed_datasources=config_cache.computed_datasources(hostname),
            datasource_programs=config_cache.datasource_programs(hostname),
            tag_list=config_cache.host_tags.tag_list(hostname),
            management_ip=ip_address_of_mgmt(hostname, primary_family),
            management_protocol=config_cache.management_protocol(hostname),
            special_agent_command_lines=config_cache.special_agent_command_lines(
                hostname,
                primary_family,
                ipaddress,
                password_store_file=used_password_store,
                passwords=passwords,
                ip_address_of=ip_address_of,
            ),
            agent_connection_mode=config_cache.agent_connection_mode(hostname),
            check_mk_check_interval=config_cache.check_mk_check_interval(hostname),
        )
    ]

    if config_cache.is_ping_host(hostname):
        agenttypes.append("PING only")

    print_(tty.yellow + "Agent mode:             " + tty.normal)
    print_(_agent_description(config_cache.computed_datasources(hostname)) + "\n")

    print_(tty.yellow + "Type of agent:          " + tty.normal)
    if len(agenttypes) == 1:
        print_(agenttypes[0] + "\n")
    else:
        print_("\n  ")
        print_("\n  ".join(agenttypes) + "\n")

    print_(tty.yellow + "Services:" + tty.normal + "\n")

    headers = ["checktype", "item", "params", "description", "groups"]
    colors = [tty.normal, tty.blue, tty.normal, tty.green, tty.normal]

    table_data = []
    for service in sorted(
        config_cache.check_table(
            hostname,
            plugins.check_plugins,
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            service_name_config,
        ).values(),
        key=lambda s: s.description,
    ):
        table_data.append(
            [
                str(service.check_plugin_name),
                str(service.item),
                _evaluate_params(service.parameters),
                service.description,
                ",".join(
                    config_cache.servicegroups_of_service(
                        hostname, service.description, service.labels
                    )
                ),
            ]
        )

    tty.print_table(headers, colors, table_data, "  ")


def _complementary_family(
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
) -> Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]:
    match family:
        case socket.AddressFamily.AF_INET:
            return socket.AddressFamily.AF_INET6
        case socket.AddressFamily.AF_INET6:
            return socket.AddressFamily.AF_INET


def _evaluate_params(params: TimespecificParameters) -> str:
    return (
        repr(params.evaluate(timeperiod_active))
        if params.is_constant()
        else f"Timespecific parameters at {cmk.utils.render.date_and_time(time.time())}: {params.evaluate(timeperiod_active)!r}"
    )
