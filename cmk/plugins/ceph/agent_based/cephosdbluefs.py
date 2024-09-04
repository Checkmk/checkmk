#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.ceph.constants import MIB
from cmk.plugins.lib import df


@dataclass(frozen=True)
class BlueFS:
    db_total_mb: float
    db_used_mb: float
    wal_total_mb: float
    wal_used_mb: float
    slow_total_mb: float
    slow_used_mb: float

    @property
    def db_avail_mb(self) -> float:
        return self.db_total_mb - self.db_used_mb

    @property
    def wal_avail_mb(self) -> float:
        return self.wal_total_mb - self.wal_used_mb

    @property
    def slow_avail_mb(self) -> float:
        return self.slow_total_mb - self.slow_used_mb


Section = Mapping[str, BlueFS]


def parse_cephosdbluefs(string_table: StringTable) -> Section:
    raw = json.loads("".join(string_table[0]))

    return {
        osdid: BlueFS(
            db_total_mb=float(bluefs.get("db_total_bytes", 0)) / MIB,
            db_used_mb=float(bluefs.get("db_used_bytes", 0)) / MIB,
            wal_total_mb=float(bluefs.get("wal_total_bytes", 0)) / MIB,
            wal_used_mb=float(bluefs.get("wal_used_bytes", 0)) / MIB,
            slow_total_mb=float(bluefs.get("slow_total_bytes", 0)) / MIB,
            slow_used_mb=float(bluefs.get("slow_used_bytes", 0)) / MIB,
        )
        for osdid, raw_inner in raw.items()
        if (bluefs := raw_inner.get("bluefs")) is not None
    }


agent_section_cephosdbluefs = AgentSection(
    name="cephosdbluefs",
    parse_function=parse_cephosdbluefs,
)


def discovery_cephosdbluefs_db(section: Section) -> DiscoveryResult:
    yield from (Service(item=osdid) for osdid, bluefs in section.items() if bluefs.db_total_mb > 0)


def check_cephosdbluefs_db(
    item: str,
    params: Mapping[str, object],
    section: Section,
) -> CheckResult:
    if (bluefs := section.get(item)) is None:
        return
    yield from df.df_check_filesystem_single(
        get_value_store(),
        item,
        bluefs.db_total_mb,
        bluefs.db_avail_mb,
        0,
        None,
        None,
        params=params,
        this_time=time.time(),
    )


check_plugin_cephosdbluefs_db = CheckPlugin(
    name="cephosdbluefs_db",
    service_name="Ceph OSD %s DB",
    sections=["cephosdbluefs"],
    discovery_function=discovery_cephosdbluefs_db,
    check_function=check_cephosdbluefs_db,
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)


def discovery_cephosdbluefs_wal(section: Section) -> DiscoveryResult:
    yield from (Service(item=osdid) for osdid, bluefs in section.items() if bluefs.wal_total_mb > 0)


def check_cephosdbluefs_wal(
    item: str,
    params: Mapping[str, object],
    section: Section,
) -> CheckResult:
    if (bluefs := section.get(item)) is None:
        return
    yield from df.df_check_filesystem_single(
        get_value_store(),
        item,
        bluefs.wal_total_mb,
        bluefs.wal_avail_mb,
        0,
        None,
        None,
        params=params,
        this_time=time.time(),
    )


check_plugin_cephosdbluefs_wal = CheckPlugin(
    name="cephosdbluefs_wal",
    service_name="Ceph OSD %s WAL",
    sections=["cephosdbluefs"],
    discovery_function=discovery_cephosdbluefs_wal,
    check_function=check_cephosdbluefs_wal,
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)


def discovery_cephosdbluefs_slow(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=osdid) for osdid, bluefs in section.items() if bluefs.slow_total_mb > 0
    )


def check_cephosdbluefs_slow(
    item: str,
    params: Mapping[str, object],
    section: Section,
) -> CheckResult:
    if (bluefs := section.get(item)) is None:
        return
    yield from df.df_check_filesystem_single(
        get_value_store(),
        item,
        bluefs.slow_total_mb,
        bluefs.slow_avail_mb,
        0,
        None,
        None,
        params=params,
        this_time=time.time(),
    )


check_plugin_cephosdbluefs_slow = CheckPlugin(
    name="cephosdbluefs_slow",
    service_name="Ceph OSD %s Slow",
    sections=["cephosdbluefs"],
    discovery_function=discovery_cephosdbluefs_slow,
    check_function=check_cephosdbluefs_slow,
    check_default_parameters=df.FILESYSTEM_DEFAULT_PARAMS,
    check_ruleset_name="filesystem",
)
