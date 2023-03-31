#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.unit.conftest import FixRegister

from cmk.base.api.agent_based.register import get_relevant_raw_sections


def test_detect_spec_dedup(
    fix_register: FixRegister,
) -> None:
    """Test which snmp sections share a detect spec, but do not share the code for it

    If this test turns red, you have either
     a) deduplicated code (nice!)
     b) accidently changed a detect specification where you should have changed all of them
        -> please try a)!
    """
    plugins_by_detect_spec: dict[tuple[tuple[str, ...], ...], dict[int, list[str]]] = {}
    for snmp_section in fix_register.snmp_sections.values():
        plugins_by_detect_spec.setdefault(
            tuple(tuple(e) for e in snmp_section.detect_spec), {}
        ).setdefault(id(snmp_section.detect_spec), []).append(str(snmp_section.name))

    offenders: set[tuple[str, ...]] = {
        tuple(sorted([s for sections in values.values() for s in sections]))
        for _spec, values in plugins_by_detect_spec.items()
        if len(values) > 1
    }
    assert offenders == {
        ("alcatel_timetra_chassis", "alcatel_timetra_cpu"),
        ("apc_netbotz_fluid", "apc_netbotz_smoke"),
        ("apc_netbotz_other_sensors", "apc_netbotz_sensors"),
        ("apc_sts_inputs", "apc_sts_source"),
        ("arbor_peakflow_sp", "arbor_peakflow_sp_cpu_load"),
        ("arbor_peakflow_tms", "arbor_peakflow_tms_cpu_load"),
        ("arbor_pravail", "arbor_pravail_cpu_load"),
        ("artec_documents", "artec_temp"),
        ("bdt_tape_info", "bdt_tape_status"),
        ("bintec_brrp_status", "bintec_sensors"),
        ("blade_powerfan", "blade_powermod"),
        ("bluecoat_diskcpu", "bluecoat_sensors"),
        ("bluenet_meter", "bluenet_sensor"),
        ("cisco_asa_conn", "cisco_asa_connections"),
        ("dell_powerconnect_fans", "dell_powerconnect_psu"),
        ("docsis_channels_downstream", "docsis_channels_upstream"),
        ("emerson_stat", "emerson_temp"),
        ("fjdarye_pcie_flash_modules", "fjdarye_pools"),
        ("gude_humidity", "gude_temp"),
        ("h3c_lanswitch_cpu", "h3c_lanswitch_sensors"),
        ("hitachi_hus_dkc", "hitachi_hus_dku"),
        ("hp_fan", "hp_psu"),
        ("hp_hh3c_fan", "hp_hh3c_power"),
        ("hp_mcs_sensors", "hp_mcs_system"),
        ("hp_proliant_systeminfo", "hp_sts_drvbox"),
        ("huawei_wlc_aps", "huawei_wlc_devs"),
        ("hwg_humidity", "hwg_temp"),
        ("ibm_tl_changer_devices", "ibm_tl_media_access_devices"),
        ("if", "inv_if"),
        ("innovaphone_priports_l1", "innovaphone_priports_l2"),
        ("ipr400_in_voltage", "ipr400_temp"),
        ("juniper_trpz_aps", "juniper_trpz_aps_sessions"),
        ("netapp_cluster", "netapp_vfiler"),
        ("nimble_latency", "nimble_volumes"),
        ("packeteer_fan_status", "packeteer_ps_status"),
        ("poseidon_inputs", "poseidon_temp"),
        ("qlogic_sanbox", "qlogic_sanbox_fabric_element"),
        ("quantum_libsmall_door", "quantum_libsmall_status"),
        ("raritan_emx", "raritan_emx_sensors"),
        ("raritan_pdu_outletcount", "raritan_pdu_plugs"),
        ("raritan_px_outlets", "raritan_px_sensors"),
        ("safenet_hsm", "safenet_ntls"),
        ("sentry_pdu_outlets_v4", "sentry_pdu_v4"),
        ("sophos", "sophos_messages"),
        ("stormshield_cluster", "stormshield_cluster_node"),
        ("teracom_tcw241_analog", "teracom_tcw241_digital"),
        ("zebra_model", "zebra_printer_status"),
        ("adva_fsp_current", "adva_fsp_if", "adva_fsp_temp"),
        ("akcp_sensor_drycontact", "akcp_sensor_humidity", "akcp_sensor_temp"),
        ("arris_cmts_cpu", "arris_cmts_mem", "arris_cmts_temp"),
        ("aruba_aps", "aruba_clients", "aruba_cpu_util"),
        ("atto_fibrebridge_chassis", "atto_fibrebridge_fcport", "atto_fibrebridge_sas"),
        ("avaya_45xx_cpu", "avaya_45xx_fan", "avaya_45xx_temp"),
        ("barracuda_mail_latency", "barracuda_mailqueues", "barracuda_system_cpu_util"),
        ("bdtms_tape_info", "bdtms_tape_module", "bdtms_tape_status"),
        ("cisco_srst_call_legs", "cisco_srst_phones", "cisco_srst_state"),
        ("climaveneta_alarm", "climaveneta_fan", "climaveneta_temp"),
        ("dell_idrac_fans", "dell_idrac_power", "dell_idrac_raid"),
        ("f5_bigip_cluster_status_v11_2", "f5_bigip_vcmpfailover", "f5_bigip_vcmpguests"),
        ("hp_procurve_cpu", "hp_procurve_mem", "hp_procurve_sensors"),
        ("ispro_sensors_digital", "ispro_sensors_humid", "ispro_sensors_temp"),
        ("knuerr_rms_humidity", "knuerr_rms_temp", "knuerr_sensors"),
        ("mcafee_webgateway", "mcafee_webgateway_info", "mcafee_webgateway_misc"),
        ("netgear_fans", "netgear_powersupplies", "netgear_temp"),
        ("orion_backup", "orion_batterytest", "orion_system"),
        ("pfsense_counter", "pfsense_if", "pfsense_status"),
        ("qnap_disks", "qnap_fans", "qnap_hdd_temp"),
        ("quanta_fan", "quanta_temperature", "quanta_voltage"),
        ("ra32e_power", "ra32e_sensors", "ra32e_switch"),
        ("raritan_pdu_inlet", "raritan_pdu_inlet_summary", "raritan_px2_sensors"),
        ("sentry_pdu", "sentry_pdu_outlets", "sentry_pdu_systempower"),
        ("sni_octopuse_cpu", "sni_octopuse_status", "sni_octopuse_trunks"),
        ("sophos_cpu", "sophos_disk", "sophos_memory"),
        ("steelhead_connections", "steelhead_peers", "steelhead_status"),
        ("ups_cps_battery", "ups_cps_inphase", "ups_cps_outphase"),
        ("alcatel_cpu", "alcatel_fans", "alcatel_power", "alcatel_temp"),
        ("alcatel_cpu_aos7", "alcatel_fans_aos7", "alcatel_power_aos7", "alcatel_temp_aos7"),
        ("blade_bx_blades", "blade_bx_powerfan", "blade_bx_powermod", "blade_bx_temp"),
        (
            "fjdarye_controller_modules_flash",
            "fjdarye_expanders",
            "fjdarye_inlet_thermal_sensors",
            "fjdarye_thermal_sensors",
        ),
        (
            "ups_modulys_alarms",
            "ups_modulys_battery",
            "ups_modulys_inphase",
            "ups_modulys_outphase",
        ),
        ("vutlan_ems_humidity", "vutlan_ems_leakage", "vutlan_ems_smoke", "vutlan_ems_temp"),
        (  # these are the same "by chance"
            "fjdarye_channel_adapters",
            "fjdarye_channel_modules",
            "fjdarye_controller_enclosures",
            "fjdarye_controller_modules_memory",
            "fjdarye_disks",
            "fjdarye_summary_status",
            "fjdarye_system_capacitors",
        ),
        (  # these probably are the same due to rebranding? Only two different implementations.
            "fortiauthenticator_auth_fail",
            "fortiauthenticator_system",
            "primekey",
            "primekey_cpu_temperature",
            "primekey_data",
            "primekey_db_usage",
            "primekey_fan",
            "primekey_hsm_battery_voltage",
        ),
    }


