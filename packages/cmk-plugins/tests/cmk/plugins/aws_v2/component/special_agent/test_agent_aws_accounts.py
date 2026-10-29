#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""An agent run over several accounts, against the fake STS endpoint."""

import itertools
import json
import re

import pytest

from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import agent_aws_main, parse_arguments
from cmk.testlib.aws_v2.fake_sts import (
    ACTIVE_ORGANIZATION_ACCOUNTS,
    AssumeRoleCall,
    DENIED_ACCOUNT,
    FakeSts,
    HUB_ACCOUNT,
    LIST_ROLE,
    MANAGEMENT_ACCOUNT,
    NO_LIST_KEY_ID,
    NOT_ENABLED_REGION,
    ROLE,
    ROLE_ACCOUNT,
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


def test_each_account_role_is_assumed_right_before_its_account(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch
) -> None:
    # With one job at a time the order is exact. More jobs look ahead by as many accounts.
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    agent_aws_main(parse_arguments([*LOGIN_ARGS, *_account_args(ACCOUNTS)]), parallel_jobs=1)

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


def _hosts(
    fake_sts: FakeSts,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> set[str | None]:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    agent_aws_main(parse_arguments(args))
    return set(_sections_by_host(capsys.readouterr().out))


def test_organization_mode_gives_every_active_account_its_own_host(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hosts = _hosts(fake_sts, monkeypatch, capsys, [*LOGIN_ARGS, "--organization"])

    assert hosts == {None, *ACTIVE_ORGANIZATION_ACCOUNTS}


def test_excluded_account_of_the_organization_gets_no_host(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [*LOGIN_ARGS, "--organization", "--exclude-account", MANAGEMENT_ACCOUNT]

    assert MANAGEMENT_ACCOUNT not in _hosts(fake_sts, monkeypatch, capsys, args)


def test_account_list_role_lists_the_accounts_of_the_organization(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [*LOGIN_ARGS, "--organization", "--account-list-role-arn", LIST_ROLE]
    _hosts(fake_sts, monkeypatch, capsys, args)

    assert {call.key_id for call in fake_sts.list_accounts_calls} == {
        temporary_key_id(MANAGEMENT_ACCOUNT)
    }


def test_failed_listing_is_a_run_error_in_the_agent_info(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    args = [NO_LIST_KEY_ID if arg == "AKIAHUB" else arg for arg in LOGIN_ARGS]

    agent_aws_main(parse_arguments([*args, "--organization"]))

    [header, row] = _sections_by_host(capsys.readouterr().out)[None][-2:]
    assert (header, json.loads(row)["reason"].split(":")[0]) == (
        "<<<aws_v2_agent_info:sep(0)>>>",
        "Cannot list the accounts in the organization",
    )


def test_organization_without_an_account_to_monitor_is_a_run_error(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    excluded = [
        arg for account in ACTIVE_ORGANIZATION_ACCOUNTS for arg in ("--exclude-account", account)
    ]

    agent_aws_main(parse_arguments([*LOGIN_ARGS, "--organization", *excluded]))

    [header, row] = _sections_by_host(capsys.readouterr().out)[None][-2:]
    assert (header, set(json.loads(row)), json.loads(row)["status"]) == (
        "<<<aws_v2_agent_info:sep(0)>>>",
        {"status", "reason"},
        "error",
    )


SINGLE_ACCOUNT_ARGS = [
    arg for arg in LOGIN_ARGS if arg not in ("--spoke-role-name", "CheckmkMonitoring")
]


def test_single_account_gets_its_own_host(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _hosts(fake_sts, monkeypatch, capsys, SINGLE_ACCOUNT_ARGS) == {None, HUB_ACCOUNT}


def test_single_account_leaves_only_the_agent_info_on_the_rule_host(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    agent_aws_main(parse_arguments(SINGLE_ACCOUNT_ARGS))

    assert _sections_by_host(capsys.readouterr().out)[None] == [
        "<<<aws_v2_agent_info:sep(0)>>>",
        f'{{"status": "ok", "account": "{HUB_ACCOUNT}"}}',
    ]


def test_assumed_role_account_gets_its_own_host(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    args = [*SINGLE_ACCOUNT_ARGS, "--assume-role", "--role-arn", ROLE]

    assert _hosts(fake_sts, monkeypatch, capsys, args) == {None, ROLE_ACCOUNT}


def _two_regions_with_s3() -> list[str]:
    return [
        *LOGIN_ARGS,
        *_account_args(ACCOUNTS),
        "--region",
        "eu-west-1",
        "--service",
        "s3",
        "--s3-limits",
        "--no-cache",
    ]


def _run(
    fake_sts: FakeSts,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    parallel_jobs: int,
) -> str:
    monkeypatch.setenv("AWS_ENDPOINT_URL", fake_sts.url)
    agent_aws_main(parse_arguments(_two_regions_with_s3()), parallel_jobs=parallel_jobs)
    # The cache timestamps in the section headers differ from run to run.
    return re.sub(r":cached\(\d+,", ":cached(<time>,", capsys.readouterr().out)


def test_parallel_jobs_give_the_same_output_as_one_job(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    one_job = _run(fake_sts, monkeypatch, capsys, 1)

    assert _run(fake_sts, monkeypatch, capsys, 4) == one_job


def test_s3_limits_are_written_once_per_account_with_parallel_regions(
    fake_sts: FakeSts, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    output = _sections_by_host(_run(fake_sts, monkeypatch, capsys, 4))

    assert {
        account: sum(line.startswith("<<<aws_v2_s3_limits") for line in output[account])
        for account in ACCOUNTS
    } == dict.fromkeys(ACCOUNTS, 1)
