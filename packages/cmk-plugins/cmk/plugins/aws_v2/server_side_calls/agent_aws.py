#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand, SpecialAgentConfig


class AccessKey(BaseModel):
    access_key_id: str
    secret_access_key: Secret


class AssumeRole(BaseModel):
    role_arn_id: str
    external_id: str | None = None


class AccessKeyAndAssumeRole(AccessKey, AssumeRole): ...


class ProxyDetails(BaseModel):
    proxy_host: str
    proxy_port: int | None = None
    proxy_user: str | None = None
    proxy_password: Secret | None = None


class Tag(BaseModel):
    key: str
    values: list[str]


class ServiceOptions(BaseModel):
    names: list[str] = []
    tags: list[Tag] = []
    limits: bool = False
    # S3 only
    requests: bool = False
    # WAFV2 only
    cloudfront: bool = False
    # CloudFront only
    host_assignment: Literal["aws_host", "domain_host"] = "aws_host"


ServiceSelection = (
    tuple[Literal["none"], None] | tuple[Literal["all", "tags", "names"], ServiceOptions]
)


class AwsParams(BaseModel):
    auth: (
        tuple[Literal["access_key"], AccessKey]
        | tuple[Literal["access_key_sts"], AccessKeyAndAssumeRole]
        | tuple[Literal["sts"], AssumeRole]
        | tuple[Literal["none"], None]
    )
    global_service_region: str = "default"
    proxy_details: ProxyDetails | None = None
    regions: list[str] = []
    overall_tags: list[Tag] = []
    import_tags: (
        tuple[Literal["all_tags"], None]
        | tuple[Literal["filter_tags"], str]
        | tuple[Literal["ignore_tags"], None]
    ) = ("all_tags", None)
    global_services: Mapping[str, ServiceSelection] = {}
    regional_services: Mapping[str, ServiceSelection] = {}
    piggyback_naming_convention: Literal["ip_region_instance", "private_dns_name"]
    connection_test: bool = False  # only used by the Quick Setup


def _region_from_formspec_name(formspec_name: str) -> str:
    # Form spec names must be Python identifiers, so the rule stores "eu_central_1".
    return formspec_name.replace("_", "-")


def _service_from_formspec_name(formspec_name: str) -> str:
    # "lambda" is a Python keyword, so the rule stores it as "aws_lambda".
    return "lambda" if formspec_name == "aws_lambda" else formspec_name


def _auth_args(auth: AccessKey | AssumeRole | None) -> list[str | Secret]:
    # AccessKeyAndAssumeRole is both, so it gets the arguments of both.
    args: list[str | Secret] = []
    if isinstance(auth, AccessKey):
        args += ["--access-key-identity", auth.access_key_id, "--secret-id", auth.secret_access_key]
    if isinstance(auth, AssumeRole):
        args += ["--assume-role", "--role-arn", auth.role_arn_id]
        if auth.external_id:
            args += ["--external-id", auth.external_id]
    return args


def _proxy_args(details: ProxyDetails) -> list[str | Secret]:
    args: list[str | Secret] = ["--proxy-host", details.proxy_host]
    if details.proxy_port:
        args += ["--proxy-port", str(details.proxy_port)]
    if details.proxy_user and details.proxy_password:
        args += ["--proxy-user", details.proxy_user, "--proxysecret-id", details.proxy_password]
    return args


def _tag_args(tags: Sequence[Tag], prefix: str) -> list[str]:
    # The agent pairs the n-th key with the n-th value, so the key is repeated for every value.
    return [
        arg
        for tag in tags
        for value in tag.values
        for arg in (f"--{prefix}-tag-key", tag.key, f"--{prefix}-tag-value", value)
    ]


def _service_args(formspec_name: str, selection: ServiceSelection, is_global: bool) -> list[str]:
    kind, options = selection
    if options is None:
        return []

    service = _service_from_formspec_name(formspec_name)
    args = ["--global-service" if is_global else "--service", service]
    if options.limits:
        args.append(f"--{service}-limits")
    if kind == "names":
        name_option = (
            "--cloudwatch-alarm" if service == "cloudwatch_alarms" else f"--{service}-name"
        )
        args += [arg for name in options.names for arg in (name_option, name)]
    if kind == "tags":
        args += _tag_args(options.tags, service)
    if service == "s3" and options.requests:
        args.append("--s3-requests")
    if service == "wafv2" and options.cloudfront:
        args.append("--wafv2-cloudfront")
    if service == "cloudfront":
        args += ["--cloudfront-host-assignment", options.host_assignment]
    return args


def _import_tags_args(import_tags: tuple[str, str | None]) -> list[str]:
    kind, pattern = import_tags
    if kind == "filter_tags" and pattern is not None:
        return ["--import-matching-tags-as-labels", pattern]
    if kind == "ignore_tags":
        return ["--ignore-all-tags"]
    return []


def aws_arguments(params: AwsParams, host_config: HostConfig) -> Iterable[SpecialAgentCommand]:
    args = _auth_args(params.auth[1])
    if params.proxy_details:
        args += _proxy_args(params.proxy_details)
    if params.global_service_region != "default":
        args += [
            "--global-service-region",
            _region_from_formspec_name(params.global_service_region),
        ]
    for region in params.regions:
        args += ["--region", _region_from_formspec_name(region)]
    for name, selection in params.global_services.items():
        args += _service_args(name, selection, is_global=True)
    for name, selection in params.regional_services.items():
        args += _service_args(name, selection, is_global=False)
    args += _tag_args(params.overall_tags, "overall")
    args += _import_tags_args(params.import_tags)
    args += [
        "--hostname",
        host_config.name,
        "--piggyback-naming-convention",
        params.piggyback_naming_convention,
    ]
    if params.connection_test:
        args.append("--connection-test")
    yield SpecialAgentCommand(command_arguments=args)


special_agent_aws_v2 = SpecialAgentConfig(
    name="aws_v2",
    parameter_parser=AwsParams.model_validate,
    commands_function=aws_arguments,
)
