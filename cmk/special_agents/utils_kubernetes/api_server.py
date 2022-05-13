#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Mapping, Optional, Sequence, Tuple, Union

from kubernetes import client  # type: ignore[import]

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
    cron_job_from_client,
    daemonset_from_client,
    deployment_from_client,
    namespace_from_client,
    node_from_client,
    pod_from_client,
    resource_quota_from_client,
    statefulset_from_client,
)

LOGGER = logging.getLogger()
VERSION_MATCH_RE = re.compile(r"\s*v?([0-9]+(?:\.[0-9]+)*).*")
SUPPORTED_VERSIONS = [(1, 21), (1, 22), (1, 23)]
LOWEST_FUNCTIONING_VERSION = min(SUPPORTED_VERSIONS)
SUPPORTED_VERSIONS_DISPLAY = ", ".join(f"v{major}.{minor}" for major, minor in SUPPORTED_VERSIONS)


class BatchAPI:
    def __init__(self, api_client: client.ApiClient, timeout) -> None:
        self.connection = client.BatchV1Api(api_client)
        self.timeout = timeout
        self.raw_jobs = self._query_raw_jobs()
        self.raw_cron_jobs = self._query_raw_cron_jobs()

    def _query_raw_cron_jobs(self) -> Sequence[client.V1CronJob]:
        return self.connection.list_cron_job_for_all_namespaces(_request_timeout=self.timeout).items

    def _query_raw_jobs(self) -> Sequence[client.V1Job]:
        return self.connection.list_job_for_all_namespaces(_request_timeout=self.timeout).items


class CoreAPI:
    """
    Wrapper around CoreV1Api; Implementation detail of APIServer
    """

    def __init__(self, api_client: client.ApiClient, timeout) -> None:
        self.connection = client.CoreV1Api(api_client)
        self.timeout = timeout
        self.raw_pods = self._query_raw_pods()
        self.raw_nodes = self._query_raw_nodes()
        self.raw_namespaces = self._query_raw_namespaces()
        self.raw_resource_quotas = self._query_raw_resource_quotas()

    def _query_raw_nodes(self) -> Sequence[client.V1Node]:
        return self.connection.list_node(_request_timeout=self.timeout).items

    def _query_raw_pods(self) -> Sequence[client.V1Pod]:
        return self.connection.list_pod_for_all_namespaces(_request_timeout=self.timeout).items

    def _query_raw_resource_quotas(self) -> Sequence[client.V1ResourceQuota]:
        return self.connection.list_resource_quota_for_all_namespaces().items

    def _query_raw_namespaces(self):
        return self.connection.list_namespace(_request_timeout=self.timeout).items


class AppsAPI:
    """
    Wrapper around ExternalV1APi; Implementation detail of APIServer
    """

    def __init__(self, api_client: client.ApiClient, timeout) -> None:
        self.connection = client.AppsV1Api(api_client)
        self.timeout = timeout
        self.raw_deployments = self._query_raw_deployments()
        self.raw_daemon_sets = self._query_raw_daemon_sets()
        self.raw_statefulsets = self._query_raw_statefulsets()
        self.raw_replica_sets = self._query_raw_replica_sets()

    def _query_raw_deployments(self) -> Sequence[client.V1Deployment]:
        return self.connection.list_deployment_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def _query_raw_daemon_sets(self) -> Sequence[client.V1DaemonSet]:
        return self.connection.list_daemon_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def _query_raw_statefulsets(self) -> Sequence[client.V1StatefulSet]:
        return self.connection.list_stateful_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def _query_raw_replica_sets(self) -> Sequence[client.V1ReplicaSet]:
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

    def __init__(self, api_client: client.ApiClient, timeout) -> None:
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

    def _get_healthz(self, url) -> api.HealthZ:
        def get_health(query_params=None) -> Tuple[int, str]:
            # https://kubernetes.io/docs/reference/using-api/health-checks/
            try:
                response = self._request("GET", url, query_params=query_params)
            except client.rest.ApiException as e:
                return e.status, e.body
            return response.status_code, response.response

        status_code, http_body = get_health()
        response = http_body
        verbose_response = None
        if status_code != 200:
            _status_code, http_body = get_health({"verbose": "1"})
            verbose_response = http_body

        return api.HealthZ(
            response=response,
            status_code=status_code,
            verbose_response=verbose_response,
        )

    def query_raw_version(self) -> str:
        return self._request("GET", "/version").response

    def query_api_health(self) -> api.APIHealth:
        return api.APIHealth(ready=self._get_healthz("/readyz"), live=self._get_healthz("/livez"))

    def query_kubelet_health(self, node_name) -> api.HealthZ:
        return self._get_healthz(f"/api/v1/nodes/{node_name}/proxy/healthz")


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
    git_version: str,
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


