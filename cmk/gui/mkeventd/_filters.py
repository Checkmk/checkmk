#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from functools import partial
from typing import override

from cmk.gui import query_filters
from cmk.gui.config import active_config, RequestCacheConfig
from cmk.gui.i18n import _l
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Row
from cmk.gui.visuals.filter import (
    AjaxDropdownFilter,
    CheckboxRowFilter,
    drilldowns,
    Filter,
    FilterGroup,
    FilterGroupCombo,
    FilterNumberRange,
    FilterOption,
    FilterRegistry,
    FilterTime,
    InputTextFilter,
    RegexFilter,
)
from cmk.gui.visuals.filter.components import Dropdown, FilterComponent
from cmk.web.utils.autocompleter_config import AutocompleterConfig, GroupAutocompleterConfig
from cmk.web.utils.request_cache import RequestCache
from cmk.web.utils.speaklater import LazyString

from .defines import action_whats, phase_names, syslog_priorities


def register(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        InputTextFilter(
            title=_l("Event ID (exact match)"),
            sort_index=200,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_id", op="="),
            drilldown=drilldowns.text("event_id", "event_id"),
        )
    )

    filter_registry.register(
        InputTextFilter(
            title=_l("ID of rule (exact match)"),
            sort_index=200,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_rule_id", op="="),
            drilldown=drilldowns.text("event_rule_id", "event_rule_id"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Message/Text of event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_text",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Application / Syslog-Tag (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_application",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Contact person (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_contact",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Comment to the event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_comment",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Host name of original event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_host_regex",
                op="~~",
                column="event_host",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        InputTextFilter(
            title=_l("Host name of event (exact match)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.EventHostQuery(),
            drilldown=drilldowns.text("event_host", "event_host"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Original IP address of event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_ipaddress",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Owner of event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_owner",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("User that performed action (regex)"),
            sort_index=221,
            info="history",
            query_filter=query_filters.TextQuery(
                ident="history_who",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        InputTextFilter(
            title=_l("Line number in history log file (exact match)"),
            sort_index=222,
            info="history",
            query_filter=query_filters.TextQuery(ident="history_line", op="="),
        )
    )

    filter_registry.register(
        FilterOption(
            title=_l("Host in downtime during event creation"),
            sort_index=223,
            info="event",
            query_filter=query_filters.TristateQuery(
                ident="event_host_in_downtime",
                filter_code=query_filters.column_flag("event_host_in_downtime"),
            ),
            is_show_more=False,
            drilldown=drilldowns.Drilldown(
                columns=["event_host_in_downtime"], variables=_event_host_in_downtime
            ),
        )
    )

    filter_registry.register(
        FilterNumberRange(
            title=_l("Message count"),
            sort_index=205,
            info="event",
            query_filter=query_filters.NumberRangeQuery(ident="event_count"),
        )
    )

    filter_registry.register(
        CheckboxRowFilter(
            title=_l("State classification"),
            sort_index=206,
            info="event",
            query_filter=query_filters.MultipleOptionsQuery(
                ident="event_state",
                options=query_filters.svc_state_min_options("event_state_"),
                livestatus_query=partial(query_filters.options_toggled_filter, "event_state"),
            ),
            drilldown=drilldowns.checked_option("event_state_", "event_state"),
        )
    )

    filter_registry.register(
        CheckboxRowFilter(
            title=_l("Phase"),
            sort_index=207,
            info="event",
            query_filter=query_filters.MultipleOptionsQuery(
                ident="event_phase",
                options=[("event_phase_" + var, title) for var, title in phase_names.items()],
                livestatus_query=partial(query_filters.options_toggled_filter, "event_phase"),
            ),
            drilldown=drilldowns.checked_option("event_phase_", "event_phase"),
        )
    )

    filter_registry.register(
        CheckboxRowFilter(
            title=_l("Syslog Priority"),
            sort_index=209,
            info="event",
            query_filter=query_filters.MultipleOptionsQuery(
                ident="event_priority",
                options=[("event_priority_%d" % e[0], e[1]) for e in syslog_priorities],
                livestatus_query=partial(query_filters.options_toggled_filter, "event_priority"),
            ),
            drilldown=drilldowns.checked_option("event_priority_", "event_priority"),
        )
    )

    filter_registry.register(
        CheckboxRowFilter(
            title=_l("History action type"),
            sort_index=225,
            info="history",
            query_filter=query_filters.MultipleOptionsQuery(
                ident="history_what",
                options=[("history_what_%s" % k, k) for k in action_whats],
                livestatus_query=partial(query_filters.options_toggled_filter, "history_what"),
            ),
            drilldown=drilldowns.checked_option("history_what_", "history_what"),
        )
    )

    filter_registry.register(
        FilterTime(
            title=_l("First occurrence of event"),
            sort_index=220,
            info="event",
            query_filter=query_filters.TimeQuery(ident="event_first"),
        )
    )

    filter_registry.register(
        FilterTime(
            title=_l("Last occurrence of event"),
            sort_index=221,
            info="event",
            query_filter=query_filters.TimeQuery(ident="event_last"),
        )
    )

    filter_registry.register(
        FilterTime(
            title=_l("Time of entry in event history"),
            sort_index=222,
            info="history",
            query_filter=query_filters.TimeQuery(
                ident="history_time",
            ),
        )
    )

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Syslog Facility (exact match)"),
            sort_index=210,
            info="event",
            autocompleter=AutocompleterConfig(ident="syslog_facilities", strict=True),
            query_filter=query_filters.TextQuery(ident="event_facility", op="="),
            drilldown=drilldowns.text("event_facility", "event_facility"),
        )
    )

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Service level at least"),
            sort_index=211,
            info="event",
            autocompleter=AutocompleterConfig(ident="service_levels"),
            query_filter=query_filters.TextQuery(ident="event_sl", op=">="),
        )
    )

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Service level at most"),
            sort_index=211,
            info="event",
            autocompleter=AutocompleterConfig(ident="service_levels"),
            query_filter=query_filters.TextQuery(ident="event_sl_max", op="<=", column="event_sl"),
        )
    )

    filter_registry.register(_FilterOptEventEffectiveContactgroup())

    filter_registry.register(
        FilterECServiceLevelRange(
            ident="svc_service_level",
            title=_l("Service service level"),
            info="service",
        )
    )

    filter_registry.register(
        FilterECServiceLevelRange(
            ident="hst_service_level",
            title=_l("Host service level"),
            info="host",
            group=FilterGroup.HOST_PROPERTIES,
        )
    )


def _event_host_in_downtime(
    row: drilldowns.RowValues, _keys: Sequence[str]
) -> FilterHTTPVariables | None:
    match row.get("event_host_in_downtime"):
        case int(in_downtime):
            return {"is_event_host_in_downtime": "1" if in_downtime else "0"}
        case _:
            return None


def _event_contact_group(
    row: drilldowns.RowValues, _keys: Sequence[str]
) -> FilterHTTPVariables | None:
    column = (
        "event_contact_groups"
        if row.get("event_contact_groups_precedence") == "rule"
        else "host_contact_groups"
    )
    match row.get(column):
        case [str(group)]:
            return {"optevent_effective_contact_group": group}
        case _:
            return None


def _service_level(ident: str, info: str) -> drilldowns.Drilldown:
    column = f"{info}_custom_variables"

    def variables(row: drilldowns.RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        if (level := drilldowns.mapping_value(row, column, "EC_SL")) is None:
            return None
        return {f"{ident}_lower": level, f"{ident}_upper": level}

    return drilldowns.Drilldown(columns=[column], variables=variables)


# TODO: Cleanup as a dropdown visual Filter later on
class _FilterOptEventEffectiveContactgroup(FilterGroupCombo):
    def __init__(self) -> None:
        super().__init__(
            title=_l("Contact group (effective)"),
            sort_index=212,
            group_type="event_effective_contact",
            autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="contact"),
            query_filter=query_filters.OptEventEffectiveContactgroupQuery(),
            drilldown=drilldowns.Drilldown(
                columns=[
                    "event_contact_groups",
                    "event_contact_groups_precedence",
                    "host_contact_groups",
                ],
                variables=_event_contact_group,
            ),
        )

    @override
    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {}


# choices = [ (value, "readable"), .. ]
class FilterECServiceLevelRange(Filter):
    def __init__(
        self, *, ident: str, title: str | LazyString, info: str, group: FilterGroup | None = None
    ) -> None:
        self.lower_bound_varname = "%s_lower" % ident
        self.upper_bound_varname = "%s_upper" % ident
        super().__init__(
            ident=ident,
            title=title,
            sort_index=310,
            info=info,
            htmlvars=[
                self.lower_bound_varname,
                self.upper_bound_varname,
            ],
            link_columns=[],
            is_show_more=True,
            group=group,
            drilldown=_service_level(ident, info),
        )

    @staticmethod
    def _options() -> list[tuple[str, str]]:
        choices = sorted(active_config.mkeventd_service_levels[:])
        return [("", "")] + [(str(x[0]), f"{x[0]} - {x[1]}") for x in choices]

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        choices = dict(self._options())
        yield Dropdown(
            id=self.lower_bound_varname,
            choices=choices,
            label="From",
        )
        yield Dropdown(
            id=self.upper_bound_varname,
            choices=choices,
            label="To",
        )

    def _parse_bounds(self, value: FilterHTTPVariables) -> tuple[int, int] | None:
        """A single given bound stands for exactly that level; invalid input disables the filter."""
        raw_lower = value.get(self.lower_bound_varname, "")
        raw_upper = value.get(self.upper_bound_varname, "")
        if not raw_lower and not raw_upper:
            return None
        try:
            return int(raw_lower or raw_upper), int(raw_upper or raw_lower)
        except ValueError:
            return None

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        bounds = self._parse_bounds(value)
        if bounds is None:
            return ""
        lower_bound, upper_bound = bounds

        # Custom variable values are compared as strings by Livestatus, so a numeric range
        # cannot be expressed directly. The bounds are chosen from the configured service
        # levels, so we match each configured level within the range exactly instead.
        levels_in_range = [
            str(level)
            for level, _name in active_config.mkeventd_service_levels
            if lower_bound <= level <= upper_bound
        ]
        if not levels_in_range:
            return "Or: 0\n"

        return query_filters.lq_logic(
            f"Filter: {self.info}_custom_variables = EC_SL", levels_in_range, "Or"
        )
