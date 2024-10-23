#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.version import Edition, edition

from cmk.utils import paths
from cmk.utils.hostaddress import HostAddress
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common_tls_verification import tls_verify_flag_default_no
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    MigrateNotUpdated,
    RegExp,
    TextInput,
    Tuple,
    Url,
)
from cmk.gui.wato import (
    HTTPProxyReference,
    MigrateToIndividualOrStoredPassword,
    RulespecGroupVMCloudContainer,
)
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry

OPENSHIFT_EDITIONS = (Edition.CME, Edition.CCE, Edition.CEE)


def _url(title: str, _help: str, default_value: str, placeholder: str = "") -> Url:
    return Url(
        allow_empty=False,
        show_as_link=True,
        default_scheme="http",
        allowed_schemes=["http", "https"],
        default_value=default_value,
        size=80,
        title=title,
        placeholder=placeholder,
        help=_help,
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


def _usage_endpoint() -> tuple[str, CascadingDropdown] | tuple[str, Tuple]:
    if edition(paths.omd_root) in OPENSHIFT_EDITIONS:
        return (
            "usage_endpoint",
            CascadingDropdown(
                title=("Enrich with usage data"),
                choices=[
                    _cluster_collector(),
                    _openshift(),
                ],
            ),
        )

    value, title, spec = _cluster_collector()
    return (
        "usage_endpoint",
        Tuple(
            elements=[
                FixedValue(value=value, totext=""),
                spec,
            ],
            show_titles=False,
            title=title,
        ),
    )


def _is_cre_spec(k: str, vs: object) -> bool:
    if k != "usage_endpoint":
        return True
    return isinstance(vs, tuple) and vs[0] == "cluster-collector"


def _migrate_cce2cre(p: dict[str, object]) -> dict[str, object]:
    return (
        p
        if edition(paths.omd_root) in OPENSHIFT_EDITIONS
        else {k: v for k, v in p.items() if _is_cre_spec(k, v)}
    )


def _openshift() -> tuple[str, str, Dictionary]:
    return (
        "prometheus",
        _("Use data from OpenShift"),
        Dictionary(
            elements=[
                (
                    "endpoint_v2",
                    _url(
                        title=_("Prometheus API endpoint"),
                        default_value="https://",
                        _help=_(
                            "The full URL to the Prometheus API endpoint including the "
                            "protocol (http or https). OpenShift exposes such "
                            "endpoints via a route in the openshift-monitoring "
                            "namespace called prometheus-k8s."
                        ),
                    ),
                ),
                tls_verify_flag_default_no(),
                (
                    "proxy",
                    HTTPProxyReference(),
                ),
                _tcp_timeouts(),
            ],
            required_keys=["endpoint_v2", "verify-cert"],
        ),
    )


def _cluster_collector() -> tuple[str, str, Dictionary]:
    return (
        "cluster-collector",
        _("Use data from Checkmk Cluster Collector"),
        Dictionary(  # TODO: adjust help texts depending on ingress inclusion
            elements=[
                (
                    "endpoint_v2",
                    _url(
                        title=_("Collector NodePort / Ingress endpoint"),
                        default_value="",
                        placeholder="https://<service url>:30035",
                        _help=_(
                            "The full URL to the Cluster Collector service including "
                            "the protocol (http or https) and the port. Depending on "
                            "the deployed configuration of the service this can "
                            "either be the NodePort or the Ingress endpoint."
                        ),
                    ),
                ),
                tls_verify_flag_default_no(),
                (
                    "proxy",
                    HTTPProxyReference(),
                ),
                _tcp_timeouts(),
            ],
            required_keys=["endpoint_v2", "verify-cert"],
        ),
    )


def _api_endpoint() -> tuple[str, Dictionary]:
    return (
        "kubernetes-api-server",
        Dictionary(
            elements=[
                (
                    "endpoint_v2",
                    _url(
                        title=_("Endpoint"),
                        default_value="",
                        placeholder="https://<control plane ip>:443",
                        _help=_(
                            "The full URL to the Kubernetes API server including the protocol "
                            "(http or https) and the port. One trailing slash (if present) "
                            "will be removed."
                        ),
                    ),
                ),
                tls_verify_flag_default_no(),
                (
                    "proxy",
                    HTTPProxyReference({"http", "https"}),  # Kubernetes client does not
                    # support socks proxies.
                ),
                _tcp_timeouts(),
            ],
            required_keys=["endpoint_v2", "verify-cert"],
            title=_("API server connection"),
        ),
    )


def _validate_hostname(hostname: str, varprefix: str) -> None:
    try:
        HostAddress.validate(hostname)
    except ValueError as exception:
        raise MKUserError(
            varprefix,
            _(
                "Please enter a valid host name or IPv4 address. "
                "Only letters, digits, dash, underscore and dot are allowed."
            ),
        ) from exception


def _valuespec_special_agents_kube():
    return MigrateNotUpdated(
        valuespec=Dictionary(
            elements=[
                (
                    "cluster-name",
                    TextInput(
                        size=38,
                        allow_empty=False,
                        title=_("Cluster name"),
                        help=_(
                            "You must specify a name for your Kubernetes cluster. The provided name"
                            " will be used to make the objects from your cluster unique in a "
                            "multi-cluster setup."
                        ),
                        validate=_validate_hostname,
                    ),
                ),
                (
                    "token",
                    MigrateToIndividualOrStoredPassword(
                        title=_("Token"),
                        allow_empty=False,
                    ),
                ),
                _api_endpoint(),
                _usage_endpoint(),
                (
                    "monitored-objects",
                    ListChoice(
                        choices=[
                            ("deployments", _("Deployments")),
                            ("daemonsets", _("DaemonSets")),
                            ("statefulsets", _("StatefulSets")),
                            ("namespaces", _("Namespaces")),
                            ("nodes", _("Nodes")),
                            ("pods", _("Pods")),
                            ("pvcs", _("Persistent Volume Claims")),
                            ("cronjobs", _("CronJobs")),
                            ("cronjobs_pods", _("Pods of CronJobs")),
                        ],
                        default_value=[
                            "cronjobs",
                            "deployments",
                            "daemonsets",
                            "statefulsets",
                            "namespaces",
                            "nodes",
                            "pods",
                            "pvcs",
                        ],
                        allow_empty=False,
                        title=_("Collect information about..."),
                        help=_(
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
                (
                    "namespaces",
                    CascadingDropdown(
                        choices=[
                            (
                                "namespace-include-patterns",
                                _("Monitor namespaces matching"),
                                ListOf(
                                    valuespec=RegExp(
                                        mode=RegExp.infix,
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
                                        mode=RegExp.infix,
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
                    "cluster-resource-aggregation",
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
                                    default_value=["control-plane", "infra"],
                                ),
                            ),
                            ("cluster-aggregation-include-all-nodes", _("Include all Nodes")),
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
                (
                    "import-annotations",
                    CascadingDropdown(
                        title=("Import annotations as host labels"),
                        choices=[
                            (
                                "include-matching-annotations-as-host-labels",
                                _("Filter valid annotations by key pattern"),
                                RegExp(
                                    mode=RegExp.infix,
                                    allow_empty=False,
                                    default_value="checkmk-monitoring$",
                                    size=50,
                                ),
                            ),
                            (
                                "include-annotations-as-host-labels",
                                _("Import all valid annotations"),
                                None,
                            ),
                        ],
                        orientation="horizontal",
                        help=_(
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
                    ),
                ),
            ],
            optional_keys=[
                "namespaces",
                "usage_endpoint",
                "cluster-resource-aggregation",
                "import-annotations",
            ],
            default_keys=["usage_endpoint"],
            title=_("Kubernetes"),
        ),
        migrate=_migrate_cce2cre,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name=RuleGroup.SpecialAgents("kube"),
        valuespec=_valuespec_special_agents_kube,
        doc_references={DocReference.KUBERNETES: _("Monitoring Kubernetes")},
    )
)
