#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'graylog_cluster_stats'

info = [
    [
        u'{"stream_rule_count": 7, "input_count_by_type": {"org.graylog.plugins.beats.Beats2Input": 1, "org.graylog2.inputs.syslog.tcp.SyslogTCPInput": 2, "org.graylog2.inputs.syslog.udp.SyslogUDPInput": 1}, "global_input_count": 4, "user_count": 3, "mongo": {"host_info": null, "database_stats": {"extent_free_list": null, "num_extents": 0, "db": "graylog", "storage_size": 1519616, "avg_obj_size": 323.20581808249113, "indexes": 106, "ns_size_mb": null, "index_size": 2899968, "objects": 7322, "collections": 47, "file_size": null, "data_file_version": null, "data_size": 2366513}, "server_status": null, "build_info": {"javascript_engine": "mozjs", "compiler_flags": null, "git_version": "5776e3cbf9e7afe86e6b29e22520ffb6766e95d4", "version": "4.0.12", "sys_info": "deprecated", "debug": false, "loader_flags": null, "version_array": [4, 0, 12, 0], "bits": 64, "max_bson_object_size": 16777216, "allocator": "tcmalloc"}, "servers": ["server1:27019", "server2:27018", "server3:27017"]}, "extractor_count_by_type": {}, "stream_count": 5, "output_count": 0, "stream_rule_count_by_stream": {"000000000000000000000001": 0, "000000000000000000000002": 0, "000000000000000000000003": 0, "9d9241564fb89f18c1f353e3": 6, "9d9223cb4fb89f18c1f33645": 1}, "extractor_count": 0, "ldap_stats": {"active_directory": true, "enabled": true, "role_mapping_count": 1, "role_count": 10}, "input_count": 4, "output_count_by_type": {}, "elasticsearch": {"status": "GREEN", "indices_stats": {"store_size": 1148947754, "index_count": 3, "id_cache_size": 0, "field_data_size": 636952}, "nodes_stats": {"data_only": -1, "master_data": -1, "total": 6, "master_only": -1, "client": -1}, "cluster_name": "graylog", "cluster_health": {"number_of_nodes": 6, "unassigned_shards": 0, "pending_tasks": 0, "timed_out": false, "active_primary_shards": 14, "pending_tasks_time_in_queue": [], "initializing_shards": 0, "active_shards": 20, "number_of_data_nodes": 6, "relocating_shards": 0}, "cluster_version": "6.8.2"}, "dashboard_count": 0, "alarm_stats": {"alert_count": 0, "alarmcallback_count_by_type": {}}}'
    ]
]

discovery = {
    '': [(None, {})],
    'mongodb': [(None, {})],
    'elastic': [(None, {})]
}

checks = {
    '': [
        (
            None, {}, [
                (
                    0, 'Number of inputs: 4', [
                        ('num_input', 4, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of outputs: 0', [
                        ('num_output', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of streams: 5', [
                        ('streams', 5, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of stream rules: 7', [
                        ('num_stream_rule', 7, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of extractors: 0', [
                        ('num_extractor', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of user: 3', [
                        ('num_user', 3, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'mongodb': [
        (
            None, {}, [
                (0, u'Name: Graylog', []), (0, u'Version: 4.0.12', []),
                (
                    0, 'Indices: 106', [
                        ('index_count', 106, None, None, None, None)
                    ]
                ),
                (
                    0, 'Allocated storage: 1.45 MiB', [
                        (
                            'mongodb_collection_storage_size', 1519616, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size: 2.77 MiB', [
                        ('indexes_size', 2899968, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total size of uncompressed data: 2.26 MiB', [
                        (
                            'mongodb_collection_size', 2366513, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Average document size: 323 B', [
                        (
                            'avg_doc_size', 323.20581808249113, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Number of extents: 0', [
                        ('num_extents', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of collections: 47', [
                        ('num_collections', 47, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of objects: 7322', [
                        ('num_objects', 7322, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'elastic': [
        (
            None, {
                'green': 0,
                'red': 2,
                'yellow': 1
            }, [
                (0, u'Name: Graylog', []), (0, u'Version: 6.8.2', []),
                (0, u'Status: Green', []),
                (
                    0, 'Nodes: 6', [
                        ('number_of_nodes', 6, None, None, None, None)
                    ]
                ),
                (
                    0, 'Data nodes: 6', [
                        ('number_of_data_nodes', 6, None, None, None, None)
                    ]
                ),
                (
                    0, 'Active shards: 20', [
                        ('active_shards', 20, None, None, None, None)
                    ]
                ),
                (
                    0, 'Active primary shards: 14', [
                        ('active_primary_shards', 14, None, None, None, None)
                    ]
                ),
                (
                    0, 'Initializing shards: 0', [
                        ('initializing_shards', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Relocating shards: 0', [
                        ('relocating_shards', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Unassigned shards: 0', [
                        ('unassigned_shards', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Pending tasks: 0', [
                        ('number_of_pending_tasks', 0, None, None, None, None)
                    ]
                ), (0, 'Timed out: no', []),
                (
                    0, 'Index count: 3', [
                        ('index_count', 3, None, None, None, None)
                    ]
                ),
                (
                    0, 'Store size: 1.07 GiB', [
                        ('store_size', 1148947754, None, None, None, None)
                    ]
                ),
                (
                    0, 'ID cache size: 0 B', [
                        ('id_cache_size', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Field data size: 622 KiB', [
                        ('field_data_size', 636952, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
