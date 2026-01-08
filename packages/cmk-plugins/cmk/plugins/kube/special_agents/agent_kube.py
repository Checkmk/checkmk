#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

"""agent_kube

Checkmk special agent for monitoring Kubernetes clusters.
This agent is required for monitoring data provided by the Kubernetes API and the Checkmk collectors,
which can optionally be deployed within a cluster.
The agent requires Kubernetes version v1.26 or higher.
Moreover, read access to the Kubernetes API endpoints monitored by Checkmk must be provided.
"""

from __future__ import annotations

import argparse
import cProfile
import enum
import logging
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import TypeVar

import requests
import urllib3
from pydantic import TypeAdapter

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option, Secret
from cmk.plugins.kube import common, performance, prometheus_section, query
from cmk.plugins.kube.agent_handlers import (
    cluster_handler,
    cronjob_handler,
    daemonset_handler,
    deployment_handler,
    namespace_handler,
    node_handler,
    pod_handler,
    statefulset_handler,
)
from cmk.plugins.kube.agent_handlers.common import (
    AnnotationNonPatternOption,
    any_match_from_list_of_infix_patterns,
    CheckmkHostSettings,
    Cluster,
    DaemonSet,
    Deployment,
    kube_object_namespace_name,
    KubeNamespacedObj,
    namespace_name,
    Node,
    PB_KUBE_OBJECT,
    PiggybackFormatter,
    pod_name,
    StatefulSet,
)
from cmk.plugins.kube.agent_handlers.persistent_volume_claim_handler import (
    attached_pvc_names_from_pods,
    create_pvc_sections,
    filter_kubelet_volume_metrics,
    group_parsed_pvcs_by_namespace,
    group_serialized_volumes_by_namespace,
    pod_attached_persistent_volume_claim_names,
    serialize_attached_volumes_from_kubelet_metrics,
)
from cmk.plugins.kube.api_server import APIData, from_kubernetes
from cmk.plugins.kube.common import (
    LOGGER,
    lookup_name,
    Piggyback,
    PodLookupName,
    PodsToHost,
    RawMetrics,
)
from cmk.plugins.kube.prometheus_api import ResponseSuccess
from cmk.plugins.kube.schemata import api, section
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__VERSION__ = "2.6.0b1"

AGENT_NAME = "kube"

TOKEN_OPTION = "token"


class Profile:
    def __init__(self, *, profile_file: str) -> None:
        self._profile_file = Path(profile_file)
        self._profile: cProfile.Profile | None = None

    def __enter__(self) -> Profile:
        self._profile = cProfile.Profile()
        self._profile.enable()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if not self._profile:
            return

        self._profile.disable()

        self._profile.dump_stats(str(self._profile_file))
        self._write_dump_script()

    def _write_dump_script(self) -> None:
        script_path = self._profile_file.with_suffix(".py")
        with script_path.open("w", encoding="utf-8") as f:
            f.write(
                "#!/usr/bin/env python3\n"
                "import pstats\n"
                f'stats = pstats.Stats("{self._profile_file}")\n'
                "stats.sort_stats('cumtime').print_stats()\n"
            )
        script_path.chmod(0o755)


class MonitoredObject(enum.Enum):
    deployments = "deployments"
    daemonsets = "daemonsets"
    statefulsets = "statefulsets"
    namespaces = "namespaces"
    nodes = "nodes"
    pods = "pods"
    cronjobs = "cronjobs"
    cronjobs_pods = "cronjobs_pods"
    pvcs = "pvcs"


