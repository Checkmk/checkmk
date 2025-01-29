#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui import sites
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.utils.urls import urlencode

from ._base import SidebarSnapin
from ._helpers import bulletlink


class GroupSnapin(SidebarSnapin, abc.ABC):
    @abc.abstractmethod
    def _group_type_ident(self):
        raise NotImplementedError()

    def show(self):
        group_type = self._group_type_ident()
        html.open_ul()
        for name, alias in sites.all_groups(group_type.replace("group", "")):
            url = f"view.py?view_name={group_type}&{group_type}={urlencode(name)}"
            bulletlink(alias or name, url)
        html.close_ul()

    @classmethod
    def refresh_on_restart(cls):
        return True


class HostGroups(GroupSnapin):
    def _group_type_ident(self):
        return "hostgroup"

    @staticmethod
    def type_name():
        return "hostgroups"

    @classmethod
    def title(cls):
        return _("Host groups")

    @classmethod
    def description(cls):
        return _("Directs links to all host groups")


class ServiceGroups(GroupSnapin):
    def _group_type_ident(self):
        return "servicegroup"

    @staticmethod
    def type_name():
        return "servicegroups"

    @classmethod
    def title(cls):
        return _("Service groups")

    @classmethod
    def description(cls):
        return _("Direct links to all service groups")
