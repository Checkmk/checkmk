#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, NamedTuple, Dict, Literal, Tuple, Optional
from dataclasses import dataclass, asdict
from livestatus import SiteId, LivestatusResponse, OnlySites
from cmk.gui.valuespec import Timerange, Integer

from cmk.utils.type_defs import HostName

import cmk.gui.sites as sites
from cmk.gui.globals import html, request
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.i18n import _
from cmk.gui.valuespec import Dictionary
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry, ABCFigureDashlet, ABCDataGenerator
from cmk.gui.plugins.dashboard.site_overview import (
    ABCElement,)


@dataclass
class AlertElement(ABCElement):
    """Renders a regularly available sitae"""
    object_type: Literal["host", "service"]
    link: str
    num_ok: int
    num_warn: int
    num_crit: int
    num_unknown: int
    num_problems: int

    def serialize(self):
        serialized = asdict(self)
        serialized["type"] = "alert_element"
        return serialized


class AlertStats(NamedTuple):
    num_ok: int
    num_warn: int
    num_crit: int
    num_unknown: int
    num_problems: int


class AlertStatisticsDashletDataGenerator(ABCDataGenerator):
    def vs_parameters(self) -> Dictionary:
        return Dictionary(
            title=_("Properties"),
            render="form",
            optional_keys=["limit_objects"],
            elements=[
                ("time_range", Timerange(
                    title=_("Time range"),
                    default_value=90000,
                )),
                ("limit_objects", Integer(
                    title=_("Limit objects"),
                    default_value=100,
                    minvalue=1,
                )),
            ],
        )

    @classmethod
    def generate_response_data(cls, properties, context, settings):
        site_id = context.get("site", {}).get("site")

        time_range, range_title = Timerange().compute_range(properties["time_range"])

        elements = cls._collect_data(
            only_sites=[SiteId(site_id)] if site_id else None,
            since=time_range[0],
            limit=properties.get("limit_objects"),
        )

        return {
            "render_mode": "alert_statistics",
            # TODO: Get the correct dashlet title. This needs to use the general dashlet title
            # calculation. We somehow have to get the title from
            # cmk.gui.dashboard._render_dashlet_title.
            "title": _("Top alerters - %s") % range_title,
            "plot_definitions": [],
            "data": [e.serialize() for e in elements],
            "upper_bound": max([100] + [e.num_problems + 1 for e in elements]),
        }

    @classmethod
    def _collect_data(cls, only_sites: OnlySites, since: int,
                      limit: Optional[int]) -> List[AlertElement]:
        elements: List[AlertElement] = []

        entries = sorted(cls._get_alert_stats(only_sites, since).items(),
                         key=lambda h: h[1].num_problems,
                         reverse=True)
        if limit is not None:
            entries = entries[:limit]

        for (site_id, host_name, service_description), alert_stats in entries:

            if service_description is not None:
                link = makeuri_contextless(
                    request,
                    [
                        ("host", host_name),
                        ("service", service_description),
                        ("site", str(site_id)),
                        ("view_name", "svcevents"),
                        ("filled_in", "filter"),
                        ("logtime_from", "1"),
                        ("logtime_from_range", "86400"),
                        ("_show_filter_form", "0"),
                    ],
                    filename="view.py",
                )
            else:
                link = makeuri_contextless(
                    request,
                    [
                        ("host", host_name),
                        ("site", str(site_id)),
                        ("view_name", "hostsvcevents"),
                        ("filled_in", "filter"),
                        ("logtime_from", "1"),
                        ("logtime_from_range", "86400"),
                        ("_show_filter_form", "0"),
                    ],
                    filename="view.py",
                )

            elements.append(
                AlertElement(
                    object_type="host" if service_description is None else "service",
                    title=host_name,
                    link=link,
                    num_ok=alert_stats.num_ok,
                    num_warn=alert_stats.num_warn,
                    num_crit=alert_stats.num_crit,
                    num_unknown=alert_stats.num_unknown,
                    num_problems=alert_stats.num_problems,
                    tooltip=cls._get_tooltip(host_name, service_description, alert_stats),
                ))

        return elements

    @classmethod
    def _get_tooltip(cls, host_name: HostName, service_description: str,
                     alert_stats: AlertStats) -> str:
        with html.plugged():
            if service_description:
                html.h3(f"{host_name} - {service_description}")
            else:
                html.h3(host_name)

            html.open_table()
            for title, count in [
                (_("Problems in total"), alert_stats.num_problems),
                (_("Critical"), alert_stats.num_crit),
                (_("Unknown"), alert_stats.num_unknown),
                (_("Warning"), alert_stats.num_warn),
            ]:
                html.open_tr()
                html.td(str(count), class_="count")
                html.td(title, class_="title")
                html.close_tr()

            html.close_table()
            return html.drain()

    @classmethod
    def _get_alert_stats(cls, only_sites: OnlySites,
                         since: int) -> Dict[Tuple[SiteId, HostName, str], AlertStats]:
        try:
            sites.live().set_only_sites(only_sites)
            sites.live().set_prepend_site(True)
            rows: LivestatusResponse = sites.live().query(cls._alert_stats_query(since))
        finally:
            sites.live().set_prepend_site(False)
            sites.live().set_only_sites(None)

        return {(SiteId(row[0]), HostName(row[1]), row[2]): AlertStats(*row[3:]) for row in rows}

    @classmethod
    def _alert_stats_query(cls, since: int) -> str:
        return "\n".join([
            "GET log",
            "Columns: host_name service_description",
            "Filter: class = 1",
            "Stats: state = 0",
            "Stats: state = 1",
            "Stats: state = 2",
            "Stats: state = 3",
            "Stats: state != 0",
            "Filter: log_time >= %d" % since,
        ])


@page_registry.register_page("ajax_alert_statistics_dashlet_data")
class AjaxAlertStatisticsDashletData(AjaxPage):
    def page(self):
        return AlertStatisticsDashletDataGenerator().generate_response_from_request()


@dashlet_registry.register
class AlertStatisticsDashlet(ABCFigureDashlet):
    @classmethod
    def type_name(cls):
        return "alert_statistics"

    @classmethod
    def title(cls):
        return _("Top alerters")

    @classmethod
    def description(cls):
        return _("Displays hosts and services producing the most notifications")

    @classmethod
    def data_generator(cls):
        return AlertStatisticsDashletDataGenerator()

    @classmethod
    def single_infos(cls):
        return []
