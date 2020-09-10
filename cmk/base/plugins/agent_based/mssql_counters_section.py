#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Turns a @mssql_counters section into a dict mapping database instances to metric -> value dicts

A @mssql_counters section may look like this:

<<<mssql_counters:sep(124)>>>
None|utc_time|None|19.08.2020 14:25:04
MSSQL_VEEAMSQL2012:Memory_Broker_Clerks|memory_broker_clerk_size|Buffer_Pool|180475
MSSQL_VEEAMSQL2012:Memory_Broker_Clerks|simulation_benefit|Buffer_Pool|0
MSSQL_VEEAMSQL2012:Buffer_Manager|buffer_cache_hit_ratio|None|3090
MSSQL_VEEAMSQL2012:Buffer_Manager|buffer_cache_hit_ratio_base|None|3090
MSSQL_VEEAMSQL2012:Buffer_Manager|page_life_expectancy|None|12890
MSSQL_VEEAMSQL2012:Buffer_Node|database_pages|000|180475
MSSQL_VEEAMSQL2012:Buffer_Node|remote_node_page_lookups/sec|000|0
MSSQL_VEEAMSQL2012:General_Statistics|active_temp_tables|None|229
MSSQL_VEEAMSQL2012:Databases|data_file(s)_size_(kb)|tempdb|164928
MSSQL_VEEAMSQL2012:Databases|log_file(s)_size_(kb)|tempdb|13624
"""

from typing import Sequence
from contextlib import suppress
from datetime import datetime, timezone

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import AgentStringTable

from .utils.mssql_counters import Section


def to_timestamp(values: Sequence[str]) -> float:
    """
    >>> to_timestamp(('31.08.2017', '16:13:43'))
    1504196023.0
    >>> to_timestamp(('08/31/2017', '04:13:43', 'PM'))
    1504196023.0
    >>> to_timestamp(('31-08-2017', '16:13:43'))
    1504196023.0
    >>> to_timestamp(('2017-08-31', '16:13:43.123'))
    1504196023.0
    """
    def to_datetime(values: Sequence[str]) -> datetime:
        with suppress(ValueError):
            return datetime.strptime(' '.join(values), '%d.%m.%Y %H:%M:%S')
        with suppress(ValueError):
            return datetime.strptime(' '.join(values), '%m/%d/%Y %I:%M:%S %p')
        with suppress(ValueError):
            return datetime.strptime(' '.join(values), '%d-%m-%Y %H:%M:%S')
        with suppress(ValueError):
            return datetime.strptime(" ".join(values).split(".")[0], "%Y-%m-%d %H:%M:%S")
        raise ValueError('Time string %r does not match any known pattern' % ' '.join(values))

    return to_datetime(values).replace(tzinfo=timezone.utc).timestamp()


def parse_mssql_counters(string_table: AgentStringTable) -> Section:
    """
    >>> for k, v in parse_mssql_counters([
    ...     ['None', 'utc_time', 'None', '19.08.2020 14:25:04'],
    ...     ['MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'memory_broker_clerk_size', 'Buffer_Pool', '180475'],
    ...     ['MSSQL_VEEAMSQL2012:Databases', 'log_file(s)_size_(kb)', 'tempdb', '13624'],
    ...     ['MSSQL_VEEAMSQL2012:Database_Replica', 'redo_bytes_remaining', '_Total', '0'],
    ... ]).items():
    ...   print(k, v)
    ('None', 'None') {'utc_time': 1597847104.0}
    ('MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'Buffer_Pool') {'memory_broker_clerk_size': 180475}
    ('MSSQL_VEEAMSQL2012', 'tempdb') {'log_file(s)_size_(kb)': 13624}
    ('MSSQL_VEEAMSQL2012:Database_Replica', '_Total') {'redo_bytes_remaining': 0}
    """
    valid_rows = (row for row in string_table if len(row) >= 4 and not row[-1].startswith("ERROR:"))
    parsed: Section = {}
    for obj, counter, instance, *values in valid_rows:
        value = to_timestamp(values) if counter == "utc_time" else int(values[0])
        obj_id = obj[:-10] if obj.endswith(':Databases') else obj
        parsed.setdefault((obj_id, instance), {}).setdefault(counter, value)
    return parsed


register.agent_section(name="mssql_counters", parse_function=parse_mssql_counters)
