#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import cmk.gui.sites as sites
from cmk.gui.globals import html, request, response, user
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import (
    begin_footnote_links,
    end_footnote_links,
    link,
    render_link,
    SidebarSnapin,
    snapin_registry,
)
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.urls import makeuri_contextless


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
        return _("Site status")

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
                url = makeuri_contextless(
                    request,
                    [
                        ("_site_switch", "%s:%s" % (sitename, switch)),
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
    def allowed_roles(cls):
        return ["user", "admin"]

    def page_handlers(self):
        return {
            "switch_site": self._ajax_switch_site,
            "set_all_sites": self._ajax_set_all_sites,
        }

    def _ajax_switch_site(self):
        check_csrf_token()
        response.set_content_type("application/json")
        # _site_switch=sitename1:on,sitename2:off,...
        if not user.may("sidesnap.sitestatus"):
            return

        switch_var = request.var("_site_switch")
        if switch_var:
            for info in switch_var.split(","):
                sitename, onoff = info.split(":")
                if sitename not in sites.sitenames():
                    continue

                if onoff == "on":
                    user.enable_site(sitename)
                else:
                    user.disable_site(sitename)

            user.save_site_config()

    def _ajax_set_all_sites(self):
        sites.update_site_states_from_dead_sites()
        new_state = request.var("_new_state")

        for sitename, _sitealias in sites.sorted_sites():
            current_state = sites.states().get(sitename, sites.SiteStatus({})).get("state")

            # Enable all disabled sites
            if new_state == "online" and current_state == "disabled":
                user.enable_site(sitename)
            # Disable all online sites
            elif new_state == "disabled" and current_state == "online":
                user.disable_site(sitename)

        user.save_site_config()
