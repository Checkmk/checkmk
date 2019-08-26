# -*- encoding: utf-8
# yapf: disable


checkname = 'jenkins_queue'


freeze_time = '2019-08-27T11:15:00'


info = [[u'[{"task": {"color": "blue_anime", "_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "name": "testbuild"}, "inQueueSince": 1566892922469, "why": "Build #475 is already in progress (ETA: 23 min)", "stuck": false, "_class": "hudson.model.Queue$BlockedItem", "buildableStartMilliseconds": 1566892928443, "id": 174702, "blocked": true}]']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Queue lenght: 1 Tasks',
                  [('queue', 1, None, None, None, None)]),
                 (0,
                  u'\nID: 174702, In queue since: 192 m (2019-08-27 10:02:02), Stuck: False, Blocked: True, Why kept: Build #475 is already in progress (ETA: 23 min)',
                  [])])]}