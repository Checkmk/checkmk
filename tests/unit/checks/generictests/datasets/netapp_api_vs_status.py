# yapf: disable


checkname = 'netapp_api_vs_status'


info = [['kermit1_ng-mc', 'running'], ['bill_vm', 'stopped']]


discovery = {'': [('bill_vm', None), ('kermit1_ng-mc', None)]}


checks = {'': [('bill_vm', {}, [(2, 'State is stopped', [])]),
               ('kermit1_ng-mc', {}, [(0, 'State is running', [])])]}