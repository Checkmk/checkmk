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

import livestatus

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.notifications as notifications
from cmk.gui.i18n import _
from cmk.gui.globals import html
from . import (
    SidebarSnapin,
    snapin_registry,
    write_snapin_exception,
    snapin_width,
    link,
)

@snapin_registry.register
class TacticalOverviewSnapin(SidebarSnapin):
    @staticmethod
    def type_name():
        return "tactical_overview"


    @classmethod
    def title(cls):
        return _("Tactical Overview")


    @classmethod
    def description(cls):
        return _("The total number of hosts and service with and without problems")


    @classmethod
    def refresh_regularly(cls):
        return True


    def show(self):
        #def render_tactical_overview(extra_filter_headers="", extra_url_variables=None):
        extra_filter_headers = ""
        extra_url_variables = None

        if extra_url_variables is None:
            extra_url_variables = []

        hstdata, svcdata, notdata, event_data = self._get_tactical_overview_data(extra_filter_headers)

        if hstdata is None or svcdata is None or notdata is None or event_data is None:
            html.center(_("No data from any site"))
            return

        td_class = 'col3'
        if hstdata[-1] or svcdata[-1]:
            td_class = 'col4'

        rows = [
            {
                "what"  : 'host',
                "title" : _("Hosts"),
                "data"  : hstdata,
                "views" : {
                    "all"       : [
                        ("view_name", "allhosts"),
                    ],
                    "handled"   : [
                        ("view_name", 'hostproblems'),
                    ],
                    "unhandled" : [
                        ("view_name", "hostproblems"),
                        ("is_host_acknowledged", 0),
                    ],
                    "stale"     : [
                        ("view_name", 'stale_hosts'),
                    ],
                },
            },
            {
                "what"  : "service",
                "title" : _("Services"),
                "data"  : svcdata,
                "views" : {
                    "all"       : [
                        ("view_name", "allservices"),
                    ],
                    "handled"   : [
                        ("view_name", "svcproblems"),
                    ],
                    "unhandled" : [
                        ("view_name", "svcproblems"),
                        ("is_service_acknowledged", 0),
                    ],
                    "stale"     : [
                        ("view_name", "uncheckedsvc"),
                    ],
                },
            }
        ]

        if config.user.may("mkeventd.see_in_tactical_overview"):
            rows.append({
                "what"  : "event",
                "title" : _("Events"),
                "data"  : event_data,
                "views" : {
                    "all"       : [
                        ("view_name", "ec_events"),
                    ],
                    "handled"   : [
                        ("view_name", "ec_events"),
                        ("event_state_1", "on"),
                        ("event_state_2", "on"),
                        ("event_state_3", "on"),

                    ],
                    "unhandled" : [
                        ("view_name", "ec_events"),
                        ("event_phase_open", "on"),
                        ("event_state_1", "on"),
                        ("event_state_2", "on"),
                        ("event_state_3", "on"),
                        ("is_event_host_in_downtime", "0"),
                    ],
                    "stale"     : None,
                },
            })

        html.open_table(class_=["content_center", "tacticaloverview"], cellspacing=2, cellpadding=0, border=0)

        show_stales = config.user.may("general.see_stales_in_tactical_overview")

        for row in rows:
            if row["what"] == "event":
                amount, problems, unhandled_problems = row["data"]
                stales = 0

                # no events open and disabled in local site: don't show events
                if amount == 0 and not config.mkeventd_enabled:
                    continue
            else:
                amount, problems, unhandled_problems, stales = row["data"]

            html.open_tr()
            html.th(row["title"])
            html.th(_("Problems"))
            html.th(_("Unhandled"))
            if show_stales and td_class == 'col4':
                html.th(_("Stale"))
            html.close_tr()

            html.open_tr()
            url = html.makeuri_contextless(row["views"]["all"] + extra_url_variables,filename="view.py")
            html.open_td(class_=["total", td_class])
            html.a(amount, href=url, target="main")
            html.close_td()

            for value, ty in [ (problems, "handled"), (unhandled_problems, "unhandled") ]:
                url = html.makeuri_contextless(row["views"][ty] + extra_url_variables, filename="view.py")
                html.open_td(class_=[td_class, "states prob" if value != 0 else None])
                link(str(value), url)
                html.close_td()

            if show_stales and td_class == 'col4':
                if row["views"]["stale"]:
                    url = html.makeuri_contextless(row["views"]["stale"] + extra_url_variables, filename="view.py")
                    html.open_td(class_=[td_class, "states prob" if stales != 0 else None])
                    link(str(stales), url)
                    html.close_td()
                else:
                    html.td('')

            html.close_tr()
        html.close_table()

        failed_notifications = notdata[0]
        if failed_notifications:
            html.open_div(class_="spacertop")
            html.open_div(class_="tacticalalert")

            confirm_url = html.makeuri_contextless(extra_url_variables,
                                                   filename="clear_failed_notifications.py")
            html.icon_button(confirm_url, _("Confirm failed notifications"), "delete", target="main")

            view_url = html.makeuri_contextless(
                [("view_name", "failed_notifications")] + extra_url_variables, filename="view.py")

            html.a(_("%d failed notifications") % failed_notifications, target="main", href=view_url)
            html.close_div()
            html.close_div()


    def _get_tactical_overview_data(self, extra_filter_headers):
        configured_staleness_threshold = config.staleness_threshold

        host_query = \
            "GET hosts\n" \
            "Stats: state >= 0\n" \
            "Stats: state > 0\n" \
            "Stats: scheduled_downtime_depth = 0\n" \
            "StatsAnd: 2\n" \
            "Stats: state > 0\n" \
            "Stats: scheduled_downtime_depth = 0\n" \
            "Stats: acknowledged = 0\n" \
            "StatsAnd: 3\n" \
            "Stats: host_staleness >= %s\n" % configured_staleness_threshold + \
            "Stats: host_scheduled_downtime_depth = 0\n" \
            "StatsAnd: 2\n" \
            + extra_filter_headers

        service_query = \
            "GET services\n" \
            "Stats: state >= 0\n" \
            "Stats: state > 0\n" \
            "Stats: scheduled_downtime_depth = 0\n" \
            "Stats: host_scheduled_downtime_depth = 0\n" \
            "Stats: host_state = 0\n" \
            "StatsAnd: 4\n" \
            "Stats: state > 0\n" \
            "Stats: scheduled_downtime_depth = 0\n" \
            "Stats: host_scheduled_downtime_depth = 0\n" \
            "Stats: acknowledged = 0\n" \
            "Stats: host_state = 0\n" \
            "StatsAnd: 5\n" \
            "Stats: service_staleness >= %s\n" % configured_staleness_threshold + \
            "Stats: host_scheduled_downtime_depth = 0\n" \
            "Stats: service_scheduled_downtime_depth = 0\n" \
            "StatsAnd: 3\n" \
            + extra_filter_headers

        # In case the user is not allowed to see unrelated events
        ec_filters = ""
        if not config.user.may("mkeventd.seeall") and not config.user.may("mkeventd.seeunrelated"):
            ec_filters = "Filter: event_contact_groups != \n" \
                       + "Filter: host_name != \n" \
                       + "Or: 2\n"

        event_query = (
            # "Events" column
            "GET eventconsoleevents\n"
            "Stats: event_phase = open\n"
            "Stats: event_phase = ack\n"
            "StatsOr: 2\n"
            # "Problems" column
            "Stats: event_phase = open\n"
            "Stats: event_phase = ack\n"
            "StatsOr: 2\n"
            "Stats: event_state != 0\n"
            "StatsAnd: 2\n"
            # "Unhandled" column
            "Stats: event_phase = open\n"
            "Stats: event_state != 0\n"
            "Stats: event_host_in_downtime != 1\n"
            "StatsAnd: 3\n"
            + ec_filters
        )

        try:
            hstdata = sites.live().query_summed_stats(host_query)
            svcdata = sites.live().query_summed_stats(service_query)

            notdata = notifications.load_failed_notifications(
                            after=notifications.acknowledged_time(),
                            stat_only=True,
                            extra_headers=extra_filter_headers)


            if config.user.may("mkeventd.see_in_tactical_overview"):
                try:
                    sites.live().set_auth_domain("ec")
                    event_data = sites.live().query_summed_stats(event_query)
                except livestatus.MKLivestatusNotFoundError:
                    event_data = [0, 0, 0]
                finally:
                    sites.live().set_auth_domain("read")
            else:
                    event_data = [0, 0, 0]

        except livestatus.MKLivestatusNotFoundError:
            return None, None, None, None

        return hstdata, svcdata, notdata, event_data


    @classmethod
    def allowed_roles(cls):
        return [ "user", "admin", "guest" ]


    def styles(self):
        return """
table.tacticaloverview {
   border-collapse: separate;
   width: %dpx;
   margin-top: -7px;
}
table.tacticaloverview th {
    font-size: 8pt;
    line-height: 7pt;
    text-align: left;
    color: #123a4a;
    font-weight: normal;
    padding: 0;
    padding-top: 2px;
    vertical-align: bottom;
}
table.tacticaloverview td {
    text-align: right;
    background-color: #6da1b8;
    padding: 0px;
    height: 14px;
}
table.tacticaloverview td.prob {
    box-shadow: 0px 0px 4px #ffd000;
}
table.tacticaloverview td.col3 {
    width:33%%;
}
table.tacticaloverview td.col4 {
    width:25%%;
}
table.tacticaloverview a { display: block; margin-right: 2px; }
div.tacticalalert {
    font-size: 9pt;
    line-height: 25px;
    height: 25px;
    text-align: center;
    background-color: #ff5500;
    box-shadow: 0px 0px 4px #ffd000;
}
div.spacertop {
    padding-top: 5px;
}
#snapin_tactical_overview img {
    width: 15px;
    height: auto;
    position: relative;
    top: -1px;
}

""" % snapin_width
