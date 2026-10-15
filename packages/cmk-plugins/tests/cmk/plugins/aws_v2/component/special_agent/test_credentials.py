#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws_v2.special_agent.config import AwsAccessError
from cmk.plugins.aws_v2.special_agent.credentials import (
    AccessKey,
    AssumedRole,
    AwsCredentials,
    DefaultCredentials,
    HubCredentials,
    SpokeAccounts,
)
from cmk.testlib.aws_v2.fake_sts import DENIED_ACCOUNT, FakeSts, HUB_ACCOUNT, ROLE, ROLE_ACCOUNT


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


def test_no_role_makes_no_assume_role_call(fake_sts: FakeSts) -> None:
    _session_account_id(HubCredentials(AccessKey("AKIAHUB", "secret")))

    assert fake_sts.assume_role_calls == []


@pytest.mark.usefixtures("fake_sts")
def test_access_key_with_assumed_role_ends_in_the_role_account() -> None:
    hub = HubCredentials(AccessKey("AKIAHUB", "secret"), AssumedRole(ROLE))

    assert _session_account_id(hub) == ROLE_ACCOUNT


@pytest.mark.usefixtures("fake_sts")
def test_default_credentials_with_assumed_role_end_in_the_role_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAENV")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    assert (
        _session_account_id(HubCredentials(DefaultCredentials(), AssumedRole(ROLE))) == ROLE_ACCOUNT
    )


def test_role_is_assumed_with_its_arn_and_external_id(fake_sts: FakeSts) -> None:
    _session_account_id(
        HubCredentials(AccessKey("AKIAHUB", "secret"), AssumedRole(ROLE, "tenant-42"))
    )

    [call] = fake_sts.assume_role_calls
    assert (call.params["RoleArn"], call.params["ExternalId"]) == (ROLE, "tenant-42")


def test_role_without_external_id_omits_it(fake_sts: FakeSts) -> None:
    _session_account_id(HubCredentials(AccessKey("AKIAHUB", "secret"), AssumedRole(ROLE)))

    [call] = fake_sts.assume_role_calls
    assert "ExternalId" not in call.params


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


def test_spoke_without_external_id_omits_it(fake_sts: FakeSts) -> None:
    _spoke_accounts(SpokeAccounts(["333333333333"], "CheckmkMonitoring"))

    [call] = fake_sts.assume_role_calls
    assert "ExternalId" not in call.params
