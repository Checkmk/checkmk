#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.views.command import command_registry

COMMAND_PERMISSION_PAIRS = (
    ("acknowledge", "action.acknowledge"),
    ("add_comment", "action.addcomment"),
    ("clear_modified_attributes", "action.clearmodattr"),
    ("delete_crash_reports", "action.delete_crash_report"),
    ("ec_archive_event", "mkeventd.delete"),
    ("ec_archive_events_of_host", "mkeventd.archive_events_of_hosts"),
    ("ec_change_state", "mkeventd.changestate"),
    ("ec_custom_actions", "mkeventd.actions"),
    ("ec_update_event", "mkeventd.update"),
    ("fake_check_result", "action.fakechecks"),
    ("freeze_aggregation", "action.aggregation_freeze"),
    ("notifications", "action.notifications"),
    ("remove_acknowledgments", "action.acknowledge"),
    ("remove_comments", "action.addcomment"),
    ("remove_downtimes", "action.downtimes"),
    ("remove_downtimes_hosts_services", "action.downtimes"),
    ("reschedule", "action.reschedule"),
    ("schedule_downtimes", "action.downtimes"),
    ("send_custom_notification", "action.customnotification"),
    ("toggle_active_checks", "action.enablechecks"),
    ("toggle_passive_checks", "action.enablechecks"),
)


@pytest.mark.parametrize("command_ident, permission_name", COMMAND_PERMISSION_PAIRS)
def test_command_requires_permission(command_ident: str, permission_name: str) -> None:
    assert command_registry[command_ident].permission.name == permission_name


def test_all_commands_covered() -> None:
    # This asserts that we have all commands covered.
    # But beware: What commands are in the registry here is determined by the bazel runtime files.
    # A command disappearing from here is not a bad thing, it may mean we have better test
    # separation. Testing this this way may not be sustainable, but we'll see.
    assert set(command_registry) == {ident for ident, _permission in COMMAND_PERMISSION_PAIRS}
