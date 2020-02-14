# -*- encoding: utf-8
# yapf: disable

checkname = "domino_mailqueues"


info = [
    [[u'.1.3.6.1.4.1.334.72.1.1.4.1.0', u'1']],
    [[u'.1.3.6.1.4.1.334.72.1.1.4.6.0', u'4711']],
    [[u'.1.3.6.1.4.1.334.72.1.1.4.21.0', u'815']],
    [[u'.1.3.6.1.4.1.334.72.1.1.4.31.0', u'1']],
    [[u'.1.3.6.1.4.1.334.72.1.1.4.34.0', u'12']],
]


discovery = {
    '': [
        ("lnDeadMail", {}),
        ("lnWaitingMail", {}),
        ("lnMailHold", {}),
        ("lnMailTotalPending", {}),
        ("InMailWaitingforDNS", {}),
    ],
}


checks = {
    '': [
        ("lnDeadMail", {'queue_length': (300, 350)}, [
            (0, "1 Dead Mails", [
                ('mails', 1, 300, 350, None, None),
            ]),
        ]),
        ("lnWaitingMail", {'queue_length': (300, 350)}, [
            (2, "4711 Waiting Mails (Warn/Crit at 300/350)", [
                ('mails', 4711, 300, 350, None, None),
            ]),
        ]),
        ("lnMailHold", {'queue_length': (300, 350)}, [
            (2, "815 Mails on Hold (Warn/Crit at 300/350)", [
                ('mails', 815, 300, 350, None, None),
            ]),
        ]),
        ("lnMailTotalPending", {'queue_length': (300, 350)}, [
            (0, "1 Total Pending Mails", [
                ('mails', 1, 300, 350, None, None),
            ]),
        ]),
        ("InMailWaitingforDNS", {'queue_length': (300, 350)}, [
            (0, "12 Mails waiting for DNS", [
                ('mails', 12, 300, 350, None, None),
            ])
        ]),
    ],
}
