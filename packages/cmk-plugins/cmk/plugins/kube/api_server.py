#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

import contextlib
import itertools
import json
import logging
import re
import time
import typing
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pydantic
import requests
from kubernetes.client import (  # type: ignore[attr-defined]
    # https://github.com/kubernetes-client/python/issues/2033
    ApiClient,
    V1CronJob,
    V1DaemonSet,
    V1Deployment,
    V1Job,
    V1Namespace,
    V1PersistentVolume,
    V1PersistentVolumeClaim,
    V1Pod,
    V1ReplicaSet,
    V1ResourceQuota,
)

from cmk.password_store.v1_unstable import Secret
from cmk.plugins.kube import query
from cmk.plugins.kube.controllers import ControllerGraph
from cmk.plugins.kube.schemata import api
from cmk.plugins.kube.transform import (
    cron_job_from_client,
    daemonset_from_client,
    deployment_from_client,
    job_from_client,
    namespace_from_client,
    parse_object_to_owners,
    persistent_volume_claim_from_client,
    pod_from_client,
    resource_quota_from_client,
)
from cmk.plugins.kube.transform_any import parse_open_metric_samples
from cmk.plugins.kube.transform_json import (
    dependent_object_uid_from_json,
    JSONNodeList,
    JSONStatefulSetList,
    node_list_from_json,
    statefulset_from_json,
)

LOGGER = logging.getLogger()
VERSION_MATCH_RE = re.compile(r"\s*v?([0-9]+(?:\.[0-9]+)*).*")
SUPPORTED_VERSIONS = [(1, 26), (1, 27), (1, 28), (1, 29), (1, 30), (1, 31)]
# PM decision: LOWEST_FUNCTIONING_VERSION is incremented, if an issue is reported by a customer.
# Otherwise, we try not change anything in monitoring (despite lack of support).
LOWEST_FUNCTIONING_VERSION = (1, 21)
SUPPORTED_VERSIONS_DISPLAY = ", ".join(f"v{major}.{minor}" for major, minor in SUPPORTED_VERSIONS)


class FakeResponse:
    def __init__(self, response: requests.Response):
        self.data: str = response.text


class Deserializer:
    def __init__(self) -> None:
        self._api_client = ApiClient()

    def run(self, response_type: str, data: requests.Response) -> typing.Any:
        return self._api_client.deserialize(FakeResponse(data), response_type)


class ClientAPI:
    def __init__(
        self,
        client_config: query.APISessionConfig,
        request_client: requests.Session,
        deserizalizer: Deserializer,
    ) -> None:
        self._config = client_config
        self._client = request_client
        self._deserializer = deserizalizer


