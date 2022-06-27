#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'huawei_wlc_aps'

info = [
    [
        ['8', '23', '66', '40', '1'], ['4', '0', '0', '255', '0'],
        ['8', '23', '1', '43', '0'], ['8', '23', '1', '38', '0'],
        ['8', '23', '1', '38', '0'], ['8', '23', '1', '39', '1'],
        ['8', '23', '1', '37', '1'], ['8', '23', '1', '38', '0']
    ],
    [
        ['to-ap-04', '1', '12', '1'], ['to-ap-04', '1', '1', '0'],
        ['to-simu', '', '87', '55'], ['to-simu', '', '93', '34'],
        ['huawei-test-ap-01', '1', '10', '0'],
        ['huawei-test-ap-01', '1', '7', '0'], ['to-ap-02', '1', '13', '0'],
        ['to-ap-02', '1', '1', '0'], ['to-ap-06', '1', '89', '0'],
        ['to-ap-06', '1', '1', '0'], ['to-ap-03', '1', '13', '2'],
        ['to-ap-03', '1', '1', '0'], ['to-ap-05', '1', '13', '0'],
        ['to-ap-05', '1', '1', '0'], ['to-ap-01', '1', '12', '0'],
        ['to-ap-01', '1', '1', '0']
    ]
]

discovery = {
    '': [],
    'status': [
        ('huawei-test-ap-01', {}), ('to-ap-01', {}), ('to-ap-02', {}),
        ('to-ap-03', {}), ('to-ap-04', {}), ('to-ap-05', {}), ('to-ap-06', {}),
        ('to-simu', {})
    ],
    'cpu': [
        ('huawei-test-ap-01', {}), ('to-ap-01', {}), ('to-ap-02', {}),
        ('to-ap-03', {}), ('to-ap-04', {}), ('to-ap-05', {}), ('to-ap-06', {}),
        ('to-simu', {})
    ],
    'mem': [
        ('huawei-test-ap-01', {}), ('to-ap-01', {}), ('to-ap-02', {}),
        ('to-ap-03', {}), ('to-ap-04', {}), ('to-ap-05', {}), ('to-ap-06', {}),
        ('to-simu', {})
    ],
    'temp': [
        ('huawei-test-ap-01', {}), ('to-ap-01', {}), ('to-ap-02', {}),
        ('to-ap-03', {}), ('to-ap-04', {}), ('to-ap-05', {}), ('to-ap-06', {}),
        ('to-simu', {})
    ]
}

