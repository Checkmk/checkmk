# -*- encoding: utf-8
# yapf: disable


checkname = u'hp_msa_fan'


parsed = {u'Enclosure 1 Left': {u'extended-status': u'16',
                                u'fw-revision': '',
                                u'health': u'OK',
                                u'health-numeric': u'0',
                                u'health-reason': '',
                                u'health-recommendation': '',
                                u'hw-revision': '',
                                'item_type': u'fan',
                                u'location': u'Enclosure 1 - Left',
                                u'locator-led': u'Aus',
                                u'locator-led-numeric': u'0',
                                u'name': u'Fan Loc:left-PSU 1',
                                u'position': u'Links',
                                u'position-numeric': u'0',
                                u'serial-number': '',
                                u'speed': u'3950',
                                u'status': u'Aktiv',
                                u'status-numeric': u'0',
                                u'status-ses': u'OK',
                                u'status-ses-numeric': u'1'},
          u'Enclosure 1 Right': {u'extended-status': u'16',
                                 u'fw-revision': '',
                                 u'health': u'OK',
                                 u'health-numeric': u'0',
                                 u'health-reason': '',
                                 u'health-recommendation': '',
                                 u'hw-revision': '',
                                 'item_type': u'fan',
                                 u'location': u'Enclosure 1 - Right',
                                 u'locator-led': u'Aus',
                                 u'locator-led-numeric': u'0',
                                 u'name': u'Fan Loc:right-PSU 2',
                                 u'position': u'Rechts',
                                 u'position-numeric': u'1',
                                 u'serial-number': '',
                                 u'speed': u'4020',
                                 u'status': u'Aktiv',
                                 u'status-numeric': u'0',
                                 u'status-ses': u'OK',
                                 u'status-ses-numeric': u'1'}}


discovery = {'': [(u'Enclosure 1 Left', None), (u'Enclosure 1 Right', None)]}


checks = {'': [(u'Enclosure 1 Left', {}, [(0, 'Status: up, speed: 3950 RPM', [])]),
               (u'Enclosure 1 Right', {}, [(0, 'Status: up, speed: 4020 RPM', [])])]}