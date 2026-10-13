#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.aws_v2.server_side_calls.agent_aws import special_agent_aws_v2
from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import parse_arguments
from cmk.server_side_calls.v1 import HostConfig, Secret

_MINIMAL_PARAMS: Mapping[str, object] = {
    "auth": ("none", None),
    "piggyback_naming_convention": "ip_region_instance",
}

_HOST_ARGS = ["--hostname", "testhost", "--piggyback-naming-convention", "ip_region_instance"]


def _arguments(**params: object) -> Sequence[str | Secret]:
    (command,) = special_agent_aws_v2({**_MINIMAL_PARAMS, **params}, HostConfig(name="testhost"))
    return command.command_arguments


def test_access_key_is_passed_as_secret() -> None:
    arguments = _arguments(
        auth=("access_key", {"access_key_id": "my_key_id", "secret_access_key": Secret(0)})
    )

    assert arguments == [
        "--access-key-identity",
        "my_key_id",
        "--secret-id",
        Secret(0),
        *_HOST_ARGS,
    ]


def test_role_is_assumed_with_its_external_id() -> None:
    arguments = _arguments(auth=("sts", {"role_arn_id": "my_role", "external_id": "my_id"}))

    assert arguments == [
        "--assume-role",
        "--role-arn",
        "my_role",
        "--external-id",
        "my_id",
        *_HOST_ARGS,
    ]


def test_access_key_and_role_are_both_passed() -> None:
    arguments = _arguments(
        auth=(
            "access_key_sts",
            {
                "access_key_id": "my_key_id",
                "secret_access_key": Secret(0),
                "role_arn_id": "my_role",
            },
        )
    )

    assert arguments == [
        "--access-key-identity",
        "my_key_id",
        "--secret-id",
        Secret(0),
        "--assume-role",
        "--role-arn",
        "my_role",
        *_HOST_ARGS,
    ]


def test_proxy_password_is_passed_as_secret() -> None:
    arguments = _arguments(
        proxy_details={
            "proxy_host": "proxy.example.com",
            "proxy_port": 3128,
            "proxy_user": "my_user",
            "proxy_password": Secret(1),
        }
    )

    assert arguments == [
        "--proxy-host",
        "proxy.example.com",
        "--proxy-port",
        "3128",
        "--proxy-user",
        "my_user",
        "--proxysecret-id",
        Secret(1),
        *_HOST_ARGS,
    ]


def test_regions_are_passed_with_their_aws_ids() -> None:
    arguments = _arguments(
        global_service_region="us_gov_west_1", regions=["eu_central_1", "us_east_1"]
    )

    assert arguments == [
        "--global-service-region",
        "us-gov-west-1",
        "--region",
        "eu-central-1",
        "--region",
        "us-east-1",
        *_HOST_ARGS,
    ]


def test_service_that_is_not_monitored_is_not_passed() -> None:
    assert _arguments(regional_services={"ec2": ("none", None)}) == _HOST_ARGS


def test_global_service_is_passed_as_global_service() -> None:
    assert _arguments(global_services={"ce": ("all", {})}) == [
        "--global-service",
        "ce",
        *_HOST_ARGS,
    ]


def test_service_limits_are_requested() -> None:
    assert _arguments(regional_services={"ec2": ("all", {"limits": True})}) == [
        "--service",
        "ec2",
        "--ec2-limits",
        *_HOST_ARGS,
    ]


def test_service_is_restricted_to_the_given_names() -> None:
    arguments = _arguments(regional_services={"ebs": ("names", {"names": ["vol1", "vol2"]})})

    assert arguments == [
        "--service",
        "ebs",
        "--ebs-name",
        "vol1",
        "--ebs-name",
        "vol2",
        *_HOST_ARGS,
    ]


def test_tag_key_is_repeated_for_every_tag_value() -> None:
    arguments = _arguments(
        regional_services={"s3": ("tags", {"tags": [{"key": "env", "values": ["prod", "dev"]}]})}
    )

    assert arguments == [
        "--service",
        "s3",
        "--s3-tag-key",
        "env",
        "--s3-tag-value",
        "prod",
        "--s3-tag-key",
        "env",
        "--s3-tag-value",
        "dev",
        *_HOST_ARGS,
    ]


