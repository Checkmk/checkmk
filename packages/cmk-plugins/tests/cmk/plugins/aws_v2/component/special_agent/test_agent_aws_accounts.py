#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""An agent run over a list of accounts, against the fake STS endpoint."""

import itertools

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import agent_aws_main, parse_arguments
from cmk.testlib.aws_v2.fake_sts import AssumeRoleCall, FakeSts, SignedRequest, temporary_key_id

ACCOUNTS = ["333333333333", "444444444444"]

LIST_MODE_ARGS = [
    "--hostname",
    "aws-org",
    "--piggyback-naming-convention",
    "ip_region_instance",
    "--access-key-identity",
    "AKIAHUB",
    "--secret",
    "secret",
    "--spoke-role-name",
    "CheckmkMonitoring",
    "--region",
    "eu-central-1",
    "--service",
    "sns",
    *(arg for account in ACCOUNTS for arg in ("--account", account)),
]


def _sections_by_host(output: str) -> dict[str | None, list[str]]:
    """Every line of the agent output, grouped by its piggyback host. None is the rule host."""
    by_host: dict[str | None, list[str]] = {}
    host: str | None = None
    for line in output.splitlines():
        if line.startswith("<<<<") and line.endswith(">>>>"):
            host = line[4:-4] or None
            continue
        by_host.setdefault(host, []).append(line)
    return by_host


@pytest.fixture(name="list_mode_output")
def _list_mode_output(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> dict[str | None, list[str]]:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    agent_aws_main(parse_arguments(LIST_MODE_ARGS))
    return _sections_by_host(capsys.readouterr().out)


def test_every_account_writes_to_its_own_host(
    list_mode_output: dict[str | None, list[str]],
) -> None:
    labels = {
        host: lines[lines.index("<<<labels:sep(0)>>>") + 1]
        for host, lines in list_mode_output.items()
    }

    assert labels == {account: f'{{"cmk/aws/account": "{account}"}}' for account in ACCOUNTS}


def test_list_mode_writes_nothing_to_the_rule_host(
    list_mode_output: dict[str | None, list[str]],
) -> None:
    assert None not in list_mode_output


@pytest.mark.usefixtures("list_mode_output")
def test_every_account_is_queried_with_its_own_credentials(fake_sts: FakeSts) -> None:
    assert {request.key_id for request in fake_sts.service_requests} == {
        temporary_key_id(account) for account in ACCOUNTS
    }


def _steps(calls: list[AssumeRoleCall | SignedRequest]) -> list[str]:
    return [
        f"assume {call.params['RoleArn'].split(':')[4]}"
        if isinstance(call, AssumeRoleCall)
        else f"query {call.key_id.removeprefix('ASIA')}"
        for call in calls
    ]


@pytest.mark.usefixtures("list_mode_output")
def test_each_account_role_is_assumed_right_before_its_account(fake_sts: FakeSts) -> None:
    steps = [step for step, _ in itertools.groupby(_steps(fake_sts.calls))]

    assert steps == [
        f"assume {ACCOUNTS[0]}",
        f"query {ACCOUNTS[0]}",
        f"assume {ACCOUNTS[1]}",
        f"query {ACCOUNTS[1]}",
    ]
