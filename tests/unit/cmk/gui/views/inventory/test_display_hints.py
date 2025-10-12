#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

import datetime
from collections.abc import Callable

import pytest

import cmk.gui.inventory
import cmk.gui.utils
from cmk.gui.inventory._tree import InventoryPath, TreeSource
from cmk.gui.inventory.filters import (
    FilterInvtableText,
    FilterInvText,
)
from cmk.gui.num_split import cmp_version
from cmk.gui.type_defs import DynamicIconName
from cmk.gui.views.inventory._display_hints import (
    _cmp_inv_generic,
    _decorate_sort_function,
    _PaintBool,
    _PaintChoice,
    _PaintNumber,
    _PaintText,
    _parse_view_name,
    _SortFunctionChoice,
    _SortFunctionText,
    _wrap_paint_function,
    AttributeDisplayHint,
    ColumnDisplayHint,
    ColumnDisplayHintOfView,
    inv_display_hints,
    NodeDisplayHint,
    Table,
    TableWithView,
    TDStyles,
)
from cmk.gui.views.inventory._paint_functions import (
    inv_paint_generic,
    inv_paint_if_oper_status,
    inv_paint_number,
    inv_paint_service_status,
    inv_paint_size,
)
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.inventory.structured_data import SDKey, SDNodeName, SDPath
from cmk.inventory_ui.v1_unstable import AgeNotation as AgeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Alignment as AlignmentFromAPI
from cmk.inventory_ui.v1_unstable import BackgroundColor as BackgroundColorFromAPI
from cmk.inventory_ui.v1_unstable import BoolField as BoolFieldFromAPI
from cmk.inventory_ui.v1_unstable import ChoiceField as ChoiceFieldFromAPI
from cmk.inventory_ui.v1_unstable import DecimalNotation as DecimalNotationFromAPI
from cmk.inventory_ui.v1_unstable import IECNotation as IECNotationFromAPI
from cmk.inventory_ui.v1_unstable import Label as LabelFromAPI
from cmk.inventory_ui.v1_unstable import LabelColor as LabelColorFromAPI
from cmk.inventory_ui.v1_unstable import NumberField as NumberFieldFromAPI
from cmk.inventory_ui.v1_unstable import SINotation as SINotationFromAPI
from cmk.inventory_ui.v1_unstable import (
    StandardScientificNotation as StandardScientificNotationFromAPI,
)
from cmk.inventory_ui.v1_unstable import TextField as TextFieldFromAPI
from cmk.inventory_ui.v1_unstable import TimeNotation as TimeNotationFromAPI
from cmk.inventory_ui.v1_unstable import Title as TitleFromAPI
from cmk.inventory_ui.v1_unstable import Unit as UnitFromAPI


def test_display_hint_titles() -> None:
    assert not inventory_displayhints


def test_paths() -> None:
    assert sorted(h.path for h in inv_display_hints) == sorted(
        [
            (),
            ("hardware",),
            ("hardware", "chassis"),
            ("hardware", "components"),
            ("hardware", "components", "backplanes"),
            ("hardware", "components", "chassis"),
            ("hardware", "components", "containers"),
            ("hardware", "components", "fans"),
            ("hardware", "components", "modules"),
            ("hardware", "components", "others"),
            ("hardware", "components", "psus"),
            ("hardware", "components", "sensors"),
            ("hardware", "components", "stacks"),
            ("hardware", "components", "unknowns"),
            ("hardware", "cpu"),
            ("hardware", "cpu", "nodes"),
            ("hardware", "firmware"),
            ("hardware", "firmware", "redfish"),
            ("hardware", "memory"),
            ("hardware", "memory", "arrays"),
            ("hardware", "memory", "arrays", "devices"),
            ("hardware", "nwadapter"),
            ("hardware", "storage"),
            ("hardware", "storage", "controller"),
            ("hardware", "storage", "disks"),
            ("hardware", "system"),
            ("hardware", "system", "nodes"),
            ("hardware", "uploaded_files"),
            ("hardware", "video"),
            ("hardware", "volumes"),
            ("hardware", "volumes", "physical_volumes"),
            ("networking",),
            ("networking", "addresses"),
            ("networking", "cdp_cache"),
            ("networking", "cdp_cache", "neighbors"),
            ("networking", "interfaces"),
            ("networking", "interfaces", "name"),
            ("networking", "kube"),
            ("networking", "lldp_cache"),
            ("networking", "lldp_cache", "neighbours"),
            ("networking", "routes"),
            ("networking", "sip_interfaces"),
            ("networking", "tunnels"),
            ("networking", "uplinks"),
            ("networking", "wlan"),
            ("networking", "wlan", "controller"),
            ("networking", "wlan", "controller", "accesspoints"),
            ("software",),
            ("software", "applications"),
            ("software", "applications", "azure"),
            ("software", "applications", "azure", "application_gateways"),
            ("software", "applications", "azure", "application_gateways", "rules"),
            ("software", "applications", "azure", "application_gateways", "rules", "backends"),
            ("software", "applications", "azure", "application_gateways", "rules", "listeners"),
            ("software", "applications", "azure", "load_balancers"),
            ("software", "applications", "azure", "load_balancers", "inbound_nat_rules"),
            (
                "software",
                "applications",
                "azure",
                "load_balancers",
                "inbound_nat_rules",
                "private_ips",
            ),
            (
                "software",
                "applications",
                "azure",
                "load_balancers",
                "inbound_nat_rules",
                "public_ips",
            ),
            ("software", "applications", "azure", "load_balancers", "outbound_rules"),
            ("software", "applications", "check_mk"),
            ("software", "applications", "check_mk", "cluster"),
            ("software", "applications", "check_mk", "cluster", "nodes"),
            ("software", "applications", "check_mk", "sites"),
            ("software", "applications", "check_mk", "versions"),
            ("software", "applications", "checkmk-agent"),
            ("software", "applications", "checkmk-agent", "local_checks"),
            ("software", "applications", "checkmk-agent", "plugins"),
            ("software", "applications", "citrix"),
            ("software", "applications", "citrix", "controller"),
            ("software", "applications", "citrix", "vm"),
            ("software", "applications", "docker"),
            ("software", "applications", "docker", "container"),
            ("software", "applications", "docker", "container", "networks"),
            ("software", "applications", "docker", "container", "ports"),
            ("software", "applications", "docker", "containers"),
            ("software", "applications", "docker", "images"),
            ("software", "applications", "docker", "networks"),
            ("software", "applications", "docker", "networks", "containers"),
            ("software", "applications", "docker", "node_labels"),
            ("software", "applications", "docker", "swarm_manager"),
            ("software", "applications", "fortinet"),
            ("software", "applications", "fortinet", "fortigate_high_availability"),
            ("software", "applications", "fortinet", "fortisandbox"),
            ("software", "applications", "fritz"),
            ("software", "applications", "ibm_mq"),
            ("software", "applications", "ibm_mq", "channels"),
            ("software", "applications", "ibm_mq", "managers"),
            ("software", "applications", "ibm_mq", "queues"),
            ("software", "applications", "kube"),
            ("software", "applications", "kube", "cluster"),
            ("software", "applications", "kube", "containers"),
            ("software", "applications", "kube", "daemonset"),
            ("software", "applications", "kube", "deployment"),
            ("software", "applications", "kube", "labels"),
            ("software", "applications", "kube", "metadata"),
            ("software", "applications", "kube", "node"),
            ("software", "applications", "kube", "pod"),
            ("software", "applications", "kube", "statefulset"),
            ("software", "applications", "mobileiron"),
            ("software", "applications", "mssql"),
            ("software", "applications", "mssql", "instances"),
            ("software", "applications", "oracle"),
            ("software", "applications", "oracle", "dataguard_stats"),
            ("software", "applications", "oracle", "instance"),
            ("software", "applications", "oracle", "pga"),
            ("software", "applications", "oracle", "recovery_area"),
            ("software", "applications", "oracle", "sga"),
            ("software", "applications", "oracle", "systemparameter"),
            ("software", "applications", "oracle", "tablespaces"),
            ("software", "applications", "podman"),
            ("software", "applications", "podman", "container"),
            ("software", "applications", "podman", "network"),
            ("software", "applications", "podman", "containers"),
            ("software", "applications", "podman", "images"),
            ("software", "applications", "proxmox_ve"),
            ("software", "applications", "proxmox_ve", "cluster"),
            ("software", "applications", "proxmox_ve", "metadata"),
            ("software", "applications", "synthetic_monitoring"),
            ("software", "applications", "synthetic_monitoring", "plans"),
            ("software", "applications", "synthetic_monitoring", "tests"),
            ("software", "applications", "synthetic_monitoring", "scheduler"),
            ("software", "applications", "synthetic_monitoring", "scheduler", "config"),
            ("software", "applications", "vmwareesx"),
            ("software", "bios"),
            ("software", "configuration"),
            ("software", "configuration", "organisation"),
            ("software", "configuration", "snmp_info"),
            ("software", "firmware"),
            ("software", "kernel_config"),
            ("software", "os"),
            ("software", "os", "service_packs"),
            ("software", "packages"),
            (
                "software",
                "applications",
                "azure",
                "load_balancers",
                "inbound_nat_rules",
                "backend_ip_configs",
            ),
            (
                "software",
                "applications",
                "azure",
                "load_balancers",
                "outbound_rules",
                "backend_pools",
            ),
            (
                "software",
                "applications",
                "azure",
                "application_gateways",
                "rules",
                "listeners",
                "private_ips",
            ),
            (
                "software",
                "applications",
                "azure",
                "application_gateways",
                "rules",
                "listeners",
                "public_ips",
            ),
            (
                "software",
                "applications",
                "azure",
                "load_balancers",
                "outbound_rules",
                "backend_pools",
                "addresses",
            ),
            ("software", "applications", "azure", "metadata"),
        ]
    )


