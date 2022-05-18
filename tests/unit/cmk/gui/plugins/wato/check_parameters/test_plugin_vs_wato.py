#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import typing as t

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.inventory_classes import InventoryPlugin
from cmk.base.api.agent_based.type_defs import ParametersTypeAlias

from cmk.gui.plugins.wato.inventory import RulespecGroupInventory
from cmk.gui.plugins.wato.utils import RulespecGroupCheckParametersDiscovery
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    Rulespec,
    rulespec_registry,
)

T = t.TypeVar("T")
TF = t.TypeVar("TF", bound=Rulespec)
TC = t.TypeVar("TC", bound=t.Union[CheckPlugin, InventoryPlugin])


class FixRegister:  # TODO: make the original class importable?!
    check_plugins: t.Dict[str, CheckPlugin]
    inventory_plugins: t.Dict[str, InventoryPlugin]


class MergeKey(t.NamedTuple):
    type_name: str
    name: str


class DefaultLoadingFailed(BaseException):
    pass


class Base(t.Generic[T], abc.ABC):
    type: str

    def __init__(self, element: T):
        self._element: T = element

    @abc.abstractmethod
    def get_merge_name(self) -> str:
        """
        return name by which Wato and Plugin lists are merged
        """
        ...

    def get_name(self) -> str:
        """
        return name that identifies this element
        """
        return self.get_merge_name()

    def get_merge_key(self) -> MergeKey:
        return MergeKey(self.type, self.get_merge_name())

    @abc.abstractmethod
    def get_description(self) -> str:
        """
        return human readable uniqe identifier for this element
        """
        ...

    def __lt__(self, other: object) -> bool:
        if other is None or not isinstance(other, Base):
            raise ValueError()
        return self.get_merge_key() < other.get_merge_key()

    def __eq__(self, other: object) -> bool:
        if other is None or not isinstance(other, Base):
            return False
        return self.get_merge_key() == other.get_merge_key()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self._element}>"


class BaseProtocol(t.Protocol):
    type: str

    def get_name(self) -> str:
        ...

    def get_merge_name(self) -> str:
        ...

    def get_description(self) -> str:
        ...

    def __eq__(self, other: object) -> bool:
        ...

    def __lt__(self, other: object) -> bool:
        ...


class WatoProtocol(BaseProtocol, t.Protocol):
    def validate_parameter(
        self, parameters: t.Optional[ParametersTypeAlias]
    ) -> t.Optional[Exception]:
        ...


class PluginProtocol(BaseProtocol, t.Protocol):
    def get_default_parameters(self) -> t.Optional[ParametersTypeAlias]:
        ...


class Plugin(Base[TC], abc.ABC):
    def get_description(self) -> str:
        return f"{self.type}-plugin '{self.get_name()}'"

    def get_name(self) -> str:
        return str(self._element.name)

    @abc.abstractmethod
    def get_default_parameters(self) -> t.Optional[ParametersTypeAlias]:
        ...


class PluginDiscovery(Plugin[CheckPlugin]):
    type = "discovery"

    def get_merge_name(self) -> str:
        assert self._element.discovery_ruleset_name
        return str(self._element.discovery_ruleset_name)

    def get_default_parameters(self) -> t.Optional[ParametersTypeAlias]:
        return self._element.discovery_default_parameters


class PluginInventory(Plugin[InventoryPlugin]):
    type = "inventory"

    def get_merge_name(self) -> str:
        assert self._element.inventory_ruleset_name
        return str(self._element.inventory_ruleset_name)

    def get_default_parameters(self) -> t.Optional[ParametersTypeAlias]:
        return self._element.inventory_default_parameters


class PluginCheck(Plugin[CheckPlugin]):
    type = "check"

    def get_merge_name(self) -> str:
        assert self._element.check_ruleset_name
        return str(self._element.check_ruleset_name)

    def get_default_parameters(self) -> t.Optional[ParametersTypeAlias]:
        return self._element.check_default_parameters

    def has_item(self) -> bool:
        return "%" in self._element.service_name


class Wato(Base[TF]):
    def get_description(self) -> str:
        return f"wato {self.type}-rule '{self.get_name()}'"

    def validate_parameter(
        self, parameters: t.Optional[ParametersTypeAlias]
    ) -> t.Optional[Exception]:
        try:
            self._element.valuespec.validate_datatype(parameters, "")
            self._element.valuespec.validate_value(parameters, "")
        except Exception as exception:
            return exception
        return None


class WatoDiscovery(Wato[Rulespec]):
    type = "discovery"

    def get_merge_name(self) -> str:
        return self._element.name


class WatoInventory(Wato[Rulespec]):
    type = "inventory"

    def get_merge_name(self) -> str:
        return self._element.name


