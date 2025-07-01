#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import Config
from cmk.gui.dashboard import get_permitted_dashboards
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import MainMenuTopic

from ._base import SidebarSnapin
from ._helpers import footnotelinks, make_main_menu, show_main_menu


class Dashboards(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "dashboards"

    @classmethod
    def title(cls) -> str:
        return _("Dashboards")

    @classmethod
    def description(cls) -> str:
        return _("Links to all dashboards")

    def show(self, config: Config) -> None:
        show_main_menu(treename="dashboards", menu=self._get_dashboard_menu_items())

        links = []
        if user.may("general.edit_dashboards"):
            if config.debug:
                links.append((_("Export"), "export_dashboards.py"))
            links.append((_("Edit"), "edit_dashboards.py"))
            footnotelinks(links)

    def _get_dashboard_menu_items(self) -> list[MainMenuTopic]:
        return make_main_menu(
            [("dashboards", (k, v)) for k, v in get_permitted_dashboards().items()]
        )
