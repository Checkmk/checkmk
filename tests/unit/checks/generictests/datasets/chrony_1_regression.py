# -*- encoding: utf-8
# yapf: disable


checkname = 'chrony'


info = [[u'Reference', u'ID', u':', u'0.0.0.0', u'()'],
        [u'Stratum', u':', u'0'],
        [u'Ref', u'time', u'(UTC)', u':', u'Thu', u'Jan', u'1', u'00:00:00', u'1970'],
        [u'System',
         u'time',
         u':',
         u'0.000000062',
         u'seconds',
         u'slow',
         u'of',
         u'NTP',
         u'time'],
        [u'Last', u'offset', u':', u'+0.000000000', u'seconds'],
        [u'RMS', u'offset', u':', u'0.000000000', u'seconds'],
        [u'Frequency', u':', u'12.616', u'ppm', u'slow'],
        [u'Residual', u'freq', u':', u'+0.000', u'ppm'],
        [u'Skew', u':', u'0.000', u'ppm'],
        [u'Root', u'delay', u':', u'0.000000', u'seconds'],
        [u'Root', u'dispersion', u':', u'0.000000', u'seconds'],
        [u'Update', u'interval', u':', u'0.0', u'seconds'],
        [u'Leap', u'status', u':', u'Not', u'synchronised']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {'alert_delay': (300, 3600), 'ntp_levels': (10, 200.0, 500.0)},
                [(1, u'NTP servers unreachable. Reference ID: 0.0.0.0 ()', [])])]}