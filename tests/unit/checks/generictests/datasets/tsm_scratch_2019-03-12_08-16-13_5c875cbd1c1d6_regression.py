# -*- encoding: utf-8
# yapf: disable


checkname = u'tsm_scratch'


info = [[u'Foo23',
         u'SELECT:',
         u'No',
         u'match',
         u'found',
         u'using',
         u'this',
         u'criteria.'],
        [u'Bar42', u'R\xfcckkehrcode', u'11.'],
        [u'Baz123', u'6', u'Any.Lib1'],
        [u'default', u'8', u'Any.Lib2']]


discovery = {'': [(u'Any.Lib2', 'tsm_scratch_default_levels'),
                  (u'Baz123 / Any.Lib1', 'tsm_scratch_default_levels')]}


checks = {'': [(u'Any.Lib2',
                (5, 7),
                [(0, 'Found tapes: 8', [('tapes_free', 8, None, None, None, None)])]),
               (u'Baz123 / Any.Lib1',
                (5, 7),
                [(1,
                  'Found tapes: 6 (warn/crit below 7/5)',
                  [('tapes_free', 6, None, None, None, None)])])]}