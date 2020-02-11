# -*- encoding: utf-8
# yapf: disable
checkname = 'netscaler_mem'

info = [['4.2', '23']]

discovery = {'': [(None, 'netscaler_mem_default_levels')]}

checks = {
    '': [
        (
            None, (80.0, 90.0), [
                (
                    0, 'Usage: 4.2% - 989.18 kB of 23.00 MB', [
                        (
                            'mem', 1012924.4160000001, 19293798.400000002,
                            21705523.2, 0, 24117248.0
                        )
                    ]
                )
            ]
        )
    ]
}
