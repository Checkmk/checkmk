# -*- encoding: utf-8
# yapf: disable
checkname = 'ewon'

info = []


discovery = {
    '': [
        ('eWON Status', {'device': None}),
    ],
}


checks = {
    '': [
        ('eWON Status', {'device': None}, [
            (1, 'This device requires configuration. Please pick the device type.', []),
        ]),
    ],
}
