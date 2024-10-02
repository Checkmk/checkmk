#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from pathlib import Path

import pytest

from tests.testlib import on_time

from cmk.utils.user import UserId

from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.plugins.actions.audit_log import (
    SanitizeAuditLog,
    UpdateAuditLog,
    WatoAuditLogConversion,
)


@pytest.fixture(name="plugin", scope="module")
def fixture_plugin() -> UpdateAuditLog:
    test = UpdateAuditLog(
        name="update_audit_log",
        title="Split large audit logs",
        sort_index=130,
    )
    test._audit_log_target_size = 100
    return test


def test_audit_log(plugin: UpdateAuditLog) -> None:
    """
    Create new audit log, execute update action and check for result
    """
    for action, text in [
        ("add_host", "Added host"),
        ("created_user", "Created user"),
        ("change_config", "Changed config"),
    ]:
        add_change(action, text)

    assert (wato_var_dir() / "log" / "wato_audit.log").exists()

    with open(wato_var_dir() / "log" / "wato_audit.log", "rb") as f:
        expected_content = f.read()

    with on_time("2023-11-08 13:00", "CET"):
        plugin(logging.getLogger(), {})

    content = b""
    for file in [
        "wato_audit.log-backup",
        "wato_audit.log.2023-11-08-1",
        "wato_audit.log.2023-11-08-2",
        "wato_audit.log.2023-11-08-3",
        "wato_audit.log.2023-11-08-4",
    ]:
        assert (wato_var_dir() / "log" / file).exists()
        if file == "wato_audit.log-backup":
            continue

        with open(wato_var_dir() / "log" / file, "rb") as f:
            content += f.read() + b"\n"

    assert expected_content == content[:-1]  # remove duplicated b"\n"


@pytest.fixture(name="sanitize_plugin", scope="module")
def fixture_sanitize_plugin() -> SanitizeAuditLog:
    test = SanitizeAuditLog(
        name="sanitize_audit_log",
        title="Sanitize audit logs",
        sort_index=131,
    )
    return test


@pytest.mark.parametrize(
    ["entry", "expected_diff_text"],
    [
        pytest.param(
            AuditLogStore.Entry(
                time=int(time.time()),
                object_ref=None,
                user_id=UserId("automation"),
                action="edit-user",
                text="'Modified users: automation'",
                diff_text='Value of "automation_secret" changed from "IQGTEQLILOTMYGJIXUMV" to "BYHENVFFWF@RMKUBCGBG".',
            ),
            "",
            id="Simple user edit entry without \n",
        ),
        pytest.param(
            AuditLogStore.Entry(
                time=int(time.time()),
                object_ref=None,
                user_id=UserId("automation"),
                action="edit-user",
                text="'Modified users: automation'",
                diff_text='Value of "automation_secret" changed from "BYHENVFFWF@RMKUBCGBG" to "PJPKBDG@BGBOXPVSMGXS".\nAttribute "enforce_pw_change" with value False removed.\nValue of "last_pw_change" changed from 1718791477 to 1718794918.\nValue of "serial" changed from 11 to 12.',
            ),
            'Attribute "enforce_pw_change" with value False removed.\nValue of "last_pw_change" changed from 1718791477 to 1718794918.\nValue of "serial" changed from 11 to 12.',
            id="Multiple entries with \n",
        ),
        pytest.param(
            AuditLogStore.Entry(
                time=int(time.time()),
                object_ref=None,
                user_id=UserId("automation"),
                action="edit-user",
                text="'Modified users: automation'",
                diff_text='Attribute "automation_secret" with value "TRALALPCXORMUOR@HUHU" added.',
            ),
            "",
            id="Simple user creation entry without \n",
        ),
        pytest.param(
            AuditLogStore.Entry(
                time=int(time.time()),
                object_ref=None,
                user_id=UserId("automation"),
                action="edit-user",
                text="'Modified users: automation'",
                diff_text='Attribute "alias" with value "testuser" added.\nAttribute "automation_secret" with value "TRALAPCXORMUOR@HUHU" added.\nAttribute "connector" with value "htpasswd" added.\nAttribute "contactgroups" with value [] added.\nAttribute "disable_notifications" with value {} added.\nAttribute "email" with value "" added.\nAttribute "fallback_contact" with value False added.\nAttribute "force_authuser" with value False added.\nAttribute "icons_per_item" with value None added.\nAttribute "last_pw_change" with value 1719231415 added.\nAttribute "locked" with value False added.\nAttribute "nav_hide_icons_title" with value None added.\nAttribute "pager" with value "" added.\nAttribute "roles" with value [\'user\'] added.\nAttribute "serial" with value 1 added.\nAttribute "show_mode" with value None added.\nAttribute "temperature_unit" with value None added.',
            ),
            'Attribute "alias" with value "testuser" added.\nAttribute "connector" with value "htpasswd" added.\nAttribute "contactgroups" with value [] added.\nAttribute "disable_notifications" with value {} added.\nAttribute "email" with value "" added.\nAttribute "fallback_contact" with value False added.\nAttribute "force_authuser" with value False added.\nAttribute "icons_per_item" with value None added.\nAttribute "last_pw_change" with value 1719231415 added.\nAttribute "locked" with value False added.\nAttribute "nav_hide_icons_title" with value None added.\nAttribute "pager" with value "" added.\nAttribute "roles" with value [\'user\'] added.\nAttribute "serial" with value 1 added.\nAttribute "show_mode" with value None added.\nAttribute "temperature_unit" with value None added.',
            id="Multiple user creation entries with \n",
        ),
    ],
)
def test_sanitize_audit_log(
    sanitize_plugin: UpdateAuditLog, entry: AuditLogStore.Entry, expected_diff_text: str
) -> None:
    AuditLogStore().append(entry)
    update_flag = wato_var_dir() / "log" / ".werk-13330"
    if update_flag.exists():
        update_flag.unlink()
    sanitize_plugin(logging.getLogger(), {})
    assert AuditLogStore().read()[-1].diff_text == expected_diff_text


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
