import pytest  # type: ignore
from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual, \
                         CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks

#   .--Test info sections--------------------------------------------------.
#   |                _____         _     _        __                       |
#   |               |_   _|__  ___| |_  (_)_ __  / _| ___                  |
#   |                 | |/ _ \/ __| __| | | '_ \| |_ / _ \                 |
#   |                 | |  __/\__ \ |_  | | | | |  _| (_) |                |
#   |                 |_|\___||___/\__| |_|_| |_|_|  \___/                 |
#   |                                                                      |
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'

info_1 = [
    [None, 'ClusState', 'RUNNING'],  #   .
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
]  #.

info_2 = [
    [None, 'ClusState', 'RUNNING'],  #   .
    [None, 'ClusterName', 'minions'],
    [None, '#System', 'Attribute', 'Value'],
    [None, 'dave', 'SysState', 'RUNNING'],
    [None, 'stuart', 'SysState', 'RUNNING'],
    [None, '#Group', 'Attribute', 'System', 'Value'],
    [None, 'ClusterService', 'State', 'dave', '|ONLINE|'],
    [None, 'bob1', 'State', 'dave', '|ONLINE|'],
    [None, 'bob2', 'State', 'dave', '|ONLINE|'],
    [None, 'bob3', 'State', 'dave', '|ONLINE|'],
    [None, 'bob4', 'State', 'dave', '|PARTIAL|'],
    [None, 'bob5', 'State', 'dave', '|ONLINE|'],
    [None, 'agnes', 'State', 'dave', '|ONLINE|'],
    [None, '#Resource', 'Attribute', 'System', 'Value'],
    [None, 'gru', 'State', 'dave', 'ONLINE'],
    [None, 'bob1-db', 'State', 'dave', 'ONLINE'],
    [None, 'bob1-dg', 'State', 'dave', 'ONLINE'],
    [None, 'bob1-ip', 'State', 'dave', 'ONLINE'],
    [None, 'bob1-mnt', 'State', 'dave', 'ONLINE'],
    [None, 'bob1-nic-proxy', 'State', 'dave', 'ONLINE'],
    [None, 'bob1-vol', 'State', 'dave', 'ONLINE'],
    [None, 'bob2-db', 'State', 'dave', 'ONLINE'],
    [None, 'bob2-dg', 'State', 'dave', 'ONLINE'],
    [None, 'bob2-ip', 'State', 'dave', 'ONLINE'],
    [None, 'bob2-mnt', 'State', 'dave', 'ONLINE'],
    [None, 'bob2-nic-proxy', 'State', 'dave', 'ONLINE'],
    [None, 'bob2-vol', 'State', 'dave', 'ONLINE'],
    [None, 'bob3-db', 'State', 'dave', 'ONLINE'],
    [None, 'bob3-dg', 'State', 'dave', 'ONLINE'],
    [None, 'bob3-ip', 'State', 'dave', 'ONLINE'],
    [None, 'bob3-mnt', 'State', 'dave', 'ONLINE'],
    [None, 'bob3-nic-proxy', 'State', 'dave', 'ONLINE'],
    [None, 'bob3-vol', 'State', 'dave', 'ONLINE'],
    [None, 'bob4-db', 'State', 'dave', 'OFFLINE'],
    [None, 'bob4-dg', 'State', 'dave', 'ONLINE'],
    [None, 'bob4-ip', 'State', 'dave', 'OFFLINE'],
    [None, 'bob4-mnt', 'State', 'dave', 'ONLINE'],
    [None, 'bob4-nic-proxy', 'State', 'dave', 'ONLINE'],
    [None, 'bob4-vol', 'State', 'dave', 'ONLINE'],
    [None, 'bob5-db', 'State', 'dave', 'ONLINE'],
    [None, 'bob5-dg', 'State', 'dave', 'ONLINE'],
    [None, 'bob5-ip', 'State', 'dave', 'ONLINE'],
    [None, 'bob5-mnt', 'State', 'dave', 'ONLINE'],
    [None, 'bob5-nic-proxy', 'State', 'dave', 'ONLINE'],
    [None, 'bob5-vol', 'State', 'dave', 'ONLINE'],
    [None, 'agnes-nic', 'State', 'dave', 'ONLINE'],
    [None, 'agnes-phantom', 'State', 'dave', 'ONLINE'],
    [None, 'webip', 'State', 'dave', 'ONLINE']
]  #.

