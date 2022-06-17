#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Type

import pytest

import cmk.utils.version as cmk_version

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato
import cmk.gui.watolib.rulespecs
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.plugins.wato.utils import register_check_parameters, TimeperiodValuespec
from cmk.gui.valuespec import Dictionary, FixedValue, TextInput, Tuple, ValueSpec
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.rulespec_groups import RulespecGroupEnforcedServices
from cmk.gui.watolib.rulespecs import (
    CheckTypeGroupSelection,
    get_rulegroup,
    HostRulespec,
    main_module_from_rulespec_group_name,
    ManualCheckParameterRulespec,
    MatchItemGeneratorRules,
    register_rule,
    register_rulegroup,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
    RulespecGroupRegistry,
    RulespecRegistry,
    RulespecSubGroup,
)
from cmk.gui.watolib.search import MatchItem


def test_rulespec_sub_group() -> None:
    class TestGroup(RulespecGroup):
        @property
        def name(self) -> str:
            return "main_group"

        @property
        def title(self) -> str:
            return "Title"

        @property
        def help(self):
            return "help text"

    class TestSubGroup(RulespecSubGroup):
        @property
        def main_group(self) -> Type[RulespecGroup]:
            return TestGroup

        @property
        def sub_group_name(self) -> str:
            return "sub_group"

        @property
        def title(self) -> str:
            return "Sub"

    test_sub_group = TestSubGroup()
    assert test_sub_group.name == "main_group/sub_group"
    assert test_sub_group.title == "Sub"


def test_legacy_register_rulegroup(monkeypatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )
    register_rulegroup("abc", "A B C", "abc 123")

    group = get_rulegroup("abc")
    assert isinstance(group, RulespecGroup)
    assert group.name == "abc"
    assert group.title == "A B C"
    assert group.help == "abc 123"


def test_legacy_get_not_existing_rulegroup(monkeypatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )

    group = get_rulegroup("xyz")
    assert isinstance(group, cmk.gui.watolib.rulespecs.RulespecGroup)
    assert group.name == "xyz"
    assert group.title == "xyz"
    assert group.help is None


def test_legacy_get_not_existing_rule_sub_group(monkeypatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )

    group = get_rulegroup("xyz/Abc, xxx ding./aaa")
    assert isinstance(group, RulespecSubGroup)
    assert group.name == "xyz/abcxxxdingaaa"
    assert group.title == "Abc, xxx ding./aaa"
    assert group.help is None


