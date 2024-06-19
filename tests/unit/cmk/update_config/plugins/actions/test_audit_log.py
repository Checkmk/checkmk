#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time

import pytest

from cmk.utils.type_defs import UserId

from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.plugins.actions.audit_log import SanitizeAuditLog


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
            id="Simple entry without \n",
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
    ],
)
def test_sanitize_audit_log(
    sanitize_plugin: SanitizeAuditLog, entry: AuditLogStore.Entry, expected_diff_text: str
) -> None:
    AuditLogStore(AuditLogStore.make_path()).append(entry)
    update_flag = wato_var_dir() / "log" / ".werk-13330"
    if update_flag.exists():
        update_flag.unlink()
    sanitize_plugin(logging.getLogger(), {})
    assert AuditLogStore(AuditLogStore.make_path()).read()[-1].diff_text == expected_diff_text
