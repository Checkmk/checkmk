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

# Previously the current html object was available to all GUI code via the
# __builtin__ namespace while processing a request. This was tool friendly
# and has been replaced with this mechanism. We have a proxy object which
# forwards all requests to the html() object of the current request.

class HTMLProxy(object):
    def __init__(self):
        super(HTMLProxy, self).__init__()
        self._current_html = None


    def set_current(self, obj):
        self._current_html = obj


    def unset_current(self):
        self._current_html = None


    def __getattribute__(self, name):
        if name == "set_current" or name == "unset_current" or name == "_current_html":
            return object.__getattribute__(self, name)

        h = self._current_html
        if h is None:
            raise AttributeError("Not in html context")
        return getattr(h, name)


    def __repr__(self):
        return repr(self._current_html)


html = HTMLProxy()