# These tests make adding new elements needlessly painful.
# Skip pending discussion with development team.
@pytest.mark.skip
def test_grouped_rulespecs() -> None:
    by_group = {
        "static/networking": [
            "static_checks:mtr",
            "static_checks:palo_alto_sessions",
            "static_checks:fortinet_signatures",
            "static_checks:huawei_osn_laser",
            "static_checks:brocade_optical",
            "static_checks:fortigate_sessions",
            "static_checks:fortigate_node_sessions",
            "static_checks:cisco_asa_failover",
            "static_checks:threepar_ports",
            "static_checks:ipsecvpn",
            "static_checks:hp_hh3c_ext_states",
            "static_checks:fortisandbox_queues",
            "static_checks:cisco_stack",
            "static_checks:viprinet_router",
            "static_checks:docsis_channels_upstream",
            "static_checks:docsis_channels_downstream",
            "static_checks:docsis_cm_status",
            "static_checks:vpn_tunnel",
            "static_checks:lsnat",
            "static_checks:enterasys_powersupply",
            "static_checks:hivemanager_devices",
            "static_checks:hivemanager_ng_devices",
            "static_checks:wlc_clients",
            "static_checks:cisco_wlc",
            "static_checks:tcp_conn_stats",
            "static_checks:tcp_connections",
            "static_checks:bonding",
            "static_checks:if",
            "static_checks:fcp",
            "static_checks:signal_quality",
            "static_checks:cisco_ip_sla",
            "static_checks:cisco_qos",
            "static_checks:mem_cluster",
            "static_checks:cpu_utilization_cluster",
            "static_checks:adva_ifs",
            "static_checks:bluecat_ntp",
            "static_checks:bluecat_dhcp",
            "static_checks:bluecat_command_server",
            "static_checks:bluecat_dns",
            "static_checks:bluecat_ha",
            "static_checks:steelhead_connections",
            "static_checks:k8s_if",
        ],
        "eventconsole": [
            "extra_host_conf:_ec_event_limit",
            "active_checks:mkevents",
            "extra_host_conf:_ec_contact",
            "extra_service_conf:_ec_contact",
        ],
        "agents/generic_options": [
            "agent_config:only_from",
            "agent_config:package_name",
            "agent_config:agent_paths",
            "agent_config:real_time_checks",
            "agent_config:mrpe",
            "agent_config:custom_files",
        ],
        "agents/windows_agent": [
            "agent_config:logging",
            "agent_config:firewall",
            "agent_config:win_controller",
            "agent_config:win_clean_uninstall",
            "agent_config:win_exe_suffixes",
            "agent_config:win_agent_sections",
            "agent_config:win_agent_disabled_sections",
            "agent_config:win_script_async",
            "agent_config:win_script_timeout",
            "agent_config:win_script_cache_age",
            "agent_config:win_script_retry_count",
            "agent_config:win_script_execution",
            "agent_config:win_set_wmi_timeout",
            "agent_config:win_ps",
            "agent_config:win_openhardwaremonitor",
            "agent_config:win_printers",
            "agent_config:mcafee_av_client",
        ],
        "agents/windows_modules": [
            "agent_config:install_python",
        ],
        "datasource_programs": [
            "datasource_programs",
            "special_agents:ddn_s2a",
            "special_agents:kubernetes",
            "special_agents:vsphere",
            "special_agents:hp_msa",
            "special_agents:ipmi_sensors",
            "special_agents:netapp",
            "special_agents:activemq",
            "special_agents:emcvnx",
            "special_agents:ibmsvc",
            "special_agents:random",
            "special_agents:acme_sbc",
            "special_agents:fritzbox",
            "special_agents:innovaphone",
            "special_agents:hivemanager",
            "special_agents:hivemanager_ng",
            "special_agents:allnet_ip_sensoric",
            "special_agents:ucs_bladecenter",
            "special_agents:siemens_plc",
            "special_agents:ruckus_spot",
            "special_agents:appdynamics",
            "special_agents:jolokia",
            "special_agents:tinkerforge",
            "special_agents:prism",
            "special_agents:3par",
            "special_agents:storeonce",
            "special_agents:salesforce",
            "special_agents:azure",
            "special_agents:bi",
            "special_agents:aws",
            "special_agents:vnx_quotas",
        ],
        "checkparams/networking": [
            "ping_levels",
            "checkgroup_parameters:mtr",
            "checkgroup_parameters:palo_alto_sessions",
            "checkgroup_parameters:fortinet_signatures",
            "checkgroup_parameters:huawei_osn_laser",
            "checkgroup_parameters:brocade_optical",
            "checkgroup_parameters:fortigate_sessions",
            "checkgroup_parameters:fortigate_node_sessions",
            "checkgroup_parameters:cisco_asa_failover",
            "checkgroup_parameters:threepar_ports",
            "checkgroup_parameters:ipsecvpn",
            "checkgroup_parameters:hp_hh3c_ext_states",
            "checkgroup_parameters:fortisandbox_queues",
            "checkgroup_parameters:cisco_stack",
            "checkgroup_parameters:viprinet_router",
            "checkgroup_parameters:docsis_channels_upstream",
            "checkgroup_parameters:docsis_channels_downstream",
            "checkgroup_parameters:docsis_cm_status",
            "checkgroup_parameters:vpn_tunnel",
            "checkgroup_parameters:lsnat",
            "checkgroup_parameters:enterasys_powersupply",
            "checkgroup_parameters:hivemanager_devices",
            "checkgroup_parameters:hivemanager_ng_devices",
            "checkgroup_parameters:wlc_clients",
            "checkgroup_parameters:cisco_wlc",
            "checkgroup_parameters:tcp_conn_stats",
            "checkgroup_parameters:bonding",
            "checkgroup_parameters:if",
            "checkgroup_parameters:fcp",
            "checkgroup_parameters:signal_quality",
            "checkgroup_parameters:cisco_ip_sla",
            "checkgroup_parameters:cisco_qos",
            "if_groups",
            "if_disable_if64_hosts",
            "checkgroup_parameters:k8s_if",
            "checkgroup_parameters:adva_ifs",
            "checkgroup_parameters:bluecat_ntp",
            "checkgroup_parameters:bluecat_dhcp",
            "checkgroup_parameters:bluecat_command_server",
            "checkgroup_parameters:bluecat_dns",
            "checkgroup_parameters:bluecat_ha",
            "checkgroup_parameters:steelhead_connections",
        ],
        "static/printers": [
            "static_checks:printer_supply",
            "static_checks:cups_queues",
            "static_checks:windows_printer_queues",
            "static_checks:printer_input",
            "static_checks:printer_output",
        ],
        "static/applications": [
            "static_checks:f5_bigip_snat",
            "static_checks:veritas_vcs",
            "static_checks:f5_bigip_vserver",
            "static_checks:cluster_status",
            "static_checks:local",
            "static_checks:threepar_remotecopy",
            "static_checks:livestatus_status",
            "static_checks:ad_replication",
            "static_checks:mq_queues",
            "static_checks:sshd_config",
            "static_checks:websphere_mq",
            "static_checks:websphere_mq_channels",
            "static_checks:websphere_mq_manager",
            "static_checks:websphere_mq_instance",
            "static_checks:plesk_backups",
            "static_checks:firewall_if",
            "static_checks:kaspersky_av_client",
            "static_checks:mcafee_av_client",
            "static_checks:mcafee_web_gateway",
            "static_checks:mcafee_web_gateway_misc",
            "static_checks:mcafee_emailgateway_bridge",
            "static_checks:pfsense_counter",
            "static_checks:lnx_quota",
            "static_checks:ruckus_mac",
            "static_checks:ruckus_ap",
            "static_checks:esx_licenses",
            "static_checks:ibmsvc_licenses",
            "static_checks:citrix_licenses",
            "static_checks:rds_licenses",
            "static_checks:win_license",
            "static_checks:citrix_sessions",
            "static_checks:citrix_state",
            "static_checks:mssql_stats",
            "static_checks:mssql_instance",
            "static_checks:mssql_databases",
            "static_checks:mssql_connections",
            "static_checks:varnish_cache",
            "static_checks:varnish_client",
            "static_checks:varnish_backend",
            "static_checks:varnish_fetch",
            "static_checks:varnish_esi",
            "static_checks:varnish_objects",
            "static_checks:varnish_worker",
            "static_checks:varnish_cache_hit_ratio",
            "static_checks:varnish_backend_success_ratio",
            "static_checks:varnish_worker_thread_ratio",
            "static_checks:clr_memory",
            "static_checks:skype_mobile",
            "static_checks:skype_conferencing",
            "static_checks:skype_sip",
            "static_checks:skype_mediation_server",
            "static_checks:skype_xmpp",
            "static_checks:skype_edgeauth",
            "static_checks:acme_certificates",
            "static_checks:acme_sbc_snmp",
            "static_checks:skype",
            "static_checks:skype_proxy",
            "static_checks:skype_edge",
            "static_checks:ps",
            "static_checks:generic_number",
            "static_checks:generic_rate",
            "static_checks:generic_string",
            "static_checks:jvm_uptime",
            "static_checks:k8s_nodes",
            "static_checks:k8s_resources",
            "static_checks:k8s_pods_cpu",
            "static_checks:k8s_pods_memory",
            "static_checks:k8s_pods_fs",
            "static_checks:k8s_roles",
            "static_checks:netapp_systemtime",
            "static_checks:jvm_sessions",
            "static_checks:jvm_requests",
            "static_checks:jvm_queue",
            "static_checks:jvm_memory",
            "static_checks:safenet_hsm_operstats",
            "static_checks:safenet_hsm_eventstats",
            "static_checks:safenet_ntls_links",
            "static_checks:safenet_ntls_clients",
            "static_checks:fireeye_active_vms",
            "static_checks:fireeye_lic",
            "static_checks:fireeye_quarantine",
            "static_checks:fireeye_mailq",
            "static_checks:fireeye_mail",
            "static_checks:oracle_logswitches",
            "static_checks:systemd_services",
            "static_checks:hacmp_resources",
            "static_checks:webserver",
            "static_checks:aws_costs_and_usage",
            "static_checks:aws_ec2_cpu_credits",
            "static_checks:aws_rds_cpu_credits",
            "static_checks:aws_elb_backend_connection_errors",
            "static_checks:aws_elb_healthy_hosts",
            "static_checks:aws_elb_http",
            "static_checks:aws_elb_latency",
            "static_checks:aws_elb_statistics",
            "static_checks:azure_agent_info",
            "static_checks:azure_databases",
            "static_checks:azure_storageaccounts",
            "static_checks:azure_vms",
            "static_checks:azure_vms_summary",
            "static_checks:azure_virtualnetworkgateways",
            "static_checks:apache_status",
            "static_checks:saprouter_cert_age",
            "static_checks:sap_dialog",
            "static_checks:nginx_status",
            "static_checks:sles_license",
            "static_checks:msx_info_store",
            "static_checks:msx_rpcclientaccess",
            "static_checks:msx_database",
            "static_checks:msx_queues",
            "static_checks:msexch_copyqueue",
            "static_checks:services_summary",
            "static_checks:solaris_services_summary",
            "static_checks:esx_vsphere_objects",
            "static_checks:esx_vsphere_objects_count",
            "static_checks:oracle_tablespaces",
            "static_checks:oracle_processes",
            "static_checks:oracle_recovery_area",
            "static_checks:oracle_dataguard_stats",
            "static_checks:oracle_undostat",
            "static_checks:oracle_rman",
            "static_checks:oracle_recovery_status",
            "static_checks:oracle_jobs",
            "static_checks:oracle_instance",
            "static_checks:oracle_sql",
            "static_checks:asm_diskgroup",
            "static_checks:mssql_backup",
            "static_checks:mssql_backup_per_type",
            "static_checks:mssql_file_sizes",
            "static_checks:mssql_tablespaces",
            "static_checks:mssql_page_activity",
            "static_checks:mssql_transactionlogs",
            "static_checks:mssql_datafiles",
            "static_checks:vm_snapshots",
            "static_checks:veeam_backup",
            "static_checks:backup_timemachine",
            "static_checks:job",
            "static_checks:mssql_counters_locks",
            "static_checks:mssql_blocked_sessions",
            "static_checks:mssql_instance_blocked_sessions",
            "static_checks:mysql_sessions",
            "static_checks:mysql_innodb_io",
            "static_checks:mysql_connections",
            "static_checks:mysql_slave",
            "static_checks:db_bloat",
            "static_checks:db_connections",
            "static_checks:postgres_locks",
            "static_checks:postgres_maintenance",
            "static_checks:f5_connections",
            "static_checks:cisco_fw_connections",
            "static_checks:checkpoint_connections",
            "static_checks:checkpoint_packets",
            "static_checks:f5_pools",
            "static_checks:mysql_db_size",
            "static_checks:postgres_sessions",
            "static_checks:postgres_instance_sessions",
            "static_checks:asa_svc_sessions",
            "static_checks:oracle_sessions",
            "static_checks:oracle_locks",
            "static_checks:oracle_longactivesessions",
            "static_checks:postgres_stat_database",
            "static_checks:win_dhcp_pools",
            "static_checks:vms_procs",
            "static_checks:mailqueue_length",
            "static_checks:mail_queue_length",
            "static_checks:mail_latency",
            "static_checks:services",
            "static_checks:solaris_services",
            "static_checks:winperf_ts_sessions",
            "static_checks:mbg_lantime_state",
            "static_checks:sansymphony_pool",
            "static_checks:sansymphony_alerts",
            "static_checks:jvm_threads",
            "static_checks:sym_brightmail_queues",
            "static_checks:db2_logsize",
            "static_checks:db2_sortoverflow",
            "static_checks:db2_tablespaces",
            "static_checks:db2_connections",
            "static_checks:db2_counters",
            "static_checks:db2_backup",
            "static_checks:db2_mem",
            "static_checks:windows_updates",
            "static_checks:synology_update",
            "static_checks:antivir_update_age",
            "static_checks:logwatch_ec",
            "static_checks:wmic_process",
            "static_checks:citrix_load",
            "static_checks:jvm_gc",
            "static_checks:jvm_tp",
            "static_checks:docker_node_containers",
            "static_checks:docker_node_disk_usage",
            "static_checks:domino_tasks",
            "static_checks:domino_mailqueues",
            "static_checks:domino_users",
            "static_checks:domino_transactions",
            "static_checks:netscaler_dnsrates",
            "static_checks:netscaler_tcp_conns",
            "static_checks:netscaler_sslcerts",
        ],
        "agents/linux_agent": [
            "agent_config:agent_user",
            "agent_config:runas",
            "agent_config:lnx_remote_alert_handlers",
        ],
        "checkparams/environment": [
            "checkgroup_parameters:voltage",
            "checkgroup_parameters:fan_failures",
            "checkgroup_parameters:pll_lock_voltage",
            "checkgroup_parameters:ipmi",
            "checkgroup_parameters:ps_voltage",
            "checkgroup_parameters:bvip_link",
            "checkgroup_parameters:ocprot_current",
            "checkgroup_parameters:brightness",
            "checkgroup_parameters:motion",
            "checkgroup_parameters:ewon",
            "checkgroup_parameters:lamp_operation_time",
            "checkgroup_parameters:apc_symentra",
            "checkgroup_parameters:hw_psu",
            "checkgroup_parameters:apc_system_events",
            "checkgroup_parameters:ups_test",
            "checkgroup_parameters:apc_power",
            "checkgroup_parameters:humidity",
            "checkgroup_parameters:single_humidity",
            "checkgroup_parameters:switch_contact",
            "checkgroup_parameters:plugs",
            "checkgroup_parameters:temperature",
            "checkgroup_parameters:room_temperature",
            "checkgroup_parameters:hw_single_temperature",
            "checkgroup_parameters:evolt",
            "checkgroup_parameters:efreq",
            "checkgroup_parameters:epower",
            "checkgroup_parameters:ups_out_load",
            "checkgroup_parameters:epower_single",
            "checkgroup_parameters:hw_temperature",
            "checkgroup_parameters:hw_temperature_single",
            "checkgroup_parameters:disk_temperature",
            "checkgroup_parameters:eaton_enviroment",
            "checkgroup_parameters:ups_outphase",
            "checkgroup_parameters:el_inphase",
            "checkgroup_parameters:hw_fans",
            "checkgroup_parameters:hw_fans_perc",
            "checkgroup_parameters:pdu_gude",
            "checkgroup_parameters:hostsystem_sensors",
            "checkgroup_parameters:netapp_instance",
            "checkgroup_parameters:temperature_trends",
            "checkgroup_parameters:smoke",
            "checkgroup_parameters:apc_ats_output",
            "checkgroup_parameters:airflow",
            "checkgroup_parameters:ups_capacity",
            "checkgroup_parameters:airflow_deviation",
            "checkgroup_parameters:plug_count",
            "checkgroup_parameters:ucs_bladecenter_chassis_voltage",
            "checkgroup_parameters:hp_msa_psu_voltage",
            "checkgroup_parameters:siemens_plc_flag",
            "checkgroup_parameters:siemens_plc_duration",
            "checkgroup_parameters:siemens_plc_counter",
            "checkgroup_parameters:carbon_monoxide",
        ],
        "inventory": [
            "active_checks:cmk_inv",
            "inv_exports:software_csv",
            "inv_parameters:inv_if",
        ],
        "static/virtualization": [
            "static_checks:vm_state",
        ],
        "monconf/inventory_and_check_mk_settings": [
            "only_hosts",
            "ignored_services",
            "ignored_checks",
            "clustered_services",
            "periodic_discovery",
        ],
        "monconf/various": [
            "clustered_services_mapping",
            "extra_host_conf:service_period",
            "extra_service_conf:service_period",
            "cmc_graphite_service_metrics",
            "cmc_service_rrd_config",
            "cmc_host_rrd_config",
        ],
        "agents/automatic_updates": [
            "agent_config:cmk_update_agent",
        ],
        "agent/general_settings": [
            "dyndns_hosts",
            "piggyback_translation",
            "primary_address_family",
            "service_description_translation",
        ],
        "static/os": [
            "static_checks:fortigate_node_memory",
            "static_checks:uptime",
            "static_checks:systemtime",
            "static_checks:memory_pagefile_win",
            "static_checks:sp_util",
            "static_checks:innovaphone_mem",
            "static_checks:mem_pages",
            "static_checks:statgrab_mem",
            "static_checks:cisco_mem",
            "static_checks:juniper_mem",
            "static_checks:juniper_mem_modules",
            "static_checks:juniper_cpu_util",
            "static_checks:netscaler_mem",
            "static_checks:netscaler_vserver",
            "static_checks:general_flash_usage",
            "static_checks:cisco_supervisor_mem",
            "static_checks:memory_linux",
            "static_checks:memory",
            "static_checks:memory_relative",
            "static_checks:memory_simple",
            "static_checks:memory_multiitem",
            "static_checks:memory_arbor",
            "static_checks:esx_host_memory",
            "static_checks:vm_guest_tools",
            "static_checks:vm_heartbeat",
            "static_checks:cpu_load",
            "static_checks:cpu_utilization",
            "static_checks:cpu_utilization_multiitem",
            "static_checks:fpga_utilization",
            "static_checks:cpu_utilization_os",
            "static_checks:cpu_iowait",
            "static_checks:threads",
            "static_checks:logins",
            "static_checks:vm_counter",
            "static_checks:pf_used_states",
            "static_checks:ntp_time",
            "static_checks:ntp_peer",
            "static_checks:zypper",
            "static_checks:apt",
        ],
        "checkparams/os": [
            "checkgroup_parameters:fortigate_node_memory",
            "checkgroup_parameters:uptime",
            "checkgroup_parameters:systemtime",
            "checkgroup_parameters:memory_pagefile_win",
            "checkgroup_parameters:sp_util",
            "checkgroup_parameters:innovaphone_mem",
            "checkgroup_parameters:mem_pages",
            "checkgroup_parameters:statgrab_mem",
            "checkgroup_parameters:cisco_mem",
            "checkgroup_parameters:juniper_mem",
            "checkgroup_parameters:juniper_mem_modules",
            "checkgroup_parameters:juniper_cpu_util",
            "checkgroup_parameters:netscaler_mem",
            "checkgroup_parameters:netscaler_vserver",
            "checkgroup_parameters:general_flash_usage",
            "checkgroup_parameters:cisco_supervisor_mem",
            "checkgroup_parameters:memory_linux",
            "checkgroup_parameters:memory",
            "checkgroup_parameters:memory_relative",
            "checkgroup_parameters:memory_simple",
            "checkgroup_parameters:memory_multiitem",
            "checkgroup_parameters:memory_arbor",
            "checkgroup_parameters:esx_host_memory",
            "checkgroup_parameters:vm_guest_tools",
            "checkgroup_parameters:vm_heartbeat",
            "checkgroup_parameters:cpu_load",
            "checkgroup_parameters:cpu_utilization",
            "checkgroup_parameters:cpu_utilization_multiitem",
            "checkgroup_parameters:fpga_utilization",
            "checkgroup_parameters:cpu_utilization_os",
            "checkgroup_parameters:cpu_iowait",
            "checkgroup_parameters:threads",
            "checkgroup_parameters:logins",
            "checkgroup_parameters:vm_counter",
            "checkgroup_parameters:pf_used_states",
            "checkgroup_parameters:ntp_time",
            "checkgroup_parameters:ntp_peer",
            "checkgroup_parameters:apt",
        ],
        "static/hardware": [
            "static_checks:hw_errors",
        ],
        "checkparams/printers": [
            "checkgroup_parameters:printer_supply",
            "checkgroup_parameters:cups_queues",
            "checkgroup_parameters:windows_printer_queues",
            "checkgroup_parameters:printer_input",
            "checkgroup_parameters:printer_output",
        ],
        "static/storage": [
            "static_checks:disk_failures",
            "static_checks:ddn_s2a_port_errors",
            "static_checks:read_hits",
            "static_checks:storage_iops",
            "static_checks:storage_throughput",
            "static_checks:ddn_s2a_wait",
            "static_checks:blank_tapes",
            "static_checks:mongodb_flushing",
            "static_checks:mongodb_asserts",
            "static_checks:mongodb_mem",
            "static_checks:openhardwaremonitor_smart",
            "static_checks:mongodb_locks",
            "static_checks:prism_container",
            "static_checks:inotify",
            "static_checks:emcvnx_disks",
            "static_checks:lvm_lvs_pools",
            "static_checks:emcvnx_storage_pools",
            "static_checks:emcvnx_storage_pools_tiering",
            "static_checks:filehandler",
            "static_checks:brocade_fcport",
            "static_checks:brocade_sfp",
            "static_checks:fcport_words",
            "static_checks:fs_mount_options",
            "static_checks:storcli_vdrives",
            "static_checks:storcli_pdisks",
            "static_checks:veeam_tapejobs",
            "static_checks:ceph_status",
            "static_checks:ceph_osds",
            "static_checks:ceph_mgrs",
            "static_checks:quantum_storage_status",
            "static_checks:filesystem",
            "static_checks:threepar_capacity",
            "static_checks:threepar_cpgs",
            "static_checks:nfsiostats",
            "static_checks:fileinfo",
            "static_checks:fileinfo-groups",
            "static_checks:filestats",
            "static_checks:netapp_fcportio",
            "static_checks:mongodb_collections",
            "static_checks:volume_groups",
            "static_checks:ibm_svc_mdiskgrp",
            "static_checks:esx_vsphere_datastores",
            "static_checks:esx_hostystem_maintenance",
            "static_checks:ibm_svc_total_latency",
            "static_checks:ibm_svc_host",
            "static_checks:ibm_svc_mdisk",
            "static_checks:diskstat",
            "static_checks:disk_io",
            "static_checks:zpool_status",
            "static_checks:network_fs",
            "static_checks:windows_multipath",
            "static_checks:multipath",
            "static_checks:multipath_count",
            "static_checks:hpux_multipath",
            "static_checks:drbd",
            "static_checks:snapvault",
            "static_checks:netapp_snapshots",
            "static_checks:netapp_disks",
            "static_checks:netapp_volumes",
            "static_checks:netapp_luns",
            "static_checks:raid",
            "static_checks:raid_summary",
            "static_checks:raid_disk",
            "static_checks:pfm_health",
            "static_checks:fc_port",
            "static_checks:heartbeat_crm",
            "static_checks:heartbeat_crm_resources",
            "static_checks:bossock_fibers",
        ],
        "checkparams/storage": [
            "checkgroup_parameters:disk_failures",
            "checkgroup_parameters:ddn_s2a_port_errors",
            "checkgroup_parameters:read_hits",
            "checkgroup_parameters:storage_iops",
            "checkgroup_parameters:storage_throughput",
            "checkgroup_parameters:ddn_s2a_wait",
            "checkgroup_parameters:blank_tapes",
            "checkgroup_parameters:mongodb_flushing",
            "checkgroup_parameters:mongodb_asserts",
            "checkgroup_parameters:mongodb_mem",
            "checkgroup_parameters:openhardwaremonitor_smart",
            "checkgroup_parameters:mongodb_locks",
            "checkgroup_parameters:prism_container",
            "checkgroup_parameters:inotify",
            "checkgroup_parameters:emcvnx_disks",
            "checkgroup_parameters:lvm_lvs_pools",
            "checkgroup_parameters:emcvnx_storage_pools",
            "checkgroup_parameters:emcvnx_storage_pools_tiering",
            "checkgroup_parameters:filehandler",
            "checkgroup_parameters:brocade_fcport",
            "checkgroup_parameters:brocade_sfp",
            "checkgroup_parameters:fcport_words",
            "checkgroup_parameters:fs_mount_options",
            "checkgroup_parameters:storcli_vdrives",
            "checkgroup_parameters:storcli_pdisks",
            "checkgroup_parameters:veeam_tapejobs",
            "checkgroup_parameters:ceph_status",
            "checkgroup_parameters:ceph_osds",
            "checkgroup_parameters:ceph_mgrs",
            "checkgroup_parameters:quantum_storage_status",
            "checkgroup_parameters:filesystem",
            "checkgroup_parameters:threepar_capacity",
            "checkgroup_parameters:threepar_cpgs",
            "checkgroup_parameters:nfsiostats",
            "checkgroup_parameters:fileinfo",
            "filesystem_groups",
            "fileinfo_groups",
            "checkgroup_parameters:fileinfo-groups",
            "checkgroup_parameters:filestats",
            "checkgroup_parameters:netapp_fcportio",
            "checkgroup_parameters:mongodb_collections",
            "checkgroup_parameters:volume_groups",
            "checkgroup_parameters:ibm_svc_mdiskgrp",
            "checkgroup_parameters:esx_vsphere_datastores",
            "checkgroup_parameters:esx_hostystem_maintenance",
            "checkgroup_parameters:ibm_svc_total_latency",
            "checkgroup_parameters:ibm_svc_host",
            "checkgroup_parameters:ibm_svc_mdisk",
            "checkgroup_parameters:diskstat",
            "checkgroup_parameters:disk_io",
            "diskstat_inventory",
            "checkgroup_parameters:network_fs",
            "checkgroup_parameters:windows_multipath",
            "checkgroup_parameters:multipath",
            "inventory_multipath_rules",
            "checkgroup_parameters:multipath_count",
            "checkgroup_parameters:hpux_multipath",
            "checkgroup_parameters:drbd",
            "checkgroup_parameters:snapvault",
            "checkgroup_parameters:netapp_snapshots",
            "checkgroup_parameters:netapp_disks",
            "checkgroup_parameters:netapp_volumes",
            "checkgroup_parameters:netapp_luns",
            "checkgroup_parameters:raid_summary",
            "checkgroup_parameters:raid_disk",
            "checkgroup_parameters:pfm_health",
            "checkgroup_parameters:fc_port",
            "checkgroup_parameters:heartbeat_crm",
            "checkgroup_parameters:heartbeat_crm_resources",
            "checkgroup_parameters:bossock_fibers",
        ],
        "checkparams/applications": [
            "checkgroup_parameters:f5_bigip_snat",
            "checkgroup_parameters:veritas_vcs",
            "checkgroup_parameters:f5_bigip_vserver",
            "checkgroup_parameters:cluster_status",
            "logwatch_rules",
            "checkgroup_parameters:local",
            "checkgroup_parameters:threepar_remotecopy",
            "checkgroup_parameters:livestatus_status",
            "checkgroup_parameters:ad_replication",
            "checkgroup_parameters:mq_queues",
            "checkgroup_parameters:sshd_config",
            "checkgroup_parameters:websphere_mq",
            "checkgroup_parameters:websphere_mq_channels",
            "checkgroup_parameters:websphere_mq_manager",
            "checkgroup_parameters:websphere_mq_instance",
            "checkgroup_parameters:plesk_backups",
            "checkgroup_parameters:firewall_if",
            "checkgroup_parameters:kaspersky_av_client",
            "checkgroup_parameters:mcafee_av_client",
            "checkgroup_parameters:mcafee_web_gateway",
            "checkgroup_parameters:mcafee_web_gateway_misc",
            "checkgroup_parameters:mcafee_emailgateway_bridge",
            "checkgroup_parameters:pfsense_counter",
            "checkgroup_parameters:lnx_quota",
            "checkgroup_parameters:ruckus_mac",
            "checkgroup_parameters:ruckus_ap",
            "checkgroup_parameters:esx_licenses",
            "checkgroup_parameters:ibmsvc_licenses",
            "checkgroup_parameters:citrix_licenses",
            "checkgroup_parameters:rds_licenses",
            "checkgroup_parameters:win_license",
            "checkgroup_parameters:citrix_sessions",
            "checkgroup_parameters:citrix_state",
            "checkgroup_parameters:mssql_stats",
            "checkgroup_parameters:mssql_instance",
            "checkgroup_parameters:mssql_databases",
            "checkgroup_parameters:mssql_connections",
            "checkgroup_parameters:varnish_cache",
            "checkgroup_parameters:varnish_client",
            "checkgroup_parameters:varnish_backend",
            "checkgroup_parameters:varnish_fetch",
            "checkgroup_parameters:varnish_esi",
            "checkgroup_parameters:varnish_objects",
            "checkgroup_parameters:varnish_worker",
            "checkgroup_parameters:varnish_cache_hit_ratio",
            "checkgroup_parameters:varnish_backend_success_ratio",
            "checkgroup_parameters:varnish_worker_thread_ratio",
            "checkgroup_parameters:clr_memory",
            "checkgroup_parameters:skype_mobile",
            "checkgroup_parameters:skype_conferencing",
            "checkgroup_parameters:skype_sip",
            "checkgroup_parameters:skype_mediation_server",
            "checkgroup_parameters:skype_xmpp",
            "checkgroup_parameters:skype_edgeauth",
            "checkgroup_parameters:acme_certificates",
            "checkgroup_parameters:acme_sbc_snmp",
            "checkgroup_parameters:skype",
            "checkgroup_parameters:skype_proxy",
            "checkgroup_parameters:skype_edge",
            "checkgroup_parameters:ps",
            "checkgroup_parameters:generic_number",
            "checkgroup_parameters:generic_rate",
            "checkgroup_parameters:generic_string",
            "checkgroup_parameters:jvm_uptime",
            "checkgroup_parameters:k8s_nodes",
            "checkgroup_parameters:k8s_resources",
            "checkgroup_parameters:k8s_pods_cpu",
            "checkgroup_parameters:k8s_pods_memory",
            "checkgroup_parameters:k8s_pods_fs",
            "checkgroup_parameters:k8s_roles",
            "checkgroup_parameters:netapp_systemtime",
            "checkgroup_parameters:jvm_sessions",
            "checkgroup_parameters:jvm_requests",
            "checkgroup_parameters:jvm_queue",
            "checkgroup_parameters:jvm_memory",
            "checkgroup_parameters:safenet_hsm_operstats",
            "checkgroup_parameters:safenet_hsm_eventstats",
            "checkgroup_parameters:safenet_ntls_links",
            "checkgroup_parameters:safenet_ntls_clients",
            "checkgroup_parameters:fireeye_active_vms",
            "checkgroup_parameters:fireeye_lic",
            "checkgroup_parameters:fireeye_quarantine",
            "checkgroup_parameters:fireeye_mailq",
            "checkgroup_parameters:fireeye_mail",
            "checkgroup_parameters:oracle_logswitches",
            "checkgroup_parameters:systemd_services",
            "checkgroup_parameters:hacmp_resources",
            "checkgroup_parameters:webserver",
            "checkgroup_parameters:aws_costs_and_usage",
            "checkgroup_parameters:aws_ec2_cpu_credits",
            "checkgroup_parameters:aws_rds_cpu_credits",
            "checkgroup_parameters:aws_elb_backend_connection_errors",
            "checkgroup_parameters:aws_elb_healthy_hosts",
            "checkgroup_parameters:aws_elb_http",
            "checkgroup_parameters:aws_elb_latency",
            "checkgroup_parameters:aws_elb_statistics",
            "checkgroup_parameters:azure_agent_info",
            "checkgroup_parameters:azure_databases",
            "checkgroup_parameters:azure_storageaccounts",
            "checkgroup_parameters:azure_vms",
            "checkgroup_parameters:azure_vms_summary",
            "checkgroup_parameters:azure_virtualnetworkgateways",
            "checkgroup_parameters:apache_status",
            "checkgroup_parameters:saprouter_cert_age",
            "checkgroup_parameters:sap_dialog",
            "checkgroup_parameters:nginx_status",
            "checkgroup_parameters:sles_license",
            "checkgroup_parameters:msx_info_store",
            "checkgroup_parameters:msx_rpcclientaccess",
            "checkgroup_parameters:msx_database",
            "checkgroup_parameters:msx_queues",
            "checkgroup_parameters:msexch_copyqueue",
            "checkgroup_parameters:services_summary",
            "checkgroup_parameters:solaris_services_summary",
            "checkgroup_parameters:esx_vsphere_objects",
            "checkgroup_parameters:esx_vsphere_objects_count",
            "checkgroup_parameters:oracle_tablespaces",
            "checkgroup_parameters:oracle_processes",
            "checkgroup_parameters:oracle_recovery_area",
            "checkgroup_parameters:oracle_dataguard_stats",
            "checkgroup_parameters:oracle_undostat",
            "checkgroup_parameters:oracle_rman",
            "checkgroup_parameters:oracle_recovery_status",
            "checkgroup_parameters:oracle_jobs",
            "checkgroup_parameters:oracle_instance",
            "checkgroup_parameters:asm_diskgroup",
            "checkgroup_parameters:mssql_backup",
            "checkgroup_parameters:mssql_backup_per_type",
            "checkgroup_parameters:mssql_file_sizes",
            "checkgroup_parameters:mssql_tablespaces",
            "checkgroup_parameters:mssql_page_activity",
            "checkgroup_parameters:mssql_transactionlogs",
            "checkgroup_parameters:mssql_datafiles",
            "checkgroup_parameters:vm_snapshots",
            "checkgroup_parameters:veeam_backup",
            "checkgroup_parameters:backup_timemachine",
            "checkgroup_parameters:job",
            "checkgroup_parameters:mssql_counters_locks",
            "checkgroup_parameters:mssql_blocked_sessions",
            "checkgroup_parameters:mssql_instance_blocked_sessions",
            "checkgroup_parameters:mysql_sessions",
            "checkgroup_parameters:mysql_innodb_io",
            "checkgroup_parameters:mysql_connections",
            "checkgroup_parameters:mysql_slave",
            "checkgroup_parameters:db_bloat",
            "checkgroup_parameters:db_connections",
            "checkgroup_parameters:postgres_locks",
            "checkgroup_parameters:postgres_maintenance",
            "checkgroup_parameters:f5_connections",
            "checkgroup_parameters:cisco_fw_connections",
            "checkgroup_parameters:checkpoint_connections",
            "checkgroup_parameters:checkpoint_packets",
            "checkgroup_parameters:f5_pools",
            "checkgroup_parameters:mysql_db_size",
            "checkgroup_parameters:postgres_sessions",
            "checkgroup_parameters:postgres_instance_sessions",
            "checkgroup_parameters:asa_svc_sessions",
            "checkgroup_parameters:oracle_sessions",
            "checkgroup_parameters:oracle_sql",
            "checkgroup_parameters:oracle_locks",
            "checkgroup_parameters:oracle_longactivesessions",
            "checkgroup_parameters:postgres_stat_database",
            "checkgroup_parameters:win_dhcp_pools",
            "checkgroup_parameters:vms_procs",
            "checkgroup_parameters:mailqueue_length",
            "checkgroup_parameters:mail_queue_length",
            "checkgroup_parameters:mail_latency",
            "checkgroup_parameters:services",
            "checkgroup_parameters:solaris_services",
            "checkgroup_parameters:winperf_ts_sessions",
            "checkgroup_parameters:mbg_lantime_state",
            "checkgroup_parameters:sansymphony_pool",
            "checkgroup_parameters:sansymphony_alerts",
            "checkgroup_parameters:jvm_threads",
            "checkgroup_parameters:sym_brightmail_queues",
            "checkgroup_parameters:db2_logsize",
            "checkgroup_parameters:db2_sortoverflow",
            "checkgroup_parameters:db2_tablespaces",
            "checkgroup_parameters:db2_connections",
            "checkgroup_parameters:db2_counters",
            "checkgroup_parameters:db2_backup",
            "checkgroup_parameters:db2_mem",
            "checkgroup_parameters:windows_updates",
            "checkgroup_parameters:synology_update",
            "checkgroup_parameters:antivir_update_age",
            "checkgroup_parameters:logwatch_ec",
            "logwatch_groups",
            "checkgroup_parameters:citrix_load",
            "checkgroup_parameters:jvm_gc",
            "checkgroup_parameters:jvm_tp",
            "checkgroup_parameters:docker_node_containers",
            "checkgroup_parameters:docker_node_disk_usage",
            "checkgroup_parameters:domino_mailqueues",
            "checkgroup_parameters:domino_users",
            "checkgroup_parameters:domino_transactions",
            "checkgroup_parameters:netscaler_dnsrates",
            "checkgroup_parameters:netscaler_tcp_conns",
            "checkgroup_parameters:netscaler_sslcerts",
        ],
        "monconf/notifications": [
            "extra_host_conf:notifications_enabled",
            "extra_service_conf:notifications_enabled",
            "extra_host_conf:notification_options",
            "extra_service_conf:notification_options",
            "extra_host_conf:notification_period",
            "extra_service_conf:notification_period",
            "extra_host_conf:first_notification_delay",
            "extra_service_conf:first_notification_delay",
            "extra_host_conf:notification_interval",
            "extra_service_conf:notification_interval",
            "extra_host_conf:flap_detection_enabled",
            "extra_service_conf:flap_detection_enabled",
            "extra_service_conf:notes_url",
            "extra_host_conf:notes_url",
            "extra_service_conf:display_name",
            "notification_parameters:mail",
            "notification_parameters:slack",
            "notification_parameters:victorops",
            "notification_parameters:pagerduty",
            "notification_parameters:asciimail",
            "notification_parameters:mkeventd",
            "notification_parameters:spectrum",
            "notification_parameters:pushover",
            "notification_parameters:cisco_webex_teams",
            "cmc_service_flap_settings",
            "cmc_host_flap_settings",
            "host_recurring_downtimes",
            "service_recurring_downtimes",
        ],
        "monconf/service_checks": [
            "extra_service_conf:max_check_attempts",
            "extra_service_conf:check_interval",
            "extra_service_conf:retry_interval",
            "extra_service_conf:check_period",
            "check_periods",
            "extra_service_conf:process_perf_data",
            "extra_service_conf:passive_checks_enabled",
            "extra_service_conf:active_checks_enabled",
            "cmc_service_check_timeout",
            "service_state_translation",
        ],
        "user_interface": [
            "extra_host_conf:icon_image",
            "extra_service_conf:icon_image",
            "host_icons_and_actions",
            "service_icons_and_actions",
            "extra_host_conf:_ESCAPE_PLUGIN_OUTPUT",
            "extra_service_conf:_ESCAPE_PLUGIN_OUTPUT",
        ],
        "activechecks": [
            "active_checks:ssh",
            "active_checks:icmp",
            "active_checks:ftp",
            "active_checks:sftp",
            "active_checks:dns",
            "active_checks:sql",
            "active_checks:tcp",
            "active_checks:uniserv",
            "active_checks:http",
            "active_checks:ldap",
            "active_checks:smtp",
            "active_checks:disk_smb",
            "custom_checks",
            "active_checks:bi_aggr",
            "active_checks:form_submit",
            "active_checks:notify_count",
            "active_checks:traceroute",
            "active_checks:mail_loop",
            "active_checks:mail",
            "active_checks:mailboxes",
            "active_checks:by_ssh",
        ],
        "agent/check_mk_agent": [
            "agent_ports",
            "tcp_connect_timeouts",
            "agent_encryption",
            "check_mk_exit_status",
            "check_mk_agent_target_versions",
        ],
        "checkparams/discovery": [
            "inventory_ipmi_rules",
            "ewon_discovery_rules",
            "mssql_transactionlogs_discovery",
            "inventory_services_rules",
            "inventory_solaris_services_rules",
            "discovery_systemd_units_services_rules",
            "discovery_win_dhcp_pools",
            "inventory_if_rules",
            "brocade_fcport_inventory",
            "inventory_processes_rules",
            "inv_domino_tasks_rules",
            "inventory_sap_values",
            "sap_value_groups",
            "inventory_heartbeat_crm_rules",
            "inventory_df_rules",
            "inventory_mssql_counters_rules",
            "inventory_fujitsu_ca_ports",
            "discovery_mssql_backup",
            "discovery_rules_vnx_quotas",
        ],
        "agents/agent_plugins": [
            "agent_config:jar_signature",
            "agent_config:mailman_lists",
            "agent_config:windows_multipath",
            "agent_config:windows_updates",
            "agent_config:isc_dhcpd",
            "agent_config:lnx_quota",
            "agent_config:mk_logins",
            "agent_config:mk_iptables",
            "agent_config:winperf",
            "agent_config:win_eventlog",
            "agent_config:fileinfo",
            "agent_config:smart",
            "agent_config:vxvm",
            "agent_config:ad_replication",
            "agent_config:windows_tasks",
            "agent_config:winperf_if",
            "agent_config:windows_broadcom_bonding",
            "agent_config:mssql",
            "agent_config:citrix_licenses",
            "agent_config:citrix_xenapp",
            "agent_config:hyperv_vms",
            "agent_config:hyperv_vms_guestinfos",
            "agent_config:arcserve_backup",
            "agent_config:storcli",
            "agent_config:win_megaraid",
            "agent_config:rds_licenses",
            "agent_config:win_license",
            "agent_config:websphere_mq",
            "agent_config:unitrends",
            "agent_config:lvm",
            "agent_config:nfsexports",
            "agent_config:netstat",
            "agent_config:symantec_av",
            "agent_config:kaspersky_av",
            "agent_config:win_dmidecode",
            "agent_config:win_dhcp_pools",
            "agent_config:mk_scaleio",
            "agent_config:mk_cups_queues",
            "agent_config:mk_inventory",
            "agent_config:mk_apt",
            "agent_config:mk_zypper",
            "agent_config:plesk",
            "agent_config:dnsclient",
            "agent_config:mk_tsm",
            "agent_config:mk_mysql",
            "agent_config:db2_mem",
            "agent_config:mk_postgres",
            "agent_config:mk_mongodb",
            "agent_config:mk_sshd_config",
            "agent_config:mk_suseconnect",
            "agent_config:mk_jolokia",
            "agent_config:mk_saprouter",
            "agent_config:mk_sap",
            "agent_config:mk_logwatch",
            "agent_config:mk_filestats",
            "agent_config:nginx_status",
            "agent_config:apache_status",
            "agent_config:mk_oracle",
            "agent_config:mtr",
            "agent_config:mk_inotify",
            "agent_config:msexch_dag",
            "agent_config:msexch_database",
            "agent_config:mk_site_object_counts",
            "agent_config:mk_docker_container_piggybacked",
            "agent_config:mk_docker_node",
            "agent_config:veeam_backup_status",
            "agent_config:mk_nfsiostat",
        ],
        "static/environment": [
            "static_checks:voltage",
            "static_checks:fan_failures",
            "static_checks:pll_lock_voltage",
            "static_checks:ipmi",
            "static_checks:ps_voltage",
            "static_checks:bvip_link",
            "static_checks:ocprot_current",
            "static_checks:brightness",
            "static_checks:motion",
            "static_checks:ewon",
            "static_checks:lamp_operation_time",
            "static_checks:apc_symentra",
            "static_checks:hw_psu",
            "static_checks:apc_system_events",
            "static_checks:ups_test",
            "static_checks:apc_power",
            "static_checks:humidity",
            "static_checks:single_humidity",
            "static_checks:switch_contact",
            "static_checks:plugs",
            "static_checks:temperature",
            "static_checks:room_temperature",
            "static_checks:hw_single_temperature",
            "static_checks:evolt",
            "static_checks:efreq",
            "static_checks:epower",
            "static_checks:ups_out_load",
            "static_checks:epower_single",
            "static_checks:hw_temperature",
            "static_checks:hw_temperature_single",
            "static_checks:disk_temperature",
            "static_checks:eaton_enviroment",
            "static_checks:ups_outphase",
            "static_checks:el_inphase",
            "static_checks:hw_fans",
            "static_checks:hw_fans_perc",
            "static_checks:pdu_gude",
            "static_checks:hostsystem_sensors",
            "static_checks:netapp_instance",
            "static_checks:temperature_auto",
            "static_checks:temperature_trends",
            "static_checks:smoke",
            "static_checks:apc_ats_output",
            "static_checks:airflow",
            "static_checks:ups_capacity",
            "static_checks:airflow_deviation",
            "static_checks:plug_count",
            "static_checks:ucs_bladecenter_chassis_voltage",
            "static_checks:hp_msa_psu_voltage",
            "static_checks:siemens_plc_flag",
            "static_checks:siemens_plc_duration",
            "static_checks:siemens_plc_counter",
            "static_checks:carbon_monoxide",
        ],
        "monconf/host_checks": [
            "extra_host_conf:max_check_attempts",
            "extra_host_conf:check_interval",
            "extra_host_conf:retry_interval",
            "extra_host_conf:check_period",
            "host_check_commands",
            "cmc_smartping_settings",
            "host_state_translation",
        ],
        "agent/snmp": [
            "snmp_communities",
            "management_board_config",
            "snmp_character_encodings",
            "snmp_check_interval",
            "bulkwalk_hosts",
            "management_bulkwalk_hosts",
            "snmp_bulk_size",
            "snmp_without_sys_descr",
            "snmpv2c_hosts",
            "snmpv3_contexts",
            "snmp_timing",
            "snmp_backend_hosts",
            "usewalk_hosts",
            "snmp_ports",
            "snmp_limit_oid_range",
        ],
        "grouping": [
            "host_groups",
            "service_groups",
            "host_contactgroups",
            "service_contactgroups",
            "extra_service_conf:_sla_config",
            "extra_host_conf:_ec_sl",
            "extra_service_conf:_ec_sl",
        ],
    }
    for group_name in rulespec_registry.get_all_groups():
        rulespec_names = [rulespec.name for rulespec in rulespec_registry.get_by_group(group_name)]
        assert sorted(by_group[group_name]) == sorted(rulespec_names)


