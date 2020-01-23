# -*- encoding: utf-8
# yapf: disable
checkname = 'megaraid_pdisks'

info = [
    ['Enclosure', 'Device', 'ID:', '10'], ['Slot', 'Number:', '0'],
    ['Device', 'Id:', '4'],
    ['Raw', 'Size:', '140014MB', '[0x11177330', 'Sectors]'],
    ['Firmware', 'state:', 'Unconfigured(good)'],
    ['Predictive', 'Failure', 'Count:', '10'],
    ['Inquiry', 'Data:', 'FUJITSU', 'MBB2147RC', '5204BS04P9104BV5'],
    ['Enclosure', 'Device', 'ID:', '11'], ['Slot', 'Number:', '1'],
    ['Device', 'Id:', '5'],
    ['Raw', 'Size:', '140014MB', '[0x11177330', 'Sectors]'],
    ['Firmware', 'state:', 'Unconfigured(good)'],
    ['Inquiry', 'Data:', 'FUJITSU', 'MBB2147RC', '5204BS04P9104BSC'],
    ['Enclosure', 'Device', 'ID:', '12'], ['Slot', 'Number:', '2'],
    ['Device', 'Id:', '6'],
    ['Raw', 'Size:', '140014MB', '[0x11177330', 'Sectors]'],
    ['Predictive', 'Failure', 'Count:', '19'],
    ['Firmware', 'state:', 'Failed'],
    ['Inquiry', 'Data:', 'FUJITSU', 'MBB2147RC', '5204BS04P9104BSC']
]

discovery = {'': [('e10/0', None), ('e11/1', None), ('e12/2', None)]}

checks = {
    '': [
        (
            'e10/0', {}, [
                (
                    1,
                    'Unconfigured(good) (FUJITSU MBB2147RC 5204BS04P9104BV5) (predictive fail count: 10)',
                    []
                )
            ]
        ),
        (
            'e11/1', {}, [
                (
                    0,
                    'Unconfigured(good) (FUJITSU MBB2147RC 5204BS04P9104BSC)',
                    []
                )
            ]
        ),
        (
            'e12/2', {}, [
                (
                    2,
                    'Failed (FUJITSU MBB2147RC 5204BS04P9104BSC) (predictive fail count: 19)',
                    []
                )
            ]
        )
    ]
}
