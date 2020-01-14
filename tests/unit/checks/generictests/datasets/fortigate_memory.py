# -*- encoding: utf-8
# yapf: disable
checkname = 'fortigate_memory'

info = [['42']]

discovery = {'': [(None, 'fortigate_memory_default_levels')]}

checks = {
    '': [
        (None, (70, 80), [
            (0, 'Usage: 42.0%', [('mem_usage', 42, 70.0, 80.0, None, None)]),
        ]),
        (None, (30, 80), [
            (1, 'Usage: 42.0% (warn/crit at 30.0%/80.0%)', [('mem_usage', 42, 30.0, 80.0, None, None)]),
        ]),
        (None, (-80, -30), [
            (1, 'Usage: 42.0% (warn/crit at 20.0%/70.0%)', [('mem_usage', 42, 20.0, 70.0, None, None)]),
        ]),
        (None, {"levels": (-80, -30)}, [
            (3, "Absolute levels are not supported", []),
            (0, 'Usage: 42.0%', [('mem_usage', 42, None, None, None, None)]),
        ]),
    ],
}