def parse_arguments(args: list[str]) -> argparse.Namespace:
    prog, description = __doc__.split("\n\n", maxsplit=1)
    p = argparse.ArgumentParser(prog=prog, description=description)
    p.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (for even more output use -vvv)",
    )
    p.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_headers=[("authorization", "Bearer ****")]),
        help="Enables VCR tracing for the API calls",
    )
    p.add_argument(
        "--cluster",
        required=True,
        help="The name of the Kubernetes cluster",
    )
    p.add_argument(
        "--kubernetes-cluster-hostname",
        required=True,
        help="The name of the Checkmk host which represents the Kubernetes cluster (this will be "
        "the host where the Kubernetes rule has been assigned to)",
    )
    parser_add_secret_option(p, long=f"--{TOKEN_OPTION}", help="Token for that user", required=True)
    p.add_argument(
        "--monitored-objects",
        type=MonitoredObject,
        nargs="+",
        default=[
            MonitoredObject.deployments,
            MonitoredObject.daemonsets,
            MonitoredObject.statefulsets,
            MonitoredObject.pods,
            MonitoredObject.namespaces,
            MonitoredObject.nodes,
            MonitoredObject.cronjobs,
        ],
        help="The Kubernetes objects which are supposed to be monitored. Available objects: "
        "deployments, nodes, pods, daemonsets, statefulsets, cronjobs_pods",
    )
    p.add_argument(
        "--api-server-endpoint", required=True, help="API server endpoint for Kubernetes API calls"
    )
    p.add_argument(
        "--api-server-proxy",
        type=str,
        default="FROM_ENVIRONMENT",
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the Kubernetes api server. If not set, the environment settings "
            "will be used."
        ),
    )

    p.add_argument("--verify-cert-api", action="store_true", help="Verify certificate")
    namespaces = p.add_mutually_exclusive_group()
    namespaces.add_argument(
        "--namespace-include-patterns",
        "-n",
        action="append",
        default=[],
        help="Regex patterns of namespaces to show in the output. Cannot use both include and "
        "exclude patterns",
    )
    namespaces.add_argument(
        "--namespace-exclude-patterns",
        action="append",
        default=[],
        help="Regex patterns of namespaces to exclude in the output. Cannot use both include and "
        "exclude patterns.",
    )
    p.add_argument(
        "--profile",
        metavar="FILE",
        help="Profile the performance of the agent and write the output to a file",
    )
    p.add_argument(
        "--k8s-api-connect-timeout",
        type=int,
        default=10,
        help="The timeout in seconds the special agent will wait for a "
        "connection to the Kubernetes API.",
    )
    p.add_argument(
        "--k8s-api-read-timeout",
        type=int,
        default=12,
        help="The timeout in seconds the special agent will wait for a "
        "response from the Kubernetes API.",
    )
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--cluster-aggregation-exclude-node-roles",
        nargs="+",
        default=["control-plane", "infra"],
        dest="roles",
        help="You may find that some Nodes don't add resources to the overall "
        "workload your Cluster can handle. This option allows you to remove "
        "Nodes from aggregations on the Cluster host based on their role. A "
        "node will be omitted, if any of the listed {role}s matches a label "
        "with name 'node-role.kubernetes.io/{role}'.  This affects the "
        "following services: Memory resources, CPU resources, Pod resources. "
        "Only Services on the Cluster host are affected. By default, Nodes "
        "with role control-plane and infra are omitted.",
    )
    group.add_argument(
        "--cluster-aggregation-include-all-nodes",
        action="store_false",
        dest="roles",
        help="Services on the cluster host will not exclude nodes based on their roles.",
    )
    group_host_labels = p.add_mutually_exclusive_group()
    group_host_labels.add_argument(
        "--include-annotations-as-host-labels",
        action="store_const",
        const=AnnotationNonPatternOption.import_all,
        dest="annotation_key_pattern",
        help="By default, the agent ignores annotations. With this option, all "
        "Kubernetes annotations that are valid Kubernetes labels are written to "
        "the agent output. Specifically, it is verified that the annotation "
        "value meets the same requirements as a label value. These annotations "
        "are added as host labels to their respective piggyback host using the "
        "syntax 'cmk/kubernetes/annotation/{key}:{value}'.",
    )
    group_host_labels.add_argument(
        "--include-matching-annotations-as-host-labels",
        dest="annotation_key_pattern",
        help="You can further restrict the imported annotations by specifying "
        "a pattern which the agent searches for in the key of the annotation.",
    )
    group_host_labels.set_defaults(annotation_key_pattern=AnnotationNonPatternOption.ignore_all)

    data_endpoint = p.add_mutually_exclusive_group()
    data_endpoint.add_argument(
        "--cluster-collector-endpoint",
        help="Endpoint to query metrics from Kubernetes cluster agent",
    )
    data_endpoint.add_argument(
        "--prometheus-endpoint",
        help="The full URL to the Prometheus API endpoint including the protocol (http or https). "
        "OpenShift exposes such endpoints via a route in the openshift-monitoring namespace called "
        "prometheus-k8s.",
    )
    p.add_argument(
        "--usage-connect-timeout",
        type=int,
        default=10,
        help="The timeout in seconds the special agent will wait for a "
        "connection to the endpoint specified by --prometheus-endpoint or "
        "--cluster-collector-endpoint.",
    )
    p.add_argument(
        "--usage-read-timeout",
        type=int,
        default=12,
        help="The timeout in seconds the special agent will wait for a "
        "response from the endpoint specified by --prometheus-endpoint or "
        "--cluster-collector-endpoint.",
    )
    p.add_argument(
        "--usage-proxy",
        type=str,
        default="FROM_ENVIRONMENT",
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the endpoint specified by --prometheus-endpoint or "
            "--cluster-collector-endpoint. "
            "If not set, the environment settings will be used."
        ),
    )
    p.add_argument(
        "--usage-verify-cert",
        action="store_true",
        help="Verify certificate for the endpoint specified by --prometheus-endpoint or "
        "--cluster-collector-endpoint.",
    )
    arguments = p.parse_args(args)
    return arguments


def setup_logging(verbosity: int) -> None:
    if verbosity >= 3:
        lvl = logging.DEBUG
    elif verbosity == 2:
        lvl = logging.INFO
    elif verbosity == 1:
        lvl = logging.WARN
    else:
        logging.disable(logging.CRITICAL)
        lvl = logging.CRITICAL
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(message)s")


@dataclass(frozen=True)
class ComposedEntities:
    # TODO: Currently, this class prepares APIData by packaging data from
    # different API queries. Some, but not all user configurations are taken
    # into account. In particular, some things such as namespace filtering is
    # done elsewhere. If we such functionality here, we can consider changing
    # the name to MonitoredEntities.
    daemonsets: Sequence[DaemonSet]
    statefulsets: Sequence[StatefulSet]
    deployments: Sequence[Deployment]
    nodes: Sequence[Node]
    cluster: Cluster

    @classmethod
    def from_api_resources(
        cls, excluded_node_roles: Sequence[str], api_data: APIData
    ) -> ComposedEntities:
        """Creating and filling the Cluster with the Kubernetes Objects"""

        LOGGER.debug("Constructing k8s objects based on collected API data")

        uid_to_api_pod = {api_pod.uid: api_pod for api_pod in api_data.pods}
        agent_deployments = [
            Deployment(
                metadata=api_deployment.metadata,
                spec=api_deployment.spec,
                status=api_deployment.status,
                pods=[uid_to_api_pod[uid] for uid in api_deployment.pods],
            )
            for api_deployment in api_data.deployments
        ]

        agent_daemonsets = [
            DaemonSet(
                metadata=api_daemon_set.metadata,
                spec=api_daemon_set.spec,
                status=api_daemon_set.status,
                pods=[uid_to_api_pod[uid] for uid in api_daemon_set.pods],
            )
            for api_daemon_set in api_data.daemonsets
        ]

        agent_statefulsets = [
            StatefulSet(
                metadata=api_statefulset.metadata,
                spec=api_statefulset.spec,
                status=api_statefulset.status,
                pods=[uid_to_api_pod[uid] for uid in api_statefulset.pods],
            )
            for api_statefulset in api_data.statefulsets
        ]

        node_to_api_pod = defaultdict(list)
        for api_pod in api_data.pods:
            if (node_name := api_pod.spec.node) is not None:
                node_to_api_pod[node_name].append(api_pod)

        agent_nodes = [
            Node(
                metadata=node_api.metadata,
                status=node_api.status,
                kubelet_health=node_api.kubelet_health,
                pods=node_to_api_pod[node_api.metadata.name],
            )
            for node_api in api_data.nodes
        ]

        agent_cluster = Cluster.from_api_resources(excluded_node_roles, api_data)

        LOGGER.debug(
            "Cluster composition: Nodes (%s), Deployments (%s), DaemonSets (%s), StatefulSets (%s)",
            len(agent_nodes),
            len(agent_deployments),
            len(agent_daemonsets),
            len(agent_statefulsets),
        )

        return cls(
            daemonsets=agent_daemonsets,
            statefulsets=agent_statefulsets,
            deployments=agent_deployments,
            nodes=agent_nodes,
            cluster=agent_cluster,
        )


