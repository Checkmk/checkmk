#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import itertools
import json
import re
import traceback
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, unique
from typing import Final, Literal, TypeVar

import livestatus

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKException, MKGeneralException

from cmk.utils.redis import get_redis_client

import cmk.gui.utils
from cmk.gui import sites
from cmk.gui.config import active_config, Config
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import get_main_menu_items_prefixed_by_segment, main_menu_registry
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.type_defs import (
    HTTPVariables,
    Icon,
    Row,
    Rows,
    SearchQuery,
    SearchResult,
    SearchResultsByTopic,
    ViewName,
)
from cmk.gui.utils.labels import (
    encode_labels_for_livestatus,
    filter_http_vars_for_simple_label_group,
    Label,
    label_help_text,
    Labels,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.urls import makeuri
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.search import IndexNotFoundException, IndexSearcher, PermissionsHandler

from ._base import PageHandlers, SidebarSnapin

#   .--Quicksearch---------------------------------------------------------.
#   |         ___        _      _                            _             |
#   |        / _ \ _   _(_) ___| | _____  ___  __ _ _ __ ___| |__          |
#   |       | | | | | | | |/ __| |/ / __|/ _ \/ _` | '__/ __| '_ \         |
#   |       | |_| | |_| | | (__|   <\__ \  __/ (_| | | | (__| | | |        |
#   |        \__\_\\__,_|_|\___|_|\_\___/\___|\__,_|_|  \___|_| |_|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Quicksearch basics                                                   |
#   '----------------------------------------------------------------------'

LivestatusTable = str
LivestatusColumn = str
LivestatusFilterHeaders = str
UsedFilters = dict[str, list[str]]
Matches = tuple[str, HTTPVariables] | None


@dataclass
class LivestatusResult:
    text_tokens: list[tuple[str, str]]
    url: str
    row: Row
    display_text: str
    context: str = ""


@unique
class FilterBehaviour(Enum):
    # Continue search
    CONTINUE = "continue"
    # Search finished: Only show results of this filter
    FINISHED_DISTINCT = "finished_distinct"
    # Search finished: Also show all results of previous filters
    FINISHED = "finished"


def _to_regex(s):
    """Ensures the provided search string is a regex, does some basic conversion
    and then tries to verify it is a regex"""
    s = s.replace("*", ".*")
    validate_regex(s, varname=None)

    return s


class TooManyRowsError(MKException):
    pass


class IncorrectLabelInputError(MKUserError):
    pass


def _build_url(url_params: HTTPVariables) -> str:
    new_params = url_params[:]
    return makeuri(request, new_params, delvars=["q"], filename="view.py")


class ABCQuicksearchConductor(abc.ABC):
    def __init__(self, used_filters: UsedFilters, filter_behaviour: FilterBehaviour) -> None:
        # used_filters:     {u'h': [u'heute'], u's': [u'Check_MK']}
        self._used_filters = used_filters
        self._filter_behaviour = filter_behaviour

    @property
    def filter_behaviour(self) -> FilterBehaviour:
        return self._filter_behaviour

    @abc.abstractmethod
    def do_query(self) -> None:
        """Execute the lookup of the data using the given query"""
        raise NotImplementedError()

    @abc.abstractmethod
    def num_rows(self) -> int:
        """Returns the number of matching results"""
        raise NotImplementedError()

    @abc.abstractmethod
    def remove_rows_from_end(self, num: int) -> None:
        """Strips off some rows from the end of the results"""
        raise NotImplementedError()

    @abc.abstractmethod
    def row_limit_exceeded(self) -> bool:
        """Whether or not the results exceeded the config.quicksearch_dropdown_limit"""
        raise NotImplementedError()

    @abc.abstractmethod
    def get_search_url_params(self) -> HTTPVariables:
        """Returns the HTTP variables to link to to show the results on a content page"""
        raise NotImplementedError()

    @abc.abstractmethod
    def create_results(self) -> list[SearchResult]:
        """Returns the results for the given query"""
        raise NotImplementedError()

    def get_match_topic(self) -> str:
        if len(self._used_filters.keys()) > 1:
            return "Multi-Filter"
        shortname = list(self._used_filters.keys())[0]
        return self._get_plugin_with_shortname(shortname).get_match_topic()

    def _get_plugin_with_shortname(self, name: str) -> "ABCMatchPlugin":
        try:
            return match_plugin_registry[name]
        except KeyError:
            raise NotImplementedError()


class BasicPluginQuicksearchConductor(ABCQuicksearchConductor):
    """Passes queries through to a non livestatus plug-in

    There is no aggregation done by this conductor. It deals with a single search plug-in.
    """

    def __init__(self, used_filters: UsedFilters, filter_behaviour: FilterBehaviour) -> None:
        super().__init__(used_filters, filter_behaviour)
        self._results: list[SearchResult] = []

    def do_query(self) -> None:
        """Execute the lookup of the data using the given query"""
        assert len(self._used_filters) == 1, "Only supporting single filter lookups"
        name, queries = list(self._used_filters.items())[0]

        plugin = self._get_plugin_with_shortname(name)
        assert isinstance(plugin, ABCBasicMatchPlugin)

        assert len(queries) == 1, "Only supporting single query lookups"
        self._results = plugin.get_results(queries[0])

    def num_rows(self) -> int:
        """Returns the number of matching results"""
        return len(self._results)

    def remove_rows_from_end(self, num: int) -> None:
        """Strips off some rows from the end of the results"""
        self._results = self._results[:-num]

    def row_limit_exceeded(self) -> bool:
        """Whether or not the results exceeded the config.quicksearch_dropdown_limit"""
        return len(self._results) > active_config.quicksearch_dropdown_limit

    def get_search_url_params(self) -> HTTPVariables:
        """Returns the HTTP variables to link to to show the results on a content page"""
        raise NotImplementedError()  # TODO: Implement this

    def create_results(self) -> list[SearchResult]:
        return self._results[: active_config.quicksearch_dropdown_limit]


class LivestatusQuicksearchConductor(ABCQuicksearchConductor):
    """Executes the livestatus search plug-ins and collects results

    It cares about aggregating the queries of different filters together to a single livestatus
    query (see _generate_livestatus_command) in case they are given with "used_filters".

    Based on all the given plug-in selection expressions it decides which one to use. There is only a
    single table selected and queried! This means that incompatible search plug-ins in a single
    search query (e.g. service group and host name) are not both executed.

    Based on the used_filters it selects a livestatus table to query. Then it constructs the
    livestatus query with the help of all search plug-ins that support searching the previously
    selected table.
    """

    def __init__(self, used_filters: UsedFilters, filter_behaviour: FilterBehaviour) -> None:
        super().__init__(used_filters, filter_behaviour)

        self._livestatus_table: str | None = None
        self._livestatus_command: str = ""  # Computed livestatus query
        self._rows: Rows = []  # Raw data from livestatus
        self._queried_livestatus_columns: list[str] = []

    @property
    def livestatus_table(self) -> str:
        if self._livestatus_table is None:
            raise RuntimeError("Livestatus table not computed yet")
        return self._livestatus_table

    def do_query(self) -> None:
        self._execute_livestatus_command()

    def num_rows(self) -> int:
        return len(self._rows)

    def remove_rows_from_end(self, num: int) -> None:
        self._rows = self._rows[:-num]

    def row_limit_exceeded(self) -> bool:
        return self._too_much_rows

    def _execute_livestatus_command(self) -> None:
        self._rows = []
        self._too_much_rows = False

        self._generate_livestatus_command()

        if not self._livestatus_command:
            return

        sites.live().set_prepend_site(True)
        results = sites.live().query(self._livestatus_command)
        sites.live().set_prepend_site(False)

        # Invalid livestatus response, missing headers..
        if not results:
            return

        headers = ["site"] + self._queried_livestatus_columns
        self._rows = [dict(zip(headers, x)) for x in results]

        limit = active_config.quicksearch_dropdown_limit
        if len(self._rows) > limit:
            self._too_much_rows = True
            self._rows.pop()  # Remove limit+1nth element

    def _generate_livestatus_command(self) -> None:
        self._determine_livestatus_table()
        columns_to_query = set(self._get_livestatus_default_columns())
        livestatus_filter_domains: dict[str, list[str]] = {}

        self._used_search_plugins = self._get_used_search_plugins()

        for plugin in self._used_search_plugins:
            columns_to_query.update(set(plugin.get_livestatus_columns(self.livestatus_table)))
            name = plugin.name
            livestatus_filter_domains.setdefault(name, [])
            livestatus_filter_domains[name].append(
                plugin.get_livestatus_filters(self.livestatus_table, self._used_filters)
            )

        # Combine filters of same domain (h/s/sg/hg/..)
        livestatus_filters = []
        for entries in livestatus_filter_domains.values():
            livestatus_filters.append("\n".join(entries))
            if len(entries) > 1:
                livestatus_filters[-1] += "\nOr: %d" % len(entries)

        if len(livestatus_filters) > 1:
            livestatus_filters.append("And: %d" % len(livestatus_filters))

        self._queried_livestatus_columns = list(columns_to_query)
        self._livestatus_command = "GET {}\nColumns: {}\n{}\n".format(
            self.livestatus_table,
            " ".join(self._queried_livestatus_columns),
            "\n".join(livestatus_filters),
        )

        # Limit number of results
        limit = active_config.quicksearch_dropdown_limit
        self._livestatus_command += "Cache: reload\nLimit: %d\nColumnHeaders: off" % (limit + 1)

    def _get_used_search_plugins(self) -> list["ABCLivestatusMatchPlugin"]:
        return [
            plugin
            for plugin in match_plugin_registry.get_livestatus_match_plugins()
            if plugin.is_used_for_table(self.livestatus_table, self._used_filters)
        ]

    def _determine_livestatus_table(self) -> None:
        """Returns the livestatus table fitting the given filters

        Available tables
        hosts / services / hostgroups / servicegroups

        {table} -> {is_included_in_table}
        Host groups -> Hosts -> Services
        Service groups -> Services
        """

        preferred_tables = []
        for shortname in self._used_filters.keys():
            plugin = self._get_plugin_with_shortname(shortname)
            assert isinstance(plugin, ABCLivestatusMatchPlugin)
            preferred_tables.append(plugin.get_preferred_livestatus_table())

        table_to_query = ""
        if "services" in preferred_tables:
            table_to_query = "services"
        elif "servicegroups" in preferred_tables:
            if "hosts" in preferred_tables or "hostgroups" in preferred_tables:
                table_to_query = "services"
            else:
                table_to_query = "servicegroups"
        elif "hosts" in preferred_tables:
            table_to_query = "hosts"
        elif "hostgroups" in preferred_tables:
            table_to_query = "hostgroups"

        self._livestatus_table = table_to_query

    def _get_livestatus_default_columns(self) -> list[str]:
        return {
            "services": ["description", "host_name"],
            "hosts": ["name"],
            "hostgroups": ["name"],
            "servicegroups": ["name"],
        }.get(self.livestatus_table, [])  # TODO: Is the default correct/necessary?

    def get_search_url_params(self) -> HTTPVariables:
        exact_match = self.num_rows() == 1
        target_view = self._get_target_view(exact_match=exact_match)

        url_params: HTTPVariables = [
            ("view_name", target_view),
            ("filled_in", "filter"),
            ("_show_filter_form", "0"),
        ]

        for plugin in self._used_search_plugins:
            match_info = plugin.get_matches(
                target_view,
                self._rows[0] if exact_match else None,
                self.livestatus_table,
                self._used_filters,
                self._rows,
            )
            if not match_info:
                continue
            _text, url_filters = match_info
            url_params.extend(url_filters)

        return url_params

    def create_results(self) -> list[SearchResult]:
        elements: list[LivestatusResult] = []

        if not self._rows:
            return []

        target_view = self._get_target_view()

        # Feed each row to the filters and let them add additional text/url infos
        for row in self._rows:
            text_tokens: list[tuple[str, str]] = []
            url_params: HTTPVariables = []
            skip_site = False
            for name in self._used_filters:
                plugin = self._get_plugin_with_shortname(name)
                assert isinstance(plugin, ABCLivestatusMatchPlugin)

                if plugin.is_group_match():
                    skip_site = True

                match_info = plugin.get_matches(
                    target_view, row, self.livestatus_table, self._used_filters, []
                )
                if not match_info:
                    continue
                text, url_filters = match_info
                url_params.extend(url_filters)
                text_tokens.append((plugin.name, text))

            url_tokens: HTTPVariables = []
            url_tokens.append(("view_name", target_view))
            url_tokens += url_params

            if not skip_site:
                url_tokens.append(("site", row["site"]))

            elements.append(
                LivestatusResult(
                    text_tokens=text_tokens,
                    url=_build_url(url_tokens),
                    row=row,
                    display_text="",  # Is created later by self._generate_display_texts
                )
            )

        return self._generate_display_texts(elements)

    def _get_target_view(self, exact_match: bool = True) -> ViewName:
        if exact_match:
            if self.livestatus_table == "hosts":
                return "host"
            if self.livestatus_table == "services":
                return "allservices"
            if self.livestatus_table == "hostgroups":
                return "hostgroup"
            if self.livestatus_table == "servicegroups":
                return "servicegroup"
        else:
            if self.livestatus_table == "hosts":
                return "searchhost"
            if self.livestatus_table == "services":
                return "searchsvc"
            if self.livestatus_table == "hostgroups":
                return "hostgroups"
            if self.livestatus_table == "servicegroups":
                return "svcgroups"

        raise NotImplementedError()

    def _generate_display_texts(self, elements: list[LivestatusResult]) -> list[SearchResult]:
        """Creates the text displayed to the user

        Analyzes all display texts and ensures that we have unique ones"""
        for element in elements:
            if self.livestatus_table == "services":
                element.display_text = element.row["description"]
            else:
                element.display_text = element.text_tokens[0][1]

        if self._element_texts_unique(elements):
            return [SearchResult(title=e.display_text, url=e.url) for e in elements]

        # Some (ugly) special handling when the results are not unique
        # Whenever this happens we try to find a fitting second value

        if self.livestatus_table in ["hostgroups", "servicegroups"]:
            # Discard redundant hostgroups
            results: list[SearchResult] = []
            used_groups: set[str] = set()
            for element in elements:
                if element.display_text in used_groups:
                    continue
                results.append(SearchResult(title=element.display_text, url=element.url))
                used_groups.add(element.display_text)
            return results

        # Add additional info to the display text
        for element in elements:
            hostname = element.row.get("host_name", element.row.get("name"))
            assert hostname is not None  # TODO: Why is this the case? Needed for correct typing.
            if "&host_regex=" not in element.url:
                element.url += "&host_regex=%s" % hostname

            for shortname, text in element.text_tokens:
                if shortname in ["h", "al"] and text not in element.display_text:
                    element.context = text
                    break
            else:
                element.context = hostname

        return [SearchResult(title=e.display_text, url=e.url, context=e.context) for e in elements]

    def _element_texts_unique(self, elements: list[LivestatusResult]) -> bool:
        used_texts: set[str] = set()
        for entry in elements:
            if entry.display_text in used_texts:
                return False
            used_texts.add(entry.display_text)
        return True


class QuicksearchManager:
    """Producing the results for the given search query"""

    def __init__(self, raise_too_many_rows_error: bool = True) -> None:
        self.raise_too_many_rows_error = raise_too_many_rows_error

    def generate_results(self, query: SearchQuery) -> SearchResultsByTopic:
        search_objects = self._determine_search_objects(query)
        self._conduct_search(search_objects)
        return self._evaluate_results(search_objects)

    def generate_search_url(self, query: SearchQuery) -> str:
        search_objects = self._determine_search_objects(query)

        # Hitting enter on the search field to open the search in the
        # page content area is currently only supported for livestatus
        # search plugins
        search_objects = [
            s for s in search_objects if isinstance(s, LivestatusQuicksearchConductor)
        ]

        try:
            self._conduct_search(search_objects)
        except TooManyRowsError:
            pass

        # Generate a search page for the topmost search_object with results
        url_params: HTTPVariables = []
        for search_object in search_objects:
            if search_object.num_rows() > 0:
                url_params.extend(search_object.get_search_url_params())
                break
        else:
            url_params.extend(
                [
                    ("view_name", "allservices"),
                    ("filled_in", "filter"),
                    ("_show_filter_form", "0"),
                    ("service_regex", query),
                ]
            )

        return _build_url(url_params)

    def _determine_search_objects(self, query: SearchQuery) -> list[ABCQuicksearchConductor]:
        """Construct search objects from the query

        Try to find search object expressions and construct objects or
        create the search objects in the configured search order

        Please note: Search expressions are currently only supported for
        livestatus based search plugins.
        """

        found_filters = self._find_search_object_expressions(query)

        if found_filters:
            # The query contains at least one search expression to search a specific search plugin.
            used_filters = self._get_used_filters_from_query(query, found_filters)
            return [
                LivestatusQuicksearchConductor(
                    used_filters,
                    FilterBehaviour.CONTINUE,
                )
            ]

        # No explicit filters specified by search expression. Execute the quicksearch plug-ins in
        # the order they are configured to let them answer the query.
        return [
            self._make_conductor(
                filter_name,
                {filter_name: [_to_regex(query)]},
                FilterBehaviour[filter_behaviour_str.upper()],
            )
            for filter_name, filter_behaviour_str in active_config.quicksearch_search_order
        ]

    @staticmethod
    def _find_search_object_expressions(query: SearchQuery) -> list[tuple[str, int]]:
        """Extract a list of search plug-in expressions from the search query

        The returned list contains the name of the search plug-in and the character
        at which the search starts
        """

        filter_names = {"%s" % x.name for x in match_plugin_registry.values()}
        filter_regex = "|".join(filter_names)

        # Goal: "((^| )(hg|h|sg|s|al|tg|ad):)"
        regex = f"((^| )({filter_regex}):)"
        found_filters = []
        matches = re.finditer(regex, query)
        for match in matches:
            found_filters.append((match.group(1), match.start()))
        return found_filters

    @staticmethod
    def _get_used_filters_from_query(
        query: SearchQuery,
        found_filters: list[tuple[str, int]],
    ) -> UsedFilters:
        """Extract the expressions for each search plugin

        Create a structure like this: {'h': ['heute'], 's': ['Check_MK']}
        """
        used_filters: dict[str, list[str]] = {}
        current_string = query
        for filter_type, offset in found_filters[-1::-1]:
            filter_text = _to_regex(current_string[offset + len(filter_type) :]).strip()
            filter_name = filter_type.strip().rstrip(":")
            used_filters.setdefault(filter_name, []).append(filter_text)
            current_string = current_string[:offset]
        return used_filters

    def _make_conductor(
        self,
        filter_name: str,
        used_filters: UsedFilters,
        filter_behaviour: FilterBehaviour,
    ) -> ABCQuicksearchConductor:
        plugin = match_plugin_registry[filter_name]
        if isinstance(plugin, ABCLivestatusMatchPlugin):
            return LivestatusQuicksearchConductor(used_filters, filter_behaviour)

        return BasicPluginQuicksearchConductor(used_filters, filter_behaviour)

    def _conduct_search(self, search_objects: list[ABCQuicksearchConductor]) -> None:
        """Collect the raw data from livestatus

        1. The single search objects execute the query.
        2. The number of results are counted and either limited or other filters are limited,
           depending on the configured filter behavior.
        """
        total_rows = 0
        for idx, search_object in enumerate(search_objects):
            search_object.do_query()
            total_rows += search_object.num_rows()

            if total_rows > active_config.quicksearch_dropdown_limit:
                search_object.remove_rows_from_end(
                    total_rows - active_config.quicksearch_dropdown_limit
                )
                if self.raise_too_many_rows_error:
                    raise TooManyRowsError(
                        _("More than %d results") % active_config.quicksearch_dropdown_limit
                    )

            if search_object.row_limit_exceeded():
                if self.raise_too_many_rows_error:
                    raise TooManyRowsError(
                        _("More than %d results") % active_config.quicksearch_dropdown_limit
                    )

            if (
                search_object.num_rows() > 0
                and search_object.filter_behaviour is not FilterBehaviour.CONTINUE
            ):
                if search_object.filter_behaviour is FilterBehaviour.FINISHED_DISTINCT:
                    # Discard all data of previous filters and break
                    for i in range(idx - 1, -1, -1):
                        search_objects[i].remove_rows_from_end(
                            active_config.quicksearch_dropdown_limit
                        )
                break

    def _evaluate_results(
        self,
        search_objects: list[ABCQuicksearchConductor],
    ) -> SearchResultsByTopic:
        """Generates elements out of the raw data"""
        yield from (
            (
                search_object.get_match_topic(),
                results,
            )
            for search_object in search_objects
            for results in [search_object.create_results()]
            if results
        )


def _maybe_strip(param: str | None) -> str | None:
    if param is None:
        return None
    return param.strip()


class QuicksearchSnapin(SidebarSnapin):
    def __init__(self) -> None:
        self._quicksearch_manager = QuicksearchManager()
        super().__init__()

    @classmethod
    def type_name(cls) -> str:
        return "search"

    @classmethod
    def title(cls) -> str:
        return _("Quicksearch")

    @classmethod
    def description(cls) -> str:
        return _(
            "Interactive search field for direct access to monitoring instances (hosts, services, "
            "host and service groups).<br>You can use the following filters: <i>h:</i> Host,<br> "
            "<i>s:</i> Service, <i>hg:</i> Host group, <i>sg:</i> Service group,<br><i>ad:</i> "
            "Address, <i>al:</i> Alias, <i>tg:</i> Host tag, <i>hl:</i> Host label, <i>sl:</i> "
            "Service label"
        )

    def show(self, config: Config) -> None:
        id_ = "mk_side_search_field"
        html.open_div(id_="mk_side_search", onclick="cmk.quicksearch.close_popup();")
        html.input(id_=id_, type_="text", name="search", autocomplete="off")
        html.icon_button(
            "#",
            _("Search"),
            "quicksearch",
            onclick="cmk.quicksearch.on_search_click();",
        )
        html.close_div()
        html.div("", id_="mk_side_clear")
        html.javascript(f"cmk.quicksearch.register_search_field('{id_}');")

    def page_handlers(self) -> PageHandlers:
        return {
            "ajax_search": self._ajax_search,
            "search_open": self._page_search_open,
        }

    def _ajax_search(self, config: Config) -> None:
        """Generate the search result list"""
        query = _maybe_strip(request.get_str_input("q"))
        if not query:
            return

        search_objects: list[ABCQuicksearchConductor] = []
        try:
            search_objects = self._quicksearch_manager._determine_search_objects(
                livestatus.lqencode(query)
            )
            self._quicksearch_manager._conduct_search(search_objects)

        except TooManyRowsError as e:
            html.show_warning(str(e))

        except IncorrectLabelInputError:
            pass

        except MKException as e:
            html.show_error("%s" % e)

        except Exception:
            logger.exception("error generating quicksearch results")
            if active_config.debug:
                raise
            html.show_error(traceback.format_exc())

        if not search_objects:
            return

        QuicksearchResultRenderer().show(
            self._quicksearch_manager._evaluate_results(search_objects), query
        )

    def _page_search_open(self, config: Config) -> None:
        """Generate the URL to the view that is opened when confirming the search field"""
        query = _maybe_strip(request.var("q"))
        if not query:
            return

        raise HTTPRedirect(self._quicksearch_manager.generate_search_url(query))


class QuicksearchResultRenderer:
    """HTML rendering the matched results"""

    def show(self, results_by_topic: SearchResultsByTopic, query: SearchQuery) -> None:
        """Renders the elements

        Show search topic if at least two search objects provide elements
        """
        sorted_results = sorted(results_by_topic, key=lambda x: x[0])
        show_match_topics = len(sorted_results) > 1

        for match_topic, results in sorted_results:
            if show_match_topics:
                html.div(match_topic, class_="topic")

            for result in sorted(results, key=lambda x: x.title):
                html.open_a(id_="result_%s" % query, href=result.url, target="main")
                html.write_text_permissive(
                    result.title
                    + (" %s" % HTMLWriter.render_b(result.context) if result.context else "")
                )
                html.close_a()


#   .--Quicksearch Plugins-------------------------------------------------.
#   |         ___        _      _                            _             |
#   |        / _ \ _   _(_) ___| | _____  ___  __ _ _ __ ___| |__          |
#   |       | | | | | | | |/ __| |/ / __|/ _ \/ _` | '__/ __| '_ \         |
#   |       | |_| | |_| | | (__|   <\__ \  __/ (_| | | | (__| | | |        |
#   |        \__\_\\__,_|_|\___|_|\_\___/\___|\__,_|_|  \___|_| |_|        |
#   |                                                                      |
#   |                   ____  _             _                              |
#   |                  |  _ \| |_   _  __ _(_)_ __  ___                    |
#   |                  | |_) | | | | |/ _` | | '_ \/ __|                   |
#   |                  |  __/| | |_| | (_| | | | | \__ \                   |
#   |                  |_|   |_|\__,_|\__, |_|_| |_|___/                   |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Realize the search mechanism to find objects via livestatus          |
#   '----------------------------------------------------------------------'


class ABCMatchPlugin(abc.ABC):
    """Base class for all match plugins"""

    def __init__(self, name: str) -> None:
        super().__init__()
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abc.abstractmethod
    def get_match_topic(self) -> str:
        raise NotImplementedError()


class ABCBasicMatchPlugin(ABCMatchPlugin):
    """Base class for all non livestatus based match plugins"""

    @abc.abstractmethod
    def get_results(self, query: str) -> list[SearchResult]:
        raise NotImplementedError()


class ABCLivestatusMatchPlugin(ABCMatchPlugin):
    """Base class for all livestatus based match plugins"""

    def __init__(
        self,
        supported_livestatus_tables: list[LivestatusTable],
        preferred_livestatus_table: LivestatusTable,
        name: str,
    ):
        super().__init__(name)
        self._supported_livestatus_tables = supported_livestatus_tables
        self._preferred_livestatus_table = preferred_livestatus_table

    def get_preferred_livestatus_table(self) -> LivestatusTable:
        return self._preferred_livestatus_table

    def is_used_for_table(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> bool:
        # Check if this filters handles the table at all
        if livestatus_table not in self._supported_livestatus_tables:
            return False

        if self.name not in used_filters:
            return False

        return True

    @abc.abstractmethod
    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        raise NotImplementedError()

    def is_group_match(self) -> bool:
        return False

    def _create_textfilter_regex(self, used_filters: UsedFilters) -> str:
        patterns = used_filters[self.name]
        if len(patterns) > 1:
            return "(%s)" % "|".join(patterns)
        return patterns[0]

    @abc.abstractmethod
    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        raise NotImplementedError()


class MatchPluginRegistry(cmk.ccc.plugin_registry.Registry[ABCMatchPlugin]):
    def plugin_name(self, instance: ABCMatchPlugin) -> str:
        return instance.name

    def get_livestatus_match_plugins(self) -> list[ABCLivestatusMatchPlugin]:
        return [p for p in self.values() if isinstance(p, ABCLivestatusMatchPlugin)]


match_plugin_registry = MatchPluginRegistry()


class GroupMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self, group_type: str, name: str) -> None:
        super().__init__(
            ["%sgroups" % group_type, "%ss" % group_type, "services"],
            "%sgroups" % group_type,
            name,
        )
        self._group_type = group_type

    def is_group_match(self) -> bool:
        return True

    def get_match_topic(self) -> str:
        if self._group_type == "host":
            return _("Host group")
        return _("Service group")

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        if livestatus_table == "%sgroups" % self._group_type:
            return ["name"]
        return ["%s_groups" % self._group_type]

    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        filter_lines = []
        filter_prefix = ""
        if livestatus_table == "%sgroups" % self._group_type:
            filter_prefix = "name ~~ "
        else:
            filter_prefix = "%s_groups >= " % self._group_type

        for entry in used_filters.get(self.name, []):
            filter_lines.append(f"Filter: {filter_prefix}{entry}")

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        supported_views = {
            # View name    url fieldname,                  key in row
            # Group domains (hostgroups, servicegroups)
            "hostgroup": ["hostgroup", "name"],
            "hostgroups": ["hostgroup_regex", "name"],
            "servicegroup": ["servicegroup", "name"],
            "svcgroups": ["servicegroup_regex", "name"],
            # Host/Service domain (hosts, services)
            "allservices": [
                "%sgroups" % self._group_type,
                "%s_groups" % self._group_type,
            ],
            "searchsvc": [
                "%sgroups" % self._group_type,
                self._group_type == "service" and "groups" or "host_groups",
            ],
            "searchhost": [
                "%sgroups" % self._group_type,
                self._group_type == "service" and "groups" or "host_groups",
            ],
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return None

        filter_name, row_fieldname = view_info

        value = row[row_fieldname] if row else used_filters[self.name]
        filter_value = "|".join(value) if isinstance(value, list) else value

        return filter_value, [(filter_name, filter_value)]


match_plugin_registry.register(
    GroupMatchPlugin(
        group_type="service",
        name="sg",
    )
)

match_plugin_registry.register(
    GroupMatchPlugin(
        group_type="host",
        name="hg",
    )
)


class ServiceMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["services"], "services", "s")

    def get_match_topic(self) -> str:
        return _("Service description")

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        return ["service_description"]

    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        filter_lines = []
        for entry in used_filters.get(self.name, []):
            filter_lines.append("Filter: service_description ~~ %s" % entry)

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        supported_views = ["allservices", "searchsvc"]
        if for_view not in supported_views:
            return None

        if row:
            field_value = row["description"]
            search_key = "service"
        else:
            field_value = self._create_textfilter_regex(used_filters)
            search_key = "service_regex"

        return field_value, [(search_key, field_value)]


match_plugin_registry.register(ServiceMatchPlugin())


class ServiceStateMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["services"], "services", "st")
        self._state_mapping = {
            "ok": "0",
            "warn": "1",
            "crit": "2",
            "unkn": "3",
            "pend": "p",
        }
        self._supported_views = frozenset({"allservices", "searchsvc"})

    def _get_service_state_from_filter(self, value: str) -> str:
        return self._state_mapping.get(value.lower(), "")

    def get_match_topic(self) -> str:
        return _("Service states")

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        return ["state"]

    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        if not (raw_used_filters := used_filters.get(self.name, [])):
            return ""

        filter_lines = [
            f"Filter: state = {self._get_service_state_from_filter(entry)}"
            for entry in raw_used_filters
        ]

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        if for_view not in self._supported_views:
            return None

        url_infos: HTTPVariables = [
            (f"st{self._get_service_state_from_filter(entry)}", "on")
            for entry in used_filters.get(self.name, [])
        ]

        # add support for clicking on an individual filtered service.
        service_field = row["description"] if row else ""
        url_infos.append(("service", service_field))

        return service_field, url_infos


