# -*- encoding: utf-8
# yapf: disable


checkname = 'jenkins_queue'


freeze_time = '2019-08-27T11:15:00'


info = [[u'[{"task": {"color": "blue_anime", "_class": "org.jenkinsci.plugins.workflow.job.WorkflowJob", "name": "testbuild"}, "inQueueSince": 1566892922469, "why": "Build #475 is already in progress (ETA: 23 min)", "stuck": false, "_class": "hudson.model.Queue$BlockedItem", "buildableStartMilliseconds": 1566892928443, "id": 174702, "blocked": true, "pending": false}]']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'blocked': 0,
                 'in_queue_since': (3600, 7200),
                 'jenkins_stuck_tasks': (1, 2),
                 'pending': 0,
                 'stuck': 2},
                [(0,
                  'Queue length: 1 Tasks',
                  [('queue', 1, None, None, None, None)]),
                 (0, 'Stuck: 0', [('jenkins_stuck_tasks', 0, 1.0, 2.0, None, None)]),
                 (0,
                  'Blocked: 1',
                  [('jenkins_blocked_tasks', 1, None, None, None, None)]),
                 (0,
                  'Pending: 0',
                  [('jenkins_pending_tasks', 0, None, None, None, None)]),
                 (2, 'See long output for further information', []),
                 (0,
                  u'\nID: 174702, Stuck: no, Blocked: yes, Pending: no, In queue since: 192 m (2019-08-27 10:02:02) (warn/crit at 60 m/120 m)(!!), Why kept: Build #475 is already in progress (ETA: 23 min)',
                  [])])]}