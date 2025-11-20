#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.utils.notify_types import EventRule

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib.notifications import (
    NotificationRuleConfigFile,
)

from cmk.update_config.plugins.pre_actions.migrate_html_email import (
    PreMigrateHtmlEmail,
)
from cmk.update_config.plugins.pre_actions.utils import ConflictMode


@pytest.mark.parametrize(
    ["rule_config", "expected", "expected_error"],
    [
        pytest.param(
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", {"from": "lala@po.com"}),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", {"from": {"address": "lala@po.com"}}),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            None,
            id="Single rule with HTML email in old format",
        ),
        pytest.param(
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", {"from": {"address": "lala@po.com"}}),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", {"from": {"address": "lala@po.com"}}),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            None,
            id="Single rule with HTML email rule in new format",
        ),
        pytest.param(
            [
                {
                    "rule_id": "6a7ab251-e0ec-419f-b90e-07159f0680dc",
                    "allow_disable": True,
                    "contact_all": False,
                    "contact_all_with_email": False,
                    "contact_object": True,
                    "description": "HTML email to all contacts about service/host status changes",
                    "disabled": False,
                    "notify_plugin": ("mail", "4869b78e-bbef-5138-a828-5f290405557c"),
                    "match_host_event": ["?d", "?r"],
                    "match_service_event": ["?c", "?w", "?r"],
                }
            ],
            [
                {
                    "rule_id": "6a7ab251-e0ec-419f-b90e-07159f0680dc",
                    "allow_disable": True,
                    "contact_all": False,
                    "contact_all_with_email": False,
                    "contact_object": True,
                    "description": "HTML email to all contacts about service/host status changes",
                    "disabled": False,
                    "notify_plugin": ("mail", "4869b78e-bbef-5138-a828-5f290405557c"),
                    "match_host_event": ["?d", "?r"],
                    "match_service_event": ["?c", "?w", "?r"],
                }
            ],
            None,
            id="Single rule, parameter already migrated",
        ),
        pytest.param(
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", {"from": "Some invalid string"}),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            [],
            "invalid email address",
            id="Single rule with HTML email in invalid format",
        ),
        pytest.param(
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", None),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            [
                {
                    "comment": "",
                    "allow_disable": True,
                    "description": "Notify all contacts of a host/service via HTML email",
                    "disabled": False,
                    "notify_plugin": ("mail", None),
                    "contact_all_with_email": False,
                    "docu_url": "",
                    "contact_all": False,
                    "contact_object": True,
                }
            ],
            None,
            id="Single rule with no parameters",
        ),
    ],
)
def test_migrate_html_email(
    rule_config: list[EventRule], expected: list[EventRule], expected_error: str | None
) -> None:
    with application_and_request_context():
        NotificationRuleConfigFile().save(rule_config)

        if expected_error:
            with pytest.raises(MKUserError) as e:
                _migrate()
            assert expected_error == e.value.args[1]
        else:
            _migrate()
            assert expected == NotificationRuleConfigFile().load_for_reading()


def _migrate() -> None:
    PreMigrateHtmlEmail(
        name="migrate_notification_parameters",
        title="Migrate notification parameters",
        sort_index=50,
    )(logging.getLogger(), ConflictMode.ABORT)
