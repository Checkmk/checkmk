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

import logging as _logging

import cmk.utils.log
import cmk.utils.paths


class CMKWebLogger(_logging.getLoggerClass()):
    def exception(self, msg, *args, **kwargs):
        from cmk.gui.globals import html
        if html:
            msg = "%s %s" % (html.request.requested_url, msg)

        super(CMKWebLogger, self).exception(msg, *args, **kwargs)


_logging.setLoggerClass(CMKWebLogger)

logger = cmk.utils.log.get_logger("web")


def init_logging():
    handler = _logging.FileHandler("%s/web.log" % cmk.utils.paths.log_dir, encoding="UTF-8")
    handler.setFormatter(cmk.utils.log.get_formatter())
    root = _logging.getLogger()
    del root.handlers[:]  # Remove all previously existing handlers
    root.addHandler(handler)


def set_log_levels(log_levels):
    for name, level in _augmented_log_levels(log_levels).iteritems():
        _logging.getLogger(name).setLevel(level)


# To see log entries from libraries and non-GUI code, reuse cmk.web's level.
def _augmented_log_levels(log_levels):
    root_level = log_levels.get("cmk.web")
    all_levels = {} if root_level is None else {"": root_level, "cmk": root_level}
    all_levels.update(log_levels)
    return all_levels
