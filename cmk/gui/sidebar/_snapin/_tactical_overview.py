#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection, Mapping, Sequence
from typing import Literal, NamedTuple

import livestatus

from cmk.ccc.site import SiteId

from cmk.gui import notifications, sites, visuals
from cmk.gui.config import Config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import CascadingDropdown, Checkbox, Dictionary, ListOf, TextInput, ValueSpec

from ._base import CustomizableSidebarSnapin
from ._helpers import link
from ._registry import CustomSnapinParamsConfig, CustomSnapinParamsRowConfig


class ViewURLParams(NamedTuple):
    total: Sequence[tuple[str, str]]
    handled: Sequence[tuple[str, str]]
    unhandled: Sequence[tuple[str, str | int]]
    stale: Sequence[tuple[str, str]] | None


class OverviewRow(NamedTuple):
    what: str
    title: str
    context: Mapping
    stats: Sequence[int] | None
    views: ViewURLParams


def get_context_url_variables(context: VisualContext) -> list[tuple[str, str]]:
    """Returns the URL variables of a context.
    Returns a list of two-element tuples

    Please note: This does not deal with single contexts.
    """
    add_vars: dict[str, str] = {}
    for filter_vars in context.values():
        add_vars.update(filter_vars)
    return list(add_vars.items())


def group_by_state(
    acc: dict[str, list[str]],
    id_and_state: tuple[str, str],
) -> dict[str, list[str]]:
    id_, state = id_and_state
    acc[state].append(id_)
    return acc