def test_all_sections_are_subscribed_by_some_plugin(
    fix_register: FixRegister,
) -> None:
    """Test that all registered sections are subscribed to by some plugin

    We have very few sections (one at the time of this writing),
    that are not subscribed to by any plugin.
    We can afford to keep track of those.
    """
    all_section_names = set(fix_register.snmp_sections) | set(fix_register.agent_sections)

    subscribed_sections_names = set(
        get_relevant_raw_sections(
            check_plugin_names=fix_register.check_plugins,
            inventory_plugin_names=fix_register.inventory_plugins,
        )
    )

    unsubscribed_sections_names = {str(n) for n in all_section_names - subscribed_sections_names}

    assert unsubscribed_sections_names == {"labels"}


def test_section_detection_uses_sysdescr_or_sysobjid(
    fix_register: FixRegister,
) -> None:
    """Make sure the first OID is the system description or the system object ID

    Checking the system description or the system object ID first increases performance
    massively, because we can reduce the number of devices for which the subsequent OIDs
    are fetched, based on an OID information we fetch anyway.

    You should really have an exceptionally good reason to add something here.

    The known exceptions cannot easily be fixed, because introducing a too strict
    criterion is an incompatible change.
    In most of the cases I was unable to spot the identifying feature of the system
    description.
    """

    allowed_oids = {
        ".1.3.6.1.2.1.1.1.0",  # system description
        ".1.3.6.1.2.1.1.2.0",  # system object ID
    }

    known_exceptions = {
        ".1.3.6.1.2.1.2.2.1.*": {"if", "inv_if"},
        ".1.3.6.1.2.1.25.1.1.0": {"hr_cpu", "hr_fs", "hr_ps"},
        ".1.3.6.1.2.1.31.1.1.1.6.*": {"if64", "if64adm"},
        ".1.3.6.1.2.1.43.*": {
            "printer_alerts",
            "printer_input",
            "printer_output",
            "printer_pages",
            "printer_supply",
        },
        ".1.3.6.1.2.1.47.1.1.1.1.*": {"snmp_extended_info"},
        ".1.3.6.1.2.1.105.1.3.1.1.*": {"pse_poe"},
        ".1.3.6.1.4.1.14848.2.1.1.1.0": {"etherbox"},
        ".1.3.6.1.4.1.2036.2.1.1.4.0": {"snmp_quantum_storage_info"},
        ".1.3.6.1.4.1.232.2.2.4.2.0": {
            "hp_proliant_cpu",
            "hp_proliant_da_cntlr",
            "hp_proliant_da_phydrv",
            "hp_proliant_fans",
            "hp_proliant_mem",
            "hp_proliant_power",
            "hp_proliant_psu",
            "hp_proliant_raid",
            "hp_proliant_systeminfo",
            "hp_proliant_temp",
            "hp_sts_drvbox",
        },
        ".1.3.6.1.4.1.30155.2.1.1.0": {"openbsd_sensors"},
        ".1.3.6.1.4.1.6302.2.1.1.1.0": {"emerson_stat", "emerson_temp"},
        ".1.3.6.1.4.1.674.*": {
            "dell_compellent_controller",
            "dell_compellent_disks",
            "dell_compellent_enclosure",
            "dell_compellent_folder",
            "dell_hw_info",
        },
    }

    for section in fix_register.snmp_sections.values():
        for (first_checked_oid, *_rest1), *_rest2 in (  #
            criterion for criterion in section.detect_spec if criterion  #
        ):
            if first_checked_oid in allowed_oids:
                continue
            assert str(section.name) in known_exceptions.get(
                first_checked_oid, ()
            ), f"""
            If you've made it here, you have added a case to the known exceptions above.
            Even worse: You may have added an OID to the list of OIDs that are fetched
            from *all SNMP devices* known to the Checkmk site. Please reconsider!

            First OID fetched by {section.name}: {first_checked_oid}
            """


