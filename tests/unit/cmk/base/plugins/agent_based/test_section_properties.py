#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.api.agent_based.register import get_relevant_raw_sections


def test_all_sections_are_subscribed_by_some_plugin(fix_register):
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


def test_section_detection_uses_sysdescr_or_sysobjid(fix_register):
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
        ".1.3.6.1.4.1.2036.2.1.1.4.0": {"snmp_quantum_storage_info", "aruba_wlc_aps"},
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


def test_section_parse_function_does_something(fix_register):
    """We make sure that the parse function is not trivial

    To ease the learning curve when developing check plugins
    we allow to omit the parse_function (defaulting to lambda x: x).

    However this is allmost always a bad idea, so we make sure it
    does not happen in mainline code.
    """

    noop_code = (lambda x: x).__code__.co_code

    legacy_exceptions_for_easier_migration = {
        # snmp sections
        "infoblox_systeminfo",
        "inv_cisco_vlans",
        "juniper_info",
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
        "k8s_pods_cpu",
        "k8s_pods_fs",
        "k8s_pods_memory",
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
        "vxvm_enclosures",
        "vxvm_multipath",
        "vxvm_objstatus",
        "win_dhcp_pools",
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
        "ibm_svc_systemstats",
        "j4p_performance",
        "jolokia_metrics",
        "libelle_business_shadow",
        "msexch_dag",
        "netctr",
        "netif",
        "nvidia",
        "sap",
        "siemens_plc",
        "vms_diskstat",
        "vms_system",
        "winperf",
    }

    for name, snmp_section in fix_register.snmp_sections.items():
        assert (str(name) not in legacy_exceptions_for_easier_migration) is (
            snmp_section.parse_function.__code__.co_code != noop_code
        ), f"💚 The snmp section {name} now has a parse function! Remove it from the list above!"

    for name, agent_section in fix_register.agent_sections.items():
        assert (str(name) not in legacy_exceptions_for_easier_migration) is (
            agent_section.parse_function.__code__.co_code != noop_code
        ), f"💚 The agent section {name} now has a parse function! Remove it from the list above!"


def test_snmp_section_parse_function_deals_with_empty_input(fix_register):
    """We make sure that all parse functions can handle empty table data"""
    for section in fix_register.snmp_sections.values():
        _ = section.parse_function(len(section.trees) * [[]])
