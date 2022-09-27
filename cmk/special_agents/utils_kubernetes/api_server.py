#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import json
import logging
import re
from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
    cron_job_from_client,
    daemonset_from_client,
    dependent_object_owner_refererences_from_client,
    deployment_from_client,
    job_from_client,
    namespace_from_client,
    node_from_client,
    parse_object_to_owners,
    pod_from_client,
    resource_quota_from_client,
    statefulset_from_client,
)
from cmk.special_agents.utils_kubernetes.transform_json import (
    JSONStatefulSetList,
    statefulset_list_from_json,
)

LOGGER = logging.getLogger()
VERSION_MATCH_RE = re.compile(r"\s*v?([0-9]+(?:\.[0-9]+)*).*")
SUPPORTED_VERSIONS = [(1, 21), (1, 22), (1, 23)]
LOWEST_FUNCTIONING_VERSION = min(SUPPORTED_VERSIONS)
SUPPORTED_VERSIONS_DISPLAY = ", ".join(f"v{major}.{minor}" for major, minor in SUPPORTED_VERSIONS)


class BatchAPI:
    def __init__(self, api_client: client.ApiClient, timeout: tuple[int, int]) -> None:
        self.connection = client.BatchV1Api(api_client)
        self.timeout = timeout

    def query_raw_cron_jobs(self) -> Sequence[client.V1CronJob]:
        return self.connection.list_cron_job_for_all_namespaces(_request_timeout=self.timeout).items

    def query_raw_jobs(self) -> Sequence[client.V1Job]:
        return self.connection.list_job_for_all_namespaces(_request_timeout=self.timeout).items


class CoreAPI:
    def __init__(self, api_client: client.ApiClient, timeout: tuple[int, int]) -> None:
        self.connection = client.CoreV1Api(api_client)
        self.timeout = timeout

    def query_raw_nodes(self) -> Sequence[client.V1Node]:
        return self.connection.list_node(_request_timeout=self.timeout).items

    def query_raw_pods(self) -> Sequence[client.V1Pod]:
        return self.connection.list_pod_for_all_namespaces(_request_timeout=self.timeout).items

    def query_raw_resource_quotas(self) -> Sequence[client.V1ResourceQuota]:
        return self.connection.list_resource_quota_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def query_raw_namespaces(self):
        return self.connection.list_namespace(_request_timeout=self.timeout).items


class AppsAPI:
    def __init__(self, api_client: client.ApiClient, timeout: tuple[int, int]) -> None:
        self.connection = client.AppsV1Api(api_client)
        self.timeout = timeout

    def query_raw_deployments(self) -> Sequence[client.V1Deployment]:
        return self.connection.list_deployment_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def query_raw_daemon_sets(self) -> Sequence[client.V1DaemonSet]:
        return self.connection.list_daemon_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def query_raw_statefulsets(self) -> Sequence[client.V1StatefulSet]:
        return self.connection.list_stateful_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def query_raw_replica_sets(self) -> Sequence[client.V1ReplicaSet]:
        return self.connection.list_replica_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items


@dataclass
class RawAPIResponse:
    response: str
    status_code: int
    headers: Dict[str, str]


class RawAPI:
    """
    readyz and livez is not part of the OpenAPI doc, so we have to query it directly.
    """

    def __init__(self, api_client: client.ApiClient, timeout: tuple[int, int]) -> None:
        self.timeout = timeout
        self._api_client = api_client

    def _request(
        self,
        method: Literal["GET", "POST", "PUT", "OPTIONS", "DELETE"],
        resource_path: str,
        query_params: Optional[Dict[str, str]] = None,
    ) -> RawAPIResponse:
        # Found the auth_settings here:
        # https://github.com/kubernetes-client/python/issues/528
        response, status_code, headers = self._api_client.call_api(
            resource_path,
            method,
            query_params=query_params,
            auth_settings=["BearerToken"],
            _request_timeout=self.timeout,
            _preload_content=False,
        )
        return RawAPIResponse(
            response=response.data.decode("utf-8"), status_code=status_code, headers=headers
        )

    def _get_healthz(self, url: str) -> api.HealthZ:
        def get_health(query_params: Optional[Dict[str, str]] = None) -> tuple[int, str]:
            # https://kubernetes.io/docs/reference/using-api/health-checks/
            try:
                response = self._request("GET", url, query_params=query_params)
            except client.rest.ApiException as e:
                return e.status, e.body
            return response.status_code, response.response

        status_code, response = get_health()
        if status_code != 200:
            _status_code, verbose_response = get_health({"verbose": "1"})
        else:
            verbose_response = None

        return api.HealthZ(
            response=response,
            status_code=status_code,
            verbose_response=verbose_response,
        )

    def query_raw_version(self) -> str:
        return self._request("GET", "/version").response

    def query_api_health(self) -> api.APIHealth:
        return api.APIHealth(ready=self._get_healthz("/readyz"), live=self._get_healthz("/livez"))

    def query_kubelet_health(self, node_name: str) -> api.HealthZ:
        return self._get_healthz(f"/api/v1/nodes/{node_name}/proxy/healthz")

    def query_raw_statefulsets(self) -> JSONStatefulSetList:
        return json.loads(self._request("GET", "/apis/apps/v1/statefulsets").response)


