# yapf: disable


checkname = 'netapp_api_vs_status'


info = [['kermit1_ng-mc', 'running'], ['bill_vm', 'stopped']]


discovery = {'': [('bill_vm', {}), ('kermit1_ng-mc', {})]}


checks = {'': [('bill_vm', {}, [(2, 'State: stopped', [])]),
               ('kermit1_ng-mc', {}, [(0, 'State: running', [])])]}