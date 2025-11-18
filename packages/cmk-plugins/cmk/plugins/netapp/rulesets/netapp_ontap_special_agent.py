#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

DEFAULT_RESOURCES = [
    "volumes",
    "volumes_counters",
    "disk",
    "luns",
    "aggr",
    "vs_status",
    "ports",
    "interfaces",  # counters can eventually be collected separately
    "node",
    "fan",
    "temp",
    "alerts",
    "vs_traffic",
    "psu",
    "environment",
    "qtree_quota",
    "snapvault",
    "fc_interfaces",
]


def _migrate_netapp_config(p: object) -> dict[str, object]:
    """Migrate old NetApp configuration format to new fetched_resources approach"""
    if not isinstance(p, dict):
        raise TypeError(p)

    # Default monitored objects (all components with performance data)
    default_fetched_resources = DEFAULT_RESOURCES

    migrated = dict(p)

    if "skip_elements" in migrated:
        skip_elements = migrated.pop("skip_elements")  # Remove old parameter

        fetched_resources = default_fetched_resources.copy()

        if isinstance(skip_elements, list) and "ctr_volumes" in skip_elements:
            if "volumes_counters" in fetched_resources:
                fetched_resources.remove("volumes_counters")

        if "fetched_resources" not in migrated:
            migrated["fetched_resources"] = fetched_resources

    if "fetched_resources" not in migrated:
        migrated["fetched_resources"] = default_fetched_resources

    return migrated


def _formspec_netapp_ontap() -> Dictionary:
    return Dictionary(
        title=Title("NetApp via Ontap REST API"),
        help_text=Help(
            "This rule set selects the NetApp special agent instead of the normal Checkmk Agent "
            "and allows monitoring via the NetApp Ontap REST API."
        ),
        migrate=_migrate_netapp_config,
        elements={
            "username": DictElement(
                parameter_form=String(
                    title=Title("Username"),
                    help_text=Help(
                        "The username that should be used for accessing the NetApp API."
                    ),
                    custom_validate=[
                        validators.LengthInRange(min_value=1),
                    ],
                ),
                required=True,
            ),
            "password": DictElement(
                parameter_form=Password(
                    help_text=Help("The password of the user."),
                    title=Title("Password of the user"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
                required=True,
            ),
            "no_cert_check": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Skip TLS certificate verification"),
                    prefill=DefaultValue(False),
                ),
                required=True,
            ),
            "fetched_resources": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    elements=[
                        MultipleChoiceElement(name="volumes", title=Title("Volumes")),
                        MultipleChoiceElement(
                            name="volumes_counters",
                            title=Title("Volume Performance Counters (requires Volumes)"),
                        ),
                        MultipleChoiceElement(name="disk", title=Title("Disks")),
                        MultipleChoiceElement(name="luns", title=Title("LUNs")),
                        MultipleChoiceElement(name="aggr", title=Title("Aggregations")),
                        MultipleChoiceElement(name="qtree_quota", title=Title("Qtree Quotas")),
                        MultipleChoiceElement(name="snapvault", title=Title("SnapVaults")),
                        MultipleChoiceElement(name="interfaces", title=Title("Network Interfaces")),
                        MultipleChoiceElement(name="ports", title=Title("Network Ports")),
                        MultipleChoiceElement(name="fc_interfaces", title=Title("Interface FCP")),
                        MultipleChoiceElement(
                            name="node", title=Title("Nodes")
                        ),  # NVRAM Battery, Info
                        MultipleChoiceElement(name="vs_status", title=Title("SVM Status")),
                        MultipleChoiceElement(name="vs_traffic", title=Title("Traffic SVM")),
                        MultipleChoiceElement(name="fan", title=Title("Fans")),
                        MultipleChoiceElement(name="temp", title=Title("Temperature Sensors")),
                        MultipleChoiceElement(name="psu", title=Title("Power Supplies")),
                        MultipleChoiceElement(
                            name="environment", title=Title("Environment Sensors")
                        ),
                        MultipleChoiceElement(name="alerts", title=Title("Alerts")),
                    ],
                    prefill=DefaultValue(DEFAULT_RESOURCES),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    title=Title("Fetch information about..."),
                    help_text=Help(
                        "Select the NetApp resources you would like to fetch from the API. "
                        "Note that some sections depend on others: 'Volume Performance Counters' "
                        "requires 'Volumes' data. Performance counter sections may "
                        "consume more resources and take longer to collect on large systems."
                    ),
                ),
            ),
        },
    )


rule_spec_netapp_ontap = SpecialAgent(
    name="netapp_ontap",
    title=Title("NetApp via Ontap REST API"),
    topic=Topic.APPLICATIONS,
    parameter_form=_formspec_netapp_ontap,
)
