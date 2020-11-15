#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import pytest  # type: ignore[import]

from testlib import on_time

from cmk.utils.type_defs import UserId

from cmk.gui.htmllib import HTML
from cmk.gui.watolib.changes import (AuditLogStore, SiteChanges, ChangeSpec, log_audit,
                                     make_diff_text)


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
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch", None)
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_append_multiple(self, store):
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch", None)
        store.append(entry)
        store.append(entry)
        assert list(store.read()) == [entry, entry]

    def test_transport_html(self, store, register_builtin_html):
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action",
                                    HTML("Mäss<b>ädsch</b>"), None)
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_clear(self, store):
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch", None)
        store.append(entry)
        assert list(store.read()) == [entry]

        store.clear()
        assert list(store.read()) == []

        archive_path = store._path.with_name(store._path.name + time.strftime(".%Y-%m-%d"))
        assert archive_path.exists()

    def test_clear_produced_archive_file_per_clear(self, store):
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch", None)

        for n in range(5):
            store.append(entry)
            assert list(store.read()) == [entry]

            store.clear()
            assert list(store.read()) == []

            for archive_num in range(n + 1):
                archive_path = store._path.with_name(store._path.name + time.strftime(".%Y-%m-%d"))
                if archive_num != 0:
                    archive_path = archive_path.with_name(archive_path.name + "-%d" %
                                                          (archive_num + 1))

                assert archive_path.exists()


class TestSiteChanges:
    @pytest.fixture(name="store")
    def fixture_store(self, tmp_path):
        return SiteChanges(tmp_path / ("replication_changes_mysite.mk"))

    def test_read_not_existing(self, store):
        assert not store.exists()
        assert list(store.read()) == []

    def test_clear_not_existing(self, store):
        assert not store.exists()
        store.clear()

    def test_write(self, store):
        entry1: ChangeSpec = {"a": "b"}
        store.append(entry1)
        assert list(store.read()) == [entry1]

        entry2: ChangeSpec = {"x": "y"}
        store.write([entry2])
        assert list(store.read()) == [entry2]

    def test_append(self, store):
        entry: ChangeSpec = {"a": "b"}
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_clear(self, store):
        entry: ChangeSpec = {"a": "b"}
        store.append(entry)
        assert list(store.read()) == [entry]

        store.clear()
        assert list(store.read()) == []


def test_log_audit_with_object_diff():
    old = {
        "a": "b",
        "b": "c",
    }
    new = {
        "b": "c",
    }

    with on_time('2018-04-15 16:50', 'CET'):
        log_audit(
            linkinfo=None,
            action="bla",
            message="Message",
            user_id=UserId("calvin"),
            diff_text=make_diff_text(old, new),
        )

    store = AuditLogStore(AuditLogStore.make_path())
    assert store.read() == [
        AuditLogStore.Entry(
            time=1523811000,
            linkinfo='-',
            user_id='calvin',
            action='bla',
            text='Message',
            diff_text='Attribute "a" with value "b" removed.',
        ),
    ]


def test_log_audit_with_html_message(register_builtin_html):
    with on_time('2018-04-15 16:50', 'CET'):
        log_audit(
            linkinfo=None,
            user_id=UserId('calvin'),
            action="bla",
            message=HTML("Message <b>bla</b>"),
        )

    store = AuditLogStore(AuditLogStore.make_path())
    assert store.read() == [
        AuditLogStore.Entry(
            time=1523811000,
            linkinfo='-',
            user_id='calvin',
            action='bla',
            text=HTML("Message <b>bla</b>"),
            diff_text=None,
        ),
    ]
