#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Some helpers for ntop related GUI code

Needs to be part of the generic code, not packed into NTOP addon.
"""

from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.logged_in import user


def get_ntop_connection() -> dict | None:
    # Use this function if you *really* want to try accessing the ntop connection settings
    try:
        # ntop is currently part of CEE and will *only* be defined if we are a CEE
        return active_config.ntop_connection  # type: ignore[attr-defined, unused-ignore]
    except AttributeError:
        return None


def get_ntop_connection_mandatory() -> dict:
    connection = get_ntop_connection()
    return connection if connection else {}


def is_ntop_available() -> bool:
    # Use this function if you want to know if the ntop intergration is available in general
    return isinstance(get_ntop_connection(), dict)


def is_ntop_active() -> bool:
    if not is_ntop_available():
        return False

    ntop = get_ntop_connection_mandatory()
    if not ntop.get("is_activated", False):
        return False
    return True


def is_ntop_configured() -> bool:
    # Use this function if you want to know if the connection to ntop is fully set-up
    # e.g. to decide if ntop links should be hidden

    if not is_ntop_available():
        return False

    ntop = get_ntop_connection_mandatory()
    if not ntop.get("is_activated", False):
        return False

    custom_attribute_name = ntop.get("use_custom_attribute_as_ntop_username", False)
    # We currently have two options to get an ntop username
    # 1) User needs to define his own -> if this string is empty, declare ntop as not configured
    # 2) Take the checkmk username as ntop username -> always declare ntop as configured
    return (
        bool(user.get_attribute(custom_attribute_name, ""))
        if isinstance(custom_attribute_name, str)
        else not custom_attribute_name
    )


def use_ntopng_host_filter() -> bool:
    return get_ntop_connection_mandatory().get("is_host_filter_activated", True)


def get_ntop_misconfiguration_reason() -> str:
    if not is_ntop_available():
        return _("ntopng integration is only available in CEE")
    ntop = get_ntop_connection()
    assert isinstance(ntop, dict)
    if not ntop.get("is_activated", False):
        return _("ntopng integration is not activated under global settings.")
    custom_attribute_name = ntop.get("use_custom_attribute_as_ntop_username", "")
    if custom_attribute_name and not user.get_attribute(custom_attribute_name, ""):
        return _(
            "The ntopng username should be derived from 'ntopng Username' "
            "under the current's user settings (identity) but this is not "
            "set for the current user."
        )
    return ""
