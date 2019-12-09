checkname = 'qnap_hdd_temp'

info = [[u'HDD1', u'GOOD', u'37 C/98 F', u'HDS722020ALA330 \n'],
        [u'HDD2', u'GOOD', u'32 C/89 F', u'WD20EFRX-68EUZN0\n'],
        [u'HDD3', u'GOOD', u'40 C/104 F', u'HDS722020ALA330 \n'],
        [u'HDD4', u'GOOD', u'39 C/102 F', u'HDS723020BLA642 \n'],
        [u'HDD5', u'Normal', u'45 C/113 F', u'HDS722020ALA330 \n'],
        [u'HDD6', u'Normal', u'43 C/109 F', u'HDS722020ALA330 \n']]

discovery = {
    '': [(u'HDD1', {}), (u'HDD2', {}), (u'HDD3', {}), (u'HDD4', {}), (u'HDD5', {}), (u'HDD6', {})]
}
checks = {
    '': [
        ('HDD1', {}, [(0, u"State is GOOD, HDD-model: HDS722020ALA330, Temperature: 37.0 \xb0C",
                       [('temp', 37, 40, 45, None, None)])]),
        ('HDD2', {}, [(0, u"State is GOOD, HDD-model: WD20EFRX-68EUZN0, Temperature: 32.0 \xb0C",
                       [('temp', 32, 40, 45, None, None)])]),
        ('HDD3', {}, [(1, u"State is GOOD, HDD-model: HDS722020ALA330, Temperature: 40.0 \xb0C",
                       [('temp', 40, 40, 45, None, None)])]),
        ('HDD4', {}, [(0, u"State is GOOD, HDD-model: HDS723020BLA642, Temperature: 39.0 \xb0C",
                       [('temp', 39, 40, 45, None, None)])]),
        ('HDD5', {}, [(2, u"State is Normal, HDD-model: HDS722020ALA330, Temperature: 45.0 \xb0C",
                       [('temp', 45, 40, 45, None, None)])]),
        ('HDD6', {}, [(1, u"State is Normal, HDD-model: HDS722020ALA330, Temperature: 43.0 \xb0C",
                       [('temp', 43, 40, 45, None, None)])]),
    ]
}
