# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'qnap_fans'

info = [[u'1', u'1027 RPM'], [u'2', u'968 RPM']]

discovery = {'': [(u'1', {}), (u'2', {})]}

checks = {
    '': [
        (
            u'1', {
                'upper': (6000, 6500),
                'lower': (None, None)
            }, [(0, 'Speed: 1027 RPM', [])]
        ),
        (
            u'2', {
                'upper': (6000, 6500),
                'lower': (None, None)
            }, [(0, 'Speed: 968 RPM', [])]
        )
    ]
}
