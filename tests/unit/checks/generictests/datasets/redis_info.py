# -*- encoding: utf-8
# yapf: disable
checkname = 'redis_info'

freeze_time = '2019-12-06T11:36:00'

info = [
    [u'[[[MY_FIRST_REDIS|127.0.0.1|6380]]]'], [u'# Server'],
    [u'redis_version', u'4.0.9'], [u'redis_git_sha1', u'00000000'],
    [u'redis_git_dirty', u'0'], [u'redis_build_id', u'9435c3c2879311f3'],
    [u'redis_mode', u'standalone'], [u'os', u'Linux 4.15.0-1065-oem x86_64'],
    [u'arch_bits', u'64'], [u'multiplexing_api', u'epoll'],
    [u'atomicvar_api', u'atomic-builtin'], [u'gcc_version', u'7.4.0'],
    [u'process_id', u'1064'],
    [u'run_id', u'38d09b0d45dcc76bbff989d894fae6bb98e93a15'],
    [u'tcp_port', u'6380'], [u'uptime_in_seconds', u'10267'],
    [u'uptime_in_days', u'0'], [u'hz', u'10'], [u'lru_clock', u'15347536'],
    [u'executable', u'/usr/bin/redis-server'],
    [u'config_file', u'/etc/redis/redis2.conf'], [u'# Clients'],
    [u'connected_clients', u'1'], [u'client_longest_output_list', u'0'],
    [u'client_biggest_input_buf', u'0'], [u'blocked_clients', u'0'],
    [u'# Memory'], [u'used_memory', u'533072'],
    [u'used_memory_human', u'520.58K'], [u'used_memory_rss', u'4083712'],
    [u'used_memory_rss_human', u'3.89M'], [u'used_memory_peak', u'534096'],
    [u'used_memory_peak_human', u'521.58K'],
    [u'used_memory_peak_perc',
     u'99.81%'], [u'used_memory_overhead', u'524942'],
    [u'used_memory_startup', u'475312'], [u'used_memory_dataset', u'8130'],
    [u'used_memory_dataset_perc', u'14.08%'],
    [u'total_system_memory', u'16522428416'],
    [u'total_system_memory_human', u'15.39G'], [u'used_memory_lua', u'37888'],
    [u'used_memory_lua_human', u'37.00K'], [u'maxmemory', u'0'],
    [u'maxmemory_human', u'0B'], [u'maxmemory_policy', u'noeviction'],
    [u'mem_fragmentation_ratio',
     u'7.66'], [u'mem_allocator', u'jemalloc-3.6.0'],
    [u'active_defrag_running', u'0'], [u'lazyfree_pending_objects', u'0'],
    [u'# Persistence'], [u'loading', u'0'],
    [u'rdb_changes_since_last_save', u'0'], [u'rdb_bgsave_in_progress', u'0'],
    [u'rdb_last_save_time', u'1575618357'], [u'rdb_last_bgsave_status', u'ok'],
    [u'rdb_last_bgsave_time_sec', u'-1'],
    [u'rdb_current_bgsave_time_sec', u'-1'], [u'rdb_last_cow_size', u'0'],
    [u'aof_enabled', u'0'], [u'aof_rewrite_in_progress', u'0'],
    [u'aof_rewrite_scheduled', u'0'], [u'aof_last_rewrite_time_sec', u'-1'],
    [u'aof_current_rewrite_time_sec', u'-1'],
    [u'aof_last_bgrewrite_status', u'ok'], [u'aof_last_write_status', u'ok'],
    [u'aof_last_cow_size', u'0'], [u'# Stats'],
    [u'total_connections_received',
     u'140'], [u'total_commands_processed', u'279'],
    [u'instantaneous_ops_per_sec', u'0'], [u'total_net_input_bytes', u'6300'],
    [u'total_net_output_bytes', u'387527'],
    [u'instantaneous_input_kbps', u'0.00'],
    [u'instantaneous_output_kbps', u'0.00'], [u'rejected_connections', u'0'],
    [u'sync_full', u'0'], [u'sync_partial_ok', u'0'],
    [u'sync_partial_err', u'0'], [u'expired_keys', u'0'],
    [u'expired_stale_perc', u'0.00'],
    [u'expired_time_cap_reached_count', u'0'], [u'evicted_keys', u'0'],
    [u'keyspace_hits', u'0'], [u'keyspace_misses', u'0'],
    [u'pubsub_channels', u'0'], [u'pubsub_patterns', u'0'],
    [u'latest_fork_usec', u'0'], [u'migrate_cached_sockets', u'0'],
    [u'slave_expires_tracked_keys', u'0'], [u'active_defrag_hits', u'0'],
    [u'active_defrag_misses', u'0'], [u'active_defrag_key_hits', u'0'],
    [u'active_defrag_key_misses', u'0'], [u'# Replication'],
    [u'role', u'master'], [u'connected_slaves', u'0'],
    [u'master_replid', u'6327bee2847a3f6e0d39ab05b52967d354a30543'],
    [u'master_replid2', u'0000000000000000000000000000000000000000'],
    [u'master_repl_offset', u'0'], [u'second_repl_offset', u'-1'],
    [u'repl_backlog_active', u'0'], [u'repl_backlog_size', u'1048576'],
    [u'repl_backlog_first_byte_offset', u'0'], [u'repl_backlog_histlen', u'0'],
    [u'# CPU'], [u'used_cpu_sys', u'11.64'], [u'used_cpu_user', u'6.65'],
    [u'used_cpu_sys_children', u'0.00'], [u'used_cpu_user_children', u'0.00'],
    [u'# Cluster'], [u'cluster_enabled', u'0'], [u'# Keyspace'],
    [u'[[[MY_SECOND_REDIS|127.0.0.1|6379]]]'], [u'# Server'],
    [u'redis_version', u'4.0.9'], [u'redis_git_sha1', u'00000000'],
    [u'redis_git_dirty', u'0'], [u'redis_build_id', u'9435c3c2879311f3'],
    [u'redis_mode', u'standalone'], [u'os', u'Linux 4.15.0-1065-oem x86_64'],
    [u'arch_bits', u'64'], [u'multiplexing_api', u'epoll'],
    [u'atomicvar_api', u'atomic-builtin'], [u'gcc_version', u'7.4.0'],
    [u'process_id', u'1320'],
    [u'run_id', u'd9fb68e25be9d16e6eacd4643aefa4d1a8cec9ce'],
    [u'tcp_port', u'6379'], [u'uptime_in_seconds', u'10266'],
    [u'uptime_in_days', u'0'], [u'hz', u'10'], [u'lru_clock', u'15347536'],
    [u'executable', u'/usr/bin/redis-server'],
    [u'config_file', u'/etc/redis/redis.conf'], [u'# Clients'],
    [u'connected_clients', u'1'], [u'client_longest_output_list', u'0'],
    [u'client_biggest_input_buf', u'0'], [u'blocked_clients', u'0'],
    [u'# Memory'], [u'used_memory', u'841264'],
    [u'used_memory_human', u'821.55K'], [u'used_memory_rss', u'3846144'],
    [u'used_memory_rss_human', u'3.67M'], [u'used_memory_peak', u'842288'],
    [u'used_memory_peak_human', u'822.55K'],
    [u'used_memory_peak_perc',
     u'99.88%'], [u'used_memory_overhead', u'832438'],
    [u'used_memory_startup', u'782512'], [u'used_memory_dataset', u'8826'],
    [u'used_memory_dataset_perc', u'15.02%'],
    [u'total_system_memory', u'16522428416'],
    [u'total_system_memory_human', u'15.39G'], [u'used_memory_lua', u'37888'],
    [u'used_memory_lua_human', u'37.00K'], [u'maxmemory', u'0'],
    [u'maxmemory_human', u'0B'], [u'maxmemory_policy', u'noeviction'],
    [u'mem_fragmentation_ratio',
     u'4.57'], [u'mem_allocator', u'jemalloc-3.6.0'],
    [u'active_defrag_running', u'0'], [u'lazyfree_pending_objects', u'0'],
    [u'# Persistence'], [u'loading', u'0'],
    [u'rdb_changes_since_last_save', u'0'], [u'rdb_bgsave_in_progress', u'0'],
    [u'rdb_last_save_time', u'1575618358'], [u'rdb_last_bgsave_status', u'ok'],
    [u'rdb_last_bgsave_time_sec', u'-1'],
    [u'rdb_current_bgsave_time_sec', u'-1'], [u'rdb_last_cow_size', u'0'],
    [u'aof_enabled', u'0'], [u'aof_rewrite_in_progress', u'0'],
    [u'aof_rewrite_scheduled', u'0'], [u'aof_last_rewrite_time_sec', u'-1'],
    [u'aof_current_rewrite_time_sec', u'-1'],
    [u'aof_last_bgrewrite_status', u'ok'], [u'aof_last_write_status', u'ok'],
    [u'aof_last_cow_size', u'0'], [u'# Stats'],
    [u'total_connections_received',
     u'140'], [u'total_commands_processed', u'139'],
    [u'instantaneous_ops_per_sec', u'0'], [u'total_net_input_bytes', u'1960'],
    [u'total_net_output_bytes', u'385217'],
    [u'instantaneous_input_kbps', u'0.00'],
    [u'instantaneous_output_kbps', u'0.00'], [u'rejected_connections', u'0'],
    [u'sync_full', u'0'], [u'sync_partial_ok', u'0'],
    [u'sync_partial_err', u'0'], [u'expired_keys', u'0'],
    [u'expired_stale_perc',
     u'0.00'], [u'expired_time_cap_reached_count', u'0'],
    [u'evicted_keys', u'0'], [u'keyspace_hits', u'0'],
    [u'keyspace_misses', u'0'], [u'pubsub_channels', u'0'],
    [u'pubsub_patterns', u'0'], [u'latest_fork_usec', u'0'],
    [u'migrate_cached_sockets', u'0'], [u'slave_expires_tracked_keys', u'0'],
    [u'active_defrag_hits', u'0'], [u'active_defrag_misses', u'0'],
    [u'active_defrag_key_hits', u'0'], [u'active_defrag_key_misses', u'0'],
    [u'# Replication'], [u'role', u'master'], [u'connected_slaves', u'0'],
    [u'master_replid', u'fc24a4f675674698bde072eccf4cc8dc06ecb603'],
    [u'master_replid2', u'0000000000000000000000000000000000000000'],
    [u'master_repl_offset', u'0'], [u'second_repl_offset', u'-1'],
    [u'repl_backlog_active', u'0'], [u'repl_backlog_size', u'1048576'],
    [u'repl_backlog_first_byte_offset', u'0'], [u'repl_backlog_histlen', u'0'],
    [u'# CPU'], [u'used_cpu_sys', u'16.29'], [u'used_cpu_user', u'6.27'],
    [u'used_cpu_sys_children', u'0.00'], [u'used_cpu_user_children', u'0.00'],
    [u'# Cluster'], [u'cluster_enabled', u'0'], [u'# Keyspace'],
    [u'db0', u'keys=5,expires=0,avg_ttl=0']
]

