# -*- encoding: utf-8
# yapf: disable


checkname = u'aix_if'


info = [[u'[en3]'],
        [u'Hardware', u'Address:', u'00:AA:BB:CC:DD:EE'],
        [u'Packets:', u'38832476370', u'Packets:', u'4125941951'],
        [u'Bytes:', u'57999949458755', u'Bytes:', u'627089523952']]


discovery = {'': [('1', "{'state': ['1'], 'speed': 0}")]}


checks = {'': [('1',
                {'errors': (0.01, 0.1), 'speed': 0, 'state': ['1']},
                [(0, '[en3] (up) MAC: 00:AA:BB:CC:DD:EE, speed unknown', [])])]}