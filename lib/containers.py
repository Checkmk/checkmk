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

# This file contains special containers needed for data representation

from collections import OrderedDict

# Dictionary class with the ability of appending items like provided
# by a list.
class AutomaticDict(OrderedDict):

    def __init__(self, list_identifier = None, start_index = None):
        OrderedDict.__init__(self)
        self._list_identifier = list_identifier or "item"
        self._item_index = start_index or 0

    def __getitem__(self, item):
        if item in self.keys():
            return OrderedDict.__getitem__(self, item)
        else:
            return self["%s_%i" %(self._list_identifier, item)]

    def append(self, item):
        self["%s_%i" %(self._list_identifier, self._item_index)] = item
        self._item_index += 1
