#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Service,
    StringTable,
)
from cmk.plugins.lib.netapp_api import check_netapp_vs_traffic
from cmk.plugins.netapp import models

# <<<netapp_ontap_vs_traffic:sep(0)>>>
# {
#     "counters": [
#         {"name": "received_data", "value": 0},
#         {"name": "received_packets", "value": 0},
#         {"name": "received_errors", "value": 0},
#         {"name": "sent_data", "value": 0},
#         {"name": "sent_packets", "value": 0},
#         {"name": "sent_errors", "value": 0},
#     ],
#     "table": "lif",
# }
# {
#     "counters": [
#         {"name": "received_data", "value": 0},
#         {"name": "received_packets", "value": 0},
#         {"name": "received_errors", "value": 0},
#         {"name": "sent_data", "value": 0},
#         {"name": "sent_packets", "value": 0},
#         {"name": "sent_errors", "value": 0},
#     ],
#     "table": "lif",
# }

Section = Mapping[str, models.SvmTrafficCountersModel]


def parse_netapp_ontap_vs_traffic(string_table: StringTable) -> Section:
    return {
        f"{counters.table}.{counters.svm_name}": counters
        for line in string_table
        for counters in [models.SvmTrafficCountersModel.model_validate_json(line[0])]
    }


agent_section_netapp_ontap_vs_traffic = AgentSection(
    name="netapp_ontap_vs_traffic",
    parse_function=parse_netapp_ontap_vs_traffic,
)


def discovery_netapp_ontap_vs_traffic(section: Section) -> DiscoveryResult:
    vservers = {x.split(".", 1)[1] for x in section}
    yield from (Service(item=vserver) for vserver in vservers)


def check_netapp_ontap_vs_traffic(item: str, section: Section) -> CheckResult:
    protocol_map = {
        "lif": (
            "Ethernet",
            # ( what         perfname        perftext      scale     format_func)
            [
                ("received_data", "if_in_octets", "received data", 1, render.bytes),
                ("sent_data", "if_out_octets", "sent data", 1, render.bytes),
                ("received_errors", "if_in_errors", "received errors", 1, int),
                ("sent_errors", "if_out_errors", "sent errors", 1, int),
                ("received_packets", "if_in_pkts", "received packets", 1, int),
                ("sent_packets", "if_out_pkts", "sent packets", 1, int),
            ],
        ),
        "fcp_lif": (
            "FCP",
            [
                (
                    "average_read_latency",
                    "fcp_read_latency",
                    "avg. Read latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                (
                    "average_write_latency",
                    "fcp_write_latency",
                    "avg. Write latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                ("read_data", "fcp_read_data", "read data", 1, render.bytes),
                ("write_data", "fcp_write_data", "write data", 1, render.bytes),
            ],
        ),
        "svm_cifs": (
            "CIFS",
            [
                (
                    "average_read_latency",
                    "cifs_read_latency",
                    "read latency",
                    0.000000001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                (
                    "average_write_latency",
                    "cifs_write_latency",
                    "write latency",
                    0.000000001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                ("total_read_ops", "cifs_read_ios", "read OPs", 1, int),
                ("total_write_ops", "cifs_write_ios", "write OPs", 1, int),
            ],
        ),
        "iscsi_lif": (
            "iSCSI",
            [
                (
                    "average_read_latency",
                    "iscsi_read_latency",
                    "avg. Read latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                (
                    "average_write_latency",
                    "iscsi_write_latency",
                    "avg. Write latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                ("read_data", "iscsi_read_data", "read data", 1, render.bytes),
                ("write_data", "iscsi_write_data", "write data", 1, render.bytes),
            ],
        ),
        "svm_nfs_v3": (
            "NFS",
            [
                ("read_ops", "nfs_read_ios", "read OPs", 1, int),
                ("write_ops", "nfs_write_ios", "write OPs", 1, int),
                (
                    "read_throughput",
                    "nfs_read_throughput",
                    "read throughput",
                    1,
                    render.iobandwidth,
                ),
                (
                    "write_throughput",
                    "nfs_write_throughput",
                    "write throughput",
                    1,
                    render.iobandwidth,
                ),
                ("ops", "nfs_ios", "OPs", 1, int),
            ],
        ),
        "svm_nfs_v4": (
            "NFSv4",
            [
                (
                    "total.read_throughput",
                    "nfsv4_read_throughput",
                    "read throughput",
                    1,
                    render.iobandwidth,
                ),
                (
                    "total.write_throughput",
                    "nfsv4_write_throughput",
                    "write throughput",
                    1,
                    render.iobandwidth,
                ),
                ("ops", "nfsv4_ios", "OPs", 1, int),
            ],
        ),
        "svm_nfs_v41": (
            "NFSv4.1",
            [
                ("ops", "nfsv4_1_ios", "OPs", 1, int),
                (
                    "total.read_throughput",
                    "nfsv4_1_read_throughput",
                    "read throughput",
                    1,
                    render.iobandwidth,
                ),
                (
                    "total.write_throughput",
                    "nfsv4_1_write_throughput",
                    "write throughput",
                    1,
                    render.iobandwidth,
                ),
            ],
        ),
    }

    now = time.time()
    value_store = get_value_store()

    latency_calc_ref = {
        "iscsi": {
            "average_read_latency": "iscsi_read_ops",
            "average_write_latency": "iscsi_write_ops",
        },
        "fcp": {
            "average_read_latency": "read_ops",
            "average_write_latency": "write_ops",
        },
        "cifs": {
            "cifs_read_latency": "total_read_ops",
            "cifs_write_latency": "total_write_ops",
        },
    }

    for protocol in protocol_map:
        data = section.get(f"{protocol}.{item}")
        if not data or not data.counters:
            continue

        counters = {el["name"]: el["value"] for el in data.counters}

        yield from check_netapp_vs_traffic(
            counters, protocol, protocol_map, latency_calc_ref, now, value_store
        )


check_plugin_netapp_ontap_vs_traffic = CheckPlugin(
    name="netapp_ontap_vs_traffic",
    service_name="Traffic SVM %s",
    discovery_function=discovery_netapp_ontap_vs_traffic,
    check_function=check_netapp_ontap_vs_traffic,
)