class WatoCheck(Wato[t.Union[CheckParameterRulespecWithoutItem, CheckParameterRulespecWithItem]]):
    type = "check"

    def get_merge_name(self) -> str:
        return self._element.check_group_name

    def get_name(self) -> str:
        return self._element.name

    def has_item(self) -> bool:
        return isinstance(self._element, CheckParameterRulespecWithItem)


def load_plugin(fix_register: FixRegister) -> t.Iterator[PluginProtocol]:
    for check_element in fix_register.check_plugins.values():
        if check_element.check_ruleset_name is not None:
            yield PluginCheck(check_element)
    for discovery_element in fix_register.check_plugins.values():
        if discovery_element.discovery_ruleset_name is not None:
            yield PluginDiscovery(discovery_element)
    for inventory_element in fix_register.inventory_plugins.values():
        if inventory_element.inventory_ruleset_name is not None:
            yield PluginInventory(inventory_element)


def load_wato() -> t.Iterator[WatoProtocol]:
    for element in rulespec_registry.values():
        if element.group == RulespecGroupCheckParametersDiscovery:
            yield WatoDiscovery(element)
        elif element.group == RulespecGroupInventory:
            yield WatoInventory(element)
        elif isinstance(
            element,
            (
                CheckParameterRulespecWithItem,
                CheckParameterRulespecWithoutItem,
            ),
        ):
            yield WatoCheck(element)


def test_plugin_vs_wato(fix_register: FixRegister) -> None:
    error_reporter = ErrorReporter()
    for plugin, wato in merge(sorted(load_plugin(fix_register)), sorted(load_wato())):
        if plugin is None and wato is not None:
            error_reporter.report_wato_unused(wato)
        elif wato is None and plugin is not None:
            error_reporter.report_wato_missing(plugin)
        else:
            assert plugin is not None and wato is not None, "something is wrong with merge()"
            error_reporter.run_tests(plugin, wato)

    error_reporter.raise_last_default_loading_exception()
    assert not error_reporter.failed()
    error_reporter.test_for_vanished_known_problems()


