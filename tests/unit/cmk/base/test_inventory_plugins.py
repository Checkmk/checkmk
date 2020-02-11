import pytest
import cmk.base.inventory_plugins
from cmk.utils.exceptions import MKGeneralException


@pytest.mark.parametrize("inv_info,expected_order", [
    ({
        'a_plugin': {},
        'b_plugin': {}
    }, ['a_plugin', 'b_plugin']),
    ({
        'a_plugin': {
            'depends_on': ['b_plugin']
        },
        'b_plugin': {}
    }, ['b_plugin', 'a_plugin']),
])
def test_iteritems_sorted_by_dependency(monkeypatch, inv_info, expected_order):
    monkeypatch.setattr(cmk.base.inventory_plugins, "inv_info", inv_info)
    order = [item[0] for item in cmk.base.inventory_plugins.sorted_inventory_plugins()]
    assert order == expected_order


def test_iteritems_sorted_by_dependency_cyclic(monkeypatch):
    monkeypatch.setattr(
        cmk.base.inventory_plugins, "inv_info", {
            "a_plugin": {
                'depends_on': ["b_plugin"]
            },
            "b_plugin": {
                'depends_on': ["c_plugin"]
            },
            "c_plugin": {
                'depends_on': ["a_plugin"]
            },
        })
    with pytest.raises(MKGeneralException, match="cyclic plugin dependencies for '._plugin'"):
        list(cmk.base.inventory_plugins.sorted_inventory_plugins())


def test_iteritems_sorted_by_dependency_unknown(monkeypatch):
    monkeypatch.setattr(cmk.base.inventory_plugins, "inv_info", {
        "a_plugin": {
            'depends_on': ["whoopdeedoo"]
        },
    })
    with pytest.raises(MKGeneralException, match="unknown plugin dependency: 'whoopdeedoo'"):
        list(cmk.base.inventory_plugins.sorted_inventory_plugins())
