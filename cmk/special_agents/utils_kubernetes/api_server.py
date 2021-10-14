#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Dict, Generic, Literal, Optional, Sequence, Tuple, Type, TypeVar

from kubernetes import client  # type: ignore[import] # pylint: disable=import-error

from cmk.special_agents.utils_kubernetes.schemas import (
    APIHealth,
    APIHealthStatus,
    ClusterInfo,
    NodeAPI,
    PodAPI,
)


class CoreAPI:
    """
    Wrapper around CoreV1Api; Implementation detail of APIServer
    """

    def __init__(self, api_client: client.ApiClient) -> None:
        self.connection = client.CoreV1Api(api_client)
        self._nodes: Dict[str, NodeAPI] = {}
        self._pods: Dict[str, PodAPI] = {}
        self._collect_objects()

    def nodes(self) -> Sequence[NodeAPI]:
        return tuple(self._nodes.values())

    def pods(self) -> Sequence[PodAPI]:
        return tuple(self._pods.values())

    def _collect_objects(self):
        self._collect_nodes()
        self._collect_pods()

    def _collect_pods(self):
        self._pods.update(
            {
                pod.metadata.name: PodAPI.from_client(pod)
                for pod in self.connection.list_pod_for_all_namespaces().items
            }
        )

    def _collect_nodes(self):
        self._nodes.update(
            {
                node.metadata.name: NodeAPI.from_client(node)
                for node in self.connection.list_node().items
            }
        )


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
        response, status_code, headers = self._api_client.call_api(
            resource_path, method, response_type=str, query_params=query_params
        )
        return RawAPIResponse(response=response, status_code=status_code, headers=headers)

    def _get_api_health(self, endpoint_name) -> APIHealthStatus:
        def get_health(query_params=None) -> Tuple[int, str]:
            # https://kubernetes.io/docs/reference/using-api/health-checks/
            response = self._request(
                "GET", f"/{endpoint_name}z", response_type=str, query_params=query_params
            )
            return response.status_code, response.response

        status_code, http_body = get_health()
        response = http_body
        verbose_response = None
        if status_code != 200:
            _status_code, http_body = get_health({"verbose": ""})
            verbose_response = http_body

        return APIHealthStatus(
            response=response,
            status_code=status_code,
            verbose_response=verbose_response,
        )

    def api_health(self) -> APIHealth:
        return APIHealth(ready=self._get_api_health("ready"), live=self._get_api_health("live"))


class APIServer:
    """
    APIServer provides a stable interface that should not change between kubernetes versions
    This should be the only data source for all special agent code!
    """

    @classmethod
    def from_kubernetes(cls, api_client):
        return cls(CoreAPI(api_client), RawAPI(api_client))

    def __init__(
        self,
        core_api: CoreAPI,
        raw_api: RawAPI,
    ) -> None:
        self.core_api = core_api
        self.raw_api = raw_api

    def nodes(self) -> Sequence[NodeAPI]:
        return self.core_api.nodes()

    def pods(self) -> Sequence[PodAPI]:
        return self.core_api.pods()

    def cluster_details(self) -> ClusterInfo:
        health = self.raw_api.api_health()
        return ClusterInfo(api_health=health)
