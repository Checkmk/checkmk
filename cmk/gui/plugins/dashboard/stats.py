#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, NamedTuple, Tuple
from dataclasses import asdict, dataclass

from livestatus import MKLivestatusNotFoundError
import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
from cmk.gui.i18n import _
from cmk.gui.globals import request

from cmk.gui.plugins.dashboard import (ABCFigureDashlet, dashlet_registry)
from cmk.gui.utils.urls import makeuri_contextless


class HostStats(NamedTuple):
    up: int
    downtime: int
    unreachable: int
    down: int


class ServiceStats(NamedTuple):
    ok: int
    downtime: int
    host_down: int
    warning: int
    unknown: int
    critical: int


@dataclass
class StatsPart:
    title: str
    css_class: str
    count: int
    url: str


@dataclass
class StatsElement:
    title: str
    total: StatsPart
    parts: List[StatsPart]

    def serialize(self):
        serialized = asdict(self)
        serialized["total"] = asdict(self.total)
        serialized["parts"] = [asdict(p) for p in self.parts]
        return serialized


class StatsDashletDataGenerator:
    @classmethod
    def generate_response_data(cls, properties, context, settings):
        return {
            # TODO: Get the correct dashlet title. This needs to use the general dashlet title
            # calculation. We somehow have to get the title from
            # cmk.gui.dashboard._render_dashlet_title.
            "title": cls._title(),
            "data": cls._collect_data(context, settings["single_infos"]).serialize(),
        }

    @classmethod
    def _title(cls):
        raise NotImplementedError()

    @classmethod
    def _livestatus_table(cls):
        raise NotImplementedError()

    @classmethod
    def _view_name(cls):
        raise NotImplementedError()

    @classmethod
    def _named_stats(cls, stats):
        raise NotImplementedError()

    @classmethod
    def _collect_data(cls, context, single_infos) -> StatsElement:
        stats = cls._get_stats(context)

        general_url_vars = [
            ("view_name", cls._view_name()),
            ("filled_in", "filter"),
            ("search", "1"),
        ]
        general_url_vars.extend(visuals.get_context_uri_vars(context, single_infos))

        parts, total = cls._get_parts_and_total_count(stats, general_url_vars)
        total_part = StatsPart(
            title=_("Total"),
            css_class="",
            count=total,
            url=(makeuri_contextless(request, general_url_vars, filename="view.py")),
        )

        return StatsElement(
            title=cls._title(),
            parts=parts,
            total=total_part,
        )

    @classmethod
    def _get_stats(cls, context):
        filter_headers, only_sites = visuals.get_filter_headers(table=cls._livestatus_table(),
                                                                infos=HostStatsDashlet.infos(),
                                                                context=context)
        query = cls._stats_query() + "\n" + filter_headers
        try:
            if only_sites:
                with sites.only_sites(only_sites):
                    result: List[int] = sites.live().query_row(query)
            else:
                result = sites.live().query_summed_stats(query)
        except MKLivestatusNotFoundError:
            result = []

        return cls._named_stats(result)

    @classmethod
    def _get_parts_and_total_count(cls, stats, general_url_vars) -> Tuple[List[StatsPart], int]:
        raise NotImplementedError()

    @classmethod
    def _stats_query(cls) -> str:
        raise NotImplementedError()


class HostStatsDashletDataGenerator(StatsDashletDataGenerator):
    @classmethod
    def _title(cls):
        return HostStatsDashlet.title()

    @classmethod
    def _livestatus_table(cls):
        return "hosts"

    @classmethod
    def _url_add_vars(cls):
        return {
            "up": [("is_host_scheduled_downtime_depth", "0"), ("hst0", "on")],
            "downtime": [("searchhost&search", "1"), ("is_host_scheduled_downtime_depth", "1")],
            "unreachable": [("is_host_scheduled_downtime_depth", "0"), ("hst2", "on")],
            "down": [("is_host_scheduled_downtime_depth", "0"), ("hst1", "on")],
        }

    @classmethod
    def _view_name(cls):
        return "searchhost"

    @classmethod
    def _named_stats(cls, stats):
        return HostStats(*stats)

    @classmethod
    def _get_parts_and_total_count(cls, stats, general_url_vars) -> Tuple[List[StatsPart], int]:
        parts = []
        total = 0
        url_add_vars = cls._url_add_vars()
        for title, css_class, count, url_vars in [
            (_("Up"), "ok", stats.up, url_add_vars["up"]),
            (_("In downtime"), "downtime", stats.downtime, url_add_vars["downtime"]),
            (_("Unreachable"), "unknown", stats.unreachable, url_add_vars["unreachable"]),
            (_("Down"), "critical", stats.down, url_add_vars["down"]),
        ]:
            url_vars.extend(general_url_vars)
            url = makeuri_contextless(request, url_vars, filename="view.py")
            parts.append(StatsPart(title=title, css_class=css_class, count=count, url=url))
            total += count
        return parts, total

    @classmethod
    def _stats_query(cls) -> str:
        return "\n".join([
            "GET hosts",

            # Up
            "Stats: state = 0",
            "Stats: scheduled_downtime_depth = 0",
            "StatsAnd: 2",

            # Downtime
            "Stats: scheduled_downtime_depth > 0",

            # Unreachable
            "Stats: state = 2",
            "Stats: scheduled_downtime_depth = 0",
            "StatsAnd: 2",

            # Down
            "Stats: state = 1",
            "Stats: scheduled_downtime_depth = 0",
            "StatsAnd: 2",

            # Filter
            "Filter: custom_variable_names < _REALNAME",
        ])