match_plugin_registry.register(ServiceStateMatchPlugin())


class HostMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self, livestatus_field: LivestatusColumn, name: str) -> None:
        super().__init__(["hosts", "services"], "hosts", name)
        self._livestatus_field = livestatus_field  # address, name or alias

    def get_match_topic(self) -> str:
        if self._livestatus_field == "name":
            return _("Host name")
        if self._livestatus_field == "address":
            return _("Hostaddress")
        return _("Hostalias")

    def _get_real_fieldname(self, livestatus_table: LivestatusTable) -> LivestatusColumn:
        if livestatus_table != "hosts":
            return "host_%s" % self._livestatus_field
        return self._livestatus_field

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        return [self._get_real_fieldname(livestatus_table), "host_name"]

    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        filter_lines = []
        for entry in used_filters.get(self.name, []):
            filter_lines.append(f"Filter: {self._get_real_fieldname(livestatus_table)} ~~ {entry}")

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        supported_views = {
            # View name     Filter name
            # Exact matches (always uses hostname as filter)
            "host": {"name": "host", "address": "host", "alias": "host"},
            "allservices": {
                "name": "host_regex",
                "address": "host_regex",
                "alias": "host_regex",
            },
            # Multi matches
            "searchhost": {
                "name": "host_regex",
                "address": "host_address",
                "alias": "hostalias",
            },
            "searchsvc": {
                "name": "host_regex",
                "address": "host_address",
                "alias": "hostalias",
            },
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return None

        filter_name: str = view_info[self._livestatus_field]

        if row:
            field_value: str = row[self._get_real_fieldname(livestatus_table)]
            hostname = row.get("host_name", row.get("name"))
            url_info = [(filter_name, hostname)]
        else:
            field_value = self._create_textfilter_regex(used_filters)
            url_info = [(filter_name, field_value)]
            if self._livestatus_field == "address":
                url_info.append(("host_address_prefix", "yes"))

        return field_value, url_info


match_plugin_registry.register(
    HostMatchPlugin(
        livestatus_field="name",
        name="h",
    )
)

match_plugin_registry.register(
    HostMatchPlugin(
        livestatus_field="alias",
        name="al",
    )
)

match_plugin_registry.register(
    HostMatchPlugin(
        livestatus_field="address",
        name="ad",
    )
)


class HosttagMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["hosts", "services"], "hosts", "tg")

    def _get_hosttag_dict(self):
        lookup_dict = {}
        for tag_group in active_config.tags.tag_groups:
            for grouped_tag in tag_group.tags:
                lookup_dict[grouped_tag.id] = tag_group.id
        return lookup_dict

    def _get_auxtag_dict(self):
        lookup_dict = {}
        for tag_id in active_config.tags.aux_tag_list.get_tag_ids():
            lookup_dict[tag_id] = tag_id
        return lookup_dict

    def get_match_topic(self) -> str:
        return _("Hosttag")

    def get_livestatus_columns(self, livestatus_table):
        return ["host_tags"]

    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        filter_lines = []

        entries = used_filters.get(self.name, [])
        if len(entries) > 3:
            raise MKGeneralException("You can only set up to three 'tg:' filters")

        for entry in entries:
            if ":" not in entry:
                # Be compatible to pre 1.6 filtering for some time (no
                # tag-group:tag-value, but tag-value only)
                filter_lines.append("Filter: host_tag_values >= %s" % livestatus.lqencode(entry))
                continue

            tag_key, tag_value = entry.split(":", 1)
            filter_lines.append(
                f"Filter: tags = {livestatus.lqencode(tag_key)} {livestatus.lqencode(tag_value)}"
            )

        if len(filter_lines) > 1:
            filter_lines.append("And: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        # "searchsvc" and "allservices" are needed for Multi-Filter use
        supported_views = {
            "searchhost": "host_regex",
            "host": "host",
            "searchsvc": "searchsvc",
            "allservices": "allservices",
        }

        filter_name = supported_views.get(for_view)
        if not filter_name:
            return None

        if row and filter_name not in ["allservices", "searchsvc"]:
            hostname = row.get("host_name", row.get("name"))
            assert hostname is not None  # TODO: Why is this the case? Needed for correct typing.
            return hostname, [(filter_name, hostname)]

        url_infos = []
        hosttag_to_group_dict = self._get_hosttag_dict()
        auxtag_to_group_dict = self._get_auxtag_dict()

        for idx, entry in enumerate(used_filters.get(self.name, [])):
            if ":" not in entry:
                # Be compatible to pre 1.6 filtering for some time (no
                # tag-group:tag-value, but tag-value only)
                if entry in hosttag_to_group_dict:
                    tag_key, tag_value = hosttag_to_group_dict[entry], entry
                elif entry in auxtag_to_group_dict:
                    tag_key, tag_value = auxtag_to_group_dict[entry], entry
                else:
                    continue
            else:
                tag_key, tag_value = entry.split(":", 1)

            # here we check which *_to_group_dict containes the tag_value
            # we do not care about the actual data
            # its purpose is to decide which 'url info' to use
            if tag_value in hosttag_to_group_dict:
                url_infos.append(("host_tag_%d_grp" % idx, tag_key))
                url_infos.append(("host_tag_%d_op" % idx, "is"))
                url_infos.append(("host_tag_%d_val" % idx, tag_value))
            elif tag_value in auxtag_to_group_dict:
                url_infos.append(("host_auxtags_%d" % idx, tag_key))

        return "", url_infos


match_plugin_registry.register(HosttagMatchPlugin())


class ABCLabelMatchPlugin(ABCLivestatusMatchPlugin):
    @staticmethod
    def _input_to_key_value(inpt: str) -> Label:
        if ":" not in inpt:
            raise IncorrectLabelInputError(None, label_help_text())
        key, value = inpt.split(":", maxsplit=1)
        if not key or not value:
            raise IncorrectLabelInputError(None, label_help_text())
        return Label(key, value, False)

    def _user_inputs_to_labels(self, user_inputs: Iterable[str]) -> Labels:
        yield from (self._input_to_key_value(inpt) for inpt in user_inputs)

    def get_livestatus_filters(
        self,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
    ) -> LivestatusFilterHeaders:
        user_inputs = used_filters.get(self.name, [])
        return encode_labels_for_livestatus(
            column=self.get_livestatus_columns(livestatus_table)[0],
            labels=self._user_inputs_to_labels(user_inputs),
        ).rstrip("\n")


class HostLabelMatchPlugin(ABCLabelMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["hosts", "services"], "hosts", "hl")
        self._supported_views = {"host", "searchhost", "allservices", "searchsvc"}

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        return ["labels"] if livestatus_table == "hosts" else ["host_labels"]

    def get_match_topic(self) -> str:
        return _("Host labels")

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        _rows: Rows,
    ) -> Matches:
        if for_view not in self._supported_views:
            return None
        if for_view == "host" and row:
            return row["name"], [("host", row["name"])]
        return "", list(
            filter_http_vars_for_simple_label_group(used_filters[self.name], "host").items()
        )