def _expected_rulespec_group_choices():
    expected = [
        ("activechecks", "HTTP, TCP, Email, ..."),
        ("agent", "Access to agents"),
        ("agent/check_mk_agent", "&nbsp;&nbsp;\u2319 Checkmk agent"),
        ("agent/general_settings", "&nbsp;&nbsp;\u2319 General Settings"),
        ("agents", "Agent rules"),
        ("agents/generic_options", "&nbsp;&nbsp;\u2319 Generic Options"),
        ("checkparams", "Service discovery rules"),
        ("checkparams/discovery", "&nbsp;&nbsp;\u2319 Discovery of individual services"),
        (
            "checkparams/inventory_and_check_mk_settings",
            "&nbsp;&nbsp;\u2319 Discovery and Checkmk settings",
        ),
        ("datasource_programs", "Other integrations"),
        ("eventconsole", "Event Console rules"),
        ("inventory", "Hardware / Software Inventory"),
        ("host_monconf", "Host monitoring rules"),
        ("host_monconf/host_checks", "&nbsp;&nbsp;\u2319 Host checks"),
        ("host_monconf/host_notifications", "&nbsp;&nbsp;\u2319 Notifications"),
        ("host_monconf/host_various", "&nbsp;&nbsp;\u2319 Various"),
        ("monconf", "Service monitoring rules"),
        ("monconf/applications", "&nbsp;&nbsp;\u2319 Applications, Processes & Services"),
        ("monconf/networking", "&nbsp;&nbsp;\u2319 Networking"),
        ("monconf/os", "&nbsp;&nbsp;\u2319 Operating System Resources"),
        ("monconf/printers", "&nbsp;&nbsp;\u2319 Printers"),
        ("monconf/storage", "&nbsp;&nbsp;\u2319 Storage, Filesystems and Files"),
        (
            "monconf/environment",
            "&nbsp;&nbsp;\u2319 Temperature, Humidity, Electrical Parameters, etc.",
        ),
        ("monconf/hardware", "&nbsp;&nbsp;\u2319 Hardware, BIOS"),
        ("monconf/virtualization", "&nbsp;&nbsp;\u2319 Virtualization"),
        ("monconf/notifications", "&nbsp;&nbsp;\u2319 Notifications"),
        ("monconf/service_checks", "&nbsp;&nbsp;\u2319 Service Checks"),
        ("monconf/various", "&nbsp;&nbsp;\u2319 Various"),
        ("custom_checks", "Other services"),
        ("datasource_programs/apps", "&nbsp;&nbsp;⌙ Applications"),
        ("datasource_programs/cloud", "&nbsp;&nbsp;⌙ Cloud based environments"),
        ("datasource_programs/custom", "&nbsp;&nbsp;⌙ Custom integrations"),
        ("datasource_programs/hw", "&nbsp;&nbsp;⌙ Hardware"),
        ("datasource_programs/os", "&nbsp;&nbsp;⌙ Operating systems"),
        ("datasource_programs/testing", "&nbsp;&nbsp;⌙ Testing"),
        ("snmp", "SNMP rules"),
        ("static", "Enforced services"),
        ("static/applications", "&nbsp;&nbsp;⌙ Applications, Processes & Services"),
        ("static/environment", "&nbsp;&nbsp;⌙ Temperature, Humidity, Electrical Parameters, etc."),
        ("static/hardware", "&nbsp;&nbsp;⌙ Hardware, BIOS"),
        ("static/networking", "&nbsp;&nbsp;⌙ Networking"),
        ("static/os", "&nbsp;&nbsp;⌙ Operating System Resources"),
        ("static/printers", "&nbsp;&nbsp;⌙ Printers"),
        ("static/storage", "&nbsp;&nbsp;⌙ Storage, Filesystems and Files"),
        ("static/virtualization", "&nbsp;&nbsp;⌙ Virtualization"),
        ("vm_cloud_container", "VM, Cloud, Container"),
    ]

    if not cmk_version.is_raw_edition():
        expected += [
            ("agents/agent_plugins", "&nbsp;&nbsp;\u2319 Agent Plugins"),
            ("agents/automatic_updates", "&nbsp;&nbsp;\u2319 Automatic Updates"),
            ("agents/linux_agent", "&nbsp;&nbsp;\u2319 Linux Agent"),
            ("agents/windows_agent", "&nbsp;&nbsp;\u2319 Windows Agent"),
            ("agents/windows_modules", "&nbsp;&nbsp;\u2319 Windows Modules"),
        ]

    return expected


