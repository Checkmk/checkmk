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

KNOWN_FAILURES = {
    'blade_bays',
    'blade_blades',
    'blade_blowers',
    'blade_health',
    'blade_mediatray',
    'blade_powerfan',
    'blade_powermod',
    'checkpoint_connections',
    'checkpoint_fan',
    'checkpoint_firewall',
    'checkpoint_ha_problems',
    'checkpoint_ha_status',
    'checkpoint_memory',
    'checkpoint_packets',
    'checkpoint_powersupply',
    'checkpoint_svn_status',
    'checkpoint_temp',
    'checkpoint_tunnels',
    'checkpoint_voltage',
    'cisco_mem_asa',
    'cisco_mem_asa64',
    'f5_bigip_cluster',
    'f5_bigip_cluster_status',
    'f5_bigip_cluster_status_v11_2',
    'f5_bigip_cluster_v11',
    'f5_bigip_vcmpfailover',
    'f5_bigip_vcmpguests',
    'hr_mem',
    'if',
    'if64',
    'if64adm',
    'if_brocade',
    'if_lancom',
    'printer_pages',
    'ucd_mem',
}


@pytest.mark.parametrize("name, scan_func", list(config.snmp_scan_functions.items()))
def test_snmp_scan_tranlation(name, scan_func):

    if name in KNOWN_FAILURES:
        with pytest.raises(NotImplementedError):
            _ = create_detect_spec(name, scan_func)
    else:
        _ = create_detect_spec(name, scan_func)


@pytest.mark.parametrize("_name, snmp_info", list(config.snmp_info.items()))
def test_snmp_tree_tranlation(_name, snmp_info):
    _ = _create_snmp_trees(snmp_info)


@pytest.mark.parametrize("check_name, func_name", [
    ("if64_tplink", "has_ifHCInOctets"),
    ("fsc_subsystems", "_is_fsc_or_windows"),
    ("ucd_processes", "_is_ucd"),
    ("printer_pages", "scan_ricoh_printer"),
    ("fsc_temp", "is_fsc"),
    ("df_netapp32", "is_netapp_filer"),
    ("cisco_cpu", "_has_table_8"),
    ("cisco_cpu", "_is_cisco"),
    ("cisco_cpu", "_is_cisco_nexus"),
])
def test_explicit_conversion(check_manager, check_name, func_name):
    scan_func = check_manager.get_check(check_name).context[func_name]
    assert create_detect_spec("unit-test", scan_func) == _explicit_conversions(scan_func.__name__)
