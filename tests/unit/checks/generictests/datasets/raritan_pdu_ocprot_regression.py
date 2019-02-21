# yapf: disable
checkname = 'raritan_pdu_ocprot'

info = [[[u'1.1.1', u'4', u'0'], [u'1.1.15', u'1', u'0'], [u'1.2.1', u'4', u'0'],
         [u'1.2.15', u'1', u'0'], [u'1.3.1', u'4', u'70'], [u'1.3.15', u'1', u'0'],
         [u'1.4.1', u'4', u'0'], [u'1.4.15', u'1', u'0'], [u'1.5.1', u'4', u'0'],
         [u'1.5.15', u'1', u'0'], [u'1.6.1', u'4', u'0'], [u'1.6.15', u'1', u'0']],
        [[u'1'], [u'0'], [u'1'], [u'0'], [u'1'], [u'0'], [u'1'], [u'0'], [u'1'], [u'0'], [u'1'],
         [u'0']]]

discovery = {
    '': [(u'C1', 'raritan_pdu_ocprot_current_default_levels'),
         (u'C2', 'raritan_pdu_ocprot_current_default_levels'),
         (u'C3', 'raritan_pdu_ocprot_current_default_levels'),
         (u'C4', 'raritan_pdu_ocprot_current_default_levels'),
         (u'C5', 'raritan_pdu_ocprot_current_default_levels'),
         (u'C6', 'raritan_pdu_ocprot_current_default_levels')]
}

checks = {
    '': [(u'C1', (14.0, 15.0), [(0, 'Overcurrent protector is closed', []),
                                (0, 'Current: 0.0 A', [('current', 0.0, 14.0, 15.0, None, None)])]),
         (u'C2', (14.0, 15.0), [(0, 'Overcurrent protector is closed', []),
                                (0, 'Current: 0.0 A', [('current', 0.0, 14.0, 15.0, None, None)])]),
         (u'C3', (14.0, 15.0), [(0, 'Overcurrent protector is closed', []),
                                (0, 'Current: 7.0 A', [('current', 7.0, 14.0, 15.0, None, None)])]),
         (u'C4', (14.0, 15.0), [(0, 'Overcurrent protector is closed', []),
                                (0, 'Current: 0.0 A', [('current', 0.0, 14.0, 15.0, None, None)])]),
         (u'C5', (14.0, 15.0), [(0, 'Overcurrent protector is closed', []),
                                (0, 'Current: 0.0 A', [('current', 0.0, 14.0, 15.0, None, None)])]),
         (u'C6', (14.0, 15.0), [(0, 'Overcurrent protector is closed', []),
                                (0, 'Current: 0.0 A', [('current', 0.0, 14.0, 15.0, None, None)])])]
}
