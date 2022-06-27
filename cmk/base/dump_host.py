#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from typing import Optional, Union

import cmk.utils.render
import cmk.utils.tty as tty
from cmk.utils.parameters import TimespecificParameters
from cmk.utils.type_defs import HostName

import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.ip_lookup as ip_lookup
import cmk.base.obsolete_output as out
import cmk.base.sources as sources
from cmk.base.check_utils import LegacyCheckParameters


def dump_host(hostname: HostName) -> None:  # pylint: disable=too-many-branches
    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    out.output("\n")
    if host_config.is_cluster:
        nodes = host_config.nodes
        if nodes is None:
            raise RuntimeError()
        color = tty.bgmagenta
        add_txt = " (cluster of " + (", ".join(nodes)) + ")"
    else:
        color = tty.bgblue
        add_txt = ""
    out.output("%s%s%s%-78s %s\n" % (color, tty.bold, tty.white, hostname + add_txt, tty.normal))

    ipaddress = _ip_address_for_dump_host(host_config, family=host_config.default_address_family)

    addresses: Optional[str] = ""
    if not host_config.is_ipv4v6_host:
        addresses = ipaddress
    else:
        try:
            secondary = _ip_address_for_dump_host(
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
    if host_config.is_cluster:
        parents_list = host_config.nodes
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
        source.description for source in sources.make_non_cluster_sources(host_config, ipaddress)
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
    host_config: config.HostConfig,
    *,
    family: socket.AddressFamily,
) -> Optional[str]:
    try:
        return config.lookup_ip_address(host_config, family=family)
    except Exception:
        return "" if host_config.is_cluster else ip_lookup.fallback_ip_for(family)
