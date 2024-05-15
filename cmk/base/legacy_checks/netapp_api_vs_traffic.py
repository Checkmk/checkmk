#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="attr-defined"

import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.netapp_api import netapp_api_parse_lines
from cmk.base.config import check_info

from cmk.agent_based.v2 import get_rate, get_value_store, IgnoreResultsError, render

# <<<netapp_api_vs_traffic:sep(9)>>>
# lif:vserver        instance_uuid 4294967295        instance_name sb1        sent_errors 0        recv_errors 0 ...
# lif:vserver        instance_uuid 16        instance_name vsFS        sent_errors 0        recv_errors 0        ..
# cifs:vserver        session_timed_out 17731        sd_max_ace_size         cifs_latency 9403817108427        ..
# iscsi_lif:vserver        iscsi_read_ops 4071295661        avg_write_latency 3429809602514        ..

# A list of counter name is available at
# https://library.netapp.com/ecmdocs/ECMP1608437/html/GUID-04407796-688E-489D-901C-A6C9EAC2A7A2.html


def parse_netapp_api_vs_traffic(string_table):
    return netapp_api_parse_lines(string_table, custom_keys=["protocol", "instance_name"])


def inventory_netapp_api_vs_traffic(parsed):
    vservers = {x.split(".", 1)[1] for x in parsed}
    for vserver in vservers:
        yield vserver, {}


def check_netapp_api_vs_traffic(item, _no_params, parsed):
    """
    In the case of migration, a utility function is available for this check here:
    cmk/plugins/lib/netapp_api.py -> check_netapp_vs_traffic
    """
    protocol_map = {
        "lif:vserver": (
            "Ethernet",
            # ( what         perfname        perftext      scale     format_func)
            [
                ("recv_data", "if_in_octets", "received data", 1, render.bytes),
                ("sent_data", "if_out_octets", "sent data", 1, render.bytes),
                ("recv_errors", "if_in_errors", "received errors", 1, int),
                ("sent_errors", "if_out_errors", "sent errors", 1, int),
                ("recv_packet", "if_in_pkts", "received packets", 1, int),
                ("sent_packet", "if_out_pkts", "sent packets", 1, int),
            ],
        ),
        "fcp_lif:vserver": (
            "FCP",
            [
                (
                    "fcp_read_latency",
                    "fcp_read_latency",
                    "avg. Read latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                (
                    "fcp_write_latency",
                    "fcp_write_latency",
                    "avg. Write latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                ("read_data", "fcp_read_data", "read data", 1, render.bytes),
                ("write_data", "fcp_write_data", "write data", 1, render.bytes),
            ],
        ),
        "cifs:vserver": (
            "CIFS",
            [
                (
                    "cifs_read_latency",
                    "cifs_read_latency",
                    "read latency",
                    0.000000001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                (
                    "cifs_write_latency",
                    "cifs_write_latency",
                    "write latency",
                    0.000000001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                ("cifs_read_ops", "cifs_read_ios", "read OPs", 1, int),
                ("cifs_write_ops", "cifs_write_ios", "write OPs", 1, int),
            ],
        ),
        "iscsi_lif:vserver": (
            "iSCSI",
            [
                (
                    "iscsi_read_latency",
                    "iscsi_read_latency",
                    "avg. Read latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                (
                    "iscsi_write_latency",
                    "iscsi_write_latency",
                    "avg. Write latency",
                    0.001,
                    lambda x: "%.2f ms" % (x * 1000),
                ),
                ("read_data", "iscsi_read_data", "read data", 1, render.bytes),
                ("write_data", "iscsi_write_data", "write data", 1, render.bytes),
            ],
        ),
        "nfsv3": (
            "NFS",
            [
                ("nfsv3_read_ops", "nfs_read_ios", "read OPs", 1, int),
                ("nfsv3_write_ops", "nfs_write_ios", "write OPs", 1, int),
                (
                    "nfsv3_read_throughput",
                    "nfs_read_throughput",
                    "read throughput",
                    1,
                    render.iobandwidth,
                ),
                (
                    "nfsv3_write_throughput",
                    "nfs_write_throughput",
                    "write throughput",
                    1,
                    render.iobandwidth,
                ),
                ("nfsv3_ops", "nfs_ios", "OPs", 1, int),
            ],
        ),
        "nfsv4": (
            "NFSv4",
            [
                ("nfsv4_read_ops", "nfsv4_read_ios", "read OPs", 1, int),
                ("nfsv4_write_ops", "nfsv4_write_ios", "write OPs", 1, int),
                (
                    "nfs4_read_throughput",
                    "nfsv4_read_throughput",
                    "read throughput",
                    1,
                    render.iobandwidth,
                ),
                (
                    "nfs4_write_throughput",
                    "nfsv4_write_throughput",
                    "write throughput",
                    1,
                    render.iobandwidth,
                ),
                ("nfsv4_ops", "nfsv4_ios", "OPs", 1, int),
            ],
        ),
        "nfsv4_1": (
            "NFSv4.1",
            [
                ("nfsv4_1_ops", "nfsv4_1_ios", "OPs", 1, int),
                (
                    "nfs41_read_throughput",
                    "nfsv4_1_read_throughput",
                    "read throughput",
                    1,
                    render.iobandwidth,
                ),
                (
                    "nfs41_write_throughput",
                    "nfsv4_1_write_throughput",
                    "write throughput",
                    1,
                    render.iobandwidth,
                ),
            ],
        ),
    }

    def get_ref(what, data):
        # According to "NetApp® Unified Storage Performance Management",
        # latency calculation is a function of the number of ops.
        refname = {
            "iscsi_read_latency": "iscsi_read_ops",
            "iscsi_write_latency": "iscsi_write_ops",
            "fcp_read_latency": "fcp_read_ops",
            "fcp_write_latency": "fcp_write_ops",
            "cifs_read_latency": "cifs_read_ops",
            "cifs_write_latency": "cifs_write_ops",
        }.get(what)
        try:
            return int(data[refname])
        except KeyError:
            return None

    now = time.time()
    value_store = get_value_store()
    for protocol, (protoname, values) in protocol_map.items():
        data = parsed.get(f"{protocol}.{item}")
        if not data:
            continue

        for what, perfname, perftext, scale, format_func in values:
            if what not in data:
                continue

            ref = get_ref(what, data)
            if ref is None:
                ref = now

            try:
                rate = get_rate(
                    value_store,
                    f"{protocol}.{what}",
                    ref,
                    int(data[what]) * scale,
                    raise_overflow=True,
                )
                yield (
                    0,
                    f"{protoname} {perftext}: {format_func(rate)}",  # pylint: disable=not-callable
                    [(perfname, rate)],
                )
            except IgnoreResultsError:
                yield (0, f"{protoname} {perftext}: -")


check_info["netapp_api_vs_traffic"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_vs_traffic,
    service_name="Traffic vServer %s",
    discovery_function=inventory_netapp_api_vs_traffic,
    check_function=check_netapp_api_vs_traffic,
)
