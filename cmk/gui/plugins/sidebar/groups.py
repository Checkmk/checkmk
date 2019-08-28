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

import abc
import six

import cmk.gui.sites as sites
from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    bulletlink,
)
from cmk.gui.i18n import _
from cmk.gui.globals import html


class GroupSnapin(six.with_metaclass(abc.ABCMeta, SidebarSnapin)):
    @abc.abstractmethod
    def _group_type_ident(self):
        raise NotImplementedError()

    def show(self):
        group_type = self._group_type_ident()
        html.open_ul()
        for name, alias in sites.all_groups(group_type.replace("group", "")):
            url = "view.py?view_name=%s&%s=%s" % (group_type, group_type, html.urlencode(name))
            bulletlink(alias or name, url)
        html.close_ul()

    @classmethod
    def refresh_on_restart(cls):
        return True


@snapin_registry.register
class HostGroups(GroupSnapin):
    def _group_type_ident(self):
        return "hostgroup"

    @staticmethod
    def type_name():
        return "hostgroups"

    @classmethod
    def title(cls):
        return _("Host Groups")

    @classmethod
    def description(cls):
        return _("Directs links to all host groups")


@snapin_registry.register
class ServiceGroups(GroupSnapin):
    def _group_type_ident(self):
        return "servicegroup"

    @staticmethod
    def type_name():
        return "servicegroups"

    @classmethod
    def title(cls):
        return _("Service Groups")

    @classmethod
    def description(cls):
        return _("Direct links to all service groups")
