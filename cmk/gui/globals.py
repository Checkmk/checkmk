#!/usr/bin/env python
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

# Imports are needed for type hints. These type hints are useful for
# editors completion of "html" object methods and for mypy.
from typing import Union  # pylint: disable=unused-import
import cmk.gui.htmllib  # pylint: disable=unused-import


class Proxy(object):
    def __init__(self, name):
        super(Proxy, self).__init__()
        self._proxy_name = name
        self._current_obj = None

    def set_current(self, obj):
        self._current_obj = obj

    def unset_current(self):
        self._current_obj = None

    def in_context(self):
        return self._current_obj is not None

    def __getattribute__(self, name):
        if name in ["set_current", "unset_current", "in_context", "_current_obj", "_proxy_name"]:
            return object.__getattribute__(self, name)

        h = self._current_obj
        if h is None:
            raise AttributeError("Not in %s context" % self._proxy_name)
        return getattr(h, name)

    def __repr__(self):
        return repr(self._current_obj)


html = Proxy(name="html")  # type: Union[cmk.gui.htmllib.html, Proxy]
current_app = Proxy(name="application")
