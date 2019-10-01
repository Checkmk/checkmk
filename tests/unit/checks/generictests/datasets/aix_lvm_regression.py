# -*- encoding: utf-8
# yapf: disable


checkname = 'aix_lvm'


info = [[u'rootvg:'],
        [u'LV',
         u'NAME',
         u'TYPE',
         u'LPs',
         u'PPs',
         u'PVs',
         u'LV',
         u'STATE',
         u'MOUNT',
         u'POINT'],
        [u'hd5', u'boot', u'1', u'4', u'2', u'closed/syncd', u'N/A'],
        [u'hd6', u'paging', u'119', u'238', u'2', u'open/syncd', u'N/A'],
        [u'hd8', u'jfs2log', u'1', u'3', u'2', u'open/syncd', u'N/A'],
]


discovery = {'': [(u'rootvg/hd5', None),
                  (u'rootvg/hd6', None),
                  (u'rootvg/hd8', None),
                  ]}


checks = {'': [(u'rootvg/hd5', {}, [(1, 'LV Mirrors are misaligned between physical volumes(!)', [])]),
               (u'rootvg/hd6', {}, [(0, 'LV is open/syncd', [])]),
               (u'rootvg/hd8', {}, [(0, 'LV is open/syncd', [])]),
               ]}
