# pylint: disable=invalid-name

checkname = 'filestats'

info = [
    ["[[[file_stats aix agent files]]]"],
    ["{'stat_status': 'ok', 'age': 230276, 'mtime': 1544196317,"
     " 'path': '/home/mo/git/check_mk/agents/check_mk_agent.aix', 'type': 'file', 'size': 12886}"],
    ["{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990,"
     " 'path': '/home/mo/git/check_mk/agents/plugins/mk_sap.aix', 'type': 'file', 'size': 3928}"],
    ["{'stat_status': 'ok', 'age': 230276, 'mtime': 1544196317, 'path':"
     " '/home/mo/git/check_mk/agents/plugins/mk_logwatch.aix', 'type': 'file', 'size': 1145}"],
    ["{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990, 'path':"
     " '/home/mo/git/check_mk/agents/plugins/netstat.aix', 'type': 'file', 'size': 1697}"],
    ["{'stat_status': 'ok', 'age': 9398016, 'mtime': 1535028577, 'path':"
     " '/home/mo/git/check_mk/agents/plugins/mk_inventory.aix', 'type': 'file', 'size': 2637}"],
    ["{'stat_status': 'ok', 'age': 18751603, 'mtime': 1525674990, 'path':"
     " '/home/mo/git/check_mk/agents/plugins/mk_db2.aix', 'type': 'file', 'size': 10138}"],
    ["{'type': 'summary', 'count': 6}"],
    ['[[[count_only $ection with funny characters %s &! (count files in ~)]]]'],
    ["{'type': 'summary', 'count': 35819}"],
    ['[[[extremes_only log files]]]'],
    ["{'stat_status': 'ok', 'age': 89217820, 'mtime': 1455208773, 'path':"
     " '/var/log/installer/casper.log', 'type': 'file', 'size': 1216}"],
    ["{'stat_status': 'ok', 'age': 4451, 'mtime': 1544422142, 'path': '/var/log/boot.log',"
     " 'type': 'file', 'size': 2513750}"],
    ["{'stat_status': 'ok', 'age': 252, 'mtime': 1544426341, 'path': '/var/log/auth.log',"
     " 'type': 'file', 'size': 7288}"],
    ["{'stat_status': 'ok', 'age': 15965608, 'mtime': 1528460985, 'path': '/var/log/tacwho.log',"
     " 'type': 'file', 'size': 0}"],
    ["{'type': 'summary', 'count': 17}"],
]

discovery = {
    '': [
        ('aix agent files', {}),
        ('$ection with funny characters %s &! (count files in ~)', {}),
        ('log files', {}),
    ]
}

checks = {
    '': [
        ('aix agent files', 'default', [
            (0, 'Files in total: 6', [('file_count', 6, None, None, None, None)]),
            (0, 'Smallest: 1.12 kB', []), (0, 'Largest: 12.58 kB', []),
            (0, 'Newest: 2.6 d', []), (0, 'Oldest: 217 d', [])
        ]),
        ('aix agent files', {"maxsize_largest": (12*1024, 13*1024),
                             "minage_newest": (3600*72, 3600*96)},
         [
             (0, 'Files in total: 6', [('file_count', 6, None, None, None, None)]),
             (0, 'Smallest: 1.12 kB', []),
             (1, 'Largest: 12.58 kB (warn/crit at 12.00 kB/13.00 kB):'
                 ' /home/mo/git/check_mk/agents/check_mk_agent.aix', []),
             (2, 'Newest: 2.6 d (warn/crit below 3 d/4 d):'
                 ' /home/mo/git/check_mk/agents/plugins/mk_logwatch.aix', []),
             (0, 'Oldest: 217 d', [])
         ]
        ),
        ('$ection with funny characters %s &! (count files in ~)', {"maxcount": (5, 10)},
         [
             (2, 'Files in total: 35819 (warn/crit at 5/10)',
              [('file_count', 35819, 5, 10, None, None)]),
         ]
        ),
        ('log files', 'default', [
            (0, 'Files in total: 17', [('file_count', 17, None, None, None, None)]),
            (0, 'Smallest: 0.00 B', []),
            (0, 'Largest: 2.40 MB', []),
            (0, 'Newest: 4 m', []),
            (0, 'Oldest: 2.8 y', []),
        ]),
    ]
}
