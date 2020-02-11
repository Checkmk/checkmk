# -*- encoding: utf-8
# yapf: disable


checkname = 'statgrab_mem'


info = [['mem.cache', '0'],
        ['mem.total', '4294967296'],
        ['mem.free', '677666816'],
        ['mem.used', '3617300480'],
        ['swap.total', '8589934592'],
        ['swap.free', '4976402432'],
        ['swap.used', '3613532160']]


discovery = {
    '': [
        (None, 'memused_default_levels'),
    ],
}


checks = {
    '': [
        (None, (150.0, 200.0), [
            (1, 'Total (RAM + Swap): 168% - 6.73 GB of 4.00 GB RAM (warn/crit at 150%/200% used)', [
                ('swapused', 3446.1328125, None, None, 0, 8192),
                ('ramused', 3449.7265625, None, None, 0, 4096.0),
                ('memused', 6895.859375, 6144.0, 8192.0, 0, 12288.0),
            ]),
            (0, "RAM: 84.22% - 3.37 GB of 4.00 GB", []),
            (0, "Swap: 42.07% - 3.37 GB of 8.00 GB", []),
        ]),
    ],
}
