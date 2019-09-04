# -*- encoding: utf-8
# yapf: disable


checkname = 'jenkins_nodes'


info = [[u'[{"displayName": "master", "description": "the master Jenkins node", "temporarilyOffline": false, "monitorData": {}, "numExecutors": 0, "idle": true, "offlineCause": null, "offline": false, "_class": "hudson.model.Hudson$MasterComputer", "jnlpAgent": false}, {"displayName": "BuildNode1", "description": "", "temporarilyOffline": false, "monitorData": {}, "numExecutors": 20, "idle": false, "offlineCause": null, "offline": false, "_class": "hudson.slaves.SlaveComputer", "jnlpAgent": false}, {"displayName": "BuildNode2", "description": "", "temporarilyOffline": false, "monitorData": {}, "numExecutors": 10, "idle": true, "offlineCause": {"_class": "hudson.slaves.OfflineCause$LaunchFailed"}, "offline": true, "_class": "hudson.slaves.SlaveComputer", "jnlpAgent": false}, {"displayName": "Windows", "description": "Name: VM01", "temporarilyOffline": false, "monitorData": {}, "numExecutors": 1, "idle": true, "offlineCause": null, "offline": true, "_class": "hudson.slaves.SlaveComputer", "jnlpAgent": true}, {"displayName": "Windows", "description": "vM", "temporarilyOffline": false, "monitorData": {}, "numExecutors": 1, "idle": true, "offlineCause": null, "offline": false, "_class": "hudson.slaves.SlaveComputer", "jnlpAgent": true}]']]


discovery = {'': [(u'BuildNode1', {}),
                  (u'BuildNode2', {}),
                  (u'Windows', {}),
                  (u'master', {})]}


checks = {'': [(u'BuildNode1',
                {'jenkins_offline': 2},
                [(0, u'Description: ', []),
                 (0, 'JNLPAgent: False', []),
                 (0, 'Idle: False', []),
                 (0,
                  'Number of executers: 20',
                  [('jenkins_numexecutors', 20, None, None, None, None)]),
                 (0, 'Offline: False', [])]),
               (u'BuildNode2',
                {'jenkins_offline': 2},
                [(0, u'Description: ', []),
                 (0, 'JNLPAgent: False', []),
                 (0, 'Idle: True', []),
                 (0,
                  'Number of executers: 10',
                  [('jenkins_numexecutors', 10, None, None, None, None)]),
                 (2, 'Offline: True', [])]),
               (u'Windows',
                {'jenkins_offline': 2},
                [(0, u'Description: Name: VM01', []),
                 (0, 'JNLPAgent: True', []),
                 (0, 'Idle: True', []),
                 (0,
                  'Number of executers: 1',
                  [('jenkins_numexecutors', 1, None, None, None, None)]),
                 (2, 'Offline: True', []),
                 (0, u'Description: vM', []),
                 (0, 'JNLPAgent: True', []),
                 (0, 'Idle: True', []),
                 (0,
                  'Number of executers: 1',
                  [('jenkins_numexecutors', 1, None, None, None, None)]),
                 (0, 'Offline: False', [])]),
               (u'master',
                {'jenkins_offline': 2},
                [(0, u'Description: the master Jenkins node', []),
                 (0, 'JNLPAgent: False', []),
                 (0, 'Idle: True', []),
                 (0,
                  'Number of executers: 0',
                  [('jenkins_numexecutors', 0, None, None, None, None)]),
                 (0, 'Offline: False', [])])]}