# Pod specific helpers


def filter_pods_by_namespace(
    pods: Sequence[api.Pod], api_namespace: api.NamespaceName
) -> Sequence[api.Pod]:
    return [pod for pod in pods if kube_object_namespace_name(pod) == api_namespace]


def filter_pods_by_cron_job(pods: Sequence[api.Pod], cron_job: api.CronJob) -> Sequence[api.Pod]:
    return [pod for pod in pods if pod.uid in cron_job.pod_uids]


def filter_pods_by_phase(pods: Iterable[api.Pod], phase: api.Phase) -> Sequence[api.Pod]:
    return [pod for pod in pods if pod.status.phase == phase]


def namespaced_name_from_metadata(metadata: api.MetaData) -> str:
    return api.namespaced_name(metadata.namespace, metadata.name)


def write_machine_sections(
    composed_entities: ComposedEntities,
    machine_sections: Mapping[str, str],
    piggyback_formatter: PiggybackFormatter,
) -> None:
    # make sure we only print sections for nodes currently visible via Kubernetes api:
    for api_node in composed_entities.nodes:
        if sections := machine_sections.get(str(api_node.metadata.name)):
            sys.stdout.write(f"<<<<{piggyback_formatter(api_node)}>>>>\n")
            sys.stdout.write(sections)
            sys.stdout.write("<<<<>>>>\n")


def _supported_cluster_collector_major_version(
    collector_version: str, supported_max_major_version: int
) -> bool:
    """Check if the collector version is supported

    Examples:
         >>> _supported_cluster_collector_major_version('1.1.2', 1)
         True

         >>> _supported_cluster_collector_major_version('2.2.1b2', 0)
         False
    """
    return int(collector_version[0]) <= supported_max_major_version


class ClusterConnectionError(Exception):
    pass


Model = TypeVar("Model")


def _parse_raw_metrics(content: bytes) -> list[RawMetrics]:
    # This function is called once per agent_kube invocation. Moving the TypeAdapter definition to
    # import time has no impact. TypeAdapter is faster than RootModel (see CMK-19527), thus
    # remains unchanged.
    # nosemgrep: type-adapter-detected
    adapter = TypeAdapter(list[RawMetrics])
    return adapter.validate_json(content)


def request_cluster_collector(
    token: Secret[str],
    path: query.CollectorPath,
    config: query.CollectorSessionConfig,
    parser: Callable[[bytes], Model],
) -> Model:
    session = query.create_session(token, config, LOGGER)
    url = config.cluster_collector_endpoint.removesuffix("/") + path
    request = requests.Request("GET", url)
    prepare_request = session.prepare_request(request)
    try:
        cluster_resp = session.send(prepare_request, timeout=config.requests_timeout())
        cluster_resp.raise_for_status()
    except requests.HTTPError as e:
        raise CollectorHandlingException(
            title="Connection Error",
            detail=f"Failed attempting to communicate with cluster collector at URL {url}",
        ) from e
    except requests.exceptions.RequestException as e:
        # All TCP Exceptions raised by requests inherit from RequestException,
        # see https://docs.python-requests.org/en/latest/user/quickstart/#errors-and-exceptions
        raise CollectorHandlingException(
            title="Setup Error",
            detail=f"Failure to establish a connection to cluster collector at URL {url}",
        ) from e

    return parser(cluster_resp.content)


def pod_lookup_from_api_pod(api_pod: api.Pod) -> PodLookupName:
    return lookup_name(kube_object_namespace_name(api_pod), pod_name(api_pod))


def kube_objects_from_namespaces(
    kube_objects: Sequence[KubeNamespacedObj], namespaces: set[api.NamespaceName]
) -> Sequence[KubeNamespacedObj]:
    return [kube_obj for kube_obj in kube_objects if kube_obj.metadata.namespace in namespaces]


def namespaces_from_namespacenames(
    api_namespaces: Sequence[api.Namespace], namespace_names: set[api.NamespaceName]
) -> Sequence[api.Namespace]:
    return [
        api_namespace
        for api_namespace in api_namespaces
        if namespace_name(api_namespace) in namespace_names
    ]


def filter_monitored_namespaces(
    cluster_namespaces: set[api.NamespaceName],
    namespace_include_patterns: Sequence[str],
    namespace_exclude_patterns: Sequence[str],
) -> set[api.NamespaceName]:
    """Filter Kubernetes namespaces based on the provided patterns

    Examples:
        >>> filter_monitored_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar")}, ["foo"], [])
        {'foo'}

        >>> filter_monitored_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar")}, [], ["foo"])
        {'bar'}

        >>> sorted(filter_monitored_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar"),
        ... api.NamespaceName("man")}, ["foo", "bar"], []))
        ['bar', 'foo']

    """
    if namespace_include_patterns:
        LOGGER.debug("Filtering for included namespaces")
        return _filter_namespaces(cluster_namespaces, namespace_include_patterns)

    if namespace_exclude_patterns:
        LOGGER.debug("Filtering for namespaces based on excluded patterns")
        return cluster_namespaces - _filter_namespaces(
            cluster_namespaces, namespace_exclude_patterns
        )

    return cluster_namespaces


