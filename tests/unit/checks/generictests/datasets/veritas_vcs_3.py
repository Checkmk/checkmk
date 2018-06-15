


checkname = 'veritas_vcs'


info = [
    [None, 'ClusState', 'RUNNING'],#   .
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
]#.


discovery = {
    '.resource': [(u'nepharius_mrs',  None),#   .
                  (u'nepharius_dr',   None),
                  (u'cs_ip',          None),
                  (u'cs_proxy',       None),
                  (u'lan_nic',        None),
                  (u'lan_phantom',    None),
                  (u'omd_apache',     None),
                  (u'omd_appl',       None),
                  (u'omd_dg',         None),
                  (u'omd_proxy',      None),
                  (u'omd_srdf',       None),
                  (u'omd_uc4ps1_agt', None),
                  (u'omdp_ip',        None),
                  (u'omdp_mnt',       None),
                 ],
    '.servicegroup': [(u'ClusterService', None),
                      (u'nepharius',      None),
                      (u'lan',            None),
                      (u'omd',            None),
                     ],
    '.system': [(u'dave',   None),
                (u'stuart', None),
               ],
    '': [('minions', None),
        ],
}#.


checks = {
    '.resource': [#   .
        (u'nepharius_mrs',  "default", [(0, 'online, cluster: minions')]),
        (u'nepharius_dr',   "default", [(0, 'online, cluster: minions')]),
        (u'cs_ip',          "default", [(1, 'offline, cluster: minions')]),
        (u'cs_proxy',       "default", [(0, 'online, cluster: minions')]),
        (u'lan_nic',        "default", [(0, 'online, cluster: minions')]),
        (u'lan_phantom',    "default", [(0, 'online, cluster: minions')]),
        (u'omd_apache',     "default", [(0, 'online, cluster: minions')]),
        (u'omd_appl',       "default", [(0, 'online, cluster: minions')]),
        (u'omd_dg',         "default", [(0, 'online, cluster: minions')]),
        (u'omd_proxy',      "default", [(0, 'online, cluster: minions')]),
        (u'omd_srdf',       "default", [(0, 'online, cluster: minions')]),
        (u'omd_uc4ps1_agt', "default", [(0, 'online, cluster: minions')]),
        (u'omdp_ip',        "default", [(0, 'online, cluster: minions')]),
        (u'omdp_mnt',       "default", [(0, 'online, cluster: minions')]),
    ],
    '.servicegroup': [
        (u'ClusterService', "default", [(1, 'offline, cluster: minions')]),
        (u'nepharius',      "default", [(1, 'temporarily frozen'), (0, 'online, cluster: minions')]),
        (u'lan',            "default", [(0, 'online, cluster: minions')]),
        (u'omd',            "default", [(2, 'frozen'), (0, 'online, cluster: minions')]),
    ],
    '.system': [
        (u'dave',   "default", [(0, 'running, cluster: minions')]),
        (u'stuart', "default", [(0, 'running, cluster: minions')]),
    ],
    '': [
        ('minions', "default", [(0, 'running')]),
    ],
}#.