class ServiceLabelMatchPlugin(ABCLabelMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["services"], "services", "sl")
        self._supported_views = {"allservices", "searchsvc"}

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> list[LivestatusColumn]:
        return ["labels"]

    def get_match_topic(self) -> str:
        return _("Service labels")

    def get_matches(
        self,
        for_view: ViewName,
        row: Row | None,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        _rows: Rows,
    ) -> Matches:
        if for_view not in self._supported_views:
            return None
        if row:
            return "", [("service", row["description"])]
        return "", list(
            filter_http_vars_for_simple_label_group(used_filters[self.name], "service").items()
        )


match_plugin_registry.register(HostLabelMatchPlugin())
match_plugin_registry.register(ServiceLabelMatchPlugin())


class MonitorMenuMatchPlugin(ABCBasicMatchPlugin):
    """Create matches for the entries of the monitor menu"""

    def __init__(self) -> None:
        super().__init__("menu")

    def get_match_topic(self) -> str:
        return _("Monitor")

    def get_results(self, query: str) -> list[SearchResult]:
        return [
            SearchResult(
                title=main_menu_item.title,
                url=main_menu_item.url,
            )
            for main_menu_topic in (
                main_menu_registry["monitoring"].topics()
                if main_menu_registry["monitoring"].topics
                else []
            )
            for main_menu_item in get_main_menu_items_prefixed_by_segment(main_menu_topic)
            if any(
                query.lower() in match_text.lower()
                for match_text in [
                    main_menu_item.title,
                    *main_menu_item.main_menu_search_terms,
                ]
            )
        ]


