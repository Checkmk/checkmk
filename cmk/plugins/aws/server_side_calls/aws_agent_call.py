#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping, Sequence
from typing import cast, Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class ProxyDetails(BaseModel):
    proxy_host: str
    proxy_user: str | None = None
    proxy_port: int | None = None
    proxy_password: Secret | None = None


class RoleArnId(BaseModel):
    role_arn: str
    external_id: str | None = None


class APIAccess(BaseModel):
    global_service_region: str | None = None
    role_arn_id: tuple[str, str] | None = None


Tag = tuple[str, list[str]]

# Used by various regional services
LimitsActivated = bool
# Used by cloudfront
HostAssignment = Literal["aws_host", "domain_host"]
# Used by various services
Selection = Literal["all"] | tuple[Literal["tags"], list[Tag]] | tuple[Literal["names"], list[str]]

ServiceConfig = Mapping[str, LimitsActivated | HostAssignment | Selection | None] | None


class AwsParams(BaseModel):
    access_key_id: str
    secret_access_key: Secret
    proxy_details: ProxyDetails | None = None
    access: APIAccess | None = None
    global_services: Mapping[str, ServiceConfig] | None = None
    regions_to_monitor: list[str] | None = None
    services: Mapping[str, ServiceConfig] | None = None
    piggyback_naming_convention: Literal["ip_region_instance", "private_dns_name"]
    overall_tags: list[Tag] | None = None


def _get_tag_options(tags: list[Tag], prefix: str) -> Sequence[str]:
    options = []
    for key, values in tags:
        options.append("--%s-tag-key" % prefix)
        options.append(key)
        options.append("--%s-tag-values" % prefix)
        options += values
    return options


def _get_services_args(services: Mapping[str, ServiceConfig]) -> Sequence[str]:
    # '--services': {
    #   's3': {'selection': ('tags', [('KEY', ['VAL1', 'VAL2'])])},
    #   'ec2': {'selection': 'all'},
    #   'ebs': {'selection': ('names', ['ebs1', 'ebs2'])},
    # }
    service_names: list[str] = []
    service_args: list[str] = []
    for service_name, service_config in services.items():
        service_names.append(service_name)
        if service_config is None:
            continue

        if service_config.get("limits"):
            service_args.append("--%s-limits" % service_name)

        if service_name == "cloudwatch_alarms" and (alarms := service_config.get("alarms")):
            # {'alarms': 'all'} is handled by no additionally specified names
            names = (alarms[1] if isinstance(alarms, tuple) else []) or []
            if not all(isinstance(name, str) for name in names):
                raise ValueError(f"Invalid value for {service_name} alarms: {names}")
            service_args.extend(("--cloudwatch-alarms", *names))
            continue

        selection = service_config.get("selection")
        if not isinstance(selection, tuple):
            # Here: value of selection is 'all' which means there's no
            # restriction (names or tags) to the instances of a specific
            # AWS service. The commandline option already includes this
            # service '--services SERVICE1 SERVICE2 ...' (see below).
            continue

        selection_type, selection_values = selection
        if not selection_values:
            continue
        if selection_type == "names":
            service_args.extend((f"--{service_name}-names", *selection_values))
        elif selection_type == "tags":
            if not all(isinstance(tag, tuple) for tag in selection_values):
                raise ValueError(f"Invalid value for {service_name} tags: {selection_values}")
            service_args += _get_tag_options(cast(list[Tag], selection_values), service_name)
    return [*sorted(service_names), *service_args]


def _proxy_args(details: ProxyDetails) -> list[str | Secret]:
    proxy_args: list[str | Secret] = ["--proxy-host", details.proxy_host]
    if details.proxy_port:
        proxy_args.extend(("--proxy-port", str(details.proxy_port)))
    if details.proxy_user and details.proxy_password:
        proxy_args.extend(
            (
                "--proxy-user",
                details.proxy_user,
                "--proxy-password-reference",
                details.proxy_password,
            )
        )
    return proxy_args


def aws_arguments(
    params: AwsParams,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = [
        "--access-key-id",
        params.access_key_id,
        "--secret-access-key-reference",
        params.secret_access_key,
    ]
    if params.proxy_details:
        args.extend(_proxy_args(params.proxy_details))
    access = params.access or APIAccess()
    if global_service_region := access.global_service_region:
        args.extend(("--global-service-region", global_service_region))
    if role_arn_id := access.role_arn_id:
        args.extend(("--assume-role", "--role-arn", role_arn_id[0]))
        if role_arn_id[1]:
            args.extend(("--external-id", role_arn_id[1]))
    if params.regions_to_monitor:
        args.extend(("--regions", *params.regions_to_monitor))
    global_services = params.global_services or {}
    if global_service_args := _get_services_args(global_services):
        args.extend(("--global-services", *global_service_args))
    services = params.services or {}
    if service_args := _get_services_args(services):
        args.extend(("--services", *service_args))
    if "requests" in (services.get("s3", {}) or {}):
        args.append("--s3-requests")
    if "cloudfront" in (services.get("wafv2", {}) or {}):
        args.append("--wafv2-cloudfront")
    if "cloudfront" in global_services:
        cloudfront_host_assignment = (global_services["cloudfront"] or {}).get("host_assignment")
        if not isinstance(cloudfront_host_assignment, str):
            raise ValueError(
                f"Invalid value for cloudfront host assignment: {cloudfront_host_assignment}"
            )
        args.extend(("--cloudfront-host-assignment", cloudfront_host_assignment))
    if params.overall_tags:
        args.extend(_get_tag_options(params.overall_tags, "overall"))
    args.extend(
        (
            "--hostname",
            host_config.name,
            "--piggyback-naming-convention",
            params.piggyback_naming_convention,
        )
    )

    yield SpecialAgentCommand(command_arguments=args)


special_agent_aws = SpecialAgentConfig(
    name="aws",
    parameter_parser=AwsParams.model_validate,
    commands_function=aws_arguments,
)