def test_section_parse_function_does_something(fix_register: FixRegister) -> None:
    """We make sure that the parse function is not trivial

    To ease the learning curve when developing check plugins
    we allow to omit the parse_function (defaulting to lambda x: x).

    However this is allmost always a bad idea, so we make sure it
    does not happen in mainline code.
    """

    noop_code = (lambda x: x).__code__.co_code

    for name, snmp_section in fix_register.snmp_sections.items():
        assert snmp_section.parse_function.__code__.co_code != noop_code

    legacy_exceptions_for_easier_migration = {
        # agent sections
        "3ware_disks",
        "3ware_info",
        "3ware_units",
        "ad_replication",
        "aix_lvm",
        "aix_multipath",
        "appdynamics_memory",
        "appdynamics_sessions",
        "appdynamics_web_container",
        "arc_raid_status",
        "arcserve_backup",
        "citrix_serverload",
        "citrix_sessions",
        "db2_mem",
        "db2_version",
        "dmi_sysinfo",
        "drbd",
        "emcvnx_hwstatus",
        "emcvnx_writecache",
        "esx_vsphere_sensors",
        "filehandler",
        "fsc_ipmi_mem_status",
        "heartbeat_nodes",
        "hivemanager_devices",
        "hpux_fchba",
        "hpux_lvm",
        "hpux_multipath",
        "hpux_serviceguard",
        "hyperv_checkpoints",
        "ibm_svc_eventlog",
        "ibm_svc_system",
        "innovaphone_channels",
        "innovaphone_cpu",
        "innovaphone_licenses",
        "innovaphone_mem",
        "innovaphone_temp",
        "ironport_misc",
        "jar_signature",
        "logins",
        "lvm_vgs",
        "mailman_lists",
        "mongodb_asserts",
        "mongodb_connections",
        "mongodb_flushing",
        "mongodb_instance",
        "mongodb_locks",
        "mounts",
        "mq_queues",
        "msexch_replhealth",
        "msoffice_serviceplans",
        "mssql_versions",
        "netapp_api_cluster",
        "netapp_api_connection",
        "netapp_api_info",
        "netapp_api_status",
        "netapp_api_vf_status",
        "nfsexports",
        "openvpn_clients",
        "oracle_crs_version",
        "oracle_crs_voting",
        "oracle_jobs",
        "oracle_locks",
        "oracle_logswitches",
        "oracle_longactivesessions",
        "oracle_recovery_area",
        "oracle_recovery_status",
        "oracle_rman_backups",
        "oracle_version",
        "plesk_backups",
        "plesk_domains",
        "qmail_stats",
        "sansymphony_alerts",
        "sansymphony_ports",
        "sansymphony_serverstatus",
        "sap_hana_filesystem",
        "sap_hana_full_backup",
        "sap_hana_mem",
        "sap_hana_process_list",
        "sap_hana_version",
        "sap_state",
        "siemens_plc_cpu_state",
        "solaris_multipath",
        "solaris_prtdiag_status",
        "splunk_alerts",
        "statgrab_cpu",
        "sylo",
        "symantec_av_progstate",
        "symantec_av_quarantine",
        "symantec_av_updates",
        "tsm_drives",
        "tsm_paths",
        "tsm_sessions",
        "ucs_bladecenter_topsystem",
        "unitrends_backup",
        "unitrends_replication",
        "vbox_guest",
        "veeam_jobs",
        "vms_queuejobs",
        "vms_users",
        "vnx_version",
        "vxvm_objstatus",
        "windows_broadcom_bonding",
        "windows_multipath",
        "winperf_mem",
        "winperf_ts_sessions",
        "wmic_process",
        "dmraid",
        "emcvnx_raidgroups",
        "hpux_tunables",
        "ibm_svc_enclosurestats",
        "ibm_svc_nodestats",
        "j4p_performance",
        "jolokia_metrics",
        "libelle_business_shadow",
        "msexch_dag",
        "netctr",
        "netif",
        "nvidia",
        "siemens_plc",
        "vms_system",
        "winperf",
    }

    for name, agent_section in fix_register.agent_sections.items():
        assert (str(name) not in legacy_exceptions_for_easier_migration) is (
            agent_section.parse_function.__code__.co_code != noop_code
        ), f"💚 The agent section {name} now has a parse function! Remove it from the list above!"


def test_snmp_section_parse_function_deals_with_empty_input(
    fix_register: FixRegister,
) -> None:
    """We make sure that all parse functions can handle empty table data"""
    for section in fix_register.snmp_sections.values():
        _ = section.parse_function(len(section.trees) * [[]])
