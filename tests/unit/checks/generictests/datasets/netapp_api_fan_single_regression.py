# -*- encoding: utf-8
# yapf: disable


checkname = 'netapp_api_fan'


info = [[u'cooling-element-list 0',
         u'cooling-element-number 1',
         u'rpm 3000',
         u'cooling-element-is-error false'],
        [u'cooling-element-list 0',
         u'cooling-element-number 2',
         u'rpm 3000',
         u'cooling-element-is-error true'],
        [u'cooling-element-list 0',
         u'cooling-element-number 3',
         u'rpm 3000',
         u'cooling-element-is-error false'],
        [u'cooling-element-list 0',
         u'cooling-element-number 4',
         u'rpm 3020',
         u'cooling-element-is-error false']]


discovery = {'': [(u'0/1', None), (u'0/2', None), (u'0/3', None), (u'0/4', None)],
             'summary': []}


checks = {'': [(u'0/1', {}, [(0, 'Operational state OK', [])]),
               (u'0/2', {}, [(2, u'Error in Fan 2', [])]),
               (u'0/3', {}, [(0, 'Operational state OK', [])]),
               (u'0/4', {}, [(0, 'Operational state OK', [])])]}


mock_host_conf_merged = {'': {'mode': 'single'}, 'summary': {'mode': 'single'}}