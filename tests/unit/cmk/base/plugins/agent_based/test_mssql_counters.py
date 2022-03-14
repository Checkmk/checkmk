#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
from typing import Any, Dict

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResults, Metric, Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.mssql_counters_cache_hits import (
    check_mssql_counters_cache_hits,
    discovery_mssql_counters_cache_hits,
)
from cmk.base.plugins.agent_based.mssql_counters_file_sizes import (
    check_mssql_counters_file_sizes,
    discovery_mssql_counters_file_sizes,
)
from cmk.base.plugins.agent_based.mssql_counters_locks import _check_base as check_locks_base
from cmk.base.plugins.agent_based.mssql_counters_locks import discovery_mssql_counters_locks
from cmk.base.plugins.agent_based.mssql_counters_locks_per_batch import (
    _check_base as check_locks_per_batch_base,
)
from cmk.base.plugins.agent_based.mssql_counters_locks_per_batch import (
    discovery_mssql_counters_locks_per_batch,
)
from cmk.base.plugins.agent_based.mssql_counters_pageactivity import (
    _check_base as check_pageactivity_base,
)
from cmk.base.plugins.agent_based.mssql_counters_pageactivity import (
    discovery_mssql_counters_pageactivity,
)
from cmk.base.plugins.agent_based.mssql_counters_section import parse_mssql_counters
from cmk.base.plugins.agent_based.mssql_counters_sqlstats import _check_base as check_sqlstats_base
from cmk.base.plugins.agent_based.mssql_counters_sqlstats import discovery_mssql_counters_sqlstats
from cmk.base.plugins.agent_based.mssql_counters_transactions import (
    _check_base as check_transactions_base,
)
from cmk.base.plugins.agent_based.mssql_counters_transactions import (
    discovery_mssql_counters_transactions,
)

ValueStore = Dict[str, Any]

