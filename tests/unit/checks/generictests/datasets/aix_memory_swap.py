# -*- encoding: utf-8
# yapf: disable
checkname = 'aix_memory'

info = [
    ['32702464', 'memory', 'pages'], ['31736528', 'lruable', 'pages'],
    ['858141', 'free', 'pages'], ['4', 'memory', 'pools'],
    ['6821312', 'pinned', 'pages'], ['80.0', 'maxpin', 'percentage'],
    ['3.0', 'minperm', 'percentage'], ['90.0', 'maxperm', 'percentage'],
    ['8.8', 'numperm', 'percentage'], ['2808524', 'file', 'pages'],
    ['0.0', 'compressed', 'percentage'], ['0', 'compressed', 'pages'],
    ['8.8', 'numclient', 'percentage'], ['90.0', 'maxclient', 'percentage'],
    ['2808524', 'client', 'pages'], ['0', 'remote', 'pageouts', 'scheduled'],
    ['354', 'pending', 'disk', 'I/Os', 'blocked', 'with', 'no', 'pbuf'],
    ['860832', 'paging', 'space', 'I/Os', 'blocked', 'with', 'no', 'psbuf'],
    ['2228', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
    ['508', 'client', 'filesystem', 'I/Os', 'blocked', 'with', 'no', 'fsbuf'],
    [
        '1372', 'external', 'pager', 'filesystem', 'I/Os', 'blocked', 'with',
        'no', 'fsbuf'
    ],
    [
        '88.8', 'percentage', 'of', 'memory', 'used', 'for', 'computational',
        'pages'
    ],
    [
        'allocated', '=', '8257536', 'blocks', 'used', '=', '1820821',
        'blocks', 'free', '=', '6436715', 'blocks'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (None, { 'levels': (150.0, 200.0) }, [
            (0, "Total (RAM + Swap): 94.36% - 117.71 GB of 124.75 GB RAM", [
                ('swapused', 7112.58203125, None, None, 0, 32256.0),
                ('ramused', 113421.08984375, None, None, 0, 127744.0),
                ('memused', 120533.671875, 191616.0, 255488.0, 0, 160000.0),
            ]),
            (0, "RAM: 88.79% - 110.76 GB of 124.75 GB", []),
            (0, "Swap: 22.05% - 6.95 GB of 31.50 GB", []),
        ]),
    ],
}