match_plugin_registry.register(MonitorMenuMatchPlugin())

#   .--Menu Search---------------------------------------------------------.
#   |      __  __                    ____                      _           |
#   |     |  \/  | ___ _ __  _   _  / ___|  ___  __ _ _ __ ___| |__        |
#   |     | |\/| |/ _ \ '_ \| | | | \___ \ / _ \/ _` | '__/ __| '_ \       |
#   |     | |  | |  __/ | | | |_| |  ___) |  __/ (_| | | | (__| | | |      |
#   |     |_|  |_|\___|_| |_|\__,_| |____/ \___|\__,_|_|  \___|_| |_|      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Search in menus (Monitoring + Setup)                                 |
#   '----------------------------------------------------------------------'


class MenuSearchResultsRenderer(abc.ABC):
    MAX_RESULTS_BEFORE_SHOW_ALL: Final = 10

    @abc.abstractmethod
    def generate_results(self, query: SearchQuery, config: Config) -> SearchResultsByTopic:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def search_type(self) -> Literal["monitoring", "setup"]:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def max_results_after_show_all(self) -> None | int:
        raise NotImplementedError()

    def render(self, query: str, config: Config) -> str:
        try:
            results = self.generate_results(query, config)
        # Don't render the IncorrectLabelInputError in Main Menu to make the handling of
        # incorrect inputs consistent with other search querys
        except IncorrectLabelInputError:
            return ""
        except MKException as error:
            return self._render_error(error)
        return self._render_results(results)

    def _render_error(self, error: MKException) -> str:
        with output_funnel.plugged():
            html.open_div(class_="error")
            html.write_text_permissive(f"{error}")
            html.close_div()
            error_as_html = output_funnel.drain()
        return error_as_html

    def _get_icon_mapping(
        self,
        default_icons: tuple[Icon, Icon],
    ) -> dict[str, tuple[Icon, Icon]]:
        # {topic: (Icon(Topic): green, Icon(Item): colorful)}
        mapping: dict[str, tuple[Icon, Icon]] = {}
        for menu in [
            main_menu_registry.menu_setup(),
            main_menu_registry.menu_monitoring(),
        ]:
            mapping[str(menu.title)] = (
                (menu.icon + "_active" if isinstance(menu.icon, str) else default_icons[0]),
                menu.icon if menu.icon else default_icons[1],
            )

            if menu.topics:
                for topic in menu.topics():
                    mapping[topic.title] = (
                        topic.icon if topic.icon else default_icons[0],
                        topic.icon if topic.icon else default_icons[1],
                    )
                    for item in topic.entries:
                        mapping[item.title] = (
                            topic.icon if topic.icon else default_icons[0],
                            item.icon if item.icon else default_icons[1],
                        )
        for module_class in main_module_registry.values():
            module = module_class()
            if module.title not in mapping:
                mapping[module.title] = (
                    (
                        module.topic.icon_name
                        if module.topic and module.topic.icon_name
                        else default_icons[0]
                    ),
                    module.icon if module.icon else default_icons[1],
                )
        return mapping

    def _render_results(
        self,
        results: SearchResultsByTopic,
    ) -> str:
        with output_funnel.plugged():
            default_icons = (
                "main_" + self.search_type + "_active",
                "main_" + self.search_type,
            )
            icon_mapping = self._get_icon_mapping(default_icons)

            for topic, search_results_iter in results:
                if self.max_results_after_show_all is None:
                    search_results_list = list(search_results_iter)
                    show_all_limit_exceeded = False
                else:
                    search_results_list, show_all_limit_exceeded = _evaluate_iterable_up_to(
                        search_results_iter,
                        self.max_results_after_show_all,
                    )
                if not search_results_list:
                    continue

                use_show_all = len(search_results_list) >= self.MAX_RESULTS_BEFORE_SHOW_ALL

                icons = icon_mapping.get(topic, default_icons)
                html.open_div(
                    id_=topic,
                    class_=["topic", "extendable" if use_show_all else ""],
                )
                self._render_topic(topic, icons)
                html.open_ul()
                for count, result in enumerate(search_results_list):
                    self._render_result(
                        result,
                        hidden=count >= self.MAX_RESULTS_BEFORE_SHOW_ALL,
                    )

                if use_show_all:
                    html.open_li(class_="show_all_items")
                    html.open_a(
                        href=None,
                        onclick=f"cmk.search.on_click_show_all_results({json.dumps(topic)}, 'popup_menu_{self.search_type}');",
                    )
                    html.write_text_permissive(_("Show all results"))
                    html.close_a()
                    html.close_li()

                if show_all_limit_exceeded:
                    html.open_li(
                        class_="hidden warning",
                        **{"data-extended": "false"},
                    )
                    html.write_text_permissive(
                        _("More than %d results available, please refine your search.")
                        % self.max_results_after_show_all
                    )
                    html.close_li()

                html.close_ul()
                html.close_div()
            html_text = output_funnel.drain()
        return html_text

    def _render_topic(self, topic: str, icons: tuple[Icon, Icon]) -> None:
        html.open_h2()
        html.div(class_="spacer", content="")

        html.open_a(
            class_="collapse_topic",
            href=None,
            onclick=f"cmk.search.on_click_collapse_topic({json.dumps(topic)})",
        )
        html.icon(icon="collapse_arrow", title=_("Show all topics"))
        html.close_a()

        if not user.get_attribute("icons_per_item"):
            html.icon(icons[0])
        else:
            html.icon(icons[1])
        html.span(topic)
        html.close_h2()

    def _render_result(self, result: SearchResult, hidden: bool = False) -> None:
        html.open_li(
            class_="hidden" if hidden else "",
            **{"data-extended": "false" if hidden else ""},
        )
        html.open_a(
            href=result.url,
            target="main",
            onclick=f"cmk.popup_menu.close_popup(); cmk.search.on_click_reset('{self.search_type}');",
            title=result.title + (" %s" % result.context if result.context else ""),
        )
        html.write_text_permissive(
            result.title + (" %s" % HTMLWriter.render_b(result.context) if result.context else "")
        )
        html.close_a()
        html.close_li()


