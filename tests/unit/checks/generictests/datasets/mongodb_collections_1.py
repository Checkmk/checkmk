# yapf: disable


checkname = 'mongodb_collections'


info = [[u'admin', u'system.version', u'avgObjSize', u'59'],
        [u'admin', u'system.version', u'totalIndexSize', u'16384'],
        [u'admin', u'system.version', u'storageSize', u'16384'],
        [u'admin', u'system.version', u'indexSizes', u"{u'_id_': 16384}"],
        [u'admin', u'system.version', u'size', u'59'],
        [u'local', u'startup_log', u'avgObjSize', u'1948'],
        [u'local', u'startup_log', u'indexSizes', u"{u'_id_': 36864}"],
        [u'local', u'startup_log', u'totalIndexSize', u'36864'],
        [u'local', u'startup_log', u'maxSize', u'10485760'],
        [u'local', u'startup_log', u'storageSize', u'36864'],
        [u'local', u'startup_log', u'size', u'5844'],
        [u'test', u'zips', u'avgObjSize', u'94'],
        [u'test', u'zips', u'totalIndexSize', u'315392'],
        [u'test', u'zips', u'storageSize', u'1462272'],
        [u'test', u'zips', u'indexSizes', u"{u'_id_': 315392}"],
        [u'test', u'zips', u'size', u'2774134'],
        [u'config', u'system.sessions', u'ns', u'config.system.sessions'],
        [u'config', u'system.sessions', u'ok', u'1.0'],
        [u'config', u'system.sessions', u'avgObjSize', u'99'],
        [u'config', u'system.sessions', u'totalIndexSize', u'49152'],
        [u'config', u'system.sessions', u'storageSize', u'24576'],
        [u'config',
         u'system.sessions',
         u'indexSizes',
         u"{u'_id_': 24576, u'lsidTTLIndex': 24576}"],
        [u'config', u'system.sessions', u'size', u'594']]


discovery = {'': [(u'admin system.version', {}),
                  (u'config system.sessions', {}),
                  (u'local startup_log', {}),
                  (u'test zips', {})]}


checks = {
    '': [
        (u'admin system.version', {}, [
            (0, 'Uncompressed size in memory: 59.00 B', []),
            (0, 'Allocated for document storage: 16.00 kB', []),
        ]),
        (u'config system.sessions', {}, [
            (0, 'Uncompressed size in memory: 594.00 B', []),
            (0, 'Allocated for document storage: 24.00 kB', []),
        ]),
        (u'local startup_log', {}, [
            (0, 'Uncompressed size in memory: 5.71 kB', []),
            (0, 'Allocated for document storage: 36.00 kB', []),
        ]),
        (u'test zips', {"levels_size": (1, 2), "levels_storagesize": (1, 2)}, [
            (2, 'Uncompressed size in memory: 2.65 MB (warn/crit at 1.00 MB/2.00 MB)', []),
            (1, 'Allocated for document storage: 1.39 MB (warn/crit at 1.00 MB/2.00 MB)', []),
        ]),
    ],
}