info_3 = [
    [None, 'ClusState', 'RUNNING'],  #   .
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
]  #.

items_1 = {
    '.resource': [
        u'gru',  #   .
        u'bob1-db',
        u'bob1-dg',
        u'bob1-ip',
        u'bob1-mnt',
        u'bob1-nic-proxy',
        u'bob1-vol',
        u'bob2-db',
        u'bob2-dg',
        u'bob2-ip',
        u'bob2-mnt',
        u'bob2-nic-proxy',
        u'bob2-vol',
        u'bob3-db',
        u'bob3-dg',
        u'bob3-ip',
        u'bob3-mnt',
        u'bob3-nic-proxy',
        u'bob3-vol',
        u'bob4-db',
        u'bob4-dg',
        u'bob4-ip',
        u'bob4-mnt',
        u'bob4-nic-proxy',
        u'bob4-vol',
        u'bob5-db',
        u'bob5-dg',
        u'bob5-ip',
        u'bob5-mnt',
        u'bob5-nic-proxy',
        u'bob5-vol',
        u'agnes-nic',
        u'agnes-phantom',
        u'webip',
    ],
    '.servicegroup': [
        u'ClusterService',
        u'bob1',
        u'bob2',
        u'bob3',
        u'bob4',
        u'bob5',
        u'agnes',
    ],
    '.system': [
        u'dave',
        u'stuart',
    ],
    '': ['minions',],
}  #.

items_2 = items_1

items_3 = {
    '.resource': [
        u'nepharius_mrs',  #   .
        u'nepharius_dr',
        u'cs_ip',
        u'cs_proxy',
        u'lan_nic',
        u'lan_phantom',
        u'omd_apache',
        u'omd_appl',
        u'omd_dg',
        u'omd_proxy',
        u'omd_srdf',
        u'omd_uc4ps1_agt',
        u'omdp_ip',
        u'omdp_mnt',
    ],
    '.servicegroup': [
        u'ClusterService',
        u'nepharius',
        u'lan',
        u'omd',
    ],
    '.system': [
        u'dave',
        u'stuart',
    ],
    '': ['minions',],
}  #.

results_1 = {
    '.resource': [  #   .
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
    ],
    '.servicegroup': [
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
    ],
    '.system': [
        [(0, 'running, cluster: minions')],
        [(0, 'running, cluster: minions')],
    ],
    '': [[(0, 'running')],],
}  #.

results_2 = {
    '.resource': [  #   .
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
    ],
    '.servicegroup': [
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'partial, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
    ],
    '.system': [
        [(0, 'running, cluster: minions')],
        [(0, 'running, cluster: minions')],
    ],
    '': [[(0, 'running')]],
}  #.

