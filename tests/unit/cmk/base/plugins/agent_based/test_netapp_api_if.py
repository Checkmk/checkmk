#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import netapp_api_if
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
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
                        Result(state=State.OK, summary="[GTB1020-2-CL_mgmt]"),
                        Result(state=State.OK, summary="(up)", details="Operational state: up"),
                        Result(state=State.OK, summary="Speed: 1 GBit/s"),
                        Result(
                            state=State.OK,
                            notice="Could not compute rates for the following counter(s): in_octets: Initialized: 'in_octets.1.GTB1020-2-CL_mgmt..None', "
                            "in_ucast: Initialized: 'in_ucast.1.GTB1020-2-CL_mgmt..None', in_mcast: Initialized: 'in_mcast.1.GTB1020-2-CL_mgmt..None', "
                            "in_err: Initialized: 'in_err.1.GTB1020-2-CL_mgmt..None', out_octets: Initialized: 'out_octets.1.GTB1020-2-CL_mgmt..None', "
                            "out_ucast: Initialized: 'out_ucast.1.GTB1020-2-CL_mgmt..None', out_mcast: Initialized: 'out_mcast.1.GTB1020-2-CL_mgmt..None', "
                            "out_err: Initialized: 'out_err.1.GTB1020-2-CL_mgmt..None'",
                        ),
                        Result(state=State.OK, summary="Current Port: e0f-112 (is home port)"),
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
                        Result(state=State.OK, summary="[GTB1020-2_ic1]"),
                        Result(state=State.OK, summary="(up)", details="Operational state: up"),
                        Result(state=State.OK, summary="Speed: 1 GBit/s"),
                        Result(
                            state=State.OK,
                            notice="Could not compute rates for the following counter(s): in_octets: Initialized: 'in_octets.2.GTB1020-2_ic1..None', "
                            "in_ucast: Initialized: 'in_ucast.2.GTB1020-2_ic1..None', in_mcast: Initialized: 'in_mcast.2.GTB1020-2_ic1..None', "
                            "in_err: Initialized: 'in_err.2.GTB1020-2_ic1..None', out_octets: Initialized: 'out_octets.2.GTB1020-2_ic1..None', "
                            "out_ucast: Initialized: 'out_ucast.2.GTB1020-2_ic1..None', out_mcast: Initialized: 'out_mcast.2.GTB1020-2_ic1..None', "
                            "out_err: Initialized: 'out_err.2.GTB1020-2_ic1..None'",
                        ),
                        Result(state=State.OK, summary="Current Port: e0f-2231 (is home port)"),
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
                Service(
                    item="3",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
                Service(
                    item="4",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 1000000000,
                    },
                ),
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
                        Result(state=State.OK, summary="[ifgrp_sto]"),
                        Result(state=State.OK, summary="(up)", details="Operational state: up"),
                        Result(state=State.OK, summary="MAC: 01:B0:89:22:DF:02"),
                        Result(state=State.OK, summary="Speed: 1 GBit/s"),
                        Result(
                            state=State.OK,
                            notice="Could not compute rates for the following counter(s): in_octets: Initialized: 'in_octets.5.ifgrp_sto..None', "
                            "in_ucast: Initialized: 'in_ucast.5.ifgrp_sto..None', in_mcast: Initialized: 'in_mcast.5.ifgrp_sto..None', "
                            "in_err: Initialized: 'in_err.5.ifgrp_sto..None', out_octets: Initialized: 'out_octets.5.ifgrp_sto..None', "
                            "out_ucast: Initialized: 'out_ucast.5.ifgrp_sto..None', out_mcast: Initialized: 'out_mcast.5.ifgrp_sto..None', "
                            "out_err: Initialized: 'out_err.5.ifgrp_sto..None'",
                        ),
                        Result(state=State.OK, summary="Physical interfaces: e0c(up)"),
                        Result(state=State.OK, summary="e0d(up)"),
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
                        Result(state=State.OK, summary="[cluster_mgmt]"),
                        Result(state=State.OK, summary="(up)", details="Operational state: up"),
                        Result(state=State.OK, summary="Speed: auto"),
                        Result(
                            state=State.OK,
                            notice="Could not compute rates for the following counter(s): in_octets: Initialized: 'in_octets.1.cluster_mgmt..None', "
                            "in_ucast: Initialized: 'in_ucast.1.cluster_mgmt..None', in_mcast: Initialized: 'in_mcast.1.cluster_mgmt..None', "
                            "in_err: Initialized: 'in_err.1.cluster_mgmt..None', out_octets: Initialized: 'out_octets.1.cluster_mgmt..None', "
                            "out_ucast: Initialized: 'out_ucast.1.cluster_mgmt..None', out_mcast: Initialized: 'out_mcast.1.cluster_mgmt..None', "
                            "out_err: Initialized: 'out_err.1.cluster_mgmt..None'",
                        ),
                        Result(state=State.OK, summary="Current Port: e0a (is home port)"),
                    ],
                ),
            ],
        ),
        (
            [
                [
                    "interface some-if-name",
                    "address 127.0.0.1",
                    "address-family ipv4",
                    "administrative-status up",
                    "current-node node01",
                    "current-port e0c",
                    "data-protocols.data-protocol none",
                    "dns-domain-name none",
                    "failover-group Cluster",
                    "failover-policy local_only",
                    "home-node fasc01",
                    "home-port e0c",
                    "ipspace Cluster",
                    "is-auto-revert true",
                    "is-home true",
                    "is-vip false",
                    "lif-uuid 12345678-9abc-defc-86db-00a098abc029",
                    "listen-for-dns-query false",
                    "netmask 255.255.0.0",
                    "netmask-length 16",
                    "operational-status up",
                    "role cluster",
                    "service-names.lif-service-name cluster_core",
                    "service-policy default-cluster",
                    "use-failover-group unused",
                    "vserver Cluster",
                    "instance_name some-instance",
                    "recv_data 259146428473",
                    "recv_errors 0",
                    "recv_packet 255611925",
                    "send_data 530473658468",
                    "send_errors 0",
                    "send_packet 255131226",
                    "link-status up",
                    "operational-speed 10000",
                    "failover_ports fasc01|e0a|up;fasc01|e0c|up;fasc02|e0c|up;fasc02|e0a|up",
                ],
            ],
            [
                Service(
                    item="1",
                    parameters={
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 10000000000,
                    },
                ),
            ],
            [
                (
                    "1",
                    {
                        "errors": {"both": ("abs", (10, 20))},
                        "discovered_speed": 10000000000,
                        "discovered_oper_status": ["1"],
                    },
                    [
                        Result(state=State.OK, summary="[some-if-name]"),
                        Result(state=State.OK, summary="(up)", details="Operational state: up"),
                        Result(state=State.OK, summary="Speed: 10 GBit/s"),
                        Result(
                            state=State.OK,
                            notice="Could not compute rates for the following counter(s): in_octets: Initialized: 'in_octets.1.some-if-name..None', in_ucast: Initialized: 'in_ucast.1.some-if-name..None', in_mcast: Initialized: 'in_mcast.1.some-if-name..None', in_err: Initialized: 'in_err.1.some-if-name..None', out_octets: Initialized: 'out_octets.1.some-if-name..None', out_ucast: Initialized: 'out_ucast.1.some-if-name..None', out_mcast: Initialized: 'out_mcast.1.some-if-name..None', out_err: Initialized: 'out_err.1.some-if-name..None'",
                        ),
                        Result(state=State.OK, summary="Current Port: e0c (is home port)"),
                        Result(
                            state=State.OK,
                            notice="Failover Group: [fasc01:e0a=up, fasc01:e0c=up, fasc02:e0a=up, fasc02:e0c=up]",
                        ),
                    ],
                ),
            ],
        ),
    ],
)
def test_netapp_api_if_regression(
    string_table,
    discovery_results,
    items_params_results,
):
    section = netapp_api_if.parse_netapp_api_if(string_table)
    generated_discovery_results = list(
        netapp_api_if.discover_netapp_api_if(
            [(interfaces.DISCOVERY_DEFAULT_PARAMETERS)],
            section,
        )
    )
    assert generated_discovery_results == discovery_results

    for item, params, expected_results in items_params_results:
        generated_results = list(
            netapp_api_if._check_netapp_api_if(
                item,
                (params),
                section,
                value_store={},
            )
        )
        assert generated_results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    from pathlib import Path

    from tests.testlib.utils import cmk_path

    assert not pytest.main(
        [
            "-T=unit",
            "-vvsx",
            "--doctest-modules",
            str(Path(cmk_path()) / "cmk/base/plugins/agent_based/netapp_api_if.py"),
            __file__,
        ]
    )
