# yapf: disable


checkname = 'splunk_health'


info = [[u'Overall_state', u'green'],
        [u'File_monitor_input', u'green'],
        [u'File_monitor_input', u'Tailreader-0', u'green'],
        [u'File_monitor_input', u'Batchreader-0', u'green'],
        [u'Index_processor', u'green'],
        [u'Index_processor', u'Index_optimization', u'green'],
        [u'Index_processor', u'Buckets', u'green'],
        [u'Index_processor', u'Disk_space', u'green']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'green': 0, 'red': 2, 'yellow': 1},
                [(0, u'Overall state: green', []),
                 (0, u'File monitor input: green', []),
                 (0, u'Index processor: green', []),
                 (0, u'\nBatchreader-0 - State: green\nTailreader-0 - State: green\nBuckets - State: green\nDisk space - State: green\nIndex optimization - State: green\n',
                  [])])]}
