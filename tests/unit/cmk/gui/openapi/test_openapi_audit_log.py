#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from dataclasses import dataclass
from typing import Any

import pytest
from polyfactory.factories import DataclassFactory

from cmk.gui.watolib.audit_log import AuditLogStore
from tests.testlib.unit.rest_api_client import ClientRegistry


@dataclass
class LogEntry:
    time: int
    object_ref: dict[str, str] | None
    user_id: str
    action: str
    text: list[str]
    diff_text: str | None


class LogEntryFactory(DataclassFactory[LogEntry]):
    __model__ = LogEntry

    text = ["str", "This is a test"]
    object_ref = None


ONE_DAY = 86400

BASE_DATE = "2023-08-16"
BASE_PREVIOUS_DATE = "2023-08-15"
BASE_DATE_TIMESTAMP = int(
    datetime.datetime.strptime(BASE_DATE, "%Y-%m-%d")
    .replace(hour=8, minute=0, second=0)
    .timestamp()
)


def _populate_audit_log(audit_log_store: AuditLogStore, serialized_entries: list) -> None:
    for entry in serialized_entries:
        deserialized_entry = AuditLogStore.Entry.deserialize(
            entry if isinstance(entry, dict) else entry.__dict__
        )
        audit_log_store.append(deserialized_entry)


@pytest.fixture(name="audit_log_store")
def audit_log_store_builder() -> AuditLogStore:
    als = AuditLogStore()
    als.clear()
    return als


def test_openapi_audit_log_invalid_date_filter(clients: ClientRegistry) -> None:
    res_invalid_string = clients.AuditLog.get_all(
        date="invalid", expect_ok=False
    ).assert_status_code(400)
    assert "date" in res_invalid_string.json["detail"]
    assert "date" in res_invalid_string.json["fields"]

    res_bad_date = clients.AuditLog.get_all(date="1981-12-32", expect_ok=False).assert_status_code(
        400
    )
    assert "date" in res_bad_date.json["detail"]
    assert "date" in res_bad_date.json["fields"]


def test_openapi_audit_log_archive(audit_log_store: AuditLogStore, clients: ClientRegistry) -> None:
    deserialized_entries = LogEntryFactory.batch(4, time=BASE_DATE_TIMESTAMP)
    _populate_audit_log(audit_log_store, deserialized_entries)

    res_new = clients.AuditLog.get_all(date=BASE_DATE)
    assert len(res_new.json["value"]) == 4

    clients.AuditLog.archive()

    res_archive = clients.AuditLog.get_all(date=BASE_DATE)
    assert len(res_archive.json["value"]) == 0


def test_openapi_audit_log_no_filter(
    audit_log_store: AuditLogStore, clients: ClientRegistry
) -> None:
    deserialized_entries = [
        LogEntryFactory.build(time=BASE_DATE_TIMESTAMP),
        LogEntryFactory.build(time=BASE_DATE_TIMESTAMP + 60),
        LogEntryFactory.build(time=BASE_DATE_TIMESTAMP + 120),
        LogEntryFactory.build(time=BASE_DATE_TIMESTAMP + 180),
        LogEntryFactory.build(time=BASE_DATE_TIMESTAMP + ONE_DAY),
    ]

    _populate_audit_log(audit_log_store, deserialized_entries)
    res_no_filter = clients.AuditLog.get_all(date=BASE_DATE)
    assert len(res_no_filter.json["value"]) == 4


def test_openapi_audit_log_object_type(
    audit_log_store: AuditLogStore, clients: ClientRegistry
) -> None:
    deserialized_entries = LogEntryFactory.batch(
        3, time=BASE_DATE_TIMESTAMP
    ) + LogEntryFactory.batch(
        1,
        time=BASE_DATE_TIMESTAMP,
        object_ref={"object_type": "Host", "ident": "testing"},
    )

    _populate_audit_log(audit_log_store, deserialized_entries)

    res_object_type_host = clients.AuditLog.get_all(object_type="Host", date=BASE_DATE)
    res_object_type_none = clients.AuditLog.get_all(object_type="None", date=BASE_DATE)

    assert len(res_object_type_host.json["value"]) == 1
    assert len(res_object_type_none.json["value"]) == 3


