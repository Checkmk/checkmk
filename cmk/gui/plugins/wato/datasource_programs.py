#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.bi as bi
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.mkeventd import service_levels, syslog_facilities, syslog_priorities
from cmk.gui.plugins.metrics.utils import MetricName
from cmk.gui.plugins.wato.special_agents.common import (
    api_request_authentication,
    api_request_connection_elements,
    filter_kubernetes_namespace_element,
    RulespecGroupDatasourceProgramsApps,
    RulespecGroupDatasourceProgramsCustom,
    RulespecGroupDatasourceProgramsHardware,
    RulespecGroupDatasourceProgramsOS,
    RulespecGroupVMCloudContainer,
    validate_aws_tags,
)
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    HTTPProxyReference,
    IndividualOrStoredPassword,
    monitoring_macro_help,
    PasswordFromStore,
    rulespec_registry,
)
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    HostAddress,
    Hostname,
    HTTPUrl,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    NetworkPort,
    Password,
    RegExp,
    TextInput,
    Transform,
    Tuple,
)


def _valuespec_datasource_programs():
    return TextInput(
        title=_("Individual program call instead of agent access"),
        help=_(
            "For agent based checks Check_MK allows you to specify an alternative "
            "program that should be called by Check_MK instead of connecting the agent "
            "via TCP. That program must output the agent's data on standard output in "
            "the same format the agent would do. This is for example useful for monitoring "
            "via SSH."
        )
        + monitoring_macro_help()
        + _('This option can only be used with the permission "Can add or modify executables".')
        + _(
            "<br> HINT: The individual program is called from the current working directory. "
            "You should therefore specify absolute path names in scripts (by using environment variables like OMD_SITE) "
            "to make the individual program call run correctly in all execution contexts (UI and console)."
        ),
        label=_("Command line to execute"),
        empty_text=_("Access Checkmk Agent via TCP"),
        size=80,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsCustom,
        name="datasource_programs",
        valuespec=_valuespec_datasource_programs,
    )
)


def _ssl_verification():
    return (
        "verify-cert",
        Alternative(
            title=_("SSL certificate verification"),
            elements=[
                FixedValue(value=True, title=_("Verify the certificate"), totext=""),
                FixedValue(value=False, title=_("Ignore certificate errors (unsecure)"), totext=""),
            ],
            default_value=False,
        ),
    )


def _tcp_timeouts():
    return (
        "timeout",
        Dictionary(
            title=_("TCP timeouts"),
            elements=[
                (
                    "connect",
                    Integer(
                        title=_("Connect timeout (seconds)"),
                        help=_("Number of seconds to wait for a TCP connection"),
                        default_value=10,
                    ),
                ),
                (
                    "read",
                    Integer(
                        title=_("Read timeout (seconds)"),
                        help=_(
                            "Number of seconds to wait for a response from "
                            "the API during a TCP connection"
                        ),
                        default_value=12,
                    ),
                ),
            ],
        ),
    )


