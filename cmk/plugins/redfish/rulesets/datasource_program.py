#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""rule for assinging the special agent to host objects"""
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

from cmk.rulesets.v1 import Title, Help, Label
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    migrate_to_password,
    validators,
)
from cmk.rulesets.v1.rule_specs import Topic, SpecialAgent


def _valuespec_special_agents_redfish() -> Dictionary:
    return Dictionary(
        title=Title("Redfish Compatible Management Controller"),
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
                required=True,
            ),
            "sections": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Enabled Sections... (only use in case of problems)"),
                    help_text=Help(
                        "If there are problems please use disabled sections."
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="Memory", title=Title("Memory Modules")
                        ),
                        MultipleChoiceElement(
                            name="Power", title=Title("Powers Supply")
                        ),
                        MultipleChoiceElement(name="Processors", title=Title("CPUs")),
                        MultipleChoiceElement(
                            name="Thermal", title=Title("Fan and Temperatures")
                        ),
                        MultipleChoiceElement(
                            name="FirmwareInventory",
                            title=Title("Firmware Versions"),
                        ),
                        MultipleChoiceElement(
                            name="NetworkAdapters", title=Title("Network Cards")
                        ),
                        MultipleChoiceElement(
                            name="NetworkInterfaces",
                            title=Title("Network Interfaces 1"),
                        ),
                        MultipleChoiceElement(
                            name="EthernetInterfaces",
                            title=Title("Network Interfaces 2"),
                        ),
                        MultipleChoiceElement(name="Storage", title=Title("Storage")),
                        MultipleChoiceElement(
                            name="ArrayControllers",
                            title=Title("Array Controllers"),
                        ),
                        MultipleChoiceElement(
                            name="SmartStorage",
                            title=Title("HPE - Storagesubsystem"),
                        ),
                        MultipleChoiceElement(
                            name="HostBusAdapters",
                            title=Title("Hostbustadapters"),
                        ),
                        MultipleChoiceElement(
                            name="PhysicalDrives", title=Title("iLO5 - Physical Drives")
                        ),
                        MultipleChoiceElement(
                            name="LogicalDrives", title=Title("iLO5 - Logical Drives")
                        ),
                        MultipleChoiceElement(name="Drives", title=Title("Drives")),
                        MultipleChoiceElement(name="Volumes", title=Title("Volumes")),
                        MultipleChoiceElement(
                            name="SimpleStorage",
                            title=Title("Simple Storage Collection (tbd)"),
                        ),
                    ],
                    prefill=DefaultValue(
                        [
                            "Memory",
                            "Power",
                            "Processors",
                            "Thermal",
                            "FirmwareInventory",
                            "NetworkAdapters",
                            "NetworkInterfaces",
                            "EthernetInterfaces",
                            "Storage",
                            "ArrayControllers",
                            "SmartStorage",
                            "HostBusAdapters",
                            "PhysicalDrives",
                            "LogicalDrives",
                            "Drives",
                            "Volumes",
                            "SimpleStorage",
                        ]
                    ),
                    show_toggle_all=True,
                ),
            ),
            "disabled_sections": DictElement(
                parameter_form=MultipleChoice(
                    title=Title("Disabled Sections..."),
                    help_text=Help("Please only define sections or disabled sections."),
                    elements=[
                        MultipleChoiceElement(
                            name="Memory", title=Title("Memory Modules")
                        ),
                        MultipleChoiceElement(
                            name="Power", title=Title("Powers Supply")
                        ),
                        MultipleChoiceElement(name="Processors", title=Title("CPUs")),
                        MultipleChoiceElement(
                            name="Thermal", title=Title("Fan and Temperatures")
                        ),
                        MultipleChoiceElement(
                            name="FirmwareInventory",
                            title=Title("Firmware Versions"),
                        ),
                        MultipleChoiceElement(
                            name="NetworkAdapters", title=Title("Network Cards")
                        ),
                        MultipleChoiceElement(
                            name="NetworkInterfaces",
                            title=Title("Network Interfaces 1"),
                        ),
                        MultipleChoiceElement(
                            name="EthernetInterfaces",
                            title=Title("Network Interfaces 2"),
                        ),
                        MultipleChoiceElement(name="Storage", title=Title("Storage")),
                        MultipleChoiceElement(
                            name="ArrayControllers",
                            title=Title("Array Controllers"),
                        ),
                        MultipleChoiceElement(
                            name="SmartStorage",
                            title=Title("HPE - Storagesubsystem"),
                        ),
                        MultipleChoiceElement(
                            name="HostBusAdapters",
                            title=Title("Hostbustadapters"),
                        ),
                        MultipleChoiceElement(
                            name="PhysicalDrives", title=Title("iLO5 - Physical Drives")
                        ),
                        MultipleChoiceElement(
                            name="LogicalDrives", title=Title("iLO5 - Logical Drives")
                        ),
                        MultipleChoiceElement(name="Drives", title=Title("Drives")),
                        MultipleChoiceElement(name="Volumes", title=Title("Volumes")),
                        MultipleChoiceElement(
                            name="SimpleStorage",
                            title=Title("Simple Storage Collection (tbd)"),
                        ),
                    ],
                    prefill=DefaultValue([]),
                    show_toggle_all=True,
                ),
            ),
            "cached_sections": DictElement(
                parameter_form=Dictionary(
                    title=Title("Cached times for single sections"),
                    elements={
                        "cache_time_Memory": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Memory"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_Power": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Power"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_Processors": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Processors"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_Thermal": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Thermal"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_FirmwareInventory": DictElement(
                            parameter_form=Integer(
                                title=Title("Section FirmwareInventory"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_NetworkAdapters": DictElement(
                            parameter_form=Integer(
                                title=Title("Section NetworkAdapters"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_NetworkInterfaces": DictElement(
                            parameter_form=Integer(
                                title=Title("Section NetworkInterfaces"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_EthernetInterfaces": DictElement(
                            parameter_form=Integer(
                                title=Title("Section EthernetInterfaces"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_Storage": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Storage"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_ArrayControllers": DictElement(
                            parameter_form=Integer(
                                title=Title("Section ArrayControllers"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_SmartStorage": DictElement(
                            parameter_form=Integer(
                                title=Title("Section SmartStorage"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_HostBusAdapters": DictElement(
                            parameter_form=Integer(
                                title=Title("Section HostBusAdapters"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_PhysicalDrives": DictElement(
                            parameter_form=Integer(
                                title=Title("Section PhysicalDrives"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_LogicalDrives": DictElement(
                            parameter_form=Integer(
                                title=Title("Section LogicalDrives"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_Drives": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Drives"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_Volumes": DictElement(
                            parameter_form=Integer(
                                title=Title("Section Volumes"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                        "cache_time_SimpleStorage": DictElement(
                            parameter_form=Integer(
                                title=Title("Section SimpleStorage"),
                                prefill=DefaultValue(60),
                                custom_validate=(
                                    validators.NumberInRange(min_value=1),
                                ),
                                unit_symbol="s",
                            ),
                        ),
                    },
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Advanced - TCP Port number"),
                    help_text=Help(
                        "Port number for connection to the Rest API. Usually 8443 (TLS)"
                    ),
                    prefill=DefaultValue(443),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=65535),
                    ),
                ),
            ),
            "proto": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Advanced - Protocol"),
                    prefill=DefaultValue("https"),
                    help_text=Help(
                        "Protocol for the connection to the Rest API."
                        "https is highly recommended!!!"
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="http",
                            title=Title("http"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="https",
                            title=Title("https"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                ),
            ),
            "retries": DictElement(
                parameter_form=Integer(
                    title=Title("Advanced - Number of retries"),
                    help_text=Help(
                        "Number of retry attempts made by the special agent."
                    ),
                    prefill=DefaultValue(10),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=20),
                    ),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Advanced - Timeout for connection"),
                    help_text=Help(
                        "Number of seconds for a single connection attempt before timeout occurs."
                    ),
                    prefill=DefaultValue(10),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=20),
                    ),
                ),
            ),
            "debug": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Debug mode"),
                    label=Label("enabled"),
                ),
            ),
        },
    )


def _valuespec_special_agents_redfish_power() -> Dictionary:
    return Dictionary(
        title=Title("Redfish Compatible Power Equipment (PDU)"),
        elements={
            "user": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    title=Title("Password"),
                ),
                required=True,
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Advanced - TCP Port number"),
                    help_text=Help(
                        "Port number for connection to the Rest API. Usually 8443 (TLS)"
                    ),
                    prefill=DefaultValue(443),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=65535),
                    ),
                ),
            ),
            "proto": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Advanced - Protocol"),
                    prefill=DefaultValue("https"),
                    help_text=Help(
                        "Protocol for the connection to the Rest API."
                        "https is highly recommended!!!"
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="http",
                            title=Title("http"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="https",
                            title=Title("https"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                ),
            ),
            "retries": DictElement(
                parameter_form=Integer(
                    title=Title("Advanced - Number of retries"),
                    help_text=Help(
                        "Number of retry attempts made by the special agent."
                    ),
                    prefill=DefaultValue(10),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=20),
                    ),
                ),
            ),
            "timeout": DictElement(
                parameter_form=Integer(
                    title=Title("Advanced - Timeout for connection"),
                    help_text=Help(
                        "Number of seconds for a single connection attempt before timeout occurs."
                    ),
                    prefill=DefaultValue(10),
                    custom_validate=(
                        validators.NumberInRange(min_value=1, max_value=20),
                    ),
                ),
            ),
        },
    )


rule_spec_redfish_datasource_programs = SpecialAgent(
    name="redfish",
    title=Title("Redfish Compatible Management Controller"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_valuespec_special_agents_redfish,
    help_text=(
        "This rule selects the Agent Redfish instead of the normal Check_MK Agent "
        "which collects the data through the Redfish REST API"
    ),
)

rule_spec_redfish_power_datasource_programs = SpecialAgent(
    name="redfish_power",
    title=Title("Redfish Compatible Power Equipment (PDU)"),
    topic=Topic.SERVER_HARDWARE,
    parameter_form=_valuespec_special_agents_redfish_power,
    help_text=(
        "This rule selects the Agent Redfish instead of the normal Check_MK Agent "
        "which collects the data through the Redfish REST API"
    ),
)
