# -*- encoding: utf-8
# yapf: disable


checkname = u'oracle_crs_res'


info = [[u'NAME=ora.ARCH.dg'],
        [u'TYPE=ora.diskgroup.type'],
        [u'STATE=ONLINE'],
        [u'TARGET=ONLINE'],
        [u'ENABLED=1'],
        [u'NAME=ora.DATA.dg'],
        [u'TYPE=ora.diskgroup.type'],
        [u'STATE=ONLINE'],
        [u'TARGET=ONLINE'],
        [u'ENABLED=1']]


discovery = {'': [(u'ora.ARCH.dg', None), (u'ora.DATA.dg', None)]}


checks = {'': [(u'ora.ARCH.dg', {}, [(0, u'online', [])]),
               (u'ora.DATA.dg', {}, [(0, u'online', [])])]}