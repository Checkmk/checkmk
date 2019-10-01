# -*- encoding: utf-8
# yapf: disable


checkname = 'liebert_compressor'


info = [[u'Compressor Head Pressure',
         u'5.9',
         u'bar',
         u'Compressor Head Pressure',
         u'6.1',
         u'bar',
         u'Compressor Head Pressure',
         u'Unavailable',
         u'bar',
         u'Compressor Head Pressure',
         u'0.0',
         u'bar']]


discovery = {'': [(u'Compressor Head Pressure 2', {}),
                  (u'Compressor Head Pressure 4', {}),
                  (u'Compressor Head Pressure', {})]}


checks = {
    '': [
        (u'Compressor Head Pressure 2', {'levels': (8, 12)}, [(0, u'Head pressure: 6.10 bar', [])]),
        (u'Compressor Head Pressure 4', {'levels': (8, 12)}, [(0, u'Head pressure: 0.00 bar', [])]),
        (u'Compressor Head Pressure', {'levels': (8, 12)}, [(0, u'Head pressure: 5.90 bar', [])]),
    ],
}
