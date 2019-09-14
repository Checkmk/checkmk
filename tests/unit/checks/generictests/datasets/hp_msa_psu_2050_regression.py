# -*- encoding: utf-8
# yapf: disable


checkname = 'hp_msa_psu'


info = [
    ['power-supplies', '3', 'durable-id', 'psu_1.2'],
    ['power-supplies', '3', 'url', '/power-supplies/psu_1.2'],
    ['power-supplies', '3', 'enclosures-url', '/enclosures/1'],
    ['power-supplies', '3', 'enclosure-id', '1'],
    ['power-supplies', '3', 'dom-id', '2'],
    ['power-supplies', '3', 'serial-number', '7CE849T228'],
    ['power-supplies', '3', 'part-number', '814665-001'],
    ['power-supplies', '3', 'description', 'FRU,Pwr', 'Sply,595W,AC,2U,LC,HP', 'ES'],
    ['power-supplies', '3', 'name', 'PSU', '2,', 'Right'],
    ['power-supplies', '3', 'fw-revision', 'N/A'],
    ['power-supplies', '3', 'revision', 'C1'],
    ['power-supplies', '3', 'model', '814665-001'],
    ['power-supplies', '3', 'vendor'],
    ['power-supplies', '3', 'location', 'Enclosure', '1', '-', 'Right'],
    ['power-supplies', '3', 'position', 'Right'],
    ['power-supplies', '3', 'position-numeric', '1'],
    ['power-supplies', '3', 'dash-level'],
    ['power-supplies', '3', 'fru-shortname', 'AC', 'Power', 'Supply'],
    ['power-supplies', '3', 'mfg-date', '2018-11-14', '16:44:48'],
    ['power-supplies', '3', 'mfg-date-numeric', '1542213888'],
    ['power-supplies', '3', 'mfg-location', 'Zhongshan,Guangdong,CN'],
    ['power-supplies', '3', 'mfg-vendor-id'],
    ['power-supplies', '3', 'configuration-serialnumber', '7CE849T228'],
    ['power-supplies', '3', 'dc12v', '0'],
    ['power-supplies', '3', 'dc5v', '0'],
    ['power-supplies', '3', 'dc33v', '0'],
    ['power-supplies', '3', 'dc12i', '0'],
    ['power-supplies', '3', 'dc5i', '0'],
    ['power-supplies', '3', 'dctemp', '0'],
    ['power-supplies', '3', 'health', 'OK'],
    ['power-supplies', '3', 'health-numeric', '0'],
    ['power-supplies', '3', 'health-reason'],
    ['power-supplies', '3', 'health-recommendation'],
    ['power-supplies', '3', 'status', 'Up'],
    ['power-supplies', '3', 'status-numeric', '0'],
]


discovery = {
    '': [
        ('Enclosure 1 Right', None),
    ],
    'sensor': [
    ],
    'temp': [
    ],
}


default_params = {
    'levels_12v_lower': (11.9, 11.8),
    'levels_12v_upper': (12.1, 12.2),
    'levels_33v_lower': (3.25, 3.2),
    'levels_33v_upper': (3.4, 3.45),
    'levels_5v_lower': (4.9, 4.8),
    'levels_5v_upper': (5.1, 5.2),
}


checks = {
    '': [
        ('Enclosure 1 Right', {}, [
            (0, 'Status: OK', []),
        ]),
    ],
    'sensor': [
        ('Enclosure 1 Right', default_params, [
            (0, '12 V: 0.00 V', []),
            (2, 'too low (warn/crit below 11.90 V/11.80 V)', []),
            (0, '5 V: 0.00 V', []),
            (2, 'too low (warn/crit below 4.90 V/4.80 V)', []),
            (0, '3.3 V: 0.00 V', []),
            (2, 'too low (warn/crit below 3.25 V/3.20 V)', []),
        ]),
    ],
    'temp': [
        ('Enclosure 1 Right', {'levels': (40, 45)}, [
            (0, u'0.0 \xb0C', [('temp', 0.0, 40, 45, None, None)]),
        ]),
    ]}
