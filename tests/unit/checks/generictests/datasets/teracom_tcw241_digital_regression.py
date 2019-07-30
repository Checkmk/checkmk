# -*- encoding: utf-8
# yapf: disable


checkname = 'teracom_tcw241_digital'


info = [[[u'Tank_Status', u'NEA_Status', u'Digital Input 3', u'Digital Input 4']], [[u'1', u'1', u'1', u'1']]]


discovery = {'': [('4', {}),
                  ('3', {}),
                  ('2', {}),
                  ('1', {})]}


checks = {'': [('4', {}, [(0, '[Digital Input 4] is open', [])]),
               ('3', {}, [(0, '[Digital Input 3] is open', [])]),
               ('2', {}, [(0, '[NEA_Status] is open', [])]),
               ('1', {}, [(0, '[Tank_Status] is open', [])])]}