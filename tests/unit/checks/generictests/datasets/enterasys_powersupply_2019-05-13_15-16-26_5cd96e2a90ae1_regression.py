# -*- encoding: utf-8
# yapf: disable


checkname = u'enterasys_powersupply'


info = [[u'101', u'3', u'1', u'1'], [u'102', u'', u'', u'1']]


discovery = {'': [(u'101', {})]}


checks = {'': [(u'101',
                {'redundancy_ok_states': [1]},
                [(0, 'Status: working and redundant (ac-dc)', [])])]}
