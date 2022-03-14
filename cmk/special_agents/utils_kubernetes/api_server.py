#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
    cron_job_from_client,
    daemonset_from_client,
    deployment_from_client,
    node_from_client,
    pod_from_client,
    statefulset_from_client,
)


class BatchAPI:
    def __init__(self, api_client: client.ApiClient, timeout) -> None:
        self.connection = client.BatchV1Api(api_client)
        self.timeout = timeout
        self.raw_jobs = self._query_raw_jobs()
        self.raw_cron_jobs = self._query_raw_cron_jobs()

    def _query_raw_cron_jobs(self) -> Iterator[client.V1CronJob]:
        return self.connection.list_cron_job_for_all_namespaces(_request_timeout=self.timeout).items

    def _query_raw_jobs(self) -> Iterator[client.V1Job]:
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

    def _query_raw_nodes(self) -> Sequence[client.V1Node]:
        return self.connection.list_node(_request_timeout=self.timeout).items

    def _query_raw_pods(self) -> Sequence[client.V1Pod]:
        return self.connection.list_pod_for_all_namespaces(_request_timeout=self.timeout).items


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

    def _query_raw_statefulsets(self) -> Sequence[client.V1DaemonSet]:
        return self.connection.list_stateful_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items

    def _query_raw_replica_sets(self) -> Sequence[client.V1ReplicaSet]:
        return self.connection.list_replica_set_for_all_namespaces(
            _request_timeout=self.timeout
        ).items


T = TypeVar("T")


@dataclass
class RawAPIResponse(Generic[T]):
    response: T
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
        *,
        response_type: Type[T],
        query_params: Optional[Dict[str, str]] = None,
    ) -> RawAPIResponse[T]:
        # Found the auth_settings here:
        # https://github.com/kubernetes-client/python/issues/528
        response, status_code, headers = self._api_client.call_api(
            resource_path,
            method,
            response_type=str,
            query_params=query_params,
            auth_settings=["BearerToken"],
            _request_timeout=self.timeout,
        )
        return RawAPIResponse(response=response, status_code=status_code, headers=headers)

    def _get_healthz(self, url) -> api.HealthZ:
        def get_health(query_params=None) -> Tuple[int, str]:
            # https://kubernetes.io/docs/reference/using-api/health-checks/
            try:
                response = self._request("GET", url, response_type=str, query_params=query_params)
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

    def query_api_health(self) -> api.APIHealth:
        return api.APIHealth(ready=self._get_healthz("/readyz"), live=self._get_healthz("/livez"))

    def query_kubelet_health(self, node_name) -> api.HealthZ:
        return self._get_healthz(f"/api/v1/nodes/{node_name}/proxy/healthz")


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


class APIServer:
    """
    APIServer provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """

    @classmethod
    def from_kubernetes(cls, api_client, timeout):
        return cls(
            BatchAPI(api_client, timeout),
            CoreAPI(api_client, timeout),
            RawAPI(api_client, timeout),
            AppsAPI(api_client, timeout),
        )

    def __init__(
        self,
        batch_api: BatchAPI,
        core_api: CoreAPI,
        raw_api: RawAPI,
        external_api: AppsAPI,
    ) -> None:
        self._batch_api = batch_api
        self._core_api = core_api
        self._raw_api = raw_api
        self._external_api = external_api

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

    def nodes(self) -> Sequence[api.Node]:
        return [
            node_from_client(raw_node, self.node_to_kubelet_health[raw_node.metadata.name])
            for raw_node in self._core_api.raw_nodes
        ]

    def pods(self) -> Sequence[api.Pod]:
        return [pod_from_client(pod) for pod in self._core_api.raw_pods]

    def cluster_details(self) -> api.ClusterDetails:
        return api.ClusterDetails(api_health=self.api_health)
