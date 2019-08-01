#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# YAPF is disabled in the next section to get simpler overview of the keys
# present in the dictionary as they are packed together much more
# densely. You are responsible of manually formatting this dictionary, or
# at your choice adding temporarily in the style file the option:
# each_dict_entry_on_separate_line=False

import cmk.gui.utils
from cmk.gui.plugins.views import (
    inventory_displayhints,)
from cmk.gui.i18n import _

from cmk.gui.plugins.visuals.inventory import (
    FilterInvtableVersion,
    FilterInvtableIDRange,
    FilterInvtableOperStatus,
    FilterInvtableAdminStatus,
    FilterInvtableAvailable,
    FilterInvtableInterfaceType,
    FilterInvtableTimestampAsAge,
)

# yapf: disable

inventory_displayhints.update({
    ".": {"title": _("Inventory")},
    ".hardware.": {"title": _("Hardware"), "icon": "hardware"},
    ".hardware.chassis.": {"title": _("Chassis")},
    ".hardware.cpu.": {"title": _("Processor")},
    ".hardware.cpu.model": {"title": _("Model"), "short": _("CPU Model")},
    ".hardware.cpu.cache_size": {"title": _("Cache Size"), "paint": "bytes"},
    ".hardware.cpu.max_speed": {"title": _("Maximum Speed"), "paint": "hz"},
    ".hardware.cpu.bus_speed": {"title": _("Bus Speed"), "paint": "hz"},
    ".hardware.cpu.voltage": {"title": _("Voltage"), "paint": "volt"},
    ".hardware.cpu.cores_per_cpu": {"title": _("Cores per CPU"), "paint": "count"},
    ".hardware.cpu.threads_per_cpu": {"title": _("Hyperthreads per CPU"), "paint": "count"},
    ".hardware.cpu.threads": {"title": _("Total Number of Hyperthreads"), "paint": "count"},
    ".hardware.cpu.smt_threads": {"title": _("Simultaneous multithreading"), "paint": "count"},
    ".hardware.cpu.sharing_mode": {"title": _("CPU sharing mode")},
    ".hardware.cpu.cpus": {
        "title": _("Number of physical CPUs"), "short": _("CPUs"), "paint": "count"
    },
    ".hardware.cpu.logical_cpus": {
        "title": _("Number of logical CPUs"), "short": _("Logical CPUs"), "paint": "count"
    },
    ".hardware.cpu.arch": {"title": _("CPU Architecture"), "short": _("CPU Arch")},
    ".hardware.cpu.cores": {
        "title": _("Total Number of Cores"), "short": _("Cores"), "paint": "count"
    },
    ".hardware.cpu.entitlement": {"title": _("CPU Entitlement")},
    ".hardware.memory.": {"title": _("Memory (RAM)")},
    ".hardware.memory.total_ram_usable": {"title": _("Total usable RAM"), "paint": "bytes_rounded"},
    ".hardware.memory.total_swap": {"title": _("Total swap space"), "paint": "bytes_rounded"},
    ".hardware.memory.total_vmalloc": {
        "title": _("Virtual addresses for mapping"), "paint": "bytes_rounded"
    },
    ".hardware.memory.arrays:": {"title": _("Arrays (Controllers)")},
    ".hardware.memory.arrays:*.": {"title": _("Controller %d")},
    ".hardware.memory.arrays:*.devices:": {
        "title": _("Devices"),
        "keyorder": [
            "locator",
            "bank_locator",
            "type",
            "form_factor",
            "speed",
            "data_width",
            "total_width",
            "manufacturer",
            "serial",
        ],
    },
    ".hardware.memory.arrays:*.maximum_capacity": {
        "title": _("Maximum Capacity"), "paint": "bytes"
    },
    ".hardware.memory.arrays:*.devices:*.": {"title": lambda v: v["locator"]},
    ".hardware.memory.arrays:*.devices:*.size": {"title": _("Size"), "paint": "bytes"},
    ".hardware.memory.arrays:*.devices:*.speed": {"title": _("Speed"), "paint": "hz"},
    ".hardware.system.": {"title": _("System")},
    ".hardware.system.product": {"title": _("Product")},
    ".hardware.system.serial": {"title": _("Serial Number")},
    ".hardware.system.expresscode": {"title": _("Express Servicecode")},
    ".hardware.system.model": {"title": _("Model Name")},
    ".hardware.system.manufacturer": {"title": _("Manufacturer")},

    # Legacy ones. Kept to not break existing views - DON'T use these values for new plugins
    ".hardware.system.serial_number": {"title": _("Serial Number - LEGACY, don't use")},
    ".hardware.system.model_name": {"title": _("Model Name - LEGACY, don't use")},
    ".hardware.components.": {"title": _("Physical Components")},
    ".hardware.components.others:": {
        "title": _("Other entities"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invother_of_host",
    },
    ".hardware.components.others:*.index": {"title": _("Index")},
    ".hardware.components.others:*.name": {"title": _("Name")},
    ".hardware.components.others:*.description": {"title": _("Description")},
    ".hardware.components.others:*.software": {"title": _("Software")},
    ".hardware.components.others:*.serial": {"title": _("Serial Number")},
    ".hardware.components.others:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.others:*.model": {"title": _("Model Name")},
    ".hardware.components.others:*.location": {"title": _("Location")},
    ".hardware.components.unknowns:": {
        "title": _("Unknown entities"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invunknown_of_host",
    },
    ".hardware.components.unknowns:*.index": {"title": _("Index")},
    ".hardware.components.unknowns:*.name": {"title": _("Name")},
    ".hardware.components.unknowns:*.description": {"title": _("Description")},
    ".hardware.components.unknowns:*.software": {"title": _("Software")},
    ".hardware.components.unknowns:*.serial": {"title": _("Serial Number")},
    ".hardware.components.unknowns:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.unknowns:*.model": {"title": _("Model Name")},
    ".hardware.components.unknowns:*.location": {"title": _("Location")},
    ".hardware.components.chassis:": {
        "title": _("Chassis"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invchassis_of_host",
    },
    ".hardware.components.chassis:*.index": {"title": _("Index")},
    ".hardware.components.chassis:*.name": {"title": _("Name")},
    ".hardware.components.chassis:*.description": {"title": _("Description")},
    ".hardware.components.chassis:*.software": {"title": _("Software")},
    ".hardware.components.chassis:*.serial": {"title": _("Serial Number")},
    ".hardware.components.chassis:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.chassis:*.model": {"title": _("Model Name")},
    ".hardware.components.chassis:*.location": {"title": _("Location")},
    ".hardware.components.backplanes:": {
        "title": _("Backplanes"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invbackplane_of_host",
    },
    ".hardware.components.backplanes:*.index": {"title": _("Index")},
    ".hardware.components.backplanes:*.name": {"title": _("Name")},
    ".hardware.components.backplanes:*.description": {"title": _("Description")},
    ".hardware.components.backplanes:*.software": {"title": _("Software")},
    ".hardware.components.backplanes:*.serial": {"title": _("Serial Number")},
    ".hardware.components.backplanes:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.backplanes:*.model": {"title": _("Model Name")},
    ".hardware.components.backplanes:*.location": {"title": _("Location")},
    ".hardware.components.containers:": {
        "title": _("Containers"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invcontainer_of_host",
    },
    ".hardware.components.containers:*.index": {"title": _("Index")},
    ".hardware.components.containers:*.name": {"title": _("Name")},
    ".hardware.components.containers:*.description": {"title": _("Description")},
    ".hardware.components.containers:*.software": {"title": _("Software")},
    ".hardware.components.containers:*.serial": {"title": _("Serial Number")},
    ".hardware.components.containers:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.containers:*.model": {"title": _("Model Name")},
    ".hardware.components.containers:*.location": {"title": _("Location")},
    ".hardware.components.psus:": {
        "title": _("Power Supplies"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invpsu_of_host",
    },
    ".hardware.components.psus:*.index": {"title": _("Index")},
    ".hardware.components.psus:*.name": {"title": _("Name")},
    ".hardware.components.psus:*.description": {"title": _("Description")},
    ".hardware.components.psus:*.software": {"title": _("Software")},
    ".hardware.components.psus:*.serial": {"title": _("Serial Number")},
    ".hardware.components.psus:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.psus:*.model": {"title": _("Model Name")},
    ".hardware.components.psus:*.location": {"title": _("Location")},
    ".hardware.components.fans:": {
        "title": _("Fans"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invfan_of_host",
    },
    ".hardware.components.fans:*.index": {"title": _("Index")},
    ".hardware.components.fans:*.name": {"title": _("Name")},
    ".hardware.components.fans:*.description": {"title": _("Description")},
    ".hardware.components.fans:*.software": {"title": _("Software")},
    ".hardware.components.fans:*.serial": {"title": _("Serial Number")},
    ".hardware.components.fans:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.fans:*.model": {"title": _("Model Name")},
    ".hardware.components.fans:*.location": {"title": _("Location")},
    ".hardware.components.sensors:": {
        "title": _("Sensors"),
        "keyorder": [
            "index",
            "name",
            "description",
            "software",
            "serial",
            "manufacturer",
            "model",
            "location",
        ],
        "view": "invsensor_of_host",
    },
    ".hardware.components.sensors:*.index": {"title": _("Index")},
    ".hardware.components.sensors:*.name": {"title": _("Name")},
    ".hardware.components.sensors:*.description": {"title": _("Description")},
    ".hardware.components.sensors:*.software": {"title": _("Software")},
    ".hardware.components.sensors:*.serial": {"title": _("Serial Number")},
    ".hardware.components.sensors:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.sensors:*.model": {"title": _("Model Name")},
    ".hardware.components.sensors:*.location": {"title": _("Location")},
    ".hardware.components.modules:": {
        "title": _("Modules"),
        "keyorder": [
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
        ],
        "view": "invmodule_of_host",
    },
    ".hardware.components.modules:*.index": {"title": _("Index")},
    ".hardware.components.modules:*.name": {"title": _("Name")},
    ".hardware.components.modules:*.description": {"title": _("Description")},
    ".hardware.components.modules:*.software": {"title": _("Software")},
    ".hardware.components.modules:*.serial": {"title": _("Serial Number")},
    ".hardware.components.modules:*.model": {"title": _("Model Name")},
    ".hardware.components.modules:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.modules:*.bootloader": {"title": _("Bootloader")},
    ".hardware.components.modules:*.firmware": {"title": _("Firmware")},
    ".hardware.components.modules:*.type": {"title": _("Type")},
    ".hardware.components.modules:*.location": {"title": _("Location")},
    ".hardware.components.stacks:": {
        "title": _("Stacks"),
        "keyorder": ["index", "name", "description", "software", "serial", "model", "location"],
        "view": "invstack_of_host",
    },
    ".hardware.components.stacks:*.index": {"title": _("Index")},
    ".hardware.components.stacks:*.name": {"title": _("Name")},
    ".hardware.components.stacks:*.description": {"title": _("Description")},
    ".hardware.components.stacks:*.software": {"title": _("Software")},
    ".hardware.components.stacks:*.serial": {"title": _("Serial Number")},
    ".hardware.components.stacks:*.manufacturer": {"title": _("Manufacturer")},
    ".hardware.components.stacks:*.model": {"title": _("Model Name")},
    ".hardware.components.stacks:*.location": {"title": _("Location")},
    ".hardware.storage.": {"title": _("Storage")},
    ".hardware.storage.controller.": {"title": _("Controller")},
    ".hardware.storage.controller.version": {"title": _("Version")},
    ".hardware.storage.disks:": {"title": _("Block Devices")},
    ".hardware.storage.disks:*.": {"title": _("Block Device %d")},
    ".hardware.storage.disks:*.signature": {"title": _("Disk ID")},
    ".hardware.storage.disks:*.vendor": {"title": _("Vendor")},
    ".hardware.storage.disks:*.local": {"title": _("Local")},
    ".hardware.storage.disks:*.bus": {"title": _("Bus")},
    ".hardware.storage.disks:*.product": {"title": _("Product")},
    ".hardware.storage.disks:*.fsnode": {"title": _("Filesystem Node")},
    ".hardware.storage.disks:*.serial": {"title": _("Serial Number")},
    ".hardware.storage.disks:*.size": {"title": _("Size"), "paint": "size"},
    ".hardware.storage.disks:*.type": {"title": _("Type")},
    ".hardware.video:": {"title": _("Graphic Cards")},
    ".hardware.video:*.": {"title": _("Graphic Card %d")},
    ".hardware.video:*.name": {"title": _("Graphic Card Name"), "short": _("Card Name")},
    ".hardware.video:*.subsystem": {"title": _("Vendor and Device ID"), "short": _("Vendor")},
    ".hardware.video:*.driver": {"title": _("Driver"), "short": _("Driver")},
    ".hardware.video:*.driver_date": {"title": _("Driver Date"), "short": _("Driver Date")},
    ".hardware.video:*.driver_version": {
        "title": _("Driver Version"), "short": _("Driver Version")
    },
    ".hardware.video:*.graphic_memory": {"title": _("Memory"), "paint": "bytes_rounded"},
    ".hardware.nwadapter:": {"title": _("Network Adapters")},
    ".hardware.nwadapter:*.": {"title": _("Network Adapter %d")},
    ".hardware.nwadapter:*.name": {"title": _("Name")},
    ".hardware.nwadapter:*.type": {"title": _("Type")},
    ".hardware.nwadapter:*.macaddress": {"title": _("Physical Address (MAC)")},
    ".hardware.nwadapter:*.speed": {"title": _("Speed"), "paint": "nic_speed"},
    ".hardware.nwadapter:*.ipv4_address": {"title": _("IPv4 Address")},
    ".hardware.nwadapter:*.ipv4_subnet": {"title": _("IPv4 Subnet")},
    ".hardware.nwadapter:*.ipv6_address": {"title": _("IPv6 Address")},
    ".hardware.nwadapter:*.ipv6_subnet": {"title": _("IPv6 Subnet")},
    ".hardware.nwadapter:*.gateway": {"title": _("Gateway")},
    ".software.": {"title": _("Software"), "icon": "software"},
    ".software.bios.": {"title": _("BIOS")},
    ".software.bios.vendor": {"title": _("Vendor")},
    ".software.bios.version": {"title": _("Version")},
    ".software.bios.date": {"title": _("Date"), "paint": "date"},
    ".software.firmware.vendor": {"title": _("Vendor")},
    ".software.firmware.version": {"title": _("Version")},
    ".software.firmware.platform_level": {"title": _("Platform Firmware level")},
    ".software.os.": {"title": _("Operating System")},
    ".software.os.name": {"title": _("Name"), "short": _("Operating System")},
    ".software.os.version": {"title": _("Version")},
    ".software.os.vendor": {"title": _("Vendor")},
    ".software.os.type": {"title": _("Type")},  # e.g. "linux"
    ".software.os.install_date": {"title": _("Install Date"), "paint": "date"},
    ".software.os.kernel_version": {"title": _("Kernel Version"), "short": _("Kernel")},
    ".software.os.arch": {"title": _("Kernel Architecture"), "short": _("Architecture")},
    ".software.os.service_pack": {"title": _("Latest Service Pack"), "short": _("Service Pack")},
    ".software.os.service_packs:": {"title": _("Service Packs"), "keyorder": ["name"]},
    ".software.configuration.": {"title": _("Configuration")},
    ".software.configuration.snmp_info.": {"title": _("SNMP Information")},
    ".software.configuration.snmp_info.contact": {"title": _("Contact")},
    ".software.configuration.snmp_info.location": {"title": _("Location")},
    ".software.configuration.snmp_info.name": {"title": _("System name")},
    ".software.packages:": {
        "title": _("Packages"),
        "icon": "packages",
        "keyorder": ["name", "version", "arch", "package_type", "summary"],
        "view": "invswpac_of_host",
    },
    ".software.packages:*.name": {"title": _("Name")},
    ".software.packages:*.arch": {"title": _("Architecture")},
    ".software.packages:*.package_type": {"title": _("Type")},
    ".software.packages:*.summary": {"title": _("Description")},
    ".software.packages:*.version": {
        "title": _("Version"), "sort": cmk.gui.utils.cmp_version, "filter": FilterInvtableVersion
    },
    ".software.packages:*.vendor": {"title": _("Publisher")},
    ".software.packages:*.package_version": {
        "title": _("Package Version"), "sort": cmk.gui.utils.cmp_version, "filter": FilterInvtableVersion
    },
    ".software.packages:*.install_date": {"title": _("Install Date"), "paint": "date"},
    ".software.packages:*.size": {"title": _("Size"), "paint": "count"},
    ".software.packages:*.path": {"title": _("Path")},
    ".software.applications.": {"title": _("Applications")},
    ".software.applications.check_mk.": {"title": _("Check_MK")},
    ".software.applications.check_mk.cluster.is_cluster": {
        "title": _("Cluster host"), "short": _("Cluster"), "paint": "bool"
    },
    ".software.applications.check_mk.cluster.nodes:": {"title": _("Nodes")},
    ".software.applications.check_mk.host_labels:": {
        "title": _("Discovered host labels"),
        "keyorder": [
            "label",
            "plugin_name",
        ],
    },
    ".software.applications.check_mk.host_labels:*.label": {
        "title": _("Label"),
        "paint": "cmk_label",
    },
    ".software.applications.check_mk.host_labels:*.plugin_name": {
        "title": _("Discovered by plugin"),
    },
    ".software.applications.docker.": {
        "icon": "docker", "title": "Docker", "keyorder": [
            "version",
            "num_containers_total",
            "num_containers_running",
            "num_containers_stopped",
            "num_containers_paused",
            "num_images",
            "registry",
        ]
    },
    ".software.applications.docker.version": {"title": _("Version")},
    ".software.applications.docker.num_containers_total": {"title": _("# Containers"), "short": _("Containers"),},
    ".software.applications.docker.num_containers_running": {"title": _("# Containers running"), "short": _("Running"),},
    ".software.applications.docker.num_containers_stopped": {"title": _("# Containers stopped"), "short": _("Stopped"),},
    ".software.applications.docker.num_containers_paused": {"title": _("# Containers paused"), "short": _("Paused"),},
    ".software.applications.docker.num_images": {"title": _("# Images")},
    ".software.applications.docker.images:": {
        "title": _("Images"),
        "keyorder": ["id", "creation", "size", "labels", "amount_containers", "repotags", "repodigests"],
        "view": "invdockerimages_of_host",
    },
    ".software.applications.docker.images:*.id": {"title": _("ID")},
    ".software.applications.docker.images:*.size": {"paint": "size"},
    ".software.applications.docker.images:*.labels": {"paint": "csv_labels"},
    ".software.applications.docker.images:*.amount_containers": {"title": _("# Containers")},
    ".software.applications.docker.images:*.repotags": {"title": _("Repository/Tag"), "paint": "csv_labels"},
    ".software.applications.docker.images:*.repodigests": {"title": _("Digests"), "paint": "csv_labels"},

    # Node containers
    ".software.applications.docker.containers:": {
        "title": _("Containers"),
        "keyorder": ["id", "creation", "name", "labels", "status", "image"],
        "view": "invdockercontainers_of_host",
    },
    ".software.applications.docker.containers:*.id": {"title": _("ID")},
    ".software.applications.docker.containers:*.labels": {"paint": "csv_labels"},
    ".software.applications.docker.networks.*.": {"title": "Network %s"},
    ".software.applications.docker.networks.*.network_id": {"title": "Network ID"},
    ".software.applications.docker.container.": {"title": _("Container")},
    ".software.applications.docker.container.node_name": {"title": _("Node name")},
    ".software.applications.docker.container.ports:": {
        "title": _("Ports"),
        "keyorder": ["port", "protocol", "host_addresses"],
    },
    ".software.applications.docker.container.networks:": {
        "title": _("Networks"),
        "keyorder": ["name", "ip_address", "ip_prefixlen", "gateway", "mac_address", "network_id"],
    },
    ".software.applications.docker.container.networks:*.ip_address": {"title": _("IP address")},
    ".software.applications.docker.container.networks:*.ip_prefixlen": {"title": _("IP Prefix")},
    ".software.applications.docker.container.networks:*.mac_address": {"title": _("MAC address")},
    ".software.applications.docker.container.networks:*.network_id": {"title": _("Network ID")},
    ".software.applications.docker.networks.*.containers:": {
        "keyorder": ["name", "id", "ipv4_address", "ipv6_address", "mac_address"],
    },
    ".software.applications.docker.networks.*.containers:*.id": {"title": _("ID")},
    ".software.applications.docker.networks.*.containers:*.ipv4_address": {
        "title": _("IPv4 address"),
    },
    ".software.applications.docker.networks.*.containers:*.ipv6_address": {
        "title": _("IPv6 address"),
    },
    ".software.applications.docker.networks.*.containers:*.mac_address": {
        "title": _("MAC address"),
    },
    ".software.applications.kubernetes.roles:": {
        "title": _("Roles"),
        "keyorder": ["role", "namespace"],
    },
    ".software.applications.kubernetes.nodes:": {
        "title": _("Nodes"),
        "keyorder": ["name"],
    },
    ".software.applications.kubernetes.pod_container:": {
        "title": _("Containers"),
        "keyorder": [
            "name",
            "ready",
            "restart_count",
            "image",
            "image_pull_policy",
            "image_id",
            "container_id",
        ],
    },
    ".software.applications.kubernetes.roles:*.role" : {"title": _("Name")},
    ".software.applications.kubernetes.roles:*.namespace" : {"title": _("Namespace")},
    ".software.applications.kubernetes.nodes:*.name" : {"title": _("Name")},
    ".software.applications.kubernetes.pod_container:*.name": {"title": _("Name")},
    ".software.applications.kubernetes.pod_container:*.image": {"title": _("Image")},
    ".software.applications.kubernetes.pod_container:*.image_pull_policy": {"title": _("Image pull policy")},
    ".software.applications.kubernetes.pod_container:*.image_id": {"title": _("Image ID")},
    ".software.applications.kubernetes.pod_container:*.ready": {"title": _("Ready"), "paint": "container_ready"},
    ".software.applications.kubernetes.pod_container:*.restart_count": {"title": _("Restart count")},
    ".software.applications.kubernetes.pod_container:*.container_id": {"title": _("Container ID")},
    ".software.applications.kubernetes.pod_info.": {
        "title": _("Pod"),
    },
    ".software.applications.kubernetes.pod_info.node": {"title": _("Node")},
    ".software.applications.kubernetes.pod_info.host_network": {"title": _("Host network")},
    ".software.applications.kubernetes.pod_info.dns_policy": {"title": _("DNS policy")},
    ".software.applications.kubernetes.pod_info.host_ip": {"title": _("Host IP")},
    ".software.applications.kubernetes.pod_info.pod_ip": {"title": _("Pod IP")},
    ".software.applications.kubernetes.pod_info.qos_class": {"title": _("QOS class")},
    ".software.applications.kubernetes.service_info.": {
        "title": _("Service"),
    },
    ".software.applications.kubernetes.service_info.type": {"title": _("Type")},
    ".software.applications.kubernetes.service_info.cluster_ip": {"title": _("Cluster IP")},
    ".software.applications.kubernetes.service_info.load_balancer_ip": {"title": _("Load Balancer IP")},
    ".software.applications.kubernetes.selector.": {
        "title": _("Selectors"),
    },
    ".software.applications.kubernetes.assigned_pods:": {
        "title": _("Pods"),
    },
    ".software.applications.kubernetes.assigned_pods:*.name": {"title": _("Name")},
    ".software.applications.citrix.": {"title": _("Citrix")},
    ".software.applications.citrix.controller.": {"title": _("Controller")},
    ".software.applications.citrix.controller.controller_version": {
        "title": _("Controller Version"),
    },
    ".software.applications.citrix.vm.": {"title": _("Virtual Machine")},
    ".software.applications.citrix.vm.desktop_group_name": {"title": _("Desktop Group Name")},
    ".software.applications.citrix.vm.catalog": {"title": _("Catalog")},
    ".software.applications.citrix.vm.agent_version": {"title": _("Agent Version")},
    ".software.applications.oracle.": {"title": _("Oracle DB")},
    ".software.applications.oracle.instance:": {
        "title": _("Instances"),
        "keyorder": [
            "sid",
            "version",
            "openmode",
            "logmode",
            "logins",
            "db_uptime",
            "db_creation_time",
        ],
        "view": "invorainstance_of_host",
    },
    ".software.applications.oracle.instance:*.sid": {"title": _("SID")},
    ".software.applications.oracle.instance:*.version": {"title": _("Version")},
    ".software.applications.oracle.instance:*.openmode": {"title": _("Open mode")},
    ".software.applications.oracle.instance:*.logmode": {"title": _("Log mode")},
    ".software.applications.oracle.instance:*.logins": {"title": _("Logins")},
    ".software.applications.oracle.instance:*.db_uptime": {"title": _("Uptime"), "paint": "age"},
    ".software.applications.oracle.instance:*.db_creation_time": {
        "title": _("Creation time"), "paint": "date_and_time"
    },
    ".software.applications.oracle.dataguard_stats:": {
        "title": _("Dataguard statistics"),
        "keyorder": ["sid", "db_unique", "role", "switchover"],
        "view": "invoradataguardstats_of_host",
    },
    ".software.applications.oracle.dataguard_stats:*.sid": {"title": _("SID")},
    ".software.applications.oracle.dataguard_stats:*.db_unique": {"title": _("Name")},
    ".software.applications.oracle.dataguard_stats:*.role": {"title": _("Role")},
    ".software.applications.oracle.dataguard_stats:*.switchover": {"title": _("Switchover")},
    ".software.applications.oracle.recovery_area:": {
        "title": _("Recovery area"),
        "keyorder": ["sid", "flashback"],
        "view": "invorarecoveryarea_of_host",
    },
    ".software.applications.oracle.recovery_area:*.sid": {"title": _("SID")},
    ".software.applications.oracle.recovery_area:*.flashback": {"title": _("Flashback")},
    ".software.applications.oracle.sga:": {
        "title": _("SGA Info"),
        "keyorder": [
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
        "view": "invorasga_of_host",
    },
    ".software.applications.oracle.sga:*.sid": {"title": _("SID")},
    ".software.applications.oracle.sga:*.fixed_size": {"title": _("Fixed size"), "paint": "size"},
    ".software.applications.oracle.sga:*.max_size": {"title": _("Maximum size"), "paint": "size"},
    ".software.applications.oracle.sga:*.redo_buffer": {
        "title": _("Redo buffers"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.buf_cache_size": {
        "title": _("Buffer cache size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.in_mem_area_size": {
        "title": _("In-memory area"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.shared_pool_size": {
        "title": _("Shared pool size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.large_pool_size": {
        "title": _("Large pool size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.java_pool_size": {
        "title": _("Java pool size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.streams_pool_size": {
        "title": _("Streams pool size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.shared_io_pool_size": {
        "title": _("Shared pool size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.data_trans_cache_size": {
        "title": _("Data transfer cache size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.granule_size": {
        "title": _("Granule size"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.start_oh_shared_pool": {
        "title": _("Startup overhead in shared pool"), "paint": "size"
    },
    ".software.applications.oracle.sga:*.free_mem_avail": {
        "title": _("Free SGA memory available"), "paint": "size"
    },
    ".software.applications.oracle.tablespaces:": {
        "title": _("Tablespaces"),
        "keyorder": [
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
        "view": "invoratablespace_of_host",
    },
    ".software.applications.oracle.tablespaces:*.sid": {"title": _("SID")},
    ".software.applications.oracle.tablespaces:*.name": {"title": _("Name")},
    ".software.applications.oracle.tablespaces:*.version": {"title": _("Version")},
    ".software.applications.oracle.tablespaces:*.type": {"title": _("Type")},
    ".software.applications.oracle.tablespaces:*.autoextensible": {"title": _("Autoextensible")},
    ".software.applications.oracle.tablespaces:*.current_size": {
        "title": _("Current size"), "paint": "size"
    },
    ".software.applications.oracle.tablespaces:*.max_size": {
        "title": _("Max. size"), "paint": "size"
    },
    ".software.applications.oracle.tablespaces:*.used_size": {
        "title": _("Used size"), "paint": "size"
    },
    ".software.applications.oracle.tablespaces:*.num_increments": {
        "title": _("Number of increments"),
    },
    ".software.applications.oracle.tablespaces:*.increment_size": {
        "title": _("Increment size"), "paint": "size"
    },
    ".software.applications.oracle.tablespaces:*.free_space": {
        "title": _("Free space"), "paint": "size"
    },
    ".software.applications.vmwareesx:*.": {"title": _("Datacenter %d")},
    ".software.applications.vmwareesx:*.clusters:*.": {"title": _("Cluster %d")},
    ".software.applications.mssql.": {"title": _("MSSQL")},
    ".software.applications.mssql.instances:": {
        "title": _("Instances"),
        "keyorder": [
            "name",
            "product",
            "edition",
            "version",
            "clustered",
            "cluster_name",
            "active_node",
            "node_names",
        ],
    },
    ".software.applications.mssql.instances:*.clustered": {
        "title": _("Clustered"), "paint": "mssql_is_clustered"
    },
    ".networking.": {"title": _("Networking"), "icon": "networking"},
    ".networking.total_interfaces": {"title": _("Interfaces"), "paint": "count"},
    ".networking.total_ethernet_ports": {"title": _("Ports"), "paint": "count"},
    ".networking.available_ethernet_ports": {"title": _("Ports available"), "paint": "count"},
    ".networking.addresses:": {
        "title": _("IP Addresses"),
        "keyorder": ["address", "device", "type"],
    },
    ".networking.addresses:*.address": {"title": _("Address")},
    ".networking.addresses:*.device": {"title": _("Device")},
    ".networking.addresses:*.type": {"title": _("Address Type"), "paint": "ip_address_type"},
    ".networking.routes:": {
        "title": _("Routes"), "keyorder": ["target", "device", "type", "gateway"]
    },
    ".networking.routes:*.target": {"title": _("Target"), "paint": "ipv4_network"},
    ".networking.routes:*.device": {"title": _("Device")},
    ".networking.routes:*.type": {"title": _("Type of route"), "paint": "route_type"},
    ".networking.routes:*.gateway": {"title": _("Gateway")},
    ".networking.interfaces:": {
        "title": _("Interfaces"),
        "keyorder": [
            "index",
            "description",
            "alias",
            "oper_status",
            "admin_status",
            "available",
            "speed",
        ],
        "view": "invinterface_of_host",
    },
    ".networking.interfaces:*.index": {
        "title": _("Index"), "paint": "number", "filter": FilterInvtableIDRange
    },
    ".networking.interfaces:*.description": {"title": _("Description")},
    ".networking.interfaces:*.alias": {"title": _("Alias")},
    ".networking.interfaces:*.phys_address": {"title": _("Physical Address (MAC)")},
    ".networking.interfaces:*.oper_status": {
        "title": _("Operational Status"),
        "short": _("Status"),
        "paint": "if_oper_status",
        "filter": FilterInvtableOperStatus,
    },
    ".networking.interfaces:*.admin_status": {
        "title": _("Administrative Status"),
        "short": _("Admin"),
        "paint": "if_admin_status",
        "filter": FilterInvtableAdminStatus,
    },
    ".networking.interfaces:*.available": {
        "title": _("Port Usage"),
        "short": _("Used"),
        "paint": "if_available",
        "filter": FilterInvtableAvailable,
    },
    ".networking.interfaces:*.speed": {"title": _("Speed"), "paint": "nic_speed"},
    ".networking.interfaces:*.port_type": {
        "title": _("Type"),
        "paint": "if_port_type",
        "filter": FilterInvtableInterfaceType,
    },
    ".networking.interfaces:*.last_change": {
        "title": _("Last Change"),
        "paint": "timestamp_as_age_days",
        "filter": FilterInvtableTimestampAsAge,
    },
    ".networking.interfaces:*.vlans": {"title": _("VLANs")},
    ".networking.interfaces:*.vlantype": {"title": _("VLAN type")},
    ".networking.wlan": {"title": _("WLAN")},
    ".networking.wlan.controller": {"title": _("Controller")},
    ".networking.wlan.controller.accesspoints:": {
        "title": _("Access Points"),
        "keyorder": ["name", "group", "ip_addr", "model", "serial", "sys_location"],
    },
    ".networking.wlan.controller.accesspoints:*.name": {"title": _("Name")},
    ".networking.wlan.controller.accesspoints:*.group": {"title": _("Group")},
    ".networking.wlan.controller.accesspoints:*.ip_addr": {"title": _("IP Address")},
    ".networking.wlan.controller.accesspoints:*.model": {"title": _("Model")},
    ".networking.wlan.controller.accesspoints:*.serial": {"title": _("Serial Number")},
    ".networking.wlan.controller.accesspoints:*.sys_location": {"title": _("System Location")},

    ".networking.tunnels:": {
        "title" : _("Networking Tunnels"),
    },
    ".networking.tunnels:*.index": { "title" : _("Index") },
    ".networking.tunnels:*.link_priority": { "title" : _("Link Priority") },
    ".networking.tunnels:*.peerip": { "title" : _("Peer IP Address") },
    ".networking.tunnels:*.peername": { "title" : _("Peer Name")  },
    ".networking.tunnels:*.sourceip": { "title" : _("Source IP Address") },
    ".networking.tunnels:*.tunnel_interface": { "title" : _("Tunnel Interface") },

}
)

# yapf: enable
