#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_alpha import (
    BoolField,
    DecimalNotation,
    IECNotation,
    Node,
    NumberField,
    SINotation,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_BITS_PER_SECOND = Unit(IECNotation("bits/s"))
UNIT_BYTES = Unit(IECNotation("B"))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))
UNIT_HZ = Unit(SINotation("Hz"))
UNIT_VOLTAGE = Unit(DecimalNotation("V"))

node_hardware = Node(
    name="hardware",
    path=["hardware"],
    title=Title("Hardware"),
)

node_hardware_chassis = Node(
    name="hardware_chassis",
    path=["hardware", "chassis"],
    title=Title("Chassis"),
)

node_hardware_components = Node(
    name="hardware_components",
    path=["hardware", "components"],
    title=Title("Physical components"),
)

node_hardware_components_backplanes = Node(
    name="hardware_components_backplanes",
    path=["hardware", "components", "backplanes"],
    title=Title("Backplanes"),
    table=Table(
        view=View(name="invbackplane", title=Title("Backplanes")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_chassis = Node(
    name="hardware_components_chassis",
    path=["hardware", "components", "chassis"],
    title=Title("Chassis"),
    table=Table(
        view=View(name="invchassis", title=Title("Chassis")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_containers = Node(
    name="hardware_components_containers",
    path=["hardware", "components", "containers"],
    title=Title("HW containers"),
    table=Table(
        view=View(name="invcontainer", title=Title("HW containers")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_fans = Node(
    name="hardware_components_fans",
    path=["hardware", "components", "fans"],
    title=Title("Fans"),
    table=Table(
        view=View(name="invfan", title=Title("Fans")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_modules = Node(
    name="hardware_components_modules",
    path=["hardware", "components", "modules"],
    title=Title("Modules"),
    table=Table(
        view=View(name="invmodule", title=Title("Modules")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "model": TextField(Title("Model name")),
            "manufacturer": TextField(Title("Manufacturer")),
            "bootloader": TextField(Title("Bootloader")),
            "firmware": TextField(Title("Firmware")),
            "type": TextField(Title("Type")),
            "location": TextField(Title("Location")),
            "ha_status": TextField(Title("HA status")),
            "software_version": TextField(Title("Software version")),
            "license_key_list": TextField(Title("License key list")),
        },
    ),
)

node_hardware_components_others = Node(
    name="hardware_components_others",
    path=["hardware", "components", "others"],
    title=Title("Other entities"),
    table=Table(
        view=View(name="invother", title=Title("Other entities")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_psus = Node(
    name="hardware_components_psus",
    path=["hardware", "components", "psus"],
    title=Title("Power supplies"),
    table=Table(
        view=View(name="invpsu", title=Title("Power supplies")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_sensors = Node(
    name="hardware_components_sensors",
    path=["hardware", "components", "sensors"],
    title=Title("Sensors"),
    table=Table(
        view=View(name="invsensor", title=Title("Sensors")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_stacks = Node(
    name="hardware_components_stacks",
    path=["hardware", "components", "stacks"],
    title=Title("Stacks"),
    table=Table(
        view=View(name="invstack", title=Title("Stacks")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_components_unknowns = Node(
    name="hardware_components_unknowns",
    path=["hardware", "components", "unknowns"],
    title=Title("Unknown entities"),
    table=Table(
        view=View(name="invunknown", title=Title("Unknown entities")),
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "software": TextField(Title("Software")),
            "serial": TextField(Title("Serial number")),
            "manufacturer": TextField(Title("Manufacturer")),
            "model": TextField(Title("Model name")),
            "location": TextField(Title("Location")),
        },
    ),
)

node_hardware_cpu = Node(
    name="hardware_cpu",
    path=["hardware", "cpu"],
    title=Title("Processor"),
    attributes={
        "arch": TextField(Title("CPU architecture")),
        "max_speed": NumberField(Title("Maximum speed"), render=UNIT_HZ),
        "model": TextField(Title("CPU model")),
        "type": TextField(Title("CPU type")),
        "threads": NumberField(Title("#Hyperthreads"), render=UNIT_COUNT),
        "smt_threads": NumberField(Title("SMT threads"), render=UNIT_COUNT),
        "cpu_max_capa": TextField(Title("Processor max. capacity")),
        "cpus": NumberField(Title("#Physical CPUs"), render=UNIT_COUNT),
        "logical_cpus": NumberField(Title("#Logical CPUs"), render=UNIT_COUNT),
        "cores": NumberField(Title("#Cores"), render=UNIT_COUNT),
        "cores_per_cpu": NumberField(Title("Cores per CPU"), render=UNIT_COUNT),
        "threads_per_cpu": NumberField(Title("Hyperthreads per CPU"), render=UNIT_COUNT),
        "cache_size": NumberField(Title("Cache size"), render=UNIT_BYTES),
        "bus_speed": NumberField(Title("Bus speed"), render=UNIT_HZ),
        "voltage": NumberField(Title("Voltage"), render=UNIT_VOLTAGE),
        "sharing_mode": TextField(Title("Shared processor mode")),
        "implementation_mode": TextField(Title("Processor implementation mode")),
        "entitlement": TextField(Title("Processor entitled capacity")),
    },
)

node_hardware_cpu_nodes = Node(
    name="hardware_cpu_nodes",
    path=["hardware", "cpu", "nodes"],
    title=Title("Node processor"),
    table=Table(
        columns={
            "node_name": TextField(Title("Node name")),
            "cores": NumberField(Title("#Cores"), render=UNIT_COUNT),
            "model": TextField(Title("CPU model")),
        },
    ),
)

node_hardware_firmware = Node(
    name="hardware_firmware",
    path=["hardware", "firmware"],
    title=Title("Firmware"),
)

node_hardware_firmware_redfish = Node(
    name="hardware_firmware_redfish",
    path=["hardware", "firmware", "redfish"],
    title=Title("Redfish"),
    table=Table(
        view=View(name="invfirmwareredfish", title=Title("Redfish")),
        columns={
            "component": TextField(Title("Component")),
            "version": TextField(Title("Version")),
            "location": TextField(Title("Location")),
            "description": TextField(Title("Description")),
            "updateable": BoolField(Title("Update possible")),
        },
    ),
)

node_hardware_memory = Node(
    name="hardware_memory",
    path=["hardware", "memory"],
    title=Title("Memory (RAM)"),
    attributes={
        "total_ram_usable": NumberField(Title("Total usable RAM"), render=UNIT_BYTES),
        "total_swap": NumberField(Title("Total swap space"), render=UNIT_BYTES),
        "total_vmalloc": NumberField(Title("Virtual addresses for mapping"), render=UNIT_BYTES),
    },
)

node_hardware_memory_arrays = Node(
    name="hardware_memory_arrays",
    path=["hardware", "memory", "arrays"],
    title=Title("Arrays (Controllers)"),
    table=Table(
        columns={
            "maximum_capacity": NumberField(Title("Maximum capacity"), render=UNIT_BYTES),
        },
    ),
)

node_hardware_memory_arrays_devices = Node(
    name="hardware_memory_arrays_devices",
    path=["hardware", "memory", "arrays", "devices"],
    title=Title("Devices"),
    table=Table(
        columns={
            "index": TextField(Title("Index")),
            "locator": TextField(Title("Locator")),
            "bank_locator": TextField(Title("Bank locator")),
            "type": TextField(Title("Type")),
            "form_factor": TextField(Title("Form factor")),
            "speed": NumberField(Title("Speed"), render=UNIT_HZ),
            "data_width": TextField(Title("Data width")),
            "total_width": TextField(Title("Total width")),
            "manufacturer": TextField(Title("Manufacturer")),
            "serial": TextField(Title("Serial")),
            "size": NumberField(Title("Size"), render=UNIT_BYTES),
        },
    ),
)

node_hardware_nwadapter = Node(
    name="hardware_nwadapter",
    path=["hardware", "nwadapter"],
    title=Title("Network adapters"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "type": TextField(Title("Type")),
            "macaddress": TextField(Title("Physical address (MAC)")),
            "speed": NumberField(Title("Speed"), render=UNIT_BITS_PER_SECOND),
            "gateway": TextField(Title("Gateway")),
            "ipv4_address": TextField(Title("IPv4 address")),
            "ipv6_address": TextField(Title("IPv6 address")),
            "ipv4_subnet": TextField(Title("IPv4 subnet")),
            "ipv6_subnet": TextField(Title("IPv6 subnet")),
        },
    ),
)

node_hardware_storage = Node(
    name="hardware_storage",
    path=["hardware", "storage"],
    title=Title("Storage"),
)

node_hardware_system_nodes = Node(
    name="hardware_system_nodes",
    path=["hardware", "system", "nodes"],
    title=Title("Node system"),
    table=Table(
        columns={
            "node_name": TextField(Title("Node name")),
            "id": TextField(Title("ID")),
            "model": TextField(Title("Model name")),
            "product": TextField(Title("Product")),
            "serial": TextField(Title("Serial number")),
        },
    ),
)
