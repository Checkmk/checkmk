#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import BaseModel, model_serializer

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class AuthLogin(BaseModel, frozen=True):
    username: str
    password: Secret


class AuthToken(BaseModel, frozen=True):
    token: Secret


class NodeExporter(BaseModel, frozen=True):
    host_mapping: str | None = None
    entities: Sequence[str]


class ContainerEntity(BaseModel, frozen=True):
    container_id: Literal["short", "long", "name"]


class PodEntity(BaseModel, frozen=True):
    prepend_namespaces: Literal["use_namespace", "omit_namespace"]


class ContainerAndPotEntity(BaseModel, frozen=True):
    container_id: Literal["short", "long", "name"]
    prepend_namespaces: Literal["use_namespace", "omit_namespace"]


class cAdvisor(BaseModel, frozen=True):
    entity_level: (
        tuple[Literal["container"], ContainerEntity]
        | tuple[Literal["pod"], PodEntity]
        | tuple[Literal["both"], ContainerAndPotEntity]
    )
    namespace_include_patterns: Sequence[str] | None = None
    entities: Sequence[str]


class Levels(BaseModel, frozen=True):
    lower_levels: (
        tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]] | None
    ) = None
    upper_levels: (
        tuple[Literal["no_levels"], None] | tuple[Literal["fixed"], tuple[float, float]] | None
    ) = None

    @model_serializer()
    def serialize_model(self) -> dict[str, tuple[float, float] | None]:
        serialized = {}
        if self.lower_levels:
            serialized["lower_levels"] = self.lower_levels[1]
        if self.upper_levels:
            serialized["upper_levels"] = self.upper_levels[1]
        return serialized


class MetricComponent(BaseModel, frozen=True):
    metric_label: str
    metric_name: str | None = None
    promql_query: str
    levels: Levels | None = None


class PromlQLCheck(BaseModel, frozen=True):
    service_description: str
    host_name: str | None = None
    metric_components: Sequence[MetricComponent]


class Params(BaseModel, frozen=True):
    connection: str
    verify_cert: bool
    auth_basic: (
        tuple[Literal["auth_login"], AuthLogin] | tuple[Literal["auth_token"], AuthToken] | None
    ) = None
    protocol: Literal["http", "https"]
    exporter: Sequence[
        tuple[Literal["node_exporter"], NodeExporter] | tuple[Literal["cadvisor"], cAdvisor]
    ]
    promql_checks: Sequence[PromlQLCheck]


def _commands_function(
    params: Params,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--config",
        repr(
            params.model_dump(
                exclude={
                    "auth_basic",
                    "verify_cert",
                },
                exclude_unset=True,
            )
            | {
                "host_address": _primary_ip_address_from_host_config_if_configured(host_config),
                "host_name": host_config.name,
            }
        ),
    ]
    if params.verify_cert:
        args.extend(["--cert-server-name", host_config.name])
    else:
        args.append("--disable-cert-verification")
    # the authentication parameters must come last because they are parsed by subparsers that
    # consume all remaining arguments (and throw errors if they don't recognize them)
    match params.auth_basic:
        case ("auth_login", AuthLogin(username=username, password=password)):
            args += [
                "auth_login",
                "--username",
                username,
                "--password-reference",
                password,
            ]
        case ("auth_token", AuthToken(token=token)):
            args += [
                "auth_token",
                "--token",
                token,
            ]
    yield SpecialAgentCommand(command_arguments=args)


special_agent_prometheus = SpecialAgentConfig(
    name="prometheus",
    parameter_parser=Params.model_validate,
    commands_function=_commands_function,
)


def _primary_ip_address_from_host_config_if_configured(host_config: HostConfig) -> str | None:
    try:
        primary_ip_config = host_config.primary_ip_config
    except ValueError:
        return None
    return primary_ip_config.address
