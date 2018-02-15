import pytest
import checktestlib

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

node1 = [
    ["ClusState", "RUNNING"],
    ["ClusterName", "foocluster"],
    ["#System", "Attribute", "Value"],
    ["bar", "SysState", "RUNNING"],
    ["baz", "SysState", "RUNNING"],
    ["#Group", "Attribute", "System", "Value"],
    ["ClusterService", "State", "baz", "|OFFLINE|"],
    ["something1", "State", "baz", "|OFFLINE|"],
    ["something2", "State", "baz", "|OFFLINE|"],
    ["something3", "State", "baz", "|OFFLINE|"],
    ["otherthing1", "State", "baz", "|ONLINE|"],
    ["#Resource", "Attribute", "System", "Value"],
    ["minerals", "State", "baz", "ONLINE"],
    ["vespgas", "State", "baz", "OFFLINE"],
]

info1= [ [None] + line for line in node1 ]

#.
#   .--Test functions------------------------------------------------------.
#   |   _____         _      __                  _   _                     |
#   |  |_   _|__  ___| |_   / _|_   _ _ __   ___| |_(_) ___  _ __  ___     |
#   |    | |/ _ \/ __| __| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|    |
#   |    | |  __/\__ \ |_  |  _| |_| | | | | (__| |_| | (_) | | | \__ \    |
#   |    |_|\___||___/\__| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

@pytest.mark.parametrize("info,predicate",[
    (info1, lambda result: ("foocluster", None) in result),
])
def test_veritas_vcs_discovery_with_parse(check_manager, info, predicate):
    check = check_manager.get_check("veritas_vcs")
    result = checktestlib.DiscoveryResult(check.run_discovery(check.run_parse(info)))
    assert predicate(result)
