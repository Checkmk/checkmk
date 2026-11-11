#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Contract tests: the audit log collector reads the files in the format the GUI writes them"""

import cmk.product_usage.collectors.audit_log as audit_log_collector
from cmk.ccc.user import UserId
from cmk.gui.watolib.audit_log import log_audit
from cmk.product_usage.schema import AuditLog
from cmk.utils import paths


def test_collector_reads_the_entries_that_the_gui_writes_to_the_audit_log() -> None:
    log_audit(action="edit-host", message="Modified host", user_id=None, use_git=False)

    audit_log = _collect()

    assert audit_log.platform.entries == 1


def test_collector_classifies_the_users_that_the_gui_writes_to_the_user_store(
    with_user: tuple[UserId, str], with_automation_user: tuple[UserId, str]
) -> None:
    log_audit(action="edit-host", message="Modified host", user_id=with_user[0], use_git=False)
    log_audit(
        action="edit-host", message="Modified host", user_id=with_automation_user[0], use_git=False
    )

    audit_log = _collect()

    assert (audit_log.interactive.entries, audit_log.automation.entries) == (1, 1)


def _collect() -> AuditLog:
    return audit_log_collector.collect(
        paths.var_dir, paths.default_config_dir, platform_user_ids=frozenset()
    )
