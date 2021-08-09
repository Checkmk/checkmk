# -*- encoding: utf-8
# yapf: disable


checkname = 'windows_tasks'


info = [[u'TaskName             ',
         u' Monitoring - Content Replication get failed'],
        [u'and outdated items'],
        [u'Last Run Time        ', u' 7/21/2020 6', u'30', u'02 AM'],
        [u'Next Run Time        ', u' 7/22/2020 6', u'30', u'00 AM'],
        [u'Last Result          ', u' 0'],
        [u'Scheduled Task State ', u' Enabled'],
        [u'TaskName             ',
         u' Monitoring - Content Replicaton status'],
        [u'reporting overall'],
        [u'Last Run Time        ', u' 7/21/2020 6', u'45', u'02 AM'],
        [u'Next Run Time        ', u' 7/22/2020 6', u'45', u'00 AM'],
        [u'Last Result          ', u' 0'],
        [u'Scheduled Task State ', u' Enabled'],
        [u'TaskName             ', u' Monitoring - Delete old IIS logs'],
        [u'Last Run Time        ', u' 7/20/2020 10', u'00', u'01 PM'],
        [u'Next Run Time        ', u' 7/21/2020 10', u'00', u'00 PM'],
        [u'Last Result          ', u' 0'],
        [u'Scheduled Task State ', u' Enabled'],
        ['TaskName             ', ' jherbel-task'],
        ['Last Run Time        ', ' 10/26/2020 4', '23', '10 AM'],
        ['Next Run Time        ', ' N/A'],
        ['Last Result          ', ' 0'],
        ['Scheduled Task State ', ' Disabled'],
        ['TaskName             ', ' task-unknown-exit-code'],
        ['Last Run Time        ', ' 10/26/2020 4', '23', '10 AM'],
        ['Next Run Time        ', ' N/A'],
        ['Last Result          ', ' -2147024630'],
        ['Scheduled Task State ', ' Enabled']]


discovery = {'': [(u'Monitoring - Content Replication get failed and outdated items', None),
                  (u'Monitoring - Content Replicaton status reporting overall', None),
                  (u'Monitoring - Delete old IIS logs', None),
                  ('task-unknown-exit-code', None)]}


checks = {'': [(u'Monitoring - Content Replication get failed and outdated items',
                {},
                [(0, 'The task exited successfully (0x00000000)', []),
                 (0,
                  u'Last run time: 7/21/2020 6:30:02 AM, Next run time: 7/22/2020 6:30:00 AM',
                  [])]),
               (u'Monitoring - Content Replicaton status reporting overall',
                {},
                [(0, 'The task exited successfully (0x00000000)', []),
                 (0,
                  u'Last run time: 7/21/2020 6:45:02 AM, Next run time: 7/22/2020 6:45:00 AM',
                  [])]),
               (u'Monitoring - Delete old IIS logs',
                {},
                [(0, 'The task exited successfully (0x00000000)', []),
                 (0,
                  u'Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM',
                  [])]),
               (
                   'Monitoring - Delete old IIS logs',
                   {
                       "exit_code_to_state": [{
                           "exit_code": "0x00000000",
                           "monitoring_state": 1,
                       }]
                   },
                   [
                       (
                           1,
                           'The task exited successfully (0x00000000)',
                       ),
                       (
                           0,
                           'Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM',
                       ),
                   ],
               ),
               (
                   'Monitoring - Delete old IIS logs',
                   {
                       "exit_code_to_state": [{
                           "exit_code": "0x00000000",
                           "monitoring_state": 1,
                           "info_text": "Something else",
                       }]
                   },
                   [
                       (
                           1,
                           'Something else (0x00000000)',
                       ),
                       (
                           0,
                           'Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM',
                       ),
                   ],
               ),
               (
                   'jherbel-task',
                   {},
                   [
                       (
                           0,
                           'The task exited successfully (0x00000000)',
                       ),
                       (
                           1,
                           'Task not enabled',
                       ),
                       (
                           0,
                           'Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A',
                       ),
                   ],
               ),
               (
                   'jherbel-task',
                   {"state_not_enabled": 3},
                   [
                       (
                           0,
                           'The task exited successfully (0x00000000)',
                       ),
                       (
                           3,
                           'Task not enabled',
                       ),
                       (
                           0,
                           'Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A',
                       ),
                   ],
               ),
               (
                   'task-unknown-exit-code',
                   {},
                   [
                       (
                           2,
                           'Got exit code 0x8007010a',
                       ),
                       (
                           0,
                           'Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A',
                       ),
                   ],
               ),
               (
                   'task-unknown-exit-code',
                   {
                       "exit_code_to_state": [{
                           "exit_code": "0x8007010a",
                           "monitoring_state": 0,
                       }]
                   },
                   [
                       (
                           0,
                           'Got exit code 0x8007010a',
                       ),
                       (
                           0,
                           'Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A',
                       ),
                   ],
               ),
               (
                   'task-unknown-exit-code',
                   {
                       "exit_code_to_state": [{
                           "exit_code": "0x8007010a",
                           "monitoring_state": 0,
                           "info_text": "Give me your boots and your motorcycle!",
                       }]
                   },
                   [
                       (
                           0,
                           'Give me your boots and your motorcycle! (0x8007010a)',
                       ),
                       (
                           0,
                           'Last run time: 10/26/2020 4:23:10 AM, Next run time: N/A',
                       ),
                   ],
               ),
               ],
          }
