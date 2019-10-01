# -*- encoding: utf-8
# yapf: disable


checkname = u'mknotifyd'


info = [[u'[EX]'], [u'Binary file (standard input) matches']]


parsed = {u'EX': {'connections': {}, 'queues': {}, 'spools': {}}}


discovery = {'': [(u'EX', {})], 'connection': []}


checks = {'': [(u'EX',
                {},
                [(2,
                  'The state file seems to be empty or corrupted. It is very likely that the spooler is not working properly',
                  [])])]}
