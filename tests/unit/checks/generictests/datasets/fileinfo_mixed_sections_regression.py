# -*- encoding: utf-8
# yapf: disable


checkname = 'fileinfo'


info = [[u'1611065402'],
        [u'[[[header]]]'],
        [u'name', u'status', u'size', u'time'],
        [u'[[[content]]]'],
        [u'/root/anaconda-ks.cfg', u'ok', u'6006', u'1582708355'],
        [u'1611065406'],
        [u'/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc',
         u'11072435',
         u'1609376403'],
        [u'/SAP HANA PHT 00/backup.log.3.gz', u'425', u'1609773942'],
        [u'/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc',
         u'1923',
         u'1607339609'],
        [u'/SAP HANA PHT 00/stderr2', u'793', u'1611064087']]


discovery = {'': [('/SAP HANA PHT 00/backup.log.3.gz', {}),
                  ('/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc', {}),
                  ('/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc', {}),
                  ('/SAP HANA PHT 00/stderr2', {}),
                  ('/root/anaconda-ks.cfg', {})],
             'groups': []}


checks = {'': [('/SAP HANA PHT 00/backup.log.3.gz',
                {},
                [(0, 'Size: 425 B', [('size', 425, None, None, None, None)]),
                 (0, 'Age: 15 d', [('age', 1291460, None, None, None, None)])]),
               ('/SAP HANA PHT 00/daemon_wwfcsunil286s.dc.ege.ds.30000.336.trc',
                {},
                [(0, 'Size: 10.56 MB', [('size', 11072435, None, None, None, None)]),
                 (0, 'Age: 20 d', [('age', 1688999, None, None, None, None)])]),
               ('/SAP HANA PHT 00/daemon_wwfcsunil286s_065255__children.trc',
                {},
                [(0, 'Size: 1923 B', [('size', 1923, None, None, None, None)]),
                 (0, 'Age: 43 d', [('age', 3725793, None, None, None, None)])]),
               ('/SAP HANA PHT 00/stderr2',
                {},
                [(0, 'Size: 793 B', [('size', 793, None, None, None, None)]),
                 (0, 'Age: 21 m', [('age', 1315, None, None, None, None)])]),
               ('/root/anaconda-ks.cfg',
                {},
                [(0, 'Size: 6006 B', [('size', 6006, None, None, None, None)]),
                 (0, 'Age: 328 d', [('age', 28357047, None, None, None, None)])])]}