_KNOWN_ATTRIBUTES_KEY_ORDERS = {
    ("networking", "interfaces"): [
        "is_show_more",
    ],
    ("hardware", "cpu"): [
        "arch",
        "max_speed",
        "model",
        "type",
        "threads",
        "smt_threads",
        "cpu_max_capa",
        "cpus",
        "logical_cpus",
        "cores",
        "cores_per_cpu",
        "threads_per_cpu",
        "cache_size",
        "bus_speed",
        "voltage",
        "sharing_mode",
        "implementation_mode",
        "entitlement",
    ],
    ("hardware", "memory"): ["total_ram_usable", "total_swap", "total_vmalloc"],
    ("hardware", "system"): [
        "manufacturer",
        "product",
        "serial",
        "model",
        "node_name",
        "partition_name",
        "expresscode",
        "pki_appliance_version",
        "device_number",
        "description",
        "mac_address",
        "type",
        "software_version",
        "license_key_list",
        "model_name",
        "serial_number",
    ],
    ("hardware", "uploaded_files"): ["call_progress_tones"],
    ("hardware", "storage", "controller"): ["version"],
    ("software", "applications", "check_mk"): ["num_hosts", "num_services"],
    ("software", "applications", "check_mk", "cluster"): ["is_cluster"],
    ("software", "applications", "checkmk-agent"): [
        "version",
        "agentdirectory",
        "datadirectory",
        "spooldirectory",
        "pluginsdirectory",
        "localdirectory",
        "agentcontroller",
    ],
    ("software", "applications", "docker"): [
        "version",
        "registry",
        "swarm_state",
        "swarm_node_id",
        "num_containers_total",
        "num_containers_running",
        "num_containers_stopped",
        "num_containers_paused",
        "num_images",
    ],
    ("software", "applications", "docker", "container"): ["node_name"],
    ("software", "applications", "fritz"): [
        "link_type",
        "wan_access_type",
        "auto_disconnect_time",
        "dns_server_1",
        "dns_server_2",
        "voip_dns_server_1",
        "voip_dns_server_2",
        "upnp_config_enabled",
    ],
    ("software", "applications", "kube", "metadata"): ["object", "name", "namespace"],
    ("software", "applications", "kube", "cluster"): ["version"],
    ("software", "applications", "kube", "deployment"): [
        "strategy",
        "match_labels",
        "match_expressions",
    ],
    ("software", "applications", "kube", "daemonset"): [
        "strategy",
        "match_labels",
        "match_expressions",
    ],
    ("software", "applications", "kube", "statefulset"): [
        "strategy",
        "match_labels",
        "match_expressions",
    ],
    ("software", "applications", "kube", "node"): [
        "operating_system",
        "os_image",
        "kernel_version",
        "architecture",
        "container_runtime_version",
        "kubelet_version",
        "kube_proxy_version",
    ],
    ("software", "applications", "kube", "pod"): [
        "dns_policy",
        "host_ip",
        "host_network",
        "node",
        "pod_ip",
        "qos_class",
    ],
    ("software", "applications", "podman"): [
        "mode",
        "version",
        "registry",
        "containers_running",
        "containers_paused",
        "containers_stopped",
        "containers_exited",
        "images_num",
    ],
    ("software", "applications", "podman", "container"): [
        "hostname",
        "pod",
        "labels",
    ],
    ("software", "applications", "podman", "network"): [
        "ip_address",
        "gateway",
        "mac_address",
    ],
    ("software", "applications", "proxmox_ve", "metadata"): ["object", "provider", "name", "node"],
    ("software", "applications", "proxmox_ve", "cluster"): ["cluster"],
    ("software", "applications", "mobileiron"): ["partition_name", "registration_state"],
    ("software", "applications", "citrix", "controller"): ["controller_version"],
    ("software", "applications", "citrix", "vm"): [
        "desktop_group_name",
        "catalog",
        "agent_version",
    ],
    ("software", "applications", "ibm_mq"): ["managers", "channels", "queues"],
    ("software", "bios"): ["vendor", "version", "date"],
    ("software", "configuration", "snmp_info"): ["contact", "location", "name"],
    ("software", "configuration", "organisation"): [
        "organisation_id",
        "organisation_name",
        "network_id",
        "network_name",
        "address",
    ],
    ("software", "firmware"): ["vendor", "version", "platform_level"],
    ("software", "os"): [
        "name",
        "version",
        "vendor",
        "type",
        "install_date",
        "kernel_version",
        "arch",
        "service_pack",
        "build",
    ],
    ("networking",): [
        "hostname",
        "total_interfaces",
        "total_ethernet_ports",
        "available_ethernet_ports",
    ],
    ("hardware", "storage", "disks"): ["size"],
    ("software", "applications", "azure", "metadata"): [
        "object",
        "name",
        "entity",
        "resource_group",
        "subscription_id",
        "subscription_name",
        "region",
        "tenant_id",
    ],
}