@pytest.mark.parametrize(
    "mode,result",
    [
        ("rulesets", _expected_rulespec_group_choices()),
    ],
)
def test_rulespec_group_choices(mode, result) -> None:
    assert sorted(rulespec_group_registry.get_group_choices()) == sorted(result)


@pytest.mark.parametrize(
    "term,result",
    [
        (
            "host_monconf",
            [
                "host_monconf",
                "host_monconf/host_checks",
                "host_monconf/host_notifications",
                "host_monconf/host_various",
            ],
        ),
        (
            "monconf",
            [
                "monconf",
                "monconf/applications",
                "monconf/environment",
                "monconf/hardware",
                "monconf/networking",
                "monconf/notifications",
                "monconf/os",
                "monconf/printers",
                "monconf/service_checks",
                "monconf/storage",
                "monconf/various",
                "monconf/virtualization",
            ],
        ),
        ("monconf/various", ["monconf/various"]),
        (
            "agent",
            [
                "agent",
                "agent/check_mk_agent",
                "agent/general_settings",
            ],
        ),
    ],
)
def test_rulespec_get_matching_group_names(term, result) -> None:
    assert sorted(rulespec_group_registry.get_matching_group_names(term)) == sorted(result)


def test_rulespec_get_main_groups() -> None:
    main_group_names = [g_class().name for g_class in rulespec_group_registry.get_main_groups()]
    assert sorted(main_group_names) == sorted(
        [
            "activechecks",
            "monconf",
            "host_monconf",
            "agent",
            "agents",
            "checkparams",
            "static",
            "datasource_programs",
            "inventory",
            "eventconsole",
            "custom_checks",
            "snmp",
            "vm_cloud_container",
        ]
    )


