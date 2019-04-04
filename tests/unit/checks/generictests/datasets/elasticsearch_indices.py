# -*- encoding: utf-8
# yapf: disable


checkname = 'elasticsearch_indices'


info = [[u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'filebeat-6.5.4', u'5', u'1'],
        [u'filebeat-6.5.4', u'500', u'1'],
        [u'filebeat-6.5.4', u'1100', u'1'],
        [u'filebeat-6.5.4', u'1', u'1'],
        [u'myindex-1234', u'213123', u'123121'],
        [u'myindex-1234', u'233443', u'314324'],
        [u'myindex-1234', u'242344', u'422322']]


discovery = {'': [(u'filebeat-6.5.4', {}), (u'myindex-1234', {})]}


checks = {'': [(u'filebeat-6.5.4',
                {},
                [(0,
                  'Total count: 1613 docs',
                  [('elasticsearch_count', 1613, None, None, None, None)]),
                 (0,
                  'Average count: 0 docs per Minute',
                  [('elasticsearch_count_rate', 0.0, None, None, None, None)]),
                 (0,
                  'Total size: 11.00 B',
                  [('elasticsearch_size', 11, None, None, None, None)]),
                 (0,
                  'Average size: 0.00 B  per Minute',
                  [('elasticsearch_size_rate', 0.0, None, None, None, None)])]),
               (u'myindex-1234',
                {},
                [(0,
                  'Total count: 688910 docs',
                  [('elasticsearch_count', 688910, None, None, None, None)]),
                 (0,
                  'Average count: 0 docs per Minute',
                  [('elasticsearch_count_rate', 0.0, None, None, None, None)]),
                 (0,
                  'Total size: 839.62 kB',
                  [('elasticsearch_size', 859767, None, None, None, None)]),
                 (0,
                  'Average size: 0.00 B  per Minute',
                  [('elasticsearch_size_rate', 0.0, None, None, None, None)])])]}