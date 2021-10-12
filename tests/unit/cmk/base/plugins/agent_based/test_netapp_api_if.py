#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import netapp_api_if
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.utils import interfaces


@pytest.mark.parametrize(
    "string_table, discovery_results, items_params_results",
    [
        (
            [
                [
                    "interface GTB1020-2-CL_mgmt",
                    "comment -",
                    "use-failover-group unused",
                    "address 191.128.142.33",
                    "dns-domain-name none",
                    "is-auto-revert false",
                    "lif-uuid d3233231-a1d3-12e6-a4ff-00a0231e0e11",
                    "firewall-policy mgmt",
                    "vserver FSS2220-2-CL",
                    "role cluster_mgmt",
                    "netmask-length 24",
                    "data-protocols.data-protocol none",
                    "operational-status up",
                    "ipspace Default",
                    "netmask 255.255.254.0",
                    "failover-policy broadcast_domain_wide",
                    "home-node FSS2220-2",
                    "address-family ipv4",
                    "current-port e0f-112",
                    "current-node FSS2220-2",
                    "is-dns-update-enabled false",
                    "subnet-name MGMT",
                    "listen-for-dns-query false",
                    "administrative-status up",
                    "failover-group MGMT-Netz",
                    "home-port e0f-112",
                    "is-home true",
                    "operational-speed 1000",
                    "send_data 0",
                    "send_errors 0",
                    "link-status up",
                    "recv_errors 0",
                    "send_packet 0",
                    "recv_packet 0",
                    "instance_name FSS2220-2-CL_mgmt",
                    "recv_data 0",
                ],
                [
                    "interface GTB1020-2_ic1",
                    "comment -",
                    "use-failover-group unused",
                    "address 10.12.1.4",
                    "dns-domain-name none",
                    "is-auto-revert false",
                    "lif-uuid sdfd13d4d-82db-12c5-a2ff-00a123e0e49",
                    "firewall-policy intercluster",
                    "vserver FSS2220-1-DL",
                    "role intercluster",
                    "netmask-length 24",
                    "data-protocols.data-protocol none",
                    "operational-status up",
                    "ipspace Default",
                    "netmask 255.255.244.0",
                    "failover-policy local_only",
                    "home-node FSS2220-2",
                    "address-family ipv4",
                    "current-port e0f-1137",
                    "current-node FSS2220-2",
                    "listen-for-dns-query false",
                    "administrative-status up",
                    "failover-group Intercluster",
                    "home-port e0f-2231",
                    "is-home true",
                    "operational-speed 1000",
                    "send_data 142310234",
                    "send_errors 0",
                    "link-status up",
                    "recv_errors 0",
                    "send_packet 2223111",
                    "recv_packet 2223411",
                    "instance_name FSS2220_ic1",
                    "recv_data 122333190",
                ],
            ],
            [
                Service(
                    item="1",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
                Service(
                    item="2",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
            ],
            [
                (
                    "1",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 1000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[GTB1020-2-CL_mgmt]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="Speed: 1 GBit/s"),
                        Result(state=state.OK, summary="Current Port: e0f-112 (is home port)"),
                    ],
                ),
                (
                    "2",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 1000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[GTB1020-2_ic1]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="Speed: 1 GBit/s"),
                        Result(state=state.OK, summary="Current Port: e0f-2231 (is home port)"),
                    ],
                ),
            ],
        ),
        (
            [
                [
                    "interface e0a",
                    "mediatype auto-1000t-fd-up",
                    "flowcontrol full",
                    "mtusize 9000",
                    "ipspace-name default-ipspace",
                    "mac-address 01:b0:89:22:df:01",
                ],
                [
                    "interface e0b",
                    "mediatype auto-1000t-fd-up",
                    "flowcontrol full",
                    "mtusize 9000",
                    "ipspace-name default-ipspace",
                    "mac-address 01:b0:89:22:df:01",
                ],
                [
                    "interface e0c",
                    "ipspace-name default-ipspace",
                    "flowcontrol full",
                    "mediatype auto-1000t-fd-up",
                    "mac-address 01:b0:89:22:df:02",
                ],
                [
                    "interface e0d",
                    "ipspace-name default-ipspace",
                    "flowcontrol full",
                    "mediatype auto-1000t-fd-up",
                    "mac-address 01:b0:89:22:df:02",
                ],
                [
                    "interface ifgrp_sto",
                    "v4-primary-address.ip-address-info.address 11.12.121.33",
                    "v4-primary-address.ip-address-info.addr-family af-inet",
                    "mtusize 9000",
                    "v4-primary-address.ip-address-info.netmask-or-prefix 255.255.255.220",
                    "v4-primary-address.ip-address-info.broadcast 12.13.142.33",
                    "ipspace-name default-ipspace",
                    "mac-address 01:b0:89:22:df:01",
                    "v4-primary-address.ip-address-info.creator vfiler:vfiler0",
                    "send_mcasts 1360660",
                    "recv_errors 0",
                    "instance_name ifgrp_sto",
                    "send_errors 0",
                    "send_data 323931282332034",
                    "recv_mcasts 1234567",
                    "v4-primary-address.ip-address-info.address 11.12.121.21",
                    "v4-primary-address.ip-address-info.addr-family af-inet",
                    "v4-primary-address.ip-address-info.netmask-or-prefix 255.255.253.0",
                    "v4-primary-address.ip-address-info.broadcast 14.11.123.255",
                    "ipspace-name default-ipspace",
                    "mac-address 01:b0:89:22:df:02",
                    "v4-primary-address.ip-address-info.creator vfiler:vfiler0",
                    "send_mcasts 166092",
                    "recv_errors 0",
                    "instance_name ifgrp_srv-600",
                    "send_errors 0",
                    "send_data 12367443455534",
                    "recv_mcasts 2308439",
                    "recv_data 412332323639",
                ],
            ],
            [
                Service(
                    item="5",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
            ],
            [
                (
                    "5",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 1000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[ifgrp_sto]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: 01:B0:89:22:DF:02"),
                        Result(state=state.OK, summary="Speed: 1 GBit/s"),
                        Result(state=state.OK, summary="Physical interfaces: e0c(up)"),
                        Result(state=state.OK, summary="e0d(up)"),
                    ],
                ),
            ],
        ),
        (
            [
                [
                    "interface cluster_mgmt",
                    "comment -",
                    "is-vip false",
                    "address 111.222.333.444",
                    "dns-domain-name none",
                    "is-auto-revert false",
                    "lif-uuid 000-000-000",
                    "firewall-policy mgmt",
                    "vserver peknasc01",
                    "role cluster_mgmt",
                    "netmask-length 23",
                    "data-protocols.data-protocol none",
                    "operational-status up",
                    "ipspace Default",
                    "netmask 255.255.254.0",
                    "failover-policy broadcast_domain_wide",
                    "home-node myhome",
                    "use-failover-group unused",
                    "address-family ipv4",
                    "current-port e0a",
                    "current-node mynode",
                    "service-policy custom-management-14861",
                    "listen-for-dns-query false",
                    "service-names.lif-service-name management_portmap",
                    "administrative-status up",
                    "failover-group Default",
                    "home-port e0a",
                    "is-home true",
                    "operational-speed auto",
                    "send_data 0",
                    "send_errors 0",
                    "link-status up",
                    "recv_errors 0",
                    "send_packet 0",
                    "recv_packet 0",
                    "instance_name cluster_mgmt",
                    "recv_data 0",
                ],
            ],
            [
                Service(
                    item="1",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 0,
                    },
                ),
            ],
            [
                (
                    "1",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 0,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=state.OK, summary="[cluster_mgmt]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="Speed: auto"),
                        Result(state=state.OK, summary="Current Port: e0a (is home port)"),
                    ],
                ),
            ],
        ),
    ],
)
def test_netapp_api_if_regression(
    monkeypatch,
    string_table,
    discovery_results,
    items_params_results,
):
    section = netapp_api_if.parse_netapp_api_if(string_table)

    assert (
        list(
            netapp_api_if.discover_netapp_api_if(
                [(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
                section,
            )
        )
        == discovery_results
    )

    monkeypatch.setattr(interfaces, "get_value_store", lambda: {})
    for item, par, res in items_params_results:
        assert (
            list(
                netapp_api_if.check_netapp_api_if(
                    item,
                    (par),
                    section,
                )
            )
            == res
        )
