# yapf: disable
checkname = 'hp_msa_fan'

info = [[u'fan', u'2', u'durable-id', u'fan_1.1'],
        [u'fan', u'2', u'name', u'Fan', u'Loc:left-PSU', u'1'],
        [u'fan', u'2', u'location', u'Enclosure', u'1', u'-', u'Left'],
        [u'fan', u'2', u'status-ses', u'OK'], [u'fan', u'2', u'status-ses-numeric', u'1'],
        [u'fan', u'2', u'extended-status', u'16'], [u'fan', u'2', u'status', u'Up'],
        [u'fan', u'2', u'status-numeric', u'0'], [u'fan', u'2', u'speed', u'3780'],
        [u'fan', u'2', u'position', u'Left'], [u'fan', u'2', u'position-numeric', u'0'],
        [u'fan', u'2', u'serial-number', u'N/A'], [u'fan', u'2', u'part-number', u'N/A'],
        [u'fan', u'2', u'fw-revision'], [u'fan', u'2', u'hw-revision'],
        [u'fan', u'2', u'locator-led', u'Off'], [u'fan', u'2', u'locator-led-numeric', u'0'],
        [u'fan', u'2', u'health', u'OK'], [u'fan', u'2', u'health-numeric', u'0'],
        [u'fan', u'2', u'health-reason'], [u'fan', u'2', u'health-recommendation'],
        [u'fan', u'4', u'durable-id', u'fan_1.2'],
        [u'fan', u'4', u'name', u'Fan', u'Loc:right-PSU', u'2'],
        [u'fan', u'4', u'location', u'Enclosure', u'1', u'-', u'Right'],
        [u'fan', u'4', u'status-ses', u'OK'], [u'fan', u'4', u'status-ses-numeric', u'1'],
        [u'fan', u'4', u'extended-status', u'16'], [u'fan', u'4', u'status', u'Up'],
        [u'fan', u'4', u'status-numeric', u'0'], [u'fan', u'4', u'speed', u'3840'],
        [u'fan', u'4', u'position', u'Right'], [u'fan', u'4', u'position-numeric', u'1'],
        [u'fan', u'4', u'serial-number', u'N/A'], [u'fan', u'4', u'part-number', u'N/A'],
        [u'fan', u'4', u'fw-revision'], [u'fan', u'4', u'hw-revision'],
        [u'fan', u'4', u'locator-led', u'Off'], [u'fan', u'4', u'locator-led-numeric', u'0'],
        [u'fan', u'4', u'health', u'OK'], [u'fan', u'4', u'health-numeric', u'0'],
        [u'fan', u'4', u'health-reason'], [u'fan', u'4', u'health-recommendation']]

discovery = {'': [(u'Enclosure 1 Left', None), (u'Enclosure 1 Right', None)]}

checks = {
    '': [(u'Enclosure 1 Left', {}, [(0, 'Status: up, speed: 3780 RPM', [])]),
         (u'Enclosure 1 Right', {}, [(0, 'Status: up, speed: 3840 RPM', [])])]
}
