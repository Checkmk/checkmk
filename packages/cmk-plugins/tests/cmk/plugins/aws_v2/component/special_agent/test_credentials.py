#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import stat
from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.plugins.aws_v2.special_agent.config import AwsAccessError
from cmk.plugins.aws_v2.special_agent.credentials import (
    AccessKey,
    AwsCredentials,
    DefaultCredentials,
    HubCredentials,
    NamedProfile,
    Organization,
    SpokeAccounts,
)
from cmk.testlib.aws_v2.fake_sts import (
    ACTIVE_ORGANIZATION_ACCOUNTS,
    DENIED_ACCOUNT,
    FakeSts,
    HUB_ACCOUNT,
    LIST_ROLE,
    MANAGEMENT_ACCOUNT,
    NO_LIST_KEY_ID,
    ORGANIZATION_ACCOUNT_NAMES,
    temporary_key_id,
)


def _session_account_id(hub: HubCredentials) -> str:
    return AwsCredentials(hub, "us-east-1", None).session_account_id()


@pytest.mark.usefixtures("fake_sts")
def test_access_key_logs_in_to_the_hub_account() -> None:
    assert _session_account_id(HubCredentials(AccessKey("AKIAHUB", "secret"))) == HUB_ACCOUNT


@pytest.mark.usefixtures("fake_sts")
def test_default_credentials_log_in_to_the_hub_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAENV")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    assert _session_account_id(HubCredentials(DefaultCredentials())) == HUB_ACCOUNT


def _configure_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_ids: dict[str, str]
) -> None:
    """Write an AWS config with one profile per key ID, each with a credential_process."""
    sections = []
    for section, key_id in key_ids.items():
        process = tmp_path / f"credential_process_{key_id}.sh"
        output = {"Version": 1, "AccessKeyId": key_id, "SecretAccessKey": "secret"}
        process.write_text(f"#!/bin/sh\necho '{json.dumps(output)}'\n")
        process.chmod(process.stat().st_mode | stat.S_IEXEC)
        sections.append(f"[{section}]\ncredential_process = {process}\n")
    config = tmp_path / "aws_config"
    config.write_text("\n".join(sections))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(config))


@pytest.mark.usefixtures("fake_sts")
def test_named_profile_logs_in_without_a_default_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_profiles(tmp_path, monkeypatch, {"profile checkmk": "AKIAPROFILE"})

    assert _session_account_id(HubCredentials(NamedProfile("checkmk"))) == HUB_ACCOUNT


