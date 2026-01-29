#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui.config import Config
from cmk.gui.groups import GroupType
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.utils.urls import urlencode
from cmk.gui.watolib.groups_io import all_groups

from ._base import SidebarSnapin
from ._helpers import bulletlink


class GroupSnapin(SidebarSnapin, abc.ABC):
    @abc.abstractmethod
    def _group_type_ident(self) -> str: ...

    def show(self, config: Config) -> None:
        group_type = self._group_type_ident()

        grouped_type: GroupType
        match group_type:
            case "hostgroup":
                grouped_type = "host"
            case "servicegroup":
                grouped_type = "service"
            case _:
                raise ValueError(f"Unknown group type: {group_type}")

        html.open_ul()
        for name, alias in all_groups(grouped_type):
            url = f"view.py?view_name={group_type}&{group_type}={urlencode(name)}"
            bulletlink(alias or name, url)
        html.close_ul()

    @classmethod
    def refresh_on_restart(cls) -> bool:
        return True


class HostGroups(GroupSnapin):
    def _group_type_ident(self) -> str:
        return "hostgroup"

    @staticmethod
    def type_name() -> str:
        return "hostgroups"

    @classmethod
    def title(cls) -> str:
        return _("Host groups")

    @classmethod
    def description(cls) -> str:
        return _("Directs links to all host groups")


class ServiceGroups(GroupSnapin):
    def _group_type_ident(self) -> str:
        return "servicegroup"

    @staticmethod
    def type_name() -> str:
        return "servicegroups"

    @classmethod
    def title(cls) -> str:
        return _("Service groups")

    @classmethod
    def description(cls) -> str:
        return _("Direct links to all service groups")
