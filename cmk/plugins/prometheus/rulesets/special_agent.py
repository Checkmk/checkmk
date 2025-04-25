#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.hostaddress import HostAddress

from cmk.plugins.lib.prometheus_form_elements import api_request_authentication, connection
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    Float,
    LevelDirection,
    List,
    MatchingScope,
    Metric,
    MultipleChoice,
    MultipleChoiceElement,
    RegularExpression,
    SimpleLevels,
    SimpleLevelsConfigModel,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _parameter_form() -> Dictionary:
    namespace_element = SingleChoice(
        title=Title("Prepend namespace prefix for hosts"),
        help_text=Help(
            "If a cluster uses multiple namespaces you need to activate this option. "
            "Hosts for namespaced Kubernetes objects will then be prefixed with the "
            "names of their namespaces. This makes Kubernetes resources in different "
            "namespaces that have the same name distinguishable, but results in "
            "longer host names."
        ),
        elements=[
            SingleChoiceElement("use_namespace", Title("Use a namespace prefix")),
            SingleChoiceElement("omit_namespace", Title("Don't use a namespace prefix")),
        ],
        prefill=DefaultValue("use_namespace"),
    )

    return Dictionary(
        migrate=_migrate,
        elements={
            "connection": DictElement(
                required=True,
                parameter_form=connection(),
            ),
            "verify_cert": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Verify SSL certificate (not verifying is insecure)"),
                    prefill=DefaultValue(False),
                ),
            ),
            "auth_basic": DictElement(
                parameter_form=api_request_authentication(),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol"),
                    elements=[
                        SingleChoiceElement("http", Title("HTTP")),
                        SingleChoiceElement("https", Title("HTTPS")),
                    ],
                    prefill=DefaultValue("http"),
                ),
            ),
            "exporter": DictElement(
                required=True,
                parameter_form=List(
                    title=Title(
                        "Prometheus Scrape Targets (include Prometheus Exporters) to fetch information from"
                    ),
                    help_text=Help(
                        "You can specify which Scrape Targets including Exporters "
                        "are connected to your Prometheus instance. The Prometheus "
                        "Special Agent will automatically generate services for the "
                        "selected monitoring information. You can create your own "
                        "defined services with the custom PromQL query option below "
                        "if one of the Scrape Target types are not listed here."
                    ),
                    add_element_label=Label("Add new Scrape Target"),
                    element_template=CascadingSingleChoice(
                        prefill=DefaultValue("node_exporter"),
                        elements=[
                            CascadingSingleChoiceElement(
                                name="node_exporter",
                                title=Title("Node Exporter"),
                                parameter_form=Dictionary(
                                    title=Title("Node Exporter metrics"),
                                    elements={
                                        "host_mapping": DictElement(
                                            parameter_form=String(
                                                title=Title("Explicitly map Node Exporter host"),
                                                help_text=Help(
                                                    "Per default, Checkmk tries to map the underlying Checkmk host "
                                                    "to the Node Exporter host which contains either the Checkmk "
                                                    'host name, host address or "localhost" in its endpoint address. '
                                                    "The created services of the mapped Node Exporter will "
                                                    "be assigned to the Checkmk host. A piggyback host for each "
                                                    "Node Exporter host will be created if none of the options are "
                                                    "valid. "
                                                    "This option allows you to explicitly map one of your Node "
                                                    "Exporter hosts to the underlying Checkmk host. This can be "
                                                    "used if the default options do not apply to your setup."
                                                ),
                                                custom_validate=(_validate_hostname,),
                                            ),
                                        ),
                                        "entities": DictElement(
                                            required=True,
                                            parameter_form=MultipleChoice(
                                                title=Title("Retrieve information about..."),
                                                help_text=Help(
                                                    "For your respective kernel select the hardware or OS entity "
                                                    "you would like to retrieve information about."
                                                ),
                                                custom_validate=(
                                                    validators.LengthInRange(min_value=1),
                                                ),
                                                elements=[
                                                    MultipleChoiceElement(
                                                        name="df",
                                                        title=Title("Filesystems"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="diskstat",
                                                        title=Title("Disk IO"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="mem",
                                                        title=Title("Memory"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="kernel",
                                                        title=Title(
                                                            "CPU utilization & Kernel performance"
                                                        ),
                                                    ),
                                                ],
                                                prefill=DefaultValue(
                                                    [
                                                        "df",
                                                        "diskstat",
                                                        "mem",
                                                        "kernel",
                                                    ]
                                                ),
                                            ),
                                        ),
                                    },
                                ),
                            ),
                            CascadingSingleChoiceElement(
                                name="cadvisor",
                                title=Title("cAdvisor"),
                                parameter_form=Dictionary(
                                    title=Title("CAdvisor"),
                                    custom_validate=(
                                        validators.LengthInRange(
                                            min_value=1,
                                            error_msg=Message("Please select at least one element"),
                                        ),
                                    ),
                                    elements={
                                        "entity_level": DictElement(
                                            required=True,
                                            parameter_form=CascadingSingleChoice(
                                                title=Title(
                                                    "Entity level used to create Checkmk piggyback hosts"
                                                ),
                                                help_text=Help(
                                                    "The retrieved information from the cAdvisor will be aggregated according"
                                                    " to the selected entity level. Resulting services will be allocated to the created"
                                                    " Checkmk piggyback hosts."
                                                ),
                                                prefill=DefaultValue("container"),
                                                elements=[
                                                    CascadingSingleChoiceElement(
                                                        name="container",
                                                        title=Title(
                                                            "Container - Display the information on container level"
                                                        ),
                                                        parameter_form=Dictionary(
                                                            elements={
                                                                "container_id": DictElement(
                                                                    required=True,
                                                                    parameter_form=SingleChoice(
                                                                        title=Title(
                                                                            "Host name used for containers"
                                                                        ),
                                                                        help_text=Help(
                                                                            "For Containers - Choose which identifier is used for the monitored containers."
                                                                            " This will affect the name used for the piggyback host"
                                                                            " corresponding to the container, as well as items for"
                                                                            " services created on the node for each container."
                                                                        ),
                                                                        prefill=DefaultValue(
                                                                            "short"
                                                                        ),
                                                                        elements=[
                                                                            SingleChoiceElement(
                                                                                "short",
                                                                                Title(
                                                                                    "Short - Use the first 12 characters of the docker container ID"
                                                                                ),
                                                                            ),
                                                                            SingleChoiceElement(
                                                                                "long",
                                                                                Title(
                                                                                    "Long - Use the full docker container ID"
                                                                                ),
                                                                            ),
                                                                            SingleChoiceElement(
                                                                                "name",
                                                                                Title(
                                                                                    "Name - Use the name of the container"
                                                                                ),
                                                                            ),
                                                                        ],
                                                                    ),
                                                                )
                                                            },
                                                        ),
                                                    ),
                                                    CascadingSingleChoiceElement(
                                                        name="pod",
                                                        title=Title(
                                                            "Pod - Display the information for pod level"
                                                        ),
                                                        parameter_form=Dictionary(
                                                            elements={
                                                                "prepend_namespaces": DictElement(
                                                                    required=True,
                                                                    parameter_form=namespace_element,
                                                                )
                                                            }
                                                        ),
                                                    ),
                                                    CascadingSingleChoiceElement(
                                                        name="both",
                                                        title=Title(
                                                            "Both - Display the information for both pod and container levels"
                                                        ),
                                                        parameter_form=Dictionary(
                                                            elements={
                                                                "container_id": DictElement(
                                                                    required=True,
                                                                    parameter_form=SingleChoice(
                                                                        title=Title(
                                                                            "Host name used for containers"
                                                                        ),
                                                                        help_text=Help(
                                                                            "For Containers - Choose which identifier is used for the monitored containers."
                                                                            " This will affect the name used for the piggyback host"
                                                                            " corresponding to the container, as well as items for"
                                                                            " services created on the node for each container."
                                                                        ),
                                                                        prefill=DefaultValue(
                                                                            "short"
                                                                        ),
                                                                        elements=[
                                                                            SingleChoiceElement(
                                                                                "short",
                                                                                Title(
                                                                                    "Short - Use the first 12 characters of the docker container ID"
                                                                                ),
                                                                            ),
                                                                            SingleChoiceElement(
                                                                                "long",
                                                                                Title(
                                                                                    "Long - Use the full docker container ID"
                                                                                ),
                                                                            ),
                                                                            SingleChoiceElement(
                                                                                "name",
                                                                                Title(
                                                                                    "Name - Use the name of the container"
                                                                                ),
                                                                            ),
                                                                        ],
                                                                    ),
                                                                ),
                                                                "prepend_namespaces": DictElement(
                                                                    required=True,
                                                                    parameter_form=namespace_element,
                                                                ),
                                                            },
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        "namespace_include_patterns": DictElement(
                                            parameter_form=List(
                                                title=Title("Monitor namespaces matching"),
                                                add_element_label=Label("Add new pattern"),
                                                help_text=Help(
                                                    "If your cluster has multiple namespaces, you can specify "
                                                    "a list of regex patterns. Only matching namespaces will "
                                                    "be monitored. Note that this concerns everything which "
                                                    "is part of the matching namespaces such as pods for "
                                                    "example."
                                                ),
                                                custom_validate=(
                                                    validators.LengthInRange(min_value=1),
                                                ),
                                                element_template=RegularExpression(
                                                    title=Title("Pattern"),
                                                    predefined_help_text=MatchingScope.FULL,
                                                    custom_validate=(
                                                        validators.LengthInRange(min_value=1),
                                                    ),
                                                ),
                                            ),
                                        ),
                                        "entities": DictElement(
                                            required=True,
                                            parameter_form=MultipleChoice(
                                                title=Title("Retrieve information about..."),
                                                help_text=Help(
                                                    "For your respective kernel select the hardware or OS entity "
                                                    "you would like to retrieve information about."
                                                ),
                                                custom_validate=(
                                                    validators.LengthInRange(min_value=1),
                                                ),
                                                migrate=_migrate_entities,
                                                elements=[
                                                    MultipleChoiceElement(
                                                        name="diskio",
                                                        title=Title("Disk IO"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="cpu",
                                                        title=Title("CPU utilization"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="df",
                                                        title=Title("Filesystem"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="interfaces",
                                                        title=Title("Network"),
                                                    ),
                                                    MultipleChoiceElement(
                                                        name="memory",
                                                        title=Title("Memory"),
                                                    ),
                                                ],
                                                prefill=DefaultValue(
                                                    [
                                                        "diskio",
                                                        "cpu",
                                                        "df",
                                                        "interfaces",
                                                        "memory",
                                                    ]
                                                ),
                                            ),
                                        ),
                                    },
                                ),
                            ),
                        ],
                    ),
                ),
            ),
            "promql_checks": DictElement(
                required=True,
                parameter_form=List(
                    title=Title("Service creation using PromQL queries"),
                    add_element_label=Label("Add new service"),
                    element_template=Dictionary(
                        elements={
                            "service_description": DictElement(
                                required=True,
                                parameter_form=String(
                                    title=Title("Service name"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                            ),
                            "host_name": DictElement(
                                parameter_form=String(
                                    title=Title("Assign service to following host"),
                                    custom_validate=(
                                        validators.LengthInRange(min_value=1),
                                        _validate_hostname,
                                    ),
                                    help_text=Help(
                                        "Specify the host to which the resulting "
                                        "service will be assigned to. The host "
                                        "should be configured to allow Piggyback "
                                        "data."
                                    ),
                                ),
                            ),
                            "metric_components": DictElement(
                                required=True,
                                parameter_form=List(
                                    title=Title("PromQL queries for Service"),
                                    add_element_label=Label("Add new PromQL query"),
                                    custom_validate=(
                                        validators.LengthInRange(min_value=1),
                                        _validate_service_metrics,
                                    ),
                                    element_template=Dictionary(
                                        title=Title("PromQL query"),
                                        elements={
                                            "metric_label": DictElement(
                                                required=True,
                                                parameter_form=String(
                                                    title=Title("Metric label"),
                                                    custom_validate=(
                                                        validators.LengthInRange(min_value=1),
                                                    ),
                                                    help_text=Help(
                                                        "The metric label is displayed alongside the "
                                                        "queried value in the status detail the resulting service. "
                                                        "The metric name will be taken as label if "
                                                        "nothing was specified."
                                                    ),
                                                ),
                                            ),
                                            "metric_name": DictElement(
                                                parameter_form=Metric(),
                                            ),
                                            "promql_query": DictElement(
                                                required=True,
                                                parameter_form=String(
                                                    title=Title(
                                                        "PromQL query (only single return value permitted)"
                                                    ),
                                                    custom_validate=(
                                                        validators.LengthInRange(min_value=1),
                                                    ),
                                                    help_text=Help(
                                                        'Example PromQL query: up{job="node_exporter"}'
                                                    ),
                                                ),
                                            ),
                                            "levels": DictElement(
                                                parameter_form=Dictionary(
                                                    title=Title("Metric levels"),
                                                    help_text=Help(
                                                        "Specify upper and/or lower levels for the queried PromQL value. This option "
                                                        "should be used for simple cases where levels are only required once. You "
                                                        "should use the Prometheus custom services monitoring rule if you want to "
                                                        "specify a rule which applies to multiple Prometheus custom services at once. "
                                                        "The custom rule always has priority over the rule specified here "
                                                        "if the two overlap."
                                                    ),
                                                    custom_validate=(
                                                        validators.LengthInRange(
                                                            min_value=1,
                                                            error_msg=Message(
                                                                "Please specify at least one type of levels"
                                                            ),
                                                        ),
                                                    ),
                                                    elements={
                                                        "lower_levels": DictElement(
                                                            parameter_form=SimpleLevels(
                                                                title=Title("Lower levels"),
                                                                level_direction=LevelDirection.LOWER,
                                                                form_spec_template=Float(),
                                                                prefill_fixed_levels=DefaultValue(
                                                                    (0.0, 0.0)
                                                                ),
                                                                migrate=_migrate_levels,
                                                            ),
                                                        ),
                                                        "upper_levels": DictElement(
                                                            parameter_form=SimpleLevels(
                                                                title=Title("Upper levels"),
                                                                level_direction=LevelDirection.UPPER,
                                                                form_spec_template=Float(),
                                                                prefill_fixed_levels=DefaultValue(
                                                                    (0.0, 0.0)
                                                                ),
                                                                migrate=_migrate_levels,
                                                            ),
                                                        ),
                                                    },
                                                ),
                                            ),
                                        },
                                    ),
                                ),
                            ),
                        },
                    ),
                ),
            ),
        },
    )


rule_spec_special_agent_prometheus = SpecialAgent(
    name="prometheus",
    title=Title("Prometheus"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
)


def _validate_hostname(value: str) -> None:
    try:
        HostAddress(value)
    except ValueError as exception:
        raise validators.ValidationError(
            message=Message(
                "Please enter a valid host name or IPv4 address. "
                "Only letters, digits, dash, underscore and dot are allowed."
            )
        ) from exception


def _validate_service_metrics(value: Sequence[Mapping[str, object]]) -> None:
    used_metric_names = set()
    for metric_details in value:
        if not (metric_name := metric_details.get("metric_name")):
            continue
        if metric_name in used_metric_names:
            raise validators.ValidationError(
                message=Message("Each metric must be unique for a service")
            )
        used_metric_names.add(metric_name)


def _migrate(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    if "verify_cert" in value:
        return value
    migrated_rule = value.copy()
    verify_cert = migrated_rule.pop("verify-cert")
    return migrated_rule | {"verify_cert": verify_cert}


def _migrate_entities(value: object) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(value)
    return ["interfaces" if v == "if" else v for v in value]


def _migrate_levels(value: object) -> SimpleLevelsConfigModel[float]:
    if not isinstance(value, tuple):
        raise TypeError(value)
    match value:
        case (float(), float()):
            return ("fixed", value)
        case _:
            return value
