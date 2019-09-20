# -*- encoding: utf-8
# yapf: disable


checkname = 'oracle_crs_res'


info = [['oracle_host', 'NAME=ora.DG_CLUSTER.dg'],
        ['oracle_host', 'TYPE=ora.diskgroup.type'],
        ['oracle_host', 'STATE=ONLINE on oracle_host'],
        ['oracle_host', 'TARGET=ONLINE'],
]


discovery = {'': [('ora.DG_CLUSTER.dg', None)]}


checks = {'': [('ora.DG_CLUSTER.dg', {}, [(0, 'on oracle_host: online', [])])]}
