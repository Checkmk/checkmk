#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""An agent run over a list of accounts, against the fake STS endpoint."""

import itertools
import json

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import agent_aws_main, parse_arguments
from cmk.testlib.aws_v2.fake_sts import (
    AssumeRoleCall,
    DENIED_ACCOUNT,
    FakeSts,
    NOT_ENABLED_REGION,
    SCP_DENIED_ACCOUNT,
    SignedRequest,
    temporary_key_id,
)

ACCOUNTS = ["333333333333", "444444444444"]

LOGIN_ARGS = [
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
]


def _account_args(accounts: list[str]) -> list[str]:
    return [arg for account in accounts for arg in ("--account", account)]


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
    agent_aws_main(parse_arguments([*LOGIN_ARGS, *_account_args(ACCOUNTS)]))
    return _sections_by_host(capsys.readouterr().out)


def test_every_account_writes_to_its_own_host(
    list_mode_output: dict[str | None, list[str]],
) -> None:
    labels = {
        host: lines[lines.index("<<<labels:sep(0)>>>") + 1]
        for host, lines in list_mode_output.items()
        if host is not None
    }

    assert labels == {account: f'{{"cmk/aws/account": "{account}"}}' for account in ACCOUNTS}


def test_list_mode_writes_only_the_agent_info_to_the_rule_host(
    list_mode_output: dict[str | None, list[str]],
) -> None:
    assert list_mode_output[None] == [
        "<<<aws_v2_agent_info:sep(0)>>>",
        *(f'{{"status": "ok", "account": "{account}"}}' for account in ACCOUNTS),
    ]


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


@pytest.fixture(name="output_with_unreachable_account")
def _output_with_unreachable_account(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> dict[str | None, list[str]]:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    accounts = [ACCOUNTS[0], DENIED_ACCOUNT, ACCOUNTS[1]]
    agent_aws_main(parse_arguments([*LOGIN_ARGS, *_account_args(accounts)]))
    return _sections_by_host(capsys.readouterr().out)


def test_unreachable_account_leaves_the_others_complete(
    output_with_unreachable_account: dict[str | None, list[str]],
) -> None:
    assert set(output_with_unreachable_account) == {None, *ACCOUNTS}


def test_unreachable_account_is_one_error_in_the_agent_info(
    output_with_unreachable_account: dict[str | None, list[str]],
) -> None:
    rows = [json.loads(line) for line in output_with_unreachable_account[None][1:]]

    assert [(row["status"], row["account"], "reason" in row) for row in rows] == [
        ("ok", ACCOUNTS[0], False),
        ("error", DENIED_ACCOUNT, True),
        ("ok", ACCOUNTS[1], False),
    ]


def test_failed_login_is_a_run_error_in_the_agent_info(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    login_args = [
        arg
        for arg in LOGIN_ARGS
        if arg not in ("--access-key-identity", "AKIAHUB", "--secret", "secret")
    ]

    agent_aws_main(parse_arguments([*login_args, *_account_args(ACCOUNTS)]))

    [header, row] = _sections_by_host(capsys.readouterr().out)[None][-2:]
    assert (header, set(json.loads(row))) == (
        "<<<aws_v2_agent_info:sep(0)>>>",
        {"status", "reason"},
    )


def _agent_info(
    fake_sts: FakeSts,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> list[dict[str, str]]:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    agent_aws_main(parse_arguments(args))
    return [json.loads(line) for line in _sections_by_host(capsys.readouterr().out)[None][1:]]


def test_run_without_regions_queries_the_global_services(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    regional = ("--region", "eu-central-1", "--service", "sns")
    args = [arg for arg in LOGIN_ARGS if arg not in regional]

    rows = _agent_info(
        fake_sts, monkeypatch, capsys, [*args, "--global-service", "ce", *_account_args(ACCOUNTS)]
    )

    assert [row["status"] for row in rows] == ["ok", "ok"]


def test_region_not_enabled_is_info_for_its_account(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [*LOGIN_ARGS, "--region", NOT_ENABLED_REGION, *_account_args(ACCOUNTS[:1])]

    assert {"account": ACCOUNTS[0], "region": NOT_ENABLED_REGION, "status": "info"}.items() <= (
        _agent_info(fake_sts, monkeypatch, capsys, args)[1].items()
    )


def test_region_not_enabled_is_not_queried(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [*LOGIN_ARGS, "--region", NOT_ENABLED_REGION, *_account_args(ACCOUNTS[:1])]
    _agent_info(fake_sts, monkeypatch, capsys, args)

    assert NOT_ENABLED_REGION not in {
        request.region for request in fake_sts.service_requests if request.service == "sns"
    }


def test_deny_of_a_service_control_policy_is_info_not_error(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = _agent_info(
        fake_sts, monkeypatch, capsys, [*LOGIN_ARGS, *_account_args([SCP_DENIED_ACCOUNT])]
    )

    assert {(row["status"], row.get("region")) for row in rows} == {
        ("ok", None),
        ("info", "eu-central-1"),
    }