def _filter_namespaces(
    kubernetes_namespaces: set[api.NamespaceName], re_patterns: Sequence[str]
) -> set[api.NamespaceName]:
    """Filter namespaces based on the provided regular expression patterns

    Examples:
         >>> sorted(_filter_namespaces({api.NamespaceName("foo"), api.NamespaceName("bar"),
         ... api.NamespaceName("man")}, ["foo", "man"]))
         ['foo', 'man']
    """
    return {
        namespace
        for namespace in kubernetes_namespaces
        if any_match_from_list_of_infix_patterns(re_patterns, namespace)
    }


def _names_of_running_pods(
    kube_object: Node | Deployment | DaemonSet | StatefulSet,
) -> Sequence[PodLookupName]:
    # TODO: This function should really be simple enough to allow a doctest.
    # However, due to the way kube_object classes are constructed (e.g., see
    # api_to_agent_daemonset) this is currently not possible. If we improve
    # this function to use a PodOwner method instead, we can side-step these
    # issues.
    running_pods = filter_pods_by_phase(kube_object.pods, api.Phase.RUNNING)
    return list(map(pod_lookup_from_api_pod, running_pods))


def determine_pods_to_host(
    monitored_objects: Sequence[MonitoredObject],
    composed_entities: ComposedEntities,
    monitored_namespaces: set[api.NamespaceName],
    api_pods: Sequence[api.Pod],
    resource_quotas: Sequence[api.ResourceQuota],
    monitored_api_namespaces: Sequence[api.Namespace],
    api_cron_jobs: Sequence[api.CronJob],
    piggyback_formatter: PiggybackFormatter,
) -> PodsToHost:
    piggybacks: list[Piggyback] = []
    namespace_piggies = []
    if MonitoredObject.namespaces in monitored_objects:
        for api_namespace in monitored_api_namespaces:
            namespace_api_pods = filter_pods_by_phase(
                filter_pods_by_namespace(api_pods, namespace_name(api_namespace)),
                api.Phase.RUNNING,
            )
            resource_quota = namespace_handler.filter_matching_namespace_resource_quota(
                namespace_name(api_namespace), resource_quotas
            )
            if resource_quota is not None:
                resource_quota_pod_names = [
                    pod_lookup_from_api_pod(pod)
                    for pod in namespace_handler.filter_pods_by_resource_quota_criteria(
                        namespace_api_pods, resource_quota
                    )
                ]
            else:
                resource_quota_pod_names = []

            piggyback_name = piggyback_formatter(api_namespace)
            piggybacks.append(
                Piggyback(
                    piggyback=piggyback_name,
                    pod_names=[pod_lookup_from_api_pod(pod) for pod in namespace_api_pods],
                )
            )
            namespace_piggies.append(
                Piggyback(
                    piggyback=piggyback_name,
                    pod_names=resource_quota_pod_names,
                )
            )
    # TODO: write_object_sections_based_on_performance_pods is the equivalent
    # function based solely on api.Pod rather than class Pod. All objects relying
    # on write_sections_based_on_performance_pods should be refactored to use the
    # other function similar to namespaces
    if MonitoredObject.pods in monitored_objects:
        monitored_pods = kube_objects_from_namespaces(
            filter_pods_by_phase(api_pods, api.Phase.RUNNING),
            monitored_namespaces,
        )
        if MonitoredObject.cronjobs_pods not in monitored_objects:
            cronjob_pod_uids = {uid for cronjob in api_cron_jobs for uid in cronjob.pod_uids}
            monitored_pods = [pod for pod in monitored_pods if pod.uid not in cronjob_pod_uids]
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(pod),
                pod_names=[pod_lookup_from_api_pod(pod)],
            )
            for pod in monitored_pods
        )
    if MonitoredObject.nodes in monitored_objects:
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(node),
                pod_names=names,
            )
            for node in composed_entities.nodes
            if (names := _names_of_running_pods(node))
        )
    name_type_objects: Sequence[
        tuple[str, MonitoredObject, Sequence[Deployment | DaemonSet | StatefulSet]]
    ] = [
        ("deployment", MonitoredObject.deployments, composed_entities.deployments),
        ("statefulset", MonitoredObject.statefulsets, composed_entities.statefulsets),
        ("daemonset", MonitoredObject.daemonsets, composed_entities.daemonsets),
    ]
    for _object_type_name, object_type, objects in name_type_objects:
        if object_type in monitored_objects:
            piggybacks.extend(
                Piggyback(
                    piggyback=piggyback_formatter(k),
                    pod_names=names,
                )
                for k in kube_objects_from_namespaces(objects, monitored_namespaces)
                if (names := _names_of_running_pods(k))
            )
    piggybacks.append(
        Piggyback(
            piggyback="",
            pod_names=list(
                map(
                    pod_lookup_from_api_pod,
                    filter_pods_by_phase(
                        composed_entities.cluster.aggregation_pods, api.Phase.RUNNING
                    ),
                )
            ),
        )
    )
    if MonitoredObject.cronjobs in monitored_objects:
        piggybacks.extend(
            Piggyback(
                piggyback=piggyback_formatter(k),
                pod_names=[
                    pod_lookup_from_api_pod(pod)
                    for pod in filter_pods_by_phase(
                        filter_pods_by_cron_job(api_pods, k),
                        api.Phase.RUNNING,
                    )
                ],
            )
            for k in api_cron_jobs
        )
    return PodsToHost(
        piggybacks=piggybacks,
        namespace_piggies=namespace_piggies,
    )