_KNOWN_COLUMNS_KEY_ORDERS = {
    ("hardware", "cpu", "nodes"): ["node_name", "cores", "model"],
    ("hardware", "firmware", "redfish"): [
        "component",
        "version",
        "location",
        "description",
        "updateable",
    ],
    ("hardware", "memory", "arrays"): ["maximum_capacity"],
    ("hardware", "memory", "arrays", "devices"): [
        "index",
        "locator",
        "bank_locator",
        "type",
        "form_factor",
        "speed",
        "data_width",
        "total_width",
        "manufacturer",
        "serial",
        "size",
    ],
    ("hardware", "system", "nodes"): ["node_name", "id", "model", "product", "serial"],
    ("hardware", "components", "others"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "unknowns"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "chassis"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "backplanes"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "containers"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "psus"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "fans"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "sensors"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "components", "modules"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "model",
        "manufacturer",
        "bootloader",
        "firmware",
        "type",
        "location",
        "ha_status",
        "software_version",
        "license_key_list",
    ],
    ("hardware", "components", "stacks"): [
        "index",
        "name",
        "description",
        "software",
        "serial",
        "manufacturer",
        "model",
        "location",
    ],
    ("hardware", "storage", "disks"): [
        "fsnode",
        "controller",
        "signature",
        "bus",
        "drive_index",
        "local",
        "product",
        "serial",
        "size",
        "type",
        "vendor",
    ],
    ("hardware", "volumes", "physical_volumes"): [
        "volume_group_name",
        "physical_volume_name",
        "physical_volume_status",
        "physical_volume_total_partitions",
        "physical_volume_free_partitions",
    ],
    ("hardware", "video"): [
        "slot",
        "name",
        "subsystem",
        "driver",
        "driver_version",
        "driver_date",
        "graphic_memory",
    ],
    ("hardware", "nwadapter"): [
        "name",
        "type",
        "macaddress",
        "speed",
        "gateway",
        "ipv4_address",
        "ipv6_address",
        "ipv4_subnet",
        "ipv6_subnet",
    ],
    ("software", "applications", "check_mk", "versions"): [
        "version",
        "number",
        "edition",
        "demo",
        "num_sites",
    ],
    ("software", "applications", "check_mk", "sites"): [
        "site",
        "used_version",
        "num_hosts",
        "num_services",
        "check_mk_helper_usage",
        "fetcher_helper_usage",
        "checker_helper_usage",
        "livestatus_usage",
        "check_helper_usage",
        "autostart",
        "apache",
        "cmc",
        "crontab",
        "dcd",
        "liveproxyd",
        "mkeventd",
        "mknotifyd",
        "rrdcached",
        "stunnel",
        "xinetd",
        "nagios",
        "npcd",
    ],
    ("software", "applications", "check_mk", "cluster", "nodes"): ["name"],
    ("software", "applications", "checkmk-agent", "plugins"): ["name", "version", "cache_interval"],
    ("software", "applications", "checkmk-agent", "local_checks"): [
        "name",
        "version",
        "cache_interval",
    ],
    ("software", "applications", "docker", "node_labels"): ["label"],
    ("software", "applications", "docker", "swarm_manager"): ["NodeID", "Addr"],
    ("software", "applications", "docker", "images"): [
        "id",
        "creation",
        "size",
        "labels",
        "amount_containers",
        "repotags",
        "repodigests",
    ],
    ("software", "applications", "docker", "containers"): [
        "id",
        "creation",
        "name",
        "labels",
        "status",
        "image",
    ],
    ("software", "applications", "docker", "networks"): [
        "network_id",
        "short_id",
        "name",
        "scope",
        "labels",
    ],
    ("software", "applications", "docker", "container", "ports"): [
        "port",
        "protocol",
        "host_addresses",
    ],
    ("software", "applications", "docker", "container", "networks"): [
        "name",
        "ip_address",
        "ip_prefixlen",
        "gateway",
        "mac_address",
        "network_id",
    ],
    ("software", "applications", "docker", "networks", "containers"): [
        "network_id",
        "id",
        "name",
        "ipv4_address",
        "ipv6_address",
        "mac_address",
    ],
    ("software", "applications", "fortinet", "fortisandbox"): ["name", "version"],
    ("software", "applications", "kube", "labels"): ["label_name", "label_value"],
    ("networking", "kube"): ["ip", "address_type"],
    ("software", "applications", "kube", "containers"): [
        "name",
        "ready",
        "restart_count",
        "image",
        "image_pull_policy",
        "image_id",
        "container_id",
    ],
    ("software", "applications", "synthetic_monitoring", "plans"): [
        "application",
        "suite_name",
        "variant",
        "plan_id",
    ],
    ("software", "applications", "synthetic_monitoring", "scheduler", "config"): [
        "scheduler_interval",
        "env_creation",
        "n_attempts_max",
        "robot_type",
        "assigned_to_host",
        "plan_id",
    ],
    ("software", "applications", "synthetic_monitoring", "tests"): [
        "application",
        "suite_name",
        "variant",
        "top_level_suite_name",
        "bottom_level_suite_name",
        "test_name",
        "plan_id",
        "test_item",
    ],
    ("software", "applications", "oracle", "systemparameter"): [
        "sid",
        "name",
        "value",
        "isdefault",
    ],
    ("software", "applications", "oracle", "instance"): [
        "sid",
        "pname",
        "version",
        "openmode",
        "logmode",
        "logins",
        "db_uptime",
        "db_creation_time",
    ],
    ("software", "applications", "oracle", "dataguard_stats"): [
        "sid",
        "db_unique",
        "role",
        "switchover",
    ],
    ("software", "applications", "oracle", "recovery_area"): ["sid", "flashback"],
    ("software", "applications", "oracle", "sga"): [
        "sid",
        "fixed_size",
        "redo_buffer",
        "buf_cache_size",
        "in_mem_area_size",
        "shared_pool_size",
        "large_pool_size",
        "java_pool_size",
        "streams_pool_size",
        "shared_io_pool_size",
        "data_trans_cache_size",
        "granule_size",
        "max_size",
        "start_oh_shared_pool",
        "free_mem_avail",
    ],
    ("software", "applications", "oracle", "pga"): [
        "sid",
        "aggregate_pga_auto_target",
        "aggregate_pga_target_parameter",
        "bytes_processed",
        "extra_bytes_read_written",
        "global_memory_bound",
        "maximum_pga_allocated",
        "maximum_pga_used_for_auto_workareas",
        "maximum_pga_used_for_manual_workareas",
        "total_pga_allocated",
        "total_pga_inuse",
        "total_pga_used_for_auto_workareas",
        "total_pga_used_for_manual_workareas",
        "total_freeable_pga_memory",
    ],
    ("software", "applications", "oracle", "tablespaces"): [
        "sid",
        "name",
        "version",
        "type",
        "autoextensible",
        "current_size",
        "max_size",
        "used_size",
        "num_increments",
        "increment_size",
        "free_space",
    ],
    ("software", "applications", "mssql", "instances"): [
        "name",
        "product",
        "edition",
        "version",
        "clustered",
        "cluster_name",
        "active_node",
        "node_names",
    ],
    ("software", "applications", "ibm_mq", "managers"): [
        "name",
        "instver",
        "instname",
        "status",
        "standby",
        "ha",
    ],
    ("software", "applications", "ibm_mq", "channels"): [
        "qmgr",
        "name",
        "type",
        "status",
        "monchl",
    ],
    ("software", "applications", "ibm_mq", "queues"): [
        "qmgr",
        "name",
        "maxdepth",
        "maxmsgl",
        "created",
        "altered",
        "monq",
    ],
    ("software", "applications", "azure", "application_gateways", "rules", "listeners"): [
        "application_gateway",
        "rule",
        "listener",
        "protocol",
        "port",
        "host_names",
    ],
    (
        "software",
        "applications",
        "azure",
        "application_gateways",
        "rules",
        "listeners",
        "private_ips",
    ): ["application_gateway", "rule", "listener", "ip_address", "allocation_method"],
    (
        "software",
        "applications",
        "azure",
        "application_gateways",
        "rules",
        "listeners",
        "public_ips",
    ): [
        "application_gateway",
        "rule",
        "listener",
        "name",
        "location",
        "ip_address",
        "allocation_method",
        "dns_fqdn",
    ],
    ("software", "applications", "azure", "application_gateways", "rules", "backends"): [
        "application_gateway",
        "rule",
        "address_pool_name",
        "protocol",
        "port",
    ],
    ("software", "applications", "azure", "load_balancers", "inbound_nat_rules"): [
        "load_balancer",
        "inbound_nat_rule",
        "frontend_port",
        "backend_port",
    ],
    ("software", "applications", "azure", "load_balancers", "inbound_nat_rules", "public_ips"): [
        "load_balancer",
        "inbound_nat_rule",
        "location",
        "public_ip_name",
        "ip_address",
        "ip_allocation_method",
        "dns_fqdn",
    ],
    ("software", "applications", "azure", "load_balancers", "inbound_nat_rules", "private_ips"): [
        "load_balancer",
        "inbound_nat_rule",
        "ip_address",
        "ip_allocation_method",
    ],
    (
        "software",
        "applications",
        "azure",
        "load_balancers",
        "inbound_nat_rules",
        "backend_ip_configs",
    ): [
        "load_balancer",
        "inbound_nat_rule",
        "backend_ip_config",
        "ip_address",
        "ip_allocation_method",
    ],
    ("software", "applications", "azure", "load_balancers", "outbound_rules"): [
        "load_balancer",
        "outbound_rule",
        "protocol",
        "idle_timeout",
    ],
    ("software", "applications", "azure", "load_balancers", "outbound_rules", "backend_pools"): [
        "load_balancer",
        "outbound_rule",
        "backend_pool",
    ],
    (
        "software",
        "applications",
        "azure",
        "load_balancers",
        "outbound_rules",
        "backend_pools",
        "addresses",
    ): [
        "load_balancer",
        "outbound_rule",
        "backend_pool",
        "address_name",
        "ip_address",
        "ip_allocation_method",
        "primary",
    ],
    ("software", "kernel_config"): ["name", "value"],
    ("software", "os", "service_packs"): ["name"],
    ("software", "packages"): [
        "name",
        "arch",
        "package_type",
        "summary",
        "version",
        "vendor",
        "package_version",
        "install_date",
        "size",
        "path",
    ],
    ("networking", "addresses"): [
        "address",
        "device",
        "type",
        "network",
        "netmask",
        "prefixlength",
        "broadcast",
        "scope_id",
    ],
    ("networking", "cdp_cache", "neighbors"): [
        "neighbor_name",
        "neighbor_port",
        "local_port",
        "neighbor_address",
        "neighbor_id",
        "platform",
        "platform_details",
        "capabilities",
        "duplex",
        "native_vlan",
        "vtp_mgmt_domain",
        "power_consumption",
    ],
    ("networking", "interfaces"): [
        "index",
        "name",
        "description",
        "alias",
        "oper_status",
        "admin_status",
        "available",
        "speed",
        "last_change",
        "port_type",
        "phys_address",
        "vlantype",
        "vlans",
    ],
    ("networking", "lldp_cache"): [
        "local_cap_supported",
        "local_cap_enabled",
    ],
    ("networking", "lldp_cache", "neighbours"): [
        "capabilities",
        "capabilities_map_supported",
        "local_port",
        "neighbour_address",
        "neighbour_id",
        "neighbour_name",
        "neighbour_port",
        "port_description",
        "system_description",
    ],
    ("networking", "routes"): ["target", "device", "type", "gateway"],
    ("networking", "uplinks"): [
        "interface",
        "protocol",
        "address",
        "gateway",
        "public_address",
        "assignment_mode",
    ],
    ("networking", "wlan", "controller", "accesspoints"): [
        "name",
        "group",
        "ip_addr",
        "model",
        "serial",
        "sys_location",
    ],
    ("networking", "tunnels"): [
        "peername",
        "index",
        "peerip",
        "sourceip",
        "tunnelinterface",
        "linkpriority",
    ],
    ("networking", "sip_interfaces"): [
        "index",
        "name",
        "application_type",
        "sys_interface",
        "device",
        "tcp_port",
        "gateway",
    ],
    ("software", "applications", "vmwareesx"): ["clusters"],
    ("software", "applications", "podman", "containers"): [
        "id",
        "creation",
        "name",
        "labels",
        "status",
        "image",
    ],
    ("software", "applications", "podman", "images"): [
        "id",
        "creation",
        "size",
        "container_num",
        "repository",
        "tag",
    ],
}


