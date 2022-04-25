#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for main module internals and the plugins"""

# TODO: More feature related splitting up would be better

import abc
import re
from itertools import chain
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    get_args,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

from livestatus import SiteId

import cmk.utils.plugin_registry

import cmk.gui.query_filters as query_filters
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.htmllib.context import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import PageMenuEntry
from cmk.gui.site_config import get_site_config
from cmk.gui.type_defs import (
    Choices,
    ColumnName,
    FilterHeader,
    FilterHTTPVariables,
    FilterName,
    Row,
    Rows,
    VisualContext,
)
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import DualListChoice, ValueSpec
from cmk.gui.view_utils import get_labels


class VisualInfo(abc.ABC):
    """Base class for all visual info classes"""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a visual type. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The human readable GUI title"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title_plural(self) -> str:
        """The human readable GUI title for multiple items"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def single_spec(self) -> List[Tuple[str, ValueSpec]]:
        """The key / valuespec pairs (choices) to identify a single row"""
        raise NotImplementedError()

    @property
    def multiple_site_filters(self) -> List[str]:
        """Returns a list of filter identifiers.

        When these filters are set, the site hint will not be added to urls
        which link to views using this datasource, because the resuling view
        should show the objects spread accross the sites"""
        return []

    @property
    def single_site(self) -> bool:
        """When there is one non single site info used by a visual
        don't add the site hint"""
        return True

    @property
    def sort_index(self) -> int:
        """Used for sorting when listing multiple infos. Lower is displayed first"""
        return 30


class VisualInfoRegistry(cmk.utils.plugin_registry.Registry[Type[VisualInfo]]):
    def plugin_name(self, instance):
        return instance().ident

    # At least painter <> info matching extracts the info name from the name of the painter by
    # splitting at first "_" and use the text before it as info name. See
    # cmk.gui.views.infos_needed_by_painter().
    def registration_hook(self, instance):
        ident = instance().ident
        if ident == "aggr_group":
            return  # TODO: Allow this broken thing for the moment
        if "_" in ident:
            raise MKGeneralException("Underscores must not be used in info names: %s" % ident)


visual_info_registry = VisualInfoRegistry()