def test_rulespec_get_all_groups() -> None:
    expected_rulespec_groups = [
        "activechecks",
        "host_monconf/host_checks",
        "host_monconf/host_notifications",
        "host_monconf/host_various",
        "monconf/applications",
        "monconf/environment",
        "monconf/hardware",
        "monconf/service_checks",
        "monconf/networking",
        "monconf/notifications",
        "monconf/os",
        "monconf/printers",
        "monconf/storage",
        "monconf/various",
        "agent/general_settings",
        "agent/check_mk_agent",
        "agents/generic_options",
        "custom_checks",
        "snmp",
        "vm_cloud_container",
        "checkparams/inventory_and_check_mk_settings",
        "static/networking",
        "static/applications",
        "checkparams/discovery",
        "static/environment",
        "static/storage",
        "static/printers",
        "static/os",
        "static/virtualization",
        "static/hardware",
        "datasource_programs/apps",
        "datasource_programs/custom",
        "datasource_programs/hw",
        "datasource_programs/os",
        "datasource_programs/testing",
        "inventory",
        "eventconsole",
    ]

    if not cmk_version.is_raw_edition():
        expected_rulespec_groups += [
            "agents/automatic_updates",
            "agents/linux_agent",
            "agents/windows_agent",
            "agents/windows_modules",
            "agents/agent_plugins",
        ]

    assert sorted(rulespec_registry.get_all_groups()) == sorted(expected_rulespec_groups)


