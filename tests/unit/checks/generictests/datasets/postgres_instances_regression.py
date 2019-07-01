# -*- encoding: utf-8
# yapf: disable


checkname = 'postgres_instances'


info = [[u'[[[postgres]]]'],
        [u'30611',
         u'/usr/lib/postgresql/10/bin/postgres',
         u'-D',
         u'/var/lib/postgresql/10/main',
         u'-c',
         u'config_file=/etc/postgresql/10/main/postgresql.conf']]


discovery = {'': [(u'POSTGRES', {})]}


checks = {'': [(u'POSTGRES', {}, [(0, u'Status: running with PID 30611', [])])]}