class ErrorReporter:
    KNOWN_WATO_UNUSED = {
        # type # name
        ("check", "checkgroup_parameters:checkmk_agent_plugins"),
        ("check", "checkgroup_parameters:ceph_status"),
        ("check", "checkgroup_parameters:disk_temperature"),
        ("check", "checkgroup_parameters:entersekt_soaprrors"),
        ("check", "checkgroup_parameters:hw_single_temperature"),
        ("check", "checkgroup_parameters:hw_temperature"),
        ("check", "checkgroup_parameters:hw_temperature_single"),
        ("check", "checkgroup_parameters:mailqueue_length"),
        ("check", "checkgroup_parameters:mssql_blocked_sessions"),
        ("check", "checkgroup_parameters:postgres_sessions"),
        ("check", "checkgroup_parameters:room_temperature"),
        ("check", "checkgroup_parameters:ruckus_mac"),
        ("check", "checkgroup_parameters:statgrab_mem"),
        ("check", "checkgroup_parameters:temperature_trends"),
        ("discovery", "brocade_fcport_inventory"),
        ("discovery", "discovery_cisco_dom_rules"),
        ("discovery", "discovery_hr_processes_rules"),
        ("discovery", "discovery_mssql_backup"),
        ("discovery", "discovery_netapp_api_fan_rules"),
        ("discovery", "discovery_netapp_api_ports_ignored"),
        ("discovery", "discovery_netapp_api_psu_rules"),
        ("discovery", "discovery_win_dhcp_pools"),
        ("discovery", "ewon_discovery_rules"),
        ("discovery", "inventory_df_rules"),
        ("discovery", "inventory_fujitsu_ca_ports"),
        ("discovery", "inventory_heartbeat_crm_rules"),
        ("discovery", "inventory_sap_values"),
        ("discovery", "inventory_solaris_services_rules"),
        ("discovery", "oracle_performance_discovery"),
        ("discovery", "sap_value_groups"),
        ("inventory", "active_checks:cmk_inv"),
        ("inventory", "inv_exports:software_csv"),
        ("inventory", "inv_parameters:inv_if"),
        ("inventory", "inv_parameters:lnx_sysctl"),
        ("inventory", "inv_retention_intervals"),
    }
    KNOWN_ITEM_REQUIREMENTS = {
        # type # plugin # wato
        ("check", "azure_ad_sync", "checkgroup_parameters:azure_ad"),
        ("check", "azure_agent_info", "checkgroup_parameters:azure_agent_info"),
        ("check", "checkpoint_memory", "checkgroup_parameters:memory_simple"),
        ("check", "cisco_cpu_memory", "checkgroup_parameters:cisco_cpu_memory"),
        ("check", "datapower_mem", "checkgroup_parameters:memory_simple"),
        ("check", "f5_bigip_mem", "checkgroup_parameters:memory_simple"),
        ("check", "f5_bigip_mem_tmm", "checkgroup_parameters:memory_simple"),
        ("check", "haproxy_frontend", "checkgroup_parameters:haproxy_frontend"),
        ("check", "haproxy_server", "checkgroup_parameters:haproxy_server"),
        ("check", "hp_procurve_mem", "checkgroup_parameters:memory_simple"),
        ("check", "k8s_pods_cpu", "checkgroup_parameters:k8s_pods_cpu"),
        ("check", "k8s_pods_fs", "checkgroup_parameters:k8s_pods_fs"),
        ("check", "k8s_pods_memory", "checkgroup_parameters:k8s_pods_memory"),
        ("check", "mongodb_replica_set", "checkgroup_parameters:mongodb_replica_set"),
        ("check", "mongodb_replica_set_election", "checkgroup_parameters:mongodb_replica_set"),
        ("check", "netapp_fcpio", "checkgroup_parameters:netapp_fcportio"),
        (
            "check",
            "systemd_units_services_summary",
            "checkgroup_parameters:systemd_services_summary",
        ),
        ("check", "ucd_mem", "checkgroup_parameters:memory_simple"),
    }
    KNOWN_WATO_MISSING = {
        # type # instance # wato
        ("check", "3ware_units", "raid"),
        ("check", "brocade_tm", "brocade_tm"),
        ("check", "checkpoint_vsx_status", "checkpoint_vsx_traffic_status"),
        ("check", "domino_tasks", "domino_tasks"),
        ("check", "drbd_disk", "drbd.disk"),
        ("check", "drbd_net", "drbd.net"),
        ("check", "drbd_stats", "drbd.stats"),
        ("check", "entersekt_soaperrors", "entersekt_soaperrors"),
        ("check", "h3c_lanswitch_cpu", "h3c_lanswitch_cpu"),
        ("check", "h3c_lanswitch_sensors", "h3c_lanswitch_sensors"),
        ("check", "hpux_snmp_cs_cpu", "hpux_snmp_cs.cpu"),
        ("check", "innovaphone_channels", "hw_single_channelserature"),
        ("check", "ironport_misc", "obsolete"),
        ("check", "j4p_performance_app_sess", "j4p_performance.app_sess"),
        ("check", "j4p_performance_app_state", "j4p_performance.app_state"),
        ("check", "j4p_performance_mem", "j4p_performance.mem"),
        ("check", "j4p_performance_serv_req", "j4p_performance.serv_req"),
        ("check", "j4p_performance_threads", "j4p_performance.threads"),
        ("check", "j4p_performance_uptime", "j4p_performance.uptime"),
        ("check", "lgp_pdu_aux", "lgp_pdu_aux"),
        ("check", "lsi_array", "raid"),
        ("check", "md", "raid"),
        ("check", "mongodb_replication_info", "mongodb_replication_info"),
        ("check", "moxa_iologik_register", "iologik_register"),
        ("check", "netstat", "tcp_connections"),
        ("check", "nvidia_errors", "hw_errors"),
        ("check", "qlogic_fcport", "qlogic_fcport"),
        ("check", "sap_hana_proc", "sap_hana_proc"),
        ("check", "stormshield_cluster_node", "stormshield_quality"),
        ("check", "stormshield_policy", "stormshield"),
        ("check", "stormshield_updates", "stormshield_updates"),
        ("check", "tsm_stagingpools", "tsm_stagingspools"),
        ("check", "vbox_guest", "vm_state"),
        ("check", "win_netstat", "tcp_connections"),
        ("check", "wmic_process", "wmic_process"),
        ("check", "zerto_vpg_rpo", "zerto_vpg_rpo"),
        ("check", "zertificon_mail_queues", "zertificon_mail_queues"),
        ("check", "zpool_status", "zpool_status"),
        ("check", "zypper", "zypper"),
        ("discovery", "fileinfo", "fileinfo_groups"),
        ("discovery", "fileinfo_groups", "fileinfo_groups"),
        ("discovery", "sap_hana_fileinfo", "fileinfo_groups"),
        ("discovery", "sap_hana_fileinfo_groups", "fileinfo_groups"),
        ("discovery", "logwatch_groups", "logwatch_groups"),
        ("discovery", "logwatch", "logwatch_groups"),
        ("inventory", "inv_if", "inv_if"),
        ("inventory", "lnx_sysctl", "lnx_sysctl"),
        ("inventory", "suseconnect", "suseconnect"),
    }
    KNOWN_ERROR_LOADING_DEFAULTS = {
        # type # plugin # wato
        ("check", "3par_remotecopy", "checkgroup_parameters:threepar_remotecopy"),
        ("check", "ad_replication", "checkgroup_parameters:ad_replication"),
        ("check", "apc_ats_output", "checkgroup_parameters:apc_ats_output"),
        ("check", "apc_humidity", "checkgroup_parameters:humidity"),
        ("check", "apc_symmetra", "checkgroup_parameters:apc_symentra"),
        ("check", "apc_symmetra_power", "checkgroup_parameters:apc_power"),
        ("check", "apc_symmetra_temp", "checkgroup_parameters:temperature"),
        ("check", "apc_symmetra_test", "checkgroup_parameters:ups_test"),
        ("check", "appdynamics_sessions", "checkgroup_parameters:jvm_sessions"),
        ("check", "appdynamics_web_container", "checkgroup_parameters:jvm_threads"),
        ("check", "avaya_88xx_cpu", "checkgroup_parameters:cpu_utilization"),
        (
            "check",
            "aws_dynamodb_table_read_capacity",
            "checkgroup_parameters:aws_dynamodb_capacity",
        ),
        (
            "check",
            "aws_dynamodb_table_write_capacity",
            "checkgroup_parameters:aws_dynamodb_capacity",
        ),
        ("check", "barracuda_mail_latency", "checkgroup_parameters:mail_latency"),
        ("check", "blade_bx_powerfan", "checkgroup_parameters:hw_fans_perc"),
        ("check", "bluenet2_powerrail_rcm", "checkgroup_parameters:el_inphase"),
        ("check", "brocade_fan", "checkgroup_parameters:hw_fans"),
        ("check", "brocade_mlx_module_mem", "checkgroup_parameters:memory_multiitem"),
        ("check", "brocade_optical", "checkgroup_parameters:brocade_optical"),
        ("check", "brocade_sys_mem", "checkgroup_parameters:memory_relative"),
        ("check", "bvip_fans", "checkgroup_parameters:hw_fans"),
        ("check", "bvip_poe", "checkgroup_parameters:epower_single"),
        ("check", "casa_cpu_mem", "checkgroup_parameters:memory_multiitem"),
        ("check", "ceph_status_mgrs", "checkgroup_parameters:ceph_mgrs"),
        ("check", "ceph_status_osds", "checkgroup_parameters:ceph_osds"),
        (
            "check",
            "cisco_prime_wifi_access_points",
            "checkgroup_parameters:cisco_prime_wifi_access_points",
        ),
        (
            "check",
            "cisco_prime_wifi_connections",
            "checkgroup_parameters:cisco_prime_wifi_connections",
        ),
        ("check", "cisco_sys_mem", "checkgroup_parameters:cisco_supervisor_mem"),
        ("check", "citrix_licenses", "checkgroup_parameters:citrix_licenses"),
        ("check", "citrix_serverload", "checkgroup_parameters:citrix_load"),
        ("check", "couchbase_buckets_mem", "checkgroup_parameters:memory_multiitem"),
        ("check", "datapower_cpu", "checkgroup_parameters:cpu_utilization"),
        ("check", "db2_backup", "checkgroup_parameters:db2_backup"),
        ("check", "db2_mem", "checkgroup_parameters:db2_mem"),
        ("check", "ddn_s2a_faultsbasic_disks", "checkgroup_parameters:disk_failures"),
        ("check", "ddn_s2a_faultsbasic_fans", "checkgroup_parameters:fan_failures"),
        ("check", "ddn_s2a_stats_io", "checkgroup_parameters:storage_iops"),
        ("check", "ddn_s2a_stats_readhits", "checkgroup_parameters:read_hits"),
        ("check", "dell_idrac_fans", "checkgroup_parameters:hw_fans"),
        ("check", "dell_om_fans", "checkgroup_parameters:hw_fans"),
        ("check", "docsis_channels_upstream", "checkgroup_parameters:docsis_channels_upstream"),
        ("check", "domino_transactions", "checkgroup_parameters:domino_transactions"),
        ("check", "domino_users", "checkgroup_parameters:domino_users"),
        ("check", "eltek_fans", "checkgroup_parameters:hw_fans_perc"),
        ("check", "emc_isilon_power", "checkgroup_parameters:evolt"),
        ("check", "emcvnx_sp_util", "checkgroup_parameters:sp_util"),
        ("check", "enterasys_lsnat", "checkgroup_parameters:lsnat"),
        ("check", "enviromux_aux_voltage", "checkgroup_parameters:voltage"),
        ("check", "enviromux_external_voltage", "checkgroup_parameters:voltage"),
        ("check", "enviromux_sems_external_voltage", "checkgroup_parameters:voltage"),
        ("check", "enviromux_sems_voltage", "checkgroup_parameters:voltage"),
        ("check", "enviromux_voltage", "checkgroup_parameters:voltage"),
        ("check", "epson_beamer_lamp", "checkgroup_parameters:lamp_operation_time"),
        ("check", "esx_vsphere_licenses", "checkgroup_parameters:esx_licenses"),
        ("check", "esx_vsphere_objects_count", "checkgroup_parameters:esx_vsphere_objects_count"),
        ("check", "esx_vsphere_sensors", "checkgroup_parameters:hostsystem_sensors"),
        ("check", "esx_vsphere_vm_guest_tools", "checkgroup_parameters:vm_guest_tools"),
        ("check", "esx_vsphere_vm_heartbeat", "checkgroup_parameters:vm_heartbeat"),
        ("check", "etherbox_switch", "checkgroup_parameters:switch_contact"),
        ("check", "f5_bigip_fans", "checkgroup_parameters:hw_fans"),
        ("check", "f5_bigip_pool", "checkgroup_parameters:f5_pools"),
        ("check", "fortigate_antivirus", "checkgroup_parameters:fortigate_antivirus"),
        ("check", "fortigate_ips", "checkgroup_parameters:fortigate_ips"),
        ("check", "fortigate_ipsecvpn", "checkgroup_parameters:ipsecvpn"),
        ("check", "fortigate_memory", "checkgroup_parameters:memory"),
        ("check", "fortigate_node_sessions", "checkgroup_parameters:fortigate_node_sessions"),
        ("check", "fortigate_sessions_base", "checkgroup_parameters:fortigate_sessions"),
        ("check", "fortigate_sessions", "checkgroup_parameters:fortigate_sessions"),
        ("check", "fortimail_cpu_load", "checkgroup_parameters:fortimail_cpu_load"),
        ("check", "fortimail_disk_usage", "checkgroup_parameters:fortimail_disk_usage"),
        ("check", "genua_pfstate", "checkgroup_parameters:pf_used_states"),
        ("check", "heartbeat_crm_resources", "checkgroup_parameters:heartbeat_crm_resources"),
        ("check", "hitachi_hnas_bossock", "checkgroup_parameters:bossock_fibers"),
        ("check", "hivemanager_devices", "checkgroup_parameters:hivemanager_devices"),
        ("check", "hp_proliant_power", "checkgroup_parameters:epower_single"),
        ("check", "hp_proliant_psu", "checkgroup_parameters:hw_psu"),
        ("check", "hpux_multipath", "checkgroup_parameters:hpux_multipath"),
        ("check", "huawei_osn_laser", "checkgroup_parameters:huawei_osn_laser"),
        ("check", "ibm_imm_fan", "checkgroup_parameters:hw_fans_perc"),
        ("check", "ibm_svc_license", "checkgroup_parameters:ibmsvc_licenses"),
        ("check", "icom_repeater_ps_volt", "checkgroup_parameters:ps_voltage"),
        ("check", "innovaphone_mem", "checkgroup_parameters:innovaphone_mem"),
        ("check", "inotify", "checkgroup_parameters:inotify"),
        ("check", "ipr400_in_voltage", "checkgroup_parameters:evolt"),
        ("check", "janitza_umg_freq", "checkgroup_parameters:efreq"),
        ("check", "jolokia_metrics_app_sess", "checkgroup_parameters:jvm_sessions"),
        ("check", "jolokia_metrics_bea_queue", "checkgroup_parameters:jvm_queue"),
        ("check", "jolokia_metrics_bea_requests", "checkgroup_parameters:jvm_requests"),
        ("check", "jolokia_metrics_bea_sess", "checkgroup_parameters:jvm_sessions"),
        ("check", "jolokia_metrics_bea_threads", "checkgroup_parameters:jvm_threads"),
        ("check", "jolokia_metrics_requests", "checkgroup_parameters:jvm_requests"),
        ("check", "jolokia_metrics_serv_req", "checkgroup_parameters:jvm_requests"),
        ("check", "juniper_mem", "checkgroup_parameters:juniper_mem_modules"),
        ("check", "juniper_screenos_mem", "checkgroup_parameters:juniper_mem"),
        ("check", "juniper_trpz_flash", "checkgroup_parameters:general_flash_usage"),
        ("check", "juniper_trpz_mem", "checkgroup_parameters:juniper_mem"),
        ("check", "keepalived", "checkgroup_parameters:keepalived"),
        ("check", "kernel", "checkgroup_parameters:vm_counter"),
        ("check", "knuerr_rms_humidity", "checkgroup_parameters:single_humidity"),
        ("check", "liebert_cooling", "checkgroup_parameters:liebert_cooling"),
        ("check", "liebert_cooling_position", "checkgroup_parameters:liebert_cooling_position"),
        ("check", "liebert_fans", "checkgroup_parameters:hw_fans_perc"),
        ("check", "liebert_fans_condenser", "checkgroup_parameters:hw_fans_perc"),
        ("check", "liebert_humidity_air", "checkgroup_parameters:humidity"),
        ("check", "lnx_quota", "checkgroup_parameters:lnx_quota"),
        ("check", "logins", "checkgroup_parameters:logins"),
        ("check", "logwatch_ec", "checkgroup_parameters:logwatch_ec"),
        ("check", "lvm_vgs", "checkgroup_parameters:volume_groups"),
        ("check", "mikrotik_signal", "checkgroup_parameters:signal_quality"),
        ("check", "mongodb_collections", "checkgroup_parameters:mongodb_collections"),
        ("check", "mounts", "checkgroup_parameters:fs_mount_options"),
        ("check", "mq_queues", "checkgroup_parameters:mq_queues"),
        ("check", "msexch_dag_copyqueue", "checkgroup_parameters:msexch_copyqueue"),
        ("check", "msexch_isclienttype", "checkgroup_parameters:msx_info_store"),
        ("check", "msexch_isstore", "checkgroup_parameters:msx_info_store"),
        ("check", "mssql_connections", "checkgroup_parameters:mssql_connections"),
        ("check", "mssql_jobs", "checkgroup_parameters:mssql_jobs"),
        ("check", "multipath", "checkgroup_parameters:multipath"),
        ("check", "mysql_slave", "checkgroup_parameters:mysql_slave"),
        ("check", "netapp_api_connection", "checkgroup_parameters:netapp_instance"),
        ("check", "netapp_api_cpu_utilization", "checkgroup_parameters:cpu_utilization"),
        ("check", "netapp_api_environment_fan_faults", "checkgroup_parameters:hw_fans"),
        ("check", "netapp_api_environment_fans", "checkgroup_parameters:hw_fans"),
        ("check", "netscaler_health_fan", "checkgroup_parameters:hw_fans"),
        ("check", "netscaler_mem", "checkgroup_parameters:netscaler_mem"),
        ("check", "openhardwaremonitor_fan", "checkgroup_parameters:hw_fans"),
        ("check", "openhardwaremonitor_smart", "checkgroup_parameters:openhardwaremonitor_smart"),
        ("check", "openhardwaremonitor_temperature", "checkgroup_parameters:temperature"),
        ("check", "oracle_diva_csm_tapes", "checkgroup_parameters:blank_tapes"),
        ("check", "plesk_backups", "checkgroup_parameters:plesk_backups"),
        ("check", "prometheus_custom", "checkgroup_parameters:prometheus_custom"),
        ("check", "ps", "checkgroup_parameters:ps"),
        ("check", "pulse_secure_mem_util", "checkgroup_parameters:pulse_secure_mem_util"),
        ("check", "pulse_secure_users", "checkgroup_parameters:pulse_secure_users"),
        ("check", "qnap_fans", "checkgroup_parameters:hw_fans"),
        ("check", "quanta_fan", "checkgroup_parameters:hw_fans"),
        ("check", "ra32e_switch", "checkgroup_parameters:switch_contact"),
        ("check", "rabbitmq_nodes_mem", "checkgroup_parameters:memory_multiitem"),
        ("check", "raritan_pdu_ocprot", "checkgroup_parameters:ocprot_current"),
        ("check", "raritan_pdu_outletcount", "checkgroup_parameters:plug_count"),
        ("check", "rds_licenses", "checkgroup_parameters:rds_licenses"),
        ("check", "redis_info_persistence", "checkgroup_parameters:redis_info_persistence"),
        ("check", "ruckus_spot_ap", "checkgroup_parameters:ruckus_ap"),
        ("check", "safenet_ntls_clients", "checkgroup_parameters:safenet_ntls_clients"),
        ("check", "safenet_ntls_links", "checkgroup_parameters:safenet_ntls_links"),
        ("check", "sansymphony_alerts", "checkgroup_parameters:sansymphony_alerts"),
        ("check", "sansymphony_pool", "checkgroup_parameters:sansymphony_pool"),
        ("check", "siemens_plc_flag", "checkgroup_parameters:siemens_plc_flag"),
        ("check", "skype_conferencing", "checkgroup_parameters:skype_conferencing"),
        ("check", "skype_sip_stack", "checkgroup_parameters:skype_sip"),
        ("check", "solaris_multipath", "checkgroup_parameters:multipath"),
        ("check", "symantec_av_updates", "checkgroup_parameters:antivir_update_age"),
        ("check", "tinkerforge_ambient", "checkgroup_parameters:brightness"),
        ("check", "tplink_mem", "checkgroup_parameters:memory_percentage_used"),
        ("check", "tplink_poe_summary", "checkgroup_parameters:epower_single"),
        ("check", "ucs_c_rack_server_util_cpu", "checkgroup_parameters:cpu_utilization_multiitem"),
        ("check", "ups_in_freq", "checkgroup_parameters:efreq"),
        ("check", "ups_in_voltage", "checkgroup_parameters:evolt"),
        ("check", "ups_out_voltage", "checkgroup_parameters:evolt"),
        ("check", "ups_power", "checkgroup_parameters:epower"),
        ("check", "ups_socomec_in_voltage", "checkgroup_parameters:evolt"),
        ("check", "ups_socomec_out_voltage", "checkgroup_parameters:evolt"),
        ("check", "ups_test", "checkgroup_parameters:ups_test"),
        ("check", "veeam_tapejobs", "checkgroup_parameters:veeam_tapejobs"),
        ("check", "vms_system_procs", "checkgroup_parameters:vms_procs"),
        (
            "check",
            "wagner_titanus_topsense_airflow_deviation",
            "checkgroup_parameters:airflow_deviation",
        ),
        ("check", "watchdog_sensors_humidity", "checkgroup_parameters:humidity"),
        ("check", "websphere_mq_channels", "checkgroup_parameters:websphere_mq_channels"),
        ("check", "windows_multipath", "checkgroup_parameters:windows_multipath"),
        ("check", "wmi_cpuload", "checkgroup_parameters:cpu_load"),
        ("discovery", "domino_tasks", "inv_domino_tasks_rules"),
        ("discovery", "mssql_counters_cache_hits", "inventory_mssql_counters_rules"),
        ("discovery", "mssql_datafiles", "mssql_transactionlogs_discovery"),
        ("discovery", "mssql_transactionlogs", "mssql_transactionlogs_discovery"),
        ("discovery", "ps", "inventory_processes_rules"),
        ("discovery", "vnx_quotas", "discovery_rules_vnx_quotas"),
        ("discovery", "hitachi_hnas_volume", "filesystem_groups"),
        ("discovery", "hitachi_hnas_volume_virtual", "filesystem_groups"),
    }

    def __init__(self):
        self._last_exception: t.Optional[DefaultLoadingFailed] = None
        self._failed = False
        self._known_wato_unused = self.KNOWN_WATO_UNUSED.copy()
        self._known_item_requirements = self.KNOWN_ITEM_REQUIREMENTS.copy()
        self._known_wato_missing = self.KNOWN_WATO_MISSING.copy()
        self._known_error_loading_defaults = self.KNOWN_ERROR_LOADING_DEFAULTS.copy()

    def failed(self) -> bool:
        return self._failed

    def report_wato_unused(self, wato: WatoProtocol) -> None:
        element = (wato.type, wato.get_name())
        if element in self._known_wato_unused:
            self._known_wato_unused.remove(element)
            return
        print(f"{wato.get_description()} is not used by any plugin")
        self._failed |= True

    def report_wato_missing(self, plugin: PluginProtocol) -> None:
        element = (plugin.type, plugin.get_name(), plugin.get_merge_name())
        if element in self._known_wato_missing:
            self._known_wato_missing.remove(element)
            return
        print(
            f"{plugin.get_description()} wants to use "
            f"wato ruleset '{plugin.get_merge_name()}' but this can not be found"
        )
        self._failed |= True

    def run_tests(self, plugin: PluginProtocol, wato: WatoProtocol) -> None:
        # try to load the plugin defaults into wato ruleset
        exception = wato.validate_parameter(plugin.get_default_parameters())
        if exception:
            self._report_error_loading_defaults(plugin, wato, exception)

        # see if both plugin and wato have the same idea about items
        if isinstance(plugin, PluginCheck) and isinstance(wato, WatoCheck):
            if wato.has_item() != plugin.has_item():
                self._report_check_item_requirements(plugin, wato)

    def _report_check_item_requirements(
        self,
        plugin: PluginCheck,
        wato: WatoCheck,
    ) -> None:
        element = (plugin.type, plugin.get_name(), wato.get_name())
        if element in self._known_item_requirements:
            self._known_item_requirements.remove(element)
            return
        print(
            f"{plugin.get_description()} and {wato.get_description()} have different item requirements:"
        )
        print("    wato   handles item:", wato.has_item())
        print("    plugin handles items:", plugin.has_item())
        self._failed |= True

    def _report_error_loading_defaults(
        self,
        plugin: PluginProtocol,
        wato: WatoProtocol,
        exception: Exception,
    ) -> None:
        element = (plugin.type, plugin.get_name(), wato.get_name())
        if element in self._known_error_loading_defaults:
            self._known_error_loading_defaults.remove(element)
            return
        print(
            f"Loading the default value of {plugin.get_description()} "
            f"into {wato.get_description()} failed:\n    {exception.__class__.__name__}: {exception}"
        )
        self._last_exception = DefaultLoadingFailed(
            f"Loading the default value of {plugin.type} {plugin.get_name()} "
            f"into wato rulespec {wato.get_name()} failed! "
            "The original exception is reported above."
        )
        self._last_exception.__cause__ = exception
        self._failed |= True

    def test_for_vanished_known_problems(self) -> None:
        """
        Generally test_plugin_vs_wato makes sure that the plugin default values
        matches the structure of the wato ruleset.

        This particular test makes sure that the known defects defined in the
        `_known_*` class variables are up to date and don't have obsolete
        values.

        So If this test failes, chances are high you recently fixed such an
        missmatch! Then simply remove the element from the corresponding
        `_known_*` set.
        """
        # ci does not report the variables, so we print them...
        print(self._known_error_loading_defaults)
        print(self._known_item_requirements)
        print(self._known_wato_missing)
        print(self._known_wato_unused)
        assert len(self._known_error_loading_defaults) == 0
        assert len(self._known_item_requirements) == 0
        assert len(self._known_wato_missing) == 0
        assert len(self._known_wato_unused) == 0

    def raise_last_default_loading_exception(self) -> None:
        if self._last_exception is not None:
            raise self._last_exception  # pylint: disable-msg=E0702  # https://stackoverflow.com/a/2228811


