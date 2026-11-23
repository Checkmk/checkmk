#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
import uuid
from pathlib import Path

import pytest
from pytest_mock import MockerFixture, MockType

from cmk.livestatus_client import MKLivestatusSocketError
from cmk.product_usage.collection import collect_cloud_trial_data, collect_data
from cmk.product_usage.collectors.host_services import ServicesPerHostReader
from cmk.product_usage.schema import (
    AuditLog,
    AuditLogActorClass,
    CloudTrialPayload,
    InventoryData,
    ProductUsagePayload,
    SessionStats,
    UserCount,
)
from tests.unit.cmk.product_usage.user_store import write_user_store

NO_ENTRIES = AuditLogActorClass(entries=0, last_entry_at=None)


@pytest.fixture
def created_site(tmp_path: Path) -> None:
    """Every test site has the instance ID from OMD and the creation time from the platform"""
    _write_instance_id(tmp_path, mtime=1767690000)
    _write_site_created_at(tmp_path, 1767700800)


pytestmark = pytest.mark.usefixtures("created_site")


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


def test_cloud_trial_payload_carries_the_statistics_of_the_sessions_before_its_collection(
    tmp_path: Path,
) -> None:
    collected_at = _product_usage_payload().timestamp
    _write_session(
        tmp_path,
        user_id="jane@acme.com",
        started_at=collected_at - 1000,
        last_activity=collected_at,
    )

    payload = _collect_from_site(tmp_path)

    assert payload.sessions == SessionStats(
        count=1, average_duration=1000.0, median_duration=1000.0, stddev_duration=0.0
    )


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


@pytest.fixture(name="mock_checkmk_info")
def fixture_mock_checkmk_info(mocker: MockerFixture) -> None:
    """The edition and version, which are read from the installed version tree"""
    mocker.patch(
        "cmk.ccc.version_info.get_general_version_infos",
        return_value={"version": "2.5.0p1", "edition": "pro", "os": "Ubuntu 24.04.3 LTS"},
    )


@pytest.mark.usefixtures("mock_checkmk_info")
def test_payload_has_no_distributed_monitoring_role_when_the_site_config_is_broken(
    tmp_path: Path, local_connection: MockType
) -> None:
    (tmp_path / "distributed_wato.mk").write_text("is_wato_slave_site = True\n")
    (tmp_path / "multisite.d").mkdir()
    (tmp_path / "multisite.d" / "sites.mk").write_text("sites.update({\n")

    payload = _collect_product_usage(tmp_path, local_connection)

    assert payload.distributed_monitoring is None
    assert (payload.count_hosts, payload.count_services, payload.checks) == (10, 20, {})


@pytest.mark.usefixtures("mock_checkmk_info")
def test_payload_has_no_languages_when_the_locale_dir_is_unreadable(
    tmp_path: Path, local_connection: MockType
) -> None:
    locale_dir = tmp_path / "locale"
    locale_dir.write_text("")

    payload = _collect_product_usage(tmp_path, local_connection, locale_dir=locale_dir)

    assert payload.languages is None
    assert (payload.count_hosts, payload.count_services, payload.checks) == (10, 20, {})


@pytest.mark.usefixtures("mock_checkmk_info")
def test_payload_has_no_users_and_no_languages_when_the_user_store_is_corrupt(
    tmp_path: Path, local_connection: MockType
) -> None:
    _write_corrupt_user_store(tmp_path)

    payload = _collect_product_usage(tmp_path, local_connection)

    assert (payload.users, payload.languages) == (None, None)
    assert (payload.count_hosts, payload.count_services, payload.checks) == (10, 20, {})


@pytest.mark.usefixtures("mock_checkmk_info")
def test_corrupt_user_store_logs_the_error_of_the_users(
    tmp_path: Path, local_connection: MockType, caplog: pytest.LogCaptureFixture
) -> None:
    _write_corrupt_user_store(tmp_path)

    _collect_product_usage(tmp_path, local_connection)

    assert (
        "ERROR",
        "Could not read the users, sending no user counts and no languages",
        True,
    ) in [
        (record.levelname, record.getMessage(), record.exc_info is not None)
        for record in caplog.records
    ]


@pytest.mark.usefixtures("mock_checkmk_info")
def test_payload_has_no_users_but_languages_when_the_users_cannot_be_counted(
    tmp_path: Path, local_connection: MockType
) -> None:
    write_user_store(tmp_path, {"alice": {"roles": "admin"}})

    payload = _collect_product_usage(tmp_path, local_connection)

    assert payload.users is None
    assert payload.languages is not None


def _collect_product_usage(
    site_dir: Path, local_connection: MockType, *, locale_dir: Path | None = None
) -> ProductUsagePayload:
    """Collect the product usage data of a test site: 10 hosts, 20 services, nothing else

    The four Livestatus answers are the site status, the services, the disabled services
    and the hosts with inventory data, in the order 'collect_data' asks for them.
    """
    local_connection.query.side_effect = [[[10, 20]], [], [], []]
    (site_dir / "wato").mkdir(parents=True, exist_ok=True)

    return collect_data(
        site_dir,
        site_dir,
        site_dir,
        site_dir,
        locale_dir or site_dir / "locale",
        logging.getLogger(__name__),
    )


def test_cloud_trial_payload_prefers_the_platform_time_over_the_instance_id_time(
    tmp_path: Path,
) -> None:
    # The created_site fixture writes the instance ID with another time
    _write_site_created_at(tmp_path, 1767600000)

    payload = _collect_from_site(tmp_path)

    assert payload.site_created_at == 1767600000


def test_cloud_trial_payload_carries_the_instance_id_time_without_a_creation_time_from_the_platform(
    tmp_path: Path,
) -> None:
    _write_site_created_at(tmp_path, None)

    payload = _collect_from_site(tmp_path)

    assert payload.site_created_at == 1767690000


def test_cloud_trial_payload_has_no_site_creation_time_when_its_collection_fails(
    tmp_path: Path,
) -> None:
    complete_payload = _collect_from_site(tmp_path)
    _write_site_created_at(tmp_path, "not a number")

    payload = _collect_from_site(tmp_path)

    assert payload == complete_payload.model_copy(update={"site_created_at": None})


def test_failed_site_creation_time_collection_logs_the_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write_site_created_at(tmp_path, "not a number")

    _collect_from_site(tmp_path)

    assert [record.levelname for record in caplog.records] == ["ERROR"]


def test_site_without_a_creation_time_from_the_platform_logs_that_it_sends_the_instance_id_time(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    _write_site_created_at(tmp_path, None)

    _collect_from_site(tmp_path)

    assert [(record.levelname, record.getMessage()) for record in caplog.records] == [
        (
            "INFO",
            (
                "No site creation time from the Cloud platform,"
                " sending the modification time of etc/omd/instance_id"
            ),
        )
    ]


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
        omd_root=site_dir,
        cloud_config_dir=site_dir,
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
        inventory=InventoryData(hosts_with_inventory=4),
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


def _write_instance_id(omd_root: Path, *, mtime: int) -> None:
    path = omd_root / "etc/omd/instance_id"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("0f8fad5b-d9cb-469f-a165-70867728950e")
    os.utime(path, (mtime, mtime))


def _write_site_created_at(cloud_config_dir: Path, site_created_at: object) -> None:
    """Write a shortened Cloud edition config: the collector reads only the creation time"""
    (cloud_config_dir / "edition_config.json").write_text(
        json.dumps({"site_created_at": site_created_at})
    )