class ServiceStatsDashletDataGenerator(StatsDashletDataGenerator):
    @classmethod
    def _title(cls):
        return ServiceStatsDashlet.title()

    @classmethod
    def _livestatus_table(cls):
        return "services"

    @classmethod
    def _url_add_vars(cls):
        return {
            "ok": [("hst0", "on"), ("st0", "on"), ("is_in_downtime", "0")],
            "downtime": [("is_in_downtime", "1")],
            "host_down": [("hst1", "on"), ("hst2", "on"), ("hstp", "on"), ("is_in_downtime", "0")],
            "warning": [("hst0", "on"), ("st1", "on"), ("is_in_downtime", "0")],
            "unknown": [("hst0", "on"), ("st3", "on"), ("is_in_downtime", "0")],
            "critical": [("hst0", "on"), ("st2", "on"), ("is_in_downtime", "0")],
        }

    @classmethod
    def _view_name(cls):
        return "searchsvc"

    @classmethod
    def _named_stats(cls, stats):
        return ServiceStats(*stats)

    @classmethod
    def _get_parts_and_total_count(cls, stats, general_url_vars) -> Tuple[List[StatsPart], int]:
        parts = []
        total = 0
        url_add_vars = cls._url_add_vars()
        for title, css_class, count, url_vars in [
            (_("OK"), "ok", stats.ok, url_add_vars["ok"]),
            (_("In downtime"), "downtime", stats.downtime, url_add_vars["downtime"]),
            (_("On down host"), "host_down", stats.host_down, url_add_vars["host_down"]),
            (_("Warning"), "warning", stats.warning, url_add_vars["warning"]),
            (_("Unknown"), "unknown", stats.unknown, url_add_vars["unknown"]),
            (_("Critical"), "critical", stats.critical, url_add_vars["critical"]),
        ]:
            url_vars.extend(general_url_vars)
            url = makeuri_contextless(request, url_vars, filename="view.py")
            parts.append(StatsPart(title=title, css_class=css_class, count=count, url=url))
            total += count
        return parts, total

    @classmethod
    def _stats_query(cls) -> str:
        return "\n".join([
            "GET services",

            # OK
            "Stats: state = 0",
            "Stats: scheduled_downtime_depth = 0",
            "Stats: host_scheduled_downtime_depth = 0",
            "Stats: host_state = 0",
            "Stats: host_has_been_checked = 1",
            "StatsAnd: 5",

            # Downtime
            "Stats: scheduled_downtime_depth > 0",
            "Stats: host_scheduled_downtime_depth > 0",
            "StatsOr: 2",

            # Down host
            "Stats: scheduled_downtime_depth = 0",
            "Stats: host_scheduled_downtime_depth = 0",
            "Stats: host_state != 0",
            "StatsAnd: 3",

            # Warning
            "Stats: state = 1",
            "Stats: scheduled_downtime_depth = 0",
            "Stats: host_scheduled_downtime_depth = 0",
            "Stats: host_state = 0",
            "Stats: host_has_been_checked = 1",
            "StatsAnd: 5",

            # Unknown
            "Stats: state = 3",
            "Stats: scheduled_downtime_depth = 0",
            "Stats: host_scheduled_downtime_depth = 0",
            "Stats: host_state = 0",
            "Stats: host_has_been_checked = 1",
            "StatsAnd: 5",

            # Critical
            "Stats: state = 2",
            "Stats: scheduled_downtime_depth = 0",
            "Stats: host_scheduled_downtime_depth = 0",
            "Stats: host_state = 0",
            "Stats: host_has_been_checked = 1",
            "StatsAnd: 5",

            # Filter
            "Filter: host_custom_variable_names < _REALNAME",
        ])


@dashlet_registry.register
class HostStatsDashlet(ABCFigureDashlet):
    @classmethod
    def generate_response_data(cls, properties, context, settings):
        return HostStatsDashletDataGenerator.generate_response_data(properties, context, settings)

    @classmethod
    def type_name(cls):
        return "hoststats"

    @classmethod
    def title(cls):
        return _("Host Statistics")

    @classmethod
    def description(cls):
        return _("Displays statistics about host states as globe and a table.")

    @classmethod
    def sort_index(cls):
        return 45

    @classmethod
    def is_resizable(cls):
        return False

    @classmethod
    def initial_size(cls):
        return (30, 18)

    @classmethod
    def infos(cls) -> List[str]:
        return ["host"]

    @classmethod
    def data_generator(cls):
        return HostStatsDashletDataGenerator


@dashlet_registry.register
class ServiceStatsDashlet(ABCFigureDashlet):
    @classmethod
    def generate_response_data(cls, properties, context, settings):
        return ServiceStatsDashletDataGenerator.generate_response_data(
            properties, context, settings)

    @classmethod
    def type_name(cls):
        return "servicestats"

    @classmethod
    def title(cls):
        return _("Service Statistics")

    @classmethod
    def description(cls):
        return _("Displays statistics about service states as globe and a table.")

    @classmethod
    def sort_index(cls):
        return 50

    @classmethod
    def is_resizable(cls):
        return False

    @classmethod
    def initial_size(cls):
        return (30, 18)

    @classmethod
    def data_generator(cls):
        return ServiceStatsDashletDataGenerator
