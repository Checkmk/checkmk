#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import typing as t

from tests.unit.cmk.conftest import import_plugins

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.rulesets.definition import RuleGroup

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.inventory_classes import InventoryPlugin

from cmk.gui.inventory import RulespecGroupInventory
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


class DefaultLoadingFailed(Exception):
    pass


class Base(t.Generic[T], abc.ABC):
    type: str

    def __init__(self, element: T) -> None:
        self._element: T = element

    @abc.abstractmethod
    def get_merge_name(self) -> str:
        """
        return name by which Wato and Plugin lists are merged
        """

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
        return human readable unique identifier for this element
        """

    def __gt__(self, other: object) -> bool:
        if other is None or not isinstance(other, Base):
            raise ValueError()
        return self.get_merge_key() > other.get_merge_key()

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

    def __gt__(self, other: object) -> bool:
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


@import_plugins(["cmk.gui.cce.plugins.wato"])
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
        ("check", RuleGroup.CheckgroupParameters("checkmk_agent_plugins")),
        ("check", RuleGroup.CheckgroupParameters("ceph_status")),
        ("check", RuleGroup.CheckgroupParameters("disk_temperature")),
        ("check", RuleGroup.CheckgroupParameters("entersekt_soaprrors")),
        ("check", RuleGroup.CheckgroupParameters("hw_single_temperature")),
        ("check", RuleGroup.CheckgroupParameters("hw_temperature")),
        ("check", RuleGroup.CheckgroupParameters("mailqueue_length")),
        ("check", RuleGroup.CheckgroupParameters("mssql_blocked_sessions")),
        ("check", RuleGroup.CheckgroupParameters("postgres_sessions")),
        ("check", RuleGroup.CheckgroupParameters("room_temperature")),
        ("check", RuleGroup.CheckgroupParameters("ruckus_mac")),
        ("check", RuleGroup.CheckgroupParameters("statgrab_mem")),
        ("check", RuleGroup.CheckgroupParameters("systemd_services")),
        ("check", RuleGroup.CheckgroupParameters("temperature_trends")),
        ("check", RuleGroup.CheckgroupParameters("prism_container")),
        ("discovery", "discovery_systemd_units_services_rules"),
        ("inventory", RuleGroup.ActiveChecks("cmk_inv")),
        ("inventory", RuleGroup.InvParameters("inv_if")),
        ("inventory", RuleGroup.InvParameters("lnx_sysctl")),
        ("inventory", "inv_retention_intervals"),
        (
            "inventory",
            RuleGroup.InvExports("software_csv"),
        ),  # deprecated since 2.2
    }
    KNOWN_ITEM_REQUIREMENTS = {
        # type # plugin # wato
        ("check", "azure_ad_sync", RuleGroup.CheckgroupParameters("azure_ad")),
        (
            "check",
            "azure_agent_info",
            RuleGroup.CheckgroupParameters("azure_agent_info"),
        ),
        (
            "check",
            "checkpoint_memory",
            RuleGroup.CheckgroupParameters("memory_simple"),
        ),
        (
            "check",
            "cisco_cpu_memory",
            RuleGroup.CheckgroupParameters("cisco_cpu_memory"),
        ),
        (
            "check",
            "datapower_mem",
            RuleGroup.CheckgroupParameters("memory_simple"),
        ),
        (
            "check",
            "f5_bigip_mem",
            RuleGroup.CheckgroupParameters("memory_simple"),
        ),
        (
            "check",
            "f5_bigip_mem_tmm",
            RuleGroup.CheckgroupParameters("memory_simple"),
        ),
        (
            "check",
            "haproxy_frontend",
            RuleGroup.CheckgroupParameters("haproxy_frontend"),
        ),
        (
            "check",
            "haproxy_server",
            RuleGroup.CheckgroupParameters("haproxy_server"),
        ),
        (
            "check",
            "hp_procurve_mem",
            RuleGroup.CheckgroupParameters("memory_simple"),
        ),
        (
            "check",
            "mongodb_replica_set",
            RuleGroup.CheckgroupParameters("mongodb_replica_set"),
        ),
        (
            "check",
            "mongodb_replica_set_election",
            RuleGroup.CheckgroupParameters("mongodb_replica_set"),
        ),
        (
            "check",
            "netapp_fcpio",
            RuleGroup.CheckgroupParameters("netapp_fcportio"),
        ),
        (
            "check",
            "systemd_units_services_summary",
            RuleGroup.CheckgroupParameters("systemd_services_summary"),
        ),
        ("check", "ucd_mem", RuleGroup.CheckgroupParameters("memory_simple")),
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
        ("check", "innovaphone_channels", "hw_single_channelserature"),
        ("check", "ironport_misc", "obsolete"),
        ("check", "j4p_performance_app_sess", "j4p_performance.app_sess"),
        ("check", "j4p_performance_app_state", "j4p_performance.app_state"),
        ("check", "j4p_performance_mem", "j4p_performance.mem"),
        ("check", "j4p_performance_serv_req", "j4p_performance.serv_req"),
        ("check", "j4p_performance_threads", "j4p_performance.threads"),
        ("check", "j4p_performance_uptime", "j4p_performance.uptime"),
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
        ("discovery", "fileinfo", "fileinfo_groups"),
        ("discovery", "fileinfo_groups", "fileinfo_groups"),
        ("discovery", "sap_hana_fileinfo", "fileinfo_groups"),
        ("discovery", "sap_hana_fileinfo_groups", "fileinfo_groups"),
        ("discovery", "logwatch_groups", "logwatch_groups"),
        ("discovery", "logwatch", "logwatch_groups"),
        ("inventory", "inv_if", "inv_if"),
        ("inventory", "lnx_sysctl", "lnx_sysctl"),
    }
    KNOWN_ERROR_LOADING_DEFAULTS = {
        # type # plugin # wato
        (
            "check",
            "ad_replication",
            RuleGroup.CheckgroupParameters("ad_replication"),
        ),
        (
            "check",
            "apc_ats_output",
            RuleGroup.CheckgroupParameters("apc_ats_output"),
        ),
        ("check", "apc_humidity", RuleGroup.CheckgroupParameters("humidity")),
        (
            "check",
            "apc_symmetra",
            RuleGroup.CheckgroupParameters("apc_symentra"),
        ),
        (
            "check",
            "apc_symmetra_temp",
            RuleGroup.CheckgroupParameters("temperature"),
        ),
        (
            "check",
            "appdynamics_sessions",
            RuleGroup.CheckgroupParameters("jvm_sessions"),
        ),
        (
            "check",
            "appdynamics_web_container",
            RuleGroup.CheckgroupParameters("jvm_threads"),
        ),
        (
            "check",
            "aws_dynamodb_table_read_capacity",
            RuleGroup.CheckgroupParameters("aws_dynamodb_capacity"),
        ),
        (
            "check",
            "aws_dynamodb_table_write_capacity",
            RuleGroup.CheckgroupParameters("aws_dynamodb_capacity"),
        ),
        (
            "check",
            "barracuda_mail_latency",
            RuleGroup.CheckgroupParameters("mail_latency"),
        ),
        (
            "check",
            "blade_bx_powerfan",
            RuleGroup.CheckgroupParameters("hw_fans_perc"),
        ),
        ("check", "brocade_fan", RuleGroup.CheckgroupParameters("hw_fans")),
        (
            "check",
            "brocade_mlx_module_mem",
            RuleGroup.CheckgroupParameters("memory_multiitem"),
        ),
        (
            "check",
            "brocade_optical",
            RuleGroup.CheckgroupParameters("brocade_optical"),
        ),
        (
            "check",
            "brocade_sys_mem",
            RuleGroup.CheckgroupParameters("memory_relative"),
        ),
        ("check", "bvip_fans", RuleGroup.CheckgroupParameters("hw_fans")),
        ("check", "bvip_poe", RuleGroup.CheckgroupParameters("epower_single")),
        (
            "check",
            "casa_cpu_mem",
            RuleGroup.CheckgroupParameters("memory_multiitem"),
        ),
        (
            "check",
            "ceph_status_mgrs",
            RuleGroup.CheckgroupParameters("ceph_mgrs"),
        ),
        (
            "check",
            "ceph_status_osds",
            RuleGroup.CheckgroupParameters("ceph_osds"),
        ),
        (
            "check",
            "cisco_prime_wifi_access_points",
            RuleGroup.CheckgroupParameters("cisco_prime_wifi_access_points"),
        ),
        (
            "check",
            "cisco_prime_wifi_connections",
            RuleGroup.CheckgroupParameters("cisco_prime_wifi_connections"),
        ),
        (
            "check",
            "cisco_sys_mem",
            RuleGroup.CheckgroupParameters("cisco_supervisor_mem"),
        ),
        (
            "check",
            "citrix_licenses",
            RuleGroup.CheckgroupParameters("citrix_licenses"),
        ),
        (
            "check",
            "citrix_serverload",
            RuleGroup.CheckgroupParameters("citrix_load"),
        ),
        (
            "check",
            "couchbase_buckets_mem",
            RuleGroup.CheckgroupParameters("memory_multiitem"),
        ),
        ("check", "db2_backup", RuleGroup.CheckgroupParameters("db2_backup")),
        ("check", "db2_mem", RuleGroup.CheckgroupParameters("db2_mem")),
        (
            "check",
            "ddn_s2a_faultsbasic_disks",
            RuleGroup.CheckgroupParameters("disk_failures"),
        ),
        (
            "check",
            "ddn_s2a_faultsbasic_fans",
            RuleGroup.CheckgroupParameters("fan_failures"),
        ),
        (
            "check",
            "ddn_s2a_stats_io",
            RuleGroup.CheckgroupParameters("storage_iops"),
        ),
        (
            "check",
            "ddn_s2a_stats_readhits",
            RuleGroup.CheckgroupParameters("read_hits"),
        ),
        (
            "check",
            "dell_idrac_fans",
            RuleGroup.CheckgroupParameters("hw_fans"),
        ),
        ("check", "dell_om_fans", RuleGroup.CheckgroupParameters("hw_fans")),
        (
            "check",
            "docsis_channels_upstream",
            RuleGroup.CheckgroupParameters("docsis_channels_upstream"),
        ),
        (
            "check",
            "domino_transactions",
            RuleGroup.CheckgroupParameters("domino_transactions"),
        ),
        (
            "check",
            "domino_users",
            RuleGroup.CheckgroupParameters("domino_users"),
        ),
        (
            "check",
            "eltek_fans",
            RuleGroup.CheckgroupParameters("hw_fans_perc"),
        ),
        ("check", "emcvnx_sp_util", RuleGroup.CheckgroupParameters("sp_util")),
        ("check", "enterasys_lsnat", RuleGroup.CheckgroupParameters("lsnat")),
        (
            "check",
            "epson_beamer_lamp",
            RuleGroup.CheckgroupParameters("lamp_operation_time"),
        ),
        (
            "check",
            "esx_vsphere_licenses",
            RuleGroup.CheckgroupParameters("esx_licenses"),
        ),
        (
            "check",
            "esx_vsphere_objects_count",
            RuleGroup.CheckgroupParameters("esx_vsphere_objects_count"),
        ),
        (
            "check",
            "esx_vsphere_sensors",
            RuleGroup.CheckgroupParameters("hostsystem_sensors"),
        ),
        (
            "check",
            "esx_vsphere_vm_guest_tools",
            RuleGroup.CheckgroupParameters("vm_guest_tools"),
        ),
        (
            "check",
            "esx_vsphere_vm_heartbeat",
            RuleGroup.CheckgroupParameters("vm_heartbeat"),
        ),
        ("check", "f5_bigip_fans", RuleGroup.CheckgroupParameters("hw_fans")),
        ("check", "f5_bigip_pool", RuleGroup.CheckgroupParameters("f5_pools")),
        (
            "check",
            "fortigate_antivirus",
            RuleGroup.CheckgroupParameters("fortigate_antivirus"),
        ),
        (
            "check",
            "fortigate_ips",
            RuleGroup.CheckgroupParameters("fortigate_ips"),
        ),
        (
            "check",
            "fortigate_ipsecvpn",
            RuleGroup.CheckgroupParameters("ipsecvpn"),
        ),
        (
            "check",
            "fortigate_memory",
            RuleGroup.CheckgroupParameters("memory"),
        ),
        (
            "check",
            "fortigate_node_sessions",
            RuleGroup.CheckgroupParameters("fortigate_node_sessions"),
        ),
        (
            "check",
            "fortigate_sessions_base",
            RuleGroup.CheckgroupParameters("fortigate_sessions"),
        ),
        (
            "check",
            "fortigate_sessions",
            RuleGroup.CheckgroupParameters("fortigate_sessions"),
        ),
        (
            "check",
            "fortimail_cpu_load",
            RuleGroup.CheckgroupParameters("fortimail_cpu_load"),
        ),
        (
            "check",
            "fortimail_disk_usage",
            RuleGroup.CheckgroupParameters("fortimail_disk_usage"),
        ),
        (
            "check",
            "genua_pfstate",
            RuleGroup.CheckgroupParameters("pf_used_states"),
        ),
        (
            "check",
            "hitachi_hnas_bossock",
            RuleGroup.CheckgroupParameters("bossock_fibers"),
        ),
        (
            "check",
            "hivemanager_devices",
            RuleGroup.CheckgroupParameters("hivemanager_devices"),
        ),
        (
            "check",
            "hpux_multipath",
            RuleGroup.CheckgroupParameters("hpux_multipath"),
        ),
        (
            "check",
            "huawei_osn_laser",
            RuleGroup.CheckgroupParameters("huawei_osn_laser"),
        ),
        (
            "check",
            "ibm_imm_fan",
            RuleGroup.CheckgroupParameters("hw_fans_perc"),
        ),
        (
            "check",
            "ibm_svc_license",
            RuleGroup.CheckgroupParameters("ibmsvc_licenses"),
        ),
        (
            "check",
            "icom_repeater_ps_volt",
            RuleGroup.CheckgroupParameters("ps_voltage"),
        ),
        (
            "check",
            "innovaphone_mem",
            RuleGroup.CheckgroupParameters("innovaphone_mem"),
        ),
        ("check", "inotify", RuleGroup.CheckgroupParameters("inotify")),
        (
            "check",
            "jolokia_metrics_app_sess",
            RuleGroup.CheckgroupParameters("jvm_sessions"),
        ),
        (
            "check",
            "jolokia_metrics_bea_queue",
            RuleGroup.CheckgroupParameters("jvm_queue"),
        ),
        (
            "check",
            "jolokia_metrics_bea_requests",
            RuleGroup.CheckgroupParameters("jvm_requests"),
        ),
        (
            "check",
            "jolokia_metrics_bea_sess",
            RuleGroup.CheckgroupParameters("jvm_sessions"),
        ),
        (
            "check",
            "jolokia_metrics_bea_threads",
            RuleGroup.CheckgroupParameters("jvm_threads"),
        ),
        (
            "check",
            "jolokia_metrics_requests",
            RuleGroup.CheckgroupParameters("jvm_requests"),
        ),
        (
            "check",
            "jolokia_metrics_serv_req",
            RuleGroup.CheckgroupParameters("jvm_requests"),
        ),
        (
            "check",
            "juniper_mem",
            RuleGroup.CheckgroupParameters("juniper_mem_modules"),
        ),
        (
            "check",
            "juniper_screenos_mem",
            RuleGroup.CheckgroupParameters("juniper_mem"),
        ),
        (
            "check",
            "juniper_trpz_flash",
            RuleGroup.CheckgroupParameters("general_flash_usage"),
        ),
        (
            "check",
            "juniper_trpz_mem",
            RuleGroup.CheckgroupParameters("juniper_mem"),
        ),
        ("check", "keepalived", RuleGroup.CheckgroupParameters("keepalived")),
        ("check", "kernel", RuleGroup.CheckgroupParameters("vm_counter")),
        (
            "check",
            "knuerr_rms_humidity",
            RuleGroup.CheckgroupParameters("single_humidity"),
        ),
        (
            "check",
            "liebert_cooling",
            RuleGroup.CheckgroupParameters("liebert_cooling"),
        ),
        (
            "check",
            "liebert_cooling_position",
            RuleGroup.CheckgroupParameters("liebert_cooling_position"),
        ),
        (
            "check",
            "liebert_fans",
            RuleGroup.CheckgroupParameters("hw_fans_perc"),
        ),
        (
            "check",
            "liebert_fans_condenser",
            RuleGroup.CheckgroupParameters("hw_fans_perc"),
        ),
        (
            "check",
            "liebert_humidity_air",
            RuleGroup.CheckgroupParameters("humidity"),
        ),
        ("check", "logins", RuleGroup.CheckgroupParameters("logins")),
        ("check", "lvm_vgs", RuleGroup.CheckgroupParameters("volume_groups")),
        (
            "check",
            "mikrotik_signal",
            RuleGroup.CheckgroupParameters("signal_quality"),
        ),
        (
            "check",
            "mongodb_collections",
            RuleGroup.CheckgroupParameters("mongodb_collections"),
        ),
        (
            "check",
            "mounts",
            RuleGroup.CheckgroupParameters("fs_mount_options"),
        ),
        ("check", "mq_queues", RuleGroup.CheckgroupParameters("mq_queues")),
        (
            "check",
            "msexch_dag_copyqueue",
            RuleGroup.CheckgroupParameters("msexch_copyqueue"),
        ),
        (
            "check",
            "msexch_isclienttype",
            RuleGroup.CheckgroupParameters("msx_info_store"),
        ),
        (
            "check",
            "msexch_isstore",
            RuleGroup.CheckgroupParameters("msx_info_store"),
        ),
        (
            "check",
            "mssql_connections",
            RuleGroup.CheckgroupParameters("mssql_connections"),
        ),
        (
            "check",
            "mysql_slave",
            RuleGroup.CheckgroupParameters("mysql_slave"),
        ),
        (
            "check",
            "netapp_api_connection",
            RuleGroup.CheckgroupParameters("netapp_instance"),
        ),
        (
            "check",
            "netapp_api_environment_fan_faults",
            RuleGroup.CheckgroupParameters("hw_fans"),
        ),
        (
            "check",
            "netapp_api_environment_fans",
            RuleGroup.CheckgroupParameters("hw_fans"),
        ),
        (
            "check",
            "netscaler_health_fan",
            RuleGroup.CheckgroupParameters("hw_fans"),
        ),
        (
            "check",
            "netscaler_mem",
            RuleGroup.CheckgroupParameters("netscaler_mem"),
        ),
        (
            "check",
            "openhardwaremonitor_fan",
            RuleGroup.CheckgroupParameters("hw_fans"),
        ),
        (
            "check",
            "openhardwaremonitor_smart",
            RuleGroup.CheckgroupParameters("openhardwaremonitor_smart"),
        ),
        (
            "check",
            "openhardwaremonitor_temperature",
            RuleGroup.CheckgroupParameters("temperature"),
        ),
        (
            "check",
            "oracle_diva_csm_tapes",
            RuleGroup.CheckgroupParameters("blank_tapes"),
        ),
        (
            "check",
            "plesk_backups",
            RuleGroup.CheckgroupParameters("plesk_backups"),
        ),
        (
            "check",
            "prometheus_custom",
            RuleGroup.CheckgroupParameters("prometheus_custom"),
        ),
        ("check", "ps", RuleGroup.CheckgroupParameters("ps")),
        (
            "check",
            "pulse_secure_mem_util",
            RuleGroup.CheckgroupParameters("pulse_secure_mem_util"),
        ),
        (
            "check",
            "pulse_secure_users",
            RuleGroup.CheckgroupParameters("pulse_secure_users"),
        ),
        ("check", "qnap_fans", RuleGroup.CheckgroupParameters("hw_fans")),
        ("check", "quanta_fan", RuleGroup.CheckgroupParameters("hw_fans")),
        (
            "check",
            "ra32e_switch",
            RuleGroup.CheckgroupParameters("switch_contact"),
        ),
        (
            "check",
            "rabbitmq_nodes_mem",
            RuleGroup.CheckgroupParameters("memory_multiitem"),
        ),
        (
            "check",
            "raritan_pdu_ocprot",
            RuleGroup.CheckgroupParameters("ocprot_current"),
        ),
        (
            "check",
            "raritan_pdu_outletcount",
            RuleGroup.CheckgroupParameters("plug_count"),
        ),
        (
            "check",
            "rds_licenses",
            RuleGroup.CheckgroupParameters("rds_licenses"),
        ),
        (
            "check",
            "redis_info_persistence",
            RuleGroup.CheckgroupParameters("redis_info_persistence"),
        ),
        (
            "check",
            "safenet_ntls_clients",
            RuleGroup.CheckgroupParameters("safenet_ntls_clients"),
        ),
        (
            "check",
            "safenet_ntls_links",
            RuleGroup.CheckgroupParameters("safenet_ntls_links"),
        ),
        (
            "check",
            "sansymphony_alerts",
            RuleGroup.CheckgroupParameters("sansymphony_alerts"),
        ),
        (
            "check",
            "siemens_plc_flag",
            RuleGroup.CheckgroupParameters("siemens_plc_flag"),
        ),
        (
            "check",
            "skype_conferencing",
            RuleGroup.CheckgroupParameters("skype_conferencing"),
        ),
        (
            "check",
            "skype_sip_stack",
            RuleGroup.CheckgroupParameters("skype_sip"),
        ),
        (
            "check",
            "symantec_av_updates",
            RuleGroup.CheckgroupParameters("antivir_update_age"),
        ),
        (
            "check",
            "tinkerforge_ambient",
            RuleGroup.CheckgroupParameters("brightness"),
        ),
        (
            "check",
            "tplink_mem",
            RuleGroup.CheckgroupParameters("memory_percentage_used"),
        ),
        (
            "check",
            "tplink_poe_summary",
            RuleGroup.CheckgroupParameters("epower_single"),
        ),
        (
            "check",
            "veeam_tapejobs",
            RuleGroup.CheckgroupParameters("veeam_tapejobs"),
        ),
        (
            "check",
            "vms_system_procs",
            RuleGroup.CheckgroupParameters("vms_procs"),
        ),
        (
            "check",
            "wagner_titanus_topsense_airflow_deviation",
            RuleGroup.CheckgroupParameters("airflow_deviation"),
        ),
        (
            "check",
            "watchdog_sensors_humidity",
            RuleGroup.CheckgroupParameters("humidity"),
        ),
        (
            "check",
            "websphere_mq_channels",
            RuleGroup.CheckgroupParameters("websphere_mq_channels"),
        ),
        (
            "check",
            "windows_multipath",
            RuleGroup.CheckgroupParameters("windows_multipath"),
        ),
        ("discovery", "domino_tasks", "inv_domino_tasks_rules"),
        ("discovery", "mssql_counters_cache_hits", "inventory_mssql_counters_rules"),
        ("discovery", "mssql_datafiles", "mssql_transactionlogs_discovery"),
        ("discovery", "mssql_transactionlogs", "mssql_transactionlogs_discovery"),
        ("discovery", "ps", "inventory_processes_rules"),
        ("discovery", "vnx_quotas", "discovery_rules_vnx_quotas"),
        ("discovery", "hitachi_hnas_volume", "filesystem_groups"),
        ("discovery", "hitachi_hnas_volume_virtual", "filesystem_groups"),
    }

    def __init__(self) -> None:
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
        mismatch! Then simply remove the element from the corresponding
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
            raise self._last_exception


################################################################################
# implementation details
################################################################################


T_contra = t.TypeVar("T_contra", contravariant=True)


class SupportsGreaterThan(t.Protocol, t.Generic[T_contra]):
    def __gt__(self, other: T_contra) -> bool:
        ...


A = t.TypeVar("A", bound=SupportsGreaterThan)
B = t.TypeVar("B")


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
    result = merge([1, 3, 5], [2, 3, 4])
    assert list(result) == [(1, None), (None, 2), (3, 3), (None, 4), (5, None)]
    result = merge([1, 1, 5], [2, 3, 4])
    assert list(result) == [(1, None), (1, None), (None, 2), (None, 3), (None, 4), (5, None)]
    result = merge([1], [2, 3, 4])
    assert list(result) == [(1, None), (None, 2), (None, 3), (None, 4)]
    result = merge([1, 1, 1, 4], [1, 2, 3, 4])
    assert list(result) == [(1, 1), (1, 1), (1, 1), (None, 2), (None, 3), (4, 4)]
    result = merge([1, 1, 1], [1, 1, 1])
    assert list(result) == [(1, 1), (1, 1), (1, 1)]


def test_compare() -> None:
    class CompareBase(Base[MergeKey]):
        def __init__(self, element: MergeKey) -> None:
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
