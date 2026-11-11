#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import uuid
from pathlib import Path

import pytest

from cmk.product_usage.collection import collect_cloud_trial_data
from cmk.product_usage.schema import (
    AuditLog,
    AuditLogActorClass,
    CloudTrialPayload,
    ProductUsagePayload,
)

NO_ENTRIES = AuditLogActorClass(entries=0, last_entry_at=None)


def test_cloud_trial_payload_carries_the_audit_log_of_the_site(tmp_path: Path) -> None:
    _write_audit_log_entry(tmp_path, user_id="-", time=1767790000)

    payload = collect_cloud_trial_data(
        _product_usage_payload(),
        var_dir=tmp_path,
        default_config_dir=tmp_path,
        logger=logging.getLogger(__name__),
    )

    assert payload.audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=NO_ENTRIES,
        platform=AuditLogActorClass(entries=1, last_entry_at=1767790000),
    )


@pytest.mark.parametrize(
    "user_id",
    [
        pytest.param("api_user", id="Cloud API user"),
        pytest.param("agent_registration", id="agent registration user"),
    ],
)
def test_cloud_trial_payload_counts_the_cloud_platform_users_as_platform(
    tmp_path: Path, user_id: str
) -> None:
    _write_audit_log_entry(tmp_path, user_id=user_id, time=1767790000)

    payload = collect_cloud_trial_data(
        _product_usage_payload(),
        var_dir=tmp_path,
        default_config_dir=tmp_path,
        logger=logging.getLogger(__name__),
    )

    assert payload.audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=NO_ENTRIES,
        platform=AuditLogActorClass(entries=1, last_entry_at=1767790000),
    )


def test_cloud_trial_payload_has_no_audit_log_when_its_collection_fails(tmp_path: Path) -> None:
    _write_corrupt_user_store(tmp_path)
    product_usage = _product_usage_payload()

    payload = collect_cloud_trial_data(
        product_usage,
        var_dir=tmp_path,
        default_config_dir=tmp_path,
        logger=logging.getLogger(__name__),
    )

    assert payload == CloudTrialPayload(**product_usage.model_dump())


def test_failed_audit_log_collection_logs_the_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_corrupt_user_store(tmp_path)

    collect_cloud_trial_data(
        _product_usage_payload(),
        var_dir=tmp_path,
        default_config_dir=tmp_path,
        logger=logging.getLogger(__name__),
    )

    assert [record.levelname for record in caplog.records] == ["ERROR"]


@pytest.mark.parametrize(
    "user_id",
    [
        pytest.param("alice@example.com", id="email address"),
        pytest.param("automation_bob", id="user ID"),
    ],
)
def test_cloud_trial_payload_contains_no_user_id_of_the_audit_log(
    tmp_path: Path, user_id: str
) -> None:
    _write_audit_log_entry(tmp_path, user_id=user_id, time=1767790000)

    payload = collect_cloud_trial_data(
        _product_usage_payload(),
        var_dir=tmp_path,
        default_config_dir=tmp_path,
        logger=logging.getLogger(__name__),
    )

    assert user_id not in payload.model_dump_with_metadata_json().decode()


def _product_usage_payload() -> ProductUsagePayload:
    return ProductUsagePayload(
        id=uuid.UUID("0f8fad5b-d9cb-469f-a165-70867728950e"),
        count_hosts=1,
        count_services=2,
        count_folders=3,
        edition="cloud",
        cmk_version="2.5.0-2026.01.06",
        timestamp=1767790000,
        checks={},
        grafana=None,
    )


def _write_audit_log_entry(var_dir: Path, *, user_id: str, time: int) -> None:
    """Write a shortened audit log entry: the collector reads only the user ID and the time"""
    path = var_dir / "wato/log/wato_audit.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(repr({"time": time, "user_id": user_id, "action": "edit-host"}) + "\n")


def _write_corrupt_user_store(default_config_dir: Path) -> None:
    path = default_config_dir / "multisite.d/wato/users.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("multisite_users = {")
