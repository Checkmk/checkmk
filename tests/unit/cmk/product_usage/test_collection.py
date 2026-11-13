#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import uuid
from pathlib import Path

import pytest

from cmk.livestatus_client import MKLivestatusSocketError
from cmk.product_usage.collection import collect_cloud_trial_data
from cmk.product_usage.collectors.host_services import ServicesPerHostReader
from cmk.product_usage.schema import (
    AuditLog,
    AuditLogActorClass,
    CloudTrialPayload,
    ProductUsagePayload,
    UserCount,
)
from tests.unit.cmk.product_usage.user_store import write_user_store

NO_ENTRIES = AuditLogActorClass(entries=0, last_entry_at=None)


def test_cloud_trial_payload_carries_the_audit_log_of_the_site(tmp_path: Path) -> None:
    _write_audit_log_entry(tmp_path, user_id="-", time=1767790000)

    payload = _collect_from_site(tmp_path)

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

    payload = _collect_from_site(tmp_path)

    assert payload.audit_log == AuditLog(
        interactive=NO_ENTRIES,
        automation=NO_ENTRIES,
        platform=AuditLogActorClass(entries=1, last_entry_at=1767790000),
    )


def test_cloud_trial_payload_has_no_audit_log_and_no_user_counts_when_the_user_store_is_corrupt(
    tmp_path: Path,
) -> None:
    complete_payload = _collect_from_site(tmp_path)
    _write_corrupt_user_store(tmp_path)

    payload = _collect_from_site(tmp_path)

    assert payload == complete_payload.model_copy(update={"audit_log": None, "count_users": None})


def test_corrupt_user_store_logs_the_error_of_each_signal_with_its_cause(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_corrupt_user_store(tmp_path)

    _collect_from_site(tmp_path)

    assert sorted(
        (record.levelname, record.getMessage(), record.exc_info is not None)
        for record in caplog.records
    ) == [
        ("ERROR", "Could not collect the audit log, sending no audit log", True),
        ("ERROR", "Could not count the users, sending no user counts", True),
    ]


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

    payload = _collect_from_site(tmp_path)

    assert user_id not in payload.model_dump_with_metadata_json().decode()


def test_cloud_trial_payload_carries_the_user_counts_of_the_site(tmp_path: Path) -> None:
    write_user_store(
        tmp_path,
        {"jane@acme.com": {"connector": "cognito"}, "john@gmail.com": {"connector": "cognito"}},
    )

    payload = _collect_from_site(tmp_path)

    assert payload.count_users == UserCount(business=1, non_business=1)


def test_cloud_trial_payload_contains_no_address_domain_or_provider_of_the_users(
    tmp_path: Path,
) -> None:
    write_user_store(
        tmp_path,
        {"jane@acme.com": {"connector": "cognito"}, "john@gmail.com": {"connector": "cognito"}},
    )

    payload = _collect_from_site(tmp_path)

    # Without user counts, the payload would contain nothing to leak.
    assert payload.count_users is not None
    dumped = payload.model_dump_with_metadata_json().decode()
    assert [
        text for text in ("jane@acme.com", "john@gmail.com", "acme", "gmail") if text in dumped
    ] == []


def test_cloud_trial_payload_carries_the_count_of_hosts_with_default_services_only(
    tmp_path: Path,
) -> None:
    payload = _collect_from_site(
        tmp_path, read_services_per_host=lambda: [["Check_MK", "Check_MK Discovery"]]
    )

    assert payload.count_hosts_default_services_only == 1


def test_cloud_trial_payload_has_no_count_of_hosts_with_default_services_only_when_its_collection_fails(
    tmp_path: Path,
) -> None:
    complete_payload = _collect_from_site(tmp_path)

    payload = _collect_from_site(tmp_path, read_services_per_host=_raise_livestatus_error)

    assert payload == complete_payload.model_copy(
        update={"count_hosts_default_services_only": None}
    )


def test_failed_count_of_hosts_with_default_services_only_logs_the_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _collect_from_site(tmp_path, read_services_per_host=_raise_livestatus_error)

    assert [record.levelname for record in caplog.records] == ["ERROR"]


def test_cloud_trial_payload_carries_the_product_usage_data(tmp_path: Path) -> None:
    payload = _collect_from_site(tmp_path)

    assert payload.model_dump(include=set(ProductUsagePayload.model_fields)) == (
        _product_usage_payload().model_dump()
    )


def _collect_from_site(
    site_dir: Path,
    *,
    read_services_per_host: ServicesPerHostReader = list,
) -> CloudTrialPayload:
    """Collect the Cloud trial data of a test site: no hosts, fixed product usage payload"""
    return collect_cloud_trial_data(
        _product_usage_payload(),
        var_dir=site_dir,
        default_config_dir=site_dir,
        read_services_per_host=read_services_per_host,
        logger=logging.getLogger(__name__),
    )


def _product_usage_payload() -> ProductUsagePayload:
    return ProductUsagePayload(
        id=uuid.UUID("0f8fad5b-d9cb-469f-a165-70867728950e"),
        count_hosts=1,
        count_services=2,
        count_folders=3,
        edition="cloud",
        cmk_version="2.5.0-2026.01.06",
        os="Ubuntu 24.04.3 LTS",
        timestamp=1767790000,
        checks={},
        users={
            "humans": {
                "total": 1,
                "by_role": {"admin": 1},
                "by_connector_type": {"htpasswd": 1},
                "active": {"24h": 1, "7d": 1, "30d": 1},
            },
            "automation": {
                "total": 0,
                "by_role": {},
                "by_connector_type": {},
                "active": {"24h": 0, "7d": 0, "30d": 0},
            },
        },
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


def _raise_livestatus_error() -> list[list[str]]:
    raise MKLivestatusSocketError("connection refused")
