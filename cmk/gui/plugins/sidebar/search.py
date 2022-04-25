#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
import re
import traceback
from dataclasses import dataclass
from enum import Enum, unique
from typing import Dict, Iterable, List, Optional, Set, Tuple

import livestatus

import cmk.utils.plugin_registry
from cmk.utils.exceptions import MKException, MKGeneralException

import cmk.gui.sites as sites
import cmk.gui.utils
from cmk.gui.config import active_config
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.globals import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.plugins.sidebar.utils import PageHandlers, SidebarSnapin, snapin_registry
from cmk.gui.plugins.wato.utils import main_module_registry
from cmk.gui.type_defs import (
    ABCMegaMenuSearch,
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
    encode_labels_for_http,
    encode_labels_for_livestatus,
    Label,
    label_help_text,
    Labels,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.urls import makeuri
from cmk.gui.wato.pages.hosts import ModeEditHost
from cmk.gui.watolib.search import (
    IndexNotFoundException,
    IndexSearcher,
    PermissionsHandler,
    URLChecker,
)

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
UsedFilters = Dict[str, List[str]]
Matches = Optional[Tuple[str, HTTPVariables]]


@dataclass
class LivestatusResult:
    text_tokens: List[Tuple[str, str]]
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
    def create_results(self) -> List[SearchResult]:
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
    """Passes queries through to a non livestatus plugin

    There is no aggregation done by this conductor. It deals with a single search plugin."""

    def __init__(self, used_filters: UsedFilters, filter_behaviour: FilterBehaviour) -> None:
        super().__init__(used_filters, filter_behaviour)
        self._results: List[SearchResult] = []

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

    def create_results(self) -> List[SearchResult]:
        return self._results[: active_config.quicksearch_dropdown_limit]


class LivestatusQuicksearchConductor(ABCQuicksearchConductor):
    """Executes the livestatus search plugins and collects results

    It cares about aggregating the queries of different filters together to a single livestatus
    query (see _generate_livestatus_command) in case they are given with "used_filters".

    Based on all the given plugin selection expressions it decides which one to use. There is only a
    single table selected and queried! This means that incompatible search plugins in a single
    search query (e.g. service group and host name) are not both executed.

    Based on the used_filters it selects a livestatus table to query. Then it constructs the
    livestatus query with the help of all search plugins that support searching the previously
    selected table.
    """

    def __init__(self, used_filters: UsedFilters, filter_behaviour: FilterBehaviour) -> None:
        super().__init__(used_filters, filter_behaviour)

        self._livestatus_table: Optional[str] = None
        self._livestatus_command: str = ""  # Computed livestatus query
        self._rows: Rows = []  # Raw data from livestatus
        self._queried_livestatus_columns: List[str] = []

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
        livestatus_filter_domains: Dict[str, List[str]] = {}

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
        self._livestatus_command = "GET %s\nColumns: %s\n%s\n" % (
            self.livestatus_table,
            " ".join(self._queried_livestatus_columns),
            "\n".join(livestatus_filters),
        )

        # Limit number of results
        limit = active_config.quicksearch_dropdown_limit
        self._livestatus_command += "Cache: reload\nLimit: %d\nColumnHeaders: off" % (limit + 1)

    def _get_used_search_plugins(self) -> List["ABCLivestatusMatchPlugin"]:
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

    def _get_livestatus_default_columns(self) -> List[str]:
        return {
            "services": ["description", "host_name"],
            "hosts": ["name"],
            "hostgroups": ["name"],
            "servicegroups": ["name"],
        }.get(
            self.livestatus_table, []
        )  # TODO: Is the default correct/necessary?

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

    def create_results(self) -> List[SearchResult]:
        elements: List[LivestatusResult] = []

        if not self._rows:
            return []

        target_view = self._get_target_view()

        # Feed each row to the filters and let them add additional text/url infos
        for row in self._rows:
            text_tokens: List[Tuple[str, str]] = []
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

    def _generate_display_texts(self, elements: List[LivestatusResult]) -> List[SearchResult]:
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
            results: List[SearchResult] = []
            used_groups: Set[str] = set()
            for element in elements:
                if element.display_text in used_groups:
                    continue
                results.append(SearchResult(title=element.display_text, url=element.url))
                used_groups.add(element.display_text)
            return results

        # Add additional info to the display text
        for element in elements:
            hostname = element.row.get("host_name", element.row.get("name"))
            if "&host_regex=" not in element.url:
                element.url += "&host_regex=%s" % hostname

            for shortname, text in element.text_tokens:
                if shortname in ["h", "al"] and text not in element.display_text:
                    element.context = text
                    break
            else:
                element.context = hostname

        return [SearchResult(title=e.display_text, url=e.url, context=e.context) for e in elements]

    def _element_texts_unique(self, elements: List[LivestatusResult]) -> bool:
        used_texts: Set[str] = set()
        for entry in elements:
            if entry.display_text in used_texts:
                return False
            used_texts.add(entry.display_text)
        return True


class QuicksearchManager:
    """Producing the results for the given search query"""

    def __init__(self, raise_too_many_rows_error: bool = True):
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

    def _determine_search_objects(self, query: SearchQuery) -> List[ABCQuicksearchConductor]:
        """Construct search objects from the query

        Try to find search object expressions and construct objects or
        create the search objects in the configured search order

        Please note: Search expressions are currently only supported for
        livestatus based search plugins.
        """

        found_filters = self._find_search_object_expressions(query)

        search_objects: List[ABCQuicksearchConductor] = []
        if found_filters:
            # The query contains at least one search expression to search a specific search plugin.
            used_filters = self._get_used_filters_from_query(query, found_filters)
            search_objects.append(
                LivestatusQuicksearchConductor(
                    used_filters,
                    FilterBehaviour.CONTINUE,
                )
            )
        else:
            # No explicit filters specified by search expression. Execute the quicksearch plugins in
            # the order they are configured to let them answer the query.
            for filter_name, filter_behaviour_str in active_config.quicksearch_search_order:
                search_objects.append(
                    self._make_conductor(
                        filter_name,
                        {filter_name: [_to_regex(query)]},
                        FilterBehaviour[filter_behaviour_str.upper()],
                    )
                )

        return search_objects

    @staticmethod
    def _find_search_object_expressions(query: SearchQuery) -> List[Tuple[str, int]]:
        """Extract a list of search plugin expressions from the search query

        The returned list contains the name of the search plugin and the character
        at which the search starts
        """

        filter_names = {"%s" % x.name for x in match_plugin_registry.values()}
        filter_regex = "|".join(filter_names)

        # Goal: "((^| )(hg|h|sg|s|al|tg|ad):)"
        regex = "((^| )(%(filter_regex)s):)" % {"filter_regex": filter_regex}
        found_filters = []
        matches = re.finditer(regex, query)
        for match in matches:
            found_filters.append((match.group(1), match.start()))
        return found_filters

    @staticmethod
    def _get_used_filters_from_query(
        query: SearchQuery,
        found_filters: List[Tuple[str, int]],
    ) -> UsedFilters:
        """Extract the expressions for each search plugin

        Create a structure like this: {'h': ['heute'], 's': ['Check_MK']}
        """
        used_filters: Dict[str, List[str]] = {}
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

    def _conduct_search(self, search_objects: List[ABCQuicksearchConductor]) -> None:
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
        search_objects: List[ABCQuicksearchConductor],
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


def _maybe_strip(param: Optional[str]) -> Optional[str]:
    if param is None:
        return None
    return param.strip()


@snapin_registry.register
class QuicksearchSnapin(SidebarSnapin):
    def __init__(self):
        self._quicksearch_manager = QuicksearchManager()
        super().__init__()

    @classmethod
    def type_name(cls):
        return "search"

    @classmethod
    def title(cls):
        return _("Quicksearch")

    @classmethod
    def description(cls):
        return _(
            "Interactive search field for direct access to monitoring instances (hosts, services, "
            "host and service groups).<br>You can use the following filters: <i>h:</i> Host,<br> "
            "<i>s:</i> Service, <i>hg:</i> Host group, <i>sg:</i> Service group,<br><i>ad:</i> "
            "Address, <i>al:</i> Alias, <i>tg:</i> Host tag, <i>hl:</i> Host label, <i>sl:</i> "
            "Service label"
        )

    def show(self):
        id_ = "mk_side_search_field"
        html.open_div(id_="mk_side_search", onclick="cmk.quicksearch.close_popup();")
        html.input(id_=id_, type_="text", name="search", autocomplete="off")
        html.icon_button(
            "#", _("Search"), "quicksearch", onclick="cmk.quicksearch.on_search_click();"
        )
        html.close_div()
        html.div("", id_="mk_side_clear")
        html.javascript(f"cmk.quicksearch.register_search_field('{id_}');")

    @classmethod
    def allowed_roles(cls):
        return ["user", "admin", "guest"]

    def page_handlers(self) -> PageHandlers:
        return {
            "ajax_search": self._ajax_search,
            "search_open": self._page_search_open,
        }

    def _ajax_search(self) -> None:
        """Generate the search result list"""
        query = _maybe_strip(request.get_str_input("q"))
        if not query:
            return

        try:
            results = self._quicksearch_manager.generate_results(query)
            QuicksearchResultRenderer().show(results, query)

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

    def _page_search_open(self) -> None:
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
                html.write_text(
                    result.title + (" %s" % html.render_b(result.context) if result.context else "")
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

    def __init__(self, name: str):
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
    def get_results(self, query: str) -> List[SearchResult]:
        raise NotImplementedError()


class ABCLivestatusMatchPlugin(ABCMatchPlugin):
    """Base class for all livestatus based match plugins"""

    def __init__(
        self,
        supported_livestatus_tables: List[LivestatusTable],
        preferred_livestatus_table: LivestatusTable,
        name: str,
    ):
        super().__init__(name)
        self._supported_livestatus_tables = supported_livestatus_tables
        self._preferred_livestatus_table = preferred_livestatus_table

    def get_preferred_livestatus_table(self) -> LivestatusTable:
        return self._preferred_livestatus_table

    def is_used_for_table(self, livestatus_table: LivestatusTable, used_filters: UsedFilters):
        # Check if this filters handles the table at all
        if livestatus_table not in self._supported_livestatus_tables:
            return False

        if self.name not in used_filters:
            return False

        return True

    @abc.abstractmethod
    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
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
        row: Optional[Row],
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        raise NotImplementedError()


class MatchPluginRegistry(cmk.utils.plugin_registry.Registry[ABCMatchPlugin]):
    def plugin_name(self, instance):
        return instance.name

    def get_livestatus_match_plugins(self) -> List[ABCLivestatusMatchPlugin]:
        return [p for p in self.values() if isinstance(p, ABCLivestatusMatchPlugin)]


match_plugin_registry = MatchPluginRegistry()


class GroupMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self, group_type: str, name: str):
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

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
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
            filter_lines.append("Filter: %s%s" % (filter_prefix, entry))

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Optional[Row],
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
            "allservices": ["%sgroups" % self._group_type, "%s_groups" % self._group_type],
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
    def __init__(self):
        super().__init__(["services"], "services", "s")

    def get_match_topic(self) -> str:
        return _("Service Description")

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
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
        row: Optional[Row],
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


class HostMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self, livestatus_field, name):
        super().__init__(["hosts", "services"], "hosts", name)
        self._livestatus_field = livestatus_field  # address, name or alias

    def get_match_topic(self) -> str:
        if self._livestatus_field == "name":
            return _("Hostname")
        if self._livestatus_field == "address":
            return _("Hostaddress")
        return _("Hostalias")

    def _get_real_fieldname(self, livestatus_table):
        if livestatus_table != "hosts":
            return "host_%s" % self._livestatus_field
        return self._livestatus_field

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
        return [self._get_real_fieldname(livestatus_table), "host_name"]

    def get_livestatus_filters(
        self, livestatus_table: LivestatusTable, used_filters: UsedFilters
    ) -> LivestatusFilterHeaders:
        filter_lines = []
        for entry in used_filters.get(self.name, []):
            filter_lines.append(
                "Filter: %s ~~ %s" % (self._get_real_fieldname(livestatus_table), entry)
            )

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Optional[Row],
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        supported_views = {
            # View name     Filter name
            # Exact matches (always uses hostname as filter)
            "host": {"name": "host", "address": "host", "alias": "host"},
            "allservices": {"name": "host_regex", "address": "host_regex", "alias": "host_regex"},
            # Multi matches
            "searchhost": {"name": "host_regex", "address": "host_address", "alias": "hostalias"},
            "searchsvc": {"name": "host_regex", "address": "host_address", "alias": "hostalias"},
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
    def __init__(self):
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
        return ["tags"]

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
                filter_lines.append("Filter: tag_values >= %s" % livestatus.lqencode(entry))
                continue

            tag_key, tag_value = entry.split(":", 1)
            filter_lines.append(
                "Filter: tags = %s %s"
                % (livestatus.lqencode(tag_key), livestatus.lqencode(tag_value))
            )

        if len(filter_lines) > 1:
            filter_lines.append("And: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(
        self,
        for_view: ViewName,
        row: Optional[Row],
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        rows: Rows,
    ) -> Matches:
        supported_views = {"searchhost": "host_regex", "host": "host"}

        filter_name = supported_views.get(for_view)
        if not filter_name:
            return None

        if row:
            hostname = row.get("host_name", row.get("name"))
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

    def _user_inputs_to_http(self, user_inputs: Iterable[str]) -> str:
        return encode_labels_for_http(self._user_inputs_to_labels(user_inputs))

    def get_livestatus_filters(
        self,
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
    ) -> LivestatusFilterHeaders:
        user_inputs = used_filters.get(self.name, [])
        return encode_labels_for_livestatus(
            self.get_livestatus_columns(livestatus_table)[0],
            self._user_inputs_to_labels(user_inputs),
        )


class HostLabelMatchPlugin(ABCLabelMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["hosts", "services"], "hosts", "hl")
        self._supported_views = {"host", "searchhost", "allservices", "searchsvc"}

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
        return ["labels"] if livestatus_table == "hosts" else ["host_labels"]

    def get_match_topic(self) -> str:
        return _("Host labels")

    def get_matches(
        self,
        for_view: ViewName,
        row: Optional[Row],
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        _rows: Rows,
    ) -> Matches:
        if for_view not in self._supported_views:
            return None
        if for_view == "host" and row:
            return row["name"], [("host", row["name"])]
        return "", [("host_label", self._user_inputs_to_http(used_filters[self.name]))]


class ServiceLabelMatchPlugin(ABCLabelMatchPlugin):
    def __init__(self) -> None:
        super().__init__(["services"], "services", "sl")
        self._supported_views = {"allservices", "searchsvc"}

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
        return ["labels"]

    def get_match_topic(self) -> str:
        return _("Service labels")

    def get_matches(
        self,
        for_view: ViewName,
        row: Optional[Row],
        livestatus_table: LivestatusTable,
        used_filters: UsedFilters,
        _rows: Rows,
    ) -> Matches:
        if for_view not in self._supported_views:
            return None
        if row:
            return "", [("service", row["description"])]
        return "", [("service_label", self._user_inputs_to_http(used_filters[self.name]))]


match_plugin_registry.register(HostLabelMatchPlugin())
match_plugin_registry.register(ServiceLabelMatchPlugin())


class MonitorMenuMatchPlugin(ABCBasicMatchPlugin):
    """Create matches for the entries of the monitor menu"""

    def __init__(self) -> None:
        super().__init__("menu")

    def get_match_topic(self) -> str:
        return _("Monitor")

    def get_results(self, query: str) -> List[SearchResult]:
        return [
            SearchResult(
                title=topic_menu_item.title,
                url=topic_menu_item.url,
            )
            for topic_menu_topic in mega_menu_registry["monitoring"].topics()
            for topic_menu_item in topic_menu_topic.items
            if query.lower() in topic_menu_item.title.lower()
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


class MenuSearchResultsRenderer:
    _max_num_displayed_results = 10

    def __init__(self, search_type: str):

        # TODO: In the future, we should separate the rendering and the generation of the results
        if search_type == "monitoring":
            self._generate_results = QuicksearchManager(
                raise_too_many_rows_error=False
            ).generate_results
        elif search_type == "setup":
            self._generate_results = IndexSearcher(
                PermissionsHandler(URLChecker[ModeEditHost](ModeEditHost))
            ).search
        else:
            raise NotImplementedError(f"Renderer not implemented for type '{search_type}'")
        self.search_type = search_type

    def render(self, query: str) -> str:
        try:
            results = self._generate_results(query)
        # Don't render the IncorrectLapelInputError in Mega Menu to make the handling of
        # incorrect inputs consistent with other search querys
        except IncorrectLabelInputError:
            return ""
        except MKException as error:
            return self._render_error(error)
        return self._render_results(results)

    def _render_error(self, error: MKException) -> str:
        with output_funnel.plugged():
            html.open_div(class_="error")
            html.write_text(f"{error}")
            html.close_div()
            error_as_html = output_funnel.drain()
        return error_as_html

    def _get_icon_mapping(
        self,
        default_icons: Tuple[Icon, Icon],
    ) -> Dict[str, Tuple[Icon, Icon]]:
        # {topic: (Icon(Topic): green, Icon(Item): colorful)}
        mapping: Dict[str, Tuple[Icon, Icon]] = {}
        for menu in [
            mega_menu_registry.menu_setup(),
            mega_menu_registry.menu_monitoring(),
        ]:
            mapping[str(menu.title)] = (
                menu.icon + "_active" if isinstance(menu.icon, str) else default_icons[0],
                menu.icon if menu.icon else default_icons[1],
            )

            for topic in menu.topics():
                mapping[topic.title] = (
                    topic.icon if topic.icon else default_icons[0],
                    topic.icon if topic.icon else default_icons[1],
                )
                for item in topic.items:
                    mapping[item.title] = (
                        topic.icon if topic.icon else default_icons[0],
                        item.icon if item.icon else default_icons[1],
                    )
        for module_class in main_module_registry.values():
            module = module_class()
            if module.title not in mapping:
                mapping[module.title] = (
                    module.topic.icon_name
                    if module.topic and module.topic.icon_name
                    else default_icons[0],
                    module.icon if module.icon else default_icons[1],
                )
        return mapping

    def _render_results(
        self,
        results: SearchResultsByTopic,
    ) -> str:
        with output_funnel.plugged():
            default_icons = ("main_" + self.search_type + "_active", "main_" + self.search_type)
            icon_mapping = self._get_icon_mapping(default_icons)

            for topic, search_results in results:
                max_num_displayed_results_exceeded = (
                    len(list(search_results)) >= self._max_num_displayed_results
                )

                icons = icon_mapping.get(topic, default_icons)
                html.open_div(
                    id_=topic,
                    class_=["topic", "extendable" if max_num_displayed_results_exceeded else ""],
                )
                self._render_topic(topic, icons)
                html.open_ul()
                for count, result in enumerate(list(search_results)):
                    self._render_result(
                        result,
                        hidden=count >= self._max_num_displayed_results,
                    )

                # TODO: Remove this as soon as the index search does limit its search results
                if max_num_displayed_results_exceeded:
                    html.open_li(class_="show_all_items")
                    html.open_a(
                        href="",
                        onclick=f"cmk.search.on_click_show_all_results({json.dumps(topic)}, 'popup_menu_{self.search_type}');",
                    )
                    html.write_text(_("Show all results"))
                    html.close_a()
                    html.close_li()

                html.close_ul()
                html.close_div()
            html_text = output_funnel.drain()
        return html_text

    def _render_topic(self, topic: str, icons: Tuple[Icon, Icon]):
        html.open_h2()
        html.div(class_="spacer", content="")

        html.open_a(
            class_="show_all_topics",
            href="",
            onclick=f"cmk.search.on_click_show_all_topics({json.dumps(topic)})",
        )
        html.icon(icon="collapse_arrow", title=_("Show all topics"))
        html.close_a()

        if not user.get_attribute("icons_per_item"):
            html.icon(icons[0])
        else:
            html.icon(icons[1])
        html.span(topic)
        html.close_h2()

    def _render_result(self, result, hidden=False):
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
        html.write_text(
            result.title + (" %s" % html.render_b(result.context) if result.context else "")
        )
        html.close_a()
        html.close_li()


class MonitoringSearch(ABCMegaMenuSearch):
    """Search field in the monitoring menu"""

    def show_search_field(self) -> None:
        html.open_div(id_="mk_side_search_monitoring")
        # TODO: Implement submit action (e.g. show all results of current query)
        html.begin_form(f"mk_side_{self.name}", add_transid=False, onsubmit="return false;")
        tooltip = _(
            "Search with regular expressions for menu entries, \n"
            "hosts, services or host and service groups.\n\n"
            "You can use the following filters:\n"
            "h: Host\n"
            "s: Service\n"
            "hg: Host group\n"
            "sg: Service group\n"
            "ad: Address\n"
            "al: Alias\n"
            "tg: Host tag\n"
            "hl: Host label (e.g. hl: cmk/os_family:linux)\n"
            "sl: Service label (e.g. sl: cmk/os_family:linux)\n\n"
            "Note that for simplicity '*' will be substituted with '.*'."
        )
        html.input(
            id_=f"mk_side_search_field_{self.name}",
            type_="text",
            name="search",
            title=tooltip,
            autocomplete="off",
            placeholder=_("Search in Monitoring"),
            onkeydown="cmk.search.on_key_down('monitoring')",
            oninput="cmk.search.on_input_search('monitoring')",
        )
        html.input(
            id_=f"mk_side_search_field_clear_{self.name}",
            name="reset",
            type_="button",
            onclick="cmk.search.on_click_reset('monitoring');",
        )
        html.end_form()
        html.close_div()
        html.div("", id_="mk_side_clear")


@page_registry.register_page("ajax_search_monitoring")
class PageSearchMonitoring(AjaxPage):
    def page(self):
        query = request.get_str_input_mandatory("q")
        return MenuSearchResultsRenderer("monitoring").render(query)


class SetupSearch(ABCMegaMenuSearch):
    """Search field in the setup menu"""

    def show_search_field(self) -> None:
        html.open_div(id_="mk_side_search_setup")
        # TODO: Implement submit action (e.g. show all results of current query)
        html.begin_form(f"mk_side_{self.name}", add_transid=False, onsubmit="return false;")
        tooltip = _("Search for menu entries, settings, hosts and rulesets.")
        html.input(
            id_=f"mk_side_search_field_{self.name}",
            type_="text",
            name="search",
            title=tooltip,
            autocomplete="off",
            placeholder=_("Search in Setup"),
            onkeydown="cmk.search.on_key_down('setup')",
            oninput="cmk.search.on_input_search('setup');",
        )
        html.input(
            id_=f"mk_side_search_field_clear_{self.name}",
            name="reset",
            type_="button",
            onclick="cmk.search.on_click_reset('setup');",
        )
        html.end_form()
        html.close_div()
        html.div("", id_="mk_side_clear")


@page_registry.register_page("ajax_search_setup")
class PageSearchSetup(AjaxPage):
    def page(self):
        query = request.get_str_input_mandatory("q")
        try:
            return MenuSearchResultsRenderer("setup").render(query)
        except IndexNotFoundException:
            with output_funnel.plugged():
                html.open_div(class_="topic")
                html.open_ul()
                html.write_text(_("Currently indexing, please try again shortly."))
                html.close_ul()
                html.close_div()
                return output_funnel.drain()
