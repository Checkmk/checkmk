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
    'alcatel_cpu',
    'alcatel_cpu_aos7',
    'alcatel_fans',
    'alcatel_fans_aos7',
    'alcatel_power',
    'alcatel_power_aos7',
    'alcatel_temp',
    'alcatel_temp_aos7',
    'blade_bays',
    'blade_blades',
    'blade_blowers',
    'blade_health',
    'blade_mediatray',
    'blade_powerfan',
    'blade_powermod',
    'bvip_fans',
    'bvip_info',
    'bvip_link',
    'bvip_poe',
    'bvip_temp',
    'bvip_util',
    'bvip_video_alerts',
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
    'cisco_cpu',
    'cisco_cpu_memory',
    'cisco_cpu_multiitem',
    'cisco_mem_asa',
    'cisco_mem_asa64',
    'cisco_nexus_cpu',
    'cisco_oldcpu',
    'docsis_channels_downstream',
    'docsis_channels_upstream',
    'docsis_cm_status',
    'domino_info',
    'domino_mailqueues',
    'domino_tasks',
    'domino_transactions',
    'domino_users',
    'f5_bigip_cluster',
    'f5_bigip_cluster_status',
    'f5_bigip_cluster_status_v11_2',
    'f5_bigip_cluster_v11',
    'f5_bigip_vcmpfailover',
    'f5_bigip_vcmpguests',
    'genua_carp',
    'genua_fan',
    'genua_pfstate',
    'genua_state_correlation',
    'genua_vpn',
    'hitachi_hnas_bossock',
    'hitachi_hnas_cifs',
    'hitachi_hnas_cpu',
    'hitachi_hnas_drives',
    'hitachi_hnas_fan',
    'hitachi_hnas_fc_if',
    'hitachi_hnas_fpga',
    'hitachi_hnas_pnode',
    'hitachi_hnas_psu',
    'hitachi_hnas_quorumdevice',
    'hitachi_hnas_span',
    'hitachi_hnas_temp',
    'hitachi_hnas_vnode',
    'hitachi_hnas_volume',
    'hp_fan',
    'hp_psu',
    'hr_mem',
    'if',
    'if64',
    'if64adm',
    'if_brocade',
    'if_lancom',
    'printer_pages',
    'ucd_mem',
    'ups_bat_temp',
    'ups_capacity',
    'ups_in_freq',
    'ups_in_voltage',
    'ups_out_load',
    'ups_out_voltage',
    'ups_power',
    'ups_test',
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
])
def test_explicit_conversion(check_manager, check_name, func_name):
    scan_func = check_manager.get_check(check_name).context[func_name]
    assert create_detect_spec("unit-test", scan_func) == _explicit_conversions(scan_func.__name__)
