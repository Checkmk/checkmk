#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import typing

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.metrics.utils import MetricName
from cmk.gui.plugins.wato.special_agents.common import (
    api_request_authentication,
    filter_kubernetes_namespace_element,
    RulespecGroupVMCloudContainer,
    ssl_verification,
)
from cmk.gui.plugins.wato.utils import HostRulespec, rulespec_registry
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    Float,
    Hostname,
    ListChoice,
    ListOf,
    Migrate,
    NetworkPort,
    TextInput,
    Tuple,
)


def _deprecate_dynamic_host_adress(*value: object, **kwargs: object) -> typing.NoReturn:
    raise MKUserError(None, _("The options IP Address and Host name are deprecated - Werk 14573."))


def _check_not_empty_exporter_dict(value, _varprefix):
    if not value:
        raise MKUserError("dict_selection", _("Please select at least one element"))


def _rename_path_prefix_key(connection_elements: dict[str, object]) -> dict[str, object]:
    if (prefix := connection_elements.pop("path-prefix", None)) is not None:
        connection_elements["base_prefix"] = prefix
    return connection_elements


def _valuespec_connection_elements(  # pylint: disable=redefined-builtin
    help: str,
) -> Migrate:
    return Migrate(
        valuespec=Dictionary(
            elements=[
                ("port", NetworkPort(title=_("Port"), default_value=6443)),
                (
                    "path_prefix",
                    TextInput(
                        title=_("Custom path prefix"),
                        help=_(
                            "Specifies a URL path prefix, which is prepended to API calls "
                            "to the Prometheus API. If this option is not relevant for "
                            "your installation, please leave it unchecked."
                        ),
                        allow_empty=False,
                    ),
                ),
                (
                    "base_prefix",
                    TextInput(
                        title=_("Custom URL base prefix"),
                        help=_(
                            "Specifies a prefix, which is prepended to the hostname "
                            "or base address. This is an exotic option, which is "
                            "kept for legacy reasons. Consider using a custom URL instead. "
                            "If this option is not relevant for your installation, "
                            "please leave it unchecked."
                        ),
                        allow_empty=False,
                    ),
                ),
            ],
            show_more_keys=["base_prefix"],
            help=help,
        ),
        migrate=_rename_path_prefix_key,
        validate=_deprecate_dynamic_host_adress,
    )


