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

import time

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.globals import html
from . import SidebarSnapin, snapin_registry, write_snapin_exception


@snapin_registry.register
class MasterControlSnapin(SidebarSnapin):
    @staticmethod
    def type_name():
        return "master_control"

    @classmethod
    def title(cls):
        return _("Master Control")

    @classmethod
    def description(cls):
        return _("Buttons for switching globally states such as enabling "
                 "checks and notifications")

    def show(self):
        items = [
            ("enable_notifications", _("Notifications")),
            ("execute_service_checks", _("Service checks")),
            ("execute_host_checks", _("Host checks")),
            ("enable_flap_detection", _("Flap Detection")),
            ("enable_event_handlers", _("Event handlers")),
            ("process_performance_data", _("Performance data")),
            ("enable_event_handlers", _("Alert handlers")),
        ]

        sites.update_site_states_from_dead_sites()

        site_status_info = {}
        try:
            sites.live().set_prepend_site(True)
            for row in sites.live().query("GET status\nColumns: %s" %
                                          " ".join([i[0] for i in items])):
                site_id, values = row[0], row[1:]
                site_status_info[site_id] = values
        finally:
            sites.live().set_prepend_site(False)

        def _render_master_control_site(site_id):
            site_state = sites.state(site_id)
            if site_state["state"] == "dead":
                html.show_error(site_state["exception"])

            elif site_state["state"] == "disabled":
                html.show_info(_("Site is disabled"))

            elif site_state["state"] == "unknown":
                if site_state.get("exception"):
                    html.show_error(site_state["exception"])
                else:
                    html.show_error(_("Site state is unknown"))

            else:
                is_cmc = site_state["program_version"].startswith("Check_MK ")

                try:
                    site_info = site_status_info[site_id]
                except KeyError:
                    site_info = None

                html.open_table(class_="master_control")
                for i, (colname, title) in enumerate(items):
                    # Do not show event handlers on Check_MK Micro Core
                    if is_cmc and title == _("Event handlers"):
                        continue
                    elif not is_cmc and title == _("Alert handlers"):
                        continue

                    colvalue = site_info[i]
                    url = html.makeactionuri_contextless([
                        ("site", site_id),
                        ("switch", colname),
                        ("state", "%d" % (1 - colvalue)),
                    ],
                                                         filename="switch_master_state.py")
                    onclick = "cmk.ajax.get_url('%s', cmk.utils.update_contents, 'snapin_master_control')" % url

                    html.open_tr()
                    html.td(title, class_="left")
                    html.open_td()
                    html.toggle_switch(
                        enabled=colvalue,
                        help_txt=_("Switch '%s' to '%s'") %
                        (title, _("off") if colvalue else _("on")),
                        onclick=onclick,
                    )
                    html.close_td()
                    html.close_tr()

                html.close_table()

        for site_id, site_alias in config.sorted_sites():
            if not config.is_single_local_site():
                html.begin_foldable_container("master_control", site_id, True, site_alias)

            try:
                _render_master_control_site(site_id)
            except Exception as e:
                logger.exception("error rendering master control for site %s", site_id)
                write_snapin_exception(e)
            finally:
                if not config.is_single_local_site():
                    html.end_foldable_container()

    @classmethod
    def allowed_roles(cls):
        return ["admin"]

    def page_handlers(self):
        return {
            "switch_master_state": self._ajax_switch_masterstate,
        }

    def _ajax_switch_masterstate(self):
        html.set_output_format("text")

        if not config.user.may("sidesnap.master_control"):
            return

        if not html.check_transaction():
            return

        site = html.request.var("site")
        column = html.request.var("switch")
        state = int(html.request.var("state"))
        commands = {
            ("enable_notifications", 1): "ENABLE_NOTIFICATIONS",
            ("enable_notifications", 0): "DISABLE_NOTIFICATIONS",
            ("execute_service_checks", 1): "START_EXECUTING_SVC_CHECKS",
            ("execute_service_checks", 0): "STOP_EXECUTING_SVC_CHECKS",
            ("execute_host_checks", 1): "START_EXECUTING_HOST_CHECKS",
            ("execute_host_checks", 0): "STOP_EXECUTING_HOST_CHECKS",
            ("enable_flap_detection", 1): "ENABLE_FLAP_DETECTION",
            ("enable_flap_detection", 0): "DISABLE_FLAP_DETECTION",
            ("process_performance_data", 1): "ENABLE_PERFORMANCE_DATA",
            ("process_performance_data", 0): "DISABLE_PERFORMANCE_DATA",
            ("enable_event_handlers", 1): "ENABLE_EVENT_HANDLERS",
            ("enable_event_handlers", 0): "DISABLE_EVENT_HANDLERS",
        }

        command = commands.get((column, state))
        if command:
            sites.live().command("[%d] %s" % (int(time.time()), command), site)
            sites.live().set_only_sites([site])
            sites.live().query("GET status\nWaitTrigger: program\nWaitTimeout: 10000\nWaitCondition: %s = %d\nColumns: %s\n" % \
                   (column, state, column))
            sites.live().set_only_sites()
            self.show()
        else:
            html.write(_("Command %s/%d not found") % (html.attrencode(column), state))