def _identify_unsupported_node_collector_components(
    nodes: Sequence[section.NodeMetadata], supported_max_major_version: int
) -> Sequence[str]:
    invalid_nodes = []
    for api_node in nodes:
        unsupported_components = [
            f"{component.collector_type.value}: {component.checkmk_kube_agent.project_version}"
            for component in api_node.components.values()
            if not _supported_cluster_collector_major_version(
                component.checkmk_kube_agent.project_version,
                supported_max_major_version=supported_max_major_version,
            )
        ]
        if unsupported_components:
            invalid_nodes.append(f"{api_node.name} ({', '.join(unsupported_components)})")
    return invalid_nodes


def _group_metadata_by_node(
    node_collectors_metadata: Sequence[section.NodeCollectorMetadata],
) -> Sequence[section.NodeMetadata]:
    nodes_components: dict[section.NodeName, dict[str, section.NodeComponent]] = {}
    for node_collector in node_collectors_metadata:
        components = nodes_components.setdefault(node_collector.node, {})

        for component, version in node_collector.components.model_dump().items():
            if version is not None:
                components[component] = section.NodeComponent(
                    collector_type=node_collector.collector_type,
                    checkmk_kube_agent=node_collector.checkmk_kube_agent,
                    name=component,
                    version=version,
                )

    return [
        section.NodeMetadata(name=node_name, components=nodes_components[node_name])
        for node_name in {node_collector.node for node_collector in node_collectors_metadata}
    ]


def write_cluster_collector_info_section(
    processing_log: section.CollectorHandlerLog,
    cluster_collector: section.ClusterCollectorMetadata | None = None,
    node_collectors_metadata: Sequence[section.NodeMetadata] | None = None,
) -> None:
    section_content = section.CollectorComponentsMetadata(
        processing_log=processing_log,
        cluster_collector=cluster_collector,
        nodes=node_collectors_metadata,
    ).model_dump_json()
    sys.stdout.write("<<<kube_collector_metadata_v1:sep(0)>>>\n")
    sys.stdout.write(f"{section_content}\n")


class CollectorHandlingException(Exception):
    # This exception is used as report medium for the Cluster Collector service
    def __init__(self, title: str, detail: str) -> None:
        self.title = title
        self.detail = detail
        super().__init__()

    def __str__(self) -> str:
        return f"{self.title}: {self.detail}" if self.detail else self.title

    def to_section(self) -> section.CollectorHandlerLog:
        return section.CollectorHandlerLog(
            status=section.CollectorState.ERROR,
            title=self.title,
            detail=self.detail,
        )


def cluster_piggyback_formatter(
    cluster_name: str, object_type: str, obj_namespaced_name: str
) -> str:
    return f"{object_type}_{cluster_name}_{obj_namespaced_name}"


def piggyback_formatter_with_cluster_name(
    cluster_name: str,
    kube_object: PB_KUBE_OBJECT,
) -> str:
    match kube_object:
        case Cluster():
            return ""
        case Node():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="node",
                obj_namespaced_name=kube_object.metadata.name,
            )
        case Deployment() | DaemonSet() | StatefulSet():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type=kube_object.type_,
                obj_namespaced_name=namespaced_name_from_metadata(kube_object.metadata),
            )
        case api.Namespace():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="namespace",
                obj_namespaced_name=namespace_name(kube_object),
            )
        case api.CronJob():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="cronjob",
                obj_namespaced_name=namespaced_name_from_metadata(kube_object.metadata),
            )
        case api.Pod():
            return cluster_piggyback_formatter(
                cluster_name,
                object_type="pod",
                obj_namespaced_name=namespaced_name_from_metadata(kube_object.metadata),
            )


def _collect_api_data(
    token: Secret[str], api_session_config: query.APISessionConfig, query_kubelet_endpoints: bool
) -> APIData:
    LOGGER.info("Collecting API data")
    try:
        return from_kubernetes(
            token,
            api_session_config,
            LOGGER,
            query_kubelet_endpoints,
        )
    except urllib3.exceptions.MaxRetryError as e:
        raise ClusterConnectionError(
            f"Failed to establish a connection to {e.pool.host}:{e.pool.port} at URL {e.url}"
        ) from e
    except requests.RequestException as e:
        if e.request is not None:
            raise ClusterConnectionError(
                f"Failed to establish a connection at URL {e.request.url} "
            ) from e
        raise ClusterConnectionError("Failed to establish a connection.") from e


