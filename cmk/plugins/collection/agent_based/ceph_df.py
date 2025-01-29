#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    RuleSetType,
    StringTable,
)
from cmk.plugins.lib.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS, FSBlocks


def _sanitize_line(line: list[str]) -> list[str]:
    """Merges units to values in case values and units are contained in separate line elements."""
    units = ("k", "K", "B", "M", "G", "T", "P", "E", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB")
    sanitized_line: list[str] = []
    for word in line:
        if word in units and sanitized_line:
            sanitized_line[-1] += word
        else:
            sanitized_line.append(word)
    return sanitized_line


def _parse_byte_values(value_str: str) -> float:
    """
    Returns the used storage in mebibytes.
    """
    # sanitize to possible units to single representation
    value_str = value_str.rstrip("iB")

    if value_str.endswith("E"):
        return float(value_str[:-1]) * 1024**4
    if value_str.endswith("P"):
        return float(value_str[:-1]) * 1024**3
    if value_str.endswith("T"):
        return float(value_str[:-1]) * 1024**2
    if value_str.endswith("G"):
        return float(value_str[:-1]) * 1024
    if value_str.endswith("M"):
        return float(value_str[:-1])
    if value_str.lower().endswith("k"):
        return float(value_str[:-1]) / 1024
    if value_str == "N/A":
        return 0.0
    return float(value_str) / (1024**2)


def parse_ceph_df(string_table: StringTable) -> FSBlocks:
    parsed: dict[str, dict[str, str]] = {}
    section = None
    global_headers = None
    pools_headers = None

    for line in string_table:
        if line[0] in ["GLOBAL:", "RAW"] or re.sub("[-: ]", "", "".join(line)) == "RAWSTORAGE":
            section = "global"
            continue
        if re.sub("[-: ]", "", "".join(line)) == "POOLS":
            section = "pools"
            continue

        line = _sanitize_line(line)
        if section == "global":
            match line:
                case ["SIZE", "AVAIL", "RAW", "USED", "%RAW", "USED", "OBJECTS"]:
                    global_headers = ["SIZE", "AVAIL", "RAW USED", "%RAW USED", "OBJECTS"]
                case ["CLASS", "SIZE", "AVAIL", "USED", "RAW", "USED", "%RAW", "USED"]:
                    global_headers = ["CLASS", "SIZE", "AVAIL", "USED", "RAW USED", "%RAW USED"]
                case values:
                    if global_headers is not None:
                        parsed.setdefault("SUMMARY", dict(zip(global_headers, values)))
            continue

        if section == "pools":
            match line:
                case [
                    "NAME",
                    "ID",
                    "CATEGORY",
                    "QUOTA",
                    "OBJECTS",
                    "QUOTA",
                    "BYTES",
                    "USED",
                    "%USED",
                    "MAX",
                    "AVAIL",
                    "OBJECTS",
                    "DIRTY",
                    "READ",
                    "WRITE",
                    "RAW",
                    "USED",
                ]:
                    pools_headers = [
                        "NAME",
                        "ID",
                        "CATEGORY",
                        "QUOTA OBJECTS",
                        "QUOTA BYTES",
                        "USED",
                        "%USED",
                        "MAX AVAIL",
                        "OBJECTS",
                        "DIRTY",
                        "READ",
                        "WRITE",
                        "RAW USED",
                    ]

                case [
                    "NAME",
                    "ID",
                    "QUOTA",
                    "OBJECTS",
                    "QUOTA",
                    "BYTES",
                    "USED",
                    "%USED",
                    "MAX",
                    "AVAIL",
                    "OBJECTS",
                    "DIRTY",
                    "READ",
                    "WRITE",
                    "RAW",
                    "USED",
                ]:
                    pools_headers = [
                        "NAME",
                        "ID",
                        "QUOTA OBJECTS",
                        "QUOTA BYTES",
                        "USED",
                        "%USED",
                        "MAX AVAIL",
                        "OBJECTS",
                        "DIRTY",
                        "READ",
                        "WRITE",
                        "RAW USED",
                    ]

                case [
                    "POOL",
                    "ID",
                    "STORED",
                    "OBJECTS",
                    "USED",
                    "%USED",
                    "MAX",
                    "AVAIL",
                    "QUOTA",
                    "OBJECTS",
                    "QUOTA",
                    "BYTES",
                    "DIRTY",
                    "USED",
                    "COMPR",
                    "UNDER",
                    "COMPR",
                ]:
                    pools_headers = [
                        "POOL",
                        "ID",
                        "STORED",
                        "OBJECTS",
                        "USED",
                        "%USED",
                        "MAX AVAIL",
                        "QUOTA OBJECTS",
                        "QUOTA BYTES",
                        "DIRTY",
                        "USED COMPR",
                        "UNDER COMPR",
                    ]

                case [
                    "POOL",
                    "ID",
                    "PGS",
                    "STORED",
                    "OBJECTS",
                    "USED",
                    "%USED",
                    "MAX",
                    "AVAIL",
                    "QUOTA",
                    "OBJECTS",
                    "QUOTA",
                    "BYTES",
                    "DIRTY",
                    "USED",
                    "COMPR",
                    "UNDER",
                    "COMPR",
                ]:
                    pools_headers = [
                        "POOL",
                        "ID",
                        "PGS",
                        "STORED",
                        "OBJECTS",
                        "USED",
                        "%USED",
                        "MAX AVAIL",
                        "QUOTA OBJECTS",
                        "QUOTA BYTES",
                        "DIRTY",
                        "USED COMPR",
                        "UNDER COMPR",
                    ]

                case [
                    "POOL",
                    "ID",
                    "STORED",
                    "(DATA)",
                    "(OMAP)",
                    "OBJECTS",
                    "USED",
                    "(DATA)",
                    "(OMAP)",
                    "%USED",
                    "MAX",
                    "AVAIL",
                    "QUOTA",
                    "OBJECTS",
                    "QUOTA",
                    "BYTES",
                    "DIRTY",
                    "USED",
                    "COMPR",
                    "UNDER",
                    "COMPR",
                ]:
                    pools_headers = [
                        "POOL",
                        "ID",
                        "STORED",
                        "(DATA)",
                        "(OMAP)",
                        "OBJECTS",
                        "USED",
                        "(DATA)",
                        "(OMAP)",
                        "%USED",
                        "MAX AVAIL",
                        "QUOTA OBJECTS",
                        "QUOTA BYTES",
                        "DIRTY",
                        "USED COMPR",
                        "UNDER COMPR",
                    ]

                case [
                    "POOL",
                    "ID",
                    "PGS",
                    "STORED",
                    "(DATA)",
                    "(OMAP)",
                    "OBJECTS",
                    "USED",
                    "(DATA)",
                    "(OMAP)",
                    "%USED",
                    "MAX",
                    "AVAIL",
                    "QUOTA",
                    "OBJECTS",
                    "QUOTA",
                    "BYTES",
                    "DIRTY",
                    "USED",
                    "COMPR",
                    "UNDER",
                    "COMPR",
                ]:
                    pools_headers = [
                        "POOL",
                        "ID",
                        "PGS",
                        "STORED",
                        "STORED (DATA)",
                        "STORED (OMAP)",
                        "OBJECTS",
                        "USED",
                        "USED (DATA)",
                        "USED (OMAP)",
                        "%USED",
                        "MAX AVAIL",
                        "QUOTA OBJECTS",
                        "QUOTA BYTES",
                        "DIRTY",
                        "USED COMPR",
                        "UNDER COMPR",
                    ]

                case [item, *values]:
                    if pools_headers is not None:
                        parsed.setdefault(item, dict(zip(pools_headers[1:], values)))

    mps = []
    for mp, data in parsed.items():
        # http://docs.ceph.com/docs/master/rados/operations/monitoring/
        # GLOBAL section:
        #   SIZE: The overall storage capacity of the cluster.
        #   AVAIL: The amount of free space available in the cluster.
        # POOLS section:
        #   USED: The notional amount of data stored in kilobytes, unless the number appends M for megabytes or G for gigabytes.
        #   MAX AVAIL: An estimate of the notional amount of data that can be written to this pool.
        if mp == "SUMMARY":
            size_mb = _parse_byte_values(data["SIZE"])
            avail_mb = _parse_byte_values(data["AVAIL"])
        else:
            avail_mb = _parse_byte_values(data["MAX AVAIL"])

            # from ceph version pacific STORED is a notional amount of data stored
            # USED is the total data stored (incl. replication)
            # https://docs.ceph.com/en/latest/rados/operations/monitoring/
            # werk 12199
            used_size = data["STORED"] if "STORED" in data else data["USED"]
            size_mb = avail_mb + _parse_byte_values(used_size)
        mps.append((mp, size_mb, avail_mb, 0))
    return mps


agent_section_ceph_df = AgentSection(
    name="ceph_df",
    parse_function=parse_ceph_df,
)


def dont_discover(params: Sequence[Mapping[str, Any]], section: FSBlocks) -> DiscoveryResult:
    """The plugin was replaced with the new Ceph integration in 2.4.0"""
    yield from ()


def check_ceph_df(item: str, params: Mapping[str, Any], section: FSBlocks) -> CheckResult:
    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=section,
        this_time=time.time(),
    )


check_plugin_ceph_df = CheckPlugin(
    name="ceph_df",
    service_name="Ceph Pool %s",
    discovery_function=dont_discover,
    discovery_ruleset_name="filesystem_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"groups": []},
    check_function=check_ceph_df,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