################################################################################
# implementation details
################################################################################

A = t.TypeVar("A", bound="ComparableA")
B = t.TypeVar("B", bound="ComparableB")


class ComparableA(t.Protocol):
    def __lt__(self, other: "ComparableB") -> bool:
        ...


class ComparableB(t.Protocol):
    def __lt__(self, other: ComparableA) -> bool:
        ...


def merge(a: t.Iterable[A], b: t.Iterable[B]) -> t.Iterator[t.Tuple[t.Optional[A], t.Optional[B]]]:
    """
    merge a and b in a way that elements that are equal in a and b are in the
    same tuple.
    a and b have to be sorted before calling this function!
    """
    iter_a = iter(a)
    iter_b = iter(b)

    def next_a() -> t.Optional[A]:
        try:
            return next(iter_a)
        except StopIteration:
            return None

    def next_b() -> t.Optional[B]:
        try:
            return next(iter_b)
        except StopIteration:
            return None

    value_a = next_a()
    value_b = next_b()

    while True:
        if value_a is None and value_b is None:
            break
        if value_a is None:
            yield (None, value_b)
            value_b = next_b()
        elif value_b is None:
            yield (value_a, None)
            value_a = next_a()
        elif value_a == value_b:
            yield (value_a, value_b)
            prev_a = value_a
            prev_b = value_b
            value_a = next_a()
            value_b = next_b()
            if (prev_a == value_a) and (prev_b == value_b):
                continue
            while prev_a == value_a:
                yield (value_a, prev_b)
                value_a = next_a()
            while prev_b == value_b:
                yield (prev_a, value_b)
                value_b = next_b()
        elif value_a > value_b:
            yield (None, value_b)
            value_b = next_b()
        else:
            yield (value_a, None)
            value_a = next_a()