discovery = {
    '': [(u'MY_FIRST_REDIS', {}), (u'MY_SECOND_REDIS', {})],
    'clients': [(u'MY_FIRST_REDIS', {}), (u'MY_SECOND_REDIS', {})],
    'persistence': [(u'MY_FIRST_REDIS', {}), (u'MY_SECOND_REDIS', {})]
}

checks = {
    '': [
        (
            u'MY_FIRST_REDIS', {}, [
                (0, u'Mode: Standalone', []),
                (
                    0, 'Up since Fri Dec  6 09:44:53 2019, uptime: 2:51:07', [
                        ('uptime', 10267, None, None, None, None)
                    ]
                ), (0, u'Version: 4.0.9', []),
                (0, u'GCC compiler version: 7.4.0', []), (0, 'PID: 1064', []),
                (0, u'IP: 127.0.0.1', []), (0, u'Port: 6380', [])
            ]
        ),
        (
            u'MY_SECOND_REDIS', {}, [
                (0, u'Mode: Standalone', []),
                (
                    0, 'Up since Fri Dec  6 09:44:54 2019, uptime: 2:51:06', [
                        ('uptime', 10266, None, None, None, None)
                    ]
                ), (0, u'Version: 4.0.9', []),
                (0, u'GCC compiler version: 7.4.0', []), (0, 'PID: 1320', []),
                (0, u'IP: 127.0.0.1', []), (0, u'Port: 6379', [])
            ]
        )
    ],
    'clients': [
        (
            u'MY_FIRST_REDIS', {}, [
                (
                    0, 'Number of client connections: 1', [
                        ('redis_clients_connected', 1, None, None, None, None)
                    ]
                ),
                (
                    0, 'Longest output list: 0', [
                        ('redis_clients_output', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Biggest input buffer: 0', [
                        ('redis_clients_input', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of clients pending on a blocking call: 0', [
                        ('redis_clients_blocked', 0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'MY_SECOND_REDIS', {}, [
                (
                    0, 'Number of client connections: 1', [
                        ('redis_clients_connected', 1, None, None, None, None)
                    ]
                ),
                (
                    0, 'Longest output list: 0', [
                        ('redis_clients_output', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Biggest input buffer: 0', [
                        ('redis_clients_input', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of clients pending on a blocking call: 0', [
                        ('redis_clients_blocked', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'persistence': [
        (
            u'MY_FIRST_REDIS', {
                'rdb_last_bgsave': 1,
                'aof_last_rewrite': 1
            }, [
                (0, 'Last RDB save operation: successful', []),
                (0, 'Last AOF rewrite operation: successful', []),
                (0, 'Last successful RDB save: 2019-12-06 08:45:57', []),
                (
                    0, 'Number of changes since last dump: 0', [
                        ('redis_rdb_changes', 0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'MY_SECOND_REDIS', {
                'rdb_last_bgsave': 1,
                'aof_last_rewrite': 1
            }, [
                (0, 'Last RDB save operation: successful', []),
                (0, 'Last AOF rewrite operation: successful', []),
                (0, 'Last successful RDB save: 2019-12-06 08:45:58', []),
                (
                    0, 'Number of changes since last dump: 0', [
                        ('redis_rdb_changes', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
