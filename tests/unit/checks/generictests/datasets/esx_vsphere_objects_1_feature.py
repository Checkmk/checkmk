

checkname = 'esx_vsphere_objects'


info = [['hostsystem', '10.1.1.112', '', 'poweredOn'],
        ['hostsystem', '10.1.1.111', '', 'poweredOn'],
        ['virtualmachine', 'Grafana', '10.1.1.111', 'poweredOn'],
        ['virtualmachine', 'Server', '10.1.1.111', 'poweredOff'],
        ['virtualmachine', 'virt1-1.4.2', '10.1.1.112', 'poweredOff'],
        ['virtualmachine', 'Schulungs_ESXi', '10.1.1.112', 'poweredOff'],
]


checks = {
    'count': [(None,
               {"distribution": [{"vm_names": ["Grafana", "Server"],
                                  "hosts_count": 2, "state": 2},]},
               [(0, 'Virtualmachines: 4', [('vms', 4, None, None, None, None)]),
                (0, 'Hostsystems: 2', [('hosts', 2, None, None, None, None)]),
                (2, 'VMs Grafana, Server are running on 1 host: 10.1.1.111', []),
               ]
              ),
              (None,
               {"distribution": [{"vm_names": ["Grafana", "Schulungs_ESXi"],
                                  "hosts_count": 2, "state": 2},]},
               [(0, 'Virtualmachines: 4', [('vms', 4, None, None, None, None)]),
                (0, 'Hostsystems: 2', [('hosts', 2, None, None, None, None)]),
               ]
              )
    ],
}