def test_cloudwatch_alarms_are_restricted_by_alarm_name() -> None:
    arguments = _arguments(
        regional_services={"cloudwatch_alarms": ("names", {"names": ["my_alarm"]})}
    )

    assert arguments == [
        "--service",
        "cloudwatch_alarms",
        "--cloudwatch-alarm",
        "my_alarm",
        *_HOST_ARGS,
    ]


# fmt: off
@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param({"regional_services": {"s3": ("all", {"requests": True})}}, ["--service", "s3", "--s3-requests"], id="S3 request metrics"),
        pytest.param({"regional_services": {"wafv2": ("all", {"cloudfront": True})}}, ["--service", "wafv2", "--wafv2-cloudfront"], id="CloudFront WAFs"),
        pytest.param({"global_services": {"cloudfront": ("all", {"host_assignment": "domain_host"})}}, ["--global-service", "cloudfront", "--cloudfront-host-assignment", "domain_host"], id="CloudFront host assignment"),
    ],
)
# fmt: on
def test_service_specific_option_is_passed(
    params: Mapping[str, object], expected: Sequence[str]
) -> None:
    assert _arguments(**params) == [*expected, *_HOST_ARGS]


def test_overall_tags_are_passed() -> None:
    arguments = _arguments(overall_tags=[{"key": "team", "values": ["cloud"]}])

    assert arguments == [
        "--overall-tag-key",
        "team",
        "--overall-tag-value",
        "cloud",
        *_HOST_ARGS,
    ]


# fmt: off
@pytest.mark.parametrize(
    ("import_tags", "expected"),
    [
        pytest.param(("all_tags", None), [], id="import all tags"),
        pytest.param(("filter_tags", "^cmk"), ["--import-matching-tags-as-labels", "^cmk"], id="import matching tags"),
        pytest.param(("ignore_tags", None), ["--ignore-all-tags"], id="import no tags"),
    ],
)
# fmt: on
def test_tag_import_follows_the_rule(
    import_tags: tuple[str, str | None], expected: Sequence[str]
) -> None:
    assert _arguments(import_tags=import_tags) == [*expected, *_HOST_ARGS]


def test_connection_test_is_requested() -> None:
    assert _arguments(connection_test=True) == [*_HOST_ARGS, "--connection-test"]


def test_agent_accepts_the_arguments_of_every_option() -> None:
    arguments = _arguments(
        auth=(
            "access_key_sts",
            {
                "access_key_id": "my_key_id",
                "secret_access_key": Secret(0),
                "role_arn_id": "my_role",
                "external_id": "my_id",
            },
        ),
        proxy_details={
            "proxy_host": "proxy.example.com",
            "proxy_port": 3128,
            "proxy_user": "my_user",
            "proxy_password": Secret(1),
        },
        global_service_region="us_gov_west_1",
        regions=["eu_central_1"],
        global_services={
            "ce": ("all", {}),
            "cloudfront": (
                "tags",
                {"tags": [{"key": "env", "values": ["prod"]}], "host_assignment": "domain_host"},
            ),
        },
        regional_services={
            "s3": ("all", {"limits": True, "requests": True}),
            "wafv2": ("all", {"cloudfront": True}),
            "aws_lambda": ("names", {"names": ["my_function"]}),
            "cloudwatch_alarms": ("names", {"names": ["my_alarm"]}),
        },
        overall_tags=[{"key": "team", "values": ["cloud"]}],
        import_tags=("filter_tags", "^cmk"),
        connection_test=True,
    )
    # The backend replaces every secret with a reference to the password store.
    command_line = [arg if isinstance(arg, str) else "password_store_reference" for arg in arguments]

    parsed = parse_arguments(command_line)

    assert (parsed.global_services, parsed.services) == (
        ["ce", "cloudfront"],
        ["s3", "wafv2", "lambda", "cloudwatch_alarms"],
    )
