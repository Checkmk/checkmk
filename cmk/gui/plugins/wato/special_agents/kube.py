#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.version import Edition, is_cloud_edition, mark_edition_only

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    RulespecGroupVMCloudContainer,
    ssl_verification,
)
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    HTTPProxyReference,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Hostname,
    HTTPUrl,
    Integer,
    ListChoice,
    ListOf,
    MigrateNotUpdated,
    RegExp,
    Tuple,
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


def _usage_endpoint(cloud_edition: bool) -> tuple[str, CascadingDropdown] | tuple[str, Tuple]:
    if cloud_edition:
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
    return p if is_cloud_edition() else {k: v for k, v in p.items() if _is_cre_spec(k, v)}


def _openshift() -> tuple[str, str, Dictionary]:
    return (
        "prometheus",
        mark_edition_only(_("Use data from OpenShift"), Edition.CCE),
        Dictionary(
            elements=[
                (
                    "endpoint",
                    HTTPUrl(
                        title=_("Prometheus API endpoint"),
                        allow_empty=False,
                        default_value="https://",
                        help=_(
                            "The full URL to the Prometheus API endpoint including the "
                            "protocol (http or https). OpenShift exposes such "
                            "endpoints via a route in the openshift-monitoring "
                            "namespace called prometheus-k8s."
                        ),
                        size=80,
                    ),
                ),
                ssl_verification(),
                (
                    "proxy",
                    HTTPProxyReference(),
                ),
                _tcp_timeouts(),
            ],
            required_keys=["endpoint", "verify-cert"],
        ),
    )


def _cluster_collector() -> tuple[str, str, Dictionary]:
    return (
        "cluster-collector",
        _("Use data from Checkmk Cluster Collector"),
        Dictionary(  # TODO: adjust help texts depending on ingress inclusion
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
                ssl_verification(),
                (
                    "proxy",
                    HTTPProxyReference(),
                ),
                _tcp_timeouts(),
            ],
            required_keys=["endpoint", "verify-cert"],
        ),
    )


def _valuespec_special_agents_kube():
    return MigrateNotUpdated(
        valuespec=Dictionary(
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
                    MigrateToIndividualOrStoredPassword(
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
                                        "The full URL to the Kubernetes API server "
                                        "including the protocol (http or https) and "
                                        "the port. Be aware that a trailing "
                                        "slash at the end of the URL is likely to "
                                        "result in an error."
                                    ),
                                    size=80,
                                ),
                            ),
                            ssl_verification(),
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
                _usage_endpoint(is_cloud_edition()),
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
                            ("pvcs", _("Persistent Volume Claims & Persistent Volumes")),
                            ("cronjobs", _("CronJobs")),
                            ("cronjobs_pods", _("Pods of CronJobs")),
                        ],
                        default_value=[
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
        name="special_agents:kube",
        valuespec=_valuespec_special_agents_kube,
        doc_references={DocReference.KUBERNETES: _("Monitoring Kubernetes")},
    )
)