def test_related_display_hints() -> None:
    all_paths = [h.path for h in inv_display_hints]
    for hint in inv_display_hints:
        assert all(hint.path[:idx] in all_paths for idx in range(1, len(hint.path)))
        assert _KNOWN_ATTRIBUTES_KEY_ORDERS.get(hint.path, []) == list(hint.attributes), hint.path
        assert _KNOWN_COLUMNS_KEY_ORDERS.get(hint.path, []) == list(hint.table.columns), hint.path


@pytest.mark.parametrize(
    "val_a, val_b, result",
    [
        (None, None, 0),
        (None, 0, -1),
        (0, None, 1),
        (0, 0, 0),
        (1, 0, 1),
        (0, 1, -1),
    ],
)
def test__cmp_inv_generic(val_a: object, val_b: object, result: int) -> None:
    assert _decorate_sort_function(_cmp_inv_generic)(val_a, val_b) == result


@pytest.mark.parametrize(
    "path, expected_node_hint",
    [
        (
            (),
            NodeDisplayHint(
                name="inv",
                path=(),
                icon="",
                title="Inventory tree",
                short_title="Inventory tree",
                long_title="Inventory tree",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ("hardware",),
            NodeDisplayHint(
                path=(SDNodeName("hardware"),),
                name="inv_hardware",
                icon="hardware",
                title="Hardware",
                short_title="Hardware",
                long_title="Hardware",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ("hardware", "cpu"),
            NodeDisplayHint(
                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                name="inv_hardware_cpu",
                icon="",
                title="Processor",
                short_title="Processor",
                long_title="Hardware ➤ Processor",
                # The single attribute hints are not checked here
                attributes={
                    SDKey("arch"): AttributeDisplayHint(
                        name="inv_hardware_cpu_arch",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_arch",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("arch"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("max_speed"): AttributeDisplayHint(
                        name="inv_hardware_cpu_max_speed",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_max_speed",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("max_speed"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("model"): AttributeDisplayHint(
                        name="inv_hardware_cpu_model",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_model",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("model"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("type"): AttributeDisplayHint(
                        name="inv_hardware_cpu_type",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_type",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("type"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("threads"): AttributeDisplayHint(
                        name="inv_hardware_cpu_threads",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_threads",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("threads"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("smt_threads"): AttributeDisplayHint(
                        name="inv_hardware_cpu_smt_threads",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_smt_threads",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("smt_threads"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cpu_max_capa"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cpu_max_capa",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cpu_max_capa",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cpu_max_capa"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cpus"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cpus",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cpus",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cpus"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("logical_cpus"): AttributeDisplayHint(
                        name="inv_hardware_cpu_logical_cpus",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_logical_cpus",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("logical_cpus"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cores"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cores",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cores",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cores"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cores_per_cpu"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cores_per_cpu",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cores_per_cpu",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cores_per_cpu"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("threads_per_cpu"): AttributeDisplayHint(
                        name="inv_hardware_cpu_threads_per_cpu",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_threads_per_cpu",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("threads_per_cpu"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("cache_size"): AttributeDisplayHint(
                        name="inv_hardware_cpu_cache_size",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_cache_size",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("cache_size"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("bus_speed"): AttributeDisplayHint(
                        name="inv_hardware_cpu_bus_speed",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_bus_speed",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("bus_speed"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("voltage"): AttributeDisplayHint(
                        name="inv_hardware_cpu_voltage",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_voltage",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("voltage"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("sharing_mode"): AttributeDisplayHint(
                        name="inv_hardware_cpu_sharing_mode",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_sharing_mode",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("sharing_mode"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("implementation_mode"): AttributeDisplayHint(
                        name="inv_hardware_cpu_implementation_mode",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_implementation_mode",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("implementation_mode"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                    SDKey("entitlement"): AttributeDisplayHint(
                        name="inv_hardware_cpu_entitlement",
                        title="",
                        short_title="",
                        long_title="",
                        paint_function=lambda *args: (
                            TDStyles(
                                css_class="",
                                text_align="",
                                background_color="",
                                color="",
                            ),
                            "",
                        ),
                        sort_function=lambda *args: 0,
                        filter=FilterInvText(
                            ident="inv_hardware_cpu_entitlement",
                            title="",
                            inventory_path=InventoryPath(
                                path=(SDNodeName("hardware"), SDNodeName("cpu")),
                                source=TreeSource.attributes,
                                key=SDKey("entitlement"),
                            ),
                            is_show_more=True,
                        ),
                    ),
                },
                table=Table(columns={}),
            ),
        ),
        (
            ("software", "applications", "docker", "images"),
            NodeDisplayHint(
                name="inv_software_applications_docker_images",
                path=(
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("docker"),
                    SDNodeName("images"),
                ),
                icon="",
                title="Images",
                short_title="Images",
                long_title="Docker ➤ Images",
                attributes={},
                # The single column hints are not checked here
                table=TableWithView(
                    columns={
                        SDKey("id"): ColumnDisplayHintOfView(
                            name="invdockerimages_id",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_id",
                                title="",
                            ),
                        ),
                        SDKey("creation"): ColumnDisplayHintOfView(
                            name="invdockerimages_creation",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_creation",
                                title="",
                            ),
                        ),
                        SDKey("size"): ColumnDisplayHintOfView(
                            name="invdockerimages_size",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_size",
                                title="",
                            ),
                        ),
                        SDKey("labels"): ColumnDisplayHintOfView(
                            name="invdockerimages_labels",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_labels",
                                title="",
                            ),
                        ),
                        SDKey("amount_containers"): ColumnDisplayHintOfView(
                            name="invdockerimages_amount_containers",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_amount_containers",
                                title="",
                            ),
                        ),
                        SDKey("repotags"): ColumnDisplayHintOfView(
                            name="invdockerimages_repotags",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_repotags",
                                title="",
                            ),
                        ),
                        SDKey("repodigests"): ColumnDisplayHintOfView(
                            name="invdockerimages_repodigests",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockerimages",
                                ident="invdockerimages_repodigests",
                                title="",
                            ),
                        ),
                    },
                    name="invdockerimages",
                    path=(
                        SDNodeName("software"),
                        SDNodeName("applications"),
                        SDNodeName("docker"),
                        SDNodeName("images"),
                    ),
                    long_title="Docker ➤ Images",
                    icon=DynamicIconName(""),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            NodeDisplayHint(
                name="inv_path_to_node",
                path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                icon="",
                title="Node",
                short_title="Node",
                long_title="To ➤ Node",
                attributes={},
                table=Table(columns={}),
            ),
        ),
    ],
)
def test_make_node_displayhint(path: SDPath, expected_node_hint: NodeDisplayHint) -> None:
    node_hint = inv_display_hints.get_node_hint(path)

    assert node_hint.name == expected_node_hint.name
    assert node_hint.icon == expected_node_hint.icon
    assert node_hint.title == expected_node_hint.title
    assert node_hint.long_title == expected_node_hint.long_title
    assert node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(node_hint.attributes) == list(expected_node_hint.attributes)
    assert list(node_hint.table.columns) == list(expected_node_hint.table.columns)

    if isinstance(expected_node_hint.table, TableWithView):
        assert isinstance(node_hint.table, TableWithView)
        assert node_hint.table.name == expected_node_hint.table.name
        assert node_hint.table.path == expected_node_hint.table.path
        assert node_hint.table.long_title == expected_node_hint.table.long_title
        assert node_hint.table.icon == expected_node_hint.table.icon
        assert node_hint.table.is_show_more == expected_node_hint.table.is_show_more


