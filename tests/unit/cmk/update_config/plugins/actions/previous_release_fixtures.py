#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Global settings as a 2.5 site stored them.

These are the 2.5.0 defaults of all settings that hold more than a single
value. A 2.5 site that saved such a setting has exactly this in its global.mk,
so the tests can run the update on them without upgrading a real site.
"""

import copy
from collections.abc import Mapping

PREVIOUS_RELEASE_SETTINGS: Mapping[str, object] = {
    "acknowledge_problems": {
        "ack_sticky": False,
        "ack_notify": True,
        "ack_persistent": False,
    },
    "default_bi_layout": {
        "node_style": "builtin_hierarchy",
        "line_style": "straight",
    },
    "log_levels": {
        "cmk.web": 30,
        "cmk.web.ldap": 30,
        "cmk.web.saml2": 30,
        "cmk.web.auth": 30,
        "cmk.web.bi.compilation": 30,
        "cmk.web.automations": 30,
        "cmk.web.background-job": 30,
        "cmk.web.ui-job-scheduler": 20,
        "cmk.web.slow-views": 30,
        "cmk.web.agent_registration": 30,
    },
    "login_screen": {"hide_version": True},
    "mkeventd_service_levels": [
        (0, "(no Service level)"),
        (10, "Silver"),
        (20, "Gold"),
        (30, "Platinum"),
    ],
    "quicksearch_search_order": [
        ("menu", "continue"),
        ("h", "continue"),
        ("al", "continue"),
        ("ad", "continue"),
        ("s", "continue"),
    ],
    "session_mgmt": {
        "max_duration": {"enforce_reauth": 86400, "enforce_reauth_warning_threshold": 900},
        "user_idle_timeout": 5400,
    },
    "user_security_notification_duration": {
        "max_duration": 604800,
        "update_existing_duration": False,
    },
    "wato_icon_categories": [("logos", "Logos"), ("parts", "Parts"), ("misc", "Misc")],
}

UPDATED_PREVIOUS_RELEASE_SETTINGS: Mapping[str, object] = {
    **PREVIOUS_RELEASE_SETTINGS,
    # CMK-36979 renamed the automations logger; nothing else converts.
    "log_levels": {
        "cmk.web": 30,
        "cmk.web.ldap": 30,
        "cmk.web.saml2": 30,
        "cmk.web.auth": 30,
        "cmk.web.bi.compilation": 30,
        "cmk.automations": 30,
        "cmk.web.background-job": 30,
        "cmk.web.ui-job-scheduler": 20,
        "cmk.web.slow-views": 30,
        "cmk.web.agent_registration": 30,
    },
}

WITHDRAWN_SINCE_THE_PREVIOUS_RELEASE = (
    "config_storage_format",
    "enable_deprecated_automation_user_authentication",
)
"""Settings 2.5 had and this release no longer offers. The update drops them
because they are no longer known, not because a list names them."""


def previous_release_settings() -> dict[str, object]:
    """A fresh copy each time, because the update changes the dict it gets."""
    return copy.deepcopy(dict(PREVIOUS_RELEASE_SETTINGS))
