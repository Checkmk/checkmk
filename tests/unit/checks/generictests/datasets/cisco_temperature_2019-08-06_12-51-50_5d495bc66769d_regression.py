# -*- encoding: utf-8
# yapf: disable


checkname = u'cisco_temperature'


parsed = {'8': {u'Chassis 1': {'dev_state': (3, 'sensor defect'),
                               'raw_dev_state': u'1'}}}


discovery = {'': [(u'Chassis 1', {})], 'dom': []}


checks = {'': [(u'Chassis 1', {}, [(3, 'Status: sensor defect', [])])]}