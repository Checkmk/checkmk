#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'mongodb_collections'

info = [
    [
        u'{"admin":{"collstats":{"system.version":{"count":1,"totalIndexSize":16384,"ok":1.0,"avgObjSize":59,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664525},"ops":0}}],"storageSize":16384,"nindexes":1,"ns":"admin.system.version","indexSizes":{"_id_":16384},"size":59},"system.keys":{"count":2,"totalIndexSize":16384,"ok":1.0,"avgObjSize":85,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664524},"ops":0}}],"storageSize":16384,"nindexes":1,"ns":"admin.system.keys","indexSizes":{"_id_":16384},"size":170}},"collections":["system.version","system.keys"]},"unshardedDB2":{"collstats":{"collections1":{"count":18000,"totalIndexSize":208896,"ok":1.0,"avgObjSize":34,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664538},"ops":0}}],"storageSize":344064,"nindexes":1,"ns":"unshardedDB2.collections1","indexSizes":{"_id_":208896},"size":612000},"collections2":{"count":3996,"totalIndexSize":86016,"ok":1.0,"avgObjSize":36,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664539},"ops":0}}],"storageSize":122880,"nindexes":1,"ns":"unshardedDB2.collections2","indexSizes":{"_id_":86016},"size":143856}},"collections":["collections1","collections2"]},"unshardedDB1":{"collstats":{"collections1":{"count":6000,"totalIndexSize":282624,"ok":1.0,"avgObjSize":35,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664537},"ops":0}},{"key":{"x":1.0},"host":"mongo1:27017","name":"x_1","accesses":{"since":{"$date":1573216664537},"ops":0}}],"storageSize":151552,"nindexes":2,"ns":"unshardedDB1.collections1","indexSizes":{"_id_":98304,"x_1":184320},"size":210000}},"collections":["collections1"]},"local":{"collstats":{"startup_log":{"count":28,"totalIndexSize":36864,"ok":1.0,"avgObjSize":1470,"max":-1,"sleepMS":0,"sleepCount":0,"maxSize":10485760,"capped":true,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664533},"ops":0}}],"storageSize":40960,"nindexes":1,"ns":"local.startup_log","indexSizes":{"_id_":36864},"size":41160},"replset.minvalid":{"count":1,"totalIndexSize":16384,"ok":1.0,"avgObjSize":45,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664531},"ops":0}}],"storageSize":36864,"nindexes":1,"ns":"local.replset.minvalid","indexSizes":{"_id_":16384},"size":45},"oplog.rs":{"count":123910,"totalIndexSize":0,"ok":1.0,"avgObjSize":151,"max":-1,"sleepMS":0,"sleepCount":0,"maxSize":16830742272,"capped":true,"indexStats":[],"storageSize":5885952,"nindexes":0,"ns":"local.oplog.rs","indexSizes":{},"size":18768774},"system.replset":{"count":1,"totalIndexSize":16384,"ok":1.0,"avgObjSize":794,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664534},"ops":0}}],"storageSize":16384,"nindexes":1,"ns":"local.system.replset","indexSizes":{"_id_":16384},"size":794},"replset.oplogTruncateAfterPoint":{"count":1,"totalIndexSize":16384,"ok":1.0,"avgObjSize":71,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664532},"ops":0}}],"storageSize":36864,"nindexes":1,"ns":"local.replset.oplogTruncateAfterPoint","indexSizes":{"_id_":16384},"size":71},"replset.election":{"count":1,"totalIndexSize":16384,"ok":1.0,"avgObjSize":60,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664529},"ops":0}}],"storageSize":36864,"nindexes":1,"ns":"local.replset.election","indexSizes":{"_id_":16384},"size":60},"system.rollback.id":{"count":1,"totalIndexSize":16384,"ok":1.0,"avgObjSize":41,"capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664535},"ops":0}}],"storageSize":16384,"nindexes":1,"ns":"local.system.rollback.id","indexSizes":{"_id_":16384},"size":41}},"collections":["system.rollback.id","system.replset","startup_log","replset.minvalid","oplog.rs","replset.election","replset.oplogTruncateAfterPoint"]},"config":{"collstats":{"system.sessions":{"count":21,"totalIndexSize":73728,"ok":1.0,"avgObjSize":99,"capped":false,"indexStats":[{"key":{"lastUse":1},"host":"mongo1:27017","name":"lsidTTLIndex","accesses":{"since":{"$date":1573216664527},"ops":0}},{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664527},"ops":27}}],"storageSize":36864,"nindexes":2,"ns":"config.system.sessions","indexSizes":{"_id_":36864,"lsidTTLIndex":36864},"size":2079},"transactions":{"count":0,"totalIndexSize":4096,"ok":1.0,"ns":"config.transactions","capped":false,"indexStats":[{"key":{"_id":1},"host":"mongo1:27017","name":"_id_","accesses":{"since":{"$date":1573216664528},"ops":5}}],"nindexes":1,"storageSize":4096,"indexSizes":{"_id_":4096},"size":0}},"collections":["system.sessions","transactions"]}}'
    ]
]

