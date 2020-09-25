#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Iterable,
    Mapping,
    Sequence,
    Tuple,
    TypedDict,
)
from .agent_based_api.v1 import (
    check_levels,
    register,
    render,
    Result,
    Service,
    SNMPTree,
    State as state,
    type_defs,
)
from .utils.netscaler import SNMP_DETECT

netscaler_vserver_states = {
    "0": (1, "unknown"),
    "1": (2, "down"),
    "2": (1, "unknown"),
    "3": (1, "busy"),
    "4": (1, "out of service"),
    "5": (1, "transition to out of service"),
    "7": (0, "up"),
}

netscaler_vserver_types = {
    "0": "http",
    "1": "ftp",
    "2": "tcp",
    "3": "udp",
    "4": "ssl bridge",
    "5": "monitor",
    "6": "monitor udp",
    "7": "nntp",
    "8": "http server",
    "9": "http client",
    "10": "rpc server",
    "11": "rpc client",
    "12": "nat",
    "13": "any",
    "14": "ssl",
    "15": "dns",
    "16": "adns",
    "17": "snmp",
    "18": "ha",
    "19": "monitor ping",
    "20": "sslOther tcp",
    "21": "aaa",
    "23": "secure monitor",
    "24": "ssl vpn udp",
    "25": "rip",
    "26": "dns client",
    "27": "rpc server",
    "28": "rpc client",
    "62": "service unknown",
    "69": "tftp",
}

netscaler_vserver_entitytypes = {
    "0": "unknown",
    "1": "loadbalancing",
    "2": "loadbalancing group",
    "3": "ssl vpn",
    "4": "content switching",
    "5": "cache redirection",
}


class VServer(TypedDict, total=False):
    service_state: Tuple[int, str]
    entity_service_type: str
    protocol: str
    socket: str
    request_rate: int
    rx_bytes: int
    tx_bytes: int
    health: float
    node: str


Section = Mapping[str, VServer]


def _to_vserver(line: Iterable[str]) -> Tuple[str, VServer]:
    """
    >>> import pprint
    >>> pprint.pprint(_to_vserver([
    ... 'lb_eas', '0.0.0.0', '0', '14', '7', '100', '1', '0', '0', '0', 'lb_eas',
    ... ]))
    ('lb_eas',
     {'entity_service_type': 'loadbalancing',
      'health': 100.0,
      'protocol': 'ssl',
      'request_rate': 0,
      'rx_bytes': 0,
      'service_state': (0, 'up'),
      'socket': '0.0.0.0:0',
      'tx_bytes': 0})
    """
    (name, ip, port, svr_type, svr_state, svr_health, svr_entitytype, request_rate, rx_bytes,
     tx_bytes, full_name) = line
    vserver: VServer = {
        'service_state': netscaler_vserver_states.get(svr_state, (1, "unknown")),
        'entity_service_type': netscaler_vserver_entitytypes.get(svr_entitytype,
                                                                 "unknown (%s)" % svr_entitytype),
        'protocol': netscaler_vserver_types.get(svr_type, "service unknown (%s)" % svr_type),
        'socket': '%s:%s' % (ip, port),
        'request_rate': int(request_rate),
        'rx_bytes': int(rx_bytes),
        'tx_bytes': int(tx_bytes),
    }
    if svr_entitytype in {"1", "2"}:
        vserver['health'] = float(svr_health)
    return full_name or name, vserver


