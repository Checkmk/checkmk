#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.notification_parameter import notification_parameter_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_notification_parameters() -> None:
    assert set(notification_parameter_registry) == {
        "asciimail",
        "cisco_webex_teams",
        "ilert",
        "mail",
        "mkeventd",
        "msteams",
        "opsgenie_issues",
        "pagerduty",
        "pushover",
        "signl4",
        "slack",
        "sms_api",
        "spectrum",
        "victorops",
    }
