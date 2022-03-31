#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from livestatus import SiteId

import cmk.gui.site_config as site_config
import cmk.gui.sites as sites
from cmk.gui.globals import html, request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.plugins.sidebar.utils import render_link, SidebarSnapin, snapin_registry
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri_contextless


@snapin_registry.register
class SiteStatus(SidebarSnapin):
    @staticmethod
    def type_name():
        return "sitestatus"

    @classmethod
    def refresh_regularly(cls):
        return True

    @classmethod
    def title(cls):
        return _("Site Status")

    @classmethod
    def description(cls):
        return _(
            "Connection state of each site and button for enabling "
            "and disabling the site connection"
        )

    def show(self) -> None:
        html.open_table(cellspacing="0", class_="sitestate")

        sites.update_site_states_from_dead_sites()

        for sitename, _sitealias in sites.sorted_sites():
            site = sites.get_site_config(sitename)

            state = sites.states().get(sitename, sites.SiteStatus({})).get("state")

            if state is None:
                state = "missing"
                switch = "missing"
                text = escape_to_html(sitename)

            else:
                if state == "disabled":
                    switch = "on"
                    text = escape_to_html(site["alias"])
                else:
                    switch = "off"
                    text = render_link(
                        site["alias"], "view.py?view_name=sitehosts&site=%s" % sitename
                    )

            html.open_tr()
            html.td(text, class_="left")
            html.open_td(class_="state")
            if switch == "missing":
                html.status_label(content=state, status=state, title=_("Site is missing"))
            else:
                url = makeactionuri_contextless(
                    request,
                    transactions,
                    [
                        ("_site_switch", "%s:%s" % (sitename, switch)),
                    ],
                    filename="switch_site.py",
                )
                html.status_label_button(
                    content=state,
                    status=state,
                    title=_("enable this site") if state == "disabled" else _("disable this site"),
                    onclick="cmk.sidebar.switch_site(%s)" % (json.dumps(url)),
                )
            html.close_tr()
        html.close_table()

    @classmethod
    def allowed_roles(cls):
        return ["user", "admin"]

    def page_handlers(self):
        return {
            "switch_site": self._ajax_switch_site,
        }

    def _ajax_switch_site(self):
        response.set_content_type("application/json")
        # _site_switch=sitename1:on,sitename2:off,...
        if not user.may("sidesnap.sitestatus"):
            return

        if not transactions.check_transaction():
            return

        switch_var = request.var("_site_switch")
        if switch_var:
            for info in switch_var.split(","):
                sitename_str, onoff = info.split(":")
                sitename = SiteId(sitename_str)
                if sitename not in site_config.sitenames():
                    continue

                if onoff == "on":
                    user.enable_site(sitename)
                else:
                    user.disable_site(sitename)

            user.save_site_config()
