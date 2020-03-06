# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'scaleio_devices'

info = [
    [u'DEVICE', u'Foo:'], [u'ID', u'Foo'], [u'SDS_ID', u'123'],
    [u'STORAGE_POOL_ID', u'abc'], [u'STATE', u'DEVICE_NORMAL'],
    [u'ERR_STATE', u'NO_ERROR'], [u'DEVICE', u'Bar:'], [u'ID', u'Bar'],
    [u'SDS_ID', u'123'], [u'STORAGE_POOL_ID', u'def'],
    [u'STATE', u'DEVICE_NORMAL'], [u'ERR_STATE', u'ERROR'],
    [u'DEVICE', u'Baz:'], [u'ID', u'Baz'], [u'SDS_ID', u'456'],
    [u'STORAGE_POOL_ID', u'xyz'], [u'STATE', u'DEVICE_NORMAL'],
    [u'ERR_STATE', u'NO_ERROR']
]

discovery = {'': [(u'123', {}), (u'456', {})]}

checks = {
    '': [
        (
            u'123', {}, [
                (2, u'2 devices, 1 errors (Bar)', []),
                (
                    0,
                    u'\nDevice Bar: Error: device normal, State: error (ID: Bar, Storage pool ID: def)',
                    []
                )
            ]
        ), (u'456', {}, [(0, '1 devices, no errors', [])])
    ]
}
