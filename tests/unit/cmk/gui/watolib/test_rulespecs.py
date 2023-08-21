#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest
from pytest import MonkeyPatch

import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.rulesets.definition import RuleGroup

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato
import cmk.gui.watolib.rulespecs
from cmk.gui.exceptions import MKUserError
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
        def main_group(self) -> type[RulespecGroup]:
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


def test_legacy_register_rulegroup(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )
    register_rulegroup("abc", "A B C", "abc 123")

    group = get_rulegroup("abc")
    assert isinstance(group, RulespecGroup)
    assert group.name == "abc"
    assert group.title == "A B C"
    assert group.help == "abc 123"


def test_legacy_get_not_existing_rulegroup(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )

    group = get_rulegroup("xyz")
    assert isinstance(group, cmk.gui.watolib.rulespecs.RulespecGroup)
    assert group.name == "xyz"
    assert group.title == "xyz"
    assert group.help is None


def test_legacy_get_not_existing_rule_sub_group(monkeypatch: MonkeyPatch) -> None:
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
            RuleGroup.StaticChecks("mtr"),
            RuleGroup.StaticChecks("palo_alto_sessions"),
            RuleGroup.StaticChecks("fortinet_signatures"),
            RuleGroup.StaticChecks("huawei_osn_laser"),
            RuleGroup.StaticChecks("brocade_optical"),
            RuleGroup.StaticChecks("fortigate_sessions"),
            RuleGroup.StaticChecks("fortigate_node_sessions"),
            RuleGroup.StaticChecks("cisco_asa_failover"),
            RuleGroup.StaticChecks("threepar_ports"),
            RuleGroup.StaticChecks("ipsecvpn"),
            RuleGroup.StaticChecks("hp_hh3c_ext_states"),
            RuleGroup.StaticChecks("fortisandbox_queues"),
            RuleGroup.StaticChecks("cisco_stack"),
            RuleGroup.StaticChecks("viprinet_router"),
            RuleGroup.StaticChecks("docsis_channels_upstream"),
            RuleGroup.StaticChecks("docsis_channels_downstream"),
            RuleGroup.StaticChecks("docsis_cm_status"),
            RuleGroup.StaticChecks("vpn_tunnel"),
            RuleGroup.StaticChecks("lsnat"),
            RuleGroup.StaticChecks("enterasys_powersupply"),
            RuleGroup.StaticChecks("hivemanager_devices"),
            RuleGroup.StaticChecks("hivemanager_ng_devices"),
            RuleGroup.StaticChecks("wlc_clients"),
            RuleGroup.StaticChecks("cisco_wlc"),
            RuleGroup.StaticChecks("tcp_conn_stats"),
            RuleGroup.StaticChecks("tcp_connections"),
            RuleGroup.StaticChecks("bonding"),
            RuleGroup.StaticChecks("if"),
            RuleGroup.StaticChecks("fcp"),
            RuleGroup.StaticChecks("signal_quality"),
            RuleGroup.StaticChecks("cisco_ip_sla"),
            RuleGroup.StaticChecks("cisco_qos"),
            RuleGroup.StaticChecks("mem_cluster"),
            RuleGroup.StaticChecks("cpu_utilization_cluster"),
            RuleGroup.StaticChecks("adva_ifs"),
            RuleGroup.StaticChecks("bluecat_ntp"),
            RuleGroup.StaticChecks("bluecat_dhcp"),
            RuleGroup.StaticChecks("bluecat_command_server"),
            RuleGroup.StaticChecks("bluecat_dns"),
            RuleGroup.StaticChecks("bluecat_ha"),
            RuleGroup.StaticChecks("steelhead_connections"),
        ],
        "eventconsole": [
            RuleGroup.ExtraHostConf("_ec_event_limit"),
            RuleGroup.ActiveChecks("mkevents"),
            RuleGroup.ExtraHostConf("_ec_contact"),
            RuleGroup.ExtraServiceConf("_ec_contact"),
        ],
        "agents/generic_options": [
            RuleGroup.AgentConfig("only_from"),
            RuleGroup.AgentConfig("package_name"),
            RuleGroup.AgentConfig("agent_paths"),
            RuleGroup.AgentConfig("real_time_checks"),
            RuleGroup.AgentConfig("mrpe"),
            RuleGroup.AgentConfig("custom_files"),
        ],
        "agents/windows_agent": [
            RuleGroup.AgentConfig("logging"),
            RuleGroup.AgentConfig("firewall"),
            RuleGroup.AgentConfig("win_controller"),
            RuleGroup.AgentConfig("win_clean_uninstall"),
            RuleGroup.AgentConfig("win_exe_suffixes"),
            RuleGroup.AgentConfig("win_agent_sections"),
            RuleGroup.AgentConfig("win_agent_disabled_sections"),
            RuleGroup.AgentConfig("win_script_async"),
            RuleGroup.AgentConfig("win_script_timeout"),
            RuleGroup.AgentConfig("win_script_cache_age"),
            RuleGroup.AgentConfig("win_script_retry_count"),
            RuleGroup.AgentConfig("win_script_execution"),
            RuleGroup.AgentConfig("win_set_wmi_timeout"),
            RuleGroup.AgentConfig("win_ps"),
            RuleGroup.AgentConfig("win_openhardwaremonitor"),
            RuleGroup.AgentConfig("win_robotmk"),
            RuleGroup.AgentConfig("win_printers"),
            RuleGroup.AgentConfig("mcafee_av_client"),
        ],
        "agents/windows_modules": [
            RuleGroup.AgentConfig("install_python"),
        ],
        "datasource_programs": [
            "datasource_programs",
            RuleGroup.SpecialAgents("ddn_s2a"),
            RuleGroup.SpecialAgents("kubernetes"),
            RuleGroup.SpecialAgents("vsphere"),
            RuleGroup.SpecialAgents("hp_msa"),
            RuleGroup.SpecialAgents("ipmi_sensors"),
            RuleGroup.SpecialAgents("netapp"),
            RuleGroup.SpecialAgents("activemq"),
            RuleGroup.SpecialAgents("emcvnx"),
            RuleGroup.SpecialAgents("ibmsvc"),
            RuleGroup.SpecialAgents("random"),
            RuleGroup.SpecialAgents("acme_sbc"),
            RuleGroup.SpecialAgents("fritzbox"),
            RuleGroup.SpecialAgents("innovaphone"),
            RuleGroup.SpecialAgents("hivemanager"),
            RuleGroup.SpecialAgents("hivemanager_ng"),
            RuleGroup.SpecialAgents("allnet_ip_sensoric"),
            RuleGroup.SpecialAgents("ucs_bladecenter"),
            RuleGroup.SpecialAgents("siemens_plc"),
            RuleGroup.SpecialAgents("ruckus_spot"),
            RuleGroup.SpecialAgents("appdynamics"),
            RuleGroup.SpecialAgents("jolokia"),
            RuleGroup.SpecialAgents("tinkerforge"),
            RuleGroup.SpecialAgents("prism"),
            RuleGroup.SpecialAgents("3par"),
            RuleGroup.SpecialAgents("storeonce"),
            RuleGroup.SpecialAgents("salesforce"),
            RuleGroup.SpecialAgents("azure"),
            RuleGroup.SpecialAgents("bi"),
            RuleGroup.SpecialAgents("aws"),
            RuleGroup.SpecialAgents("vnx_quotas"),
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
            "checkgroup_parameters:adva_ifs",
            "checkgroup_parameters:bluecat_ntp",
            "checkgroup_parameters:bluecat_dhcp",
            "checkgroup_parameters:bluecat_command_server",
            "checkgroup_parameters:bluecat_dns",
            "checkgroup_parameters:bluecat_ha",
            "checkgroup_parameters:steelhead_connections",
        ],
        "static/printers": [
            RuleGroup.StaticChecks("printer_supply"),
            RuleGroup.StaticChecks("cups_queues"),
            RuleGroup.StaticChecks("windows_printer_queues"),
            RuleGroup.StaticChecks("printer_input"),
            RuleGroup.StaticChecks("printer_output"),
        ],
        "static/applications": [
            RuleGroup.StaticChecks("f5_bigip_snat"),
            RuleGroup.StaticChecks("veritas_vcs"),
            RuleGroup.StaticChecks("f5_bigip_vserver"),
            RuleGroup.StaticChecks("cluster_status"),
            RuleGroup.StaticChecks("local"),
            RuleGroup.StaticChecks("threepar_remotecopy"),
            RuleGroup.StaticChecks("livestatus_status"),
            RuleGroup.StaticChecks("ad_replication"),
            RuleGroup.StaticChecks("mq_queues"),
            RuleGroup.StaticChecks("sshd_config"),
            RuleGroup.StaticChecks("websphere_mq"),
            RuleGroup.StaticChecks("websphere_mq_channels"),
            RuleGroup.StaticChecks("websphere_mq_manager"),
            RuleGroup.StaticChecks("websphere_mq_instance"),
            RuleGroup.StaticChecks("plesk_backups"),
            RuleGroup.StaticChecks("firewall_if"),
            RuleGroup.StaticChecks("kaspersky_av_client"),
            RuleGroup.StaticChecks("mcafee_av_client"),
            RuleGroup.StaticChecks("mcafee_web_gateway"),
            RuleGroup.StaticChecks("mcafee_web_gateway_misc"),
            RuleGroup.StaticChecks("mcafee_emailgateway_bridge"),
            RuleGroup.StaticChecks("pfsense_counter"),
            RuleGroup.StaticChecks("lnx_quota"),
            RuleGroup.StaticChecks("ruckus_mac"),
            RuleGroup.StaticChecks("ruckus_ap"),
            RuleGroup.StaticChecks("esx_licenses"),
            RuleGroup.StaticChecks("ibmsvc_licenses"),
            RuleGroup.StaticChecks("citrix_licenses"),
            RuleGroup.StaticChecks("rds_licenses"),
            RuleGroup.StaticChecks("win_license"),
            RuleGroup.StaticChecks("citrix_sessions"),
            RuleGroup.StaticChecks("citrix_state"),
            RuleGroup.StaticChecks("mssql_stats"),
            RuleGroup.StaticChecks("mssql_instance"),
            RuleGroup.StaticChecks("mssql_databases"),
            RuleGroup.StaticChecks("mssql_connections"),
            RuleGroup.StaticChecks("varnish_cache"),
            RuleGroup.StaticChecks("varnish_client"),
            RuleGroup.StaticChecks("varnish_backend"),
            RuleGroup.StaticChecks("varnish_fetch"),
            RuleGroup.StaticChecks("varnish_esi"),
            RuleGroup.StaticChecks("varnish_objects"),
            RuleGroup.StaticChecks("varnish_worker"),
            RuleGroup.StaticChecks("varnish_cache_hit_ratio"),
            RuleGroup.StaticChecks("varnish_backend_success_ratio"),
            RuleGroup.StaticChecks("varnish_worker_thread_ratio"),
            RuleGroup.StaticChecks("clr_memory"),
            RuleGroup.StaticChecks("skype_mobile"),
            RuleGroup.StaticChecks("skype_conferencing"),
            RuleGroup.StaticChecks("skype_sip"),
            RuleGroup.StaticChecks("skype_mediation_server"),
            RuleGroup.StaticChecks("skype_xmpp"),
            RuleGroup.StaticChecks("skype_edgeauth"),
            RuleGroup.StaticChecks("acme_certificates"),
            RuleGroup.StaticChecks("acme_sbc_snmp"),
            RuleGroup.StaticChecks("skype"),
            RuleGroup.StaticChecks("skype_proxy"),
            RuleGroup.StaticChecks("skype_edge"),
            RuleGroup.StaticChecks("ps"),
            RuleGroup.StaticChecks("generic_number"),
            RuleGroup.StaticChecks("generic_rate"),
            RuleGroup.StaticChecks("generic_string"),
            RuleGroup.StaticChecks("jvm_uptime"),
            RuleGroup.StaticChecks("netapp_systemtime"),
            RuleGroup.StaticChecks("jvm_sessions"),
            RuleGroup.StaticChecks("jvm_requests"),
            RuleGroup.StaticChecks("jvm_queue"),
            RuleGroup.StaticChecks("jvm_memory"),
            RuleGroup.StaticChecks("safenet_hsm_operstats"),
            RuleGroup.StaticChecks("safenet_hsm_eventstats"),
            RuleGroup.StaticChecks("safenet_ntls_links"),
            RuleGroup.StaticChecks("safenet_ntls_clients"),
            RuleGroup.StaticChecks("fireeye_active_vms"),
            RuleGroup.StaticChecks("fireeye_lic"),
            RuleGroup.StaticChecks("fireeye_quarantine"),
            RuleGroup.StaticChecks("fireeye_mailq"),
            RuleGroup.StaticChecks("fireeye_mail"),
            RuleGroup.StaticChecks("oracle_logswitches"),
            RuleGroup.StaticChecks("systemd_services"),
            RuleGroup.StaticChecks("hacmp_resources"),
            RuleGroup.StaticChecks("webserver"),
            RuleGroup.StaticChecks("aws_costs_and_usage"),
            RuleGroup.StaticChecks("aws_ec2_cpu_credits"),
            RuleGroup.StaticChecks("aws_rds_cpu_credits"),
            RuleGroup.StaticChecks("aws_elb_backend_connection_errors"),
            RuleGroup.StaticChecks("aws_elb_healthy_hosts"),
            RuleGroup.StaticChecks("aws_elb_http"),
            RuleGroup.StaticChecks("aws_elb_latency"),
            RuleGroup.StaticChecks("aws_elb_statistics"),
            RuleGroup.StaticChecks("azure_agent_info"),
            RuleGroup.StaticChecks("azure_databases"),
            RuleGroup.StaticChecks("azure_storageaccounts"),
            RuleGroup.StaticChecks("azure_vms"),
            RuleGroup.StaticChecks("azure_vms_summary"),
            RuleGroup.StaticChecks("azure_virtualnetworkgateways"),
            RuleGroup.StaticChecks("apache_status"),
            RuleGroup.StaticChecks("saprouter_cert_age"),
            RuleGroup.StaticChecks("sap_dialog"),
            RuleGroup.StaticChecks("nginx_status"),
            RuleGroup.StaticChecks("sles_license"),
            RuleGroup.StaticChecks("msx_info_store"),
            RuleGroup.StaticChecks("msx_rpcclientaccess"),
            RuleGroup.StaticChecks("msx_database"),
            RuleGroup.StaticChecks("msx_queues"),
            RuleGroup.StaticChecks("msexch_copyqueue"),
            RuleGroup.StaticChecks("services_summary"),
            RuleGroup.StaticChecks("solaris_services_summary"),
            RuleGroup.StaticChecks("esx_vsphere_objects"),
            RuleGroup.StaticChecks("esx_vsphere_objects_count"),
            RuleGroup.StaticChecks("oracle_tablespaces"),
            RuleGroup.StaticChecks("oracle_processes"),
            RuleGroup.StaticChecks("oracle_recovery_area"),
            RuleGroup.StaticChecks("oracle_dataguard_stats"),
            RuleGroup.StaticChecks("oracle_undostat"),
            RuleGroup.StaticChecks("oracle_rman"),
            RuleGroup.StaticChecks("oracle_recovery_status"),
            RuleGroup.StaticChecks("oracle_jobs"),
            RuleGroup.StaticChecks("oracle_instance"),
            RuleGroup.StaticChecks("oracle_sql"),
            RuleGroup.StaticChecks("asm_diskgroup"),
            RuleGroup.StaticChecks("mssql_backup"),
            RuleGroup.StaticChecks("mssql_backup_per_type"),
            RuleGroup.StaticChecks("mssql_file_sizes"),
            RuleGroup.StaticChecks("mssql_tablespaces"),
            RuleGroup.StaticChecks("mssql_page_activity"),
            RuleGroup.StaticChecks("mssql_transactionlogs"),
            RuleGroup.StaticChecks("mssql_datafiles"),
            RuleGroup.StaticChecks("vm_snapshots"),
            RuleGroup.StaticChecks("veeam_backup"),
            RuleGroup.StaticChecks("backup_timemachine"),
            RuleGroup.StaticChecks("job"),
            RuleGroup.StaticChecks("mssql_counters_locks"),
            RuleGroup.StaticChecks("mssql_blocked_sessions"),
            RuleGroup.StaticChecks("mssql_instance_blocked_sessions"),
            RuleGroup.StaticChecks("mysql_sessions"),
            RuleGroup.StaticChecks("mysql_innodb_io"),
            RuleGroup.StaticChecks("mysql_connections"),
            RuleGroup.StaticChecks("mysql_slave"),
            RuleGroup.StaticChecks("db_bloat"),
            RuleGroup.StaticChecks("db_connections"),
            RuleGroup.StaticChecks("postgres_locks"),
            RuleGroup.StaticChecks("postgres_maintenance"),
            RuleGroup.StaticChecks("f5_connections"),
            RuleGroup.StaticChecks("cisco_fw_connections"),
            RuleGroup.StaticChecks("checkpoint_connections"),
            RuleGroup.StaticChecks("checkpoint_packets"),
            RuleGroup.StaticChecks("f5_pools"),
            RuleGroup.StaticChecks("mysql_db_size"),
            RuleGroup.StaticChecks("postgres_sessions"),
            RuleGroup.StaticChecks("postgres_instance_sessions"),
            RuleGroup.StaticChecks("asa_svc_sessions"),
            RuleGroup.StaticChecks("oracle_sessions"),
            RuleGroup.StaticChecks("oracle_locks"),
            RuleGroup.StaticChecks("oracle_longactivesessions"),
            RuleGroup.StaticChecks("postgres_stat_database"),
            RuleGroup.StaticChecks("win_dhcp_pools"),
            RuleGroup.StaticChecks("vms_procs"),
            RuleGroup.StaticChecks("mailqueue_length"),
            RuleGroup.StaticChecks("mail_queue_length"),
            RuleGroup.StaticChecks("mail_latency"),
            RuleGroup.StaticChecks("services"),
            RuleGroup.StaticChecks("solaris_services"),
            RuleGroup.StaticChecks("winperf_ts_sessions"),
            RuleGroup.StaticChecks("mbg_lantime_state"),
            RuleGroup.StaticChecks("sansymphony_pool"),
            RuleGroup.StaticChecks("sansymphony_alerts"),
            RuleGroup.StaticChecks("jvm_threads"),
            RuleGroup.StaticChecks("sym_brightmail_queues"),
            RuleGroup.StaticChecks("db2_logsize"),
            RuleGroup.StaticChecks("db2_sortoverflow"),
            RuleGroup.StaticChecks("db2_tablespaces"),
            RuleGroup.StaticChecks("db2_connections"),
            RuleGroup.StaticChecks("db2_counters"),
            RuleGroup.StaticChecks("db2_backup"),
            RuleGroup.StaticChecks("db2_mem"),
            RuleGroup.StaticChecks("windows_updates"),
            RuleGroup.StaticChecks("synology_update"),
            RuleGroup.StaticChecks("antivir_update_age"),
            RuleGroup.StaticChecks("logwatch_ec"),
            RuleGroup.StaticChecks("wmic_process"),
            RuleGroup.StaticChecks("citrix_load"),
            RuleGroup.StaticChecks("jvm_gc"),
            RuleGroup.StaticChecks("jvm_tp"),
            RuleGroup.StaticChecks("docker_node_containers"),
            RuleGroup.StaticChecks("docker_node_disk_usage"),
            RuleGroup.StaticChecks("domino_tasks"),
            RuleGroup.StaticChecks("domino_mailqueues"),
            RuleGroup.StaticChecks("domino_users"),
            RuleGroup.StaticChecks("domino_transactions"),
            RuleGroup.StaticChecks("netscaler_dnsrates"),
            RuleGroup.StaticChecks("netscaler_tcp_conns"),
            RuleGroup.StaticChecks("netscaler_sslcerts"),
        ],
        "agents/linux_agent": [
            RuleGroup.AgentConfig("agent_user"),
            RuleGroup.AgentConfig("runas"),
            RuleGroup.AgentConfig("lnx_remote_alert_handlers"),
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
            RuleGroup.ActiveChecks("cmk_inv"),
            RuleGroup.InvParameters("inv_if"),
        ],
        "static/virtualization": [
            RuleGroup.StaticChecks("vm_state"),
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
            RuleGroup.ExtraHostConf("service_period"),
            RuleGroup.ExtraServiceConf("service_period"),
            "cmc_graphite_host_metrics",
            "cmc_graphite_service_metrics",
            "cmc_service_rrd_config",
            "cmc_host_rrd_config",
        ],
        "agents/automatic_updates": [
            RuleGroup.AgentConfig("cmk_update_agent"),
        ],
        "agent/general_settings": [
            "dyndns_hosts",
            "piggyback_translation",
            "primary_address_family",
            "service_description_translation",
        ],
        "static/os": [
            RuleGroup.StaticChecks("fortigate_node_memory"),
            RuleGroup.StaticChecks("uptime"),
            RuleGroup.StaticChecks("systemtime"),
            RuleGroup.StaticChecks("memory_pagefile_win"),
            RuleGroup.StaticChecks("sp_util"),
            RuleGroup.StaticChecks("innovaphone_mem"),
            RuleGroup.StaticChecks("mem_pages"),
            RuleGroup.StaticChecks("statgrab_mem"),
            RuleGroup.StaticChecks("cisco_mem"),
            RuleGroup.StaticChecks("juniper_mem"),
            RuleGroup.StaticChecks("juniper_mem_modules"),
            RuleGroup.StaticChecks("juniper_cpu_util"),
            RuleGroup.StaticChecks("netscaler_mem"),
            RuleGroup.StaticChecks("netscaler_vserver"),
            RuleGroup.StaticChecks("general_flash_usage"),
            RuleGroup.StaticChecks("cisco_supervisor_mem"),
            RuleGroup.StaticChecks("memory_linux"),
            RuleGroup.StaticChecks("memory"),
            RuleGroup.StaticChecks("memory_relative"),
            RuleGroup.StaticChecks("memory_simple"),
            RuleGroup.StaticChecks("memory_multiitem"),
            RuleGroup.StaticChecks("memory_arbor"),
            RuleGroup.StaticChecks("esx_host_memory"),
            RuleGroup.StaticChecks("vm_guest_tools"),
            RuleGroup.StaticChecks("vm_heartbeat"),
            RuleGroup.StaticChecks("cpu_load"),
            RuleGroup.StaticChecks("cpu_utilization"),
            RuleGroup.StaticChecks("cpu_utilization_multiitem"),
            RuleGroup.StaticChecks("fpga_utilization"),
            RuleGroup.StaticChecks("cpu_utilization_os"),
            RuleGroup.StaticChecks("cpu_iowait"),
            RuleGroup.StaticChecks("threads"),
            RuleGroup.StaticChecks("logins"),
            RuleGroup.StaticChecks("vm_counter"),
            RuleGroup.StaticChecks("pf_used_states"),
            RuleGroup.StaticChecks("ntp_time"),
            RuleGroup.StaticChecks("ntp_peer"),
            RuleGroup.StaticChecks("zypper"),
            RuleGroup.StaticChecks("apt"),
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
            RuleGroup.StaticChecks("hw_errors"),
        ],
        "checkparams/printers": [
            "checkgroup_parameters:printer_supply",
            "checkgroup_parameters:cups_queues",
            "checkgroup_parameters:windows_printer_queues",
            "checkgroup_parameters:printer_input",
            "checkgroup_parameters:printer_output",
        ],
        "static/storage": [
            RuleGroup.StaticChecks("disk_failures"),
            RuleGroup.StaticChecks("ddn_s2a_port_errors"),
            RuleGroup.StaticChecks("read_hits"),
            RuleGroup.StaticChecks("storage_iops"),
            RuleGroup.StaticChecks("storage_throughput"),
            RuleGroup.StaticChecks("ddn_s2a_wait"),
            RuleGroup.StaticChecks("blank_tapes"),
            RuleGroup.StaticChecks("mongodb_flushing"),
            RuleGroup.StaticChecks("mongodb_asserts"),
            RuleGroup.StaticChecks("mongodb_mem"),
            RuleGroup.StaticChecks("openhardwaremonitor_smart"),
            RuleGroup.StaticChecks("mongodb_locks"),
            RuleGroup.StaticChecks("inotify"),
            RuleGroup.StaticChecks("emcvnx_disks"),
            RuleGroup.StaticChecks("lvm_lvs_pools"),
            RuleGroup.StaticChecks("emcvnx_storage_pools"),
            RuleGroup.StaticChecks("emcvnx_storage_pools_tiering"),
            RuleGroup.StaticChecks("filehandler"),
            RuleGroup.StaticChecks("brocade_fcport"),
            RuleGroup.StaticChecks("brocade_sfp"),
            RuleGroup.StaticChecks("fcport_words"),
            RuleGroup.StaticChecks("fs_mount_options"),
            RuleGroup.StaticChecks("storcli_vdrives"),
            RuleGroup.StaticChecks("storcli_pdisks"),
            RuleGroup.StaticChecks("veeam_tapejobs"),
            RuleGroup.StaticChecks("ceph_status"),
            RuleGroup.StaticChecks("ceph_osds"),
            RuleGroup.StaticChecks("ceph_mgrs"),
            RuleGroup.StaticChecks("quantum_storage_status"),
            RuleGroup.StaticChecks("filesystem"),
            RuleGroup.StaticChecks("threepar_capacity"),
            RuleGroup.StaticChecks("threepar_cpgs"),
            RuleGroup.StaticChecks("nfsiostats"),
            RuleGroup.StaticChecks("fileinfo"),
            "static_checks:fileinfo-groups",
            RuleGroup.StaticChecks("filestats"),
            RuleGroup.StaticChecks("netapp_fcportio"),
            RuleGroup.StaticChecks("mongodb_collections"),
            RuleGroup.StaticChecks("volume_groups"),
            RuleGroup.StaticChecks("ibm_svc_mdiskgrp"),
            RuleGroup.StaticChecks("esx_vsphere_datastores"),
            RuleGroup.StaticChecks("esx_hostystem_maintenance"),
            RuleGroup.StaticChecks("ibm_svc_total_latency"),
            RuleGroup.StaticChecks("ibm_svc_host"),
            RuleGroup.StaticChecks("ibm_svc_mdisk"),
            RuleGroup.StaticChecks("diskstat"),
            RuleGroup.StaticChecks("disk_io"),
            RuleGroup.StaticChecks("zpool_status"),
            RuleGroup.StaticChecks("network_fs"),
            RuleGroup.StaticChecks("windows_multipath"),
            RuleGroup.StaticChecks("multipath"),
            RuleGroup.StaticChecks("multipath_count"),
            RuleGroup.StaticChecks("hpux_multipath"),
            RuleGroup.StaticChecks("drbd"),
            RuleGroup.StaticChecks("snapvault"),
            RuleGroup.StaticChecks("netapp_snapshots"),
            RuleGroup.StaticChecks("netapp_disks"),
            RuleGroup.StaticChecks("netapp_volumes"),
            RuleGroup.StaticChecks("netapp_luns"),
            RuleGroup.StaticChecks("raid"),
            RuleGroup.StaticChecks("raid_summary"),
            RuleGroup.StaticChecks("raid_disk"),
            RuleGroup.StaticChecks("pfm_health"),
            RuleGroup.StaticChecks("fc_port"),
            RuleGroup.StaticChecks("heartbeat_crm"),
            RuleGroup.StaticChecks("heartbeat_crm_resources"),
            RuleGroup.StaticChecks("bossock_fibers"),
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
            RuleGroup.ExtraHostConf("notifications_enabled"),
            RuleGroup.ExtraServiceConf("notifications_enabled"),
            RuleGroup.ExtraHostConf("notification_options"),
            RuleGroup.ExtraServiceConf("notification_options"),
            RuleGroup.ExtraHostConf("notification_period"),
            RuleGroup.ExtraServiceConf("notification_period"),
            RuleGroup.ExtraHostConf("first_notification_delay"),
            RuleGroup.ExtraServiceConf("first_notification_delay"),
            RuleGroup.ExtraHostConf("notification_interval"),
            RuleGroup.ExtraServiceConf("notification_interval"),
            RuleGroup.ExtraHostConf("flap_detection_enabled"),
            RuleGroup.ExtraServiceConf("flap_detection_enabled"),
            RuleGroup.ExtraServiceConf("notes_url"),
            RuleGroup.ExtraHostConf("notes_url"),
            RuleGroup.ExtraServiceConf("display_name"),
            RuleGroup.NotificationParameters("mail"),
            RuleGroup.NotificationParameters("slack"),
            RuleGroup.NotificationParameters("victorops"),
            RuleGroup.NotificationParameters("pagerduty"),
            RuleGroup.NotificationParameters("asciimail"),
            RuleGroup.NotificationParameters("mkeventd"),
            RuleGroup.NotificationParameters("spectrum"),
            RuleGroup.NotificationParameters("pushover"),
            RuleGroup.NotificationParameters("cisco_webex_teams"),
            "cmc_service_flap_settings",
            "cmc_host_flap_settings",
            "host_recurring_downtimes",
            "service_recurring_downtimes",
        ],
        "monconf/service_checks": [
            RuleGroup.ExtraServiceConf("max_check_attempts"),
            RuleGroup.ExtraServiceConf("check_interval"),
            RuleGroup.ExtraServiceConf("retry_interval"),
            RuleGroup.ExtraServiceConf("check_period"),
            "check_periods",
            RuleGroup.ExtraServiceConf("process_perf_data"),
            RuleGroup.ExtraServiceConf("passive_checks_enabled"),
            RuleGroup.ExtraServiceConf("active_checks_enabled"),
            "cmc_service_check_timeout",
            "service_state_translation",
        ],
        "user_interface": [
            RuleGroup.ExtraHostConf("icon_image"),
            RuleGroup.ExtraServiceConf("icon_image"),
            "host_icons_and_actions",
            "service_icons_and_actions",
            RuleGroup.ExtraHostConf("_ESCAPE_PLUGIN_OUTPUT"),
            RuleGroup.ExtraServiceConf("_ESCAPE_PLUGIN_OUTPUT"),
        ],
        "activechecks": [
            RuleGroup.ActiveChecks("ssh"),
            RuleGroup.ActiveChecks("icmp"),
            RuleGroup.ActiveChecks("ftp"),
            RuleGroup.ActiveChecks("sftp"),
            RuleGroup.ActiveChecks("dns"),
            RuleGroup.ActiveChecks("sql"),
            RuleGroup.ActiveChecks("tcp"),
            RuleGroup.ActiveChecks("uniserv"),
            RuleGroup.ActiveChecks("http"),
            RuleGroup.ActiveChecks("ldap"),
            RuleGroup.ActiveChecks("smtp"),
            RuleGroup.ActiveChecks("disk_smb"),
            "custom_checks",
            RuleGroup.ActiveChecks("bi_aggr"),
            RuleGroup.ActiveChecks("form_submit"),
            RuleGroup.ActiveChecks("notify_count"),
            RuleGroup.ActiveChecks("traceroute"),
            RuleGroup.ActiveChecks("mail_loop"),
            RuleGroup.ActiveChecks("mail"),
            RuleGroup.ActiveChecks("mailboxes"),
            RuleGroup.ActiveChecks("by_ssh"),
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
            RuleGroup.AgentConfig("jar_signature"),
            RuleGroup.AgentConfig("mailman_lists"),
            RuleGroup.AgentConfig("windows_multipath"),
            RuleGroup.AgentConfig("windows_updates"),
            RuleGroup.AgentConfig("isc_dhcpd"),
            RuleGroup.AgentConfig("lnx_quota"),
            RuleGroup.AgentConfig("mk_logins"),
            RuleGroup.AgentConfig("mk_iptables"),
            RuleGroup.AgentConfig("winperf"),
            RuleGroup.AgentConfig("win_eventlog"),
            RuleGroup.AgentConfig("fileinfo"),
            RuleGroup.AgentConfig("smart"),
            RuleGroup.AgentConfig("vxvm"),
            RuleGroup.AgentConfig("ad_replication"),
            RuleGroup.AgentConfig("windows_tasks"),
            RuleGroup.AgentConfig("winperf_if"),
            RuleGroup.AgentConfig("windows_broadcom_bonding"),
            RuleGroup.AgentConfig("mssql"),
            RuleGroup.AgentConfig("citrix_licenses"),
            RuleGroup.AgentConfig("citrix_xenapp"),
            RuleGroup.AgentConfig("hyperv_vms"),
            RuleGroup.AgentConfig("hyperv_vms_guestinfos"),
            RuleGroup.AgentConfig("arcserve_backup"),
            RuleGroup.AgentConfig("storcli"),
            RuleGroup.AgentConfig("win_megaraid"),
            RuleGroup.AgentConfig("rds_licenses"),
            RuleGroup.AgentConfig("win_license"),
            RuleGroup.AgentConfig("websphere_mq"),
            RuleGroup.AgentConfig("unitrends"),
            RuleGroup.AgentConfig("lvm"),
            RuleGroup.AgentConfig("nfsexports"),
            RuleGroup.AgentConfig("netstat"),
            RuleGroup.AgentConfig("symantec_av"),
            RuleGroup.AgentConfig("kaspersky_av"),
            RuleGroup.AgentConfig("win_dmidecode"),
            RuleGroup.AgentConfig("win_dhcp_pools"),
            RuleGroup.AgentConfig("mk_scaleio"),
            RuleGroup.AgentConfig("mk_cups_queues"),
            RuleGroup.AgentConfig("mk_inventory"),
            RuleGroup.AgentConfig("mk_apt"),
            RuleGroup.AgentConfig("mk_zypper"),
            RuleGroup.AgentConfig("plesk"),
            RuleGroup.AgentConfig("dnsclient"),
            RuleGroup.AgentConfig("mk_tsm"),
            RuleGroup.AgentConfig("mk_mysql"),
            RuleGroup.AgentConfig("db2_mem"),
            RuleGroup.AgentConfig("mk_postgres"),
            RuleGroup.AgentConfig("mk_mongodb"),
            RuleGroup.AgentConfig("mk_sshd_config"),
            RuleGroup.AgentConfig("mk_suseconnect"),
            RuleGroup.AgentConfig("mk_jolokia"),
            RuleGroup.AgentConfig("mk_saprouter"),
            RuleGroup.AgentConfig("mk_sap"),
            RuleGroup.AgentConfig("mk_logwatch"),
            RuleGroup.AgentConfig("mk_filestats"),
            RuleGroup.AgentConfig("nginx_status"),
            RuleGroup.AgentConfig("apache_status"),
            RuleGroup.AgentConfig("mk_oracle"),
            RuleGroup.AgentConfig("mtr"),
            RuleGroup.AgentConfig("mk_inotify"),
            RuleGroup.AgentConfig("msexch_dag"),
            RuleGroup.AgentConfig("msexch_database"),
            RuleGroup.AgentConfig("mk_site_object_counts"),
            RuleGroup.AgentConfig("mk_docker_container_piggybacked"),
            RuleGroup.AgentConfig("mk_docker_node"),
            RuleGroup.AgentConfig("veeam_backup_status"),
            RuleGroup.AgentConfig("mk_nfsiostat"),
        ],
        "static/environment": [
            RuleGroup.StaticChecks("voltage"),
            RuleGroup.StaticChecks("fan_failures"),
            RuleGroup.StaticChecks("pll_lock_voltage"),
            RuleGroup.StaticChecks("ipmi"),
            RuleGroup.StaticChecks("ps_voltage"),
            RuleGroup.StaticChecks("bvip_link"),
            RuleGroup.StaticChecks("ocprot_current"),
            RuleGroup.StaticChecks("brightness"),
            RuleGroup.StaticChecks("motion"),
            RuleGroup.StaticChecks("ewon"),
            RuleGroup.StaticChecks("lamp_operation_time"),
            RuleGroup.StaticChecks("apc_symentra"),
            RuleGroup.StaticChecks("hw_psu"),
            RuleGroup.StaticChecks("apc_system_events"),
            RuleGroup.StaticChecks("ups_test"),
            RuleGroup.StaticChecks("apc_power"),
            RuleGroup.StaticChecks("humidity"),
            RuleGroup.StaticChecks("single_humidity"),
            RuleGroup.StaticChecks("switch_contact"),
            RuleGroup.StaticChecks("plugs"),
            RuleGroup.StaticChecks("temperature"),
            RuleGroup.StaticChecks("room_temperature"),
            RuleGroup.StaticChecks("hw_single_temperature"),
            RuleGroup.StaticChecks("evolt"),
            RuleGroup.StaticChecks("efreq"),
            RuleGroup.StaticChecks("epower"),
            RuleGroup.StaticChecks("ups_out_load"),
            RuleGroup.StaticChecks("epower_single"),
            RuleGroup.StaticChecks("hw_temperature"),
            RuleGroup.StaticChecks("disk_temperature"),
            RuleGroup.StaticChecks("eaton_enviroment"),
            RuleGroup.StaticChecks("ups_outphase"),
            RuleGroup.StaticChecks("el_inphase"),
            RuleGroup.StaticChecks("hw_fans"),
            RuleGroup.StaticChecks("hw_fans_perc"),
            RuleGroup.StaticChecks("pdu_gude"),
            RuleGroup.StaticChecks("hostsystem_sensors"),
            RuleGroup.StaticChecks("netapp_instance"),
            RuleGroup.StaticChecks("temperature_auto"),
            RuleGroup.StaticChecks("temperature_trends"),
            RuleGroup.StaticChecks("smoke"),
            RuleGroup.StaticChecks("apc_ats_output"),
            RuleGroup.StaticChecks("airflow"),
            RuleGroup.StaticChecks("ups_capacity"),
            RuleGroup.StaticChecks("airflow_deviation"),
            RuleGroup.StaticChecks("plug_count"),
            RuleGroup.StaticChecks("ucs_bladecenter_chassis_voltage"),
            RuleGroup.StaticChecks("hp_msa_psu_voltage"),
            RuleGroup.StaticChecks("siemens_plc_flag"),
            RuleGroup.StaticChecks("siemens_plc_duration"),
            RuleGroup.StaticChecks("siemens_plc_counter"),
            RuleGroup.StaticChecks("carbon_monoxide"),
        ],
        "monconf/host_checks": [
            RuleGroup.ExtraHostConf("max_check_attempts"),
            RuleGroup.ExtraHostConf("check_interval"),
            RuleGroup.ExtraHostConf("retry_interval"),
            RuleGroup.ExtraHostConf("check_period"),
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
            RuleGroup.ExtraServiceConf("_sla_config"),
            RuleGroup.ExtraHostConf("_ec_sl"),
            RuleGroup.ExtraServiceConf("_ec_sl"),
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

    if cmk_version.edition() is not cmk_version.Edition.CRE:
        expected += [
            ("agents/agent_plugins", "&nbsp;&nbsp;\u2319 Agent Plugins"),
            ("agents/automatic_updates", "&nbsp;&nbsp;\u2319 Automatic Updates"),
            ("agents/linux_agent", "&nbsp;&nbsp;\u2319 Linux Agent"),
            ("agents/windows_agent", "&nbsp;&nbsp;\u2319 Windows Agent"),
            ("agents/windows_modules", "&nbsp;&nbsp;\u2319 Windows Modules"),
        ]

    return expected


@pytest.mark.parametrize(
    "result",
    [
        (_expected_rulespec_group_choices()),
    ],
)
def test_rulespec_group_choices(result: Sequence[tuple[str, str]]) -> None:
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
def test_rulespec_get_matching_group_names(term: str, result: Sequence[str]) -> None:
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
        "monconf/virtualization",
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

    if cmk_version.edition() is not cmk_version.Edition.CRE:
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

    if cmk_version.edition() is not cmk_version.Edition.CRE:
        expected_rulespec_host_groups += [
            "agents/agent_plugins",
            "agents/automatic_updates",
            "agents/linux_agent",
            "agents/windows_agent",
            "agents/windows_modules",
        ]

    group_names = rulespec_group_registry.get_host_rulespec_group_names(True)
    assert sorted(group_names) == sorted(expected_rulespec_host_groups)


def test_legacy_register_rule(monkeypatch: MonkeyPatch) -> None:
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


def test_legacy_register_rule_attributes(monkeypatch: MonkeyPatch) -> None:
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
    assert spec.title == "Deprecated: title"
    assert spec.help == "help me!"
    assert isinstance(spec.item_spec, TextInput)
    assert spec.item_type == "service"
    assert spec.item_name == "Blub"
    assert spec.item_help == "Item help"
    assert spec.is_optional is True
    assert spec.is_deprecated is True
    assert spec.factory_default == "humpf"


@pytest.fixture(name="patch_rulespec_registries")
def fixture_patch_rulespec_registries(monkeypatch: MonkeyPatch) -> None:
    group_registry = RulespecGroupRegistry()
    group_registry.register(RulespecGroupEnforcedServices)
    test_rulespec_registry = RulespecRegistry(group_registry)
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_registry", test_rulespec_registry)
    monkeypatch.setattr(cmk.gui.plugins.wato.utils, "rulespec_registry", test_rulespec_registry)


def test_register_check_parameters(patch_rulespec_registries: None) -> None:
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
    assert RuleGroup.StaticChecks("bla_params") in rulespec_names
    assert len(rulespec_names) == 1
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[RuleGroup.StaticChecks("bla_params")]
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


def test_register_host_check_parameters(patch_rulespec_registries: None) -> None:
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

    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[RuleGroup.StaticChecks("bla_params")]
    assert rulespec.is_for_services is False
    assert isinstance(rulespec.valuespec, Tuple)
    assert len(rulespec.valuespec._elements) == 3
    assert isinstance(rulespec.valuespec._elements[0], CheckTypeGroupSelection)
    assert isinstance(rulespec.valuespec._elements[1], ValueSpec)
    assert isinstance(rulespec.valuespec._elements[2], TimeperiodValuespec)


def test_register_without_discovery(patch_rulespec_registries: None) -> None:
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


def test_register_without_static(patch_rulespec_registries: None) -> None:
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

    assert RuleGroup.StaticChecks("bla_params") not in cmk.gui.watolib.rulespecs.rulespec_registry


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
            title="Deprecated: Title",
            topic="Deprecated rulesets",
            url="wato.py?mode=edit_ruleset&varname=some_deprecated_host_rulespec",
            match_texts=["deprecated: title", "some_deprecated_host_rulespec"],
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
