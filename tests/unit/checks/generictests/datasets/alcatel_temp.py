checkname = 'alcatel_temp'

info = [['10', '20'], ['11', '21'], ['12', '22']]

discovery = {
    '': [('Slot 1 Board', {}), ('Slot 1 CPU', {}), ('Slot 2 Board', {}), ('Slot 2 CPU', {}),
         ('Slot 3 Board', {}), ('Slot 3 CPU', {})]
}

checks = {
    '': [('Slot 1 Board', {
        'levels': (45, 50)
    }, [(0, u'10 \xb0C', [('temp', 10, 45, 50, None, None)])]),
         ('Slot 1 CPU', {
             'levels': (45, 50)
         }, [(0, u'20 \xb0C', [('temp', 20, 45, 50, None, None)])]),
         ('Slot 2 Board', {
             'levels': (45, 50)
         }, [(0, u'11 \xb0C', [('temp', 11, 45, 50, None, None)])]),
         ('Slot 2 CPU', {
             'levels': (45, 50)
         }, [(0, u'21 \xb0C', [('temp', 21, 45, 50, None, None)])]),
         ('Slot 3 Board', {
             'levels': (45, 50)
         }, [(0, u'12 \xb0C', [('temp', 12, 45, 50, None, None)])]),
         ('Slot 3 CPU', {
             'levels': (45, 50)
         }, [(0, u'22 \xb0C', [('temp', 22, 45, 50, None, None)])])]
}
