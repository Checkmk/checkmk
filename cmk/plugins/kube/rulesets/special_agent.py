#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc import version
from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.version import Edition

from cmk.utils import paths

from cmk.gui.form_specs.private import ListExtended  # pylint: disable=cmk-module-layer-violation

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    List,
    MatchingScope,
    migrate_to_password,
    migrate_to_proxy,
    MultipleChoice,
    MultipleChoiceElement,
    Password,
    Proxy,
    ProxySchema,
    RegularExpression,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

OPENSHIFT_EDITIONS = (Edition.CME, Edition.CCE, Edition.CEE)


def _tcp_timeouts() -> Dictionary:
    return Dictionary(
        title=Title("TCP timeouts"),
        elements={
            "connect": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connect timeout (seconds)"),
                    help_text=Help("Number of seconds to wait for a TCP connection"),
                    prefill=DefaultValue(10),
                ),
            ),
            "read": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Read timeout (seconds)"),
                    help_text=Help(
                        "Number of seconds to wait for a response from "
                        "the API during a TCP connection"
                    ),
                    prefill=DefaultValue(12),
                ),
            ),
        },
    )


def _usage_endpoint(edition: Edition) -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Enrich with usage data"),
        migrate=_migrate_usage_endpoint,
        elements=[_cluster_collector(), _openshift()]
        if edition in OPENSHIFT_EDITIONS
        else [_cluster_collector()],
        prefill=DefaultValue("cluster_collector"),
    )


def _migrate_usage_endpoint(p: object) -> tuple[str, object]:
    if not isinstance(p, tuple):
        raise TypeError(p)
    return (p[0].replace("-", "_"), p[1])


def _is_cre_spec(k: str, vs: object) -> bool:
    if k != "usage_endpoint":
        return True
    return isinstance(vs, tuple) and vs[0] in ("cluster_collector", "cluster-collector")


def _transform_openshift_endpoint(p: dict[str, object], edition: Edition) -> dict[str, object]:
    return (
        p if edition in OPENSHIFT_EDITIONS else {k: v for k, v in p.items() if _is_cre_spec(k, v)}
    )


def _migrate_and_transform(p: object, edition: Edition) -> dict[str, object]:
    p = _migrate_form_specs(p)
    return _transform_openshift_endpoint(p, edition)


def _openshift() -> CascadingSingleChoiceElement:
    return CascadingSingleChoiceElement(
        name="prometheus",
        title=Title("Use data from OpenShift"),
        parameter_form=Dictionary(
            migrate=_migrate_form_specs,
            elements={
                "endpoint_v2": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Prometheus API endpoint"),
                        prefill=DefaultValue("https://"),
                        custom_validate=(
                            validators.LengthInRange(min_value=1),
                            validators.Url(
                                protocols=[
                                    validators.UrlProtocol.HTTP,
                                    validators.UrlProtocol.HTTPS,
                                ]
                            ),
                        ),
                        help_text=Help(
                            "The full URL to the Prometheus API endpoint including the "
                            "protocol (http or https). OpenShift exposes such "
                            "endpoints via a route in the openshift-monitoring "
                            "namespace called prometheus-k8s."
                        ),
                    ),
                ),
                "verify_cert": DictElement(
                    required=True,
                    parameter_form=BooleanChoice(
                        title=Title("SSL certificate verification"),
                        label=Label("Verify the certificate"),
                        prefill=DefaultValue(True),
                    ),
                ),
                "proxy": DictElement(
                    required=False,
                    parameter_form=Proxy(migrate=migrate_to_proxy),
                ),
                "timeout": DictElement(required=False, parameter_form=_tcp_timeouts()),
            },
        ),
    )


def _cluster_collector() -> CascadingSingleChoiceElement:
    return CascadingSingleChoiceElement(
        name="cluster_collector",
        title=Title("Use data from Checkmk Cluster Collector"),
        parameter_form=Dictionary(
            migrate=_migrate_form_specs,
            elements={
                "endpoint_v2": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Collector NodePort / Ingress endpoint"),
                        prefill=InputHint("https://<service url>:30035"),
                        help_text=Help(
                            "The full URL to the Cluster Collector service including "
                            "the protocol (http or https) and the port. Depending on "
                            "the deployed configuration of the service this can "
                            "either be the NodePort or the Ingress endpoint."
                        ),
                    ),
                ),
                "verify_cert": DictElement(
                    required=True,
                    parameter_form=BooleanChoice(
                        title=Title("SSL certificate verification"),
                        label=Label("Verify the certificate"),
                        prefill=DefaultValue(True),
                    ),
                ),
                "proxy": DictElement(
                    required=False,
                    parameter_form=Proxy(migrate=migrate_to_proxy),
                ),
                "timeout": DictElement(required=False, parameter_form=_tcp_timeouts()),
            },
        ),
    )