def _write_sections_based_on_api_data(
    piggyback_formatter: Callable[[PB_KUBE_OBJECT], str],
    arguments: argparse.Namespace,
    checkmk_host_settings: CheckmkHostSettings,
    composed_entities: ComposedEntities,
    monitored_namespace_names: set[api.NamespaceName],
    monitored_api_namespaces: Sequence[api.Namespace],
    api_data: APIData,
) -> None:
    LOGGER.info("Write cluster sections based on API data")
    common.write_sections(
        cluster_handler.create_api_sections(composed_entities.cluster, arguments.cluster)
    )

    namespace_grouped_api_pvcs = group_parsed_pvcs_by_namespace(api_data.persistent_volume_claims)

    api_persistent_volumes = {
        pv.metadata.name: section.PersistentVolume(name=pv.metadata.name, spec=pv.spec)
        for pv in api_data.persistent_volumes
    }
    namespaced_grouped_attached_volumes = group_serialized_volumes_by_namespace(
        serialize_attached_volumes_from_kubelet_metrics(
            filter_kubelet_volume_metrics(api_data.kubelet_open_metrics)
        )
    )
    if MonitoredObject.nodes in arguments.monitored_objects:
        LOGGER.info("Write nodes sections based on API data")
        for api_node in composed_entities.nodes:
            sections = node_handler.create_api_sections(
                api_node,
                host_settings=checkmk_host_settings,
                piggyback_name=piggyback_formatter(api_node),
            )
            common.write_sections(sections)

    if MonitoredObject.deployments in arguments.monitored_objects:
        LOGGER.info("Write deployments sections based on API data")
        for api_deployment in kube_objects_from_namespaces(
            composed_entities.deployments, monitored_namespace_names
        ):
            deployment_piggyback_name = piggyback_formatter(api_deployment)
            sections = deployment_handler.create_api_sections(
                api_deployment,
                host_settings=checkmk_host_settings,
                piggyback_name=deployment_piggyback_name,
            )
            if MonitoredObject.pvcs in arguments.monitored_objects:
                deployment_namespace = kube_object_namespace_name(api_deployment)
                sections = chain(
                    sections,
                    create_pvc_sections(
                        piggyback_name=deployment_piggyback_name,
                        attached_pvc_names=attached_pvc_names_from_pods(api_deployment.pods),
                        api_pvcs=namespace_grouped_api_pvcs.get(deployment_namespace, {}),
                        api_pvs=api_persistent_volumes,
                        attached_volumes=namespaced_grouped_attached_volumes.get(
                            deployment_namespace, {}
                        ),
                    ),
                )
            common.write_sections(sections)

    if MonitoredObject.namespaces in arguments.monitored_objects:
        LOGGER.info("Write namespaces sections based on API data")
        for api_namespace in monitored_api_namespaces:
            namespace_piggyback_name = piggyback_formatter(api_namespace)
            api_pods_from_namespace = filter_pods_by_namespace(
                api_data.pods, namespace_name(api_namespace)
            )
            namespace_sections = namespace_handler.create_namespace_api_sections(
                api_namespace,
                api_pods_from_namespace,
                host_settings=checkmk_host_settings,
                piggyback_name=namespace_piggyback_name,
            )
            if (
                api_resource_quota := namespace_handler.filter_matching_namespace_resource_quota(
                    namespace_name(api_namespace), api_data.resource_quotas
                )
            ) is not None:
                namespace_sections = chain(
                    namespace_sections,
                    namespace_handler.create_resource_quota_api_sections(
                        api_resource_quota, piggyback_name=namespace_piggyback_name
                    ),
                )
            common.write_sections(namespace_sections)

    if MonitoredObject.daemonsets in arguments.monitored_objects:
        LOGGER.info("Write daemon sets sections based on API data")
        for api_daemonset in kube_objects_from_namespaces(
            composed_entities.daemonsets, monitored_namespace_names
        ):
            daemonset_piggyback_name = piggyback_formatter(api_daemonset)
            daemonset_sections = daemonset_handler.create_api_sections(
                api_daemonset,
                host_settings=checkmk_host_settings,
                piggyback_name=daemonset_piggyback_name,
            )
            if MonitoredObject.pvcs in arguments.monitored_objects:
                daemonset_namespace = kube_object_namespace_name(api_daemonset)
                daemonset_sections = chain(
                    daemonset_sections,
                    create_pvc_sections(
                        piggyback_name=daemonset_piggyback_name,
                        attached_pvc_names=attached_pvc_names_from_pods(api_daemonset.pods),
                        api_pvcs=namespace_grouped_api_pvcs.get(daemonset_namespace, {}),
                        api_pvs=api_persistent_volumes,
                        attached_volumes=namespaced_grouped_attached_volumes.get(
                            daemonset_namespace, {}
                        ),
                    ),
                )
            common.write_sections(daemonset_sections)

    if MonitoredObject.statefulsets in arguments.monitored_objects:
        LOGGER.info("Write StatefulSets sections based on API data")
        for api_statefulset in kube_objects_from_namespaces(
            composed_entities.statefulsets, monitored_namespace_names
        ):
            statefulset_piggyback_name = piggyback_formatter(api_statefulset)
            statefulset_sections = statefulset_handler.create_api_sections(
                api_statefulset,
                host_settings=checkmk_host_settings,
                piggyback_name=statefulset_piggyback_name,
            )
            if MonitoredObject.pvcs in arguments.monitored_objects:
                statefulset_namespace = kube_object_namespace_name(api_statefulset)
                statefulset_sections = chain(
                    statefulset_sections,
                    create_pvc_sections(
                        piggyback_name=statefulset_piggyback_name,
                        attached_pvc_names=attached_pvc_names_from_pods(api_statefulset.pods),
                        api_pvcs=namespace_grouped_api_pvcs.get(statefulset_namespace, {}),
                        api_pvs=api_persistent_volumes,
                        attached_volumes=namespaced_grouped_attached_volumes.get(
                            statefulset_namespace, {}
                        ),
                    ),
                )
            common.write_sections(statefulset_sections)

    api_cron_job_pods = [
        api_pod
        for cron_job in api_data.cron_jobs
        for api_pod in api_data.pods
        if api_pod.uid in cron_job.pod_uids
    ]
    if MonitoredObject.cronjobs in arguments.monitored_objects:
        api_jobs = {job.uid: job for job in api_data.jobs}
        for api_cron_job in kube_objects_from_namespaces(
            api_data.cron_jobs, monitored_namespace_names
        ):
            sections = cronjob_handler.create_api_sections(
                api_cron_job,
                filter_pods_by_cron_job(api_cron_job_pods, api_cron_job),
                sorted(
                    [api_jobs[uid] for uid in api_cron_job.job_uids],
                    key=lambda job: job.metadata.creation_timestamp,
                ),
                host_settings=checkmk_host_settings,
                piggyback_name=piggyback_formatter(api_cron_job),
            )
            common.write_sections(sections)

    if MonitoredObject.pods in arguments.monitored_objects:
        LOGGER.info("Write pods sections based on API data")
        pods_in_relevant_namespaces = kube_objects_from_namespaces(
            api_data.pods, monitored_namespace_names
        )
        if MonitoredObject.cronjobs_pods in arguments.monitored_objects:
            monitored_pods = pods_in_relevant_namespaces
        else:
            cronjob_pod_ids = {pod_lookup_from_api_pod(pod) for pod in api_cron_job_pods}
            monitored_pods = [
                pod
                for pod in pods_in_relevant_namespaces
                if pod_lookup_from_api_pod(pod) not in cronjob_pod_ids
            ]

        for pod in monitored_pods:
            pod_piggyback_name = piggyback_formatter(pod)
            sections = pod_handler.create_api_sections(
                pod,
                checkmk_host_settings=checkmk_host_settings,
                piggyback_name=pod_piggyback_name,
            )

            if MonitoredObject.pvcs in arguments.monitored_objects:
                sections = chain(
                    sections,
                    create_pvc_sections(
                        piggyback_name=pod_piggyback_name,
                        attached_pvc_names=list(pod_attached_persistent_volume_claim_names(pod)),
                        api_pvcs=namespace_grouped_api_pvcs.get(
                            kube_object_namespace_name(pod), {}
                        ),
                        api_pvs=api_persistent_volumes,
                        attached_volumes=namespaced_grouped_attached_volumes.get(
                            kube_object_namespace_name(pod), {}
                        ),
                    ),
                )
            common.write_sections(sections)


