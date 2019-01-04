

checkname = 'ipmi_sensors'


info = [['32', 'Temperature_Ambient', '20.00_C_(1.00/42.00)', '[OK]'],
        ['416', 'Temperature_DIMM-2A', 'NA(NA/115.00)', '[Unknown]'],
        ['4288', 'Power_Unit_PSU', '[Redundancy_Lost]'],
        ['138', 'OEM_Reserved_CPU_Temp', 'NA_NA_(NA/NA)', '[OEM_Event_=_0000h]'],
        ['875', 'Power_Supply_PS_Status', 'NA_NA_(NA/NA)', '[Presence_detected]']]


discovery = {'': [('Power_Supply_PS_Status', {}),
                  ('Power_Unit_PSU', {}),
                  ('Temperature_Ambient', {})]}


checks = {'': [('Power_Supply_PS_Status', {}, [(0, 'Status: Presence detected', [])]),
               ('Power_Unit_PSU', {}, [(2, 'Status: Redundancy Lost', [])]),
               ('Temperature_Ambient',
                {},
                [(0,
                  'Status: OK, 20.0 C',
                  [('value', 20.0, None, 42.0, None, None)])])]}