def test_openapi_audit_log_filter_user_id(
    audit_log_store: AuditLogStore, clients: ClientRegistry
) -> None:
    deserialized_entries = LogEntryFactory.batch(
        3, time=BASE_DATE_TIMESTAMP, user_id="cmkadmin"
    ) + LogEntryFactory.batch(1, time=BASE_DATE_TIMESTAMP, user_id="ghost_user")

    _populate_audit_log(audit_log_store, deserialized_entries)

    res_cmkadmin = clients.AuditLog.get_all(user_id="cmkadmin", date=BASE_DATE)
    res_ghost_user = clients.AuditLog.get_all(user_id="ghost_user", date=BASE_DATE)
    res_unknown_user = clients.AuditLog.get_all(user_id="i-do-not-exist", date=BASE_DATE)

    assert len(res_cmkadmin.json["value"]) == 3
    assert len(res_ghost_user.json["value"]) == 1
    assert len(res_unknown_user.json["value"]) == 0


def test_openapi_audit_log_filter_object_id(
    audit_log_store: AuditLogStore, clients: ClientRegistry
) -> None:
    deserialized_entries = LogEntryFactory.batch(
        3, time=BASE_DATE_TIMESTAMP, object_ref=None
    ) + LogEntryFactory.batch(
        1,
        time=BASE_DATE_TIMESTAMP,
        object_ref={"object_type": "Host", "ident": "testing"},
    )

    _populate_audit_log(audit_log_store, deserialized_entries)
    res_testing_object_id = clients.AuditLog.get_all(object_id="testing", date=BASE_DATE)
    res_empty_object_id = clients.AuditLog.get_all(object_id="", date=BASE_DATE)

    assert len(res_testing_object_id.json["value"]) == 1
    assert len(res_empty_object_id.json["value"]) == 4


def test_openapi_audit_log_pagination(
    audit_log_store: AuditLogStore, clients: ClientRegistry
) -> None:
    today_entries_count = 19
    yesterday_entries_count = 12

    deserialized_entries = LogEntryFactory.batch(
        today_entries_count, time=BASE_DATE_TIMESTAMP
    ) + LogEntryFactory.batch(yesterday_entries_count, time=BASE_DATE_TIMESTAMP - ONE_DAY)

    _populate_audit_log(audit_log_store, deserialized_entries)

    today_res = clients.AuditLog.get_all(date=BASE_DATE)
    yesteday_res = clients.AuditLog.get_all(date=BASE_PREVIOUS_DATE)

    assert (
        len(today_res.json["value"] + yesteday_res.json["value"])
        == today_entries_count + yesterday_entries_count
    )
    assert len(today_res.json["value"]) == today_entries_count
    assert len(yesteday_res.json["value"]) == yesterday_entries_count


def test_openapi_audit_log_serialization() -> None:
    def assert_entry(raw_entry: dict[str, Any], audit_log_entry: AuditLogStore.Entry) -> None:
        assert raw_entry["time"] == audit_log_entry.time
        assert raw_entry["text"][1] == audit_log_entry.text
        assert raw_entry["user_id"] == audit_log_entry.user_id
        assert raw_entry["action"] == audit_log_entry.action
        assert raw_entry["diff_text"] == audit_log_entry.diff_text

        if (
            "object_ref" in raw_entry
            and raw_entry["object_ref"] is not None
            and audit_log_entry.object_ref is not None
        ):
            assert raw_entry["object_ref"]["ident"] == audit_log_entry.object_ref.ident
            assert (
                raw_entry["object_ref"]["object_type"]
                == audit_log_entry.object_ref.object_type.name
            )

    entry1 = {
        "time": 1692174326,
        "object_ref": {"object_type": "Host", "ident": "test"},
        "user_id": "ghost-user",
        "action": "create-host",
        "text": ["str", "Created new host test."],
        "diff_text": "Nothing was changed.",
    }

    deserialized_entry1: AuditLogStore.Entry = AuditLogStore.Entry.deserialize(entry1)
    serialized_entry1 = AuditLogStore.Entry.serialize(deserialized_entry1)
    assert_entry(entry1, deserialized_entry1)
    assert_entry(serialized_entry1, deserialized_entry1)

    entry2 = {
        "time": 1692174332,
        "object_ref": None,
        "user_id": "cmkadmin",
        "action": "activate-changes",
        "text": ["str", "Starting activation (Sites: heute)"],
        "diff_text": None,
    }

    deserialized_entry2: AuditLogStore.Entry = AuditLogStore.Entry.deserialize(entry2)
    assert_entry(entry2, deserialized_entry2)
