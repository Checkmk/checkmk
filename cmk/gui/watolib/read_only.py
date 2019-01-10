#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""WATO can be set into read only mode manually."""
import time

import cmk.utils.render as render

import cmk.gui.config as config
from cmk.gui.i18n import _
from cmk.gui.globals import html


def message():
    text = _("The configuration is currently in read only mode. ")

    if config.wato_read_only["enabled"] is True:
        text += _("The read only mode is enabled until it is turned of manually. ")

    elif isinstance(config.wato_read_only['enabled'], tuple):
        end_time = config.wato_read_only['enabled'][1]
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
    if isinstance(config.wato_read_only['enabled'], tuple):
        start_time, end_time = config.wato_read_only['enabled']
        return start_time <= time.time() <= end_time
    return False


def may_override():
    return config.user.id in config.wato_read_only["rw_users"] \
            or (html.request.var("mode") == "read_only" and config.user.may("wato.set_read_only"))
