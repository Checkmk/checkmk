#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import pytest  # type: ignore[import]

from cmk.gui.watolib.changes import AuditLogStore


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
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch")
        store.append(entry)
        assert list(store.read()) == [entry]

    def test_clear(self, store):
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch")
        store.append(entry)
        assert list(store.read()) == [entry]

        store.clear()
        assert list(store.read()) == []

        archive_path = store._path.with_name(store._path.name + time.strftime(".%Y-%m-%d"))
        assert archive_path.exists()

    def test_clear_produced_archive_file_per_clear(self, store):
        entry = AuditLogStore.Entry(int(time.time()), "link", "user", "action", "Mässädsch")

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