class TacticalOverviewSnapin(CustomizableSidebarSnapin):
    @staticmethod
    def type_name() -> str:
        return "tactical_overview"

    @classmethod
    def title(cls) -> str:
        return _("Overview")

    @classmethod
    def has_show_more_items(cls) -> bool:
        return True

    @classmethod
    def description(cls) -> str:
        return _("The total number of hosts and service with and without problems")

    @classmethod
    def refresh_regularly(cls) -> bool:
        return True

    @classmethod
    def vs_parameters(cls) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "rows",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "title",
                                TextInput(
                                    title=_("Title"),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "query",
                                CascadingDropdown(
                                    orientation="horizontal",
                                    title=_("Query"),
                                    label=_("Table") + ": ",
                                    choices=[
                                        (
                                            "hosts",
                                            _("Hosts"),
                                            visuals.VisualFilterList(
                                                info_list=["host"],
                                            ),
                                        ),
                                        (
                                            "services",
                                            _("Services"),
                                            visuals.VisualFilterList(
                                                info_list=["host", "service"],
                                            ),
                                        ),
                                        (
                                            "events",
                                            _("Events"),
                                            visuals.VisualFilterList(
                                                info_list=["host", "event"],
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                    title=_("Rows"),
                    add_label=_("Add new row"),
                    del_label=_("Delete this row"),
                    allow_empty=False,
                ),
            ),
            (
                "show_stale",
                Checkbox(
                    title=_("Show stale hosts and services"),
                    default_value=True,
                ),
            ),
            (
                "show_failed_notifications",
                Checkbox(
                    title=_("Show failed notifications"),
                    default_value=True,
                ),
            ),
            (
                "show_sites_not_connected",
                Checkbox(
                    title=_("Display a message if sites are not connected"),
                    default_value=True,
                ),
            ),
        ]

    @classmethod
    def parameters(cls) -> CustomSnapinParamsConfig:
        return CustomSnapinParamsConfig(
            show_stale=True,
            show_failed_notifications=True,
            show_sites_not_connected=True,
            rows=[
                CustomSnapinParamsRowConfig(query=("hosts", {}), title="Hosts"),
                CustomSnapinParamsRowConfig(query=("services", {}), title="Services"),
                CustomSnapinParamsRowConfig(query=("events", {}), title="Events"),
            ],
        )

    def show(self, config: Config) -> None:
        self._show_rows(config.staleness_threshold, config.mkeventd_enabled)
        self._show_failed_notifications()
        self._show_site_status()

    def _show_rows(self, staleness_threshold: float, mkeventd_enabled: bool) -> None:
        rows = self._get_rows(staleness_threshold)

        if bool([r for r in rows if r.stats is None]):
            html.center(_("No data from any site"))
            return

        html.open_table(class_=["tacticaloverview"], cellspacing="2", cellpadding="0", border="0")

        show_stales = self.parameters().show_stale is not None and user.may(
            "general.see_stales_in_tactical_overview"
        )
        has_stale_objects = bool(
            [r for r in rows if r.what != "events" and r.stats is not None and r.stats[-1]]
        )

        for row in rows:
            if row.stats is None:
                continue

            if row.what == "events":
                amount, problems, unhandled_problems = row.stats
                stales = 0

                # no events open and disabled in local site: don't show events
                if amount == 0 and not mkeventd_enabled:
                    continue
            else:
                amount, problems, unhandled_problems, stales = row.stats

            context_vars = get_context_url_variables(row.context)

            html.open_tr()
            html.th(row.title)
            html.th(_("Problems"), class_="show_more_mode")
            html.th(
                HTMLWriter.render_span(_("Unhandled"), class_="more")
                + HTMLWriter.render_span(_("Unhandled p."), class_="less")
            )
            if show_stales and has_stale_objects:
                html.th(_("Stale"))
            html.close_tr()

            td_class = "col4" if has_stale_objects else "col3"

            html.open_tr()
            url = makeuri_contextless(
                request, [*row.views.total, *context_vars], filename="view.py"
            )
            html.open_td(class_=["total", td_class])
            html.a("%s" % amount, href=url, target="main")
            html.close_td()

            for value, ty in [(problems, "handled"), (unhandled_problems, "unhandled")]:
                url = makeuri_contextless(
                    request,
                    getattr(row.views, ty) + context_vars,
                    filename="view.py",
                )
                html.open_td(
                    class_=[td_class]
                    + ([] if value == 0 else ["states prob"])
                    + ["show_more_mode" if ty == "handled" else "basic"]
                )
                link(str(value), url)
                html.close_td()

            if show_stales and has_stale_objects:
                if row.views.stale:
                    url = makeuri_contextless(
                        request,
                        [*row.views.stale, *context_vars],
                        filename="view.py",
                    )
                    html.open_td(class_=[td_class] + ([] if stales == 0 else ["states prob"]))
                    link(str(stales), url)
                    html.close_td()
                else:
                    html.td(HTMLWriter.render_span("0"))

            html.close_tr()
        html.close_table()

    def _get_rows(self, staleness_threshold: float) -> list[OverviewRow]:
        rows = []
        for row_config in self.parameters().rows:
            what, context = row_config.query

            if what == "events" and not user.may("mkeventd.see_in_tactical_overview"):
                continue

            stats = self._get_stats(what, context, staleness_threshold)

            rows.append(
                OverviewRow(
                    what=what,
                    title=row_config.title,
                    context=context,
                    stats=stats,
                    views=self._row_views(what),
                )
            )

        return rows

    def _row_views(self, what: Literal["hosts", "services", "events"]) -> ViewURLParams:
        if what == "hosts":
            return ViewURLParams(
                total=[
                    ("view_name", "allhosts"),
                ],
                handled=[
                    ("view_name", "hostproblems"),
                ],
                unhandled=[
                    ("view_name", "hostproblems"),
                    ("is_host_acknowledged", 0),
                ],
                stale=[
                    ("view_name", "stale_hosts"),
                ],
            )

        if what == "services":
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
                    ("hst0", "on"),
                ],
            )

        if what == "events":
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

        raise NotImplementedError()

    def _get_stats(
        self,
        what: Literal["hosts", "services", "events"],
        context: VisualContext,
        staleness_threshold: float,
    ) -> Sequence[int] | None:
        query: str | livestatus.Query
        if what == "hosts":
            context_filters, only_sites = visuals.get_filter_headers(
                infos=["host"], context=context
            )

            query = self._get_host_stats_query(staleness_threshold, context_filters)

        elif what == "services":
            context_filters, only_sites = visuals.get_filter_headers(
                infos=["host", "service"], context=context
            )

            query = self._get_service_stats_query(staleness_threshold, context_filters)

        elif what == "events":
            context_filters, only_sites = visuals.get_filter_headers(
                infos=["host", "event"], context=context
            )

            query = self._get_event_stats_query(context_filters)
        else:
            raise NotImplementedError()

        return self._execute_stats_query(
            query,
            auth_domain="ec" if what == "events" else "read",
            only_sites=only_sites,
            deflt=[0, 0, 0] if what == "events" else None,
        )

    def _get_host_stats_query(self, staleness_threshold: float, context_filters: str) -> str:
        return (
            "GET hosts\n"
            # Total
            "Stats: state >= 0\n"
            # Handled problems
            "Stats: state > 0\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "StatsAnd: 2\n"
            # Unhandled problems
            "Stats: state > 0\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: acknowledged = 0\n"
            "StatsAnd: 3\n"
            # Stale
            "Stats: host_staleness >= %s\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "StatsAnd: 2\n"
            "%s"
        ) % (staleness_threshold, context_filters)

    def _get_service_stats_query(self, staleness_threshold: float, context_filters: str) -> str:
        return (
            "GET services\n"
            # Total
            "Stats: state >= 0\n"
            # Handled problems
            "Stats: state > 0\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: host_state = 0\n"
            "StatsAnd: 4\n"
            # Unhandled problems
            "Stats: state > 0\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: acknowledged = 0\n"
            "Stats: host_state = 0\n"
            "StatsAnd: 5\n"
            # Stale
            "Stats: service_staleness >= %s\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: service_scheduled_downtime_depth = 0\n"
            "Stats: host_state = 0\n"
            "StatsAnd: 4\n"
            "%s"
        ) % (staleness_threshold, context_filters)

    def _get_event_stats_query(self, context_filters: str) -> livestatus.Query:
        # In case the user is not allowed to see unrelated events
        ec_filters = ""
        if not user.may("mkeventd.seeall") and not user.may("mkeventd.seeunrelated"):
            ec_filters = "Filter: event_contact_groups != \nFilter: host_name != \nOr: 2\n"

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
            "StatsAnd: 3\n" + ec_filters + context_filters
        )

        # Do not mark the site as dead in case the Event Console is not available.
        return livestatus.Query(
            event_query,
            suppress_exceptions=(
                livestatus.MKLivestatusTableNotFoundError,
                livestatus.MKLivestatusBadGatewayError,
            ),
        )

    def _execute_stats_query(
        self,
        query: str | livestatus.Query,
        auth_domain: str = "read",
        only_sites: list[SiteId] | None = None,
        deflt: Sequence[int] | None = None,
    ) -> Sequence[int] | None:
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

    def _show_failed_notifications(self) -> None:
        if self.parameters().show_failed_notifications is None:
            return

        failed_notifications = notifications.number_of_failed_notifications(
            after=notifications.acknowledged_time()
        )
        if not failed_notifications:
            return

        html.open_div(class_="spacertop")
        html.open_div(class_="tacticalalert")

        confirm_url = makeuri_contextless(request, [], filename="clear_failed_notifications.py")
        html.icon_button(confirm_url, _("Confirm failed notifications"), "delete", target="main")

        view_url = makeuri_contextless(
            request,
            [("view_name", "failed_notifications")],
            filename="view.py",
        )

        html.a(_("%d failed notifications") % failed_notifications, target="main", href=view_url)
        html.close_div()
        html.close_div()

    def _show_site_status(self) -> None:
        if self.parameters().show_sites_not_connected is None:
            return

        site_states = sites.get_grouped_site_states()

        disabled = site_states["disabled"]
        if disabled.site_ids:
            self._create_status_box(disabled.site_ids, "tacticalinfo", disabled.readable)

        error = site_states["error"]
        if error.site_ids:
            self._create_status_box(error.site_ids, "tacticalalert", error.readable)

    def _create_status_box(
        self,
        site_ids: Collection[SiteId],
        css_class: str,
        site_status: str,
    ) -> None:
        html.open_div(class_="spacertop")
        html.open_div(class_=css_class)
        message_template = ungettext("%d site is %s.", "%d sites are %s.", len(site_ids))
        message = message_template % (len(site_ids), site_status)
        tooltip_template = ungettext(
            "Associated hosts, services and events are not included "
            "in the Tactical Overview. The %s site is %s.",
            "Associated hosts, services and events are not included "
            "in the Tactical Overview. The %s sites are %s.",
            len(site_ids),
        )
        tooltip = tooltip_template % (site_status, ", ".join(site_ids))

        if user.may("wato.sites"):
            url = makeuri_contextless(request, [("mode", "sites")], filename="wato.py")
            html.icon_button(url, tooltip, "sites", target="main")
            html.a(message, target="main", href=url)
        else:
            html.icon("sites", tooltip)
            html.write_text_permissive(message)
        html.close_div()
        html.close_div()