def test_rulespec_get_host_groups() -> None:

    expected_rulespec_host_groups = [
        "checkparams",
        "checkparams/discovery",
        "checkparams/inventory_and_check_mk_settings",
        "host_monconf/host_checks",
        "host_monconf/host_notifications",
        "host_monconf/host_various",
        "agent/general_settings",
        "agent/check_mk_agent",
        "agents/generic_options",
        "datasource_programs",
        "datasource_programs/apps",
        "datasource_programs/cloud",
        "datasource_programs/custom",
        "datasource_programs/hw",
        "datasource_programs/os",
        "datasource_programs/testing",
        "inventory",
        "eventconsole",
        "custom_checks",
        "snmp",
        "vm_cloud_container",
    ]

    if not cmk_version.is_raw_edition():
        expected_rulespec_host_groups += [
            "agents/agent_plugins",
            "agents/automatic_updates",
            "agents/linux_agent",
            "agents/windows_agent",
            "agents/windows_modules",
        ]

    group_names = rulespec_group_registry.get_host_rulespec_group_names(True)
    assert sorted(group_names) == sorted(expected_rulespec_host_groups)


def test_legacy_register_rule(monkeypatch) -> None:
    group_registry = RulespecGroupRegistry()
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_registry", RulespecRegistry(group_registry)
    )

    register_rule(
        "grouping",
        "dingdong_group",
        Dictionary(
            title="DING",
            help="s-o-s",
            elements=[],
        ),
    )

    group = get_rulegroup("grouping")
    assert group.name == "grouping"
    assert group.title == "grouping"

    rulespec_names = [
        r.name for r in cmk.gui.watolib.rulespecs.rulespec_registry.get_by_group("grouping")
    ]
    assert "dingdong_group" in rulespec_names
    assert len(rulespec_names) == 1

    # Check some default values
    spec = cmk.gui.watolib.rulespecs.rulespec_registry["dingdong_group"]

    assert spec.name == "dingdong_group"
    assert spec.group_name == "grouping"
    assert isinstance(spec.valuespec, Dictionary)
    assert spec.match_type == "first"
    assert spec.title == "DING"
    assert spec.help == "s-o-s"
    assert spec.item_spec is None
    assert spec.item_type is None
    assert spec.item_name is None
    assert spec.item_help is None
    assert spec.item_enum is None
    assert spec.is_optional is False
    assert spec.is_deprecated is False
    assert spec.factory_default == Rulespec.NO_FACTORY_DEFAULT


