# -*- encoding: utf-8
# yapf: disable

checkname = 'ipmi_sensors'

info = [
    [u'1', u'Temperature_Inlet_Temp', u'21.00_C_(NA/48.00)', u'[OK]'],
    [u'59', u'M2_Temp0(PCIe1)_(Temperature)', u'NA/79.00_41.00_C', u'[OK]'],
    [u'20', u'Fan_FAN1_F_Speed', u'7200.00_RPM_(NA/NA)', u'[OK]'],
]

discovery = {
    '': [
        (u'Fan_FAN1_F_Speed', {}),
        (u'M2_Temp0(PCIe1)_(Temperature)', {}),
        (u'Temperature_Inlet_Temp', {}),
    ]
}

checks = {
    '': [
        (
            u'Fan_FAN1_F_Speed',
            {},
            [(0, u'Status: OK, 7200.0 RPM', [])],
        ),
        (
            u'M2_Temp0(PCIe1)_(Temperature)',
            {},
            [(0, u'Status: OK, 41.0 C', [('value', 41.0, None, 79.0, None, None)])],
        ),
        (
            u'Temperature_Inlet_Temp',
            {},
            [(0, u'Status: OK, 21.0 C', [('value', 21.0, None, 48.0, None, None)])],
        ),
    ]
}