def _create_metadata_based_cluster_collector(
    debug: bool, token: Secret[str], usage_config: query.CollectorSessionConfig
) -> (
    tuple[section.ClusterCollectorMetadata, Sequence[section.NodeMetadata]]
    | CollectorHandlingException
):
    try:
        metadata = request_cluster_collector(
            token,
            query.CollectorPath.metadata,
            usage_config,
            section.Metadata.model_validate_json,
        )

        supported_collector_version = 1
        if not _supported_cluster_collector_major_version(
            metadata.cluster_collector_metadata.checkmk_kube_agent.project_version,
            supported_max_major_version=supported_collector_version,
        ):
            raise CollectorHandlingException(
                title="Version Error",
                detail=f"Cluster Collector version {metadata.cluster_collector_metadata.checkmk_kube_agent.project_version} is not supported",
            )

        nodes_metadata = _group_metadata_by_node(metadata.node_collector_metadata)

        if invalid_nodes := _identify_unsupported_node_collector_components(
            nodes_metadata,
            supported_max_major_version=supported_collector_version,
        ):
            raise CollectorHandlingException(
                title="Version Error",
                detail=f"Following Nodes have unsupported components and should be "
                f"downgraded: {', '.join(invalid_nodes)}",
            )
        return metadata.cluster_collector_metadata, nodes_metadata
    except CollectorHandlingException as e:
        if debug:
            raise
        return e


def _create_sections_based_on_container_metrics(
    debug: bool,
    cluster_name: str,
    pods_to_host: PodsToHost,
    token: Secret[str],
    usage_config: query.CollectorSessionConfig,
) -> section.CollectorHandlerLog:
    try:
        LOGGER.info("Collecting container metrics from cluster collector")
        container_metrics = request_cluster_collector(
            token,
            query.CollectorPath.container_metrics,
            usage_config,
            performance.parse_performance_metrics,
        )

        if not container_metrics:
            raise CollectorHandlingException(
                title="No data",
                detail="No container metrics were collected from the cluster collector",
            )

        try:
            collector_selectors = performance.create_selectors(
                cluster_name=cluster_name,
                container_metrics=container_metrics,
            )
        except Exception as e:
            raise CollectorHandlingException(
                title="Processing Error",
                detail="Successfully queried and processed container metrics, but "
                "an error occurred while processing the data",
            ) from e

        try:
            common.write_sections(
                common.create_sections(*collector_selectors, pods_to_host=pods_to_host)
            )

        except Exception as e:
            raise CollectorHandlingException(
                title="Sections write out Error",
                detail="Metrics were successfully processed but Checkmk sections could not "
                "be written out",
            ) from e
    except CollectorHandlingException as e:
        if debug:
            raise
        return e.to_section()

    # Log when successfully queried and processed the metrics
    return section.CollectorHandlerLog(
        status=section.CollectorState.OK,
        title="Processed successfully",
        detail="Successfully queried and processed container metrics",
    )


def _create_sections_based_on_machine_section(
    debug: bool,
    monitor_nodes: bool,
    composed_entities: ComposedEntities,
    piggyback_formatter: PiggybackFormatter,
    token: Secret[str],
    usage_config: query.CollectorSessionConfig,
) -> section.CollectorHandlerLog:
    try:
        LOGGER.info("Collecting machine sections from cluster collector")
        machine_sections = request_cluster_collector(
            token,
            query.CollectorPath.machine_sections,
            usage_config,
            _parse_raw_metrics,
        )

        if not machine_sections:
            raise CollectorHandlingException(
                title="No data",
                detail="No machine sections were collected from the cluster collector",
            )

        if monitor_nodes:
            try:
                write_machine_sections(
                    composed_entities,
                    {s["node_name"]: s["sections"] for s in machine_sections},
                    piggyback_formatter,
                )
            except Exception as e:
                raise CollectorHandlingException(
                    title="Sections write out Error",
                    detail="Metrics were successfully processed but Checkmk sections could "
                    "not be written out",
                ) from e
    except CollectorHandlingException as e:
        if debug:
            raise
        return e.to_section()

    # Log when successfully queried and processed the metrics
    return section.CollectorHandlerLog(
        status=section.CollectorState.OK,
        title="Processed successfully",
        detail="Machine sections queried and processed successfully",
    )


