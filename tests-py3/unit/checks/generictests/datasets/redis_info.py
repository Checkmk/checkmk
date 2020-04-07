#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'redis_info'

freeze_time = '2019-12-06T11:36:00'

info = [
    ['[[[MY_FIRST_REDIS|127.0.0.1|6380]]]'], ['# Server'],
    ['redis_version', '4.0.9'], ['redis_git_sha1', '00000000'],
    ['redis_git_dirty', '0'], ['redis_build_id', '9435c3c2879311f3'],
    ['redis_mode', 'standalone'], ['os', 'Linux 4.15.0-1065-oem x86_64'],
    ['arch_bits', '64'], ['multiplexing_api', 'epoll'],
    ['atomicvar_api', 'atomic-builtin'], ['gcc_version', '7.4.0'],
    ['process_id', '1064'],
    ['run_id',
     '38d09b0d45dcc76bbff989d894fae6bb98e93a15'], ['tcp_port', '6380'],
    ['uptime_in_seconds', '10267'], ['uptime_in_days', '0'], ['hz', '10'],
    ['lru_clock', '15347536'], ['executable', '/usr/bin/redis-server'],
    ['config_file', '/etc/redis/redis2.conf'], ['# Clients'],
    ['connected_clients', '1'], ['client_longest_output_list', '0'],
    ['client_biggest_input_buf', '0'], ['blocked_clients', '0'], ['# Memory'],
    ['used_memory', '533072'], ['used_memory_human', '520.58K'],
    ['used_memory_rss', '4083712'], ['used_memory_rss_human', '3.89M'],
    ['used_memory_peak', '534096'], ['used_memory_peak_human', '521.58K'],
    ['used_memory_peak_perc', '99.81%'], ['used_memory_overhead', '524942'],
    ['used_memory_startup', '475312'], ['used_memory_dataset', '8130'],
    ['used_memory_dataset_perc', '14.08%'],
    ['total_system_memory', '16522428416'],
    ['total_system_memory_human', '15.39G'], ['used_memory_lua', '37888'],
    ['used_memory_lua_human', '37.00K'], ['maxmemory', '0'],
    ['maxmemory_human', '0B'], ['maxmemory_policy', 'noeviction'],
    ['mem_fragmentation_ratio', '7.66'], ['mem_allocator', 'jemalloc-3.6.0'],
    ['active_defrag_running', '0'], ['lazyfree_pending_objects', '0'],
    ['# Persistence'], ['loading', '0'], ['rdb_changes_since_last_save', '0'],
    ['rdb_bgsave_in_progress', '0'], ['rdb_last_save_time', '1575618357'],
    ['rdb_last_bgsave_status', 'ok'], ['rdb_last_bgsave_time_sec', '-1'],
    ['rdb_current_bgsave_time_sec', '-1'], ['rdb_last_cow_size', '0'],
    ['aof_enabled', '0'], ['aof_rewrite_in_progress', '0'],
    ['aof_rewrite_scheduled', '0'], ['aof_last_rewrite_time_sec', '-1'],
    ['aof_current_rewrite_time_sec', '-1'],
    ['aof_last_bgrewrite_status', 'ok'], ['aof_last_write_status', 'ok'],
    ['aof_last_cow_size', '0'], ['# Stats'],
    ['total_connections_received', '140'], ['total_commands_processed', '279'],
    ['instantaneous_ops_per_sec', '0'], ['total_net_input_bytes', '6300'],
    ['total_net_output_bytes', '387527'], ['instantaneous_input_kbps', '0.00'],
    ['instantaneous_output_kbps', '0.00'], ['rejected_connections', '0'],
    ['sync_full', '0'], ['sync_partial_ok', '0'], ['sync_partial_err', '0'],
    ['expired_keys', '0'], ['expired_stale_perc', '0.00'],
    ['expired_time_cap_reached_count', '0'], ['evicted_keys', '0'],
    ['keyspace_hits', '0'], ['keyspace_misses', '0'], ['pubsub_channels', '0'],
    ['pubsub_patterns', '0'], ['latest_fork_usec', '0'],
    ['migrate_cached_sockets', '0'], ['slave_expires_tracked_keys', '0'],
    ['active_defrag_hits', '0'], ['active_defrag_misses', '0'],
    ['active_defrag_key_hits', '0'], ['active_defrag_key_misses', '0'],
    ['# Replication'], ['role', 'master'], ['connected_slaves', '0'],
    ['master_replid', '6327bee2847a3f6e0d39ab05b52967d354a30543'],
    ['master_replid2', '0000000000000000000000000000000000000000'],
    ['master_repl_offset', '0'], ['second_repl_offset', '-1'],
    ['repl_backlog_active', '0'], ['repl_backlog_size', '1048576'],
    ['repl_backlog_first_byte_offset', '0'], ['repl_backlog_histlen', '0'],
    ['# CPU'], ['used_cpu_sys', '11.64'], ['used_cpu_user', '6.65'],
    ['used_cpu_sys_children', '0.00'], ['used_cpu_user_children', '0.00'],
    ['# Cluster'], ['cluster_enabled', '0'], ['# Keyspace'],
    ['[[[MY_SECOND_REDIS|127.0.0.1|6379]]]'], ['# Server'],
    ['redis_version', '4.0.9'], ['redis_git_sha1', '00000000'],
    ['redis_git_dirty', '0'], ['redis_build_id', '9435c3c2879311f3'],
    ['redis_mode', 'standalone'], ['os', 'Linux 4.15.0-1065-oem x86_64'],
    ['arch_bits', '64'], ['multiplexing_api', 'epoll'],
    ['atomicvar_api', 'atomic-builtin'], ['gcc_version', '7.4.0'],
    ['process_id', '1320'],
    ['run_id',
     'd9fb68e25be9d16e6eacd4643aefa4d1a8cec9ce'], ['tcp_port', '6379'],
    ['uptime_in_seconds', '10266'], ['uptime_in_days', '0'], ['hz', '10'],
    ['lru_clock', '15347536'], ['executable', '/usr/bin/redis-server'],
    ['config_file', '/etc/redis/redis.conf'], ['# Clients'],
    ['connected_clients', '1'], ['client_longest_output_list', '0'],
    ['client_biggest_input_buf', '0'], ['blocked_clients', '0'], ['# Memory'],
    ['used_memory', '841264'], ['used_memory_human', '821.55K'],
    ['used_memory_rss', '3846144'], ['used_memory_rss_human', '3.67M'],
    ['used_memory_peak', '842288'], ['used_memory_peak_human', '822.55K'],
    ['used_memory_peak_perc', '99.88%'], ['used_memory_overhead', '832438'],
    ['used_memory_startup', '782512'], ['used_memory_dataset', '8826'],
    ['used_memory_dataset_perc', '15.02%'],
    ['total_system_memory', '16522428416'],
    ['total_system_memory_human', '15.39G'], ['used_memory_lua', '37888'],
    ['used_memory_lua_human', '37.00K'], ['maxmemory', '0'],
    ['maxmemory_human', '0B'], ['maxmemory_policy', 'noeviction'],
    ['mem_fragmentation_ratio', '4.57'], ['mem_allocator', 'jemalloc-3.6.0'],
    ['active_defrag_running', '0'], ['lazyfree_pending_objects', '0'],
    ['# Persistence'], ['loading', '0'], ['rdb_changes_since_last_save', '0'],
    ['rdb_bgsave_in_progress', '0'], ['rdb_last_save_time', '1575618358'],
    ['rdb_last_bgsave_status', 'ok'], ['rdb_last_bgsave_time_sec', '-1'],
    ['rdb_current_bgsave_time_sec', '-1'], ['rdb_last_cow_size', '0'],
    ['aof_enabled', '0'], ['aof_rewrite_in_progress', '0'],
    ['aof_rewrite_scheduled', '0'], ['aof_last_rewrite_time_sec', '-1'],
    ['aof_current_rewrite_time_sec', '-1'],
    ['aof_last_bgrewrite_status', 'ok'], ['aof_last_write_status', 'ok'],
    ['aof_last_cow_size', '0'], ['# Stats'],
    ['total_connections_received', '140'], ['total_commands_processed', '139'],
    ['instantaneous_ops_per_sec', '0'], ['total_net_input_bytes', '1960'],
    ['total_net_output_bytes', '385217'], ['instantaneous_input_kbps', '0.00'],
    ['instantaneous_output_kbps', '0.00'], ['rejected_connections', '0'],
    ['sync_full', '0'], ['sync_partial_ok', '0'], ['sync_partial_err', '0'],
    ['expired_keys', '0'], ['expired_stale_perc', '0.00'],
    ['expired_time_cap_reached_count', '0'], ['evicted_keys', '0'],
    ['keyspace_hits', '0'], ['keyspace_misses', '0'], ['pubsub_channels', '0'],
    ['pubsub_patterns', '0'], ['latest_fork_usec', '0'],
    ['migrate_cached_sockets', '0'], ['slave_expires_tracked_keys', '0'],
    ['active_defrag_hits', '0'], ['active_defrag_misses', '0'],
    ['active_defrag_key_hits', '0'], ['active_defrag_key_misses', '0'],
    ['# Replication'], ['role', 'master'], ['connected_slaves', '0'],
    ['master_replid', 'fc24a4f675674698bde072eccf4cc8dc06ecb603'],
    ['master_replid2', '0000000000000000000000000000000000000000'],
    ['master_repl_offset', '0'], ['second_repl_offset', '-1'],
    ['repl_backlog_active', '0'], ['repl_backlog_size', '1048576'],
    ['repl_backlog_first_byte_offset', '0'], ['repl_backlog_histlen', '0'],
    ['# CPU'], ['used_cpu_sys', '16.29'], ['used_cpu_user', '6.27'],
    ['used_cpu_sys_children', '0.00'], ['used_cpu_user_children', '0.00'],
    ['# Cluster'], ['cluster_enabled', '0'], ['# Keyspace'],
    ['db0', 'keys=5,expires=0,avg_ttl=0']
]

