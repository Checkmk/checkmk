#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import agent_aws_main, parse_arguments
from cmk.testlib.aws_v2.fake_sts import FakeSts, ROLE, TEMPORARY_KEY_ID

# Keyless: no --access-key-identity and no --secret, so boto3 walks the provider chain.
KEYLESS_ARGS = [
    "--hostname",
    "aws-host",
    "--piggyback-naming-convention",
    "ip_region_instance",
    "--region",
    "eu-central-1",
    "--service",
    "ec2",
]


ACCESS_KEY_ARGS = [*KEYLESS_ARGS, "--access-key-identity", "AKIAHUB", "--secret", "secret"]


def test_role_options_reach_the_assume_role_call(fake_sts: FakeSts) -> None:
    role_args = ["--assume-role", "--role-arn", ROLE, "--external-id", "tenant-42"]

    exit_code = agent_aws_main(parse_arguments([*ACCESS_KEY_ARGS, *role_args, "--connection-test"]))

    assert exit_code == 0
    [call] = fake_sts.assume_role_calls
    assert (call.params["RoleArn"], call.params["ExternalId"]) == (ROLE, "tenant-42")


def test_empty_external_id_is_not_sent(fake_sts: FakeSts) -> None:
    role_args = ["--assume-role", "--role-arn", ROLE, "--external-id", ""]

    exit_code = agent_aws_main(parse_arguments([*ACCESS_KEY_ARGS, *role_args, "--connection-test"]))

    assert exit_code == 0
    [call] = fake_sts.assume_role_calls
    assert "ExternalId" not in call.params


def test_role_arn_without_assume_role_flag_assumes_nothing(fake_sts: FakeSts) -> None:
    exit_code = agent_aws_main(
        parse_arguments([*ACCESS_KEY_ARGS, "--role-arn", ROLE, "--connection-test"])
    )

    assert exit_code == 0
    assert fake_sts.assume_role_calls == []


def test_assume_role_names_the_session_after_the_site(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OMD_SITE", "mysite")

    exit_code = agent_aws_main(
        parse_arguments(
            [*ACCESS_KEY_ARGS, "--assume-role", "--role-arn", ROLE, "--connection-test"]
        )
    )

    assert exit_code == 0
    [call] = fake_sts.assume_role_calls
    assert call.params["RoleSessionName"] == "checkmk-mysite"


def test_assume_role_outside_a_site_names_the_session_checkmk(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OMD_SITE", raising=False)

    exit_code = agent_aws_main(
        parse_arguments(
            [*ACCESS_KEY_ARGS, "--assume-role", "--role-arn", ROLE, "--connection-test"]
        )
    )

    assert exit_code == 0
    [call] = fake_sts.assume_role_calls
    assert call.params["RoleSessionName"] == "checkmk"


def test_one_assume_role_serves_every_region(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    regions = ["eu-central-1", "eu-west-1", "us-east-2"]
    region_args = [arg for region in regions for arg in ("--region", region)]
    args = [
        "--hostname",
        "aws-host",
        "--piggyback-naming-convention",
        "ip_region_instance",
        "--access-key-identity",
        "AKIAHUB",
        "--secret",
        "secret",
        "--assume-role",
        "--role-arn",
        ROLE,
        "--service",
        "sns",
        *region_args,
    ]

    exit_code = agent_aws_main(parse_arguments(args))

    assert exit_code == 0
    assert len(fake_sts.assume_role_calls) == 1
    assert {(r.key_id, r.region) for r in fake_sts.service_requests if r.service == "sns"} == {
        (TEMPORARY_KEY_ID, region) for region in regions
    }


SPOKE_ARGS = [
    *ACCESS_KEY_ARGS,
    "--account",
    "333333333333",
    "--account",
    "444444444444",
    "--spoke-role-name",
    "CheckmkMonitoring",
]


def test_account_options_reach_the_assume_role_calls(fake_sts: FakeSts) -> None:
    exit_code = agent_aws_main(
        parse_arguments([*SPOKE_ARGS, "--spoke-external-id", "tenant-42", "--connection-test"])
    )

    assert exit_code == 0
    assert [(c.params["RoleArn"], c.params["ExternalId"]) for c in fake_sts.assume_role_calls] == [
        ("arn:aws:iam::333333333333:role/CheckmkMonitoring", "tenant-42"),
        ("arn:aws:iam::444444444444:role/CheckmkMonitoring", "tenant-42"),
    ]
