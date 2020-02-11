# -*- encoding: utf-8
# yapf: disable
checkname = 'tplink_mem'

info = [[u'30'], [u'60']] # multiple memory units

discovery = {'': [(None, {})]}

# This check tests the level parameters as well as the averaging of the
# memory utilization values from multiple units
checks = {
    '': [
        (
            None, {'levels': (40.0, 60.0)}, [
                (1, 'Usage: 45.0% (warn/crit at 40.0%/60.0%)', [('mem_used_percent', 45.0, 40.0, 60.0)])
            ]
        )
    ]
}
