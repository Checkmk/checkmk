#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory_ui.v1_unstable import (
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
)

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

node_hardware_memory_arrays = Node(
    name="hardware_memory_arrays",
    path=["hardware", "memory", "arrays"],
    title=Title("Arrays (controllers)"),
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

node_hardware_system = Node(
    name="hardware_system",
    path=["hardware", "system"],
    title=Title("System"),
    attributes={
        "manufacturer": TextField(Title("Manufacturer")),
        "product": TextField(Title("Product")),
        "serial": TextField(Title("Serial number")),
        "model": TextField(Title("Model name")),
        "node_name": TextField(Title("Node name")),
        "partition_name": TextField(Title("Partition name")),
        "expresscode": TextField(Title("Express servicecode")),
        "pki_appliance_version": TextField(Title("Version of PKI appliance")),
        "device_number": TextField(Title("Device number")),
        "description": TextField(Title("Description")),
        "mac_address": TextField(Title("MAC address")),
        "type": TextField(Title("Type")),
        "software_version": TextField(Title("Software version")),
        "license_key_list": TextField(Title("License key list")),
        "model_name": TextField(Title("Model name - LEGACY, don't use")),
        "serial_number": TextField(Title("Serial number - LEGACY, don't use")),
    },
)
