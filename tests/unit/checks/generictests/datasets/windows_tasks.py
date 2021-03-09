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
        [u'Scheduled Task State ', u' Enabled']]


discovery = {'': [(u'Monitoring - Content Replication get failed and outdated items', None),
                  (u'Monitoring - Content Replicaton status reporting overall', None),
                  (u'Monitoring - Delete old IIS logs', None)]}


checks = {'': [(u'Monitoring - Content Replication get failed and outdated items',
                {},
                [(0, 'Service Status: operation completed successfully (0x0)', []),
                 (0,
                  u'Last run time: 7/21/2020 6:30:02 AM, Next run time: 7/22/2020 6:30:00 AM',
                  [])]),
               (u'Monitoring - Content Replicaton status reporting overall',
                {},
                [(0, 'Service Status: operation completed successfully (0x0)', []),
                 (0,
                  u'Last run time: 7/21/2020 6:45:02 AM, Next run time: 7/22/2020 6:45:00 AM',
                  [])]),
               (u'Monitoring - Delete old IIS logs',
                {},
                [(0, 'Service Status: operation completed successfully (0x0)', []),
                 (0,
                  u'Last run time: 7/20/2020 10:00:01 PM, Next run time: 7/21/2020 10:00:00 PM',
                  [])])]}
