#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import time

import pytest
from pytest_mock import MockerFixture

from tests.testlib import on_time

from livestatus import SiteId

from cmk.utils.type_defs import UserId

from cmk.gui.htmllib import HTML
from cmk.gui.watolib.changes import (
    ActivateChangesWriter,
    add_change,
    AuditLogStore,
    log_audit,
    make_diff_text,
    ObjectRef,
    ObjectRefType,
    SiteChanges,
)


class TestObjectRef:
    def test_serialize(self):
        ty = ObjectRefType.Host
        ident = "node1"
        assert ObjectRef(ty, ident).serialize() == {"ident": "node1", "object_type": "Host"}

    def test_serialization_with_labels(self):
        ty = ObjectRefType.Host
        ident = "node1"
        assert ObjectRef(ty, ident, {"a": "b"}).serialize() == {
            "ident": "node1",
            "object_type": "Host",
            "labels": {"a": "b"},
        }

    def test_serialize_represented_as_native_types(self):
        serialized = ObjectRef(ObjectRefType.Host, "h1").serialize()
        as_text = repr(serialized)
        assert ast.literal_eval(as_text) == serialized

    def test_serialize_in_sync_with_deserialize(self):
        ty = ObjectRefType.Host
        ident = "node1"
        ref = ObjectRef.deserialize(ObjectRef(ty, ident).serialize())
        assert ref.object_type == ty
        assert ref.ident == ident
        assert ref.labels == {}

    def test_serialize_in_sync_with_deserialize_with_labels(self):
        ty = ObjectRefType.Host
        ident = "node1"
        labels = {"abc": "123"}
        ref = ObjectRef.deserialize(ObjectRef(ty, ident, labels).serialize())
        assert ref.object_type == ty
        assert ref.ident == ident
        assert ref.labels == labels


class TestAuditLogStore:
    @pytest.fixture(name="store")
    def fixture_store(self, tmp_path):
        return AuditLogStore(tmp_path / "audit.log")

    def test_read_not_existing(self, store):
        assert not store.exists()
        assert list(store.read()) == []

    def test_clear_not_existing(self, store):
        assert not store.exists()
        store.clear()

    def test_append(self, store):
        entry = AuditLogStore.Entry(int(time.time()), None, "user", "action", "Mässädsch", None)
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_append_multiple(self, store):
        entry = AuditLogStore.Entry(int(time.time()), None, "user", "action", "Mässädsch", None)
        store.append(entry)
        store.append(entry)
        assert list(store.read()) == [entry, entry]

    def test_transport_html(self, store, request_context):
        entry = AuditLogStore.Entry(
            int(time.time()), None, "user", "action", HTML("Mäss<b>ädsch</b>"), None
        )
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_clear(self, store):
        entry = AuditLogStore.Entry(int(time.time()), None, "user", "action", "Mässädsch", None)
        store.append(entry)
        assert list(store.read()) == [entry]

        store.clear()
        assert list(store.read()) == []

        archive_path = store._path.with_name(store._path.name + time.strftime(".%Y-%m-%d"))
        assert archive_path.exists()

    def test_clear_produced_archive_file_per_clear(self, store):
        entry = AuditLogStore.Entry(int(time.time()), None, "user", "action", "Mässädsch", None)

        for n in range(5):
            store.append(entry)
            assert list(store.read()) == [entry]

            store.clear()
            assert list(store.read()) == []

            for archive_num in range(n + 1):
                archive_path = store._path.with_name(store._path.name + time.strftime(".%Y-%m-%d"))
                if archive_num != 0:
                    archive_path = archive_path.with_name(
                        archive_path.name + "-%d" % (archive_num + 1)
                    )

                assert archive_path.exists()


