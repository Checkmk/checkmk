#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes import query
from cmk.special_agents.utils_kubernetes.controllers import (
    map_controllers,
    map_controllers_top_to_down,
)
from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
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
from cmk.special_agents.utils_kubernetes.transform_any import parse_open_metric_samples
from cmk.special_agents.utils_kubernetes.transform_json import (
    JSONNodeList,
    JSONStatefulSetList,
    node_list_from_json,
    statefulset_list_from_json,
)

LOGGER = logging.getLogger()
VERSION_MATCH_RE = re.compile(r"\s*v?([0-9]+(?:\.[0-9]+)*).*")
SUPPORTED_VERSIONS = [(1, 24), (1, 25), (1, 26), (1, 27), (1, 28), (1, 29), (1, 30)]
# PM decision: LOWEST_FUNCTIONING_VERSION is incremented, if an issue is reported by a customer.
# Otherwise, we try not change anything in monitoring (despite lack of support).
LOWEST_FUNCTIONING_VERSION = (1, 21)
SUPPORTED_VERSIONS_DISPLAY = ", ".join(f"v{major}.{minor}" for major, minor in SUPPORTED_VERSIONS)


class FakeResponse:
    def __init__(self, response: requests.Response):
        self.data: str = response.text


class Deserializer:
    def __init__(self):
        self._api_client = client.ApiClient()

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
    def query_raw_cron_jobs(self) -> Sequence[client.V1CronJob]:
        request = requests.Request("GET", self._config.url("/apis/batch/v1/cronjobs"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1CronJobList", response).items

    def query_raw_jobs(self) -> Sequence[client.V1Job]:
        request = requests.Request("GET", self._config.url("/apis/batch/v1/jobs"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1JobList", response).items


class ClientCoreAPI(ClientAPI):
    def query_raw_pods(self) -> Sequence[client.V1Pod]:
        request = requests.Request("GET", self._config.url("/api/v1/pods"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1PodList", response).items

    def query_raw_resource_quotas(self) -> Sequence[client.V1ResourceQuota]:
        request = requests.Request("GET", self._config.url("/api/v1/resourcequotas"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1ResourceQuotaList", response).items

    def query_raw_namespaces(self):
        request = requests.Request("GET", self._config.url("/api/v1/namespaces"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1NamespaceList", response).items

    def query_persistent_volume_claims(
        self,
    ) -> Sequence[client.V1PersistentVolumeClaim]:
        request = requests.Request("GET", self._config.url("/api/v1/persistentvolumeclaims"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1PersistentVolumeClaimList", response).items

    def query_persistent_volumes(self):
        request = requests.Request("GET", self._config.url("/api/v1/persistentvolumes"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1PersistentVolumeList", response).items


class ClientAppsAPI(ClientAPI):
    def query_raw_deployments(self) -> Sequence[client.V1Deployment]:
        request = requests.Request("GET", self._config.url("/apis/apps/v1/deployments"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1DeploymentList", response).items

    def query_raw_daemon_sets(self) -> Sequence[client.V1DaemonSet]:
        request = requests.Request("GET", self._config.url("/apis/apps/v1/daemonsets"))
        response = send_request(self._config, self._client, request)
        return self._deserializer.run("V1DaemonSetList", response).items

    def query_raw_replica_sets(self) -> Sequence[client.V1ReplicaSet]:
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
    return request_client.send(
        prepared_request,
        timeout=client_config.requests_timeout(),
        **request_client.merge_environment_settings(
            url=request.url,
            proxies={},
            stream=None,
            verify=client_config.verify_cert_api,
            cert=None,
        ),
    )


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
    if version_match is None:
        LOGGER.error(
            msg=f"Could not parse version string '{git_version}', using regex from kubectl "
            f"'{VERSION_MATCH_RE.pattern}'."
        )
        return None
    return version_match.group(1)


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
        raise UnsupportedEndpointData(
            "Unknown endpoint information at endpoint /version, HTTP(S) response was "
            f"'{raw_version}'."
        ) from e
    if "gitVersion" not in version_json:
        raise UnsupportedEndpointData(
            "Data from endpoint /version did not have mandatory field 'gitVersion', HTTP(S) "
            f"response was '{raw_version}'."
        )

    return decompose_git_version(version_json["gitVersion"])


def _verify_version_support(
    version: api.KubernetesVersion | api.UnknownKubernetesVersion,
) -> None:
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
    raw_jobs: Sequence[client.V1Job]
    raw_cron_jobs: Sequence[client.V1CronJob]
    raw_pods: Sequence[client.V1Pod]
    raw_nodes: JSONNodeList
    raw_namespaces: Sequence[client.V1Namespace]
    raw_resource_quotas: Sequence[client.V1ResourceQuota]
    raw_persistent_volume_claims: Sequence[client.V1PersistentVolumeClaim]
    raw_persistent_volumes: Sequence[client.V1PersistentVolume]
    raw_deployments: Sequence[client.V1Deployment]
    raw_daemonsets: Sequence[client.V1DaemonSet]
    raw_replica_sets: Sequence[client.V1ReplicaSet]
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
    raw_cron_jobs: Sequence[client.V1CronJob],
    raw_pods: Sequence[client.V1Pod],
    raw_jobs: Sequence[client.V1Job],
    raw_nodes: JSONNodeList,
    raw_namespaces: Sequence[client.V1Namespace],
    raw_resource_quotas: Sequence[client.V1ResourceQuota],
    raw_deployments: Sequence[client.V1Deployment],
    raw_daemonsets: Sequence[client.V1DaemonSet],
    raw_statefulsets: JSONStatefulSetList,
    raw_persistent_volume_claims: Sequence[client.V1PersistentVolumeClaim],
    raw_persistent_volumes: Sequence[client.V1PersistentVolume],
    node_to_kubelet_health: Mapping[str, api.HealthZ | api.NodeConnectionError],
    api_health: api.APIHealth,
    controller_to_pods: Mapping[str, Sequence[api.PodUID]],
    pod_to_controllers: Mapping[api.PodUID, Sequence[api.Controller]],
    controllers_to_dependents: Mapping[str, Sequence[str]],
    git_version: api.GitVersion,
    kubelet_open_metrics_dumps: Sequence[str],
) -> APIData:
    """Parses the Kubernetes API to the format used"""
    job_uids = {raw_job.metadata.uid for raw_job in raw_jobs}
    pod_uids = {raw_pod.metadata.uid for raw_pod in raw_pods}

    cron_jobs = [
        cron_job_from_client(
            raw_cron_job,
            pod_uids=controller_to_pods.get(raw_cron_job.metadata.uid, []),
            job_uids=[
                api.JobUID(dependent_uid)
                for dependent_uid in controllers_to_dependents.get(raw_cron_job.metadata.uid, [])
                if dependent_uid in job_uids
            ],
        )
        for raw_cron_job in raw_cron_jobs
    ]
    deployments = [
        deployment_from_client(
            raw_deployment, controller_to_pods.get(raw_deployment.metadata.uid, [])
        )
        for raw_deployment in raw_deployments
    ]
    daemonsets = [
        daemonset_from_client(raw_daemonset, controller_to_pods.get(raw_daemonset.metadata.uid, []))
        for raw_daemonset in raw_daemonsets
    ]
    jobs = [
        job_from_client(
            raw_job,
            pod_uids=[
                api.PodUID(dependent_uid)
                for dependent_uid in controllers_to_dependents.get(raw_job.metadata.uid, [])
                if dependent_uid in pod_uids
            ],
        )
        for raw_job in raw_jobs
    ]
    statefulsets = statefulset_list_from_json(raw_statefulsets, controller_to_pods)
    namespaces = [namespace_from_client(raw_namespace) for raw_namespace in raw_namespaces]
    nodes = node_list_from_json(raw_nodes, node_to_kubelet_health)
    pods = [pod_from_client(pod, pod_to_controllers.get(pod.metadata.uid, [])) for pod in raw_pods]
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
    controller_to_pods, pod_to_controllers = map_controllers(
        raw_api_data.raw_pods,
        object_to_owners=object_to_owners,
    )

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
        controller_to_pods,
        pod_to_controllers,
        map_controllers_top_to_down(object_to_owners),
        git_version,
        kubelet_open_metrics_dumps=raw_api_data.raw_kubelet_open_metrics_dumps,
    )


def from_kubernetes(
    client_config: query.APISessionConfig,
    logger: logging.Logger,
    query_kubelet_endpoints: bool,
) -> APIData:
    """
    This function provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """
    deserizalizer = Deserializer()
    api_client_requests = query.make_api_client_requests(client_config, logger)
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
