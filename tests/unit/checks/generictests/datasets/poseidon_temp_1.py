# yapf: disable
checkname = 'poseidon_temp'

info = [[u'Bezeichnung Sensor 1', u'1', u'16.8 C']]

discovery = {'': [(u'Bezeichnung Sensor 1', {})]}

checks = {
    '': [(u'Bezeichnung Sensor 1', {}, [
        (0, u'Sensor Bezeichnung Sensor 1, State normal', []),
        (0, u'16.8 \xb0C', [('temp', 16.8, None, None, None, None)]),
    ])]
}