big_string_table = [
    ['None', 'utc_time', 'None', '19.08.2020 14:25:04'],
    ['MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'memory_broker_clerk_size', 'Buffer_Pool', '180475'],
    ['MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'simulation_benefit', 'Buffer_Pool', '0'],
    ['MSSQL_VEEAMSQL2012:Buffer_Manager', 'buffer_cache_hit_ratio', 'None', '3090'],
    ['MSSQL_VEEAMSQL2012:Buffer_Manager', 'buffer_cache_hit_ratio_base', 'None', '3090'],
    ['MSSQL_VEEAMSQL2012:Buffer_Manager', 'page_lookups/sec', 'None', '6649047653'],
    ['MSSQL_VEEAMSQL2012:Buffer_Manager', 'readahead_pages/sec', 'None', '1424319'],
    ['MSSQL_VEEAMSQL2012:Buffer_Manager', 'readahead_pages/sec', 'None', '3220650'],
    ['MSSQL_VEEAMSQL2012:Buffer_Manager', 'page_writes/sec', 'None', '3066377'],
    ['MSSQL_VEEAMSQL2012:Buffer_Node', 'database_pages', '000', '180475'],
    ['MSSQL_VEEAMSQL2012:Buffer_Node', 'remote_node_page_lookups/sec', '000', '0'],
    ['MSSQL_VEEAMSQL2012:General_Statistics', 'active_temp_tables', 'None', '229'],
    ['MSSQL_VEEAMSQL2012:General_Statistics', 'temp_tables_creation_rate', 'None', '217262'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_requests/sec', 'OibTrackTbl', '0'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_timeouts/sec', 'OibTrackTbl', '0'],
    ['MSSQL_VEEAMSQL2012:Databases', 'data_file(s)_size_(kb)', 'tempdb', '164928'],
    ['MSSQL_VEEAMSQL2012:Databases', 'log_file(s)_size_(kb)', 'tempdb', '13624'],
    ['MSSQL_VEEAMSQL2012:Databases', 'log_file(s)_used_size_(kb)', 'tempdb', '629'],
    ['MSSQL_VEEAMSQL2012:Databases', 'transactions/sec', 'tempdb', '24410428'],
    ['MSSQL_VEEAMSQL2012:Databases', 'tracked_transactions/sec', 'tempdb', '0'],
    ['MSSQL_VEEAMSQL2012:Databases', 'write_transactions/sec', 'tempdb', '10381607'],
    ['MSSQL_VEEAMSQL2012:Database_Replica', 'redo_bytes_remaining', '_Total', '0'],
    ['MSSQL_VEEAMSQL2012:Database_Replica', 'redo_blocked/sec', '_Total', '0'],
    ['MSSQL_VEEAMSQL2012:Availability_Replica', 'flow_control/sec', '_Total', '0'],
    ['MSSQL_VEEAMSQL2012:Availability_Replica', 'resent_messages/sec', '_Total', '0'],
    ['MSSQL_VEEAMSQL2012:Latches', 'latch_waits/sec', 'None', '8694347'],
    ['MSSQL_VEEAMSQL2012:Latches', 'superlatch_demotions/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Access_Methods', 'full_scans/sec', 'None', '88522013'],
    ['MSSQL_VEEAMSQL2012:Access_Methods', 'insysxact_waits/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:SQL_Errors', 'errors/sec', 'DB_Offline_Errors', '0'],
    ['MSSQL_VEEAMSQL2012:SQL_Errors', 'errors/sec', '_Total', '228398'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'batch_requests/sec', 'None', '22476651'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'misguided_plan_executions/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Plan_Cache', 'cache_hit_ratio', 'Temporary_Tables_&_Table_Variables', '588'],
    ['MSSQL_VEEAMSQL2012:Plan_Cache', 'cache_objects_in_use', '_Total', '2'],
    ['MSSQL_VEEAMSQL2012:Cursor_Manager_by_Type', 'cache_hit_ratio', 'TSQL_Local_Cursor', '730'],
    ['MSSQL_VEEAMSQL2012:Cursor_Manager_by_Type', 'number_of_active_cursor_plans', '_Total', '35'],
    ['MSSQL_VEEAMSQL2012:Cursor_Manager_Total', 'cursor_conversion_rate', 'None', '17'],
    ['MSSQL_VEEAMSQL2012:Memory_Manager', 'external_benefit_of_memory', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Memory_Manager', 'total_server_memory_(kb)', 'None', '4233648'],
    ['MSSQL_VEEAMSQL2012:Memory_Node', 'database_node_memory_(kb)', '000', '1443800'],
    ['MSSQL_VEEAMSQL2012:Memory_Node', 'total_node_memory_(kb)', '000', '4233648'],
    ['MSSQL_VEEAMSQL2012:User_Settable', 'query', 'User_counter_10', '0'],
    ['MSSQL_VEEAMSQL2012:User_Settable', 'query', 'User_counter_9', '0'],
    ['MSSQL_VEEAMSQL2012:User_Settable', 'query', 'User_counter_1', '0'],
    ['MSSQL_VEEAMSQL2012:Transactions', 'transactions', 'None', '6'],
    ['MSSQL_VEEAMSQL2012:Transactions', 'snapshot_transactions', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Broker_Statistics', 'sql_sends/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Broker_Statistics', 'sql_send_total', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Broker/DBM_Transport', 'open_connection_count', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Broker/DBM_Transport', 'send_i/os/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Broker_Activation', 'tasks_started/sec', 'VeeamBackup', '0'],
    ['MSSQL_VEEAMSQL2012:Broker_TO_Statistics', 'transmission_obj_gets/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Wait_Statistics', 'lock_waits', 'Average_wait_time_(ms)', '0'],
    ['MSSQL_VEEAMSQL2012:Wait_Statistics', 'memory_grant_queue_waits', 'Average_wait_time_(ms)', '0'],
    ['MSSQL_VEEAMSQL2012:Exec_Statistics', 'extended_procedures', 'Average_execution_time_(ms)', '0'],
    ['MSSQL_VEEAMSQL2012:Exec_Statistics', 'dtc_calls', 'Average_execution_time_(ms)', '0'],
    ['MSSQL_VEEAMSQL2012:CLR', 'clr_execution', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Catalog_Metadata', 'cache_hit_ratio', 'tempdb', '29305065'],
    ['MSSQL_VEEAMSQL2012:Catalog_Metadata', 'cache_hit_ratio_base', 'tempdb', '29450560'],
    ['MSSQL_VEEAMSQL2012:Workload_Group_Stats', 'cpu_usage_%', 'internal', '0'],
    ['MSSQL_VEEAMSQL2012:Workload_Group_Stats', 'cpu_usage_%_base', 'internal', '0'],
    ['MSSQL_VEEAMSQL2012:Resource_Pool_Stats', 'cpu_usage_%', 'internal', '0'],
    ['MSSQL_VEEAMSQL2012:Resource_Pool_Stats', 'cpu_usage_%_base', 'internal', '0'],
    ['MSSQL_VEEAMSQL2012:Query_Execution', 'remote_requests/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Query_Execution', 'remote_resend_requests/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:FileTable', 'filetable_db_operations/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:FileTable', 'filetable_table_operations/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Batch_Resp_Statistics', 'batches_>=000000ms_&_<000001ms', 'CPU_Time:Total(ms)', '0'],
    ['MSSQL_VEEAMSQL2012:Batch_Resp_Statistics', 'batches_>=000001ms_&_<000002ms', 'CPU_Time:Total(ms)', '668805'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'batch_requests/sec', 'None', '22476651'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'forced_parameterizations/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'auto-param_attempts/sec', 'None', '1133'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'failed_auto-params/sec', 'None', '1027'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'safe_auto-params/sec', 'None', '8'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'unsafe_auto-params/sec', 'None', '98'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'sql_compilations/sec', 'None', '2189403'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'sql_re-compilations/sec', 'None', '272134'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'sql_attention_rate', 'None', '199'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'guided_plan_executions/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:SQL_Statistics', 'misguided_plan_executions/sec', 'None', '0'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_requests/sec', '_Total', '3900449701'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_timeouts/sec', '_Total', '86978'],
    ['MSSQL_VEEAMSQL2012:Locks', 'number_of_deadlocks/sec', '_Total', '19'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_waits/sec', '_Total', '938'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_wait_time_(ms)', '_Total', '354413'],
    ['MSSQL_VEEAMSQL2012:Locks', 'average_wait_time_(ms)', '_Total', '354413'],
    ['MSSQL_VEEAMSQL2012:Locks', 'average_wait_time_base', '_Total', '938'],
    ['MSSQL_VEEAMSQL2012:Locks', 'lock_timeouts_(timeout_>_0)/sec', '_Total', '0'],
]


big_parsed_data = {
    ('None', 'None'): {
        'utc_time': 1597847104.0
    },
    ('MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'Buffer_Pool'): {
        'memory_broker_clerk_size': 180475,
        'simulation_benefit': 0
    },
    ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {
        'buffer_cache_hit_ratio': 3090,
        'buffer_cache_hit_ratio_base': 3090,
        'page_lookups/sec': 6649047653,
        'readahead_pages/sec': 1424319,
        'page_writes/sec': 3066377,
    },
    ('MSSQL_VEEAMSQL2012:Buffer_Node', '000'): {
        'database_pages': 180475,
        'remote_node_page_lookups/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:General_Statistics', 'None'): {
        'active_temp_tables': 229,
        'temp_tables_creation_rate': 217262
    },
    ('MSSQL_VEEAMSQL2012:Locks', 'OibTrackTbl'): {
        'lock_requests/sec': 0,
        'lock_timeouts/sec': 0
    },
    ('MSSQL_VEEAMSQL2012', 'tempdb'): {
        'data_file(s)_size_(kb)': 164928,
        'log_file(s)_size_(kb)': 13624,
        'log_file(s)_used_size_(kb)': 629,
        'transactions/sec': 24410428,
        'tracked_transactions/sec': 0,
        'write_transactions/sec': 10381607,
    },
    ('MSSQL_VEEAMSQL2012:Database_Replica', '_Total'): {
        'redo_bytes_remaining': 0,
        'redo_blocked/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Availability_Replica', '_Total'): {
        'flow_control/sec': 0,
        'resent_messages/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Latches', 'None'): {
        'latch_waits/sec': 8694347,
        'superlatch_demotions/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Access_Methods', 'None'): {
        'full_scans/sec': 88522013,
        'insysxact_waits/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:SQL_Errors', 'DB_Offline_Errors'): {
        'errors/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:SQL_Errors', '_Total'): {
        'errors/sec': 228398
    },
    ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): {
        'batch_requests/sec': 22476651,
        'misguided_plan_executions/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Plan_Cache', 'Temporary_Tables_&_Table_Variables'): {
        'cache_hit_ratio': 588
    },
    ('MSSQL_VEEAMSQL2012:Plan_Cache', '_Total'): {
        'cache_objects_in_use': 2
    },
    ('MSSQL_VEEAMSQL2012:Cursor_Manager_by_Type', 'TSQL_Local_Cursor'): {
        'cache_hit_ratio': 730
    },
    ('MSSQL_VEEAMSQL2012:Cursor_Manager_by_Type', '_Total'): {
        'number_of_active_cursor_plans': 35
    },
    ('MSSQL_VEEAMSQL2012:Cursor_Manager_Total', 'None'): {
        'cursor_conversion_rate': 17
    },
    ('MSSQL_VEEAMSQL2012:Memory_Manager', 'None'): {
        'external_benefit_of_memory': 0,
        'total_server_memory_(kb)': 4233648
    },
    ('MSSQL_VEEAMSQL2012:Memory_Node', '000'): {
        'database_node_memory_(kb)': 1443800,
        'total_node_memory_(kb)': 4233648
    },
    ('MSSQL_VEEAMSQL2012:User_Settable', 'User_counter_10'): {
        'query': 0
    },
    ('MSSQL_VEEAMSQL2012:User_Settable', 'User_counter_9'): {
        'query': 0
    },
    ('MSSQL_VEEAMSQL2012:User_Settable', 'User_counter_1'): {
        'query': 0
    },
    ('MSSQL_VEEAMSQL2012:Transactions', 'None'): {
        'transactions': 6,
        'snapshot_transactions': 0
    },
    ('MSSQL_VEEAMSQL2012:Broker_Statistics', 'None'): {
        'sql_sends/sec': 0,
        'sql_send_total': 0
    },
    ('MSSQL_VEEAMSQL2012:Broker/DBM_Transport', 'None'): {
        'open_connection_count': 0,
        'send_i/os/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Broker_Activation', 'VeeamBackup'): {
        'tasks_started/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Broker_TO_Statistics', 'None'): {
        'transmission_obj_gets/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Wait_Statistics', 'Average_wait_time_(ms)'): {
        'lock_waits': 0,
        'memory_grant_queue_waits': 0
    },
    ('MSSQL_VEEAMSQL2012:Exec_Statistics', 'Average_execution_time_(ms)'): {
        'extended_procedures': 0,
        'dtc_calls': 0
    },
    ('MSSQL_VEEAMSQL2012:CLR', 'None'): {
        'clr_execution': 0
    },
    ('MSSQL_VEEAMSQL2012:Catalog_Metadata', 'tempdb'): {
        'cache_hit_ratio': 29305065,
        'cache_hit_ratio_base': 29450560
    },
    ('MSSQL_VEEAMSQL2012:Workload_Group_Stats', 'internal'): {
        'cpu_usage_%': 0,
        'cpu_usage_%_base': 0
    },
    ('MSSQL_VEEAMSQL2012:Resource_Pool_Stats', 'internal'): {
        'cpu_usage_%': 0,
        'cpu_usage_%_base': 0
    },
    ('MSSQL_VEEAMSQL2012:Query_Execution', 'None'): {
        'remote_requests/sec': 0,
        'remote_resend_requests/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:FileTable', 'None'): {
        'filetable_db_operations/sec': 0,
        'filetable_table_operations/sec': 0
    },
    ('MSSQL_VEEAMSQL2012:Batch_Resp_Statistics', 'CPU_Time:Total(ms)'): {
        'batches_>=000000ms_&_<000001ms': 0,
        'batches_>=000001ms_&_<000002ms': 668805
    },
    ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): {
        'batch_requests/sec': 22476651,
        'forced_parameterizations/sec': 0,
        'auto-param_attempts/sec': 1133,
        'failed_auto-params/sec': 1027,
        'safe_auto-params/sec': 8,
        'unsafe_auto-params/sec': 98,
        'sql_compilations/sec': 2189403,
        'sql_re-compilations/sec': 272134,
        'sql_attention_rate': 199,
        'guided_plan_executions/sec': 0,
        'misguided_plan_executions/sec': 0,
    },
    ('MSSQL_VEEAMSQL2012:Locks', '_Total'): {
        'lock_requests/sec': 3900449701,
        'lock_timeouts/sec': 86978,
        'number_of_deadlocks/sec': 19,
        'lock_waits/sec': 938,
        'lock_wait_time_(ms)': 354413,
        'average_wait_time_(ms)': 354413,
        'average_wait_time_base': 938,
        'lock_timeouts_(timeout_>_0)/sec': 0,
    },
}

big_services = [
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None buffer_cache_hit_ratio'),
    Service(item='MSSQL_VEEAMSQL2012:Catalog_Metadata tempdb cache_hit_ratio')
]


@pytest.mark.parametrize("string_table,expected_parsed_data", [
    (big_string_table, big_parsed_data),
])
def test_parse_mssql_counters(string_table, expected_parsed_data):
    assert parse_mssql_counters(string_table) == expected_parsed_data


@pytest.mark.parametrize("params,section,expected_services", [
    ({}, big_parsed_data, big_services),
])
def test_discovery_mssql_counters_cache_hits(params, section, expected_services):
    results = list(discovery_mssql_counters_cache_hits(params, section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,section,expected_results", [
    ('MSSQL_VEEAMSQL2012:Catalog_Metadata tempdb cache_hit_ratio', big_parsed_data, [
        Result(state=state.OK, summary='99.51%'),
        Metric('cache_hit_ratio', 99.50596864711571),
    ]),
])
def test_check_mssql_counters_cache_hits(item, section, expected_results):
    results = list(check_mssql_counters_cache_hits(item, section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize("section,expected_services", [
    (big_parsed_data, [
        Service(item='MSSQL_VEEAMSQL2012 tempdb'),
    ]),
])
def test_discovery_mssql_counters_file_sizes(section, expected_services):
    results = list(discovery_mssql_counters_file_sizes(section=section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,params,section,expected_results", [
    ("MSSQL_VEEAMSQL2012 tempdb", {}, big_parsed_data, [
        Result(state=state.OK, summary='Data files: 161 MiB'),
        Metric('data_files', 168886272.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Log files total: 13.3 MiB'),
        Metric('log_files', 13950976.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Log files used: 629 KiB'),
        Metric('log_files_used', 644096.0, boundaries=(0.0, None)),
    ]),
    ("MSSQL_VEEAMSQL2012 tempdb", {'log_files_used': (12555878, 13253427),}, big_parsed_data, [
        Result(state=state.OK, summary='Data files: 161 MiB'),
        Metric('data_files', 168886272.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Log files total: 13.3 MiB'),
        Metric('log_files', 13950976.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Log files used: 629 KiB'),
        Metric('log_files_used', 644096.0, levels=(12555878.0, 13253427.0), boundaries=(0.0, None)),
    ]),
    ("MSSQL_VEEAMSQL2012 tempdb", {'log_files_used': (90.0, 95.0),}, big_parsed_data, [
        Result(state=state.OK, summary='Data files: 161 MiB'),
        Metric('data_files', 168886272.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Log files total: 13.3 MiB'),
        Metric('log_files', 13950976.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Log files used: 4.62%'),
        Metric('log_files_used', 644096.0, levels=(12555878.4, 13253427.2), boundaries=(0.0, None)),
    ]),
])
def test_check_mssql_counters_file_sizes(item, params, section, expected_results):
    results = list(check_mssql_counters_file_sizes(
        item=item,
        params=params,
        section=section,
    ))
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize("section,expected_services", [
    (big_parsed_data, [Service(item='MSSQL_VEEAMSQL2012')]),
])
def test_discovery_mssql_counters_locks_per_batch(section, expected_services):
    results = list(discovery_mssql_counters_locks_per_batch(section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,params,section,expected_results", [
    ("MSSQL_VEEAMSQL2012", {}, big_parsed_data, [
        IgnoreResults(value="Cannot calculate rates yet"),
        Result(state=state.OK, summary='0.0'),
        Metric('locks_per_batch', 0.0, boundaries=(0.0, None)),
    ]),
])
def test_check_mssql_locks_per_batch(item, params, section, expected_results):
    # re-run check_locks_per_batch_base() once in order to get rates
    vs: Dict[str, Any] = {}
    results = []
    for time in range(2):
        for result in check_locks_per_batch_base(vs, item, params, section, time*60):
            results.append(result)
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize("section,expected_services", [
    (big_parsed_data, [
        Service(item='MSSQL_VEEAMSQL2012:Locks OibTrackTbl'),
        Service(item='MSSQL_VEEAMSQL2012:Locks _Total'),
    ]),
])
def test_discovery_mssql_counters_locks(section, expected_services):
    results = list(discovery_mssql_counters_locks(section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,params,section,expected_results", [
    ("MSSQL_VEEAMSQL2012:Locks _Total lock_requests/sec", {}, big_parsed_data, [
        IgnoreResults(value="Cannot calculate rates yet"),
        IgnoreResults(value="Cannot calculate rates yet"),
        IgnoreResults(value="Cannot calculate rates yet"),
        IgnoreResults(value="Cannot calculate rates yet"),
        Result(state=state.OK, summary='Requests: 0.0/s'),
        Metric('lock_requests_per_second', 0.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Timeouts: 0.0/s'),
        Metric('lock_timeouts_per_second', 0.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Deadlocks: 0.0/s'),
        Metric('number_of_deadlocks_per_second', 0.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Waits: 0.0/s'),
        Metric('lock_waits_per_second', 0.0, boundaries=(0.0, None))
    ]),
])
def test_check_mssql_locks(item, params, section, expected_results):
    # re-run cluster_check_locks_per_batch_base() once in order to get rates
    vs: ValueStore = {}
    results = []
    t0 = 1597839904
    for i in range(2):
        for result in check_locks_base(vs, t0 + i, item, params, section):
            results.append(result)
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize("section,expected_services", [
    (big_parsed_data, [
        Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None'),
    ]),
])
def test_discovery_mssql_counters_pageactivity(section, expected_services):
    results = list(discovery_mssql_counters_pageactivity(section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,params,section,expected_results", [
    ("MSSQL_VEEAMSQL2012:Buffer_Manager None", {}, big_parsed_data, [
        IgnoreResults(value="Cannot calculate rates yet"),
        IgnoreResults(value="Cannot calculate rates yet"),
        Result(state=state.OK, summary='Writes: 0.0/s'),
        Metric('page_writes_per_second', 0.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Lookups: 0.0/s'),
        Metric('page_lookups_per_second', 0.0, boundaries=(0.0, None)),
    ]),
])
def test_check_mssql_counters_pageactivity(item, params, section, expected_results):
    # re-run cluster_check_locks_per_batch_base() once in order to get rates
    vs: ValueStore = {}
    results = []
    t0 = 1597839904
    for i in range(2):
        for result in check_pageactivity_base(vs, t0 + i, item, params, section):
            results.append(result)
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize("section,expected_services", [
    (big_parsed_data, [
        Service(item='MSSQL_VEEAMSQL2012:SQL_Statistics None batch_requests/sec'),
        Service(item='MSSQL_VEEAMSQL2012:SQL_Statistics None sql_compilations/sec'),
        Service(item='MSSQL_VEEAMSQL2012:SQL_Statistics None sql_re-compilations/sec'),
    ]),
])
def test_discovery_mssql_counters_sqlstats(section, expected_services):
    results = list(discovery_mssql_counters_sqlstats(section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,params,section,expected_results", [
    ("MSSQL_VEEAMSQL2012:SQL_Statistics None sql_compilations/sec", {}, big_parsed_data, [
        IgnoreResults(value="Cannot calculate rates yet"),
        Result(state=state.OK, summary='0.0/s'),
        Metric('sql_compilations_per_second', 0.0, boundaries=(0.0, None)),
    ]),
])
def test_check_mssql_counters_sqlstats(item, params, section, expected_results):
    # re-run cluster_check_locks_per_batch_base() once in order to get rates
    vs: ValueStore = {}
    results = []
    t0 = 1597839904
    for i in range(2):
        for result in check_sqlstats_base(vs, t0 + i, item, params, section):
            results.append(result)
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


@pytest.mark.parametrize("section,expected_services", [
    (big_parsed_data, [
        Service(item='MSSQL_VEEAMSQL2012 tempdb'),
    ]),
])
def test_discovery_mssql_counters_transactions(section, expected_services):
    results = list(discovery_mssql_counters_transactions(section))
    print(",\n".join(str(r) for r in results))
    assert results == expected_services


@pytest.mark.parametrize("item,params,section,expected_results", [
    ("MSSQL_VEEAMSQL2012 tempdb transactions/sec", {}, big_parsed_data, [
        IgnoreResults(value="Cannot calculate rates yet"),
        IgnoreResults(value="Cannot calculate rates yet"),
        IgnoreResults(value="Cannot calculate rates yet"),
        Result(state=state.OK, summary='Transactions: 0.0/s'),
        Metric('transactions_per_second', 0.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Write Transactions: 0.0/s'),
        Metric('write_transactions_per_second', 0.0, boundaries=(0.0, None)),
        Result(state=state.OK, summary='Tracked Transactions: 0.0/s'),
        Metric('tracked_transactions_per_second', 0.0, boundaries=(0.0, None)),
    ]),
])
def test_check_mssql_counters_transactions(item, params, section, expected_results):
    # re-run cluster_check_locks_per_batch_base() once in order to get rates
    vs: ValueStore = {}
    results = []
    t0 = 1597839904
    for i in range(2):
        for result in check_transactions_base(vs, t0 + i, item, params, section):
            results.append(result)
    print(",\n".join(str(r) for r in results))
    assert results == expected_results


if __name__ == "__main__":
    pytest.main(["-svv", "-T=unit", __file__])
