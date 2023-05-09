#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



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
