# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore


checkname = 'timesyncd'

info = [[u'Server:', u'(null)', u'(ntp.ubuntu.com)'],
        [
            u'Poll', u'interval:', u'0', u'(min:', u'32s;', u'max', u'34min',
            u'8s)'
        ], [u'Packet', u'count:', u'0'], [u'[[[1569922392.37]]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {
        'alert_delay': (300, 3600),
        'last_synchronised': (3600, 7200),
        'quality_levels': (200, 500),
        'stratum_level': 9
    }, [(0, 'Found no time server', []), (0, 'Just started monitoring', [])])]
}