discovery = {
    '': [
        (u'admin.system.keys', {}), (u'admin.system.version', {}),
        (u'config.system.sessions', {}), (u'config.transactions', {}),
        (u'local.oplog.rs', {}), (u'local.replset.election', {}),
        (u'local.replset.minvalid', {}),
        (u'local.replset.oplogTruncateAfterPoint', {}),
        (u'local.startup_log', {}), (u'local.system.replset', {}),
        (u'local.system.rollback.id', {}), (u'unshardedDB1.collections1', {}),
        (u'unshardedDB2.collections1', {}), (u'unshardedDB2.collections2', {})
    ]
}

checks = {
    '': [
        (
            u'admin.system.keys', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 170 B',
                    [('mongodb_collection_size', 170, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 16.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 16384, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 2 (Number of documents in collection)\n- Object Size: 85 B (Average object size)\n- Collection Size: 170 B (Uncompressed size in memory)\n- Storage Size: 16.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'admin.system.version', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 59 B',
                    [('mongodb_collection_size', 59, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 16.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 16384, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 1 (Number of documents in collection)\n- Object Size: 59 B (Average object size)\n- Collection Size: 59 B (Uncompressed size in memory)\n- Storage Size: 16.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'config.system.sessions', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 2.03 KiB', [
                        (
                            'mongodb_collection_size', 2079, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Allocated for document storage: 36.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 36864, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 72.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 73728, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 2', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 21 (Number of documents in collection)\n- Object Size: 99 B (Average object size)\n- Collection Size: 2.03 KiB (Uncompressed size in memory)\n- Storage Size: 36.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 72.0 KiB (Total size of all indexes)\n- Number of Indexes: 2\n-- Index '_id_' used 27 times since 2019-11-08 13:37:44\n-- Index 'lsidTTLIndex' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'config.transactions', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 0 B', [
                        ('mongodb_collection_size', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Allocated for document storage: 4.00 KiB', [
                        (
                            'mongodb_collection_storage_size', 4096, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 4.00 KiB', [
                        (
                            'mongodb_collection_total_index_size', 4096, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 0 (Number of documents in collection)\n- Object Size: n/a (Average object size)\n- Collection Size: 0 B (Uncompressed size in memory)\n- Storage Size: 4.00 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 4.00 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 5 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'local.oplog.rs', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 17.9 MiB', [
                        (
                            'mongodb_collection_size', 18768774, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Allocated for document storage: 5.61 MiB', [
                        (
                            'mongodb_collection_storage_size', 5885952, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 0 B', [
                        (
                            'mongodb_collection_total_index_size', 0, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 0', []),
                (
                    0,
                    '\nCollection\n- Document Count: 123910 (Number of documents in collection)\n- Object Size: 151 B (Average object size)\n- Collection Size: 17.9 MiB (Uncompressed size in memory)\n- Storage Size: 5.61 MiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 0 B (Total size of all indexes)\n- Number of Indexes: 0',
                    []
                )
            ]
        ),
        (
            u'local.replset.election', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 60 B',
                    [('mongodb_collection_size', 60, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 36.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 36864, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 1 (Number of documents in collection)\n- Object Size: 60 B (Average object size)\n- Collection Size: 60 B (Uncompressed size in memory)\n- Storage Size: 36.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'local.replset.minvalid', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 45 B',
                    [('mongodb_collection_size', 45, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 36.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 36864, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 1 (Number of documents in collection)\n- Object Size: 45 B (Average object size)\n- Collection Size: 45 B (Uncompressed size in memory)\n- Storage Size: 36.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'local.replset.oplogTruncateAfterPoint', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 71 B',
                    [('mongodb_collection_size', 71, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 36.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 36864, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 1 (Number of documents in collection)\n- Object Size: 71 B (Average object size)\n- Collection Size: 71 B (Uncompressed size in memory)\n- Storage Size: 36.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'local.startup_log', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 40.2 KiB', [
                        (
                            'mongodb_collection_size', 41160, None, None, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Allocated for document storage: 40.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 40960, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 36.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 36864, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 28 (Number of documents in collection)\n- Object Size: 1.44 KiB (Average object size)\n- Collection Size: 40.2 KiB (Uncompressed size in memory)\n- Storage Size: 40.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 36.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'local.system.replset', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 794 B',
                    [('mongodb_collection_size', 794, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 16.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 16384, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 1 (Number of documents in collection)\n- Object Size: 794 B (Average object size)\n- Collection Size: 794 B (Uncompressed size in memory)\n- Storage Size: 16.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'local.system.rollback.id', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 41 B',
                    [('mongodb_collection_size', 41, None, None, None, None)]
                ),
                (
                    0, 'Allocated for document storage: 16.0 KiB', [
                        (
                            'mongodb_collection_storage_size', 16384, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 16.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 16384, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 1 (Number of documents in collection)\n- Object Size: 41 B (Average object size)\n- Collection Size: 41 B (Uncompressed size in memory)\n- Storage Size: 16.0 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 16.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'unshardedDB1.collections1', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 205 KiB', [
                        (
                            'mongodb_collection_size', 210000, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Allocated for document storage: 148 KiB', [
                        (
                            'mongodb_collection_storage_size', 151552, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 276 KiB', [
                        (
                            'mongodb_collection_total_index_size', 282624,
                            None, None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 2', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 6000 (Number of documents in collection)\n- Object Size: 35 B (Average object size)\n- Collection Size: 205 KiB (Uncompressed size in memory)\n- Storage Size: 148 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 276 KiB (Total size of all indexes)\n- Number of Indexes: 2\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44\n-- Index 'x_1' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'unshardedDB2.collections1', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 598 KiB', [
                        (
                            'mongodb_collection_size', 612000, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Allocated for document storage: 336 KiB', [
                        (
                            'mongodb_collection_storage_size', 344064, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 204 KiB', [
                        (
                            'mongodb_collection_total_index_size', 208896,
                            None, None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 18000 (Number of documents in collection)\n- Object Size: 34 B (Average object size)\n- Collection Size: 598 KiB (Uncompressed size in memory)\n- Storage Size: 336 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 204 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        ),
        (
            u'unshardedDB2.collections2', {
                'levels_nindexes': (62, 65)
            }, [
                (
                    0, 'Uncompressed size in memory: 140 KiB', [
                        (
                            'mongodb_collection_size', 143856, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Allocated for document storage: 120 KiB', [
                        (
                            'mongodb_collection_storage_size', 122880, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, 'Total size of indexes: 84.0 KiB', [
                        (
                            'mongodb_collection_total_index_size', 86016, None,
                            None, None, None
                        )
                    ]
                ), (0, 'Number of indexes: 1', []),
                (
                    0,
                    u"\nCollection\n- Document Count: 3996 (Number of documents in collection)\n- Object Size: 36 B (Average object size)\n- Collection Size: 140 KiB (Uncompressed size in memory)\n- Storage Size: 120 KiB (Allocated for document storage)\n\nIndexes:\n- Total Index Size: 84.0 KiB (Total size of all indexes)\n- Number of Indexes: 1\n-- Index '_id_' used 0 times since 2019-11-08 13:37:44",
                    []
                )
            ]
        )
    ]
}
