#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP Commons

>>> import re
>>> all(re.match(CISCO_ASA_PRE_V9_PATTERN, v) for v in (
...     "Cisco adaptive security Version 8.2(1)",
...     "Cisco adaptive security Version 8.4(2)",
...     "cisco adaptive security Version 8.4(3)",
... ))
True
>>> any(re.match(CISCO_ASA_PRE_V9_PATTERN, v) for v in (
...     "Cisco adaptive security Version 9.1(5)",
...     "Cisco adaptive security Version 9.2(4)",
...     "Cisco adaptive security Version 9.2(4)5",
...     "Cisco adaptive security Version 9.4(3)8",
...     "Cisco adaptive security Version 9.5(1)",
...     "Cisco adaptive security Version 9.9(2)61",
...     "Cisco adaptive security Version 10.9(1)2",
...     "Cisco adaptive security Version 20.9(1)2",
...     "cisco Version 8.4(3)",
... ))
False
"""

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    get_value_store,
    matches,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cisco import DETECT_CISCO
from cmk.plugins.lib.cisco_mem import check_cisco_mem_sub


@dataclass(frozen=True)
class MemEntry:
    used: int
    free: int


Section = Mapping[str, MemEntry]
OID_SysDesc = ".1.3.6.1.2.1.1.1.0"
CISCO_ASA_PRE_V9_PATTERN = r"^[Cc]isco [Aa]daptive [Ss]ecurity.*Version [0-8]\..*"

CISCO_MEM_CHECK_DEFAULT_PARAMETERS = {
    "levels": (80.0, 90.0),
}


def _parse_mem_entry(values: Sequence[str]) -> MemEntry | None:
    try:
        return MemEntry(int(values[0]), int(values[1]))
    except ValueError:
        return None


def parse_cisco_mem(string_table: Sequence[StringTable]) -> Section | None:
    return {
        row[0]: mem_entry
        for tree in string_table
        for row in tree
        if (values := row[1:]) and (mem_entry := _parse_mem_entry(values))
    }


# .1.3.6.1.4.1.9.9.48 OID module is only capable of 32bit values
# ciscoMemoryPoolName           1.3.6.1.4.1.9.9.48.1.1.1.2
# ciscoMemoryPoolUsed           1.3.6.1.4.1.9.9.48.1.1.1.5
# ciscoMemoryPoolFree           1.3.6.1.4.1.9.9.48.1.1.1.6
# ciscoMemoryPoolLargestFree    1.3.6.1.4.1.9.9.48.1.1.1.7 (unused in check)
snmp_section_cisco_mem_legacy = SNMPSection(
    name="cisco_mem_legacy",
    parsed_section_name="cisco_mem",
    detect=DETECT_CISCO,
    parse_function=parse_cisco_mem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.48.1.1.1",
            oids=[
                "2",  # ciscoMemoryPoolName
                "5",  # ciscoMemoryPoolUsed
                "6",  # ciscoMemoryPoolFree
                "7",  # ciscoMemoryPoolLargestFree (unused by check plug-in)
            ],
        ),
    ],
)

# See https://checkmk.com/werk/1266
snmp_section_cisco_mem_asa_pre_v9 = SNMPSection(
    name="cisco_mem_asa_pre_v9",
    parsed_section_name="cisco_mem",
    detect=matches(OID_SysDesc, CISCO_ASA_PRE_V9_PATTERN),
    parse_function=parse_cisco_mem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.48.1.1.1",
            oids=["2.1", "5.1", "6.1", "7.1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.48.1.1.1",
            oids=["2.6", "5.6", "6.6", "7.6"],
        ),
    ],
    supersedes=["cisco_mem_legacy"],
)

snmp_section_cisco_mem_enhanced_32 = SNMPSection(
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.3.2.1  System memory --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolName.2.1
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.7.2.1 902008879     --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolUsed.2.1
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.8.2.1 3392957761    --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolFree.2.1
    name="cisco_mem_enhanced_32",
    parsed_section_name="cisco_mem",
    detect=all_of(
        contains(OID_SysDesc, "cisco"),
        exists(".1.3.6.1.4.1.9.9.221.1.1.1.1.*"),
    ),
    parse_function=parse_cisco_mem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.221.1.1.1.1",
            oids=[
                "3",  # cempMemPoolName
                "7",  # cempMemPoolUsed
                "8",  # cempMemPoolFree
            ],
        ),
    ],
    supersedes=["cisco_mem_legacy", "cisco_mem_asa_pre_v9"],
)

# 64 bit part of the "enhanced mempool" is not available on all devices
snmp_section_cisco_mem_enhanced_64 = SNMPSection(
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.3.2.1  System memory --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolName.2.1
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.18.2.1 902008879     --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolHCUsed.2.1
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.20.2.1 3392957761    --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolHCFree.2.1
    name="cisco_mem_enhanced_64",
    parsed_section_name="cisco_mem",
    detect=all_of(
        contains(OID_SysDesc, "cisco"),
        exists(".1.3.6.1.4.1.9.9.221.1.1.1.1.18.*"),
    ),
    parse_function=parse_cisco_mem,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.221.1.1.1.1",
            oids=[
                "3",  # cempMemPoolName
                "18",  # cempMemPoolHCUsed
                "20",  # cempMemPoolHCFree
            ],
        ),
    ],
    supersedes=["cisco_mem_legacy", "cisco_mem_asa_pre_v9", "cisco_mem_enhanced_32"],
)


def discovery_cisco_mem(section: Section) -> DiscoveryResult:
    """
    >>> for elem in discovery_cisco_mem({
    ...         'System memory': MemEntry(1251166290, 3043801006),
    ...         'MEMPOOL_DMA': MemEntry(0, 0),
    ...         'MEMPOOL_GLOBAL_SHARED': MemEntry(0, 0)}):
    ...     print(elem)
    Service(item='System memory')
    """
    yield from (
        Service(item=item)
        for item, mem_entry in section.items()
        if item and item != "Driver text" and mem_entry.used and mem_entry.free
    )


def _idem_check_cisco_mem(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """
    >>> vs = {}
    >>> for result in _idem_check_cisco_mem(
    ...         vs,
    ...         "MEMPOOL_DMA",
    ...         {
    ...             'trend_perfdata': True,
    ...             'trend_range': 24,
    ...             'trend_showtimeleft': True,
    ...             'trend_timeleft': (12, 6)},
    ...         {'System memory': MemEntry(3848263744, 8765044672),
    ...          'MEMPOOL_MSGLYR': MemEntry(123040, 8265568),
    ...          'MEMPOOL_DMA': MemEntry(429262192, 378092176),
    ...          'MEMPOOL_GLOBAL_SHARED': MemEntry(1092814800, 95541296)}):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='Usage: 53.17% - 409 MiB of 770 MiB')
    Metric('mem_used_percent', 53.16899356888102, boundaries=(0.0, None))
    """
    if not (mem_entry := section.get(item)):
        return
    mem_total = mem_entry.free + mem_entry.used
    yield from check_cisco_mem_sub(
        value_store,
        item,
        params,
        mem_entry.used,
        mem_total,
    )


def check_cisco_mem(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _idem_check_cisco_mem(get_value_store(), item, params, section)


check_plugin_cisco_mem = CheckPlugin(
    name="cisco_mem",
    service_name="Memory %s",
    discovery_function=discovery_cisco_mem,
    check_default_parameters=CISCO_MEM_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cisco_mem",
    check_function=check_cisco_mem,
)
