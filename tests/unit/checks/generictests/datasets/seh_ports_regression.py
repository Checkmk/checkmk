# -*- encoding: utf-8
# yapf: disable

checkname = 'seh_ports'

info = [[[u'2.0', u'20848_Ent_GNSMART2', u'010.099.005.209', u'15'],
         [u'3.0', u'20673_GNSMART1_Daten', u'010.028.103.077', u'4'],
         [u'4.0', u'20557_Ent_SSR-Post', u'010.028.103.076', u'5'],
         [u'5.0', u'20676_Postprocessing', u'010.028.103.075', u'6'],
         [u'6.0', u'20675_Postprocessing', u'SAPOS-Admin (010.099.005.208)', u'7'],
         [u'7.0', u'20785_Ent_GNSMART2', u'010.099.005.111', u'8'],
         [u'8.0', u'20786_Ent_GNSMART2', u'010.099.005.202', u'12'],
         [u'9.0', u'20737_GNSMART1_Vernetzung_NI', u'010.028.103.078', u'10'],
         [u'10.0', u'20119_Postprocessing', u'ent.westphal (010.028.130.016)', u'20'],
         [u'12.0', u'20672_GNSMART1_Vernetzung_NI', u'SAPOS-Admin (010.099.005.205)', u'3'],
         [u'13.0', u'20674_GNSMART1_alles', u'010.099.005.102', u'14'],
         [u'14.0', u'20414_SSR-Post', u'010.099.005.112', u'19'],
         [u'15.0', u'20833_GNSMART1_Vernetzung_DE', u'010.099.005.207', u'16'],
         [u'16.0', u'20606_GNSMART1_PE-Client', u'SAPOS-Admin (010.099.005.204)', u'17'],
         [u'17.0', u'20387_GNSMART1_Daten', u'SAPOS-Admin (010.099.005.206)', u'18'],
         [u'18.0', u'20600_GNSMART1_RxTools', u'-', u'0'],
         [u'19.0', u'20837_Ent_GNSMART2', u'Available', u'2'],
         [u'20.0', u'Test', u'SAPOS-Admin (010.099.005.203)', u'9'],
         [u'21.0', u'', u'010.099.005.114', u'13']]]

discovery = {
    '': [
        (u'10', {
            'status_at_discovery': u'010.028.103.078'
        }),
        (u'12', {
            'status_at_discovery': u'010.099.005.202'
        }),
        (u'13', {
            'status_at_discovery': u'010.099.005.114'
        }),
        (u'14', {
            'status_at_discovery': u'010.099.005.102'
        }),
        (u'15', {
            'status_at_discovery': u'010.099.005.209'
        }),
        (u'16', {
            'status_at_discovery': u'010.099.005.207'
        }),
        (u'17', {
            'status_at_discovery': u'SAPOS-Admin (010.099.005.204)'
        }),
        (u'18', {
            'status_at_discovery': u'SAPOS-Admin (010.099.005.206)'
        }),
        (u'19', {
            'status_at_discovery': u'010.099.005.112'
        }),
        (u'2', {
            'status_at_discovery': u'Available'
        }),
        (u'20', {
            'status_at_discovery': u'ent.westphal (010.028.130.016)'
        }),
        (u'3', {
            'status_at_discovery': u'SAPOS-Admin (010.099.005.205)'
        }),
        (u'4', {
            'status_at_discovery': u'010.028.103.077'
        }),
        (u'5', {
            'status_at_discovery': u'010.028.103.076'
        }),
        (u'6', {
            'status_at_discovery': u'010.028.103.075'
        }),
        (u'7', {
            'status_at_discovery': u'SAPOS-Admin (010.099.005.208)'
        }),
        (u'8', {
            'status_at_discovery': u'010.099.005.111'
        }),
        (u'9', {
            'status_at_discovery': u'SAPOS-Admin (010.099.005.203)'
        }),
    ]
}

checks = {
    '': [
        (u'8', {'status_at_discovery': u'010.099.005.111'}, [
            (0, u'Tag: 20786_Ent_GNSMART2', []),
            (0, u'Status: 010.099.005.111', []),
        ]),
        (u'9', {'status_at_discovery': u'Available'}, [
            (0, u'Tag: 20737_GNSMART1_Vernetzung_NI', []),
            (0, u'Status: SAPOS-Admin (010.099.005.203)', []),
            (1, u'Status during discovery: Available', []),
        ]),
        (u'9', {'status_at_discovery': None}, [
            (0, u'Tag: 20737_GNSMART1_Vernetzung_NI', []),
            (0, u'Status: SAPOS-Admin (010.099.005.203)', []),
            (1, u'Status during discovery: unknown', []),
        ]),
    ]
}
