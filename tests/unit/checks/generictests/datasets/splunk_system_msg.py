# -*- encoding: utf-8
# yapf: disable


checkname = 'splunk_system_msg'


info = [[u'manifest_error',
         u'warn',
         u'klappclub',
         u'2019-05-16T08:32:33+02:00',
         u'File',
         u'Integrity',
         u'checks',
         u'found',
         u'1',
         u'files',
         u'that',
         u'did',
         u'not',
         u'match',
         u'the',
         u'system-provided',
         u'manifest.',
         u'Review',
         u'the',
         u'list',
         u'of',
         u'problems',
         u'reported',
         u'by',
         u'the',
         u'InstalledFileHashChecker',
         u'in',
         u'splunkd.log',
         u'[[/app/search/integrity_check_of_installed_files?form.splunk_server=klappclub|File',
         u'Integrity',
         u'Check',
         u'View]]',
         u';',
         u'potentially',
         u'restore',
         u'files',
         u'from',
         u'installation',
         u'media,',
         u'change',
         u'practices',
         u'to',
         u'avoid',
         u'changing',
         u'files,',
         u'or',
         u'work',
         u'with',
         u'support',
         u'to',
         u'identify',
         u'the',
         u'problem.']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(1,
                  u'Worst severity: warn, Last message from server: klappclub, Creation time: 2019-05-16T08:32:33+02:00\n2019-05-16T08:32:33+02:00 - klappclub - Integrity checks found 1 files that did not match the system-provided manifest. Review the list of problems reported by the InstalledFileHashChecker in splunkd.log [[/app/search/integrity_check_of_installed_files?form.splunk_server=klappclub|File Integrity Check View]] ; potentially restore files from installation media, change practices to avoid changing files, or work with support to identify the problem.\n',
                  [])])]}