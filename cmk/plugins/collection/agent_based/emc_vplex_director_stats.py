#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import OIDEnd, SimpleSNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.diskstat import Section
from cmk.plugins.lib.emc import DETECT_VPLEX


def parse_emc_director_stats(string_table: StringTable) -> Section:
    directors = {}
    for (
        name,
        fe_ops_read,
        fe_ops_write,
        fe_ops_queued,
        _fe_ops_active,
        fe_ops_avgreadlatency,
        fe_ops_avgwritelatency,
        fe_bytes_read,
        fe_bytes_write,
        be_ops_read,
        be_ops_write,
        be_ops_avgreadlatency,
        be_ops_avgwritelatency,
        be_bytes_read,
        be_bytes_write,
        _oid_end,
    ) in string_table:
        directors[f"{name}_FE"] = {
            "read_ios": float(fe_ops_read),
            "write_ios": float(fe_ops_write),
            "queue_length": int(fe_ops_queued),
            "average_read_wait": float(fe_ops_avgreadlatency) / 1000000,
            "average_write_wait": float(fe_ops_avgwritelatency) / 1000000,
            "read_throughput": float(fe_bytes_read),
            "write_throughput": float(fe_bytes_write),
        }
        directors[f"{name}_BE"] = {
            "read_ios": float(be_ops_read),
            "write_ios": float(be_ops_write),
            "average_read_wait": float(be_ops_avgreadlatency) / 1000000,
            "average_write_wait": float(be_ops_avgwritelatency) / 1000000,
            "read_throughput": float(be_bytes_read),
            "write_throughput": float(be_bytes_write),
        }

    return directors


snmp_section_emc_vplex_director_stats = SimpleSNMPSection(
    name="emc_vplex_director_stats",
    parse_function=parse_emc_director_stats,
    parsed_section_name="diskstat_io_director",
    detect=DETECT_VPLEX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1139.21.2.2",
        oids=[
            "1.1.3",  # vplexDirectorName
            "4.1.1",  # vplexDirectorFEOpsRead
            "4.1.2",  # vplexDirectorFEOpsWrite
            "4.1.3",  # vplexDirectorFEOpsQueued
            "4.1.4",  # vplexDirectorFEOpsActive
            "4.1.5",  # vplexDirectorFEOpsAvgReadLatency
            "4.1.6",  # vplexDirectorFEOpsAvgWriteLatency
            "4.1.7",  # vplexDirectorFEBytesRead
            "4.1.8",  # vplexDirectorFEBytesWrite
            "6.1.1",  # vplexDirectorBEOpsRead
            "6.1.2",  # vplexDirectorBEOpsWrite
            "6.1.5",  # vplexDirectorBEOpsAvgReadLatency
            "6.1.6",  # vplexDirectorBEOpsAvgWriteLatency
            "6.1.7",  # vplexDirectorBEBytesRead
            "6.1.8",  # vplexDirectorBEBytesWrite
            OIDEnd(),
        ],
    ),
)
