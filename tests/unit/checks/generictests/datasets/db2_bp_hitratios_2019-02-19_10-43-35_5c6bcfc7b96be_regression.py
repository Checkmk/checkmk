# -*- encoding: utf-8
# yapf: disable


checkname = u'db2_bp_hitratios'


info = [[u'[[[serv0:ABC]]]'],
        [u'node', u'0', u'foo1.bar2.baz3', u'0'],
        [u'BP_NAME',
         u'TOTAL_HIT_RATIO_PERCENT',
         u'DATA_HIT_RATIO_PERCENT',
         u'INDEX_HIT_RATIO_PERCENT',
         u'XDA_HIT_RATIO_PERCENT'],
        [u'IBMDEFAULTBP', u'83.62', u'78.70', u'99.74', u'50.00'],
        [u'[[[serv1:XYZ]]]'],
        [u'node', u'0', u'foo1.bar2.baz3', u'0']]


discovery = {'': [(u'serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP', {})]}


checks = {'': [(u'serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP',
                {},
                [(0,
                  u'Total: 83.62%',
                  [(u'total_hitratio', 83.62, None, None, 0, 100)]),
                 (0,
                  u'Data: 78.70%',
                  [(u'data_hitratio', 78.7, None, None, 0, 100)]),
                 (0,
                  u'Index: 99.74%',
                  [(u'index_hitratio', 99.74, None, None, 0, 100)]),
                 (0, u'XDA: 50.00%', [(u'xda_hitratio', 50.0, None, None, 0, 100)])])]}