#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.aws_v2.special_agent.credentials import (
    AccessKey,
    AssumedRole,
    AwsCredentials,
    DefaultCredentials,
    HubCredentials,
)
from cmk.testlib.aws_v2.fake_sts import FakeSts, HUB_ACCOUNT, ROLE, ROLE_ACCOUNT


def _account_id(hub: HubCredentials) -> str:
    return AwsCredentials(hub, "us-east-1", None).account_id()


@pytest.mark.usefixtures("fake_sts")
def test_access_key_logs_in_to_the_hub_account() -> None:
    assert _account_id(HubCredentials(AccessKey("AKIAHUB", "secret"))) == HUB_ACCOUNT


@pytest.mark.usefixtures("fake_sts")
def test_default_credentials_log_in_to_the_hub_account(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAENV")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    assert _account_id(HubCredentials(DefaultCredentials())) == HUB_ACCOUNT


def test_no_role_makes_no_assume_role_call(fake_sts: FakeSts) -> None:
    _account_id(HubCredentials(AccessKey("AKIAHUB", "secret")))

    assert fake_sts.assume_role_calls == []


@pytest.mark.usefixtures("fake_sts")
def test_access_key_with_assumed_role_ends_in_the_role_account() -> None:
    hub = HubCredentials(AccessKey("AKIAHUB", "secret"), AssumedRole(ROLE))

    assert _account_id(hub) == ROLE_ACCOUNT


@pytest.mark.usefixtures("fake_sts")
def test_default_credentials_with_assumed_role_end_in_the_role_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAENV")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")

    assert _account_id(HubCredentials(DefaultCredentials(), AssumedRole(ROLE))) == ROLE_ACCOUNT


def test_role_is_assumed_with_its_arn_and_external_id(fake_sts: FakeSts) -> None:
    _account_id(HubCredentials(AccessKey("AKIAHUB", "secret"), AssumedRole(ROLE, "tenant-42")))

    [call] = fake_sts.assume_role_calls
    assert (call.params["RoleArn"], call.params["ExternalId"]) == (ROLE, "tenant-42")


def test_role_without_external_id_sends_none(fake_sts: FakeSts) -> None:
    _account_id(HubCredentials(AccessKey("AKIAHUB", "secret"), AssumedRole(ROLE)))

    [call] = fake_sts.assume_role_calls
    assert "ExternalId" not in call.params
