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

import json

from cmk.gui.i18n import _
from cmk.gui.globals import html
import cmk.gui.sites as sites
import cmk.gui.config as config

from . import (
    SidebarSnapin,
    snapin_registry,
    snapin_width,
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


    def show(self):
        html.open_table(cellspacing=0, class_="sitestate")

        sites.update_site_states_from_dead_sites()

        for sitename, sitealias in config.sorted_sites():
            site = config.site(sitename)

            state = sites.state(sitename, {})

            if state.get("state") == None:
                state = "missing"
                text = _("Missing site")
                title = _("Site %s does not exist") % sitename

            else:
                if state["state"] == "disabled":
                    switch = "on"
                    text = site["alias"]
                    title = _("Site %s is switched off") % site["alias"]
                else:
                    switch = "off"
                    text = render_link(site["alias"], "view.py?view_name=sitehosts&site=%s" % sitename)
                    ex = state.get("exception")
                    shs = state.get("status_host_state")

                    if ex:
                        title = ex
                    else:
                        title = "Site %s is online" % site["alias"]

            html.open_tr()
            html.open_td(class_="left")
            html.write(text)
            html.close_td()
            html.open_td(class_="state")
            html.status_label_button(content=state["state"], status=state["state"],
                help=_("%s this site") % (state["state"] == "disabled" and _("enable") or _("disable")),
                onclick="switch_site('_site_switch=%s:%s')" % (sitename, switch))
            html.close_tr()
        html.close_table()


    @classmethod
    def allowed_roles(cls):
        return [ "user", "admin" ]


    def styles(self):
        return """
table.sitestate {
    width: %dpx;
}

table.sitestate td {
    padding: 1px 0px;
    text-align: right;
}

table.sitestate td.left {
    text-align: left;
}

div.snapin table.sitestate td img.iconbutton {
    width: 60px;
    height: 16px;
}

table.sitestate td.left a {
    text-align: left;
    font-weight: normal;
}

table.sitestate td.state {
    width: 60px;
    font-size: 7pt;
}

""" % snapin_width

    def page_handlers(self):
        return {
            "switch_site": self._ajax_switch_site,
        }


    def _ajax_switch_site(self):
        # _site_switch=sitename1:on,sitename2:off,...
        if not config.user.may("sidesnap.sitestatus"):
            return

        switch_var = html.var("_site_switch")
        if switch_var:
            for info in switch_var.split(","):
                sitename, onoff = info.split(":")
                if sitename not in config.sitenames():
                    continue

                d = config.user.siteconf.get(sitename, {})
                d["disabled"] = onoff != "on"
                config.user.siteconf[sitename] = d
            config.user.save_site_config()
