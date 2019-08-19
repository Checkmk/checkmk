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

from collections import namedtuple

import livestatus

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
import cmk.gui.notifications as notifications
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import Checkbox, ListOf, CascadingDropdown, Dictionary, TextUnicode
# Things imported here are used by pre legacy (pre 1.6) cron plugins)
from . import (  # pylint: disable=unused-import
    CustomizableSidebarSnapin, snapin_registry, write_snapin_exception, snapin_width, link,
)

ViewURLParams = namedtuple("ViewURLParams", ["total", "handled", "unhandled", "stale"])
OverviewRow = namedtuple("OverviewRow", ["what", "title", "context", "stats", "views"])


def get_context_url_variables(context):
    """Returns the URL variables of a context.
    Returns a list of two-element tuples

    Please note: This does not deal with single contexts.
    """
    add_vars = {}
    for filter_vars in context.values():
        add_vars.update(filter_vars)
    return add_vars.items()


@snapin_registry.register
class TacticalOverviewSnapin(CustomizableSidebarSnapin):
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

    @classmethod
    def vs_parameters(cls):
        return [
            ("rows",
             ListOf(
                 Dictionary(
                     elements=[
                         ("title", TextUnicode(
                             title=_("Title"),
                             allow_empty=False,
                         )),
                         ("query",
                          CascadingDropdown(
                              orientation="horizontal",
                              title=_("Query"),
                              label=_("Table") + ": ",
                              choices=[
                                  ("hosts", _("Hosts"), visuals.VisualFilterList(info_list=["host"
                                                                                           ],)),
                                  ("services", _("Services"),
                                   visuals.VisualFilterList(info_list=["host", "service"],)),
                                  ("events", _("Events"),
                                   visuals.VisualFilterList(info_list=["host", "event"],)),
                              ])),
                     ],
                     optional_keys=[],
                 ),
                 title=_("Rows"),
                 add_label=_("Add new row"),
                 del_label=_("Delete this row"),
                 allow_empty=False,
             )),
            ("show_stale", Checkbox(
                title=_("Show stale hosts and services"),
                default_value=True,
            )),
            ("show_failed_notifications",
             Checkbox(
                 title=_("Show failed notifications"),
                 default_value=True,
             )),
        ]

    @classmethod
    def parameters(cls):
        return {
            "show_stale": True,
            "show_failed_notifications": True,
            "rows": [{
                "query": ("hosts", {}),
                "title": u"Hosts"
            }, {
                'query': ('services', {}),
                'title': u'Services'
            }, {
                'query': ('events', {}),
                'title': u'Events'
            }]
        }

    def show(self):
        self._show_rows()
        self._show_failed_notifications()

    def _show_rows(self):
        rows = self._get_rows()

        if bool([r for r in rows if r.stats is None]):
            html.center(_("No data from any site"))
            return

        html.open_table(class_=["content_center", "tacticaloverview"],
                        cellspacing=2,
                        cellpadding=0,
                        border=0)

        show_stales = self.parameters()["show_stale"] and config.user.may(
            "general.see_stales_in_tactical_overview")
        has_stale_objects = bool([r for r in rows if r.what != "events" and r.stats[-1]])

        for row in rows:
            if row.what == "events":
                amount, problems, unhandled_problems = row.stats
                stales = 0

                # no events open and disabled in local site: don't show events
                if amount == 0 and not config.mkeventd_enabled:
                    continue
            else:
                amount, problems, unhandled_problems, stales = row.stats

            context_vars = get_context_url_variables(row.context)

            html.open_tr()
            html.th(row.title)
            html.th(_("Problems"))
            html.th(_("Unhandled"))
            if show_stales and has_stale_objects:
                html.th(_("Stale"))
            html.close_tr()

            td_class = 'col4' if has_stale_objects else 'col3'

            html.open_tr()
            url = html.makeuri_contextless(row.views.total + context_vars, filename="view.py")
            html.open_td(class_=["total", td_class])
            html.a("%s" % amount, href=url, target="main")
            html.close_td()

            for value, ty in [(problems, "handled"), (unhandled_problems, "unhandled")]:
                url = html.makeuri_contextless(getattr(row.views, ty) + context_vars,
                                               filename="view.py")
                html.open_td(class_=[td_class, "states prob" if value != 0 else None])
                link(str(value), url)
                html.close_td()

            if show_stales and has_stale_objects:
                if row.views.stale:
                    url = html.makeuri_contextless(row.views.stale + context_vars,
                                                   filename="view.py")
                    html.open_td(class_=[td_class, "states prob" if stales != 0 else None])
                    link(str(stales), url)
                    html.close_td()
                else:
                    html.td('')

            html.close_tr()
        html.close_table()

    def _get_rows(self):
        rows = []
        for row_config in self.parameters()["rows"]:
            what, context = row_config["query"]

            if what == "events" and not config.user.may("mkeventd.see_in_tactical_overview"):
                continue

            stats = self._get_stats(what, context)

            rows.append(
                OverviewRow(
                    what=what,
                    title=row_config["title"],
                    context=context,
                    stats=stats,
                    views=self._row_views(what),
                ))

        return rows

    def _row_views(self, what):
        if what == "hosts":
            return ViewURLParams(
                total=[
                    ("view_name", "allhosts"),
                ],
                handled=[
                    ("view_name", 'hostproblems'),
                ],
                unhandled=[
                    ("view_name", "hostproblems"),
                    ("is_host_acknowledged", 0),
                ],
                stale=[
                    ("view_name", 'stale_hosts'),
                ],
            )

        elif what == "services":
            return ViewURLParams(
                total=[
                    ("view_name", "allservices"),
                ],
                handled=[
                    ("view_name", "svcproblems"),
                ],
                unhandled=[
                    ("view_name", "svcproblems"),
                    ("is_service_acknowledged", 0),
                ],
                stale=[
                    ("view_name", "uncheckedsvc"),
                ],
            )

        elif what == "events":
            return ViewURLParams(
                total=[
                    ("view_name", "ec_events"),
                ],
                handled=[
                    ("view_name", "ec_events"),
                    ("event_state_1", "on"),
                    ("event_state_2", "on"),
                    ("event_state_3", "on"),
                ],
                unhandled=[
                    ("view_name", "ec_events"),
                    ("event_phase_open", "on"),
                    ("event_state_1", "on"),
                    ("event_state_2", "on"),
                    ("event_state_3", "on"),
                    ("is_event_host_in_downtime", "0"),
                ],
                stale=None,
            )
        else:
            raise NotImplementedError()

    def _get_stats(self, what, context):
        if what == "hosts":
            context_filters, only_sites = visuals.get_filter_headers(table="hosts",
                                                                     infos=["host"],
                                                                     context=context)

            query = self._get_host_stats_query(context_filters)

        elif what == "services":
            context_filters, only_sites = visuals.get_filter_headers(table="services",
                                                                     infos=["host", "service"],
                                                                     context=context)

            query = self._get_service_stats_query(context_filters)

        elif what == "events":
            context_filters, only_sites = visuals.get_filter_headers(table="eventconsoleevents",
                                                                     infos=["host", "event"],
                                                                     context=context)

            query = self._get_event_stats_query(context_filters)
        else:
            raise NotImplementedError()

        return self._execute_stats_query(
            query,
            auth_domain="ec" if what == "events" else "read",
            only_sites=only_sites,
            deflt=[0, 0, 0] if what == "events" else None,
        )

    def _get_host_stats_query(self, context_filters):
        return ("GET hosts\n"
                "Stats: state >= 0\n"
                "Stats: state > 0\n"
                "Stats: scheduled_downtime_depth = 0\n"
                "StatsAnd: 2\n"
                "Stats: state > 0\n"
                "Stats: scheduled_downtime_depth = 0\n"
                "Stats: acknowledged = 0\n"
                "StatsAnd: 3\n"
                "Stats: host_staleness >= %s\n"
                "Stats: host_scheduled_downtime_depth = 0\n"
                "StatsAnd: 2\n"
                "%s") % (config.staleness_threshold, context_filters)

    def _get_service_stats_query(self, context_filters):
        return ("GET services\n"
                "Stats: state >= 0\n"
                "Stats: state > 0\n"
                "Stats: scheduled_downtime_depth = 0\n"
                "Stats: host_scheduled_downtime_depth = 0\n"
                "Stats: host_state = 0\n"
                "StatsAnd: 4\n"
                "Stats: state > 0\n"
                "Stats: scheduled_downtime_depth = 0\n"
                "Stats: host_scheduled_downtime_depth = 0\n"
                "Stats: acknowledged = 0\n"
                "Stats: host_state = 0\n"
                "StatsAnd: 5\n"
                "Stats: service_staleness >= %s\n"
                "Stats: host_scheduled_downtime_depth = 0\n"
                "Stats: service_scheduled_downtime_depth = 0\n"
                "StatsAnd: 3\n"
                "%s") % (config.staleness_threshold, context_filters)

    def _get_event_stats_query(self, context_filters):
        # In case the user is not allowed to see unrelated events
        ec_filters = ""
        if not config.user.may("mkeventd.seeall") and not config.user.may("mkeventd.seeunrelated"):
            ec_filters = ("Filter: event_contact_groups != \n" "Filter: host_name != \n" "Or: 2\n")

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
            "StatsAnd: 3\n" + ec_filters + context_filters)

        return event_query

    def _execute_stats_query(self, query, auth_domain="read", only_sites=None, deflt=None):
        try:
            sites.live().set_auth_domain(auth_domain)
            if only_sites:
                sites.live().set_only_sites(only_sites)

            return sites.live().query_summed_stats(query)
        except livestatus.MKLivestatusNotFoundError:
            return deflt
        finally:
            sites.live().set_only_sites(None)
            sites.live().set_auth_domain("read")

    def _show_failed_notifications(self):
        if not self.parameters()["show_failed_notifications"]:
            return

        failed_notifications = self._get_failed_notification_stats()
        if not failed_notifications:
            return

        html.open_div(class_="spacertop")
        html.open_div(class_="tacticalalert")

        confirm_url = html.makeuri_contextless([], filename="clear_failed_notifications.py")
        html.icon_button(confirm_url, _("Confirm failed notifications"), "delete", target="main")

        view_url = html.makeuri_contextless([("view_name", "failed_notifications")],
                                            filename="view.py")

        html.a(_("%d failed notifications") % failed_notifications, target="main", href=view_url)
        html.close_div()
        html.close_div()

    def _get_failed_notification_stats(self):
        try:
            return notifications.load_failed_notifications(
                after=notifications.acknowledged_time(),
                stat_only=True,
            )[0]
        except livestatus.MKLivestatusNotFoundError:
            return None

    @classmethod
    def allowed_roles(cls):
        return ["user", "admin", "guest"]
