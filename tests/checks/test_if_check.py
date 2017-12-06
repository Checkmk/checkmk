import pytest
import pprint
import ast
from testlib import cmk_path

# Mark all tests in this file as check related tests
pytestmark = pytest.mark.checks


# line in info:
# [NODE_INFO]
# ifIndex
# ifDescr
# ifType
# ifSpeed
# ifOperStatus
# ifInOctets
# inucast
# inmcast
# inbcast
# ifInDiscards
# ifInErrors
# ifOutOctets
# outucast
# outmcast
# outbcast
# ifOutDiscards
# ifOutErrors,
# ifOutQLen
# ifAlias
# ifPhysAddress


@pytest.mark.parametrize("info,inventory_if_rules,result", [
    ([], [], 0),
    ([20*[""]], [], 0),
    ([20*["0"]], [], 0),
    ([21*[""]], [], 0),
    ([21*["0"]], [], 0),
    ([["1", "EINS", "6", "10", "1"] + 13*["0"] + ["EINS-ALIAS", "00:00:00:00:00:00"]], [], 1),
    ([["1", "EINS", "6", "10", "2"] + 13*["0"] + ["EINS-ALIAS", "00:00:00:00:00:00"]], [], 0),
    ([["1", "EINS", "00000", "10", "1"] + 13*["0"] + ["EINS-ALIAS", "00:00:00:00:00:00"]], [], 0),
    ([["1", "EINS", "6", "10", "1"] + 13*["0"] + ["EINS-ALIAS", "00:00:00:00:00:00"],
      ["1", "EINS-DUPLICATE", "6", "10", "1"] + 13*["0",] + ["EINS-ALIAS-DUPLICATE", "00:00:00:00:00:00"]], [], 2),
])
def test_if_inventory_if_common_count_interfaces(check_manager, monkeypatch, info, inventory_if_rules, result):
    check = check_manager.get_check("if")
    #TODO How to handle several "host_extra_conf"s?
    #monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: inventory_if_rules)
    assert len(check.run_discovery(info)) == result
