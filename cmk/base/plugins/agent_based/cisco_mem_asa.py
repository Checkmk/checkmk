#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""F5-BIGIP Commons

>>> import re
>>> all(re.match(VERSION_PRE_V9_PATTERN, v) for v in (
...     "Version 8.2(1)",
...     "Version 8.4(2)",
...     "Version 8.4(3)",
... ))
True
>>> any(re.match(VERSION_PRE_V9_PATTERN, v) for v in (
...     "Version 9.1(5)",
...     "Version 9.2(4)",
...     "Version 9.2(4)5",
...     "Version 9.4(3)8",
...     "Version 9.5(1)",
...     "Version 9.9(2)61",
...     "Version 10.9(1)2",
...     "Version 20.9(1)2",
... ))
False
"""

from typing import Sequence, Dict
from contextlib import suppress

from .utils.size_trend import size_trend
from .utils.memory import (
    get_levels_mode_from_value,
    check_element,
)
from .agent_based_api.v1 import (
    SNMPTree,
    register,
    Service,
    Result,
    State as state,
    startswith,
    all_of,
    matches,
    not_matches,
    get_value_store,
    GetRateError,
)
from .agent_based_api.v1.type_defs import (
    SNMPStringTable,
    Parameters,
    CheckResult,
    DiscoveryResult,
    ValueStore,
)

Section = Dict[str, Sequence[str]]
OID_SysDesc = ".1.3.6.1.2.1.1.1.0"
VERSION_PRE_V9_PATTERN = r".*Version [0-8]\..*"

CISCO_MEM_CHECK_DEFAULT_PARAMETERS = {
    "levels": (80.0, 90.0),
}


def parse_cisco_mem_asa(string_table: SNMPStringTable) -> Section:
    """
    >>> for item, values in parse_cisco_mem_asa([
    ...         [['System memory', '319075344', '754665920', '731194056']],
    ...         [['MEMPOOL_DMA', '41493248', '11754752', '11743928']]]).items():
    ...     print(item, values)
    System memory ['319075344', '754665920', '731194056']
    MEMPOOL_DMA ['41493248', '11754752', '11743928']
    """
    return {
        string_table[0][0][0]: string_table[0][0][1:],
        string_table[1][0][0]: string_table[1][0][1:]
    }


def parse_cisco_mem_asa64(string_table: SNMPStringTable) -> Section:
    """
    >>> for item, values in parse_cisco_mem_asa64([[
    ...         ['System memory', '1251166290', '3043801006'],
    ...         ['MEMPOOL_DMA', '0', '0'],
    ...         ['MEMPOOL_GLOBAL_SHARED', '0', '0']]]).items():
    ...     print(item, values)
    System memory ['1251166290', '3043801006']
    MEMPOOL_DMA ['0', '0']
    MEMPOOL_GLOBAL_SHARED ['0', '0']
    """
    return {line[0]: line[1:] for line in string_table[0]}


register.snmp_section(
    name="cisco_mem_asa",
    detect=all_of(startswith(OID_SysDesc, "cisco adaptive security"),
                  matches(OID_SysDesc, VERSION_PRE_V9_PATTERN)),
    parse_function=parse_cisco_mem_asa,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.48.1.1.1",
            oids=["2.1", "5.1", "6.1", "7.1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.48.1.1.1",
            oids=["2.6", "5.6", "6.6", "7.6"],
        ),
    ],
)

register.snmp_section(
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.3.2.1  System memory --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolName.2.1
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.18.2.1 902008879     --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolHCUsed.2.1
    # .1.3.6.1.4.1.9.9.221.1.1.1.1.20.2.1 3392957761    --> CISCO-ENHANCED-MEMPOOL-MIB::cempMemPoolHCFree.2.1
    name="cisco_mem_asa64",
    parsed_section_name="cisco_mem_asa",
    detect=all_of(startswith(OID_SysDesc, "cisco adaptive security"),
                  not_matches(OID_SysDesc, VERSION_PRE_V9_PATTERN)),
    parse_function=parse_cisco_mem_asa64,
    trees=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.221.1.1.1.1",
            oids=[
                "3",  # cempMemPoolName
                "18",  # cempMemPoolHCUsed
                "20",  # cempMemPoolHCFree
            ],
        ),
    ],
)


def discovery_cisco_mem(section: Section) -> DiscoveryResult:
    """
    >>> for elem in discovery_cisco_mem({
    ...         'System memory':         ['1251166290', '3043801006'],
    ...         'MEMPOOL_DMA':           ['0', '0'],
    ...         'MEMPOOL_GLOBAL_SHARED': ['0', '0']}):
    ...     print(elem)
    Service(item='System memory', parameters={}, labels=[])
    Service(item='MEMPOOL_DMA', parameters={}, labels=[])
    Service(item='MEMPOOL_GLOBAL_SHARED', parameters={}, labels=[])
    """
    yield from (Service(item=item) for item in section if item != "Driver text")


def check_cisco_mem(item: str, params: Parameters, section: Section) -> CheckResult:
    yield from _idem_check_cisco_mem(get_value_store(), item, params, section)


def _idem_check_cisco_mem(
    value_store: ValueStore,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """
    >>> vs = {}
    >>> for result in _idem_check_cisco_mem(
    ...         vs,
    ...         "MEMPOOL_DMA",
    ...         Parameters({
    ...             'trend_perfdata': True,
    ...             'trend_range': 24,
    ...             'trend_showtimeleft': True,
    ...             'trend_timeleft': (12, 6)}),
    ...         {'System memory': ['3848263744', '8765044672'],
    ...          'MEMPOOL_MSGLYR': ['123040', '8265568'],
    ...          'MEMPOOL_DMA': ['429262192', '378092176'],
    ...          'MEMPOOL_GLOBAL_SHARED': ['1092814800', '95541296']}):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='Usage: 53.2% - 409 MiB of 770 MiB', details='Usage: 53.2% - 409 MiB of 770 MiB')
    Metric('mem_used_percent', 53.16899356888102, levels=(None, None), boundaries=(0.0, None))
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


def check_cisco_mem_sub(
    value_store: ValueStore,
    item: str,
    params: Parameters,
    mem_used: int,
    mem_total: int,
) -> CheckResult:
    if not mem_total:
        yield Result(state=state.UNKNOWN,
                     summary="Cannot calculate memory usage: Device reports total memory 0")
        return

    warn, crit = params.get("levels", (None, None))
    mode = get_levels_mode_from_value(warn)
    mega = 1024 * 1024
    if isinstance(warn, int):
        warn *= mega  # convert from megabyte to byte
        crit *= mega
    if warn is not None:
        warn = abs(warn)
        crit = abs(crit)

    yield from check_element(
        "Usage",
        mem_used,
        mem_total,
        (mode, (warn, crit)),
        create_percent_metric=True,
    )

    if params.get("trend_range"):
        with suppress(GetRateError):
            yield from size_trend(
                value_store=value_store,
                check="cisco_mem",
                item=item,
                resource="memory",
                levels=params,
                used_mb=mem_used / mega,
                size_mb=mem_total / mega,
                timestamp=None,
            )


register.check_plugin(
    name="cisco_mem_asa",  # name taken from pre-1.7 plugin
    service_name="Memory %s",
    discovery_function=discovery_cisco_mem,
    check_default_parameters=CISCO_MEM_CHECK_DEFAULT_PARAMETERS,
    check_ruleset_name="cisco_mem",
    check_function=check_cisco_mem,
)