discovery = {
    '': [('MY_FIRST_REDIS', {}), ('MY_SECOND_REDIS', {})],
    'clients': [('MY_FIRST_REDIS', {}), ('MY_SECOND_REDIS', {})],
    'persistence': [('MY_FIRST_REDIS', {}), ('MY_SECOND_REDIS', {})]
}

checks = {
    '': [
        (
            'MY_FIRST_REDIS', {}, [
                (0, 'Mode: Standalone', []),
                (
                    0, 'Up since Fri Dec  6 09:44:53 2019, uptime: 2:51:07', [
                        ('uptime', 10267, None, None, None, None)
                    ]
                ), (0, 'Version: 4.0.9', []),
                (0, 'GCC compiler version: 7.4.0', []), (0, 'PID: 1064', []),
                (0, 'IP: 127.0.0.1', []), (0, 'Port: 6380', [])
            ]
        ),
        (
            'MY_SECOND_REDIS', {}, [
                (0, 'Mode: Standalone', []),
                (
                    0, 'Up since Fri Dec  6 09:44:54 2019, uptime: 2:51:06', [
                        ('uptime', 10266, None, None, None, None)
                    ]
                ), (0, 'Version: 4.0.9', []),
                (0, 'GCC compiler version: 7.4.0', []), (0, 'PID: 1320', []),
                (0, 'IP: 127.0.0.1', []), (0, 'Port: 6379', [])
            ]
        )
    ],
    'clients': [
        (
            'MY_FIRST_REDIS', {}, [
                (
                    0, 'Number of client connections: 1', [
                        ('clients_connected', 1, None, None, None, None)
                    ]
                ),
                (
                    0, 'Longest output list: 0', [
                        ('clients_output', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Biggest input buffer: 0', [
                        ('clients_input', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of clients pending on a blocking call: 0', [
                        ('clients_blocked', 0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'MY_SECOND_REDIS', {}, [
                (
                    0, 'Number of client connections: 1', [
                        ('clients_connected', 1, None, None, None, None)
                    ]
                ),
                (
                    0, 'Longest output list: 0', [
                        ('clients_output', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Biggest input buffer: 0', [
                        ('clients_input', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of clients pending on a blocking call: 0', [
                        ('clients_blocked', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'persistence': [
        (
            'MY_FIRST_REDIS', {
                'rdb_last_bgsave': 1,
                'aof_last_rewrite': 1
            }, [
                (0, 'Last RDB save operation: successful', []),
                (0, 'Last AOF rewrite operation: successful', []),
                (0, 'Last successful RDB save: 2019-12-06 08:45:57', []),
                (
                    0, 'Number of changes since last dump: 0', [
                        ('changes_sld', 0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'MY_SECOND_REDIS', {
                'rdb_last_bgsave': 1,
                'aof_last_rewrite': 1
            }, [
                (0, 'Last RDB save operation: successful', []),
                (0, 'Last AOF rewrite operation: successful', []),
                (0, 'Last successful RDB save: 2019-12-06 08:45:58', []),
                (
                    0, 'Number of changes since last dump: 0', [
                        ('changes_sld', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
