#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

from contextlib import suppress
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

from .agent_based_api.v1 import (
    all_of,
    contains,
    exists,
    get_value_store,
    matches,
    register,
    Service,
    SNMPTree,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cisco import DETECT_CISCO
from .utils.cisco_mem import check_cisco_mem_sub

Section = Dict[str, Sequence[str]]
OID_SysDesc = ".1.3.6.1.2.1.1.1.0"
CISCO_ASA_PRE_V9_PATTERN = r"^[Cc]isco [Aa]daptive [Ss]ecurity.*Version [0-8]\..*"

CISCO_MEM_CHECK_DEFAULT_PARAMETERS = {
    "levels": (80.0, 90.0),
}


def parse_cisco_mem(string_table: List[StringTable]) -> Optional[Section]:
    """
    >>> for item, values in parse_cisco_mem([
    ...         [['System memory', '319075344', '754665920', '731194056']],
    ...         [['MEMPOOL_DMA', '41493248', '11754752', '11743928']]]).items():
    ...     print(item, values)
    System memory ['319075344', '754665920', '731194056']
    MEMPOOL_DMA ['41493248', '11754752', '11743928']
    >>> for item, values in parse_cisco_mem([[
    ...         ['System memory', '1251166290', '3043801006'],
    ...         ['MEMPOOL_DMA', '0', '0'],
    ...         ['MEMPOOL_GLOBAL_SHARED', '0', '0']]]).items():
    ...     print(item, values)
    System memory ['1251166290', '3043801006']
    MEMPOOL_DMA ['0', '0']
    MEMPOOL_GLOBAL_SHARED ['0', '0']
    """
    return {
        item: values  #
        for row in string_table
        for entry in row  #
        if entry
        for item, *values in (entry,)
    }


# .1.3.6.1.4.1.9.9.48 OID module is only capable of 32bit values
# ciscoMemoryPoolName           1.3.6.1.4.1.9.9.48.1.1.1.2
# ciscoMemoryPoolUsed           1.3.6.1.4.1.9.9.48.1.1.1.5
# ciscoMemoryPoolFree           1.3.6.1.4.1.9.9.48.1.1.1.6
# ciscoMemoryPoolLargestFree    1.3.6.1.4.1.9.9.48.1.1.1.7 (unused in check)
register.snmp_section(
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
                "7",  # ciscoMemoryPoolLargestFree (unused by check plugin)
            ],
        ),
    ],
)

# See https://checkmk.com/werk/1266
register.snmp_section(
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

register.snmp_section(
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
register.snmp_section(
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
    ...         'System memory':         ['1251166290', '3043801006'],
    ...         'MEMPOOL_DMA':           ['0', '0'],
    ...         'MEMPOOL_GLOBAL_SHARED': ['0', '0']}):
    ...     print(elem)
    Service(item='System memory')
    Service(item='MEMPOOL_DMA')
    Service(item='MEMPOOL_GLOBAL_SHARED')
    """
    yield from (Service(item=item) for item in section if item != "Driver text")


def check_cisco_mem(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from _idem_check_cisco_mem(get_value_store(), item, params, section)


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
    ...         {'System memory': ['3848263744', '8765044672'],
    ...          'MEMPOOL_MSGLYR': ['123040', '8265568'],
    ...          'MEMPOOL_DMA': ['429262192', '378092176'],
    ...          'MEMPOOL_GLOBAL_SHARED': ['1092814800', '95541296']}):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='Usage: 53.17% - 409 MiB of 770 MiB')
    Metric('mem_used_percent', 53.16899356888102, boundaries=(0.0, None))
    """
    if item not in section:
        return
    values = section[item]
    # We've seen SNMP outputs containing empty entries for free or used memory.
    # Assumption: In this case these values are zero.
    mem_free, mem_used = 0, 0

    with suppress(ValueError):
        mem_free = int(values[1])
    with suppress(ValueError):
        mem_used = int(values[0])

    mem_total = mem_free + mem_used
    yield from check_cisco_mem_sub(
        value_store,
        item,
        params,
        mem_used,
        mem_total,
    )


register.check_plugin(
    name="cisco_mem",
    service_name="Memory %s",
    discovery_function=discovery_cisco_mem,
    check_default_parameters=CISCO_MEM_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cisco_mem",
    check_function=check_cisco_mem,
)