def _api_endpoint() -> Dictionary:
    return Dictionary(
        title=Title("API server connection"),
        migrate=_migrate_form_specs,
        elements={
            "endpoint_v2": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Endpoint"),
                    prefill=InputHint("https://<control plane ip>:443"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        validators.Url(
                            protocols=[
                                validators.UrlProtocol.HTTP,
                                validators.UrlProtocol.HTTPS,
                            ]
                        ),
                    ),
                    help_text=Help(
                        "The full URL to the Kubernetes API server including the protocol "
                        "(http or https) and the port. One trailing slash (if present) "
                        "will be removed."
                    ),
                ),
            ),
            "verify_cert": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("SSL certificate verification"),
                    label=Label("Verify the certificate"),
                    prefill=DefaultValue(True),
                ),
            ),
            "proxy": DictElement(
                required=False,
                parameter_form=Proxy(
                    allowed_schemas=frozenset({ProxySchema.HTTP, ProxySchema.HTTPS}),
                    migrate=migrate_to_proxy,
                ),
            ),
            "timeout": DictElement(required=False, parameter_form=_tcp_timeouts()),
        },
    )


def _validate_hostname(hostname: str) -> None:
    try:
        HostAddress(hostname)
    except ValueError as exception:
        raise validators.ValidationError(
            Message(
                "Please enter a valid host name or IPv4 address. "
                "Only letters, digits, dash, underscore and dot are allowed."
            )
        ) from exception


def _migrate_form_specs(p: object) -> dict[str, object]:
    if not isinstance(p, dict):
        raise TypeError(p)
    return {k.replace("-", "_"): v for k, v in p.items()}


def _migrate_namespaces(p: object) -> tuple[str, list[str]]:
    match p:
        case (str(k), list(patterns)):
            return (k.replace("-", "_"), patterns)
    raise TypeError(p)


def _migrate_cluster_resource_aggregation(p: object) -> tuple[str, list[str] | None]:
    match p:
        case ("cluster-aggregation-exclude-node-roles", list(roles)):
            return "cluster_aggregation_exclude_node_roles", roles
        case "cluster-aggregation-include-all-nodes":
            return "cluster_aggregation_include_all_nodes", None
        case (str(k), roles) if roles is None or isinstance(roles, list):
            return k, roles
    raise TypeError(p)


def _migrate_import_annotations(p: object) -> tuple[str, object]:
    match p:
        case "include-annotations-as-host-labels":
            return "include_annotations_as_host_labels", None
        case "include-matching-annotations-as-host-labels", str(pattern):
            return "include_matching_annotations_as_host_labels", pattern
        case ("include_matching_annotations_as_host_labels", str(pattern)):
            return ("include_matching_annotations_as_host_labels", str(pattern))
        case ("include_annotations_as_host_labels", None):
            return ("include_annotations_as_host_labels", None)
    raise TypeError(p)