def test_merge() -> None:
    result = merge([1, 3, 5], [2, 3, 4])  # type: ignore  # TODO: XXX: how to type?!
    assert list(result) == [(1, None), (None, 2), (3, 3), (None, 4), (5, None)]
    result = merge([1, 1, 5], [2, 3, 4])  # type: ignore
    assert list(result) == [(1, None), (1, None), (None, 2), (None, 3), (None, 4), (5, None)]
    result = merge([1], [2, 3, 4])  # type: ignore
    assert list(result) == [(1, None), (None, 2), (None, 3), (None, 4)]
    result = merge([1, 1, 1, 4], [1, 2, 3, 4])  # type: ignore
    assert list(result) == [(1, 1), (1, 1), (1, 1), (None, 2), (None, 3), (4, 4)]
    result = merge([1, 1, 1], [1, 1, 1])  # type: ignore
    assert list(result) == [(1, 1), (1, 1), (1, 1)]


def test_compare() -> None:
    class CompareBase(Base[MergeKey]):
        def __init__(self, element: MergeKey):
            self._element: MergeKey
            super().__init__(element)

        def get_merge_key(self) -> MergeKey:
            return self._element

        def get_description(self) -> str:
            return ""

        def get_merge_name(self) -> str:
            return ""

    assert CompareBase(MergeKey("a", "")) < CompareBase(MergeKey("b", ""))
    assert CompareBase(MergeKey("a", "")) == CompareBase(MergeKey("a", ""))
    result = sorted([CompareBase(MergeKey("b", "zwei")), CompareBase(MergeKey("a", "eins"))])
    assert result[0]._element.name == "eins"