results_3 = {
    '.resource': [  #   .
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(1, 'offline, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
    ],
    '.servicegroup': [
        [(1, 'offline, cluster: minions')],
        [(1, 'temporarily frozen'), (0, 'online, cluster: minions')],
        [(0, 'online, cluster: minions')],
        [(2, 'frozen'), (0, 'online, cluster: minions')],
    ],
    '.system': [
        [(0, 'running, cluster: minions')],
        [(0, 'running, cluster: minions')],
    ],
    '': [[(0, 'running')],],
}  #.

#.
#   .--Test functions------------------------------------------------------.
#   |   _____         _      __                  _   _                     |
#   |  |_   _|__  ___| |_   / _|_   _ _ __   ___| |_(_) ___  _ __  ___     |
#   |    | |/ _ \/ __| __| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|    |
#   |    | |  __/\__ \ |_  |  _| |_| | | | | (__| |_| | (_) | | | \__ \    |
#   |    |_|\___||___/\__| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# TODO: If the check returned by the check manager is a subcheck,
# it is not aware of the parse function defined in the main check.
def _parse(check_manager, info):
    check = check_manager.get_check("veritas_vcs")
    return check.run_parse(info)


# DICSCOVERY
@pytest.mark.parametrize("info,items", [
    ([], []),
    (info_1, items_1),
    (info_2, items_2),
    (info_3, items_3),
])
def test_veritas_vcs_discovery_with_parse(check_manager, info, items):

    for subcheck in items:
        check = check_manager.get_check("veritas_vcs" + subcheck)
        parsed = _parse(check_manager, info)
        raw_result = check.run_discovery(parsed)
        result = DiscoveryResult(raw_result)
        result_expected = DiscoveryResult((i, None) for i in items[subcheck])
        assertDiscoveryResultsEqual(check, result, result_expected)


#   . CHECK resource
@pytest.mark.parametrize(
    "item,params,info,expected_result",
    [(i, "default", info_1, r) for i, r in zip(items_1['.resource'], results_1['.resource'])] + [
        (i, "default", info_2, r) for i, r in zip(items_2['.resource'], results_2['.resource'])
    ] + [(i, "default", info_3, r) for i, r in zip(items_3['.resource'], results_3['.resource'])])
def test_veritas_vcs_resource_with_parse(check_manager, item, params, info, expected_result):
    check = check_manager.get_check("veritas_vcs.resource")

    if params == "default":
        params = check.default_parameters()

    parsed = _parse(check_manager, info)
    result = CheckResult(check.run_check(item, params, parsed))
    e_result = CheckResult(expected_result)
    assertCheckResultsEqual(result, e_result)


#.


#   . CHECK servicegroup
@pytest.mark.parametrize("item,params,info,expected_result", [
    (i, "default", info_1, r) for i, r in zip(items_1['.servicegroup'], results_1['.servicegroup'])
] + [
    (i, "default", info_2, r) for i, r in zip(items_2['.servicegroup'], results_2['.servicegroup'])
] + [(i, "default", info_3, r) for i, r in zip(items_3['.servicegroup'], results_3['.servicegroup'])
    ])
def test_veritas_vcs_servicegroup_with_parse(check_manager, item, params, info, expected_result):
    check = check_manager.get_check("veritas_vcs.servicegroup")

    if params == "default":
        params = check.default_parameters()

    parsed = _parse(check_manager, info)
    raw_result = check.run_check(item, params, parsed)
    result = CheckResult(raw_result)
    result_expected = CheckResult(expected_result)
    assertCheckResultsEqual(result, result_expected)


#.


#   . CHECK system
@pytest.mark.parametrize(
    "item,params,info,expected_result",
    [(i, "default", info_1, r) for i, r in zip(items_1['.system'], results_1['.system'])] + [
        (i, "default", info_2, r) for i, r in zip(items_2['.system'], results_2['.system'])
    ] + [(i, "default", info_3, r) for i, r in zip(items_3['.system'], results_3['.system'])])
def test_veritas_vcs_system_with_parse(check_manager, item, params, info, expected_result):
    check = check_manager.get_check("veritas_vcs.system")

    if params == "default":
        params = check.default_parameters()

    parsed = _parse(check_manager, info)
    raw_result = check.run_check(item, params, parsed)
    result = CheckResult(raw_result)
    result_expected = CheckResult(expected_result)
    assertCheckResultsEqual(result, result_expected)


#.


#   . CHECK main
@pytest.mark.parametrize(
    "item,params,info,expected_result",
    [(i, "default", info_1, r) for i, r in zip(items_1[''], results_1[''])] + [
        (i, "default", info_2, r) for i, r in zip(items_2[''], results_2[''])
    ] + [(i, "default", info_3, r) for i, r in zip(items_3[''], results_3[''])])
def test_veritas_vcs_with_parse(check_manager, item, params, info, expected_result):
    check = check_manager.get_check("veritas_vcs")

    if params == "default":
        params = check.default_parameters()

    parsed = check.run_parse(info)
    raw_result = check.run_check(item, params, parsed)
    result = CheckResult(raw_result)
    result_expected = CheckResult(expected_result)
    assertCheckResultsEqual(result, result_expected)


#.
