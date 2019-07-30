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
            (1, '6.73 GB used (3.37 GB RAM + 3.37 GB SWAP,'
                ' this is 168.4% of 4.00 GB RAM + 8.00 GB SWAP), warning at 150.0% used', [
                ('ramused', 3449, None, None, 0, 4096.0),
                ('swapused', 3446, None, None, 0, 8192),
                ('memused', 6895.859375, 6144, 8192, 0, 12288.0),
            ]),
        ]),
    ],
}
