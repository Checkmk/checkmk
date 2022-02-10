#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Dict, Generic, Iterator, List, Literal, Optional, Sequence, Tuple, Type, TypeVar

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from cmk.special_agents.utils_kubernetes.schemata import api
from cmk.special_agents.utils_kubernetes.transform import (
    cron_job_from_client,
    deployment_from_client,
    node_from_client,
    pod_from_client,
)


class BatchAPI:
    def __init__(self, api_client: client.ApiClient) -> None:
        self.connection = client.BatchV1Api(api_client)

    def query_raw_cron_jobs(self) -> Iterator[client.V1CronJob]:
        return self.connection.list_cron_job_for_all_namespaces().items

    def query_raw_jobs(self) -> Iterator[client.V1Job]:
        return self.connection.list_job_for_all_namespaces().items


class CoreAPI:
    """
    Wrapper around CoreV1Api; Implementation detail of APIServer
    """

    def __init__(self, api_client: client.ApiClient) -> None:
        self.connection = client.CoreV1Api(api_client)
        self._nodes: Dict[str, api.Node] = {}
        self._pods: Dict[str, api.Pod] = {}
        self._collect_objects()

    def nodes(self) -> Sequence[client.V1Node]:
        return self.connection.list_node().items

    def pods(self) -> Sequence[api.Pod]:
        return tuple(self._pods.values())

    def query_namespaced_pods(
        self, namespace: str, label_selector: str = ""
    ) -> Iterator[client.V1Pod]:
        for pod in self.connection.list_namespaced_pod(
            namespace, label_selector=label_selector
        ).items:
            yield pod

    def query_raw_pods(self) -> Iterator[client.V1Pod]:
        return self.connection.list_pod_for_all_namespaces().items

    def _collect_objects(self):
        self._collect_pods()

    def _collect_pods(self):
        self._pods.update(
            {
                pod.metadata.name: pod_from_client(pod)
                for pod in self.connection.list_pod_for_all_namespaces().items
            }
        )


def get_controllers(
    owner_references: Optional[Sequence[client.V1OwnerReference]],
) -> Sequence[client.V1OwnerReference]:
    if owner_references is None:
        return []
    return [reference for reference in owner_references if reference.controller]


class AppsAPI:
    """
    Wrapper around ExternalV1APi;
    """

    def __init__(self, api_client: client.ApiClient) -> None:
        self.connection = client.AppsV1Api(api_client)

    def deployments(self) -> Iterator[client.V1Deployment]:
        for deployment in self.connection.list_deployment_for_all_namespaces().items:
            yield deployment

    def owned_by_deployment(self, pod: client.V1Pod, deployment_uid: str) -> bool:
        # owner_reference approach is taken from these two links:
        # https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/
        # https://github.com/kubernetes-client/python/issues/946
        # We have tested the solution in the github issue. It does not work, but was good
        # enough as a prototype.
        pod_controllers = get_controllers(pod.metadata.owner_references)
        for pod_controller in pod_controllers:
            if pod_controller.kind == "ReplicaSet":
                replica_controllers = get_controllers(
                    self.connection.read_namespaced_replica_set(
                        # we assume the namespace of the replica set is the same as that of the pod it is
                        # controlling
                        pod_controller.name,
                        pod.metadata.namespace,
                    ).metadata.owner_references
                )
                for replica_controller in replica_controllers:
                    if replica_controller.uid == deployment_uid:
                        return True
        return False


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

    def __init__(self, api_client: client.ApiClient) -> None:
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

    def api_health(self) -> api.APIHealth:
        return api.APIHealth(ready=self._get_healthz("/readyz"), live=self._get_healthz("/livez"))

    def get_kubelet_health(self, node_name) -> api.HealthZ:
        return self._get_healthz(f"/api/v1/nodes/{node_name}/proxy/healthz")


class APIServer:
    """
    APIServer provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """

    @classmethod
    def from_kubernetes(cls, api_client):
        return cls(
            BatchAPI(api_client), CoreAPI(api_client), RawAPI(api_client), AppsAPI(api_client)
        )

    def __init__(
        self,
        batch_api: BatchAPI,
        core_api: CoreAPI,
        raw_api: RawAPI,
        external_api: AppsAPI,
    ) -> None:
        self.batch_api = batch_api
        self.core_api = core_api
        self.apps_api = external_api
        self.raw_api = raw_api

    def cron_jobs(self) -> Sequence[api.CronJob]:
        # CronJob -controls-> Job -controls-> Pod
        cronjobs_controlling_jobs: Dict[api.CronJobUID, List[api.JobUID]] = {}
        for job in self.batch_api.query_raw_jobs():
            job_controllers = get_controllers(job.metadata.owner_references)
            for job_controller in job_controllers:
                if not job_controller.kind == "CronJob":
                    continue
                controlling_jobs = cronjobs_controlling_jobs.setdefault(
                    api.CronJobUID(job_controller.uid), []
                )
                controlling_jobs.append(job.metadata.uid)

        jobs_controlling_pods: Dict[api.JobUID, List[api.PodUID]] = {}
        for pod in self.core_api.query_raw_pods():
            pod_controllers = get_controllers(pod.metadata.owner_references)
            for pod_controller in pod_controllers:
                if not pod_controller.kind == "Job":
                    continue
                controlling_pods = jobs_controlling_pods.setdefault(
                    api.JobUID(pod_controller.uid), []
                )
                controlling_pods.append(api.PodUID(pod.metadata.uid))

        result = []
        for cron_job in self.batch_api.query_raw_cron_jobs():
            controlling_pods = [
                pod_uid
                for job in cronjobs_controlling_jobs.get(api.CronJobUID(cron_job.metadata.uid), [])
                for pod_uid in jobs_controlling_pods.get(job, [])
            ]
            result.append(cron_job_from_client(cron_job, controlling_pods))
        return result

    def deployments(self) -> Sequence[api.Deployment]:
        result = []
        for raw_deployment in self.apps_api.deployments():
            selector = raw_deployment.spec.selector
            label_selector = (
                ",".join([f"{key}={value}" for key, value in selector.match_labels.items()])
                if selector.match_labels is not None
                else ""
            )

            # TODO for pod_uids computation: Needs an integration test
            # TODO for pod_uids computation: Efficiency is questionable at best here. What we want
            # is, that each object kind (Deployment, DaemonSet, ReplicaSet,...) can map to it's
            # respective pods. For this need to parse the object_references of all the pods once.
            # But we should not need to parse them more than once (here we parse the object
            # references multiple times, if two deployments differ only by a match_expression
            # selector. Moreover, it probably makes sense to only call
            # self.core_api.query_namespaced_pods with no restriction).
            # When we do this refactoring, we should also consider writing owned_by_deployment as a
            # free function.
            result.append(
                deployment_from_client(
                    raw_deployment,
                    pod_uids=[
                        pod.metadata.uid
                        for pod in self.core_api.query_namespaced_pods(
                            raw_deployment.metadata.namespace, label_selector
                        )
                        if self.apps_api.owned_by_deployment(pod, raw_deployment.metadata.uid)
                    ],
                )
            )
        return result

    def nodes(self) -> Sequence[api.Node]:
        result = []
        for raw_node in self.core_api.nodes():
            result.append(
                node_from_client(raw_node, self.raw_api.get_kubelet_health(raw_node.metadata.name))
            )
        return result

    def pods(self) -> Sequence[api.Pod]:
        return self.core_api.pods()

    def cluster_details(self) -> api.ClusterInfo:
        health = self.raw_api.api_health()
        return api.ClusterInfo(api_health=health)
