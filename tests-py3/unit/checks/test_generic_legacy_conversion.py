import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.base.check_api as check_api
from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    create_detect_spec,
    _explicit_conversions,
)
from cmk.base.api.agent_based.register.section_plugins_legacy import _create_snmp_trees

pytestmark = pytest.mark.checks

config.load_all_checks(check_api.get_check_api_context)


@pytest.mark.parametrize("name, scan_func", list(config.snmp_scan_functions.items()))
def test_snmp_scan_tranlation(name, scan_func):
    try:
        _ = create_detect_spec(name, scan_func)
    except NotImplementedError:
        # These are deliberatly ommitted.
        # TODO: We still need a solution for them.
        pass


@pytest.mark.parametrize("_name, snmp_info", list(config.snmp_info.items()))
def test_snmp_tree_tranlation(_name, snmp_info):
    _ = _create_snmp_trees(snmp_info)


@pytest.mark.parametrize("check_name, func_name", [
    ("if64_tplink", "has_ifHCInOctets"),
    ("fsc_subsystems", "_is_fsc_or_windows"),
    ("ucd_processes", "_is_ucd"),
    ("printer_pages", "scan_ricoh_printer"),
])
def test_explicit_conversion(check_manager, check_name, func_name):
    scan_func = check_manager.get_check(check_name).context[func_name]
    assert create_detect_spec("unit-test", scan_func) == _explicit_conversions(scan_func.__name__)
