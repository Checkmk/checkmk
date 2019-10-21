# -*- encoding: utf-8
# yapf: disable


checkname = 'chrony'


info = [[u'Reference', u'ID', u':', u'55DCBEF6', u'(ernie.gerger-net.de)'],
        [u'Stratum', u':', u'11'],
        [u'Ref',
         u'time',
         u'(UTC)',
         u':',
         u'Tue',
         u'Jul',
         u'09',
         u'08:01:06',
         u'2019'],
        [u'System',
         u'time',
         u':',
         u'0.000275117',
         u'seconds',
         u'slow',
         u'of',
         u'NTP',
         u'time'],
        [u'Last', u'offset', u':', u'-0.000442775', u'seconds'],
        [u'RMS', u'offset', u':', u'0.000999328', u'seconds'],
        [u'Frequency', u':', u'2.054', u'ppm', u'fast'],
        [u'Residual', u'freq', u':', u'-0.004', u'ppm'],
        [u'Skew', u':', u'0.182', u'ppm'],
        [u'Root', u'delay', u':', u'0.023675382', u'seconds'],
        [u'Root', u'dispersion', u':', u'0.001886752', u'seconds'],
        [u'Update', u'interval', u':', u'1042.2', u'seconds'],
        [u'Leap', u'status', u':', u'Normal']]


extra_sections = {'': [[]]}


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'alert_delay': (300, 3600), 'ntp_levels': (10, 200.0, 500.0)},
                [(2, 'Stratum: 11 (warn/crit at 10/10)', []),
                 (0,
                  'Offset: 0.2751 ms',
                  [('offset', 0.275117, 200.0, 500.0, None, None)]),
                 (0, u'Reference ID: 55DCBEF6 (ernie.gerger-net.de)', [])])]}