def _main(arguments: argparse.Namespace, checkmk_host_settings: CheckmkHostSettings) -> int:
    token = resolve_secret_option(arguments, TOKEN_OPTION)
    client_config = query.APISessionConfig.model_validate(arguments.__dict__)

    try:
        api_data = _collect_api_data(
            token, client_config, MonitoredObject.pvcs in arguments.monitored_objects
        )
    except () if arguments.debug else (Exception,) as e:
        sys.stderr.write(f"{str(e).replace('\n', '')}\n")
        return 1

    # Namespaces are handled independently from the cluster object in order to improve
    # testability. The long term goal is to remove all objects from the cluster object
    composed_entities = ComposedEntities.from_api_resources(
        excluded_node_roles=arguments.roles or [], api_data=api_data
    )
    piggyback_formatter = lambda kube_obj: piggyback_formatter_with_cluster_name(
        arguments.cluster, kube_obj
    )
    monitored_namespace_names = filter_monitored_namespaces(
        {namespace_name(namespace) for namespace in api_data.namespaces},
        arguments.namespace_include_patterns,
        arguments.namespace_exclude_patterns,
    )
    # Namespaces are handled differently to other objects. Namespace piggyback hosts
    # should only be created if at least one running or pending pod is found in the
    # namespace.
    running_pending_pods = [
        pod for pod in api_data.pods if pod.status.phase in [api.Phase.RUNNING, api.Phase.PENDING]
    ]
    namespacenames_running_pending_pods = {
        kube_object_namespace_name(pod) for pod in running_pending_pods
    }
    monitored_api_namespaces = namespaces_from_namespacenames(
        api_data.namespaces,
        monitored_namespace_names.intersection(namespacenames_running_pending_pods),
    )

    _write_sections_based_on_api_data(
        piggyback_formatter,
        arguments,
        checkmk_host_settings,
        composed_entities,
        monitored_namespace_names,
        monitored_api_namespaces,
        api_data,
    )

    usage_config = query.parse_session_config(arguments)

    # Skip machine & container sections when cluster agent endpoint not configured
    if isinstance(usage_config, query.NoUsageConfig):
        return 0

    pods_to_host = determine_pods_to_host(
        composed_entities=composed_entities,
        monitored_objects=arguments.monitored_objects,
        monitored_namespaces=monitored_namespace_names,
        api_pods=api_data.pods,
        resource_quotas=api_data.resource_quotas,
        api_cron_jobs=api_data.cron_jobs,
        monitored_api_namespaces=monitored_api_namespaces,
        piggyback_formatter=piggyback_formatter,
    )

    if isinstance(usage_config, query.PrometheusSessionConfig):
        cpu, memory = query.send_requests(
            token,
            usage_config,
            [
                query.Query.sum_rate_container_cpu_usage_seconds_total,
                query.Query.sum_container_memory_working_set_bytes,
            ],
            logger=LOGGER,
        )

        common.write_sections(
            [prometheus_section.debug_section(usage_config.query_url(), cpu, memory)]
        )

        if all(not isinstance(response[1], ResponseSuccess) for response in (cpu, memory)):
            LOGGER.debug("Prometheus queries failed. Skipping generation of 'machine_sections'")
            return 0

        prometheus_selectors = prometheus_section.create_selectors(cpu[1], memory[1])
        common.write_sections(
            common.create_sections(*prometheus_selectors, pods_to_host=pods_to_host)
        )
        write_machine_sections(
            composed_entities,
            machine_sections=prometheus_section.machine_sections(token, usage_config),
            piggyback_formatter=piggyback_formatter,
        )
        return 0

    assert isinstance(usage_config, query.CollectorSessionConfig)

    # Handling of any of the cluster components should not crash the special agent as this
    # would discard all the API data. Special Agent failures of the Cluster Collector
    # components will not be highlighted in the usual Checkmk service but in a separate
    # service
    metadata_or_err = _create_metadata_based_cluster_collector(arguments.debug, token, usage_config)
    if isinstance(metadata_or_err, CollectorHandlingException):
        write_cluster_collector_info_section(processing_log=metadata_or_err.to_section())
        return 0
    cluster_collector_metadata, nodes_metadata = metadata_or_err
    write_cluster_collector_info_section(
        processing_log=section.CollectorHandlerLog(
            status=section.CollectorState.OK, title="Retrieved successfully"
        ),
        cluster_collector=cluster_collector_metadata,
        node_collectors_metadata=nodes_metadata,
    )

    collector_container_log = _create_sections_based_on_container_metrics(
        arguments.debug,
        arguments.cluster,
        pods_to_host,
        token,
        usage_config,
    )

    collector_machine_log = _create_sections_based_on_machine_section(
        arguments.debug,
        MonitoredObject.nodes in arguments.monitored_objects,
        composed_entities,
        piggyback_formatter,
        token,
        usage_config,
    )

    section_content = section.CollectorProcessingLogs(
        container=collector_container_log,
        machine=collector_machine_log,
    ).model_dump_json()
    sys.stdout.write("<<<kube_collector_processing_logs_v1:sep(0)>>>\n")
    sys.stdout.write(f"{section_content}\n")
    return 0


def _main_with_setup(
    arguments: argparse.Namespace, checkmk_host_settings: CheckmkHostSettings
) -> int:
    setup_logging(arguments.verbose)
    LOGGER.debug("parsed arguments: %s\n", arguments)

    with Profile(profile_file=arguments.profile) if arguments.profile else nullcontext():
        return _main(arguments, checkmk_host_settings)


@report_agent_crashes(AGENT_NAME, __VERSION__)
def main(args: list[str] | None = None) -> int:
    if args is None:
        args = sys.argv[1:]
    arguments = parse_arguments(args)
    checkmk_host_settings = CheckmkHostSettings(
        cluster_name=arguments.cluster,
        kubernetes_cluster_hostname=arguments.kubernetes_cluster_hostname,
        annotation_key_pattern=arguments.annotation_key_pattern,
    )

    return _main_with_setup(arguments, checkmk_host_settings)


if __name__ == "__main__":
    sys.exit(main())