@pytest.mark.parametrize(
    "raw_path, expected_node_hint",
    [
        (
            ".foo.bar.",
            NodeDisplayHint(
                name="invfoo_bar",
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".foo.bar:",
            NodeDisplayHint(
                name="invfoo_bar",
                path=(SDNodeName("foo"), SDNodeName("bar")),
                icon="",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".software.",
            NodeDisplayHint(
                name="invsoftware",
                path=(SDNodeName("software"),),
                icon="software",
                title="Software",
                short_title="Software",
                long_title="Software",
                attributes={},
                table=Table(columns={}),
            ),
        ),
        (
            ".software.applications.docker.containers:",
            NodeDisplayHint(
                name="invsoftware_applications_docker_containers",
                path=(
                    SDNodeName("software"),
                    SDNodeName("applications"),
                    SDNodeName("docker"),
                    SDNodeName("containers"),
                ),
                icon="",
                title="Containers",
                short_title="Containers",
                long_title="Docker ➤ Containers",
                attributes={},
                # The single column hints are not checked here
                table=TableWithView(
                    columns={
                        SDKey("id"): ColumnDisplayHintOfView(
                            name="invdockercontainers_id",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_id",
                                title="",
                            ),
                        ),
                        SDKey("creation"): ColumnDisplayHintOfView(
                            name="invdockercontainers_creation",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_creation",
                                title="",
                            ),
                        ),
                        SDKey("name"): ColumnDisplayHintOfView(
                            name="invdockercontainers_name",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_name",
                                title="",
                            ),
                        ),
                        SDKey("labels"): ColumnDisplayHintOfView(
                            name="invdockercontainers_labels",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_labels",
                                title="",
                            ),
                        ),
                        SDKey("status"): ColumnDisplayHintOfView(
                            name="invdockercontainers_status",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_status",
                                title="",
                            ),
                        ),
                        SDKey("image"): ColumnDisplayHintOfView(
                            name="invdockercontainers_image",
                            title="",
                            short_title="",
                            long_title="",
                            paint_function=lambda *args: (
                                TDStyles(
                                    css_class="",
                                    text_align="",
                                    background_color="",
                                    color="",
                                ),
                                "",
                            ),
                            sort_function=lambda *args: 0,
                            filter=FilterInvtableText(
                                inv_info="invdockercontainers",
                                ident="invdockercontainers_image",
                                title="",
                            ),
                        ),
                    },
                    name="invdockercontainers",
                    path=(
                        SDNodeName("software"),
                        SDNodeName("applications"),
                        SDNodeName("docker"),
                        SDNodeName("containers"),
                    ),
                    long_title="Docker ➤ Containers",
                    icon=DynamicIconName(""),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_node_displayhint_from_hint(
    raw_path: str, expected_node_hint: NodeDisplayHint
) -> None:
    node_hint = inv_display_hints.get_node_hint(
        cmk.gui.inventory.parse_internal_raw_path(raw_path).path
    )

    assert node_hint.name == "_".join(("inv",) + node_hint.path)
    assert node_hint.icon == expected_node_hint.icon
    assert node_hint.title == expected_node_hint.title
    assert node_hint.long_title == expected_node_hint.long_title
    assert node_hint.long_inventory_title == expected_node_hint.long_inventory_title

    assert list(node_hint.attributes) == list(expected_node_hint.attributes)
    assert list(node_hint.table.columns) == list(expected_node_hint.table.columns)

    if isinstance(expected_node_hint.table, TableWithView):
        assert isinstance(node_hint.table, TableWithView)
        assert node_hint.table.name == expected_node_hint.table.name
        assert node_hint.table.path == expected_node_hint.table.path
        assert node_hint.table.long_title == expected_node_hint.table.long_title
        assert node_hint.table.icon == expected_node_hint.table.icon
        assert node_hint.table.is_show_more == expected_node_hint.table.is_show_more


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            (),
            "key",
            ColumnDisplayHint(
                title="Key",
                short_title="Key",
                long_title="Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            ColumnDisplayHint(
                title="Key",
                short_title="Key",
                long_title="Node ➤ Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
            ),
        ),
    ],
)
def test_make_column_displayhint(path: SDPath, key: str, expected: ColumnDisplayHint) -> None:
    hint = inv_display_hints.get_node_hint(path).get_column_hint(key)
    assert isinstance(hint, ColumnDisplayHint)
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            ("networking", "interfaces"),
            "oper_status",
            ColumnDisplayHintOfView(
                name="invinterface_oper_status",
                title="Operational status",
                short_title="Operational status",
                long_title="Network interfaces ➤ Operational status",
                paint_function=_wrap_paint_function(inv_paint_if_oper_status),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invinterface",
                    ident="invinterface_oper_status",
                    title="Network interfaces ➤ Operational status",
                ),
            ),
        ),
        (
            ("software", "applications", "check_mk", "sites"),
            "cmc",
            ColumnDisplayHintOfView(
                name="invcmksites_cmc",
                title="CMC status",
                short_title="CMC status",
                long_title="Checkmk sites ➤ CMC status",
                paint_function=_wrap_paint_function(inv_paint_service_status),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invcmksites",
                    ident="invcmksites_cmc",
                    title="Checkmk sites ➤ CMC status",
                ),
            ),
        ),
    ],
)
def test_make_column_displayhint_of_view(
    path: SDPath, key: str, expected: ColumnDisplayHintOfView
) -> None:
    hint = inv_display_hints.get_node_hint(path).get_column_hint(key)
    assert isinstance(hint, ColumnDisplayHintOfView)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter is not None
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo:*.bar",
            ColumnDisplayHint(
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                paint_function=_wrap_paint_function(inv_paint_generic),
            ),
        ),
    ],
)
def test_make_column_displayhint_from_hint(raw_path: str, expected: ColumnDisplayHint) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_column_hint(
        inventory_path.key or ""
    )
    assert isinstance(hint, ColumnDisplayHint)
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".software.packages:*.package_version",
            ColumnDisplayHintOfView(
                name="invswpac_package_version",
                title="Package version",
                short_title="Package version",
                long_title="Software packages ➤ Package version",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(cmp_version),
                filter=FilterInvtableText(
                    inv_info="invswpac",
                    ident="invswpac_package_version",
                    title="Software packages ➤ Package version",
                ),
            ),
        ),
        (
            ".software.packages:*.version",
            ColumnDisplayHintOfView(
                name="invswpac_version",
                title="Version",
                short_title="Version",
                long_title="Software packages ➤ Version",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(cmp_version),
                filter=FilterInvtableText(
                    inv_info="invswpac",
                    ident="invswpac_version",
                    title="Software packages ➤ Version",
                ),
            ),
        ),
        (
            ".networking.interfaces:*.index",
            ColumnDisplayHintOfView(
                name="invinterface_index",
                title="Index",
                short_title="Index",
                long_title="Network interfaces ➤ Index",
                paint_function=_wrap_paint_function(inv_paint_number),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invinterface",
                    ident="invinterface_index",
                    title="Network interfaces ➤ Index",
                ),
            ),
        ),
        (
            ".networking.interfaces:*.oper_status",
            ColumnDisplayHintOfView(
                name="invinterface_oper_status",
                title="Operational status",
                short_title="Operational status",
                long_title="Network interfaces ➤ Operational status",
                paint_function=_wrap_paint_function(inv_paint_if_oper_status),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvtableText(
                    inv_info="invinterface",
                    ident="invinterface_oper_status",
                    title="Network interfaces ➤ Operational status",
                ),
            ),
        ),
    ],
)
def test_make_column_displayhint_of_view_from_hint(
    raw_path: str, expected: ColumnDisplayHintOfView
) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_column_hint(
        inventory_path.key or ""
    )
    assert isinstance(hint, ColumnDisplayHintOfView)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter is not None
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "path, key, expected",
    [
        (
            (),
            "key",
            AttributeDisplayHint(
                name="inv_key",
                title="Key",
                short_title="Key",
                long_title="Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_key",
                    title="Key",
                    inventory_path=InventoryPath(
                        path=(),
                        source=TreeSource.attributes,
                        key=SDKey("key"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ("hardware", "storage", "disks"),
            "size",
            AttributeDisplayHint(
                name="inv_hardware_storage_disks_size",
                title="Size",
                short_title="Size",
                long_title="Block devices ➤ Size",
                paint_function=_wrap_paint_function(inv_paint_size),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_storage_disks_size",
                    title="Block devices ➤ Size",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("storage"), SDNodeName("disks")),
                        source=TreeSource.attributes,
                        key=SDKey("size"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ("path", "to", "node"),
            "key",
            AttributeDisplayHint(
                name="inv_path_to_node_key",
                title="Key",
                short_title="Key",
                long_title="Node ➤ Key",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_path_to_node_key",
                    title="Node ➤ Key",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("path"), SDNodeName("to"), SDNodeName("node")),
                        source=TreeSource.attributes,
                        key=SDKey("key"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_attribute_displayhint(path: SDPath, key: str, expected: AttributeDisplayHint) -> None:
    hint = inv_display_hints.get_node_hint(path).get_attribute_hint(key)
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "raw_path, expected",
    [
        (
            ".foo.bar",
            AttributeDisplayHint(
                name="inv_foo_bar",
                title="Bar",
                short_title="Bar",
                long_title="Foo ➤ Bar",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_foo_bar",
                    title="Foo ➤ Bar",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("foo"),),
                        source=TreeSource.attributes,
                        key=SDKey("bar"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ".hardware.cpu.arch",
            AttributeDisplayHint(
                name="inv_hardware_cpu_arch",
                title="CPU architecture",
                short_title="CPU architecture",
                long_title="Processor ➤ CPU architecture",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_cpu_arch",
                    title="Processor ➤ CPU architecture",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("cpu")),
                        source=TreeSource.attributes,
                        key=SDKey("arch"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
        (
            ".hardware.system.product",
            AttributeDisplayHint(
                name="inv_hardware_system_product",
                title="Product",
                short_title="Product",
                long_title="System ➤ Product",
                paint_function=_wrap_paint_function(inv_paint_generic),
                sort_function=_decorate_sort_function(_cmp_inv_generic),
                filter=FilterInvText(
                    ident="inv_hardware_system_product",
                    title="System ➤ Product",
                    inventory_path=InventoryPath(
                        path=(SDNodeName("hardware"), SDNodeName("system")),
                        source=TreeSource.attributes,
                        key=SDKey("product"),
                    ),
                    is_show_more=True,
                ),
            ),
        ),
    ],
)
def test_make_attribute_displayhint_from_hint(
    raw_path: str, expected: AttributeDisplayHint
) -> None:
    inventory_path = cmk.gui.inventory.parse_internal_raw_path(raw_path)
    hint = inv_display_hints.get_node_hint(inventory_path.path).get_attribute_hint(
        inventory_path.key or ""
    )
    assert hint.name == expected.name
    assert hint.title == expected.title
    assert hint.short_title == expected.short_title
    assert hint.long_title == expected.long_title
    assert callable(hint.paint_function)
    assert callable(hint.sort_function)
    assert hint.filter.ident == expected.filter.ident
    assert hint.filter.title == expected.filter.title
    assert hint.long_inventory_title == expected.long_inventory_title


@pytest.mark.parametrize(
    "view_name, expected_view_name",
    [
        ("", ""),
        ("viewname", "invviewname"),
        ("invviewname", "invviewname"),
        ("viewname_of_host", "invviewname"),
        ("invviewname_of_host", "invviewname"),
    ],
)
def test__parse_view_name(view_name: str, expected_view_name: str) -> None:
    assert _parse_view_name(view_name) == expected_view_name


def test_render_bool() -> None:
    bool_field = BoolFieldFromAPI(
        TitleFromAPI("A title"),
        render_true=LabelFromAPI("It's true"),
        render_false=LabelFromAPI("It's false"),
    )
    assert _PaintBool(bool_field)(123, True) == (
        TDStyles(css_class="", text_align="left", background_color="", color=""),
        "It's true",
    )
    assert _PaintBool(bool_field)(456, False) == (
        TDStyles(css_class="", text_align="left", background_color="", color=""),
        "It's false",
    )


@pytest.mark.parametrize(
    ["render", "value", "expected"],
    [
        pytest.param(lambda v: "one" if v == 1 else "more", 1, "one", id="Callable"),
        pytest.param(
            UnitFromAPI(notation=DecimalNotationFromAPI("count")),
            1.00,
            "1 count",
            id="DecimalNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=SINotationFromAPI("B")),
            1000,
            "1 kB",
            id="SINotation",
        ),
        pytest.param(
            UnitFromAPI(notation=IECNotationFromAPI("bits")),
            1024,
            "1 Kibits",
            id="IECNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=StandardScientificNotationFromAPI("snakes")),
            1000,
            "1e+3 snakes",
            id="StandardScientificNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=TimeNotationFromAPI()),
            60,
            "1 min",
            id="TimeNotation",
        ),
        pytest.param(
            UnitFromAPI(notation=AgeNotationFromAPI()),
            datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC).timestamp(),
            "1 min",
            id="AgeNotation",
        ),
    ],
)
def test_render_number(
    render: Callable[[int | float], LabelFromAPI | str] | UnitFromAPI,
    value: int | float,
    expected: str,
) -> None:
    number_field = NumberFieldFromAPI(
        TitleFromAPI("A title"), render=render, style=lambda _: [AlignmentFromAPI.CENTER]
    )
    now = datetime.datetime(2025, 1, 1, 0, 1, 0, tzinfo=datetime.UTC).timestamp()
    assert _PaintNumber(number_field)(now, value) == (
        TDStyles(css_class="", text_align="center", background_color="", color=""),
        expected,
    )


def test_render_text() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [LabelColorFromAPI.PINK],
    )
    assert _PaintText(text_field)(123, "world") == (
        TDStyles(css_class="", text_align="left", background_color="", color="#ec48b6"),
        "hello world",
    )


def test_render_text_with_background_color() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [BackgroundColorFromAPI.BLUE],
    )
    assert _PaintText(text_field)(123, "world") == (
        TDStyles(css_class="", text_align="left", background_color="#28a2f3", color="#1e262e"),
        "hello world",
    )


def test_render_text_with_background_and_text_color() -> None:
    text_field = TextFieldFromAPI(
        TitleFromAPI("A title"),
        render=lambda v: f"hello {v}",
        style=lambda _: [LabelColorFromAPI.PINK, BackgroundColorFromAPI.BLUE],
    )
    assert _PaintText(text_field)(123, "world") == (
        TDStyles(css_class="", text_align="left", background_color="#28a2f3", color="#ec48b6"),
        "hello world",
    )


def test_render_choice() -> None:
    choice_field = ChoiceFieldFromAPI(
        TitleFromAPI("A title"),
        mapping={1: LabelFromAPI("One")},
    )
    assert _PaintChoice(choice_field)(123, 1) == (
        TDStyles(css_class="", text_align="center", background_color="", color=""),
        "One",
    )
    assert _PaintChoice(choice_field)(456, 2) == (
        TDStyles(css_class="", text_align="center", background_color="", color=""),
        "<2> (No such value)",
    )


def test_sort_text() -> None:
    text_field = TextFieldFromAPI(TitleFromAPI("A title"), sort_key=int)
    assert _decorate_sort_function(_SortFunctionText(text_field))("1", "2") == -1
    assert _decorate_sort_function(_SortFunctionText(text_field))("2", "1") == 1


def test_sort_choice() -> None:
    choice_field = ChoiceFieldFromAPI(
        TitleFromAPI("A title"),
        mapping={
            2: LabelFromAPI("Two"),
            1: LabelFromAPI("One"),
        },
    )
    assert _decorate_sort_function(_SortFunctionChoice(choice_field))(1, 2) == 1
    assert _decorate_sort_function(_SortFunctionChoice(choice_field))(2, 1) == -1
