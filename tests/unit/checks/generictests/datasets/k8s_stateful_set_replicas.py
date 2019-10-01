# -*- encoding: utf-8
# yapf: disable


checkname = 'k8s_stateful_set_replicas'


parsed = {u'ready_replicas': 2, u'replicas': 2, u'strategy_type': 'RollingUpdate'}


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Ready: 2/2',
                  [('ready_replicas', 2, None, None, None, None),
                   ('total_replicas', 2, None, None, None, None)]),
                 (0, 'Strategy: RollingUpdate', [])])]}
