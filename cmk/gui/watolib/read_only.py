#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO can be set into read only mode manually."""
import time

import cmk.utils.render as render

from cmk.gui.config import active_config
from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user


def message():
    text = _("The configuration is currently in read only mode. ")

    if active_config.wato_read_only["enabled"] is True:
        text += _("The read only mode is enabled until it is turned of manually. ")

    elif isinstance(active_config.wato_read_only["enabled"], tuple):
        end_time = active_config.wato_read_only["enabled"][1]
        text += _("The read only mode is enabled until %s. ") % render.date_and_time(end_time)

    if may_override():
        text += _("But you are allowed to make changes anyway. ")

    text += "<br><br>" + _("Reason: %s") % active_config.wato_read_only["message"]

    return text


def is_enabled():
    if not active_config.wato_read_only:
        return False
    if active_config.wato_read_only["enabled"] is True:
        return True
    if isinstance(active_config.wato_read_only["enabled"], tuple):
        start_time, end_time = active_config.wato_read_only["enabled"]
        return start_time <= time.time() <= end_time
    return False


def may_override():
    return user.id in active_config.wato_read_only["rw_users"] or (
        request.var("mode") == "read_only" and user.may("wato.set_read_only")
    )
