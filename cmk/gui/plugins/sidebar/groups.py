#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

import cmk.gui.sites as sites
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import bulletlink, SidebarSnapin, snapin_registry
from cmk.gui.utils.urls import urlencode


class GroupSnapin(SidebarSnapin, abc.ABC):
    @abc.abstractmethod
    def _group_type_ident(self):
        raise NotImplementedError()

    def show(self):
        group_type = self._group_type_ident()
        html.open_ul()
        for name, alias in sites.all_groups(group_type.replace("group", "")):
            url = "view.py?view_name=%s&%s=%s" % (group_type, group_type, urlencode(name))
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
        return _("Host groups")

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
        return _("Service groups")

    @classmethod
    def description(cls):
        return _("Direct links to all service groups")
