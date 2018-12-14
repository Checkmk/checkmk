checkname = 'veritas_vcs'

info = [
    [None, 'ClusState', 'RUNNING'],
    [None, 'ClusterName', 'minions'],
    [None, '#System', 'Attribute', 'Value'],
    [None, 'dave', 'SysState', 'RUNNING'],
    [None, 'stuart', 'SysState', 'RUNNING'],
    [None, '#Group', 'Attribute', 'System', 'Value'],
    [None, 'ClusterService', 'State', 'stuart', '|OFFLINE|'],
    [None, 'bob1', 'State', 'stuart', '|OFFLINE|'],
    [None, 'bob2', 'State', 'stuart', '|OFFLINE|'],
    [None, 'bob3', 'State', 'stuart', '|OFFLINE|'],
    [None, 'bob4', 'State', 'stuart', '|OFFLINE|'],
    [None, 'bob5', 'State', 'stuart', '|OFFLINE|'],
    [None, 'agnes', 'State', 'stuart', '|ONLINE|'],
    [None, '#Resource', 'Attribute', 'System', 'Value'],
    [None, 'gru', 'State', 'stuart', 'ONLINE'],
    [None, 'bob1-db', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob1-dg', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob1-ip', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob1-mnt', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob1-nic-proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'bob1-vol', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob2-db', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob2-dg', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob2-ip', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob2-mnt', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob2-nic-proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'bob2-vol', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob3-db', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob3-dg', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob3-ip', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob3-mnt', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob3-nic-proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'bob3-vol', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob4-db', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob4-dg', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob4-ip', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob4-mnt', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob4-nic-proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'bob4-vol', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob5-db', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob5-dg', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob5-ip', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob5-mnt', 'State', 'stuart', 'OFFLINE'],
    [None, 'bob5-nic-proxy', 'State', 'stuart', 'ONLINE'],
    [None, 'bob5-vol', 'State', 'stuart', 'OFFLINE'],
    [None, 'agnes-nic', 'State', 'stuart', 'ONLINE'],
    [None, 'agnes-phantom', 'State', 'stuart', 'ONLINE'],
    [None, 'webip', 'State', 'stuart', 'OFFLINE'],
]

discovery = {
    'resource': [
        (u'gru', None),
        (u'bob1-db', None),
        (u'bob1-dg', None),
        (u'bob1-ip', None),
        (u'bob1-mnt', None),
        (u'bob1-nic-proxy', None),
        (u'bob1-vol', None),
        (u'bob2-db', None),
        (u'bob2-dg', None),
        (u'bob2-ip', None),
        (u'bob2-mnt', None),
        (u'bob2-nic-proxy', None),
        (u'bob2-vol', None),
        (u'bob3-db', None),
        (u'bob3-dg', None),
        (u'bob3-ip', None),
        (u'bob3-mnt', None),
        (u'bob3-nic-proxy', None),
        (u'bob3-vol', None),
        (u'bob4-db', None),
        (u'bob4-dg', None),
        (u'bob4-ip', None),
        (u'bob4-mnt', None),
        (u'bob4-nic-proxy', None),
        (u'bob4-vol', None),
        (u'bob5-db', None),
        (u'bob5-dg', None),
        (u'bob5-ip', None),
        (u'bob5-mnt', None),
        (u'bob5-nic-proxy', None),
        (u'bob5-vol', None),
        (u'agnes-nic', None),
        (u'agnes-phantom', None),
        (u'webip', None),
    ],
    'servicegroup': [
        (u'ClusterService', None),
        (u'bob1', None),
        (u'bob2', None),
        (u'bob3', None),
        (u'bob4', None),
        (u'bob5', None),
        (u'agnes', None),
    ],
    'system': [
        (u'dave', None),
        (u'stuart', None),
    ],
    '': [(u'minions', None),],
}

checks = {
    'resource': [
        (u'gru', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'bob1-db', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob1-dg', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob1-ip', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob1-mnt', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob1-nic-proxy', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'bob1-vol', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob2-db', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob2-dg', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob2-ip', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob2-mnt', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob2-nic-proxy', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'bob2-vol', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob3-db', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob3-dg', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob3-ip', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob3-mnt', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob3-nic-proxy', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'bob3-vol', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob4-db', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob4-dg', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob4-ip', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob4-mnt', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob4-nic-proxy', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'bob4-vol', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob5-db', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob5-dg', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob5-ip', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob5-mnt', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob5-nic-proxy', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'bob5-vol', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'agnes-nic', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'agnes-phantom', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
        (u'webip', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
    ],
    'servicegroup': [
        (u'ClusterService', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob1', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob2', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob3', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob4', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'bob5', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(1, 'offline, cluster: minions')]),
        (u'agnes', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'online, cluster: minions')]),
    ],
    'system': [
        (u'dave', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'running, cluster: minions')]),
        (u'stuart', {
            'map_frozen': {
                'frozen': 2,
                'temporarily frozen': 1
            },
            'map_states': {
                'FAULTED': 2,
                'RUNNING': 0,
                'OK': 0,
                'ONLINE': 0,
                'default': 1,
                'PARTIAL': 1,
                'OFFLINE': 1,
                'UNKNOWN': 3,
                'EXITED': 1
            }
        }, [(0, 'running, cluster: minions')]),
    ],
    '': [(u'minions', {
        'map_frozen': {
            'frozen': 2,
            'temporarily frozen': 1
        },
        'map_states': {
            'FAULTED': 2,
            'RUNNING': 0,
            'OK': 0,
            'ONLINE': 0,
            'default': 1,
            'PARTIAL': 1,
            'OFFLINE': 1,
            'UNKNOWN': 3,
            'EXITED': 1
        }
    }, [(0, 'running')]),],
}
