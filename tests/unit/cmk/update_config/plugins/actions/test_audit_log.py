#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.gui.watolib.audit_log import AuditLogStore

from cmk.update_config.plugins.actions.audit_log import WatoAuditLogConversion

EXAMPLE_ENTRIES = [
    AuditLogStore.Entry(
        time=0,
        object_ref=None,
        user_id="unittest",
        action="oldentry",
        text="Lorem ipsum",
        diff_text="diff",
    ),
    AuditLogStore.Entry(
        time=1,
        object_ref=None,
        user_id="unittest",
        action="oldentry",
        text="Lorem ipsum\ndolor sit amen",
        diff_text="diff\0text",
    ),
]


class OldAuditStore(AuditLogStore):
    separator = b"\0"


def test_conversion(tmp_path: Path) -> None:
    store_path = tmp_path / "wato_audit.log"

    old_store = OldAuditStore(store_path)
    old_store.append(EXAMPLE_ENTRIES[0])
    old_store.append(EXAMPLE_ENTRIES[1])

    assert (
        store_path.read_bytes()
        == repr(AuditLogStore.Entry.serialize(EXAMPLE_ENTRIES[0])).encode()
        + b"\0"
        + repr(AuditLogStore.Entry.serialize(EXAMPLE_ENTRIES[1])).encode()
        + b"\0"
    )

    WatoAuditLogConversion.convert_file(store_path)
    assert (
        store_path.read_bytes()
        == repr(AuditLogStore.Entry.serialize(EXAMPLE_ENTRIES[0])).encode()
        + b"\n"
        + repr(AuditLogStore.Entry.serialize(EXAMPLE_ENTRIES[1])).encode()
        + b"\n"
    )
    new_store = AuditLogStore(store_path)
    assert new_store.read() == EXAMPLE_ENTRIES


def test_conversion_needed(tmp_path: Path) -> None:
    store_path = tmp_path / "wato_audit.log"

    old_store = OldAuditStore(store_path)
    for entry in EXAMPLE_ENTRIES:
        old_store.append(entry)
        assert WatoAuditLogConversion.needs_conversion(store_path)

    WatoAuditLogConversion.convert_file(store_path)
    assert not WatoAuditLogConversion.needs_conversion(store_path)

    new_store_path = tmp_path / "wato_audit2.log"
    new_store = AuditLogStore(new_store_path)
    for entry in EXAMPLE_ENTRIES:
        new_store.append(entry)
        assert not WatoAuditLogConversion.needs_conversion(new_store_path)
