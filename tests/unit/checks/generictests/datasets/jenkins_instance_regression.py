# -*- encoding: utf-8
# yapf: disable


checkname = 'jenkins_instance'


info = [[u'{"quietingDown": false, "nodeDescription": "the master Jenkins node", "numExecutors": 10, "mode": "NORMAL", "_class": "hudson.model.Hudson", "useSecurity": true}']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'mode': 'NORMAL'},
                [(0, 'Mode: Normal', []),
                 (0, 'Quieting Down: False', []),
                 (0, 'Security used: True', [])])]}