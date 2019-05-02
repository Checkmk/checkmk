# -*- encoding: utf-8
# yapf: disable


checkname = 'splunk_license_usage'


info = [[u'license_usage'], [u'524288000', u'5895880']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'usage_bytes': (80.0, 90.0)},
                [(0, 'Quota: 500.00 MB', []),
                 (0,
                  'Slaves usage: 5.62 MB',
                  [('splunk_slave_usage_bytes',
                    5895880,
                    419430400.0,
                    471859200.0,
                    None,
                    None)])])]}