def _valuespec_generic_metrics_prometheus() -> Dictionary:
    namespace_element = (
        "prepend_namespaces",
        DropdownChoice[str](
            title=_("Prepend namespace prefix for hosts"),
            help=_(
                "If a cluster uses multiple namespaces you need to activate this option. "
                "Hosts for namespaced Kubernetes objects will then be prefixed with the "
                "name of their namespace. This makes Kubernetes resources in different "
                "namespaces that have the same name distinguishable, but results in "
                "longer hostnames."
            ),
            choices=[
                ("use_namespace", _("Use a namespace prefix")),
                ("omit_namespace", _("Don't use a namespace prefix")),
            ],
        ),
    )

    return Dictionary(
        elements=[
            (
                "connection",
                CascadingDropdown(
                    choices=[
                        (
                            "ip_address",
                            _("(deprecated) IP Address"),
                            _valuespec_connection_elements(
                                help=_("Use IP Address of assigned host")
                            ),
                        ),
                        (
                            "host_name",
                            _("(deprecated) Host name"),
                            _valuespec_connection_elements(
                                help=_("Use host name of assigned host")
                            ),
                        ),
                        (
                            "url_custom",
                            _("Custom URL"),
                            Dictionary(
                                elements=[
                                    (
                                        "url_address",
                                        TextInput(
                                            title=_("Custom URL server address"),
                                            help=_(
                                                "Specify a custom URL to connect to "
                                                "your server. Do not include the "
                                                "protocol. This option overwrites "
                                                "all available options such as port and "
                                                "other URL prefixes."
                                            ),
                                            allow_empty=False,
                                        ),
                                    )
                                ],
                                optional_keys=[],
                            ),
                        ),
                    ],
                    title=_("Prometheus connection option"),
                ),
            ),
            ssl_verification(),
            api_request_authentication(),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                ),
            ),
            (
                "exporter",
                ListOf(
                    valuespec=CascadingDropdown(
                        choices=[
                            (
                                "node_exporter",
                                _("Node Exporter"),
                                Dictionary(
                                    elements=[
                                        (
                                            "host_mapping",
                                            Hostname(
                                                title=_("Explicitly map Node Exporter host"),
                                                allow_empty=True,
                                                help=_(
                                                    "Per default, Checkmk tries to map the underlying Checkmk host "
                                                    "to the Node Exporter host which contains either the Checkmk "
                                                    'hostname, host address or "localhost" in its endpoint address. '
                                                    "The created services of the mapped Node Exporter will "
                                                    "be assigned to the Checkmk host. A piggyback host for each "
                                                    "Node Exporter host will be created if none of the options are "
                                                    "valid. "
                                                    "This option allows you to explicitly map one of your Node "
                                                    "Exporter hosts to the underlying Checkmk host. This can be "
                                                    "used if the default options do not apply to your setup."
                                                ),
                                            ),
                                        ),
                                        (
                                            "entities",
                                            ListChoice(
                                                choices=[
                                                    ("df", _("Filesystems")),
                                                    ("diskstat", _("Disk IO")),
                                                    ("mem", _("Memory")),
                                                    (
                                                        "kernel",
                                                        _("CPU utilization & Kernel performance"),
                                                    ),
                                                ],
                                                default_value=[
                                                    "df",
                                                    "diskstat",
                                                    "mem",
                                                    "kernel",
                                                ],
                                                allow_empty=False,
                                                title=_("Retrieve information about..."),
                                                help=_(
                                                    "For your respective kernel select the hardware or OS entity "
                                                    "you would like to retrieve information about."
                                                ),
                                            ),
                                        ),
                                    ],
                                    title=_("Node Exporter metrics"),
                                    optional_keys=["host_mapping"],
                                ),
                            ),
                            (
                                "cadvisor",
                                _("cAdvisor"),
                                Dictionary(
                                    elements=[
                                        (
                                            "entity_level",
                                            CascadingDropdown(
                                                title=_(
                                                    "Entity level used to create Checkmk piggyback hosts"
                                                ),
                                                help=_(
                                                    "The retrieved information from the cAdvisor will be aggregated according"
                                                    " to the selected entity level. Resulting services will be allocated to the created"
                                                    " Checkmk piggyback hosts."
                                                ),
                                                choices=[
                                                    (
                                                        "container",
                                                        _(
                                                            "Container - Display the information on container level"
                                                        ),
                                                        Dictionary(
                                                            elements=[
                                                                (
                                                                    "container_id",
                                                                    DropdownChoice(
                                                                        title=_(
                                                                            "Host name used for containers"
                                                                        ),
                                                                        help=_(
                                                                            "For Containers - Choose which identifier is used for the monitored containers."
                                                                            " This will affect the name used for the piggyback host"
                                                                            " corresponding to the container, as well as items for"
                                                                            " services created on the node for each container."
                                                                        ),
                                                                        choices=[
                                                                            (
                                                                                "short",
                                                                                _(
                                                                                    "Short - Use the first 12 characters of the docker container ID"
                                                                                ),
                                                                            ),
                                                                            (
                                                                                "long",
                                                                                _(
                                                                                    "Long - Use the full docker container ID"
                                                                                ),
                                                                            ),
                                                                            (
                                                                                "name",
                                                                                _(
                                                                                    "Name - Use the name of the container"
                                                                                ),
                                                                            ),
                                                                        ],
                                                                    ),
                                                                )
                                                            ],
                                                            optional_keys=[],
                                                        ),
                                                    ),
                                                    (
                                                        "pod",
                                                        _(
                                                            "Pod - Display the information for pod level"
                                                        ),
                                                        Dictionary(
                                                            elements=[namespace_element],
                                                            optional_keys=[],
                                                        ),
                                                    ),
                                                    (
                                                        "both",
                                                        _(
                                                            "Both - Display the information for both, pod and container, levels"
                                                        ),
                                                        Dictionary(
                                                            elements=[
                                                                (
                                                                    "container_id",
                                                                    DropdownChoice(
                                                                        title=_(
                                                                            "Host name used for containers"
                                                                        ),
                                                                        help=_(
                                                                            "For Containers - Choose which identifier is used for the monitored containers."
                                                                            " This will affect the name used for the piggyback host"
                                                                            " corresponding to the container, as well as items for"
                                                                            " services created on the node for each container."
                                                                        ),
                                                                        choices=[
                                                                            (
                                                                                "short",
                                                                                _(
                                                                                    "Short - Use the first 12 characters of the docker container ID"
                                                                                ),
                                                                            ),
                                                                            (
                                                                                "long",
                                                                                _(
                                                                                    "Long - Use the full docker container ID"
                                                                                ),
                                                                            ),
                                                                            (
                                                                                "name",
                                                                                _(
                                                                                    "Name - Use the name of the container"
                                                                                ),
                                                                            ),
                                                                        ],
                                                                    ),
                                                                ),
                                                                namespace_element,
                                                            ],
                                                            optional_keys=[],
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ),
                                        filter_kubernetes_namespace_element(),
                                        (
                                            "entities",
                                            ListChoice(
                                                choices=[
                                                    ("diskio", _("Disk IO")),
                                                    ("cpu", _("CPU utilization")),
                                                    ("df", _("Filesystem")),
                                                    ("if", _("Network")),
                                                    ("memory", _("Memory")),
                                                ],
                                                default_value=[
                                                    "diskio",
                                                    "cpu",
                                                    "df",
                                                    "if",
                                                    "memory",
                                                ],
                                                allow_empty=False,
                                                title=_("Retrieve information about..."),
                                                help=_(
                                                    "For your respective kernel select the hardware or OS entity "
                                                    "you would like to retrieve information about."
                                                ),
                                            ),
                                        ),
                                    ],
                                    title=_("CAdvisor"),
                                    validate=_check_not_empty_exporter_dict,
                                    optional_keys=[
                                        "diskio",
                                        "cpu",
                                        "df",
                                        "if",
                                        "memory",
                                        "namespace_include_patterns",
                                    ],
                                ),
                            ),
                        ]
                    ),
                    add_label=_("Add new Scrape Target"),
                    title=_(
                        "Prometheus Scrape Targets (include Prometheus Exporters) to fetch information from"
                    ),
                    help=_(
                        "You can specify which Scrape Targets including Exporters "
                        "are connected to your Prometheus instance. The Prometheus "
                        "Special Agent will automatically generate services for the "
                        "selected monitoring information. You can create your own "
                        "defined services with the custom PromQL query option below "
                        "if one of the Scrape Target types are not listed here."
                    ),
                ),
            ),
            (
                "promql_checks",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "service_description",
                                TextInput(
                                    title=_("Service name"),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "host_name",
                                Hostname(
                                    title=_("Assign service to following host"),
                                    allow_empty=False,
                                    help=_(
                                        "Specify the host to which the resulting "
                                        "service will be assigned to. The host "
                                        "should be configured to allow Piggyback "
                                        "data."
                                    ),
                                ),
                            ),
                            (
                                "metric_components",
                                ListOf(
                                    valuespec=Dictionary(
                                        title=_("PromQL query"),
                                        elements=[
                                            (
                                                "metric_label",
                                                TextInput(
                                                    title=_("Metric label"),
                                                    allow_empty=False,
                                                    help=_(
                                                        "The metric label is displayed alongside the "
                                                        "queried value in the status detail the resulting service. "
                                                        "The metric name will be taken as label if "
                                                        "nothing was specified."
                                                    ),
                                                ),
                                            ),
                                            ("metric_name", MetricName()),
                                            (
                                                "promql_query",
                                                TextInput(
                                                    title=_(
                                                        "PromQL query (only single return value permitted)"
                                                    ),
                                                    allow_empty=False,
                                                    size=80,
                                                    help=_(
                                                        'Example PromQL query: up{job="node_exporter"}'
                                                    ),
                                                ),
                                            ),
                                            (
                                                "levels",
                                                Dictionary(
                                                    elements=[
                                                        (
                                                            "lower_levels",
                                                            Tuple(
                                                                title=_("Lower levels"),
                                                                elements=[
                                                                    Float(title=_("Warning below")),
                                                                    Float(
                                                                        title=_("Critical below")
                                                                    ),
                                                                ],
                                                            ),
                                                        ),
                                                        (
                                                            "upper_levels",
                                                            Tuple(
                                                                title=_("Upper levels"),
                                                                elements=[
                                                                    Float(title=_("Warning at")),
                                                                    Float(title=_("Critical at")),
                                                                ],
                                                            ),
                                                        ),
                                                    ],
                                                    title="Metric levels",
                                                    validate=_verify_prometheus_empty,
                                                    help=_(
                                                        "Specify upper and/or lower levels for the queried PromQL value. This option "
                                                        "should be used for simple cases where levels are only required once. You "
                                                        "should use the Prometheus custom services monitoring rule if you want to "
                                                        "specify a rule which applies to multiple Prometheus custom services at once. "
                                                        "The custom rule always has priority over the rule specified here "
                                                        "if the two overlap."
                                                    ),
                                                ),
                                            ),
                                        ],
                                        optional_keys=["metric_name", "levels"],
                                    ),
                                    title=_("PromQL queries for Service"),
                                    add_label=_("Add new PromQL query"),
                                    allow_empty=False,
                                    magic="@;@",
                                    validate=_validate_prometheus_service_metrics,
                                ),
                            ),
                        ],
                        optional_keys=["host_name"],
                    ),
                    title=_("Service creation using PromQL queries"),
                    add_label=_("Add new Service"),
                ),
            ),
        ],
        title=_("Prometheus"),
        optional_keys=["auth_basic"],
    )


def _verify_prometheus_empty(value, varprefix):
    if not value:
        raise MKUserError(varprefix, _("Please specify at least one type of levels"))


def _validate_prometheus_service_metrics(value, _varprefix):
    used_metric_names = []
    for metric_details in value:
        metric_name = metric_details.get("metric_name")
        if not metric_name:
            continue
        if metric_name in used_metric_names:
            raise MKUserError(metric_name, _("Each metric must be unique for a service"))
        used_metric_names.append(metric_name)


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:prometheus",
        valuespec=_valuespec_generic_metrics_prometheus,
        doc_references={DocReference.PROMETHEUS: _("Integrating Prometheus")},
    )
)