checks = {
    'status': [
        (
            'huawei-test-ap-01', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 0', []),
                (
                    0, 'Users online [2,4GHz]: 0', [
                        ('24ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    0, 'Channel usage [2,4GHz]: 10.00%', [
                        (
                            'channel_utilization_24ghz', 10.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 7.00%', [
                        (
                            'channel_utilization_5ghz', 7.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-ap-01', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 0', []),
                (
                    0, 'Users online [2,4GHz]: 0', [
                        ('24ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    0, 'Channel usage [2,4GHz]: 12.00%', [
                        (
                            'channel_utilization_24ghz', 12.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 1.00%', [
                        (
                            'channel_utilization_5ghz', 1.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-ap-02', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 0', []),
                (
                    0, 'Users online [2,4GHz]: 0', [
                        ('24ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    0, 'Channel usage [2,4GHz]: 13.00%', [
                        (
                            'channel_utilization_24ghz', 13.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 1.00%', [
                        (
                            'channel_utilization_5ghz', 1.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-ap-03', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 1', []),
                (
                    0, 'Users online [2,4GHz]: 2', [
                        ('24ghz_clients', 2, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    0, 'Channel usage [2,4GHz]: 13.00%', [
                        (
                            'channel_utilization_24ghz', 13.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 1.00%', [
                        (
                            'channel_utilization_5ghz', 1.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-ap-04', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 1', []),
                (
                    0, 'Users online [2,4GHz]: 1', [
                        ('24ghz_clients', 1, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    0, 'Channel usage [2,4GHz]: 12.00%', [
                        (
                            'channel_utilization_24ghz', 12.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 1.00%', [
                        (
                            'channel_utilization_5ghz', 1.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-ap-05', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 1', []),
                (
                    0, 'Users online [2,4GHz]: 0', [
                        ('24ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    0, 'Channel usage [2,4GHz]: 13.00%', [
                        (
                            'channel_utilization_24ghz', 13.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 1.00%', [
                        (
                            'channel_utilization_5ghz', 1.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-ap-06', {
                'levels': (80.0, 90.0)
            }, [
                (0, 'Normal', []), (0, 'Connected users: 0', []),
                (
                    0, 'Users online [2,4GHz]: 0', [
                        ('24ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [2,4GHz]: up', []),
                (
                    1,
                    'Channel usage [2,4GHz]: 89.00% (warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'channel_utilization_24ghz', 89.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 0', [
                        ('5ghz_clients', 0, None, None, None, None)
                    ]
                ), (0, 'Radio state [5GHz]: up', []),
                (
                    0, 'Channel usage [5GHz]: 1.00%', [
                        (
                            'channel_utilization_5ghz', 1.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'to-simu', {
                'levels': (80.0, 90.0)
            }, [
                (2, 'Fault', []), (0, 'Connected users: 0', []),
                (
                    0, 'Users online [2,4GHz]: 55', [
                        ('24ghz_clients', 55, None, None, None, None)
                    ]
                ), (3, 'Radio state [2,4GHz]: not available', []),
                (
                    1,
                    'Channel usage [2,4GHz]: 87.00% (warn/crit at 80.00%/90.00%)',
                    [
                        (
                            'channel_utilization_24ghz', 87.0, 80.0, 90.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Users online [5GHz]: 34', [
                        ('5ghz_clients', 34, None, None, None, None)
                    ]
                ), (3, 'Radio state [5GHz]: not available', []),
                (
                    2,
                    'Channel usage [5GHz]: 93.00% (warn/crit at 80.00%/90.00%)', [
                        (
                            'channel_utilization_5ghz', 93.0, 80.0, 90.0, None,
                            None
                        )
                    ]
                )
            ]
        )
    ],
    'cpu': [
        (
            'huawei-test-ap-01', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 1.00%', [
                        ('cpu_percent', 1.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-01', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 1.00%', [
                        ('cpu_percent', 1.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-02', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 1.00%', [
                        ('cpu_percent', 1.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-03', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 1.00%', [
                        ('cpu_percent', 1.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-04', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 66.00%', [
                        ('cpu_percent', 66.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-05', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 1.00%', [
                        ('cpu_percent', 1.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-06', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 1.00%', [
                        ('cpu_percent', 1.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-simu', {
                'levels': (80.0, 90.0)
            },
            [(0, 'Usage: 0%', [('cpu_percent', 0.0, 80.0, 90.0, None, None)])]
        )
    ],
    'mem': [
        (
            'huawei-test-ap-01', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-01', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-02', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-03', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-04', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-05', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-ap-06', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 23.00%', [
                        ('mem_used_percent', 23.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        ),
        (
            'to-simu', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 0%', [
                        ('mem_used_percent', 0.0, 80.0, 90.0, None, None)
                    ]
                )
            ]
        )
    ],
    'temp': [
        (
            'huawei-test-ap-01', {}, [
                (0, '43.0 °C', [('temp', 43.0, None, None, None, None)])
            ]
        ),
        (
            'to-ap-01', {}, [
                (0, '38.0 °C', [('temp', 38.0, None, None, None, None)])
            ]
        ),
        (
            'to-ap-02', {}, [
                (0, '38.0 °C', [('temp', 38.0, None, None, None, None)])
            ]
        ),
        (
            'to-ap-03', {}, [
                (0, '39.0 °C', [('temp', 39.0, None, None, None, None)])
            ]
        ),
        (
            'to-ap-04', {}, [
                (0, '40.0 °C', [('temp', 40.0, None, None, None, None)])
            ]
        ),
        (
            'to-ap-05', {}, [
                (0, '37.0 °C', [('temp', 37.0, None, None, None, None)])
            ]
        ),
        (
            'to-ap-06', {}, [
                (0, '38.0 °C', [('temp', 38.0, None, None, None, None)])
            ]
        ), ('to-simu', {}, [(0, 'invalid', [])])
    ]
}
