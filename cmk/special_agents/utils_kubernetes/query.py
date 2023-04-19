#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-any-unimported
# mypy: disallow-any-decorated
# mypy: disallow-any-explicit
# mypy: disallow-any-generics
# mypy: disallow-subclassing-any
# mypy: warn-return-any

import argparse
import enum
import json
import logging
from collections.abc import Iterable, Iterator, Mapping
from typing import final, NewType, Union

import requests
import urllib3
from pydantic import BaseModel, parse_obj_as, ValidationError

from cmk.utils.http_proxy_config import deserialize_http_proxy_config

from cmk.special_agents.utils import node_exporter
from cmk.special_agents.utils_kubernetes.prometheus_api import (
    parse_raw_response,
    Response,
    ResponseSuccess,
    Vector,
)

TCPTimeout = NewType("TCPTimeout", tuple[int, int])

HTTPResult = Union[
    Response,
    ValidationError,
    json.JSONDecodeError,
    requests.exceptions.RequestException,
]


class PrometheusEndpoints(enum.StrEnum):
    query = "/api/v1/query"


class CollectorPath(enum.StrEnum):
    metadata = "/metadata"
    container_metrics = "/container_metrics"
    machine_sections = "/machine_sections"


class Query(enum.StrEnum):
    # These two rules are 1-to-1 copies from the OKD dashboard. The reason for setting the "pod" and
    # the "container" label is, that cAdvisor and kubelet both collect the same metric. Therefore,
    # not setting these labels results in overestimating usage by a factor of 2. The specifics of
    # setting labels this way are unclear.
    sum_rate_container_cpu_usage_seconds_total = (
        'sum(rate(container_cpu_usage_seconds_total{container="",pod!=""}[5m])) BY (pod, namespace)'
    )
    sum_container_memory_working_set_bytes = (
        'sum(container_memory_working_set_bytes{container=""}) BY (pod, namespace)'
    )


HTTPResponse = tuple[Query, HTTPResult]


@final
class NoUsageConfig(BaseModel):
    pass


class SessionConfig(BaseModel):
    token: str
    usage_proxy: str
    usage_read_timeout: int
    usage_connect_timeout: int
    usage_verify_cert: bool

    class Config:
        allow_mutable = False

    def requests_timeout(self) -> TCPTimeout:
        return TCPTimeout((self.usage_connect_timeout, self.usage_read_timeout))

    def requests_proxies(self) -> Mapping[str, str]:
        return deserialize_http_proxy_config(self.usage_proxy).to_requests_proxies() or {}


class CollectorSessionConfig(SessionConfig):
    cluster_collector_endpoint: str


class PrometheusSessionConfig(SessionConfig):
    prometheus_endpoint: str

    def query_url(self) -> str:
        return self.prometheus_endpoint + PrometheusEndpoints.query


def create_session(config: SessionConfig, logger: logging.Logger) -> requests.Session:
    if not config.usage_verify_cert:
        logger.warning("Disabling SSL certificate verification.")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.proxies.update(config.requests_proxies())
    session.headers.update(
        {} if config.token is None else {"Authorization": f"Bearer {config.token}"}
    )
    return session


_AllConfigs = CollectorSessionConfig | PrometheusSessionConfig | NoUsageConfig


def parse_session_config(arguments: argparse.Namespace) -> _AllConfigs:
    return parse_obj_as(_AllConfigs, arguments.__dict__)  # type: ignore[arg-type]


def send_requests(
    config: PrometheusSessionConfig,
    queries: Iterable[Query],
    logger: logging.Logger,
) -> Iterator[HTTPResponse]:
    session = create_session(config, logger)

    for query in queries:
        yield _send_query_request_get(
            query=query,
            query_url=config.query_url(),
            session=session,
            requests_verify=config.usage_verify_cert,
            requests_timeout=config.requests_timeout(),
        )


def _send_query_request_get(
    query: Query,
    session: requests.Session,
    query_url: str,
    requests_verify: bool,
    requests_timeout: TCPTimeout,
) -> HTTPResponse:
    request = requests.Request("GET", query_url + f"?query={query}")
    prepared_request = session.prepare_request(request)
    try:
        response = session.send(prepared_request, verify=requests_verify, timeout=requests_timeout)
    except requests.exceptions.RequestException as e:
        return query, e
    return query, parse_raw_response(response.content)


def node_exporter_getter(
    config: PrometheusSessionConfig, logger: logging.Logger, promql_expression: str
) -> list[node_exporter.PromQLMetric]:
    _query, result = next(send_requests(config=config, queries=[promql_expression], logger=logger))  # type: ignore[list-item] # NodeExporter passes queries as str
    if isinstance(result, ResponseSuccess) and isinstance(result.data, Vector):
        return [
            {"value": sample.value[1], "labels": sample.metric} for sample in result.data.result
        ]
    return []
