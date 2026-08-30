#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import abc
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import NamedTuple, override

from cmk.gui import sites, visuals
from cmk.gui.dashboard.type_defs import DashletConfig
from cmk.gui.figures import FigureResponseData
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import HTTPVariables, SingleInfos, VisualContext
from cmk.livestatus_client import MKLivestatusNotFoundError
from cmk.web.utils.urls import makeuri_contextless

from ..base import RelativeLayoutConstraints, WidgetSize
from ..figure_dashlet import ABCFigureDashlet


def view_url(url_vars: HTTPVariables) -> str:
    return makeuri_contextless(request, url_vars, filename="view.py")


class HostStats(NamedTuple):
    up: int
    downtime: int
    unreachable: int
    down: int

    def get_parts_data(self, general_url_vars: HTTPVariables) -> list[tuple[str, str, int, str]]:
        return [
            (
                _("Up"),
                "ok",
                self.up,
                view_url(
                    general_url_vars + [("is_host_scheduled_downtime_depth", "0"), ("hst0", "on")]
                ),
            ),
            (
                _("In downtime"),
                "downtime",
                self.downtime,
                view_url(
                    general_url_vars + [("search", "1"), ("is_host_scheduled_downtime_depth", "1")]
                ),
            ),
            (
                _("Unreachable"),
                "unknown",
                self.unreachable,
                view_url(
                    general_url_vars + [("is_host_scheduled_downtime_depth", "0"), ("hst2", "on")]
                ),
            ),
            (
                _("Down"),
                "critical",
                self.down,
                view_url(
                    general_url_vars + [("is_host_scheduled_downtime_depth", "0"), ("hst1", "on")]
                ),
            ),
        ]


class ServiceStats(NamedTuple):
    ok: int
    downtime: int
    host_down: int
    warning: int
    unknown: int
    critical: int

    def get_parts_data(self, general_url_vars: HTTPVariables) -> list[tuple[str, str, int, str]]:
        return [
            (
                _("OK"),
                "ok",
                self.ok,
                view_url(
                    general_url_vars + [("hst0", "on"), ("st0", "on"), ("is_in_downtime", "0")]
                ),
            ),
            (
                _("In downtime"),
                "downtime",
                self.downtime,
                view_url(general_url_vars + [("is_in_downtime", "1")]),
            ),
            (
                _("On down host"),
                "host_down",
                self.host_down,
                view_url(
                    general_url_vars
                    + [
                        ("hst1", "on"),
                        ("hst2", "on"),
                        ("hstp", "on"),
                        ("is_in_downtime", "0"),
                    ]
                ),
            ),
            (
                _("Warning"),
                "warning",
                self.warning,
                view_url(
                    general_url_vars + [("hst0", "on"), ("st1", "on"), ("is_in_downtime", "0")]
                ),
            ),
            (
                _("Unknown"),
                "unknown",
                self.unknown,
                view_url(
                    general_url_vars + [("hst0", "on"), ("st3", "on"), ("is_in_downtime", "0")]
                ),
            ),
            (
                _("Critical"),
                "critical",
                self.critical,
                view_url(
                    general_url_vars + [("hst0", "on"), ("st2", "on"), ("is_in_downtime", "0")]
                ),
            ),
        ]


class EventStats(NamedTuple):
    ok: int
    warning: int
    unknown: int
    critical: int

    def get_parts_data(self, general_url_vars: HTTPVariables) -> list[tuple[str, str, int, str]]:
        return [
            (
                _("Ok"),
                "ok",
                self.ok,
                view_url(general_url_vars + [("event_state_0", "on")]),
            ),
            (
                _("Warning"),
                "warning",
                self.warning,
                view_url(general_url_vars + [("event_state_1", "on")]),
            ),
            (
                _("Unknown"),
                "unknown",
                self.unknown,
                view_url(general_url_vars + [("event_state_3", "on")]),
            ),
            (
                _("Critical"),
                "critical",
                self.critical,
                view_url(general_url_vars + [("event_state_2", "on")]),
            ),
        ]


@dataclass
class StatsPart:
    title: str
    css_class: str
    count: int
    url: str