def test_named_profile_assumes_the_spoke_roles_with_its_own_credentials(
    fake_sts: FakeSts, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_profiles(
        tmp_path, monkeypatch, {"default": "AKIADEFAULT", "profile checkmk": "AKIAPROFILE"}
    )
    credentials = AwsCredentials(
        HubCredentials(NamedProfile("checkmk")),
        "us-east-1",
        None,
        SpokeAccounts(["333333333333"], "CheckmkMonitoring"),
    )

    credentials.open_account(credentials.monitored_account_ids()[0])

    [call] = fake_sts.assume_role_calls
    assert call.caller_key_id == "AKIAPROFILE"


def test_no_role_makes_no_assume_role_call(fake_sts: FakeSts) -> None:
    _session_account_id(HubCredentials(AccessKey("AKIAHUB", "secret")))

    assert fake_sts.assume_role_calls == []


SPOKES = SpokeAccounts(["333333333333", "444444444444"], "CheckmkMonitoring")


def _spoke_accounts(spokes: SpokeAccounts) -> list[tuple[str, str]]:
    """Each monitored account with the account its session really belongs to."""
    credentials = AwsCredentials(
        HubCredentials(AccessKey("AKIAHUB", "secret")), "us-east-1", None, spokes
    )
    return [
        (account.id, account.session.client("sts").get_caller_identity()["Account"])
        for account in map(credentials.open_account, credentials.monitored_account_ids())
    ]


@pytest.mark.usefixtures("fake_sts")
def test_every_spoke_account_gets_a_session_of_that_account() -> None:
    assert _spoke_accounts(SPOKES) == [
        ("333333333333", "333333333333"),
        ("444444444444", "444444444444"),
    ]


def test_spoke_roles_are_assumed_directly_from_the_login(fake_sts: FakeSts) -> None:
    _spoke_accounts(SPOKES)

    assert [(c.caller_key_id, c.params["RoleArn"]) for c in fake_sts.assume_role_calls] == [
        ("AKIAHUB", "arn:aws:iam::333333333333:role/CheckmkMonitoring"),
        ("AKIAHUB", "arn:aws:iam::444444444444:role/CheckmkMonitoring"),
    ]


def test_listing_the_accounts_assumes_no_account_role(fake_sts: FakeSts) -> None:
    AwsCredentials(
        HubCredentials(AccessKey("AKIAHUB", "secret")), "us-east-1", None, SPOKES
    ).monitored_account_ids()

    assert fake_sts.assume_role_calls == []


def test_spoke_external_id_reaches_every_assume_role_call(fake_sts: FakeSts) -> None:
    _spoke_accounts(
        SpokeAccounts(["333333333333", "444444444444"], "CheckmkMonitoring", "tenant-42")
    )

    assert [c.params["ExternalId"] for c in fake_sts.assume_role_calls] == [
        "tenant-42",
        "tenant-42",
    ]


@pytest.mark.usefixtures("fake_sts")
def test_listed_spoke_accounts_have_no_name() -> None:
    credentials = AwsCredentials(
        HubCredentials(AccessKey("AKIAHUB", "secret")), "us-east-1", None, SPOKES
    )

    assert [
        credentials.open_account(account_id).name
        for account_id in credentials.monitored_account_ids()
    ] == [None, None]


@pytest.mark.usefixtures("fake_sts")
def test_denied_spoke_role_names_its_account() -> None:
    with pytest.raises(AwsAccessError, match=DENIED_ACCOUNT):
        _spoke_accounts(SpokeAccounts(["333333333333", DENIED_ACCOUNT], "CheckmkMonitoring"))


@pytest.mark.parametrize(
    "global_service_region, partition",
    [
        pytest.param("us-east-1", "aws", id="aws"),
        pytest.param("cn-north-1", "aws-cn", id="china"),
        pytest.param("us-gov-west-1", "aws-us-gov", id="govcloud"),
    ],
)
def test_spoke_role_arn_uses_the_partition_of_the_region(
    fake_sts: FakeSts, global_service_region: str, partition: str
) -> None:
    AwsCredentials(
        HubCredentials(AccessKey("AKIAHUB", "secret")),
        global_service_region,
        None,
        SpokeAccounts(["333333333333"], "CheckmkMonitoring"),
    ).open_account("333333333333")

    [call] = fake_sts.assume_role_calls
    assert call.params["RoleArn"] == f"arn:{partition}:iam::333333333333:role/CheckmkMonitoring"


def test_spoke_role_path_is_part_of_the_arn(fake_sts: FakeSts) -> None:
    _spoke_accounts(SpokeAccounts(["333333333333"], "monitoring/CheckmkMonitoring"))

    [call] = fake_sts.assume_role_calls
    assert call.params["RoleArn"] == "arn:aws:iam::333333333333:role/monitoring/CheckmkMonitoring"


def test_spoke_without_external_id_omits_it(fake_sts: FakeSts) -> None:
    _spoke_accounts(SpokeAccounts(["333333333333"], "CheckmkMonitoring"))

    [call] = fake_sts.assume_role_calls
    assert "ExternalId" not in call.params


def _organization(organization: Organization, key_id: str = "AKIAHUB") -> AwsCredentials:
    return AwsCredentials(
        HubCredentials(AccessKey(key_id, "secret")),
        "us-east-1",
        None,
        SpokeAccounts(organization, "CheckmkMonitoring", "tenant-42"),
    )


def _organization_account_ids(organization: Organization) -> Sequence[str]:
    return _organization(organization).monitored_account_ids()


@pytest.mark.usefixtures("fake_sts")
def test_organization_mode_reads_every_page_of_the_account_list() -> None:
    # 444444444444 is on the second page.
    assert "444444444444" in _organization_account_ids(Organization())


@pytest.mark.usefixtures("fake_sts")
def test_organization_mode_monitors_only_the_active_accounts() -> None:
    assert _organization_account_ids(Organization()) == ACTIVE_ORGANIZATION_ACCOUNTS


@pytest.mark.usefixtures("fake_sts")
def test_organization_accounts_have_their_names_from_the_account_list() -> None:
    credentials = _organization(Organization())

    assert {
        account.id: account.name
        for account in map(credentials.open_account, credentials.monitored_account_ids())
    } == ORGANIZATION_ACCOUNT_NAMES


@pytest.mark.usefixtures("fake_sts")
def test_excluded_accounts_are_not_monitored() -> None:
    assert _organization_account_ids(Organization(excluded_ids=[MANAGEMENT_ACCOUNT])) == [
        "333333333333",
        "444444444444",
    ]


def test_hub_lists_the_accounts_itself_without_a_list_role(fake_sts: FakeSts) -> None:
    _organization_account_ids(Organization())

    assert (
        {call.key_id for call in fake_sts.list_accounts_calls},
        fake_sts.assume_role_calls,
    ) == ({"AKIAHUB"}, [])


def test_account_list_role_is_assumed_only_to_list_the_accounts(fake_sts: FakeSts) -> None:
    credentials = _organization(Organization(list_role_arn=LIST_ROLE))
    credentials.open_account(credentials.monitored_account_ids()[1])

    assert (
        {call.key_id for call in fake_sts.list_accounts_calls},
        [(call.caller_key_id, call.params["RoleArn"]) for call in fake_sts.assume_role_calls],
    ) == (
        {temporary_key_id(MANAGEMENT_ACCOUNT)},
        [
            ("AKIAHUB", LIST_ROLE),
            ("AKIAHUB", "arn:aws:iam::333333333333:role/CheckmkMonitoring"),
        ],
    )


def test_account_list_role_and_spoke_roles_get_their_own_external_id(fake_sts: FakeSts) -> None:
    credentials = _organization(Organization(list_role_arn=LIST_ROLE, list_external_id="org-7"))
    credentials.open_account(credentials.monitored_account_ids()[1])

    assert [
        (call.params["RoleArn"], call.params["ExternalId"]) for call in fake_sts.assume_role_calls
    ] == [
        (LIST_ROLE, "org-7"),
        ("arn:aws:iam::333333333333:role/CheckmkMonitoring", "tenant-42"),
    ]


def test_account_list_role_without_external_id_omits_it(fake_sts: FakeSts) -> None:
    _organization_account_ids(Organization(list_role_arn=LIST_ROLE))

    [call] = fake_sts.assume_role_calls
    assert "ExternalId" not in call.params


@pytest.mark.usefixtures("fake_sts")
def test_failed_listing_is_an_access_error() -> None:
    with pytest.raises(AwsAccessError, match="Cannot list the accounts in the organization"):
        _organization(Organization(), key_id=NO_LIST_KEY_ID).monitored_account_ids()
