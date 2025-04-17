#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from typing import NamedTuple

from cmk.base.check_legacy_includes.df import df_check_filesystem_single, FILESYSTEM_DEFAULT_PARAMS

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}

# example output
# <<<aix_paging>>>
# Page Space      Physical Volume   Volume Group    Size %Used   Active    Auto    Type   Chksum
# hd6                   hdisk11                rootvg       10240MB    23        yes        yes       lv       0


class AIXPaging(NamedTuple):
    group: str
    size_mb: int
    usage_perc: int
    active: str
    auto: str
    type_: str


def parse_aix_paging(string_table):
    map_type = {
        "lv": "logical volume",
        "nfs": "NFS",
    }

    parsed = {}
    if len(string_table) <= 1:
        return parsed

    # First line is the header
    for line in string_table[1:]:
        try:
            # Always given in MB, eg. 1234MB
            size = int(line[3][:-2])
        except ValueError:
            continue
        try:
            usage = int(line[4])
        except ValueError:
            continue
        paging_type = map_type.get(line[7], "unknown[%s]" % line[7])
        parsed.setdefault(
            f"{line[0]}/{line[1]}",
            AIXPaging(line[2], size, usage, line[5], line[6], paging_type),
        )
    return parsed


def check_aix_paging(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    avail_mb = data.size_mb * (1 - data.usage_perc / 100.0)
    yield df_check_filesystem_single(item, data.size_mb, avail_mb, 0, None, None, params)
    yield 0, f"Active: {data.active}, Auto: {data.auto}, Type: {data.type_}"


def discover_aix_paging(section):
    yield from ((item, {}) for item in section)


check_info["aix_paging"] = LegacyCheckDefinition(
    name="aix_paging",
    parse_function=parse_aix_paging,
    service_name="Page Space %s",
    discovery_function=discover_aix_paging,
    check_function=check_aix_paging,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
