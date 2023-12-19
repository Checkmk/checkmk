#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# TIME WASTED TRYING TO TYPE PARAMS: 4h
# (see patch 8 of gerrit change 67437; its probably easier to simplify the valuespec first)


from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    noop_parser,
    parse_secret,
    Secret,
    SpecialAgentCommand,
    SpecialAgentConfig,
)


def _get_tag_options(tag_values: list[tuple[str, list[str]]], prefix: str) -> list[str]:
    options = []
    for key, values in tag_values:
        options.append("--%s-tag-key" % prefix)
        options.append(key)
        options.append("--%s-tag-values" % prefix)
        options += values
    return options


def _get_services_config(services):
    # '--services': {
    #   's3': {'selection': ('tags', [('KEY', ['VAL1', 'VAL2'])])},
    #   'ec2': {'selection': 'all'},
    #   'ebs': {'selection': ('names', ['ebs1', 'ebs2'])},
    # }
    service_args = []
    for service_name, service_config in services.items():
        if service_config is None:
            continue

        if service_config.get("limits"):
            service_args += ["--%s-limits" % service_name]

        selection = service_config.get("selection")
        if not isinstance(selection, tuple):
            # Here: value of selection is 'all' which means there's no
            # restriction (names or tags) to the instances of a specific
            # AWS service. The command-line option already includes this
            # service '--services SERVICE1 SERVICE2 ...' (see below).
            continue

        if not selection[1]:
            continue

        if selection[0] == "names":
            service_args.append("--%s-names" % service_name)
            service_args += selection[1]

        elif selection[0] == "tags":
            service_args += _get_tag_options(selection[1], service_name)
    return service_args


def _proxy_args(details: Mapping[str, Any]) -> Sequence[str | Secret]:
    proxy_args = ["--proxy-host", details["proxy_host"]]

    if proxy_port := details.get("proxy_port"):
        proxy_args += ["--proxy-port", str(proxy_port)]

    if (proxy_user := details.get("proxy_user")) and (proxy_pwd := details.get("proxy_password")):
        proxy_args += [
            "--proxy-user",
            proxy_user,
            "--proxy-password",
            parse_secret(proxy_pwd[0], proxy_pwd[1]),
        ]
    return proxy_args


def agent_aws_arguments(  # pylint: disable=too-many-branches
    params: Any, hostname: str
) -> Iterator[str]:
    yield from [
        "--access-key-id",
        params["access_key_id"],
        "--secret-access-key",
        parse_secret(params["secret_access_key"][0], params["secret_access_key"][1]),
        *(_proxy_args(params["proxy_details"]) if "proxy_details" in params else []),
    ]

    global_service_region = params.get("access", {}).get("global_service_region")
    if global_service_region is not None:
        yield from ["--global-service-region", global_service_region]

    role_arn_id = params.get("access", {}).get("role_arn_id")
    if role_arn_id:
        yield "--assume-role"
        if role_arn_id[0]:
            yield from ["--role-arn", role_arn_id[0]]
        if role_arn_id[1]:
            yield from ["--external-id", role_arn_id[1]]

    regions = params.get("regions")
    if regions:
        yield "--regions"
        yield from regions

    global_services = params.get("global_services", {})
    if global_services:
        yield "--global-services"
        # We need to sort the inner services-as-a-dict-params
        # in order to create reliable tests
        yield from sorted(global_services)
        yield from _get_services_config(global_services)  # type: ignore[arg-type]

    services = params.get("services", {})

    if services:
        yield "--services"
        # We need to sort the inner services-as-a-dict-params
        # in order to create reliable tests
        yield from sorted(services)
        yield from _get_services_config(services)  # type: ignore[arg-type]

    if "requests" in services.get("s3", {}):
        yield "--s3-requests"

    alarms = services.get("cloudwatch_alarms", {}).get("alarms")
    if alarms:
        # {'alarms': 'all'} is handled by no additionally specified names
        yield "--cloudwatch-alarms"
        if isinstance(alarms, tuple):
            yield from alarms[1]

    if "cloudfront" in services.get("wafv2", {}):
        yield "--wafv2-cloudfront"

    if "cloudfront" in global_services:
        cloudfront_host_assignment = global_services["cloudfront"]["host_assignment"]
        yield from ["--cloudfront-host-assignment", cloudfront_host_assignment]

    # '--overall-tags': [('KEY_1', ['VAL_1', 'VAL_2']), ...)],
    yield from _get_tag_options(params.get("overall_tags", []), "overall")
    yield from [
        "--hostname",
        hostname,
    ]
    yield from ("--piggyback-naming-convention", params["piggyback_naming_convention"])


def generate_aws_commands(
    params: object,
    host_config: HostConfig,
    _http_proxies: Mapping[str, HTTPProxy],
) -> Iterator[SpecialAgentCommand]:
    yield SpecialAgentCommand(command_arguments=list(agent_aws_arguments(params, host_config.name)))


special_agent_aws = SpecialAgentConfig(
    name="aws",
    parameter_parser=noop_parser,
    commands_function=generate_aws_commands,
)
