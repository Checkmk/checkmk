import pytest
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


@pytest.mark.parametrize("info,settings,items", [
    ([], [], []),
    ([20 * [""]], [], []),
    ([20 * ["0"]], [], []),
    ([21 * [""]], [], []),
    ([21 * ["0"]], [], []),
    ([["1", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["1", "FOO-DUPLICATE", "6", "10", "1"] + 13 * ["0"] +
      ["FOO-ALIAS-DUPLICATE", "00:00:00:00:00:00"]], [], ["1"]),
    ([["1", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["2", "BAR", "6", "10", "1"] + 13 * ["0"] + ["BAR-ALIAS", "00:00:00:00:00:00"]
     ], [], ["1", "2"]),
    ([["1", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["2", "BAR", "6", "10", "1"] + 13 * ["0"] + ["BAR-ALIAS", "00:00:00:00:00:00"]], [{
          "use_desc": True
      }], ["FOO", "BAR"]),
    ([["1", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["2", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"]], [{
          "use_desc": True
      }], ["FOO 1", "FOO 2"]),
    ([["1", "FOO", "6", "10", "2"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["2", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"]], [{
          "use_desc": True
      }], ["FOO 2"]),
    ([["1", "FOO", "6", "10", "2"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["2", "FOO", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"],
      ["3", "BAR", "6", "10", "1"] + 13 * ["0"] + ["FOO-ALIAS", "00:00:00:00:00:00"]], [{
          "use_desc": True
      }, {
          "use_desc": True
      }], ["FOO 2", "BAR"]),
])
def test_if_inventory_if_common_discovered_items(check_manager, monkeypatch, info, settings, items):
    check = check_manager.get_check("if")
    monkeypatch.setitem(check.context, "host_extra_conf", lambda _, __: settings)
    monkeypatch.setitem(check.context, "_prepare_if_group_patterns_from_conf", lambda: {})
    discovered_items = [e[0] for e in check.run_discovery(info)]
    assert discovered_items == items
