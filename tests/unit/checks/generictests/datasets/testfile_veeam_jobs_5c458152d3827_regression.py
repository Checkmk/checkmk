# -*- encoding: utf-8
# yapf: disable


checkname = u'veeam_jobs'


info = [[u'VMware_Server',
         u'Backup',
         u'Stopped',
         u'Success',
         u'21.01.2019 00:10:22',
         u'21.01.2019 00:29:12'],
        [u'Lehrer_Rechner',
         u'Backup',
         u'Stopped',
         u'Success',
         u'23.07.2018 13:08:37',
         u'23.07.2018 13:27:44'],
        [u'Windows_Admin_PC',
         u'Backup',
         u'Stopped',
         u'Success',
         u'20.01.2019 22:00:06',
         u'20.01.2019 22:02:42'],
        [u'Lehrer Rechner']]


discovery = {'': [(u'Lehrer Rechner', None),
                  (u'Lehrer_Rechner', None),
                  (u'VMware_Server', None),
                  (u'Windows_Admin_PC', None)]}


checks = {'': [(u'Lehrer Rechner', {}, [(3, 'No such job found', [])]),
               (u'Lehrer_Rechner',
                {},
                [(0,
                  u'Result: Success, Backup, Stopped, 23.07.2018 13:08:37, 23.07.2018 13:27:44',
                  [])]),
               (u'VMware_Server',
                {},
                [(0,
                  u'Result: Success, Backup, Stopped, 21.01.2019 00:10:22, 21.01.2019 00:29:12',
                  [])]),
               (u'Windows_Admin_PC',
                {},
                [(0,
                  u'Result: Success, Backup, Stopped, 20.01.2019 22:00:06, 20.01.2019 22:02:42',
                  [])])]}