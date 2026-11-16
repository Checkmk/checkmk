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
    Session,
)

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


def test_cloud_trial_payload_has_no_audit_log_when_its_collection_fails(tmp_path: Path) -> None:
    complete_payload = _collect_from_site(tmp_path)
    _write_corrupt_user_store(tmp_path)

    payload = _collect_from_site(tmp_path)

    assert payload == complete_payload.model_copy(update={"audit_log": None})


def test_failed_audit_log_collection_logs_the_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_corrupt_user_store(tmp_path)

    _collect_from_site(tmp_path)

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

    payload = _collect_from_site(tmp_path)

    assert user_id not in payload.model_dump_with_metadata_json().decode()


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


def test_cloud_trial_payload_carries_the_sessions_of_the_site(tmp_path: Path) -> None:
    _write_session(
        tmp_path, user_id="jane@acme.com", started_at=1767789000, last_activity=1767790000
    )

    payload = _collect_from_site(tmp_path)

    assert payload.sessions == [Session(started_at=1767789000, last_activity=1767790000)]


def test_cloud_trial_payload_has_no_sessions_when_their_collection_fails(tmp_path: Path) -> None:
    complete_payload = _collect_from_site(tmp_path)
    _write_corrupt_session_store(tmp_path, user_id="jane@acme.com")

    payload = _collect_from_site(tmp_path)

    assert payload == complete_payload.model_copy(update={"sessions": None})


def test_failed_sessions_collection_logs_the_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_corrupt_session_store(tmp_path, user_id="jane@acme.com")

    _collect_from_site(tmp_path)

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


def _raise_livestatus_error() -> list[list[str]]:
    raise MKLivestatusSocketError("connection refused")


def _write_session(var_dir: Path, *, user_id: str, started_at: int, last_activity: int) -> None:
    """Write a shortened session: the collector reads only the start and the last activity"""
    path = var_dir / "web" / user_id / "session_info.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        repr({"sid-1": {"started_at": started_at, "last_activity": last_activity}}) + "\n"
    )


def _write_corrupt_session_store(var_dir: Path, *, user_id: str) -> None:
    path = var_dir / "web" / user_id / "session_info.mk"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{'sid-1': {")
