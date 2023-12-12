#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from pytest_mock import MockerFixture

from tests.testlib import on_time

from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.paths import wato_var_dir

from cmk.update_config.plugins.actions.audit_log import UpdateAuditLog


@pytest.fixture(name="plugin", scope="module")
def fixture_plugin() -> UpdateAuditLog:
    test = UpdateAuditLog(
        name="update_audit_log",
        title="Split large audit logs",
        sort_index=130,
    )
    test._audit_log_target_size = 100
    return test


def test_audit_log(plugin: UpdateAuditLog, mocker: MockerFixture) -> None:
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
            content += f.read() + b"\0"

    assert expected_content == content[:-1]  # remove duplicated b"\0"