WorkloadResource = Union[
    client.V1Deployment,
    client.V1ReplicaSet,
    client.V1DaemonSet,
    client.V1Job,
    client.V1CronJob,
    client.V1ReplicationController,
    client.V1StatefulSet,
]


# TODO Needs an integration test
def _match_controllers(
    pods: Iterable[client.V1Pod],
    workload_resources: Iterable[WorkloadResource],
) -> Mapping[str, Sequence[api.PodUID]]:
    object_to_owners = {
        workload_resource.metadata.uid: workload_resource.metadata.owner_references or []
        for workload_resource in workload_resources
    }
    # owner_reference approach is taken from these two links:
    # https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/
    # https://github.com/kubernetes-client/python/issues/946
    # We have tested the solution in the github issue. It does not work, but was good
    # enough as a prototype.
    result: Mapping[str, List[api.PodUID]] = {uid: [] for uid in object_to_owners}
    for pod in pods:
        owner_references = pod.metadata.owner_references or []
        while (
            controller := next((r for r in owner_references if r.controller), None)
        ) and controller.uid in result:
            result[controller.uid].append(pod.metadata.uid)
            owner_references = object_to_owners[controller.uid]
    return result


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


class APIServer:
    """
    APIServer provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """

    @classmethod
    def from_kubernetes(cls, api_client, timeout):
        raw_api = RawAPI(api_client, timeout)

        raw_version = raw_api.query_raw_version()
        version = version_from_json(raw_version)
        _verify_version_support(version)
        return cls(
            BatchAPI(api_client, timeout),
            CoreAPI(api_client, timeout),
            raw_api,
            AppsAPI(api_client, timeout),
            version.git_version,
        )

    def __init__(
        self,
        batch_api: BatchAPI,
        core_api: CoreAPI,
        raw_api: RawAPI,
        external_api: AppsAPI,
        version: api.GitVersion,
    ) -> None:
        self._batch_api = batch_api
        self._core_api = core_api
        self._raw_api = raw_api
        self._external_api = external_api
        self.version = version

        # It's best if queries to the api happen in a small time window, since then there will fewer
        # mismatches between the objects (which might change inbetween api calls).
        self.node_to_kubelet_health = {
            raw_node.metadata.name: raw_api.query_kubelet_health(raw_node.metadata.name)
            for raw_node in self._core_api.raw_nodes
        }
        self.api_health = raw_api.query_api_health()

        self._controller_to_pods = _match_controllers(
            pods=self._core_api.raw_pods,
            workload_resources=itertools.chain(
                self._external_api.raw_deployments,
                self._external_api.raw_daemon_sets,
                self._external_api.raw_statefulsets,
                self._external_api.raw_replica_sets,
                self._batch_api.raw_cron_jobs,
                self._batch_api.raw_jobs,
            ),
        )

    def cron_jobs(self) -> Sequence[api.CronJob]:
        return [
            cron_job_from_client(raw_cron_job, self._controller_to_pods[raw_cron_job.metadata.uid])
            for raw_cron_job in self._batch_api.raw_cron_jobs
        ]

    def deployments(self) -> Sequence[api.Deployment]:
        return [
            deployment_from_client(
                raw_deployment, self._controller_to_pods[raw_deployment.metadata.uid]
            )
            for raw_deployment in self._external_api.raw_deployments
        ]

    def daemon_sets(self) -> Sequence[api.DaemonSet]:
        return [
            daemonset_from_client(
                raw_daemon_set, self._controller_to_pods[raw_daemon_set.metadata.uid]
            )
            for raw_daemon_set in self._external_api.raw_daemon_sets
        ]

    def statefulsets(self) -> Sequence[api.StatefulSet]:
        return [
            statefulset_from_client(
                raw_statefulset, self._controller_to_pods[raw_statefulset.metadata.uid]
            )
            for raw_statefulset in self._external_api.raw_statefulsets
        ]

    def namespaces(self) -> Sequence[api.Namespace]:
        return [
            namespace_from_client(raw_namespace) for raw_namespace in self._core_api.raw_namespaces
        ]

    def nodes(self) -> Sequence[api.Node]:
        return [
            node_from_client(raw_node, self.node_to_kubelet_health[raw_node.metadata.name])
            for raw_node in self._core_api.raw_nodes
        ]

    def pods(self) -> Sequence[api.Pod]:
        return [pod_from_client(pod) for pod in self._core_api.raw_pods]

    def resource_quotas(self) -> Sequence[api.ResourceQuota]:
        return [
            api_resource_quota
            for resource_quota in self._core_api.raw_resource_quotas
            if (api_resource_quota := resource_quota_from_client(resource_quota)) is not None
        ]

    def cluster_details(self) -> api.ClusterDetails:
        return api.ClusterDetails(api_health=self.api_health, version=self.version)
