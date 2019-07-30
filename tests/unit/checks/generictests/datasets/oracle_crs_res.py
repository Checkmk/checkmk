# -*- encoding: utf-8
# yapf: disable


checkname = 'oracle_crs_res'


info = [['ezszds8c', 'NAME=ora.DG_CLUSTER.dg'],
        ['ezszds8c', 'TYPE=ora.diskgroup.type'],
        ['ezszds8c', 'STATE=ONLINE on ezszds8c'],
        ['ezszds8c', 'TARGET=ONLINE'],
]


discovery = {'': [('ora.DG_CLUSTER.dg', None)]}


checks = {'': [('ora.DG_CLUSTER.dg', {}, [(0, 'on ezszds8c: online', [])])]}