def _valuespec_special_agents_kube():
    return Dictionary(
        elements=[
            (
                "cluster-name",
                Hostname(
                    title=_("Cluster name"),
                    allow_empty=False,
                    help=_(
                        "You must specify a name for your Kubernetes cluster. The provided name"
                        " will be used to make the objects from your cluster unique in a "
                        "multi-cluster setup."
                    ),
                ),
            ),
            (
                "token",
                IndividualOrStoredPassword(
                    title=_("Token"),
                    allow_empty=False,
                ),
            ),
            (
                "kubernetes-api-server",
                Dictionary(
                    elements=[
                        (
                            "endpoint",
                            HTTPUrl(
                                title=_("Endpoint"),
                                allow_empty=False,
                                default_value="https://<control plane ip>:443",
                                help=_(
                                    "The full URL to the Kubernetes API server including the "
                                    "protocol (http or https) and the port."
                                ),
                                size=80,
                            ),
                        ),
                        _ssl_verification(),
                        (
                            "proxy",
                            HTTPProxyReference({"http", "https"}),  # Kubernetes client does not
                            # support socks proxies.
                        ),
                        _tcp_timeouts(),
                    ],
                    required_keys=["endpoint", "verify-cert"],
                    title=_("API server connection"),
                ),
            ),
            (
                "cluster-collector",  # TODO: adjust help texts depending on ingress inclusion
                Dictionary(
                    elements=[
                        (
                            "endpoint",
                            HTTPUrl(
                                title=_("Collector NodePort / Ingress endpoint"),
                                allow_empty=False,
                                default_value="https://<service url>:30035",
                                help=_(
                                    "The full URL to the Cluster Collector service including "
                                    "the protocol (http or https) and the port. Depending on "
                                    "the deployed configuration of the service this can "
                                    "either be the NodePort or the Ingress endpoint."
                                ),
                                size=80,
                            ),
                        ),
                        _ssl_verification(),
                        (
                            "proxy",
                            HTTPProxyReference(),
                        ),
                        _tcp_timeouts(),
                    ],
                    required_keys=["endpoint", "verify-cert"],
                    title=_("Enrich with usage data from Checkmk Cluster Collector"),
                ),
            ),
            (
                "monitored-objects",
                ListChoice(
                    choices=[
                        ("deployments", _("Deployments")),
                        ("daemonsets", _("DaemonSets")),
                        ("statefulsets", _("StatefulSets")),
                        ("nodes", _("Nodes")),
                        ("pods", _("Pods")),
                        ("cronjobs_pods", _("Pods of CronJobs")),
                    ],
                    default_value=[
                        "deployments",
                        "daemonsets",
                        "statefulsets",
                        "nodes",
                        "pods",
                    ],
                    allow_empty=False,
                    title=_("Collect information about..."),
                    help=_(
                        "Select the Kubernetes objects you would like to monitor. Pods "
                        "controlled by CronJobs are treated separately as they are usually "
                        "quite short lived. Those pods will be monitored in the same "
                        "manner as regular pods. Your Dynamic host management rule should "
                        "be configured accordingly to avoid that the piggyback hosts for "
                        "terminated CronJob pods are kept for too long. This 'Pods of CronJobs' "
                        "option has no effect if Pods are not monitored"
                    ),
                ),
            ),
            (
                "namespaces",
                CascadingDropdown(
                    choices=[
                        (
                            "namespace-include-patterns",
                            _("Monitor namespaces matching"),
                            ListOf(
                                valuespec=RegExp(
                                    mode=RegExp.complete,
                                    title=_("Pattern"),
                                    allow_empty=False,
                                ),
                                add_label=_("Add new pattern"),
                                allow_empty=False,
                                help=_(
                                    "You can specify a list of regex patterns to monitor specific "
                                    "namespaces. Only those that do match the predefined patterns "
                                    "will be monitored."
                                ),
                            ),
                        ),
                        (
                            "namespace-exclude-patterns",
                            _("Exclude namespaces matching"),
                            ListOf(
                                valuespec=RegExp(
                                    mode=RegExp.complete,
                                    title=_("Pattern"),
                                    allow_empty=False,
                                ),
                                add_label=_("Add new pattern"),
                                allow_empty=False,
                                help=_(
                                    "You can specify a list of regex patterns to exclude "
                                    "namespaces. Only those that do not match the predefined "
                                    "patterns are monitored."
                                ),
                            ),
                        ),
                    ],
                    orientation="horizontal",
                    title=_("Monitor namespaces"),
                    help=_(
                        "If your cluster has multiple namespaces, you can filter specific ones "
                        "to be monitored. Note that this concerns everything which is part of the "
                        "selected namespaces such as pods for example."
                    ),
                ),
            ),
            (
                "roles",
                CascadingDropdown(
                    title=("Cluster resource aggregation"),
                    choices=[
                        (
                            "cluster-aggregation-exclude-node-roles",
                            _("Exclude Nodes based on their role"),
                            ListOf(
                                valuespec=RegExp(
                                    mode=RegExp.infix,
                                    allow_empty=False,
                                    size=50,
                                ),
                                add_label=_("Add new role"),
                                allow_empty=True,
                                movable=False,
                                help=RegExp(mode=RegExp.infix).help(),
                                default_value=["control-plane", "infra"],
                            ),
                        ),
                        ("cluster-aggregation-include-all-nodes", _("Include all Nodes"), None),
                    ],
                    orientation="horizontal",
                    help=_(
                        "You may find that some Nodes don't add resources to the overall "
                        "workload your Cluster can handle. This option allows you to remove "
                        "Nodes from aggregations on the Cluster host based on their role. A "
                        "node will be omitted, if any of the listed {role}s matches a label "
                        "with name 'node-role.kubernetes.io/{role}'.  This affects the "
                        "following services: Memory resources, CPU resources, Pod resources. "
                        "Only Services on the Cluster host are affected. By default, Nodes "
                        "with role control-plane and infra are omitted.",
                    ),
                ),
            ),
        ],
        optional_keys=["namespaces", "cluster-collector", "roles"],
        default_keys=["cluster-collector"],
        title=_("Kubernetes"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:kube",
        valuespec=_valuespec_special_agents_kube,
    )
)