def test_legacy_register_rule_attributes(monkeypatch) -> None:
    group_registry = RulespecGroupRegistry()
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_registry", RulespecRegistry(group_registry)
    )

    register_rule(
        "dingdong_group",
        "rule_name",
        Dictionary(
            title="DING",
            elements=[],
        ),
        title="title",
        help="help me!",
        itemspec=TextInput(title="blub"),
        itemtype="service",
        itemname="Blub",
        itemhelp="Item help",
        match="dict",
        optional=True,
        deprecated=True,
        factory_default="humpf",
    )

    spec = cmk.gui.watolib.rulespecs.rulespec_registry["rule_name"]
    assert spec.name == "rule_name"
    assert spec.group_name == "dingdong_group"
    assert isinstance(spec.valuespec, Dictionary)
    assert spec.match_type == "dict"
    assert spec.title == "title"
    assert spec.help == "help me!"
    assert isinstance(spec.item_spec, TextInput)
    assert spec.item_type == "service"
    assert spec.item_name == "Blub"
    assert spec.item_help == "Item help"
    assert spec.is_optional is True
    assert spec.is_deprecated is True
    assert spec.factory_default == "humpf"


@pytest.fixture(name="patch_rulespec_registries")
def fixture_patch_rulespec_registries(monkeypatch):
    group_registry = RulespecGroupRegistry()
    group_registry.register(RulespecGroupEnforcedServices)
    test_rulespec_registry = RulespecRegistry(group_registry)
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_registry", test_rulespec_registry)
    monkeypatch.setattr(cmk.gui.plugins.wato.utils, "rulespec_registry", test_rulespec_registry)


