# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore
checkname = 'netapp_api_systemtime'

info = [['FAS8020-2', '1498108660', '1498108660']]

discovery = {'': [('FAS8020-2', {})]}

checks = {
    '': [
        (
            'FAS8020-2', {}, [
                (
                    0,
                    'System time: 2017-06-22 07:17:40',
                    []
                ),
                (
                    0,
                    'Time difference: 0.00 s',
                    [('time_difference', 0, None, None, None, None)]
                ),
            ]
        )
    ]
}
