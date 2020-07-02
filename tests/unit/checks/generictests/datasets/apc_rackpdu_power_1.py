# -*- encoding: utf-8
# yapf: disable


checkname = 'apc_rackpdu_power'


info = [[[u'luz0010x', u'0']],
        [[u'3']],
        [[u'0', u'1', u'1', u'0'], [u'0', u'1', u'2', u'0'], [u'0', u'1', u'3', u'0']]]


discovery = {'': [(u'Device luz0010x', {}),
                  (u'Phase 1', {}),
                  (u'Phase 2', {}),
                  (u'Phase 3', {})]}


checks = {'': [(u'Device luz0010x',
                {},
                [(0, 'Power: 0.0 W', [('power', 0.0, None, None, None, None)])]),
               (u'Phase 1',
                {},
                [(0, 'Current: 0.0 A', [('current', 0.0, None, None, None, None)]),
                 (0, 'load normal', [])]),
               (u'Phase 2',
                {},
                [(0, 'Current: 0.0 A', [('current', 0.0, None, None, None, None)]),
                 (0, 'load normal', [])]),
               (u'Phase 3',
                {},
                [(0, 'Current: 0.0 A', [('current', 0.0, None, None, None, None)]),
                 (0, 'load normal', [])])]}