def _extract_sequence_based_identifier(git_version: str) -> Optional[str]:
    """

    >>> _extract_sequence_based_identifier("v1.20.0")
    '1.20.0'
    >>> _extract_sequence_based_identifier("    v1.20.0")  # some white space is allowed
    '1.20.0'
    >>> _extract_sequence_based_identifier("v   1.20.0")  # but only in specific cases

    >>> _extract_sequence_based_identifier("a1.20.0")  # v or whitespace are the only allowed letters at the start

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
) -> Union[api.KubernetesVersion, api.UnknownKubernetesVersion]:
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
) -> Union[api.UnknownKubernetesVersion, api.KubernetesVersion]:
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


def _create_api_controller(name: str, namespace: str | None, kind: str) -> api.Controller:
    return api.Controller(
        name=name,
        namespace=namespace,
        type_=api.ControllerType.from_str(kind.lower()),
    )


# TODO Needs an integration test
def _match_controllers(
    pods: Iterable[client.V1Pod], object_to_owners: Mapping[str, api.OwnerReferences]
) -> Tuple[Mapping[str, Sequence[api.PodUID]], Mapping[api.PodUID, Sequence[api.Controller]]]:
    """Matches controllers to the pods they control

    >>> pod = client.V1Pod(metadata=client.V1ObjectMeta(name="test-pod", uid="pod", owner_references=[client.V1OwnerReference(api_version="v1", kind="Job", name="test-job", uid="job", controller=True)]))
    >>> object_to_owners = {"job": [api.OwnerReference(uid='cronjob', controller=True, kind="CronJob", name="mycron", namespace='namespace_name')], "cronjob": []}
    >>> _match_controllers([pod], object_to_owners)
    ({'cronjob': ['pod']}, {'pod': [Controller(type_=<ControllerType.cronjob: 'cronjob'>, name='mycron', namespace='namespace_name')]})

    """
    # owner_reference approach is taken from these two links:
    # https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/
    # https://github.com/kubernetes-client/python/issues/946
    # We have tested the solution in the github issue. It does not work, but was good
    # enough as a prototype.

    def recursive_toplevel_owner_lookup(
        owner_references: api.OwnerReferences,
    ) -> Iterable[api.OwnerReference]:
        for owner in owner_references:
            if not owner.controller:
                continue
            if (parent := object_to_owners.get(owner.uid)) is None:
                continue
            if len(parent) == 0:
                # If an owner does not have any parent owners, then
                # the owner is the top-level-owner
                yield owner
                continue
            yield from recursive_toplevel_owner_lookup(parent)

    controller_to_pods: Dict[str, List[api.PodUID]] = {}
    pod_to_controllers: Dict[api.PodUID, List[api.Controller]] = {}
    for pod in pods:
        pod_uid = api.PodUID(pod.metadata.uid)
        for owner in recursive_toplevel_owner_lookup(
            list(dependent_object_owner_refererences_from_client(pod))
        ):
            controller_to_pods.setdefault(owner.uid, []).append(pod_uid)
            pod_to_controllers.setdefault(pod_uid, []).append(
                _create_api_controller(
                    owner.name,
                    owner.namespace,
                    owner.kind,
                )
            )

    return controller_to_pods, pod_to_controllers


def _verify_version_support(
    version: Union[api.KubernetesVersion, api.UnknownKubernetesVersion]
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
        raise UnsupportedEndpointData(
            f"Unsupported Kubernetes version '{version.git_version}'. API "
            "Servers with version < v1.21 are known to return incompatible data. "
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
    resource_quotas: Sequence[api.ResourceQuota]
    cluster_details: api.ClusterDetails


StatefulSets = TypeVar("StatefulSets", Sequence[client.V1StatefulSet], JSONStatefulSetList)


@dataclass(frozen=True)
class UnparsedAPIData(Generic[StatefulSets]):
    raw_jobs: Sequence[client.V1Job]
    raw_cron_jobs: Sequence[client.V1CronJob]
    raw_pods: Sequence[client.V1Pod]
    raw_nodes: Sequence[client.V1Node]
    raw_namespaces: Sequence[client.V1Namespace]
    raw_resource_quotas: Sequence[client.V1ResourceQuota]
    raw_deployments: Sequence[client.V1Deployment]
    raw_daemonsets: Sequence[client.V1DaemonSet]
    raw_replica_sets: Sequence[client.V1ReplicaSet]
    node_to_kubelet_health: Mapping[str, api.HealthZ]
    api_health: api.APIHealth
    raw_statefulsets: StatefulSets


def query_raw_api_data_v1(
    batch_api: BatchAPI,
    core_api: CoreAPI,
    raw_api: RawAPI,
    external_api: AppsAPI,
) -> UnparsedAPIData[Sequence[client.V1StatefulSet]]:
    raw_nodes = core_api.query_raw_nodes()
    return UnparsedAPIData(
        raw_jobs=batch_api.query_raw_jobs(),
        raw_cron_jobs=batch_api.query_raw_cron_jobs(),
        raw_pods=core_api.query_raw_pods(),
        raw_nodes=raw_nodes,
        raw_namespaces=core_api.query_raw_namespaces(),
        raw_resource_quotas=core_api.query_raw_resource_quotas(),
        raw_deployments=external_api.query_raw_deployments(),
        raw_daemonsets=external_api.query_raw_daemon_sets(),
        raw_statefulsets=external_api.query_raw_statefulsets(),
        raw_replica_sets=external_api.query_raw_replica_sets(),
        node_to_kubelet_health={
            raw_node.metadata.name: raw_api.query_kubelet_health(raw_node.metadata.name)
            for raw_node in raw_nodes
        },
        api_health=raw_api.query_api_health(),
    )


def query_raw_api_data_v2(
    batch_api: BatchAPI,
    core_api: CoreAPI,
    raw_api: RawAPI,
    external_api: AppsAPI,
) -> UnparsedAPIData[JSONStatefulSetList]:
    raw_nodes = core_api.query_raw_nodes()
    return UnparsedAPIData(
        raw_jobs=batch_api.query_raw_jobs(),
        raw_cron_jobs=batch_api.query_raw_cron_jobs(),
        raw_pods=core_api.query_raw_pods(),
        raw_nodes=raw_nodes,
        raw_namespaces=core_api.query_raw_namespaces(),
        raw_resource_quotas=core_api.query_raw_resource_quotas(),
        raw_deployments=external_api.query_raw_deployments(),
        raw_daemonsets=external_api.query_raw_daemon_sets(),
        raw_statefulsets=raw_api.query_raw_statefulsets(),
        raw_replica_sets=external_api.query_raw_replica_sets(),
        node_to_kubelet_health={
            raw_node.metadata.name: raw_api.query_kubelet_health(raw_node.metadata.name)
            for raw_node in raw_nodes
        },
        api_health=raw_api.query_api_health(),
    )


def map_controllers(
    raw_pods: Sequence[client.V1Pod],
    object_to_owners: Mapping[str, api.OwnerReferences],
) -> Tuple[Mapping[str, Sequence[api.PodUID]], Mapping[api.PodUID, Sequence[api.Controller]]]:
    return _match_controllers(
        pods=raw_pods,
        object_to_owners=object_to_owners,
    )


def map_controllers_top_to_down(
    object_to_owners: Mapping[str, api.OwnerReferences]
) -> Mapping[str, Sequence[str]]:
    """Creates a mapping where the key is the controller and the value a sequence of controlled
    objects
    """
    top_down_references: Dict[str, List[str]] = {}
    for object_uid, owner_references in object_to_owners.items():
        for owner_reference in owner_references:
            top_down_references.setdefault(owner_reference.uid, []).append(object_uid)
    return top_down_references


def statefulset_list_from_client(
    statefulset_list: Sequence[client.V1StatefulSet],
    controller_to_pods: Mapping[str, Sequence[api.PodUID]],
) -> Sequence[api.StatefulSet]:
    return [
        statefulset_from_client(
            raw_statefulset, controller_to_pods.get(raw_statefulset.metadata.uid, [])
        )
        for raw_statefulset in statefulset_list
    ]


def parse_api_data(
    raw_cron_jobs: Sequence[client.V1CronJob],
    raw_pods: Sequence[client.V1Pod],
    raw_jobs: Sequence[client.V1Job],
    raw_nodes: Sequence[client.V1Node],
    raw_namespaces: Sequence[client.V1Namespace],
    raw_resource_quotas: Sequence[client.V1ResourceQuota],
    raw_deployments: Sequence[client.V1Deployment],
    raw_daemonsets: Sequence[client.V1DaemonSet],
    raw_statefulsets: StatefulSets,
    node_to_kubelet_health: Mapping[str, api.HealthZ],
    api_health: api.APIHealth,
    controller_to_pods: Mapping[str, Sequence[api.PodUID]],
    pod_to_controllers: Mapping[api.PodUID, Sequence[api.Controller]],
    controllers_to_dependents: Mapping[str, Sequence[str]],
    git_version: api.GitVersion,
    versioned_parse_statefulsets: Callable[
        [StatefulSets, Mapping[str, Sequence[api.PodUID]]], Sequence[api.StatefulSet]
    ],
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
    statefulsets = versioned_parse_statefulsets(raw_statefulsets, controller_to_pods)
    namespaces = [namespace_from_client(raw_namespace) for raw_namespace in raw_namespaces]
    nodes = [
        node_from_client(raw_node, node_to_kubelet_health[raw_node.metadata.name])
        for raw_node in raw_nodes
    ]
    pods = [pod_from_client(pod, pod_to_controllers.get(pod.metadata.uid, [])) for pod in raw_pods]
    resource_quotas: Sequence[api.ResourceQuota] = [
        api_resource_quota
        for api_resource_quota in [
            resource_quota_from_client(resource_quota) for resource_quota in raw_resource_quotas
        ]
        if api_resource_quota is not None
    ]

    cluster_details = api.ClusterDetails(api_health=api_health, version=git_version)
    return APIData(
        cron_jobs=cron_jobs,
        deployments=deployments,
        daemonsets=daemonsets,
        jobs=jobs,
        statefulsets=statefulsets,
        namespaces=namespaces,
        nodes=nodes,
        pods=pods,
        resource_quotas=resource_quotas,
        cluster_details=cluster_details,
    )


def create_api_data_v1(
    batch_api: BatchAPI,
    core_api: CoreAPI,
    raw_api: RawAPI,
    external_api: AppsAPI,
    git_version: api.GitVersion,
) -> APIData:
    raw_api_data = query_raw_api_data_v1(
        batch_api,
        core_api,
        raw_api,
        external_api,
    )
    object_to_owners = parse_object_to_owners(
        workload_resources_client=itertools.chain(
            raw_api_data.raw_deployments,
            raw_api_data.raw_daemonsets,
            raw_api_data.raw_statefulsets,
            raw_api_data.raw_replica_sets,
            raw_api_data.raw_cron_jobs,
            raw_api_data.raw_jobs,
        ),
        workload_resources_json=(),
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
        raw_api_data.node_to_kubelet_health,
        raw_api_data.api_health,
        controller_to_pods,
        pod_to_controllers,
        map_controllers_top_to_down(object_to_owners),
        git_version,
        versioned_parse_statefulsets=statefulset_list_from_client,
    )


def create_api_data_v2(
    batch_api: BatchAPI,
    core_api: CoreAPI,
    raw_api: RawAPI,
    external_api: AppsAPI,
    git_version: api.GitVersion,
) -> APIData:
    raw_api_data = query_raw_api_data_v2(
        batch_api,
        core_api,
        raw_api,
        external_api,
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
        raw_api_data.node_to_kubelet_health,
        raw_api_data.api_health,
        controller_to_pods,
        pod_to_controllers,
        map_controllers_top_to_down(object_to_owners),
        git_version,
        versioned_parse_statefulsets=statefulset_list_from_json,
    )


def from_kubernetes(api_client: client.ApiClient, timeout: tuple[int, int]) -> APIData:
    """
    This function provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """
    batch_api = BatchAPI(api_client, timeout)
    core_api = CoreAPI(api_client, timeout)
    raw_api = RawAPI(api_client, timeout)
    external_api = AppsAPI(api_client, timeout)

    raw_version = raw_api.query_raw_version()
    version = version_from_json(raw_version)
    _verify_version_support(version)

    if isinstance(version, api.UnknownKubernetesVersion) or (version.major, version.minor) in {
        (1, 21),
        (1, 22),
    }:
        return create_api_data_v1(
            batch_api,
            core_api,
            raw_api,
            external_api,
            version.git_version,
        )

    return create_api_data_v2(
        batch_api,
        core_api,
        raw_api,
        external_api,
        version.git_version,
    )
