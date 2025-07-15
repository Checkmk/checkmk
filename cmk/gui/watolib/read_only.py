#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Setup can be set into read only mode manually."""

import time

from cmk.utils import render

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ReadOnlySpec


def message(read_only_config: ReadOnlySpec) -> str:
    text = _("The configuration is currently in read only mode. ")

    if read_only_config["enabled"] is True:
        text += _("The read only mode is enabled until it is turned of manually. ")

    elif isinstance(read_only_config["enabled"], tuple):
        end_time = read_only_config["enabled"][1]
        text += _("The read only mode is enabled until %s. ") % render.date_and_time(end_time)

    if may_override(read_only_config):
        text += _("But you are allowed to make changes anyway. ")

    text += "<br><br>" + _("Reason: %s") % read_only_config["message"]

    return text


def is_enabled(read_only_config: ReadOnlySpec) -> bool:
    if not read_only_config:
        return False
    if read_only_config["enabled"] is True:
        return True
    if isinstance(read_only_config["enabled"], tuple):
        start_time, end_time = read_only_config["enabled"]
        return start_time <= time.time() <= end_time
    return False


def may_override(read_only_config: ReadOnlySpec) -> bool:
    return user.id in read_only_config["rw_users"] or (
        request.var("mode") == "read_only" and user.may("wato.set_read_only")
    )