def parse_netscaler_vserver(string_table: type_defs.SNMPStringTable) -> Section:
    """
    >>> import pprint
    >>> pprint.pprint(parse_netscaler_vserver([[
    ... ['lb_eas', '0.0.0.0', '0', '14', '7', '100', '1', '0', '0', '0', 'lb_eas'],
    ... ['citrix.ehg.directory', '10.101.6.11', '443', '14', '7', '0', '3', '0', '0', '0', 'citrix.ehg.directory'],
    ... ['cag.erwinhymergroup.com', '10.101.6.12', '443', '14', '7', '0', '3', '0', '0', '0', 'cag.erwinhymergroup.com'],
    ... ]]))
    {'cag.erwinhymergroup.com': {'entity_service_type': 'ssl vpn',
                                 'protocol': 'ssl',
                                 'request_rate': 0,
                                 'rx_bytes': 0,
                                 'service_state': (0, 'up'),
                                 'socket': '10.101.6.12:443',
                                 'tx_bytes': 0},
     'citrix.ehg.directory': {'entity_service_type': 'ssl vpn',
                              'protocol': 'ssl',
                              'request_rate': 0,
                              'rx_bytes': 0,
                              'service_state': (0, 'up'),
                              'socket': '10.101.6.11:443',
                              'tx_bytes': 0},
     'lb_eas': {'entity_service_type': 'loadbalancing',
                'health': 100.0,
                'protocol': 'ssl',
                'request_rate': 0,
                'rx_bytes': 0,
                'service_state': (0, 'up'),
                'socket': '0.0.0.0:0',
                'tx_bytes': 0}}
    """
    return dict(_to_vserver(line) for line in string_table[0])


register.snmp_section(
    name="netscaler_vserver",
    parse_function=parse_netscaler_vserver,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.5951.4.1.3.1.1",
            oids=[  # nsVserverGroup.vserverTable.vserverEntry
                "1",  # vsvrName
                "2",  # vsvrIpAddress
                "3",  # vsvrPort
                "4",  # vsvrType
                "5",  # vsvrState
                "62",  # vsvrHealth
                "64",  # vsvrEntityType
                "43",  # NS-ROOT-MIB::vsvrRequestRate
                "44",  # NS-ROOT-MIB::vsvrRxBytesRate
                "45",  # NS-ROOT-MIB::vsvrTxBytesRate
                "59",  # vsvrFullName
            ],
        ),
    ],
    detect=SNMP_DETECT,
)


def discover_netscaler_vserver(section: Section) -> type_defs.DiscoveryResult:
    """
    >>> import pprint
    >>> pprint.pprint(list(discover_netscaler_vserver({
    ... 'cag.erwinhymergroup.com': {},
    ... 'citrix.ehg.directory': {},
    ... })))
    [Service(item='cag.erwinhymergroup.com', parameters={}, labels=[]),
     Service(item='citrix.ehg.directory', parameters={}, labels=[])]
    """
    for srv_name in section:
        yield Service(item=srv_name)


def _check_netscaler_vservers(
    params: type_defs.Parameters,
    vsevers: Sequence[VServer],
) -> type_defs.CheckResult:
    """
    >>> for result in _check_netscaler_vservers(
    ...     type_defs.Parameters({"health_levels": (100.0, 0.1), "cluster_status": "best"}),
    ...     [{
    ...         'entity_service_type': 'loadbalancing',
    ...         'health': 100.0,
    ...         'protocol': 'ssl',
    ...         'request_rate': 0,
    ...         'rx_bytes': 0,
    ...         'service_state': (0, 'up'),
    ...         'socket': '0.0.0.0:0',
    ...         'tx_bytes': 0,
    ...     }]):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='Status: up', details='Status: up')
    Result(state=<State.OK: 0>, summary='Health: 100%', details='Health: 100%')
    Metric('health_perc', 100.0, levels=(None, None), boundaries=(0.0, 100.0))
    Result(state=<State.OK: 0>, summary='Type: loadbalancing, Protocol: ssl, Socket: 0.0.0.0:0', details='Type: loadbalancing, Protocol: ssl, Socket: 0.0.0.0:0')
    Result(state=<State.OK: 0>, summary='Request rate: 0/s', details='Request rate: 0/s')
    Metric('request_rate', 0.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='In: 0.00 Bit/s', details='In: 0.00 Bit/s')
    Metric('if_in_octets', 0.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='Out: 0.00 Bit/s', details='Out: 0.00 Bit/s')
    Metric('if_out_octets', 0.0, levels=(None, None), boundaries=(None, None))
    """
    if not vsevers:
        return

    cluster_status = params.get('cluster_status', 'best')
    stat_list = []
    req_rate_list, rx_list, tx_list = [0], [0], [0]

    for vserver in vsevers:
        stat_list.append(vserver['service_state'][0])
        req_rate_list.append(vserver['request_rate'])
        rx_list.append(vserver['rx_bytes'])
        tx_list.append(vserver['tx_bytes'])

    min_state = min(stat_list)
    yield from (Result(
        state=state(min_state if cluster_status == 'best' else vserver['service_state'][0]),
        summary="Status: %s%s" % (
            vserver['service_state'][1],
            " (%s)" % vserver['node'] if 'node' in vserver else "",
        ),
    ) for vserver in vsevers)

    first_vserver = vsevers[0]
    if first_vserver['entity_service_type'] in ['loadbalancing', 'loadbalancing group']:
        yield from check_levels(
            value=first_vserver['health'],
            levels_lower=params["health_levels"],
            metric_name="health_perc",
            render_func=render.percent,
            label="Health",
            boundaries=(0, 100),
        )

    yield Result(
        state=state.OK,
        summary="Type: %s, Protocol: %s, Socket: %s" % (
            first_vserver['entity_service_type'],
            first_vserver['protocol'],
            first_vserver['socket'],
        ),
    )

    for metric_value, metric_name, render_func, label in [
        (max(req_rate_list), "request_rate", lambda x: str(x) + "/s", "Request rate"),
        (max(rx_list), "if_in_octets", render.networkbandwidth, "In"),
        (max(tx_list), "if_out_octets", render.networkbandwidth, "Out"),
    ]:
        yield from check_levels(
            value=metric_value,
            metric_name=metric_name,
            render_func=render_func,
            label=label,
        )


