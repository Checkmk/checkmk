#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import IconConfig
from cmk.gui.views.icon.builtin import RescheduleIcon

_ICON_CONFIG = IconConfig(
    wato_enabled=True,
    mkeventd_enabled=True,
    multisite_draw_ruleicon=True,
    staleness_threshold=1.5,
    debug=True,
)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_reschedule_icon_passes_service_name_unchanged() -> None:
    row = {
        "site": "heute",
        "host_name": "my host",
        "service_description": "Back\\slash",
        "service_cached_at": 0,
        "service_check_type": 0,
        "service_active_checks_enabled": 1,
        "service_check_command": "check_http",
    }

    result = RescheduleIcon.render(
        "service", row, [], {}, UserPermissions({}, {}, {}, []), _ICON_CONFIG
    )

    assert isinstance(result, tuple) and len(result) == 3
    assert result[2] == (
        'onclick:cmk.views.reschedule_check(this, "heute", "my host", "Back\\\\slash",'
        ' "Back\\\\slash");',
        "_self",
    )