def test_register_check_parameters(patch_rulespec_registries) -> None:
    register_check_parameters(
        "netblabla",
        "bla_params",
        "Title of bla",
        Dictionary(
            elements=[],
        ),
        TextInput(title="The object name"),
        "dict",
    )

    # Check either registration as discovery check ruleset
    group = get_rulegroup("checkparams/netblabla")
    assert group.name == "checkparams/netblabla"
    assert group.title == "netblabla"

    rulespec_names = [
        r.name
        for r in cmk.gui.watolib.rulespecs.rulespec_registry.get_by_group("checkparams/netblabla")
    ]
    assert "checkgroup_parameters:bla_params" in rulespec_names
    assert len(rulespec_names) == 1
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry["checkgroup_parameters:bla_params"]

    assert rulespec.title == "Title of bla"
    assert isinstance(rulespec.valuespec, TimeperiodValuespec)
    assert rulespec.is_for_services is True
    assert rulespec.item_type == "item"
    assert rulespec.item_name == "The object name"
    assert rulespec.item_help is None
    assert isinstance(rulespec.item_spec, TextInput)
    assert rulespec.match_type == "dict"
    assert rulespec.is_deprecated is False
    assert rulespec.is_optional is False

    # and also as static ruleset
    group = get_rulegroup("static/netblabla")
    assert group.name == "static/netblabla"
    assert group.title == "netblabla"

    rulespec_names = [
        r.name for r in cmk.gui.watolib.rulespecs.rulespec_registry.get_by_group("static/netblabla")
    ]
    assert "static_checks:bla_params" in rulespec_names
    assert len(rulespec_names) == 1
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry["static_checks:bla_params"]
    assert isinstance(rulespec, ManualCheckParameterRulespec)

    # Static checks rulespecs are always
    # a) host rulespecs
    # b) match_type == "all"
    assert rulespec.is_for_services is False
    assert rulespec.match_type == "all"

    assert rulespec.title == "Title of bla"
    assert rulespec.item_type is None
    assert rulespec.item_name is None
    assert rulespec.item_help is None
    # The item_spec of the ManualCheckParameterRulespec fetched differently,
    # since it is no actual item spec
    assert isinstance(rulespec._get_item_spec(), TextInput)
    assert rulespec.is_deprecated is False
    assert rulespec.is_optional is False

    # Static checks wrap the valuespec into a 3-element tuple
    # - check type selection
    # - item spec for the service description
    # - original valuespec (TimeperiodSelection)
    assert isinstance(rulespec.valuespec, Tuple)
    assert len(rulespec.valuespec._elements) == 3
    assert isinstance(rulespec.valuespec._elements[0], CheckTypeGroupSelection)
    assert isinstance(rulespec.valuespec._elements[1], ValueSpec)
    assert isinstance(rulespec.valuespec._elements[2], TimeperiodValuespec)


def test_register_host_check_parameters(patch_rulespec_registries) -> None:
    register_check_parameters(
        "netblabla",
        "bla_params",
        "Title of bla",
        Dictionary(
            elements=[],
        ),
        None,
        "dict",
    )

    # Check either registration as discovery check ruleset
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry["checkgroup_parameters:bla_params"]
    assert rulespec.is_for_services is False

    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry["static_checks:bla_params"]
    assert rulespec.is_for_services is False
    assert isinstance(rulespec.valuespec, Tuple)
    assert len(rulespec.valuespec._elements) == 3
    assert isinstance(rulespec.valuespec._elements[0], CheckTypeGroupSelection)
    assert isinstance(rulespec.valuespec._elements[1], ValueSpec)
    assert isinstance(rulespec.valuespec._elements[2], TimeperiodValuespec)


def test_register_without_discovery(patch_rulespec_registries) -> None:
    with pytest.raises(MKGeneralException, match="registering manual check"):
        register_check_parameters(
            "netblabla",
            "bla_params",
            "Title of bla",
            Dictionary(
                elements=[],
            ),
            None,
            "dict",
            has_inventory=False,
        )


def test_register_without_static(patch_rulespec_registries) -> None:
    register_check_parameters(
        "netblabla",
        "bla_params",
        "Title of bla",
        Dictionary(
            elements=[],
        ),
        None,
        "dict",
        has_inventory=True,
        register_static_check=False,
    )

    # Check either registration as discovery check ruleset
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry["checkgroup_parameters:bla_params"]
    assert rulespec.is_for_services is False

    assert "static_checks:bla_params" not in cmk.gui.watolib.rulespecs.rulespec_registry


class DummyGroup(RulespecGroup):
    @property
    def name(self) -> str:
        return "group"

    @property
    def title(self) -> str:
        return "Group title"

    @property
    def help(self):
        return "help text"


def test_rulespecs_get_by_group() -> None:
    group_registry = RulespecGroupRegistry()
    registry = RulespecRegistry(group_registry)

    with pytest.raises(KeyError):
        registry.get_by_group("group")

    group_registry.register(DummyGroup)
    result = registry.get_by_group("group")
    assert len(result) == 0

    registry.register(
        HostRulespec(name="dummy_name", group=DummyGroup, valuespec=lambda: FixedValue(value=None))
    )
    result = registry.get_by_group("group")
    assert len(result) == 1
    assert isinstance(result[0], HostRulespec)


def test_match_item_generator_rules() -> None:
    class SomeRulespecGroup(RulespecGroup):
        @property
        def name(self) -> str:
            return "rulespec_group"

        @property
        def title(self) -> str:
            return "Rulespec Group"

        @property
        def help(self):
            return ""

    rulespec_group_reg = RulespecGroupRegistry()
    rulespec_group_reg.register(SomeRulespecGroup)

    rulespec_reg = RulespecRegistry(rulespec_group_reg)
    rulespec_reg.register(
        HostRulespec(
            name="some_host_rulespec",
            group=SomeRulespecGroup,
            valuespec=lambda: TextInput(),  # pylint: disable=unnecessary-lambda
            title=lambda: "Title",  # pylint: disable=unnecessary-lambda
        )
    )
    rulespec_reg.register(
        HostRulespec(
            name="some_deprecated_host_rulespec",
            group=SomeRulespecGroup,
            valuespec=lambda: TextInput(),  # pylint: disable=unnecessary-lambda
            title=lambda: "Title",  # pylint: disable=unnecessary-lambda
            is_deprecated=True,
        )
    )

    match_item_generator = MatchItemGeneratorRules(
        "rules",
        rulespec_group_reg,
        rulespec_reg,
    )
    assert list(match_item_generator.generate_match_items()) == [
        MatchItem(
            title="Title",
            topic="Rulespec Group",
            url="wato.py?mode=edit_ruleset&varname=some_host_rulespec",
            match_texts=["title", "some_host_rulespec"],
        ),
        MatchItem(
            title="Title",
            topic="Deprecated rulesets",
            url="wato.py?mode=edit_ruleset&varname=some_deprecated_host_rulespec",
            match_texts=["title", "some_deprecated_host_rulespec"],
        ),
    ]


def test_all_rulespec_groups_have_main_group() -> None:
    for rulespec_group_name, rulespec_group_cls in rulespec_group_registry.items():
        if issubclass(rulespec_group_cls, RulespecGroup):
            main_module_from_rulespec_group_name(
                rulespec_group_name,
                main_module_registry,
            )


def test_rulespec_groups_have_unique_names() -> None:
    # The title is e.g. shown in the mega menu search. With duplicate entries a user could not
    # distinguish where a rule is located in the menu hierarchy.
    main_group_titles = [e().title for e in rulespec_group_registry.get_main_groups()]
    assert len(main_group_titles) == len(set(main_group_titles)), "Main group titles are not unique"


def test_validate_datatype_timeperiod_valuespec_inner() -> None:
    # make sure TimeperiodValuespec does propagate validate_datatype to its child
    value_spec = TimeperiodValuespec(Dictionary(elements=[]))
    with pytest.raises(MKUserError):
        value_spec.validate_datatype(["not", "a", "string"], "")  # type: ignore[arg-type]
