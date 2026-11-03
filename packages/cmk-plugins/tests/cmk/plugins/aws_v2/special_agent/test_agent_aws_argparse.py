#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import parse_arguments
from cmk.plugins.aws_v2.special_agent.config import NamingConvention, TagsImportPatternOption

# These have to always exist, so just set them here
REQUIRED_ARGS = ["--hostname", "foo", "--piggyback-naming-convention", "ip_region_instance"]


@pytest.mark.parametrize(
    "args, expected",
    [
        (
            REQUIRED_ARGS,
            {
                "hostname": "foo",
                "piggyback_naming_convention": NamingConvention.ip_region_instance,
                "tag_key_pattern": TagsImportPatternOption.import_all,
            },
        ),
        (
            REQUIRED_ARGS
            + [
                "--region",
                "af-south-1",
                "--region",
                "ap-east-1",
                "--region",
                "us-west-2",
                "--wafv2-cloudfront",
            ],
            {
                "hostname": "foo",
                "piggyback_naming_convention": NamingConvention.ip_region_instance,
                "tag_key_pattern": TagsImportPatternOption.import_all,
                "regions": ["af-south-1", "ap-east-1", "us-west-2"],
                "wafv2_cloudfront": True,
            },
        ),
        (
            REQUIRED_ARGS
            + [
                "--region",
                "af-south-1",
                "--region",
                "ap-east-1",
                "--global-service",
                "ce",
                "--global-service",
                "cloudfront",
                "--service",
                "ebs",
                "--service",
                "s3",
                "--wafv2-cloudfront",
                "--cloudwatch-alarm",
                "alarm1",
                "--cloudwatch-alarm",
                "well-thats-quite-alarming",
                "--overall-tag-key",
                "ohno",
                "--overall-tag-value",
                "mehr",
                "--overall-tag-value",
                "Werte",
                "--overall-tag-value",
                "auch",
                "--overall-tag-value",
                "auf",
                "--overall-tag-value",
                "Deutsch!",
                "--s3-name",
                "no",
                "--s3-name",
                "nargs",
                "--s3-limits",
            ],
            {
                "hostname": "foo",
                "piggyback_naming_convention": NamingConvention.ip_region_instance,
                "tag_key_pattern": TagsImportPatternOption.import_all,
                "regions": ["af-south-1", "ap-east-1"],
                "global_services": ["ce", "cloudfront"],
                "services": ["ebs", "s3"],
                "wafv2_cloudfront": True,
                "cloudwatch_alarms": ["alarm1", "well-thats-quite-alarming"],
                "overall_tag_keys": ["ohno"],
                "overall_tag_values": [
                    "mehr",
                    "Werte",
                    "auch",
                    "auf",
                    "Deutsch!",
                ],
                "s3_names": ["no", "nargs"],
                "s3_limits": True,
            },
        ),
    ],
)
def test_parse_arguments(args: Sequence[str], expected: Mapping[str, Any]) -> None:  # type: ignore[misc]
    ns = parse_arguments(args)
    for prop, value in expected.items():
        assert getattr(ns, prop) == value


def test_access_key_without_secret_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        parse_arguments([*REQUIRED_ARGS, "--access-key-identity", "AKIAEXAMPLE"])

    assert "--access-key-identity requires --secret or --secret-id" in capsys.readouterr().err


@pytest.mark.parametrize(
    "secret_args",
    [
        pytest.param(["--secret", "secret"], id="secret"),
        pytest.param(["--secret-id", "password_store_id"], id="secret id"),
    ],
)
def test_access_key_with_secret_is_accepted(secret_args: Sequence[str]) -> None:
    args = parse_arguments([*REQUIRED_ARGS, "--access-key-identity", "AKIAEXAMPLE", *secret_args])

    assert args.access_key_identity == "AKIAEXAMPLE"


ACCOUNT_ARGS = [
    *REQUIRED_ARGS,
    "--account",
    "333333333333",
    "--account",
    "444444444444",
    "--spoke-role-name",
    "CheckmkMonitoring",
]


def test_account_options_are_parsed() -> None:
    args = parse_arguments([*ACCOUNT_ARGS, "--spoke-external-id", "tenant-42"])

    assert (args.accounts, args.spoke_role_name, args.spoke_external_id) == (
        ["333333333333", "444444444444"],
        "CheckmkMonitoring",
        "tenant-42",
    )


def test_account_without_spoke_role_name_is_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_arguments([*REQUIRED_ARGS, "--account", "333333333333"])


def test_account_with_assumed_role_is_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_arguments([*ACCOUNT_ARGS, "--assume-role", "--role-arn", "arn:aws:iam::1:role/Other"])


@pytest.mark.parametrize(
    "spoke_args",
    [
        pytest.param(["--spoke-role-name", "CheckmkMonitoring"], id="role name"),
        pytest.param(["--spoke-external-id", "tenant-42"], id="external id"),
    ],
)
def test_spoke_options_without_account_are_rejected(spoke_args: Sequence[str]) -> None:
    with pytest.raises(SystemExit):
        parse_arguments([*REQUIRED_ARGS, *spoke_args])


def test_assume_role_without_role_arn_is_rejected() -> None:
    with pytest.raises(SystemExit):
        parse_arguments([*REQUIRED_ARGS, "--assume-role"])


ORGANIZATION_ARGS = [*REQUIRED_ARGS, "--organization", "--spoke-role-name", "CheckmkMonitoring"]


def test_organization_options_are_parsed() -> None:
    args = parse_arguments(
        [
            *ORGANIZATION_ARGS,
            "--exclude-account",
            "333333333333",
            "--account-list-role-arn",
            "arn:aws:iam::888888888888:role/CheckmkAccountList",
        ]
    )

    assert (args.organization, args.excluded_accounts, args.account_list_role_arn) == (
        True,
        ["333333333333"],
        "arn:aws:iam::888888888888:role/CheckmkAccountList",
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param([*REQUIRED_ARGS, "--organization"], id="without role name"),
        pytest.param([*ORGANIZATION_ARGS, "--account", "333333333333"], id="with account"),
        pytest.param(
            [*ORGANIZATION_ARGS, "--assume-role", "--role-arn", "arn:aws:iam::1:role/Other"],
            id="with assumed role",
        ),
        pytest.param(
            [*ACCOUNT_ARGS, "--exclude-account", "333333333333"], id="exclusion without it"
        ),
        pytest.param(
            [*ACCOUNT_ARGS, "--account-list-role-arn", "arn:aws:iam::1:role/List"],
            id="list role without it",
        ),
    ],
)
def test_wrong_organization_options_are_rejected(args: Sequence[str]) -> None:
    with pytest.raises(SystemExit):
        parse_arguments(args)
