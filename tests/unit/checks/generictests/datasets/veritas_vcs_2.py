# yapf: disable

checkname = 'veritas_vcs'

info = [
    [None, 'ClusState', 'RUNNING'],
    [None, 'ClusterName', 'minions'],
    [None, '#System', 'Attribute', 'Value'],
    [None, 'dave', 'SysState', 'RUNNING'],
    [None, 'stuart', 'SysState', 'RUNNING'],
    [None, '#Group', 'Attribute', 'System', 'Value'],
    [None, 'ClusterService', 'State', 'stuart', '|OFFLINE|'],
    [None, 'nepharius', 'State', 'stuart', '|ONLINE|'],
    [None, 'lan', 'State', 'stuart', '|ONLINE|'],
    [None, 'omd', 'State', 'stuart', '|ONLINE|'],
    [None, '#Resource', 'Attribute', 'System', 'Value'],
    [None, 'nepharius_mrs', 'State', 'stuart', 'ONLINE'],
    [None, 'nepharius_dr', 'State', 'stuart', 'ONLINE'],
    [None, 'cs_ip', 'State', 'stuart', 'OFFLINE'],
    [None, 'cs_proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'lan_nic', 'State', 'stuart', 'ONLINE'],
    [None, 'lan_phantom', 'State', 'stuart', 'ONLINE'],
    [None, 'omd_apache', 'State', 'stuart', 'ONLINE'],
    [None, 'omd_appl', 'State', 'stuart', 'ONLINE'],
    [None, 'omd_dg', 'State', 'stuart', 'ONLINE'],
    [None, 'omd_proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'omd_srdf', 'State', 'stuart', 'ONLINE'],
    [None, 'omd_uc4ps1_agt', 'State', 'stuart', 'ONLINE'],
    [None, 'omdp_ip', 'State', 'stuart', 'ONLINE'],
    [None, 'omdp_mnt', 'State', 'stuart', 'ONLINE'],
    [None, '#Group', 'Attribute', 'System', 'Value'],
    [None, 'ClusterService', 'Frozen', 'global', '0'],
    [None, 'ClusterService', 'TFrozen', 'global', '0'],
    [None, '#'],
    [None, 'nepharius', 'Frozen', 'global', '0'],
    [None, 'nepharius', 'TFrozen', 'global', '1'],
    [None, '#'],
    [None, 'lan', 'Frozen', 'global', '0'],
    [None, 'lan', 'TFrozen', 'global', '0'],
    [None, '#'],
    [None, 'omd', 'Frozen', 'global', '1'],
    [None, 'omd', 'TFrozen', 'global', '0'],
]

discovery = {
    '': [('minions', None)],
    'resource': [('cs_ip', None), ('cs_proxy', None), ('lan_nic', None), ('lan_phantom', None),
                 ('nepharius_dr', None), ('nepharius_mrs', None), ('omd_apache', None),
                 ('omd_appl', None), ('omd_dg', None), ('omd_proxy', None), ('omd_srdf', None),
                 ('omd_uc4ps1_agt', None), ('omdp_ip', None), ('omdp_mnt', None)],
    'servicegroup': [('ClusterService', None), ('lan', None), ('nepharius', None), ('omd', None)],
    'system': [('dave', None), ('stuart', None)]
}

checks = {
    'servicegroup': [
    ('nepharius', {
        'map_frozen': {
            'frozen': 2,
            'tfrozen': 1
        },
        'map_states': {
            'EXITED': 1,
            'FAULTED': 2,
            'OFFLINE': 1,
            'OK': 0,
            'ONLINE': 0,
            'PARTIAL': 1,
            'RUNNING': 0,
            'UNKNOWN': 3,
            'default': 1
        }
    }, [(1, 'Temporarily frozen', []), (0, 'Online', []), (0, 'Cluster: minions', [])]),
    ('omd', {
        'map_frozen': {
            'frozen': 3,
            'tfrozen': 1
        },
        'map_states': {
            'EXITED': 1,
            'FAULTED': 2,
            'OFFLINE': 1,
            'OK': 0,
            'ONLINE': 0,
            'PARTIAL': 1,
            'RUNNING': 0,
            'UNKNOWN': 3,
            'default': 1
        }
    }, [(3, 'Frozen', []), (0, 'Online', []), (0, 'Cluster: minions', [])])],
}
