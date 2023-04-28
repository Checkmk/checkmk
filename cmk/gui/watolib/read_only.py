#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""WATO can be set into read only mode manually."""
import time

import cmk.utils.render as render

from cmk.gui.globals import config, request, user
from cmk.gui.i18n import _


def message():
    text = _("The configuration is currently in read only mode. ")

    if config.wato_read_only["enabled"] is True:
        text += _("The read only mode is enabled until it is turned of manually. ")

    elif isinstance(config.wato_read_only["enabled"], tuple):
        end_time = config.wato_read_only["enabled"][1]
        text += _("The read only mode is enabled until %s. ") % render.date_and_time(end_time)

    if may_override():
        text += _("But you are allowed to make changes anyway. ")

    text += "<br><br>" + _("Reason: %s") % config.wato_read_only["message"]

    return text


def is_enabled():
    if not config.wato_read_only:
        return False
    if config.wato_read_only["enabled"] is True:
        return True
    if isinstance(config.wato_read_only["enabled"], tuple):
        start_time, end_time = config.wato_read_only["enabled"]
        return start_time <= time.time() <= end_time
    return False


def may_override():
    return user.id in config.wato_read_only["rw_users"] or (
        request.var("mode") == "read_only" and user.may("wato.set_read_only")
    )