@dataclass
class StatsElement:
    total: StatsPart
    parts: list[StatsPart]

    def serialize(self) -> dict[str, object]:
        serialized = asdict(self)
        serialized["total"] = asdict(self.total)
        serialized["parts"] = [asdict(p) for p in self.parts]
        return serialized


class StatsDashletConfig(DashletConfig): ...


class HostStatsDashlet(ABCFigureDashlet[StatsDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "hoststats"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Host statistics")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays statistics about host states as a hexagon and a table.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 45

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(
            initial_size=WidgetSize(width=30, height=18), is_resizable=False
        )

    @override
    def infos(self) -> SingleInfos:
        return ["host"]


class ServiceStatsDashlet(ABCFigureDashlet[StatsDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "servicestats"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Service statistics")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays statistics about service states as a hexagon and a table.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 50

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(
            initial_size=WidgetSize(width=30, height=18), is_resizable=False
        )


class EventStatsDashlet(ABCFigureDashlet[StatsDashletConfig]):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "eventstats"

    @classmethod
    @override
    def title(cls) -> str:
        return _("Event statistics")

    @classmethod
    @override
    def description(cls) -> str:
        return _("Displays statistics about events as a hexagon and a table.")

    @classmethod
    @override
    def sort_index(cls) -> int:
        return 55

    @classmethod
    @override
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints(
            initial_size=WidgetSize(width=30, height=18), is_resizable=False
        )

    @override
    def infos(self) -> SingleInfos:
        return ["host", "event"]


class StatsDashletDataGenerator[S: HostStats | ServiceStats | EventStats](abc.ABC):
    @classmethod
    def generate_response_data(
        cls,
        dashlet_spec: StatsDashletConfig,
        context: VisualContext,
        infos: SingleInfos,
    ) -> FigureResponseData:
        return {
            "data": cls._collect_data(dashlet_spec, context, infos).serialize(),
        }

    @classmethod
    @abc.abstractmethod
    def _livestatus_table(cls) -> str:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _view_name(cls) -> str:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _named_stats(cls, stats: Sequence[int]) -> S:
        raise NotImplementedError

    @classmethod
    def _collect_data(
        cls,
        dashlet_spec: StatsDashletConfig,
        context: VisualContext,
        infos: SingleInfos,
    ) -> StatsElement:
        stats = cls._get_stats(dashlet_spec, context, infos)
        general_url_vars = cls._general_url_vars(context)
        parts_data = stats.get_parts_data(general_url_vars)
        return cls._get_stats_element(parts_data, general_url_vars)

    @classmethod
    def _get_stats(
        cls,
        dashlet_spec: StatsDashletConfig,
        context: VisualContext,
        infos: SingleInfos,
    ) -> S:
        filter_headers, only_sites = visuals.get_filter_headers(infos=infos, context=context)
        query = cls._stats_query() + "\n" + filter_headers
        try:
            with sites.only_sites(only_sites):
                result: list[int] = sites.live().query_summed_stats(query)
        except MKLivestatusNotFoundError:
            result = []

        return cls._named_stats(result)

    @classmethod
    def _get_stats_element(
        cls,
        parts_data: list[tuple[str, str, int, str]],
        general_url_vars: HTTPVariables,
    ) -> StatsElement:
        parts = []
        total_count = 0
        for title, css_class, count, url in parts_data:
            parts.append(StatsPart(title=title, css_class=css_class, count=count, url=url))
            total_count += count

        total_part = StatsPart(
            title=_("Total"),
            css_class="",
            count=total_count,
            url=view_url(general_url_vars),
        )

        return StatsElement(parts=parts, total=total_part)

    @classmethod
    @abc.abstractmethod
    def _stats_query(cls) -> str:
        raise NotImplementedError

    @classmethod
    def _general_url_vars(cls, context: VisualContext) -> HTTPVariables:
        return [
            ("view_name", cls._view_name()),
            ("filled_in", "filter"),
            ("search", "1"),
            *visuals.context_to_uri_vars(context),
        ]


class HostStatsDashletDataGenerator(StatsDashletDataGenerator[HostStats]):
    @classmethod
    @override
    def _livestatus_table(cls) -> str:
        return "hosts"

    @classmethod
    @override
    def _view_name(cls) -> str:
        return "searchhost"

    @classmethod
    @override
    def _named_stats(cls, stats: Sequence[int]) -> HostStats:
        if not stats:
            return HostStats(0, 0, 0, 0)
        return HostStats(*stats)

    @classmethod
    @override
    def _stats_query(cls) -> str:
        return (
            "GET hosts\n"
            # Up
            "Stats: state = 0\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "StatsAnd: 2\n"
            # Downtime
            "Stats: scheduled_downtime_depth > 0\n"
            # Unreachable
            "Stats: state = 2\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "StatsAnd: 2\n"
            # Down
            "Stats: state = 1\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "StatsAnd: 2\n"
            # Filter
            "Filter: custom_variable_names < _REALNAME"
        )


class ServiceStatsDashletDataGenerator(StatsDashletDataGenerator[ServiceStats]):
    @classmethod
    @override
    def _livestatus_table(cls) -> str:
        return "services"

    @classmethod
    @override
    def _view_name(cls) -> str:
        return "searchsvc"

    @classmethod
    @override
    def _named_stats(cls, stats: Sequence[int]) -> ServiceStats:
        if not stats:
            return ServiceStats(0, 0, 0, 0, 0, 0)
        return ServiceStats(*stats)

    @classmethod
    @override
    def _stats_query(cls) -> str:
        return (
            "GET services\n"
            # OK
            "Stats: state = 0\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: host_state = 0\n"
            "Stats: host_has_been_checked = 1\n"
            "StatsAnd: 5\n"
            # Downtime
            "Stats: scheduled_downtime_depth > 0\n"
            "Stats: host_scheduled_downtime_depth > 0\n"
            "StatsOr: 2\n"
            # Down host
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: host_state != 0\n"
            "StatsAnd: 3\n"
            # Warning
            "Stats: state = 1\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: host_state = 0\n"
            "Stats: host_has_been_checked = 1\n"
            "StatsAnd: 5\n"
            # Unknown
            "Stats: state = 3\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: host_state = 0\n"
            "Stats: host_has_been_checked = 1\n"
            "StatsAnd: 5\n"
            # Critical
            "Stats: state = 2\n"
            "Stats: scheduled_downtime_depth = 0\n"
            "Stats: host_scheduled_downtime_depth = 0\n"
            "Stats: host_state = 0\n"
            "Stats: host_has_been_checked = 1\n"
            "StatsAnd: 5\n"
            # Filter
            "Filter: host_custom_variable_names < _REALNAME"
        )


class EventStatsDashletDataGenerator(StatsDashletDataGenerator[EventStats]):
    @classmethod
    @override
    def _livestatus_table(cls) -> str:
        return "eventconsoleevents"

    @classmethod
    @override
    def _view_name(cls) -> str:
        return "ec_events"

    @classmethod
    @override
    def _general_url_vars(cls, context: VisualContext) -> HTTPVariables:
        return [
            ("view_name", cls._view_name()),
            ("filled_in", "filter"),
            *visuals.context_to_uri_vars(context),
        ]

    @classmethod
    @override
    def _named_stats(cls, stats: Sequence[int]) -> EventStats:
        if not stats:
            return EventStats(0, 0, 0, 0)
        return EventStats(*stats)

    @classmethod
    @override
    def _stats_query(cls) -> str:
        # In case the user is not allowed to see unrelated events
        ec_filters = ""
        if not user.may("mkeventd.seeall") and not user.may("mkeventd.seeunrelated"):
            ec_filters = "\n".join(  # noqa: FLY002
                [
                    "Filter: event_contact_groups != ",
                    "Filter: host_name != ",
                    "Or: 2",
                ]
            )

        return (
            "GET eventconsoleevents\n"
            "Stats: event_state = 0\n"  # ok
            "Stats: event_state = 1\n"  # warning
            "Stats: event_state = 3\n"  # unknown
            "Stats: event_state = 2" + ec_filters  # critical
        )