class ClientBatchAPI(ClientAPI):
    def query_raw_cron_jobs(self) -> Sequence[V1CronJob]:
        request = requests.Request("GET", self._config.url("/apis/batch/v1/cronjobs"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1CronJobList", response).items

    def query_raw_jobs(self) -> Sequence[V1Job]:
        request = requests.Request("GET", self._config.url("/apis/batch/v1/jobs"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1JobList", response).items


class ClientCoreAPI(ClientAPI):
    def query_raw_pods(self) -> Sequence[V1Pod]:
        request = requests.Request("GET", self._config.url("/api/v1/pods"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1PodList", response).items

    def query_raw_resource_quotas(self) -> Sequence[V1ResourceQuota]:
        request = requests.Request("GET", self._config.url("/api/v1/resourcequotas"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1ResourceQuotaList", response).items

    def query_raw_namespaces(self) -> Sequence[V1Namespace]:
        request = requests.Request("GET", self._config.url("/api/v1/namespaces"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1NamespaceList", response).items

    def query_persistent_volume_claims(self) -> Sequence[V1PersistentVolumeClaim]:
        request = requests.Request("GET", self._config.url("/api/v1/persistentvolumeclaims"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1PersistentVolumeClaimList", response).items

    def query_persistent_volumes(self) -> Sequence[V1PersistentVolume]:
        request = requests.Request("GET", self._config.url("/api/v1/persistentvolumes"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1PersistentVolumeList", response).items


class ClientAppsAPI(ClientAPI):
    def query_raw_deployments(self) -> Sequence[V1Deployment]:
        request = requests.Request("GET", self._config.url("/apis/apps/v1/deployments"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1DeploymentList", response).items

    def query_raw_daemon_sets(self) -> Sequence[V1DaemonSet]:
        request = requests.Request("GET", self._config.url("/apis/apps/v1/daemonsets"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1DaemonSetList", response).items

    def query_raw_replica_sets(self) -> Sequence[V1ReplicaSet]:
        request = requests.Request("GET", self._config.url("/apis/apps/v1/replicasets"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1ReplicaSetList", response).items


class RawAPI:
    def __init__(
        self, client_config: query.APISessionConfig, request_client: requests.Session
    ) -> None:
        self._config = client_config
        self._client = request_client


def send_request(
    client_config: query.APISessionConfig,
    request_client: requests.Session,
    request: requests.Request,
) -> requests.Response:
    prepared_request = request_client.prepare_request(request)
    return request_client.send(prepared_request, timeout=client_config.requests_timeout())


class CoreAPI(RawAPI):
    """
    readyz and livez is not part of the OpenAPI doc, so we have to query it directly.
    """

    def query_raw_version(self) -> str:
        request = requests.Request("GET", self._config.url("/version"))
        return send_request(self._config, self._client, request).text

    def query_kubelet_metrics(self, node_names: Sequence[str]) -> Sequence[str]:
        result = []
        finish_time = time.time() + 30.0
        node_queue = list(node_names)
        while time.time() < finish_time and node_queue:
            node_name = node_queue.pop()
            request = requests.Request(
                "GET", self._config.url(f"/api/v1/nodes/{node_name}/proxy/metrics")
            )
            with contextlib.suppress(requests.RequestException):
                response = send_request(self._config, self._client, request)
                response.raise_for_status()
                result.append(response.text)
        return result

    def query_raw_nodes(self) -> JSONNodeList:
        request = requests.Request("GET", self._config.url("/api/v1/nodes"))
        return send_request(self._config, self._client, request).json()

    def query_api_health(self) -> api.APIHealth:
        # https://kubernetes.io/docs/reference/using-api/health-checks/
        return api.APIHealth(ready=self._get_healthz("/readyz"), live=self._get_healthz("/livez"))

    def query_kubelet_health(
        self, node_names: Sequence[str]
    ) -> Mapping[str, api.HealthZ | api.NodeConnectionError]:
        node_to_health: dict[str, api.HealthZ | api.NodeConnectionError] = {}
        for node_name in node_names:
            try:
                node_to_health[node_name] = self._get_healthz(
                    f"/api/v1/nodes/{node_name}/proxy/healthz"
                )
            except requests.RequestException as e:
                node_to_health[node_name] = api.NodeConnectionError(message=str(e))
        return node_to_health

    def _get_healthz(self, resource_path: str) -> api.HealthZ:
        request = requests.Request("GET", self._config.url(resource_path))
        response = send_request(self._config, self._client, request)
        return api.HealthZ(status_code=response.status_code, response=response.text)


class AppsAPI(RawAPI):
    def query_raw_statefulsets(self) -> JSONStatefulSetList:
        request = requests.Request("GET", self._config.url("/apis/apps/v1/statefulsets"))
        return send_request(self._config, self._client, request).json()


def _extract_sequence_based_identifier(git_version: str) -> str | None:
    """

    >>> _extract_sequence_based_identifier("v1.20.0")
    '1.20.0'
    >>> _extract_sequence_based_identifier("    v1.20.0")  # some white space is allowed
    '1.20.0'
    >>> _extract_sequence_based_identifier("v1.21.9-eks-0d102a7")  # flavors are ok, but discarded
    '1.21.9'
    >>> _extract_sequence_based_identifier("v1")  # sequences without minor are allowed
    '1'
    >>> _extract_sequence_based_identifier("v1.")  # even with a dot
    '1'
    >>> _extract_sequence_based_identifier("10")  # the v is optional
    '10'
    >>> _extract_sequence_based_identifier("1.2.3.4")  # the whole sequence is extracted, even if incompatible with the Kubernetes versioning scheme
    '1.2.3.4'
    >>> _extract_sequence_based_identifier("v1.2v3.4")  # extraction always starts at beginning
    '1.2'
    >>> _extract_sequence_based_identifier("")  # empty strings are not allowed

    >>> _extract_sequence_based_identifier("abc")  # nonesense is also not allowed

    >>> _extract_sequence_based_identifier("v   1.20.0")  # but only in specific cases

    >>> _extract_sequence_based_identifier("a1.20.0")  # v or whitespace are the only allowed letters at the start

    """
    version_match = VERSION_MATCH_RE.fullmatch(git_version)
    return None if version_match is None else version_match.group(1)


def decompose_git_version(
    git_version: api.GitVersion,
) -> api.KubernetesVersion | api.UnknownKubernetesVersion:
    # One might think that version_json["major"] and version_json["minor"] would be more suitable
    # than parsing major from GitVersion. Sadly, the minor version is not an integer, e.g. "21+".
    # The approach taken here is based on the `kubectl version`.
    # kubectl version uses `ParseSemantic` from
    # https://github.com/kubernetes/kubernetes/blob/master/staging/src/k8s.io/apimachinery/pkg/util/version/version.go
    identifier = _extract_sequence_based_identifier(git_version)
    if identifier is None:
        LOGGER.error(
            f"Could not parse version string '{git_version}', using regex from kubectl '{VERSION_MATCH_RE.pattern}'."
        )
        return api.UnknownKubernetesVersion(git_version=git_version)
    # Unlike kubectl, we do not explicitly handle cases where a component is non-numeric, since
    # this is impossible based on the regex matching done by `_extract_sequence_based_identifier`
    components = identifier.split(".")
    if len(components) < 2:
        LOGGER.error(
            msg=f"Could not parse version string '{git_version}', version '{identifier}' has no "
            "minor."
        )
        return api.UnknownKubernetesVersion(git_version=git_version)
    for component in components:
        if component.startswith("0") and component != "0":
            LOGGER.error(
                msg=f"Could not parse version string '{git_version}', a version component is "
                "zero-prefixed."
            )
            return api.UnknownKubernetesVersion(git_version=git_version)

    return api.KubernetesVersion(
        git_version=git_version,
        major=int(components[0]),
        minor=int(components[1]),
    )


class UnsupportedEndpointData(Exception):
    """Data retrieved from the endpoint cannot be parsed by Checkmk.

    This exception indicates that the agent was able to receive data, but an issue occurred, which
    makes it impossible to process the data.
    """


def version_from_json(
    raw_version: str,
) -> api.UnknownKubernetesVersion | api.KubernetesVersion:
    try:
        version_json = json.loads(raw_version)
    except Exception as e:
        LOGGER.error("Failed to parse /version endpoint response as JSON: %s", raw_version)
        raise UnsupportedEndpointData(
            "Unknown endpoint information at endpoint /version, HTTP(S) response was "
            f"'{raw_version.replace('\n', '')}'."
        ) from e
    if "gitVersion" not in version_json:
        LOGGER.error(
            "Data from endpoint /version did not have mandatory field 'gitVersion', HTTP(S) "
            "response was: %s",
            raw_version,
        )
        raise UnsupportedEndpointData(
            "Data from endpoint /version did not have mandatory field 'gitVersion', HTTP(S) "
            f"response was '{raw_version.replace('\n', '')}'."
        )

    return decompose_git_version(version_json["gitVersion"])


def _verify_version_support(version: api.KubernetesVersion | api.UnknownKubernetesVersion) -> None:
    if (
        isinstance(version, api.KubernetesVersion)
        and (version.major, version.minor) in SUPPORTED_VERSIONS
    ):
        return
    LOGGER.warning(
        msg=f"Unsupported Kubernetes version '{version.git_version}'. "
        f"Supported versions are {SUPPORTED_VERSIONS_DISPLAY}.",
    )
    if (
        isinstance(version, api.KubernetesVersion)
        and (version.major, version.minor) < LOWEST_FUNCTIONING_VERSION
    ):
        # The agent will always abort processing data, if the version is
        # known to be unsupported. If one does not abort data processing
        # for version 1.20 or below, then the agent will crash for sure.
        # E.g., it is possible that the agent succeeds in parsing version
        # 1.21 API data, if the following exception is not raised. However,
        # for 1.20 it will crash anyway with a less helpful message.
        raise UnsupportedEndpointData(
            f"Unsupported Kubernetes version '{version.git_version}'. "
            "Aborting processing API data. "
            f"Supported versions are {SUPPORTED_VERSIONS_DISPLAY}.",
        )
    LOGGER.warning(msg="Processing data is done on a best effort basis.")


@dataclass(frozen=True)
class APIData:
    cron_jobs: Sequence[api.CronJob]
    deployments: Sequence[api.Deployment]
    daemonsets: Sequence[api.DaemonSet]
    jobs: Sequence[api.Job]
    statefulsets: Sequence[api.StatefulSet]
    namespaces: Sequence[api.Namespace]
    nodes: Sequence[api.Node]
    pods: Sequence[api.Pod]
    persistent_volume_claims: Sequence[api.PersistentVolumeClaim]
    persistent_volumes: Sequence[api.PersistentVolume]
    kubelet_open_metrics: Sequence[api.OpenMetricSample]
    resource_quotas: Sequence[api.ResourceQuota]
    cluster_details: api.ClusterDetails


@dataclass(frozen=True)
class UnparsedAPIData:
    raw_jobs: Sequence[V1Job]
    raw_cron_jobs: Sequence[V1CronJob]
    raw_pods: Sequence[V1Pod]
    raw_nodes: JSONNodeList
    raw_namespaces: Sequence[V1Namespace]
    raw_resource_quotas: Sequence[V1ResourceQuota]
    raw_persistent_volume_claims: Sequence[V1PersistentVolumeClaim]
    raw_persistent_volumes: Sequence[V1PersistentVolume]
    raw_deployments: Sequence[V1Deployment]
    raw_daemonsets: Sequence[V1DaemonSet]
    raw_replica_sets: Sequence[V1ReplicaSet]
    node_to_kubelet_health: Mapping[str, api.HealthZ | api.NodeConnectionError]
    api_health: api.APIHealth
    raw_statefulsets: JSONStatefulSetList
    raw_kubelet_open_metrics_dumps: Sequence[str]


def query_raw_api_data_v2(
    core_api: CoreAPI,
    apps_api: AppsAPI,
    client_batch_api: ClientBatchAPI,
    client_core_api: ClientCoreAPI,
    client_apps_api: ClientAppsAPI,
    query_kubelet_endpoints: bool,
) -> UnparsedAPIData:
    raw_nodes = core_api.query_raw_nodes()
    node_names = [raw_node["metadata"]["name"] for raw_node in raw_nodes["items"]]
    return UnparsedAPIData(
        raw_jobs=client_batch_api.query_raw_jobs(),
        raw_cron_jobs=client_batch_api.query_raw_cron_jobs(),
        raw_pods=client_core_api.query_raw_pods(),
        raw_nodes=raw_nodes,
        raw_namespaces=client_core_api.query_raw_namespaces(),
        raw_resource_quotas=client_core_api.query_raw_resource_quotas(),
        raw_persistent_volume_claims=client_core_api.query_persistent_volume_claims(),
        raw_persistent_volumes=client_core_api.query_persistent_volumes(),
        raw_deployments=client_apps_api.query_raw_deployments(),
        raw_daemonsets=client_apps_api.query_raw_daemon_sets(),
        raw_statefulsets=apps_api.query_raw_statefulsets(),
        raw_replica_sets=client_apps_api.query_raw_replica_sets(),
        node_to_kubelet_health=core_api.query_kubelet_health(node_names),
        api_health=core_api.query_api_health(),
        raw_kubelet_open_metrics_dumps=(
            core_api.query_kubelet_metrics(node_names) if query_kubelet_endpoints else []
        ),
    )


def parse_api_data(
    raw_cron_jobs: Sequence[V1CronJob],
    raw_pods: Sequence[V1Pod],
    raw_jobs: Sequence[V1Job],
    raw_nodes: JSONNodeList,
    raw_namespaces: Sequence[V1Namespace],
    raw_resource_quotas: Sequence[V1ResourceQuota],
    raw_deployments: Sequence[V1Deployment],
    raw_daemonsets: Sequence[V1DaemonSet],
    raw_statefulsets: JSONStatefulSetList,
    raw_persistent_volume_claims: Sequence[V1PersistentVolumeClaim],
    raw_persistent_volumes: Sequence[V1PersistentVolume],
    node_to_kubelet_health: Mapping[str, api.HealthZ | api.NodeConnectionError],
    api_health: api.APIHealth,
    controller_graph: ControllerGraph,
    git_version: api.GitVersion,
    kubelet_open_metrics_dumps: Sequence[str],
) -> APIData:
    """Parses the Kubernetes API to the format used"""
    job_uids = {raw_job.metadata.uid for raw_job in raw_jobs}

    cron_jobs = [
        cron_job_from_client(
            raw_cron_job,
            pod_uids=controller_graph.pods_controlled_by(raw_cron_job.metadata.uid),
            job_uids=[
                api.JobUID(dependent_uid)
                for dependent_uid in controller_graph.dependents_owned_by(raw_cron_job.metadata.uid)
                if dependent_uid in job_uids
            ],
        )
        for raw_cron_job in raw_cron_jobs
    ]
    deployments = [
        deployment_from_client(
            raw_deployment,
            pod_uids=controller_graph.pods_controlled_by(raw_deployment.metadata.uid),
        )
        for raw_deployment in raw_deployments
    ]
    daemonsets = [
        daemonset_from_client(
            raw_daemonset, pod_uids=controller_graph.pods_controlled_by(raw_daemonset.metadata.uid)
        )
        for raw_daemonset in raw_daemonsets
    ]
    jobs = [
        job_from_client(
            raw_job,
            pod_uids=controller_graph.pods_controlled_by(raw_job.metadata.uid),
        )
        for raw_job in raw_jobs
    ]
    statefulsets = [
        statefulset_from_json(
            statefulset,
            controller_graph.pods_controlled_by(dependent_object_uid_from_json(statefulset)),
        )
        for statefulset in raw_statefulsets["items"]
    ]

    namespaces = [namespace_from_client(raw_namespace) for raw_namespace in raw_namespaces]
    nodes = node_list_from_json(raw_nodes, node_to_kubelet_health)
    pods = [
        pod_from_client(pod, controller_graph.pod_to_control_chain(pod.metadata.uid))
        for pod in raw_pods
    ]
    persistent_volume_claims = [
        persistent_volume_claim_from_client(pvc) for pvc in raw_persistent_volume_claims
    ]
    resource_quotas: Sequence[api.ResourceQuota] = [
        api_resource_quota
        for api_resource_quota in [
            resource_quota_from_client(resource_quota) for resource_quota in raw_resource_quotas
        ]
        if api_resource_quota is not None
    ]

    cluster_details = api.ClusterDetails(api_health=api_health, version=git_version)

    def _parse_obj_as(
        model: type[list[api.PersistentVolume]],
        expr: typing.Sequence[typing.Any],
    ) -> typing.Sequence[api.PersistentVolume]:
        adapter = pydantic.TypeAdapter(model)
        return adapter.validate_python(expr)

    return APIData(
        cron_jobs=cron_jobs,
        deployments=deployments,
        daemonsets=daemonsets,
        jobs=jobs,
        statefulsets=statefulsets,
        namespaces=namespaces,
        nodes=nodes,
        pods=pods,
        persistent_volume_claims=persistent_volume_claims,
        persistent_volumes=_parse_obj_as(list[api.PersistentVolume], raw_persistent_volumes),
        kubelet_open_metrics=[
            kubelet_metric_sample
            for dump in kubelet_open_metrics_dumps
            for kubelet_metric_sample in parse_open_metric_samples(dump)
        ],
        resource_quotas=resource_quotas,
        cluster_details=cluster_details,
    )


def create_api_data_v2(
    core_api: CoreAPI,
    apps_api: AppsAPI,
    client_batch_api: ClientBatchAPI,
    client_core_api: ClientCoreAPI,
    client_apps_api: ClientAppsAPI,
    git_version: api.GitVersion,
    query_kubelet_endpoints: bool,
) -> APIData:
    raw_api_data = query_raw_api_data_v2(
        core_api,
        apps_api,
        client_batch_api,
        client_core_api,
        client_apps_api,
        query_kubelet_endpoints,
    )
    object_to_owners = parse_object_to_owners(
        workload_resources_client=itertools.chain(
            raw_api_data.raw_deployments,
            raw_api_data.raw_daemonsets,
            raw_api_data.raw_replica_sets,
            raw_api_data.raw_cron_jobs,
            raw_api_data.raw_jobs,
            raw_api_data.raw_pods,
        ),
        workload_resources_json=raw_api_data.raw_statefulsets["items"],
    )
    controller_graph = ControllerGraph(raw_api_data.raw_pods, object_to_owners=object_to_owners)

    return parse_api_data(
        raw_api_data.raw_cron_jobs,
        raw_api_data.raw_pods,
        raw_api_data.raw_jobs,
        raw_api_data.raw_nodes,
        raw_api_data.raw_namespaces,
        raw_api_data.raw_resource_quotas,
        raw_api_data.raw_deployments,
        raw_api_data.raw_daemonsets,
        raw_api_data.raw_statefulsets,
        raw_api_data.raw_persistent_volume_claims,
        raw_api_data.raw_persistent_volumes,
        raw_api_data.node_to_kubelet_health,
        raw_api_data.api_health,
        controller_graph,
        git_version,
        kubelet_open_metrics_dumps=raw_api_data.raw_kubelet_open_metrics_dumps,
    )


def from_kubernetes(
    token: Secret[str],
    client_config: query.APISessionConfig,
    logger: logging.Logger,
    query_kubelet_endpoints: bool,
) -> APIData:
    """
    This function provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """
    deserizalizer = Deserializer()
    api_client_requests = query.make_api_client_requests(token, client_config, logger)
    client_batch_api = ClientBatchAPI(client_config, api_client_requests, deserizalizer)
    client_core_api = ClientCoreAPI(client_config, api_client_requests, deserizalizer)
    client_apps_api = ClientAppsAPI(client_config, api_client_requests, deserizalizer)

    core_api = CoreAPI(client_config, api_client_requests)
    apps_api = AppsAPI(client_config, api_client_requests)
    raw_version = core_api.query_raw_version()
    version = version_from_json(raw_version)
    _verify_version_support(version)

    return create_api_data_v2(
        core_api,
        apps_api,
        client_batch_api,
        client_core_api,
        client_apps_api,
        version.git_version,
        query_kubelet_endpoints,
    )
