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

import abc
from typing import Union, Optional, Tuple  # pylint: disable=unused-import

import cmk.utils.plugin_registry


class Icon(object):
    __metaclass__ = abc.ABCMeta

    @classmethod
    def type(cls):
        # type: () -> str
        return "icon"

    @classmethod
    @abc.abstractmethod
    def ident(cls):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractmethod
    def render(self, what, row, tags, custom_vars):
        # type: (str, dict, list, dict) -> Optional[Union[HTML, Tuple, str, unicode]]
        raise NotImplementedError()

    def columns(self):
        # type: () -> List[str]
        """List of livestatus columns needed by this icon idependent of
        the queried table. The table prefix will be added to each column
        (e.g. name -> host_name)"""
        return []

    def host_columns(self):
        # type: () -> List[str]
        """List of livestatus columns needed by this icon when it is
        displayed for a host row. The prefix host_ will be added to each
        column (e.g. name -> host_name)"""
        return []

    def service_columns(self):
        # type: () -> List[str]
        """List of livestatus columns needed by this icon when it is
        displayed for a service row. The prefix host_ will be added to each
        column (e.g. description -> service_description)"""
        return []

    def default_toplevel(self):
        # type: () -> bool
        """Whether or not to display the icon in the column or the action menu"""
        return 30

    def default_sort_index(self):
        # type: () -> int
        return False

    def __init__(self):
        super(Icon, self).__init__()
        self._custom_toplevel = None  # type: Optional[bool]
        self._custom_sort_index = None  # type: Optional[int]

    def toplevel(self):
        # type: () -> bool
        if self._custom_toplevel is not None:
            return self._custom_toplevel
        return self.default_toplevel()

    def sort_index(self):
        # type: () -> int
        if self._custom_sort_index is not None:
            return self._custom_sort_index
        return self.default_sort_index()

    def override_toplevel(self, toplevel):
        # type: (bool) -> None
        self._custom_toplevel = toplevel

    def override_sort_index(self, sort_index):
        # type: (int) -> None
        self._custom_sort_index = sort_index


class IconRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return Icon

    def _register(self, plugin_class):
        self._entries[plugin_class.ident()] = plugin_class


icon_and_action_registry = IconRegistry()