def _valuespec_special_agents_kube() -> Dictionary:
    return Dictionary(
        migrate=lambda v: _migrate_and_transform(v, version.edition(paths.omd_root)),
        title=Title("Kubernetes"),
        elements={
            "cluster_name": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Cluster name"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        _validate_hostname,
                    ),
                    help_text=Help(
                        "You must specify a name for your Kubernetes cluster. The provided name"
                        " will be used to make the objects from your cluster unique in a "
                        "multi-cluster setup."
                    ),
                ),
            ),
            "token": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Token"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "kubernetes_api_server": DictElement(
                required=True,
                parameter_form=_api_endpoint(),
            ),
            "usage_endpoint": DictElement(
                required=False,
                parameter_form=_usage_endpoint(version.edition(paths.omd_root)),
            ),
            "monitored_objects": DictElement(
                required=True,
                parameter_form=MultipleChoice(
                    elements=[
                        MultipleChoiceElement(name="deployments", title=Title("Deployments")),
                        MultipleChoiceElement(name="daemonsets", title=Title("DaemonSets")),
                        MultipleChoiceElement(name="statefulsets", title=Title("StatefulSets")),
                        MultipleChoiceElement(name="namespaces", title=Title("Namespaces")),
                        MultipleChoiceElement(name="nodes", title=Title("Nodes")),
                        MultipleChoiceElement(name="pods", title=Title("Pods")),
                        MultipleChoiceElement(name="pvcs", title=Title("Persistent Volume Claims")),
                        MultipleChoiceElement(name="cronjobs", title=Title("CronJobs")),
                        MultipleChoiceElement(
                            name="cronjobs_pods", title=Title("Pods of CronJobs")
                        ),
                    ],
                    prefill=DefaultValue(
                        [
                            "cronjobs",
                            "deployments",
                            "daemonsets",
                            "statefulsets",
                            "namespaces",
                            "nodes",
                            "pods",
                            "pvcs",
                        ]
                    ),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    title=Title("Collect information about..."),
                    help_text=Help(
                        "Select the Kubernetes objects you would like to monitor. Pods "
                        "controlled by CronJobs are treated separately as they are usually "
                        "quite short lived. Those pods will be monitored in the same "
                        "manner as regular pods. Persistent Volume Claims will only appear "
                        "in the respective object piggyback host instead of having their own "
                        "host. Your Dynamic host management rule should "
                        "be configured accordingly to avoid that the piggyback hosts for "
                        "terminated CronJob pods are kept for too long. This 'Pods of CronJobs' "
                        "option has no effect if Pods are not monitored"
                    ),
                ),
            ),
            "namespaces": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    migrate=_migrate_namespaces,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="namespace_include_patterns",
                            title=Title("Monitor namespaces matching"),
                            parameter_form=List(
                                element_template=RegularExpression(
                                    predefined_help_text=MatchingScope.INFIX,
                                    title=Title("Pattern"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                                add_element_label=Label("Add new pattern"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                help_text=Help(
                                    "You can specify a list of regex patterns to monitor specific "
                                    "namespaces. Only those that do match the predefined patterns "
                                    "will be monitored."
                                ),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="namespace_exclude_patterns",
                            title=Title("Exclude namespaces matching"),
                            parameter_form=List(
                                element_template=RegularExpression(
                                    predefined_help_text=MatchingScope.INFIX,
                                    title=Title("Pattern"),
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                                add_element_label=Label("Add new pattern"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                help_text=Help(
                                    "You can specify a list of regex patterns to exclude "
                                    "namespaces. Only those that do not match the predefined "
                                    "patterns are monitored."
                                ),
                            ),
                        ),
                    ],
                    title=Title("Monitor namespaces"),
                    help_text=Help(
                        "If your cluster has multiple namespaces, you can filter specific ones "
                        "to be monitored. Note that this concerns everything which is part of the "
                        "selected namespaces such as pods for example."
                    ),
                    prefill=DefaultValue("namespace_include_patterns"),
                ),
            ),
            "cluster_resource_aggregation": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    migrate=_migrate_cluster_resource_aggregation,
                    title=Title("Cluster resource aggregation"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="cluster_aggregation_exclude_node_roles",
                            title=Title("Exclude Nodes based on their role"),
                            parameter_form=ListExtended(
                                element_template=RegularExpression(
                                    predefined_help_text=MatchingScope.INFIX,
                                    custom_validate=(validators.LengthInRange(min_value=1),),
                                ),
                                add_element_label=Label("Add new role"),
                                editable_order=False,
                                prefill=DefaultValue(["control-plane", "infra"]),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="cluster_aggregation_include_all_nodes",
                            title=Title("Include all Nodes"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    help_text=Help(
                        "You may find that some Nodes don't add resources to the overall "
                        "workload your Cluster can handle. This option allows you to remove "
                        "Nodes from aggregations on the Cluster host based on their role. A "
                        "node will be omitted, if any of the listed {role}s matches a label "
                        "with name 'node-role.kubernetes.io/{role}'.  This affects the "
                        "following services: Memory resources, CPU resources, Pod resources. "
                        "Only Services on the Cluster host are affected. By default, Nodes "
                        "with role control-plane and infra are omitted.",
                    ),
                    prefill=DefaultValue("cluster_aggregation_exclude_node_roles"),
                ),
            ),
            "import_annotations": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Import annotations as host labels"),
                    migrate=_migrate_import_annotations,
                    elements=[
                        CascadingSingleChoiceElement(
                            name="include_matching_annotations_as_host_labels",
                            title=Title("Filter valid annotations by key pattern"),
                            parameter_form=RegularExpression(
                                predefined_help_text=MatchingScope.INFIX,
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                prefill=DefaultValue("checkmk-monitoring$"),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="include_annotations_as_host_labels",
                            title=Title("Import all valid annotations"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    help_text=Help(
                        "By default, Checkmk does not import annotations. If "
                        "this option is enabled, Checkmk will import any "
                        "annotation that is a valid Kubernetes label. These "
                        "imported annotations are added as host labels to their "
                        "respective piggyback host using the syntax "
                        "'cmk/kubernetes/annotation/{key}:{value}'. You can "
                        "further restrict the imported annotations by specifying "
                        "a pattern which Checkmk searches for in the key of the "
                        "annotation."
                    ),
                    prefill=DefaultValue("include_matching_annotations_as_host_labels"),
                ),
            ),
        },
    )


rule_spec_special_agent_kube = SpecialAgent(
    name="kube",
    title=Title("Kubernetes"),
    topic=Topic.CLOUD,
    parameter_form=_valuespec_special_agents_kube,
)
