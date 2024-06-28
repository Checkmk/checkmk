#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import Literal

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
    role_arn_id: RoleArnId | None = None


Selection = Literal["none", "all", "tags", "names"]
Service = tuple[Selection, dict | None]


class Tag(BaseModel):
    key: str
    values: list[str]


class AwsParams(BaseModel):
    access_key_id: str
    secret_access_key: Secret
    proxy_details: ProxyDetails | None = None
    access: APIAccess
    global_services: Mapping[str, Service]
    regions_to_monitor: list[str]
    services: Mapping[str, Service]
    piggyback_naming_convention: str
    overall_tags: list[Tag] | None = None


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


def _get_tag_options(tags: Tag, prefix: str) -> list[str]:
    return ["--%s-tag-key" % prefix, tags.key, "--%s-tag-values" % prefix, *tags.values]


def _get_services_args(services: Mapping[str, Service]) -> list[str]:
    service_names: list[str] = []
    service_args: list[str] = []
    for service_name, service in services.items():
        selection, service_config = service
        if selection == "none":
            continue

        if service_name == "aws_lambda":
            service_name = "lambda"

        service_names.append(service_name)

        if service_config is None:
            continue

        if service_config.get("limits") == "limits":
            service_args.append("--%s-limits" % service_name)

        if service_name == "cloudwatch_alarms":
            service_args.extend(("--cloudwatch-alarms", *service_config.get("names", [])))
        elif instance_names := service_config.get("names"):
            service_args.extend(("--%s-names" % service_name, *instance_names))
        elif instance_tags := service_config.get("tags"):
            for tag in instance_tags:
                service_args.extend(_get_tag_options(Tag.model_validate(tag), service_name))

    return [*sorted(service_names), *service_args]


def aws_arguments(
    params: AwsParams,
    host_config: HostConfig,
) -> Iterable[SpecialAgentCommand]:
    args: list[str | Secret] = ["--access-key-id", params.access_key_id]
    args.extend(("--secret-access-key-reference", params.secret_access_key))
    if params.proxy_details:
        args.extend(_proxy_args(params.proxy_details))
    if global_serv_region := params.access.global_service_region:
        args.extend(("--global-service-region", global_serv_region.replace("_", "-")))
    if role_arn_id := params.access.role_arn_id:
        args.extend(("--assume-role", "--role-arn", role_arn_id.role_arn))
        if role_arn_id.external_id:
            args.extend(("--external-id", role_arn_id.external_id))
    if params.regions_to_monitor:
        args.extend(
            ("--regions", *(region.replace("_", "-") for region in params.regions_to_monitor))
        )
    if global_service_args := _get_services_args(params.global_services):
        args.extend(("--global-services", *global_service_args))
    if cloudfront_config := params.global_services.get("cloudfront", ("None", None))[1]:
        args.extend(("--cloudfront-host-assignment", cloudfront_config["host_assignment"]))
    if service_args := _get_services_args(params.services):
        args.extend(("--services", *service_args))
    if (s3_config := params.services.get("s3", ("None", None))[1]) and "requests" in s3_config:
        args.append("--s3-requests")
    if (
        wafv2_config := params.services.get("wafv2", ("None", None))[1]
    ) and "cloudfront" in wafv2_config:
        args.append("--wafv2-cloudfront")
    if params.overall_tags:
        for tag in params.overall_tags:
            args.extend(_get_tag_options(tag, "overall"))
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
