# -*- encoding: utf-8
# yapf: disable


checkname = 'win_printers'


info = [
    ['PrinterStockholm', '3', '4', '0'],
    ['Printer', 'Berlin', '3', '4', '0'],
    ['WH1_BC_O3_UPS', '0', '3', '8'],
    ['"printerstatus","detectederrorstate"',
     '-Type',
     'OnlyIfInBoth',
     '|',
     'format-table',
     '-HideTableHeaders']
]


discovery = {'': [('PrinterStockholm', {}), ('Printer Berlin', {}), ('WH1_BC_O3_UPS', {})]}


checks = {'': [('PrinterStockholm',
                {'crit_states': [9, 10], 'warn_states': [8, 11]},
                [(0, '3 jobs current, State: Printing, ', [])]),
               ('Printer Berlin',
                {'crit_states': [9, 10], 'warn_states': [8, 11]},
                [(0, '3 jobs current, State: Printing, ', [])]),
               ('WH1_BC_O3_UPS',
                {'crit_states': [9, 10], 'warn_states': [8, 11]},
                [(1, '0 jobs current, State: Idle, Error State: Jammed(!)', [])])]}
