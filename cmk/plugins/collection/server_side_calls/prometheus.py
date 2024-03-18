#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Literal

from pydantic import BaseModel, Field

from cmk.server_side_calls.v1 import HostConfig, SpecialAgentCommand, SpecialAgentConfig


class BasicAuthentication(BaseModel):
    username: str
    password: str | tuple[str, str]


class TokenAuthentication(BaseModel):
    token: str | tuple[str, str]


class NodeExporterOptions(BaseModel):
    host_mapping: str | None = None
    entities: list[str]


class ContainerEntityLevel(BaseModel):
    container_id: Literal["short", "long", "name"]


class PodEntityLevel(BaseModel):
    prepend_namespaces: Literal["use_namespace", "omit_namespace"]


class BothEntityLevel(BaseModel):
    container_id: Literal["short", "long", "name"]
    prepend_namespaces: Literal["use_namespace", "omit_namespace"]


class CAdvisorOptions(BaseModel):
    entity_level: tuple[Literal["container"], ContainerEntityLevel] | tuple[
        Literal["pod"], PodEntityLevel
    ] | tuple[Literal["both"], BothEntityLevel]
    namespace_include_patterns: list[str] | None = None
    entities: list[str]


class MetricLevels(BaseModel):
    lower_levels: tuple[float, float] | None = None
    upper_levels: tuple[float, float] | None = None


class PromQLMetricComponent(BaseModel):
    metric_label: str
    metric_name: str | None = None
    promql_query: str
    levels: MetricLevels | None = None


class PromQLCheck(BaseModel):
    service_description: str
    host_name: str | None = None
    metric_components: list


class PrometheusParams(BaseModel):
    connection: str
    verify_cert: bool | None = Field(default=None, alias="verify-cert")
    auth_basic: tuple[Literal["auth_login"], BasicAuthentication] | tuple[
        Literal["auth_token"], TokenAuthentication
    ] | None = None
    protocol: Literal["http", "https"]
    exporter: list[
        tuple[Literal["node_exporter"], NodeExporterOptions]
        | tuple[Literal["cadvisor"], CAdvisorOptions]
    ] | None = None
    promql_checks: list[PromQLCheck] | None = None


def generate_prometheus_command(
    params: PrometheusParams,
    host_config: HostConfig,
    _http_proxies: object,
) -> Iterable[SpecialAgentCommand]:
    prometheus_params: dict[str, object] = {}
    if params.verify_cert is not None:
        prometheus_params["verify-cert"] = params.verify_cert
    prometheus_params.update(params.model_dump(exclude=set("verify_cert"), exclude_none=True))
    yield SpecialAgentCommand(command_arguments=[], stdin=repr(prometheus_params))


special_agent_prometheus = SpecialAgentConfig(
    name="prometheus",
    parameter_parser=PrometheusParams.model_validate,
    commands_function=generate_prometheus_command,
)