def _check_not_empty_exporter_dict(value, _varprefix):
    if not value:
        raise MKUserError("dict_selection", _("Please select at least one element"))


def _valuespec_generic_metrics_prometheus():
    namespace_element = (
        "prepend_namespaces",
        DropdownChoice(
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

    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "connection",
                    CascadingDropdown(
                        choices=[
                            (
                                "ip_address",
                                _("IP Address"),
                                Dictionary(
                                    elements=api_request_connection_elements(
                                        help_text=_(
                                            "Specifies a URL path prefix, which is prepended to API calls "
                                            "to the Prometheus API. If this option is not relevant for "
                                            "your installation, please leave it unchecked."
                                        ),
                                        default_port=6443,
                                    ),
                                ),
                            ),
                            (
                                "host_name",
                                _("Host name"),
                                Dictionary(
                                    elements=api_request_connection_elements(
                                        help_text=_(
                                            "Specifies a URL path prefix, which is prepended to API calls "
                                            "to the Prometheus API. If this option is not relevant for "
                                            "your installation, please leave it unchecked."
                                        ),
                                        default_port=6443,
                                    ),
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
                _ssl_verification(),
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
                                                            _(
                                                                "CPU utilization & Kernel performance"
                                                            ),
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
                                    "kube_state",
                                    _("Kube-state-metrics"),
                                    Dictionary(
                                        elements=[
                                            (
                                                "cluster_name",
                                                Hostname(
                                                    title=_("Cluster name"),
                                                    allow_empty=False,
                                                    help=_(
                                                        "You must specify a name for your Kubernetes cluster. The provided name"
                                                        " will be used to create a piggyback host for the cluster related services."
                                                    ),
                                                ),
                                            ),
                                            namespace_element,
                                            filter_kubernetes_namespace_element(),
                                            (
                                                "entities",
                                                ListChoice(
                                                    choices=[
                                                        ("cluster", _("Cluster")),
                                                        ("nodes", _("Nodes")),
                                                        ("services", _("Services")),
                                                        ("pods", _("Pods")),
                                                        ("daemon_sets", _("Daemon sets")),
                                                    ],
                                                    default_value=[
                                                        "cluster",
                                                        "nodes",
                                                        "services",
                                                        "pods",
                                                        "daemon_sets",
                                                    ],
                                                    allow_empty=False,
                                                    title=_("Retrieve information about..."),
                                                    help=_(
                                                        "For your Kubernetes cluster select for which entity levels "
                                                        "you would like to retrieve information about. Piggyback hosts "
                                                        "for the respective entities will be created."
                                                    ),
                                                ),
                                            ),
                                        ],
                                        title=_("Kube state metrics"),
                                        optional_keys=["namespace_include_patterns"],
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
                                                                        Float(
                                                                            title=_("Warning below")
                                                                        ),
                                                                        Float(
                                                                            title=_(
                                                                                "Critical below"
                                                                            )
                                                                        ),
                                                                    ],
                                                                ),
                                                            ),
                                                            (
                                                                "upper_levels",
                                                                Tuple(
                                                                    title=_("Upper levels"),
                                                                    elements=[
                                                                        Float(
                                                                            title=_("Warning at")
                                                                        ),
                                                                        Float(
                                                                            title=_("Critical at")
                                                                        ),
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
        ),
        forth=_transform_agent_prometheus,
    )


def _transform_agent_prometheus(params):
    if "port" in params:
        if params["connection"][0] in ("ip_address", "host_name"):
            params["connection"][1]["port"] = params["port"]
        params.pop("port", None)
    return params


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
    (
        HostRulespec(
            group=RulespecGroupVMCloudContainer,
            name="special_agents:prometheus",
            valuespec=_valuespec_generic_metrics_prometheus,
        )
    )
)


def _valuespec_special_agents_tinkerforge():
    return Dictionary(
        title=_("Tinkerforge"),
        elements=[
            (
                "port",
                Integer(
                    title=_("TCP port number"),
                    help=_("Port number that AppDynamics is listening on. The default is 8090."),
                    default_value=4223,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "segment_display_uid",
                TextInput(
                    title=_("7-segment display uid"),
                    help=_(
                        "This is the uid of the sensor you want to display in the 7-segment display, "
                        "not the uid of the display itself. There is currently no support for "
                        "controling multiple displays."
                    ),
                ),
            ),
            (
                "segment_display_brightness",
                Integer(title=_("7-segment display brightness"), minvalue=0, maxvalue=7),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:tinkerforge",
        valuespec=_valuespec_special_agents_tinkerforge,
    )
)


def _valuespec_special_agents_prism():
    return Dictionary(
        title=_("Nutanix Prism"),
        elements=[
            (
                "port",
                Integer(
                    title=_("TCP port for connection"),
                    default_value=9440,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "username",
                TextInput(
                    title=_("User ID for web login"),
                ),
            ),
            ("password", Password(title=_("Password for this user"))),
        ],
        optional_keys=["port"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name="special_agents:prism",
        valuespec=_valuespec_special_agents_prism,
    )
)


class MultisiteBiDatasource:
    def get_valuespec(self):
        return Dictionary(
            elements=self._get_dynamic_valuespec_elements(),
            optional_keys=["filter", "options", "assignments"],
        )

    def _get_dynamic_valuespec_elements(self):
        return [
            (
                "site",
                CascadingDropdown(
                    choices=[
                        ("local", _("Connect to the local site")),
                        (
                            "url",
                            _("Connect to site url"),
                            HTTPUrl(
                                help=_(
                                    "URL of the remote site, for example https://10.3.1.2/testsite"
                                )
                            ),
                        ),
                    ],
                    sorted=False,
                    orientation="horizontal",
                    title=_("Site connection"),
                ),
            ),
            (
                "credentials",
                CascadingDropdown(
                    choices=[
                        ("automation", _("Use the credentials of the 'automation' user")),
                        (
                            "configured",
                            _("Use the following credentials"),
                            Tuple(
                                elements=[
                                    TextInput(title=_("Automation Username"), allow_empty=True),
                                    Password(title=_("Automation Secret"), allow_empty=True),
                                ],
                            ),
                        ),
                    ],
                    help=_(
                        "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                        "to exist if you choose this option"
                    ),
                    title=_("Login credentials"),
                    default_value="automation",
                ),
            ),
            ("filter", self._vs_filters()),
            ("assignments", self._vs_aggregation_assignments()),
            ("options", self._vs_options()),
        ]

    def _vs_aggregation_assignments(self):
        return Dictionary(
            title=_("Aggregation assignment"),
            elements=[
                (
                    "querying_host",
                    FixedValue(
                        value="querying_host", totext="", title=_("Assign to the querying host")
                    ),
                ),
                (
                    "affected_hosts",
                    FixedValue(
                        value="affected_hosts", totext="", title=_("Assign to the affected hosts")
                    ),
                ),
                (
                    "regex",
                    ListOf(
                        valuespec=Tuple(
                            orientation="horizontal",
                            elements=[
                                RegExp(
                                    title=_("Regular expression"),
                                    help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                    mingroups=0,
                                    maxgroups=9,
                                    size=30,
                                    allow_empty=False,
                                    mode=RegExp.prefix,
                                    case_sensitive=False,
                                ),
                                TextInput(
                                    title=_("Replacement"),
                                    help=_(
                                        "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                    ),
                                    size=30,
                                    allow_empty=False,
                                ),
                            ],
                        ),
                        title=_("Assign via regular expressions"),
                        help=_(
                            "You can add any number of expressions here which are executed succesively until the first match. "
                            "Please specify a regular expression in the first field. This expression should at "
                            "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                            "In the second field you specify the translated aggregation and can refer to the first matched "
                            "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                            ""
                        ),
                        add_label=_("Add expression"),
                        movable=False,
                    ),
                ),
            ],
        )

    def _vs_filters(self):
        return Transform(
            valuespec=Dictionary(
                elements=[
                    (
                        "aggr_name",
                        ListOf(
                            valuespec=TextInput(title=_("Pattern")),
                            title=_("By aggregation name (exact match)"),
                            add_label=_("Add new aggregation"),
                            movable=False,
                        ),
                    ),
                    (
                        "aggr_group_prefix",
                        ListOf(
                            valuespec=DropdownChoice(choices=bi.aggregation_group_choices),
                            title=_("By aggregation group prefix"),
                            add_label=_("Add new group"),
                            movable=False,
                        ),
                    ),
                ],
                title=_("Filter aggregations"),
            ),
            forth=self._transform_vs_filters_forth,
        )

    def _transform_vs_filters_forth(self, value):
        # Version 2.0: Changed key
        #              from aggr_name_regex -> aggr_name_prefix
        #              from aggr_group -> aggr_group_prefix
        #              This transform can be removed with Version 2.3
        for replacement, old_name in (
            ("aggr_name", "aggr_name_regex"),
            ("aggr_group_prefix", "aggr_groups"),
        ):
            if old_name in value:
                value[replacement] = value.pop(old_name)
        return value

    def _vs_options(self):
        return Dictionary(
            elements=[
                (
                    "state_scheduled_downtime",
                    MonitoringState(title=_("State, if BI aggregate is in scheduled downtime")),
                ),
                (
                    "state_acknowledged",
                    MonitoringState(title=_("State, if BI aggregate is acknowledged")),
                ),
            ],
            optional_keys=["state_scheduled_downtime", "state_acknowledged"],
            title=_("Additional options"),
        )


def _valuespec_special_agents_bi():
    return ListOf(
        valuespec=MultisiteBiDatasource().get_valuespec(),
        title=_("BI Aggregations"),
        help=_(
            "This rule allows you to check multiple BI aggregations from multiple sites at once. "
            "You can also assign aggregations to specific hosts through the piggyback mechanism."
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:bi",
        valuespec=_valuespec_special_agents_bi,
    )
)


def _valuespec_special_agents_datadog() -> Dictionary:
    return Dictionary(
        title=_("Datadog"),
        help=_("Configuration of the Datadog special agent."),
        elements=[
            (
                "instance",
                Dictionary(
                    title=_("Datadog instance"),
                    help=_("Provide API host and credentials for your Datadog instance here."),
                    elements=[
                        (
                            "api_key",
                            IndividualOrStoredPassword(
                                title=_("API Key"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "app_key",
                            IndividualOrStoredPassword(
                                title=_("Application Key"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "api_host",
                            HTTPUrl(
                                title=_("API host"),
                                default_value="api.datadoghq.eu",
                            ),
                        ),
                    ],
                    optional_keys=False,
                ),
            ),
            (
                "proxy",
                HTTPProxyReference(),
            ),
            (
                "monitors",
                Dictionary(
                    title=_("Fetch monitors"),
                    help=_(
                        "Fetch monitors from your datadog instance. Fetched monitors will be "
                        "discovered as services on the host where the special agent is executed."
                    ),
                    elements=[
                        (
                            "tags",
                            ListOfStrings(
                                title=_("Restrict by tags"),
                                help=_(
                                    "Restrict fetched monitors by tags (API field <tt>tags</tt>). "
                                    "Monitors must have all of the configured tags in order to be "
                                    "fetched."
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ),
                        (
                            "monitor_tags",
                            ListOfStrings(
                                title=_("Restrict by monitor tags"),
                                help=_(
                                    "Restrict fetched monitors by service and/or custom tags (API "
                                    "field <tt>monitor_tags</tt>). Monitors must have all of the "
                                    "configured tags in order to be fetched."
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "events",
                Dictionary(
                    title=_("Fetch events"),
                    help=_(
                        "Fetch events from the event stream of your datadog instance. Fetched "
                        "events will be forwared to the event console of the site where the "
                        "special agent is executed."
                    ),
                    elements=[
                        (
                            "max_age",
                            Age(
                                title=_("Maximum age of fetched events (10 hours max.)"),
                                help=_(
                                    "During each run, the agent will fetch events which are at "
                                    "maximum this old. The agent memorizes events already fetched "
                                    "during the last run, s.t. no event will be sent to the event "
                                    "console multiple times. Setting this value lower than the "
                                    "check interval of the host will result in missing events. "
                                    "Also note that the Datadog API allows for creating new events "
                                    "which lie in the past. Such events will be missed by the "
                                    "agent if their age exceeds the value specified here."
                                ),
                                minvalue=10,
                                maxvalue=10 * 3600,
                                default_value=600,
                                display=["hours", "minutes", "seconds"],
                            ),
                        ),
                        (
                            "tags",
                            ListOfStrings(
                                title=_("Restrict by tags"),
                                help=_(
                                    "Restrict fetched events by tags (API field <tt>tags</tt>). "
                                    "Events must have all of the configured tags in order to be "
                                    "fetched."
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ),
                        (
                            "tags_to_show",
                            ListOfStrings(
                                valuespec=RegExp(
                                    mode=RegExp.prefix,
                                    size=30,
                                ),
                                title=_("Tags shown in Event Console"),
                                help=_(
                                    "This option allows you to configure which Datadog tags will be "
                                    "shown in the events forwarded to the Event Console. This is "
                                    "done by entering regular expressions matching one or more "
                                    "Datadog tags. Any matching tag will be added to the text of the "
                                    "corresponding event."
                                ),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "syslog_facility",
                            DropdownChoice(
                                choices=syslog_facilities,
                                title=_("Syslog facility"),
                                help=_(
                                    "Syslog facility of forwarded events shown in Event Console."
                                ),
                                default_value=1,
                            ),
                        ),
                        (
                            "syslog_priority",
                            DropdownChoice(
                                choices=syslog_priorities,
                                title=_("Syslog priority"),
                                help=_(
                                    "Syslog priority of forwarded events shown in Event Console."
                                ),
                                default_value=1,
                            ),
                        ),
                        (
                            "service_level",
                            DropdownChoice(
                                choices=service_levels(),
                                title=_("Service level"),
                                help=_("Service level of forwarded events shown in Event Console."),
                                prefix_values=True,
                            ),
                        ),
                        (
                            "add_text",
                            DropdownChoice(
                                choices=[
                                    (
                                        False,
                                        "Do not add text",
                                    ),
                                    (
                                        True,
                                        "Add text",
                                    ),
                                ],
                                title=_("Add text of events"),
                                default_value=False,
                                help=_(
                                    "Add text of events to data forwarded to the Event Console. "
                                    "Newline characters are replaced by '~'."
                                ),
                            ),
                        ),
                    ],
                    optional_keys=["tags", "tags_to_show"],
                ),
            ),
        ],
        optional_keys=["proxy", "monitors", "events"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=watolib.Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:datadog",
        valuespec=_valuespec_special_agents_datadog,
    )
)


def _factory_default_special_agents_jira():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _vs_jira_projects(title):
    return ListOf(
        valuespec=Tuple(
            orientation="horizontal",
            elements=[
                TextInput(
                    title=_("Project"),
                    help=_(
                        "Enter the full name of the "
                        "project here. You can find "
                        "the name in Jira within "
                        '"Projects" - "View all '
                        'projects" - column: "Project". '
                        "This field is case "
                        "insensitive"
                    ),
                    allow_empty=False,
                    regex="^[^']*$",
                    regex_error=_("Single quotes are not allowed here."),
                ),
                ListOfStrings(
                    title=_("Workflows"),
                    help=_('Enter the workflow name for the project here. E.g. "in progress".'),
                    valuespec=TextInput(
                        allow_empty=False,
                        regex="^[^']*$",
                        regex_error=_("Single quotes are not allowed here."),
                    ),
                    orientation="horizontal",
                ),
            ],
        ),
        add_label=_("Add new project"),
        movable=False,
        title=title,
        validate=validate_aws_tags,
    )


def _valuespec_special_agents_jira():
    return Dictionary(
        title=_("Jira statistics"),
        help=_("Use Jira Query Language (JQL) to get statistics out of your " "Jira instance."),
        elements=[
            (
                "instance",
                TextInput(
                    title=_("Jira instance to query"),
                    help=_(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_jira.com. If not set, the "
                        "assigned host is used as instance."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Username"),
                    help=_("The username that should be used for accessing the " "Jira API."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "password",
                PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                ),
            ),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                    default_value="https",
                ),
            ),
            (
                "project_workflows",
                _vs_jira_projects(
                    _(
                        "Monitor the number of issues for given projects and their "
                        "workflows. This results in a service for each project with "
                        "the number of issues per workflow."
                    ),
                ),
            ),
            (
                "jql",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "service_description",
                                TextInput(
                                    title=_("Service description: "),
                                    help=_(
                                        "The resulting service will get this entry as "
                                        "service description"
                                    ),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "query",
                                TextInput(
                                    title=_("JQL query: "),
                                    help=_(
                                        "E.g. 'project = my_project and result = "
                                        '"waiting for something"\''
                                    ),
                                    allow_empty=False,
                                    size=80,
                                ),
                            ),
                            (
                                "result",
                                CascadingDropdown(
                                    title=_("Type of result"),
                                    help=_(
                                        "Here you can define, what search result "
                                        "should be used. You can show the number of search "
                                        "results (count) or the summed up or average values "
                                        "of a given numeric field."
                                    ),
                                    choices=[
                                        ("count", _("Number of " "search results")),
                                        (
                                            "sum",
                                            _(
                                                "Summed up values of "
                                                "the following numeric field:"
                                            ),
                                            Tuple(
                                                elements=[
                                                    TextInput(
                                                        title=_("Field Name: "),
                                                        allow_empty=False,
                                                    ),
                                                    Integer(
                                                        title=_(
                                                            "Limit number of processed search results"
                                                        ),
                                                        help=_(
                                                            "Here you can define, how many search results "
                                                            "should be processed. The max. internal limit "
                                                            "of Jira is 1000 results. If you want to "
                                                            "ignore any limit, set -1 here. Default is 50."
                                                        ),
                                                        default_value=50,
                                                    ),
                                                ],
                                            ),
                                        ),
                                        (
                                            "average",
                                            _("Average value " "of the following numeric field: "),
                                            Tuple(
                                                elements=[
                                                    TextInput(
                                                        title=_("Field Name: "),
                                                        allow_empty=False,
                                                    ),
                                                    Integer(
                                                        title=_(
                                                            "Limit number of processed search results"
                                                        ),
                                                        default_value=50,
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ],
                                    sorted=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                    title=_("Custom search query"),
                ),
            ),
        ],
        optional_keys=[
            "jql",
            "project_workflows",
            "instance",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jira(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jira",
        valuespec=_valuespec_special_agents_jira,
    )
)


def _valuespec_special_agents_mqtt() -> Dictionary:
    return Dictionary(
        title=_("MQTT broker statistics"),
        help=_(
            "Connect to an MQTT broker to get statistics out of your instance. "
            "The information is fetched from the <tt>$SYS</tt> topic of the broker. The "
            "different brokers implement different topics as they are not standardized, "
            "means that not every service available with every broker. "
            "In multi-tentant, enterprise level cluster this agent may not be useful or "
            "probably only when directly connecting to single nodes, because the "
            "<tt>$SYS</tt> topic is node-specific."
        ),
        elements=[
            (
                "username",
                TextInput(
                    title=_("Username"),
                    help=_("The username used for broker authentication."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "password",
                PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                ),
            ),
            (
                "address",
                HostAddress(
                    title=_("Custom address"),
                    help=_(
                        "When set, this address is used for connecting to the MQTT "
                        "broker. If not set, the special agent will use the primary "
                        "address of the host to connect to the MQTT broker."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "port",
                NetworkPort(
                    title=_("Port"),
                    default_value=1883,
                    help=_("The port that is used for the api call."),
                ),
            ),
            (
                "client-id",
                TextInput(
                    title=_("Client ID"),
                    help=_(
                        "Unique client ID used for the broker. Will be randomly "
                        "generated when not set."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("MQTTv31", "MQTTv31"),
                        ("MQTTv311", "MQTTv311"),
                        ("MQTTv5", "MQTTv5"),
                    ],
                    default_value="MQTTv311",
                ),
            ),
            (
                "instance-id",
                TextInput(
                    title=_("Instance ID"),
                    help=_("Unique ID used to identify the instance on the host within Checkmk."),
                    size=32,
                    allow_empty=False,
                    default_value="broker",
                ),
            ),
        ],
        required_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=watolib.Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:mqtt",
        valuespec=_valuespec_special_agents_mqtt,
    )
)


def _factory_default_special_agents_rabbitmq():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_rabbitmq():
    return Dictionary(
        title=_("RabbitMQ"),
        help=_("Requests data from a RabbitMQ instance."),
        elements=[
            (
                "instance",
                TextInput(
                    title=_("RabbitMQ instance to query"),
                    help=_(
                        "Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_rabbitmq.com. If not set, the "
                        "assigned host is used as instance."
                    ),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "user",
                TextInput(
                    title=_("Username"),
                    help=_("The username that should be used for accessing the " "RabbitMQ API."),
                    size=32,
                    allow_empty=False,
                ),
            ),
            (
                "password",
                PasswordFromStore(
                    title=_("Password of the user"),
                    allow_empty=False,
                ),
            ),
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                    default_value="https",
                ),
            ),
            (
                "port",
                Integer(
                    title=_("Port"),
                    default_value=15672,
                    help=_("The port that is used for the api call."),
                ),
            ),
            (
                "sections",
                ListChoice(
                    title=_("Informations to query"),
                    help=_(
                        "Defines what information to query. You can choose "
                        "between the cluster, nodes, vhosts and queues."
                    ),
                    choices=[
                        ("cluster", _("Clusterwide")),
                        ("nodes", _("Nodes")),
                        ("vhosts", _("Vhosts")),
                        ("queues", _("Queues")),
                    ],
                    default_value=["cluster", "nodes", "vhosts", "queues"],
                    allow_empty=False,
                ),
            ),
        ],
        optional_keys=[
            "instance",
            "port",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_rabbitmq(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:rabbitmq",
        valuespec=_valuespec_special_agents_rabbitmq,
    )
)


def _valuespec_special_agents_smb_share():
    return Dictionary(
        elements=[
            (
                "hostname",
                TextInput(
                    title="Hostname",
                    allow_empty=False,
                    help=_(
                        "<p>Usually Checkmk will use the hostname of the host it is attached to. "
                        "With this option you can override this parameter.</p>"
                    ),
                ),
            ),
            (
                "ip_address",
                HostAddress(
                    title=_("IP address"),
                    allow_empty=False,
                    allow_ipv6_address=False,
                    help=_(
                        "<p>Usually Checkmk will use the primary IP address of the host it is "
                        "attached to. With this option you can override this parameter.</p>"
                    ),
                ),
            ),
            (
                "authentication",
                Tuple(
                    title=_("Authentication"),
                    elements=[
                        TextInput(title=_("Username"), allow_empty=False),
                        IndividualOrStoredPassword(title=_("Password"), allow_empty=False),
                    ],
                ),
            ),
            (
                "patterns",
                ListOfStrings(
                    title=_("File patterns"),
                    size=80,
                    help=_(
                        "<p>Here you can specify a list of filename patterns to be sent by the "
                        "agent in the section <tt>fileinfo</tt>. UNC paths with globbing patterns "
                        "are used here, e.g. <tt>\\\\hostname\\share name\\*\\foo\\*.log</tt>. "
                        "Wildcards are not allowed in host or share names. "
                        "Per default each found file will be monitored for size and age. "
                        "By building groups you can alternatively monitor a collection "
                        "of files as an entity and monitor the count, total size, the largest, "
                        "smallest oldest or newest file. Note: if you specify more than one matching rule, then "
                        "<b>all</b> matching rules will be used for defining pattern - not just the "
                        " first one.</p>"
                    ),
                    valuespec=TextInput(size=80),
                ),
            ),
        ],
        optional_keys=["hostname", "ip_address", "authentication"],
        title=_("SMB Share fileinfo"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:smb_share",
        valuespec=_valuespec_special_agents_smb_share,
    )
)
