# -*- encoding: utf-8
# yapf: disable


checkname = 'netstat'


info = [[u'tcp4', u'0', u'0', u'127.0.0.1.32832', u'127.0.0.1.32833', u'ESTABLISHED'],
        [u'tcp',
         u'0',
         u'0',
         u'172.22.182.179.45307',
         u'172.22.182.179.3624',
         u'ESTABLISHED']]


discovery = {'': []}

checks = {'': [("connections", {}, [(0, "Matching entries found: 2", [("connections", 2)]) ])]}
