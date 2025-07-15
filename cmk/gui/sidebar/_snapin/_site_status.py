#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.ccc.site import SiteId

from cmk.gui import sites, user_sites
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import RoleName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless

from ._base import PageHandlers, SidebarSnapin
from ._helpers import begin_footnote_links, end_footnote_links, link, render_link


class SiteStatus(SidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "sitestatus"

    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    @classmethod
    def title(cls) -> str:
        return _("Site status")

    @classmethod
    def description(cls) -> str:
        return _(
            "Connection state of each site and button for enabling "
            "and disabling the site connection"
        )

    def show(self, config: Config) -> None:
        html.open_table(cellspacing="0", class_="sitestate")

        sites.update_site_states_from_dead_sites()

        for sitename, _sitealias in user_sites.sorted_sites():
            site = config.sites[sitename]

            state = sites.states().get(sitename, sites.SiteStatus({})).get("state")

            if state is None:
                state = "missing"
                switch = "missing"
                text = HTML.with_escaping(sitename)

            elif state == "disabled":
                switch = "on"
                text = HTML.with_escaping(site["alias"])
            else:
                switch = "off"
                text = render_link(site["alias"], "view.py?view_name=sitehosts&site=%s" % sitename)

            html.open_tr()
            html.td(text, class_="left")
            html.open_td(class_="state")
            if switch == "missing":
                html.status_label(content=state, status=state, title=_("Site is missing"))
            else:
                url = makeuri_contextless(
                    request,
                    [
                        ("_site_switch", f"{sitename}:{switch}"),
                    ],
                    filename="switch_site.py",
                )
                html.status_label_button(
                    content=state,
                    status=state,
                    title=_("Enable this site") if state == "disabled" else _("Disable this site"),
                    onclick="cmk.sidebar.switch_site(%s)" % (json.dumps(url)),
                )
            html.close_tr()
        html.close_table()

        enable_all_url = makeuri_contextless(
            request,
            [
                ("_new_state", "online"),
            ],
            filename="set_all_sites.py",
        )
        disable_all_url = makeuri_contextless(
            request,
            [
                ("_new_state", "disabled"),
            ],
            filename="set_all_sites.py",
        )

        begin_footnote_links()
        link(
            _("Enable all"),
            "javascript:void(0)",
            onclick="cmk.sidebar.switch_site(%s)" % json.dumps(enable_all_url),
        )
        link(
            _("Disable all"),
            "javascript:void(0)",
            onclick="cmk.sidebar.switch_site(%s)" % json.dumps(disable_all_url),
        )
        end_footnote_links()

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return ["user", "admin"]

    def page_handlers(self) -> PageHandlers:
        return {
            "switch_site": self._ajax_switch_site,
            "set_all_sites": self._ajax_set_all_sites,
        }

    def _ajax_switch_site(self, config: Config) -> None:
        check_csrf_token()
        response.set_content_type("application/json")
        # _site_switch=sitename1:on,sitename2:off,...
        if not user.may("sidesnap.sitestatus"):
            return

        switch_var = request.var("_site_switch")
        if switch_var:
            for info in switch_var.split(","):
                sitename_str, onoff = info.split(":")
                sitename = SiteId(sitename_str)
                if sitename not in config.sites:
                    continue

                if onoff == "on":
                    user.enable_site(sitename)
                else:
                    user.disable_site(sitename)

            user.save_site_config()

    def _ajax_set_all_sites(self, config: Config) -> None:
        sites.update_site_states_from_dead_sites()
        new_state = request.var("_new_state")

        for sitename, _sitealias in user_sites.sorted_sites():
            current_state = sites.states().get(sitename, sites.SiteStatus({})).get("state")

            # Enable all disabled sites
            if new_state == "online" and current_state == "disabled":
                user.enable_site(SiteId(sitename))
            # Disable all online sites
            elif new_state == "disabled" and current_state == "online":
                user.disable_site(SiteId(sitename))

        user.save_site_config()
