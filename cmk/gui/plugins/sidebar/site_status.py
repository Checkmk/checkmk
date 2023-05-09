#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.gui.i18n import _
from cmk.gui.globals import html
import cmk.gui.sites as sites
import cmk.gui.config as config

from cmk.gui.plugins.sidebar import (
    SidebarSnapin,
    snapin_registry,
    render_link,
)


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
        return _("Connection state of each site and button for enabling "
                 "and disabling the site connection")

    def show(self) -> None:
        html.open_table(cellspacing="0", class_="sitestate")

        sites.update_site_states_from_dead_sites()

        for sitename, _sitealias in config.sorted_sites():
            site = config.site(sitename)

            state = sites.states().get(sitename, sites.SiteStatus({})).get("state")

            if state is None:
                state = "missing"
                switch = "missing"
                text = sitename

            else:
                if state == "disabled":
                    switch = "on"
                    text = site["alias"]
                else:
                    switch = "off"
                    text = render_link(site["alias"],
                                       "view.py?view_name=sitehosts&site=%s" % sitename)

            html.open_tr()
            html.open_td(class_="left")
            html.write(text)
            html.close_td()
            html.open_td(class_="state")
            if switch == "missing":
                html.status_label(content=state, status=state, title=_("Site is missing"))
            else:
                url = html.makeactionuri_contextless([
                    ("_site_switch", "%s:%s" % (sitename, switch)),
                ],
                                                     filename="switch_site.py")
                html.status_label_button(
                    content=state,
                    status=state,
                    title=_("enable this site") if state == "disabled" else _("disable this site"),
                    onclick="cmk.sidebar.switch_site(%s)" % (json.dumps(url)))
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
        html.set_output_format("json")
        # _site_switch=sitename1:on,sitename2:off,...
        if not config.user.may("sidesnap.sitestatus"):
            return

        if not html.check_transaction():
            return

        switch_var = html.request.var("_site_switch")
        if switch_var:
            for info in switch_var.split(","):
                sitename, onoff = info.split(":")
                if sitename not in config.sitenames():
                    continue

                if onoff == "on":
                    config.user.enable_site(sitename)
                else:
                    config.user.disable_site(sitename)

            config.user.save_site_config()
