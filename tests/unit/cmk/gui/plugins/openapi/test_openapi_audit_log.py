#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import math
import random
from typing import Any

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from cmk.gui.watolib.audit_log import AuditLogStore

BASE_DATE = "2023-08-16"

BASE_ENTRIES = [
    {
        "time": 1692174326,
        "object_ref": {"object_type": "Host", "ident": "tst"},
        "user_id": "ghost-user",
        "action": "create-host",
        "text": ["str", "Created new host tst."],
        "diff_text": "Nothing was changed.",
    },
    {
        "time": 1692174332,
        "object_ref": None,
        "user_id": "cmkadmin",
        "action": "snapshot-created",
        "text": ["str", "Created snapshot wato-snapshot-2023-08-16-10-25-32.tar"],
        "diff_text": None,
    },
    {
        "time": 1692174332,
        "object_ref": None,
        "user_id": "cmkadmin",
        "action": "activate-changes",
        "text": ["str", "Starting activation (Sites: heute)"],
        "diff_text": None,
    },
    {
        "time": 1692174332,
        "object_ref": None,
        "user_id": "cmkadmin",
        "action": "activate-changes",
        "text": ["str", "Started activation of site heute"],
        "diff_text": None,
    },
]


def generate_random_audit_log(numdays: int = 10, events_per_day: int | None = None) -> list:
    def randomize_object_ref():
        if random.randint(0, 1):
            return None
        return {"object_type": "Host", "ident": "test"}

    def randomize_user_id():
        return random.choice(
            ["cmkadmin", "test", "cfulanito", "Mathias_Kettner", "admin", "ghost-user"]
        )

    def randomize_action():
        return random.choice(["create-host", "snapshot-created", "activate-changes"])

    def randomize_text():
        string = random.choice(
            [
                "Created snapshot wato-snapshot-2023-08-16-10-25-32.tar",
                "Created new host tst",
                "Started activation of site heute, please wait.",
            ]
        )
        return ["str", string]

    def randomize_diff_text():
        return random.choice([None, None, None, "Nothing was changed", "All good"])

    base = datetime.datetime.today()
    date_list = reversed([base - datetime.timedelta(days=x) for x in range(numdays)])

    events = []

    for day in date_list:
        events_per_day_count = random.randint(1, 50) if events_per_day is None else events_per_day
        for i in range(events_per_day_count):
            timestamp = math.floor(day.timestamp() + i)

            item = {
                "time": timestamp,
                "object_ref": randomize_object_ref(),
                "user_id": randomize_user_id(),
                "action": randomize_action(),
                "text": randomize_text(),
                "diff_text": randomize_diff_text(),
            }

            events.append(item)

    return events


@pytest.fixture(name="audit_log_store")
def create_audit_log_store() -> AuditLogStore:
    audit_log_store = AuditLogStore()
    audit_log_store.clear()
    return audit_log_store


def populate_audit_log(audit_log_store: AuditLogStore, entries: list) -> None:
    for entry in entries:
        audit_log_store.append(AuditLogStore.Entry.deserialize(entry))


@pytest.fixture
def populated_audit_log(audit_log_store: AuditLogStore) -> None:
    populate_audit_log(audit_log_store, BASE_ENTRIES)


@pytest.fixture(name="populated_two_day_entries_audit_log")
def populated_with_two_day_entries_audit_log(
    audit_log_store: AuditLogStore,
) -> list[AuditLogStore.Entry]:
    entries = generate_random_audit_log(2)
    populate_audit_log(audit_log_store, entries)
    return entries


def test_openapi_audit_log_get_time_filter(clients: ClientRegistry) -> None:
    res_invalid_string = clients.AuditLog.get_all(
        date="invalid", expect_ok=False
    ).assert_status_code(400)
    assert "date" in res_invalid_string.json["detail"]
    assert "date" in res_invalid_string.json["fields"]

    res_number = clients.AuditLog.get_all(date=1234, expect_ok=False).assert_status_code(400)
    assert "date" in res_number.json["detail"]
    assert "date" in res_number.json["fields"]

    res_bad_date = clients.AuditLog.get_all(date="1981-12-32", expect_ok=False).assert_status_code(
        400
    )
    assert "date" in res_bad_date.json["detail"]
    assert "date" in res_bad_date.json["fields"]

    clients.AuditLog.get_all(date="1981-12-19")


@pytest.mark.usefixtures("populated_audit_log")
def test_openapi_audit_log_clear(clients: ClientRegistry) -> None:
    res_new = clients.AuditLog.get_all(date=BASE_DATE)
    assert len(res_new.json["value"]) > 0

    clients.AuditLog.clear()

    res_clear = clients.AuditLog.get_all(date=BASE_DATE)
    assert len(res_clear.json["value"]) == 0


@pytest.mark.usefixtures("populated_audit_log")
def test_openapi_audit_log_filter(clients: ClientRegistry) -> None:
    res_without_filters = clients.AuditLog.get_all(date=BASE_DATE)
    assert len(res_without_filters.json["value"]) == 4

    res_filter_object_type_host = clients.AuditLog.get_all(object_type="Host", date=BASE_DATE)
    assert len(res_filter_object_type_host.json["value"]) == 1

    res_filter_object_type_none = clients.AuditLog.get_all(object_type="None", date=BASE_DATE)
    assert len(res_filter_object_type_none.json["value"]) == 3

    res_filter_user_id_1 = clients.AuditLog.get_all(user_id="ghost-user", date=BASE_DATE)
    assert len(res_filter_user_id_1.json["value"]) == 1

    res_filter_user_id_3 = clients.AuditLog.get_all(user_id="cmkadmin", date=BASE_DATE)
    assert len(res_filter_user_id_3.json["value"]) == 3

    res_filter_object_id = clients.AuditLog.get_all(object_id="tst", date=BASE_DATE)
    assert len(res_filter_object_id.json["value"]) == 1

    res_filter_empty_object_id = clients.AuditLog.get_all(object_id="", date=BASE_DATE)
    assert len(res_filter_empty_object_id.json["value"]) == 4


def test_openapi_audit_log_pagination(
    clients: ClientRegistry, populated_two_day_entries_audit_log: list
) -> None:
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(days=1)

    today_res = clients.AuditLog.get_all(date=today.strftime("%Y-%m-%d"))
    yesteday_res = clients.AuditLog.get_all(date=yesterday.strftime("%Y-%m-%d"))

    assert len(today_res.json["value"] + yesteday_res.json["value"]) == len(
        populated_two_day_entries_audit_log
    )


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

    entries = generate_random_audit_log(2, 2)
    assert_entry(entries[0], AuditLogStore.Entry.deserialize(entries[0]))
    assert_entry(entries[1], AuditLogStore.Entry.deserialize(entries[1]))
    assert_entry(entries[2], AuditLogStore.Entry.deserialize(entries[2]))
    assert_entry(entries[3], AuditLogStore.Entry.deserialize(entries[3]))