class TestSiteChanges:
    @pytest.fixture(name="store")
    def fixture_store(self, tmp_path):
        return SiteChanges(tmp_path / ("replication_changes_mysite.mk"))

    @pytest.fixture(name="entry")
    def fixture_entry(self):
        return {
            "id": "d60ca3d4-7201-4a89-b66f-2f156192cad2",
            "action_name": "create-host",
            "text": "Created new host node1.",
            "object": ObjectRef(ObjectRefType.Host, "node1"),
            "user_id": "cmkadmin",
            "domains": ["check_mk"],
            "time": 1605461248.786142,
            "need_sync": True,
            "need_restart": True,
        }

    def test_read_not_existing(self, store):
        assert not store.exists()
        assert list(store.read()) == []

    def test_clear_not_existing(self, store):
        assert not store.exists()
        store.clear()

    def test_write(self, store, entry):
        store.append(entry)
        assert list(store.read()) == [entry]

        entry2 = entry.copy()
        entry2["id"] = "1"

        store.write([entry2])
        assert list(store.read()) == [entry2]

    def test_append(self, store, entry):
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_clear(self, store, entry):
        store.append(entry)
        assert list(store.read()) == [entry]

        store.clear()
        assert list(store.read()) == []

    @pytest.mark.parametrize(
        "old_type,ref_type",
        [
            ("CREHost", ObjectRefType.Host),
            ("CMEHost", ObjectRefType.Host),
            ("CREFolder", ObjectRefType.Folder),
            ("CMEFolder", ObjectRefType.Folder),
        ],
    )
    def test_read_pre_20_host_change(self, store, old_type, ref_type):
        with store._path.open("wb") as f:
            f.write(
                repr(
                    {
                        "id": "d60ca3d4-7201-4a89-b66f-2f156192cad2",
                        "action_name": "create-host",
                        "text": "Created new host node1.",
                        "object": (old_type, "node1"),
                        "user_id": "cmkadmin",
                        "domains": ["check_mk"],
                        "time": 1605461248.786142,
                        "need_sync": True,
                        "need_restart": True,
                    }
                ).encode("utf-8")
                + b"\0"
            )

        assert store.read()[0]["object"] == ObjectRef(ref_type, "node1")


def test_log_audit_with_object_diff(request_context):
    old = {
        "a": "b",
        "b": "c",
    }
    new = {
        "b": "c",
    }

    with on_time("2018-04-15 16:50", "CET"):
        log_audit(
            object_ref=None,
            action="bla",
            message="Message",
            user_id=UserId("calvin"),
            diff_text=make_diff_text(old, new),
        )

    store = AuditLogStore(AuditLogStore.make_path())
    assert store.read() == [
        AuditLogStore.Entry(
            time=1523811000,
            object_ref=None,
            user_id="calvin",
            action="bla",
            text="Message",
            diff_text='Attribute "a" with value "b" removed.',
        ),
    ]


def test_log_audit_with_html_message(request_context):
    with on_time("2018-04-15 16:50", "CET"):
        log_audit(
            object_ref=None,
            user_id=UserId("calvin"),
            action="bla",
            message=HTML("Message <b>bla</b>"),
        )

    store = AuditLogStore(AuditLogStore.make_path())
    assert store.read() == [
        AuditLogStore.Entry(
            time=1523811000,
            object_ref=None,
            user_id="calvin",
            action="bla",
            text=HTML("Message <b>bla</b>"),
            diff_text=None,
        ),
    ]


def test_disable_activate_changes_writer(mocker: MockerFixture) -> None:
    add_to_site_mock = mocker.patch.object(ActivateChangesWriter, "_add_change_to_site")

    add_change("ding", "dong", sites=[SiteId("a")])
    add_to_site_mock.assert_called_once()
    add_to_site_mock.reset_mock()

    with ActivateChangesWriter.disable():
        add_change("ding", "dong", sites=[SiteId("a")])
    add_to_site_mock.assert_not_called()
    add_to_site_mock.reset_mock()

    add_change("ding", "dong", sites=[SiteId("a")])
    add_to_site_mock.assert_called_once()