class MonitorMenuSearchResultsRenderer(MenuSearchResultsRenderer):
    max_results_after_show_all: Final = None
    search_type: Final = "monitoring"

    def __init__(self) -> None:
        self._search_manager: Final = QuicksearchManager(raise_too_many_rows_error=False)

    def generate_results(self, query: SearchQuery, config: Config) -> SearchResultsByTopic:
        return self._search_manager.generate_results(query)


class SetupMenuSearchResultsRenderer(MenuSearchResultsRenderer):
    max_results_after_show_all: Final = 80
    search_type: Final = "setup"

    def __init__(self) -> None:
        self._search_manager: Final = IndexSearcher(
            get_redis_client(),
            PermissionsHandler(),
        )

    def generate_results(self, query: SearchQuery, config: Config) -> SearchResultsByTopic:
        return self._search_manager.search(query, config)


_TIterItem = TypeVar("_TIterItem")


def _evaluate_iterable_up_to(
    iterable: Iterable[_TIterItem], up_to: int
) -> tuple[list[_TIterItem], bool]:
    """
    >>> _evaluate_iterable_up_to([1, 2, 3], 5)
    ([1, 2, 3], False)
    >>> _evaluate_iterable_up_to([1, 2, 3], 2)
    ([1, 2], True)
    """
    evaluated = list(itertools.islice(iterable, up_to + 1))
    if len(evaluated) > up_to:
        return evaluated[:-1], True
    return evaluated, False


class PageSearchMonitoring(AjaxPage):
    def page(self, config: Config) -> PageResult:
        query = request.get_str_input_mandatory("q")
        return MonitorMenuSearchResultsRenderer().render(livestatus.lqencode(query), config)


class PageSearchSetup(AjaxPage):
    def page(self, config: Config) -> PageResult:
        query = request.get_str_input_mandatory("q")
        try:
            return SetupMenuSearchResultsRenderer().render(livestatus.lqencode(query), config)
        except IndexNotFoundException:
            with output_funnel.plugged():
                html.open_div(class_="topic")
                html.open_ul()
                html.write_text_permissive(_("Currently indexing, please try again shortly."))
                html.close_ul()
                html.close_div()
                return output_funnel.drain()
        except RuntimeError:
            with output_funnel.plugged():
                html.open_div(class_="error")
                html.open_ul()
                html.write_text_permissive(_("Redis server is not reachable."))
                html.close_ul()
                html.close_div()
                return output_funnel.drain()
        except Exception:
            with output_funnel.plugged():
                handle_exception_as_gui_crash_report(
                    show_crash_link=getattr(g, "may_see_crash_reports", False),
                )
                return output_funnel.drain()
