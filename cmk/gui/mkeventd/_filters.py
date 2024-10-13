#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from functools import partial

from cmk.gui import query_filters
from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _l
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Row, Rows, VisualContext
from cmk.gui.utils.autocompleter_config import AutocompleterConfig, GroupAutocompleterConfig
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.visuals.filter import (
    AjaxDropdownFilter,
    CheckboxRowFilter,
    Filter,
    FilterGroupCombo,
    FilterNumberRange,
    FilterOption,
    FilterRegistry,
    FilterTime,
    InputTextFilter,
    RegexFilter,
)

from .defines import action_whats, phase_names, syslog_priorities


def register(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        InputTextFilter(
            title=_l("Event ID (exact match)"),
            sort_index=200,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_id", op="="),
        )
    )

    filter_registry.register(
        InputTextFilter(
            title=_l("ID of rule (exact match)"),
            sort_index=200,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_rule_id", op="="),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Message/Text of event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_text", op="~~"),
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
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Contact person (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_contact", op="~~"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Comment to the event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_comment", op="~~"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Host name of original event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(
                ident="event_host_regex", op="~~", column="event_host"
            ),
        )
    )

    filter_registry.register(
        InputTextFilter(
            title=_l("Host name of event (exact match)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_host", op="="),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Original IP address of event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_ipaddress", op="~~"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Owner of event (regex)"),
            sort_index=201,
            info="event",
            query_filter=query_filters.TextQuery(ident="event_owner", op="~~"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("User that performed action (regex)"),
            sort_index=221,
            info="history",
            query_filter=query_filters.TextQuery(ident="history_who", op="~~"),
        )
    )

    filter_registry.register(
        InputTextFilter(
            title=_l("Line number in history logfile (exact match)"),
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
            title=_l("Last occurrance of event"),
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
        )
    )


# TODO: Cleanup as a dropdown visual Filter later on
class _FilterOptEventEffectiveContactgroup(FilterGroupCombo):
    def __init__(self) -> None:
        super().__init__(
            title=_l("Contact group (effective)"),
            sort_index=212,
            group_type="event_effective_contact",
            autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="contact"),
            query_filter=query_filters.OptEventEffectiveContactgroupQuery(),
        )

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {}


# choices = [ (value, "readable"), .. ]
class FilterECServiceLevelRange(Filter):
    def __init__(self, *, ident: str, title: str | LazyString, info: str) -> None:
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
        )

    @staticmethod
    def _options() -> list[tuple[str, str]]:
        choices = sorted(active_config.mkeventd_service_levels[:])
        return [("", "")] + [(str(x[0]), f"{x[0]} - {x[1]}") for x in choices]

    def display(self, value: FilterHTTPVariables) -> None:
        selection = self._options()
        html.open_div(class_="service_level min")
        html.write_text_permissive("From")
        html.dropdown(
            self.lower_bound_varname, selection, deflt=value.get(self.lower_bound_varname, "")
        )
        html.close_div()
        html.open_div(class_="service_level max")
        html.write_text_permissive("To")
        html.dropdown(
            self.upper_bound_varname, selection, deflt=value.get(self.upper_bound_varname, "")
        )
        html.close_div()

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        # NOTE: We need this special case only because our construction of the
        # disjunction is broken. We should really have a Livestatus Query DSL...
        bounds: FilterHTTPVariables = context.get(self.ident, {})
        if not any(v for _k, v in bounds.items()):
            return rows

        lower_bound: str | None = bounds.get(self.lower_bound_varname)
        upper_bound: str | None = bounds.get(self.upper_bound_varname)

        # If user only chooses "From" or "To", use same value from the choosen
        # field for the empty field and update filter form with that value
        if not lower_bound:
            lower_bound = upper_bound
            assert upper_bound is not None
            request.set_var(self.lower_bound_varname, upper_bound)
        if not upper_bound:
            upper_bound = lower_bound
            assert lower_bound is not None
            request.set_var(self.upper_bound_varname, lower_bound)

        filtered_rows: Rows = []
        assert lower_bound is not None
        assert upper_bound is not None
        for row in rows:
            service_level = int(row["%s_custom_variables" % self.info]["EC_SL"])
            if int(lower_bound) <= service_level <= int(upper_bound):
                filtered_rows.append(row)

        return filtered_rows

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not value.get(self.lower_bound_varname) and not value.get(self.upper_bound_varname):
            return ""

        return "Filter: %s_custom_variable_names >= EC_SL\n" % self.info

    def columns_for_filter_table(self, context: VisualContext) -> Iterable[str]:
        if self.ident in context:
            yield "%s_custom_variables" % self.info
