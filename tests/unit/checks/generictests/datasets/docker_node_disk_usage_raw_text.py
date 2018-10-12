

checkname = 'docker_node_disk_usage'


info = [
    ['TYPE                TOTAL               ACTIVE              SIZE                RECLAIMABLE'],
    ['Images              15                  2                   9.57GB              8.674GB (90%)'],
    ['Containers          2                   1                   1.226GB             1.224GB (99%)'],
    ['Local Volumes       1                   1                   9.323MB             0B (0%)'],
    ['Build Cache         0                   0                   0B                  0B'],
]


discovery = {'': [('build cache', {}),
                  ('containers', {}),
                  ('images', {}),
                  ('local volumes', {})]}


checks = {'': [('build cache',
                'default',
                [(0, 'size: 0 B', [('size', 0, None, None, None, None)]),
                 (0,
                  'reclaimable: 0 B',
                  [('reclaimable', 0, None, None, None, None)]),
                 (0, 'count: 0', [('count', 0, None, None, None, None)]),
                 (0, 'active: 0', [('active', 0, None, None, None, None)])]),
               ('containers',
                'default',
                [(0,
                  'size: 1169.20 MB',
                  [('size', 1226000000, None, None, None, None)]),
                 (0,
                  'reclaimable: 1167.30 MB',
                  [('reclaimable', 1224000000, None, None, None, None)]),
                 (0, 'count: 2', [('count', 2, None, None, None, None)]),
                 (0, 'active: 1', [('active', 1, None, None, None, None)])]),
               ('images',
                'default',
                [(0,
                  'size: 8.91 GB',
                  [('size', 9570000000, None, None, None, None)]),
                 (0,
                  'reclaimable: 8.08 GB',
                  [('reclaimable', 8674000000, None, None, None, None)]),
                 (0, 'count: 15', [('count', 15, None, None, None, None)]),
                 (0, 'active: 2', [('active', 2, None, None, None, None)])]),
               ('local volumes',
                'default',
                [(0, 'size: 8.89 MB', [('size', 9323000, None, None, None, None)]),
                 (0,
                  'reclaimable: 0 B',
                  [('reclaimable', 0, None, None, None, None)]),
                 (0, 'count: 1', [('count', 1, None, None, None, None)]),
                 (0, 'active: 1', [('active', 1, None, None, None, None)])])]}