class VisualType(abc.ABC):
    """Base class for all filters"""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a visual type. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The human readable GUI title"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def ident_attr(self) -> str:
        """The name of the attribute that is used to identify a visual of this type"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def multicontext_links(self) -> bool:
        """Whether or not to show context buttons even if not single infos present"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def plural_title(self) -> str:
        """The plural title to use in the GUI"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def show_url(self) -> str:
        """The URL filename that can be used to show visuals of this type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def add_visual_handler(
        self, target_visual_name: str, add_type: str, context: Dict, parameters: Dict
    ) -> None:
        """The function to handle adding the given visual to the given visual of this type"""
        raise NotImplementedError()

    @abc.abstractmethod
    def page_menu_add_to_entries(self, add_type: str) -> Iterator[PageMenuEntry]:
        """List of visual choices another visual of the given type can be added to"""
        raise NotImplementedError()

    @abc.abstractmethod
    def load_handler(self) -> None:
        """Load all visuals of this type"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def permitted_visuals(self) -> Dict:
        """Get the permitted visuals of this type"""
        raise NotImplementedError()

    @property
    def choices(self) -> Choices:
        return [(k, v["title"]) for k, v in self.permitted_visuals.items()]

    def link_from(self, linking_view, linking_view_rows, visual, context_vars):
        """Dynamically show/hide links to other visuals (e.g. reports, dashboards, views) from views

        This method uses the conditions read from the "link_from" attribute of a given visual to
        decide whether or not the given linking_view should show a link to the given visual.

        The decision can be made based on the given context_vars, linking_view definition and
        linking_view_rows. Currently there is only a small set of conditions implemented here.

        single_infos: Only link when the given list of single_infos match.
        host_labels: Only link when the given host labels match.

        Example: The visual with this definition will only be linked from host detail pages of hosts
        that are Checkmk servers.

        'link_from': {
            'single_infos': ["host"],
            'host_labels': {
                'cmk/check_mk_server': 'yes'
            }
        }
        """
        link_from = visual["link_from"]
        if not link_from:
            return True  # No link from filtering: Always display this.

        single_info_condition = link_from.get("single_infos")
        if single_info_condition and not set(single_info_condition).issubset(
            linking_view.spec["single_infos"]
        ):
            return False  # Not matching required single infos

        # Currently implemented very specific for the cases we need at the moment. Build something
        # more generic once we need it.
        if single_info_condition != ["host"]:
            raise NotImplementedError()

        if not linking_view_rows:
            return False  # Unknown host, no linking

        # In case we have rows of a single host context we only have a single row that holds the
        # host information. In case we have multiple rows, we normally have service rows which
        # all hold the same host information in their host columns.
        row = linking_view_rows[0]

        # Exclude by host labels
        host_labels = get_labels(row, "host")
        for label_group_id, label_value in link_from.get("host_labels", {}).items():
            if host_labels.get(label_group_id) != label_value:
                return False

        return True


class VisualTypeRegistry(cmk.utils.plugin_registry.Registry[Type[VisualType]]):
    def plugin_name(self, instance):
        return instance().ident


visual_type_registry = VisualTypeRegistry()


class Filter(abc.ABC):
    """Base class for all filters"""

    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        htmlvars: List[str],
        link_columns: List[ColumnName],
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = False,
    ) -> None:
        """
        info:          The datasource info this filter needs to work. If this
                       is "service", the filter will also be available in tables
                       showing service information. "host" is available in all
                       service and host views. The log datasource provides both
                       "host" and "service". Look into datasource.py for which
                       datasource provides which information
        htmlvars:      HTML variables this filter uses
        link_columns:  If this filter is used for linking (state "hidden"), then
                       these Livestatus columns are needed to fill the filter with
                       the proper information. In most cases, this is just []. Only
                       a few filters are useful for linking (such as the host_name and
                       service_description filters with exact match)
        """
        self.ident = ident
        self._title = title
        self.sort_index = sort_index
        self.info = info
        self.htmlvars = htmlvars
        self.link_columns = link_columns
        self._description = description
        self.is_show_more = is_show_more

    @property
    def title(self) -> str:
        return str(self._title)

    @property
    def description(self) -> Optional[str]:
        return str(self._description)

    def available(self) -> bool:
        """Some filters can be unavailable due to the configuration
        (e.g. the WATO Folder filter is only available if WATO is enabled."""
        return True

    def visible(self) -> bool:
        """Some filters can be invisible. This is useful to hide filters which have always
        the same value but can not be removed using available() because the value needs
        to be set during runtime.
        A good example is the "site" filter which does not need to be available to the
        user in single site setups."""
        return True

    @abc.abstractmethod
    def display(self, value: FilterHTTPVariables) -> None:
        raise NotImplementedError()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        """Whether this filter needs to load host inventory data"""
        return False

    def validate_value(self, value: FilterHTTPVariables) -> None:
        return

    def columns_for_filter_table(self, context: VisualContext) -> Iterable[str]:
        """Columns needed to perform post-Livestatus filtering"""
        return []

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        """post-Livestatus filtering (e.g. for BI aggregations)"""
        return rows

    def request_vars_from_row(self, row: Row) -> FilterHTTPVariables:
        """return filter request variables built from the given row"""
        return {}

    def infoprefix(self, infoname: str) -> str:
        if self.info == infoname:
            return ""
        return self.info[:-1] + "_"

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        """Hidden filters may contribute to the pages headers of the views"""
        return None

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        return {varname: request.get_str_input_mandatory(varname, "") for varname in self.htmlvars}


def display_filter_radiobuttons(
    *, varname: str, options: List[Tuple[str, str]], default: str, value: FilterHTTPVariables
) -> None:
    pick = value.get(varname, default)
    html.begin_radio_group(horizontal=True)
    for state, text in options:
        html.radiobutton(varname, state, pick == state, text + " &nbsp; ")
    html.end_radio_group()


class FilterOption(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        query_filter: query_filters.SingleOptionQuery,
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        display_filter_radiobuttons(
            varname=self.query_filter.request_vars[0],
            options=self.query_filter.options,
            default=str(self.query_filter.ignore),
            value=value,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        """post-Livestatus filtering (e.g. for BI aggregations)"""
        return self.query_filter.filter_table(context, rows)


RangedTables = Literal[
    "host",
    "service",
    "event",
    "invcmksites",
    "invcmkversions",
    "invdockercontainers",
    "invdockerimages",
    "invinterface",
    "invorainstance",
    "invorapga",
    "invorasga",
    "invoratablespace",
    "invswpac",
]


def get_ranged_table(s: str) -> Optional[RangedTables]:
    for lit in get_args(RangedTables):
        if s == lit:
            return lit
    return None


def recover_pre_2_1_range_filter_request_vars(query: query_filters.NumberRangeQuery):
    """Some range filters used the _to suffix instead of the standard _until.

    Do inverse translation to search for this request vars."""
    request_var_match = ((var, re.sub("_until(_|$)", "_to\\1", var)) for var in query.request_vars)
    return {
        current_var: (
            request.get_str_input_mandatory(current_var, "")
            or request.get_str_input_mandatory(old_var, "")
        )
        for current_var, old_var in request_var_match
    }


class FilterNumberRange(Filter):  # type is int
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: RangedTables,
        query_filter: query_filters.NumberRangeQuery,
        unit: Union[str, LazyString] = "",
        is_show_more: bool = True,
    ) -> None:
        self.query_filter = query_filter
        self.unit = unit
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text(_("From:") + "&nbsp;")
        html.text_input(
            self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), style="width: 80px;"
        )
        if self.unit:
            html.write_text(" %s " % self.unit)

        html.write_text(" &nbsp; " + _("To:") + "&nbsp;")
        html.text_input(
            self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), style="width: 80px;"
        )
        if self.unit:
            html.write_text(" %s " % self.unit)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the request context."""
        return recover_pre_2_1_range_filter_request_vars(self.query_filter)


class FilterTime(Filter):
    """Filter for setting time ranges, e.g. on last_state_change and last_check"""

    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: Literal["comment", "downtime", "event", "history", "host", "log", "service"],
        query_filter: query_filters.TimeQuery,
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[self.query_filter.column],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables):
        html.open_table(class_="filtertime")
        for what, whatname in [("from", _("From")), ("until", _("Until"))]:
            varprefix = self.ident + "_" + what
            html.open_tr()
            html.td("%s:" % whatname)
            html.open_td()
            html.text_input(varprefix, default_value=value.get(varprefix, ""))
            html.close_td()
            html.open_td()
            html.dropdown(
                varprefix + "_range",
                query_filters.time_filter_options(),
                deflt=value.get(varprefix + "_range", "3600"),
            )
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the request context."""
        return recover_pre_2_1_range_filter_request_vars(self.query_filter)


def checkbox_component(htmlvar: str, value: FilterHTTPVariables, label: str):
    html.open_nobr()
    html.checkbox(htmlvar, bool(value.get(htmlvar)), label=label)
    html.close_nobr()


class InputTextFilter(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        query_filter: query_filters.TextQuery,
        show_heading: bool = True,
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=self.query_filter.link_columns,
            description=description,
            is_show_more=is_show_more,
        )
        self._show_heading = show_heading

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.query_filter.request_vars[0], "")
        html.text_input(
            self.htmlvars[0], current_value, self.query_filter.negateable and "neg" or ""
        )

        if self.query_filter.negateable:
            checkbox_component(self.query_filter.request_vars[1], value, _("negate"))

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row[self.query_filter.column]}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        if self._show_heading:
            return value.get(self.query_filter.request_vars[0])
        return None

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


def checkbox_row(
    options: List[Tuple[str, str]], value: FilterHTTPVariables, title: Optional[str] = None
) -> None:
    html.begin_checkbox_group()
    if title:
        html.write_text(title)
    checkbox_default = not any(value.values())
    for var, text in options:
        html.checkbox(var, bool(value.get(var, checkbox_default)), label=text)
    html.end_checkbox_group()


class CheckboxRowFilter(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        query_filter: query_filters.MultipleOptionsQuery,
        is_show_more: bool = False,
    ) -> None:
        super().__init__(
            ident=query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )
        self.query_filter = query_filter

    def display(self, value: FilterHTTPVariables) -> None:
        checkbox_row(self.query_filter.options, value)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


class DualListFilter(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        query_filter: query_filters.MultipleQuery,
        options: Callable[[str], query_filters.Options],
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = True,
    ):
        self.query_filter = query_filter
        self._options = options
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            description=description,
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.open_div(class_="multigroup")
        DualListChoice(choices=self._options(self.info), rows=4, enlarge_active=True).render_input(
            self.query_filter.request_vars[0], self.query_filter.selection(value)
        )

        if self.query_filter.negateable:
            checkbox_component(self.query_filter.request_vars[1], value, _("negate"))
        html.close_div()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)


def filter_cre_heading_info(value: FilterHTTPVariables) -> Optional[str]:
    current_value = value.get("site")
    return get_site_config(SiteId(current_value))["alias"] if current_value else None


class FilterRegistry(cmk.utils.plugin_registry.Registry[Filter]):
    def __init__(self) -> None:
        super().__init__()
        self.htmlvars_to_filter: Dict[str, FilterName] = {}

    def registration_hook(self, instance: Filter) -> None:
        # Know Exceptions, to this rule
        # siteopt is indistinguishable from site with the difference it
        # allows empty string.  This inverse mapping is to reconstruct
        # filters, from crosslinks, and in those we never set siteopt.
        # Because we use test first with may_add_site_hint. We set siteopt
        # over the filter menu, and there we already set the active flag.
        if instance.ident == "siteopt":
            return None

        # host_metrics_hist & svc_metrics_hist. These filters work at the
        # filter_table instant. We actually only need host_metric_hist, because
        # it has "host" info and thus, it is available in host & service infos.
        # However, the filter would only on the host filter menu. The poor
        # reason for duplication, is that as a post-processing filter, we
        # actually need to offer it on both host & service menus in case one of
        # those is a single context. It would be better to have post-processing
        # on a separte filter, as they aren't based on context.
        if instance.ident == "svc_metrics_hist":
            return None

        if any(
            self.htmlvars_to_filter.get(htmlvar, instance.ident) != instance.ident
            for htmlvar in instance.htmlvars
        ):
            # Will explode as soon as any dev tries to reuse htmlvars for different filters
            raise MKGeneralException(
                "Conflicting filter htmlvars: one of %r is already regitered" % instance.htmlvars
            )

        htmlvars_to_filter: Mapping[str, FilterName] = {
            htmlvar: instance.ident for htmlvar in instance.htmlvars
        }
        self.htmlvars_to_filter.update(htmlvars_to_filter)

    def plugin_name(self, instance):
        return instance.ident


filter_registry = FilterRegistry()


def filters_allowed_for_info(info: str) -> Iterator[Tuple[str, Filter]]:
    """Returns a map of filter names and filter objects that are registered for the given info"""
    for fname, filt in filter_registry.items():
        if filt.info is None or info == filt.info:
            yield fname, filt


def filters_allowed_for_infos(info_list: List[str]) -> Dict[str, Filter]:
    """Same as filters_allowed_for_info() but for multiple infos"""
    return dict(chain.from_iterable(map(filters_allowed_for_info, info_list)))


def active_filter_flag(allowed_filters: Set[str], url_vars: Iterator[Tuple[str, str]]) -> str:
    active_filters = {
        filt
        for var, value in url_vars  #
        if (filt := filter_registry.htmlvars_to_filter.get(var)) and filt in allowed_filters
    }
    return ";".join(sorted(active_filters))


def get_only_sites_from_context(context: VisualContext) -> Optional[List[SiteId]]:
    """Gather possible existing "only sites" information from context

    We need to deal with all possible site filters (sites, site and siteopt).

    VisualContext is structured like this:

    {"site": {"site": "sitename"}}
    {"siteopt": {"site": "sitename"}}
    {"sites": {"sites": "sitename|second"}}

    The difference is no fault or "old" data structure. We can have both kind of structures.
    These are the data structure the visuals work with.

    "site" and "sites" are conflicting filters. The new optional filter
    "sites" for many sites filter is only used if the view is configured
    to only this filter.
    """

    if "sites" in context and "site" not in context:
        only_sites = context["sites"]["sites"]
        only_sites_list = [SiteId(site) for site in only_sites.strip().split("|") if site]
        return only_sites_list if only_sites_list else None

    for var in ["site", "siteopt"]:
        if site_name := context.get(var, {}).get("site"):
            return [SiteId(site_name)]
    return None


# TODO: When this is used by the reporting then *all* filters are active.
# That way the inventory data will always be loaded. When we convert this to the
# visuals principle the we need to optimize this.
def get_livestatus_filter_headers(
    context: VisualContext, filters: Iterable[Filter]
) -> Iterable[FilterHeader]:
    """Prepare Filter headers for Livestatus"""
    for filt in filters:
        try:
            value = context.get(filt.ident, {})
            filt.validate_value(value)
            if header := filt.filter(value):
                yield header
        except MKUserError as e:
            user_errors.add(e)


def collect_filters(info_keys: Container[str]) -> Iterable[Filter]:
    for filter_obj in filter_registry.values():
        if filter_obj.info in info_keys and filter_obj.available():
            yield filter_obj


def livestatus_query_bare_string(
    table: Literal["host", "service"],
    context: VisualContext,
    columns: Iterable[str],
    cache: Optional[Literal["reload"]] = None,
) -> str:
    """Return for the service table filtered by context the given columns.
    Optional cache reload. Return with site info in"""
    infos = {"host": ["host"], "service": ["host", "service"]}.get(table, [])
    filters = collect_filters(infos)
    filterheaders = "".join(get_livestatus_filter_headers(context, filters))

    # optimization: avoid query with unconstrained result
    if not filterheaders and not get_only_sites_from_context(context):
        return ""
    query = ["GET %ss" % table, "Columns: %s" % " ".join(columns), filterheaders]
    if cache:
        query.insert(1, f"Cache: {cache}")

    return "\n".join(query)


def livestatus_query_bare(
    table: Literal["host", "service"],
    context: VisualContext,
    columns: List[str],
    cache: Optional[Literal["reload"]] = None,
) -> List[Dict[str, Any]]:
    """Return for the service table filtered by context the given columns.
    Optional cache reload. Return with site info in"""
    if query := livestatus_query_bare_string(table, context, columns, cache):
        selected_sites = get_only_sites_from_context(context)
        res_columns = ["site"] + columns
        with sites.only_sites(selected_sites), sites.prepend_site():
            return [dict(zip(res_columns, row)) for row in sites.live().query(query)]

    return []
