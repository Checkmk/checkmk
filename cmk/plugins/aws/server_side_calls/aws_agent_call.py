#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping, Sequence
from typing import cast, Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class AuthAccessKey(BaseModel):
    access_key_id: str
    secret_access_key: Secret


class AuthSts(BaseModel):
    role_arn_id: str
    external_id: str | None = None


class AuthAccessKeySts(AuthAccessKey, AuthSts): ...


class ProxyDetails(BaseModel):
    proxy_host: str
    proxy_user: str | None = None
    proxy_port: int | None = None
    proxy_password: Secret | None = None


class APIAccess(BaseModel):
    global_service_region: str | None = None


Tag = tuple[str, list[str]]

# Used by various regional services
LimitsActivated = bool
# Used by cloudfront
HostAssignment = Literal["aws_host", "domain_host"]
# Used by various services
Selection = Literal["all"] | tuple[Literal["tags"], list[Tag]] | tuple[Literal["names"], list[str]]

ServiceConfig = Mapping[str, LimitsActivated | HostAssignment | Selection | None] | None


class AwsParams(BaseModel):
    auth: (
        tuple[Literal["access_key_sts"], AuthAccessKeySts]
        | tuple[Literal["access_key"], AuthAccessKey]
        | tuple[Literal["sts"], AuthSts]
        | Literal["none"]
        | None
    ) = None
    proxy_details: ProxyDetails | None = None
    access: APIAccess | None = None
    global_services: Mapping[str, ServiceConfig] | None = None
    regions: list[str] | None = None
    regional_services: Mapping[str, ServiceConfig] | None = None
    piggyback_naming_convention: Literal["ip_region_instance", "private_dns_name"]
    overall_tags: list[Tag] | None = None
    import_tags: tuple[str, str | None] | None = None
    connection_test: bool = False  # only used by quick setup


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
    args: list[str | Secret] = []

    auth = params.auth
    access = params.access or APIAccess()

    match auth:
        case ("sts", sts):
            assert isinstance(sts, AuthSts)
            args.extend(("--assume-role", "--role-arn", sts.role_arn_id))
            if sts.external_id:
                args.extend(("--external-id", sts.external_id))
        case ("access_key", ak):
            assert isinstance(ak, AuthAccessKey)
            args.extend(("--access-key-id", ak.access_key_id))
            args.extend(("--secret-access-key-reference", ak.secret_access_key))
        case ("access_key_sts", aksts):
            assert isinstance(aksts, AuthAccessKeySts)
            args.extend(("--access-key-id", aksts.access_key_id))
            args.extend(("--secret-access-key-reference", aksts.secret_access_key))
            args.extend(("--assume-role", "--role-arn", aksts.role_arn_id))
            if aksts.external_id:
                args.extend(("--external-id", aksts.external_id))
        case ("none", _):
            ...

    if params.proxy_details:
        args.extend(_proxy_args(params.proxy_details))

    if global_service_region := access.global_service_region:
        args.extend(("--global-service-region", global_service_region))

    if params.regions:
        args.extend(("--regions", *params.regions))
    global_services = params.global_services or {}
    if global_service_args := _get_services_args(global_services):
        args.extend(("--global-services", *global_service_args))
    services = params.regional_services or {}
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
    if (import_tags := params.import_tags) is None:
        args.append("--ignore-all-tags")
    elif isinstance(import_tags, tuple) and import_tags[0] == "filter_tags":
        if not isinstance(import_tags[1], str):
            raise ValueError(f"Invalid value for tag filtering pattern: {import_tags[1]}")
        args.extend(("--import-matching-tags-as-labels", import_tags[1]))

    args.extend(
        (
            "--hostname",
            host_config.name,
            "--piggyback-naming-convention",
            params.piggyback_naming_convention,
        )
    )

    if params.connection_test:
        args.append("--connection-test")

    yield SpecialAgentCommand(command_arguments=args)


special_agent_aws = SpecialAgentConfig(
    name="aws",
    parameter_parser=AwsParams.model_validate,
    commands_function=aws_arguments,
)