def check_netscaler_vserver(
    item: str,
    params: type_defs.Parameters,
    section: Section,
) -> type_defs.CheckResult:
    """
    >>> par = type_defs.Parameters({"health_levels": (100.0, 0.1), "cluster_status": "best"})
    >>> assert list(check_netscaler_vserver('item', par, {})) == []
    >>> vserver = {
    ...     'entity_service_type': 'loadbalancing',
    ...     'health': 100.0,
    ...     'protocol': 'ssl',
    ...     'request_rate': 0,
    ...     'rx_bytes': 0,
    ...     'service_state': (0, 'up'),
    ...     'socket': '0.0.0.0:0',
    ...     'tx_bytes': 0,
    ... }
    >>> assert list(check_netscaler_vserver('item', par, {'item': vserver})) == list(
    ... _check_netscaler_vservers(par, [vserver]))
    """
    yield from _check_netscaler_vservers(
        params,
        [section[item]] if item in section else [],
    )


def cluster_check_netscaler_vserver(
    item: str,
    params: type_defs.Parameters,
    section: Mapping[str, Section],
) -> type_defs.CheckResult:
    """
    >>> par = type_defs.Parameters({"health_levels": (100.0, 0.1), "cluster_status": "best"})
    >>> vserver = {
    ...     'entity_service_type': 'loadbalancing',
    ...     'health': 100.0,
    ...     'protocol': 'ssl',
    ...     'request_rate': 0,
    ...     'rx_bytes': 0,
    ...     'service_state': (0, 'up'),
    ...     'socket': '0.0.0.0:0',
    ...     'tx_bytes': 0,
    ... }
    >>> assert list(cluster_check_netscaler_vserver(
    ... 'item',
    ... par,
    ... {'node1': {'item': vserver}, 'node2': {}})) == list(
    ... _check_netscaler_vservers(par, [{**vserver, 'node': 'node1'}]))
    """
    yield from _check_netscaler_vservers(
        params,
        [
            {
                # mypy unfortunately only accepts string literals as valid keys for TypedDicts
                **node_section[item],  # type: ignore[misc]
                'node': node_name,
            } for node_name, node_section in section.items() if item in node_section
        ],
    )


register.check_plugin(
    name="netscaler_vserver",
    service_name="VServer %s",
    discovery_function=discover_netscaler_vserver,
    check_ruleset_name="netscaler_vserver",
    check_default_parameters={
        "health_levels": (100.0, 0.1),
        "cluster_status": "best",
    },
    check_function=check_netscaler_vserver,
    cluster_check_function=cluster_check_netscaler_vserver,
)
