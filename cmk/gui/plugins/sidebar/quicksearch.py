#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import re
import traceback
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum, unique

import livestatus

import cmk.utils.plugin_registry
from cmk.utils.exceptions import (
    MKException,
    MKGeneralException,
)

import cmk.gui.utils
import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.plugins.sidebar import SidebarSnapin, snapin_registry, PageHandlers
from cmk.gui.type_defs import ViewName, Row, Rows, HTTPVariables

SearchQuery = str
LivestatusTable = str
LivestatusColumn = str
LivestatusFilterHeaders = str
UsedFilters = Dict[str, List[str]]


@dataclass
class Result:
    """Intermediate representation of a search result"""
    text_tokens: List[Tuple[str, str]]
    url: str
    row: Row
    display_text: str


@unique
class FilterBehaviour(Enum):
    # Continue search
    CONTINUE = "continue"
    # Search finished: Only show results of this filter
    FINISHED_DISTINCT = "finished_distinct"
    # Search finished: Also show all results of previous filters
    FINISHED = "finished"


@snapin_registry.register
class QuicksearchSnapin(SidebarSnapin):
    @classmethod
    def type_name(cls):
        return "search"

    @classmethod
    def title(cls):
        return _("Quicksearch")

    @classmethod
    def description(cls):
        return _(
            "Interactive search field for direct access to hosts, services, host- and "
            "servicegroups.<br>You can use the following filters:<br> <i>h:</i> Host, <i>s:</i> Service<br> "
            "<i>hg:</i> Hostgroup, <i>sg:</i> Servicegroup<br><i>ad:</i> Address, <i>al:</i> Alias, <i>tg:</i> Hosttag"
        )

    def show(self):
        html.open_div(id_="mk_side_search",
                      class_="content_center",
                      onclick="cmk.quicksearch.close_popup();")
        html.input(id_="mk_side_search_field", type_="text", name="search", autocomplete="off")
        html.icon_button("#",
                         _("Search"),
                         "quicksearch",
                         onclick="cmk.quicksearch.on_search_click();")
        html.close_div()
        html.div('', id_="mk_side_clear")
        html.javascript("cmk.quicksearch.register_search_field('mk_side_search_field');")

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
        query = _maybe_strip(html.request.get_unicode_input('q'))
        if not query:
            return

        try:
            results = LivestatusQuicksearch(query).generate_results()
            ResultRenderer().show(results, query)

        except TooManyRowsError as e:
            html.show_warning(str(e))

        except MKException as e:
            html.show_error("%s" % e)

        except Exception:
            logger.exception("error generating quicksearch results")
            if config.debug:
                raise
            html.show_error(traceback.format_exc())

    def _page_search_open(self) -> None:
        """Generate the URL to the view that is opened when confirming the search field"""
        query = _maybe_strip(html.request.var('q'))
        if not query:
            return

        raise HTTPRedirect(LivestatusQuicksearch(query).generate_search_url())


def _to_regex(s):
    """Ensures the provided search string is a regex, does some basic conversion
    and then tries to verify it is a regex"""
    s = s.replace('*', '.*')
    cmk.gui.utils.validate_regex(s, varname=None)

    return s


class TooManyRowsError(MKException):
    pass


def _build_url(url_params: HTTPVariables) -> str:
    new_params = url_params[:]
    return html.makeuri(new_params, delvars=["q"], filename="view.py")


class LivestatusSearchConductor:
    """Handles exactly one livestatus query"""
    def __init__(self, used_filters: UsedFilters, filter_behaviour: FilterBehaviour) -> None:
        # used_filters:     {u'h': [u'heute'], u's': [u'Check_MK']}
        self._used_filters = used_filters
        self._filter_behaviour = filter_behaviour

        self._livestatus_command: str = ""  # Computed livestatus query
        self._rows: Rows = []  # Raw data from livestatus
        self._queried_livestatus_columns: List[str] = []

    @property
    def filter_behaviour(self) -> FilterBehaviour:
        return self._filter_behaviour

    def do_query(self) -> None:
        self._execute_livestatus_command()

    def num_rows(self) -> int:
        return len(self._rows)

    def remove_rows_from_end(self, num: int) -> None:
        self._rows = self._rows[:-num]

    def row_limit_exceeded(self) -> bool:
        return self._too_much_rows

    def get_match_topic(self) -> str:
        if len(self._used_filters.keys()) > 1:
            return "Multi-Filter"
        shortname = list(self._used_filters.keys())[0]
        return self._get_plugin_with_shortname(shortname).get_match_topic()

    def _get_plugin_with_shortname(self, name: str) -> "ABCLivestatusMatchPlugin":
        try:
            return match_plugin_registry[name]
        except KeyError:
            raise NotImplementedError()

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

        limit = config.quicksearch_dropdown_limit
        if len(self._rows) > limit:
            self._too_much_rows = True
            self._rows.pop()  # Remove limit+1nth element

    def _generate_livestatus_command(self) -> None:
        self._determine_livestatus_table()
        columns_to_query = set(self._get_livestatus_default_columns())
        livestatus_filter_domains: Dict[str, List[str]] = {}

        self._used_search_plugins = self._get_used_search_plugins()

        for plugin in self._used_search_plugins:
            columns_to_query.update(set(plugin.get_livestatus_columns(self._livestatus_table)))
            name = plugin.name
            livestatus_filter_domains.setdefault(name, [])
            livestatus_filter_domains[name].append(
                plugin.get_livestatus_filters(self._livestatus_table, self._used_filters))

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
            self._livestatus_table,
            " ".join(self._queried_livestatus_columns),
            "\n".join(livestatus_filters),
        )

        # Limit number of results
        limit = config.quicksearch_dropdown_limit
        self._livestatus_command += "Cache: reload\nLimit: %d\nColumnHeaders: off" % (limit + 1)

    def _get_used_search_plugins(self) -> List["ABCLivestatusMatchPlugin"]:
        return [
            plugin for plugin in match_plugin_registry.values()
            if plugin.is_used_for_table(self._livestatus_table, self._used_filters)
        ]

    def _determine_livestatus_table(self) -> None:
        """Returns the livestatus table fitting the given filters

        Available tables
        hosts / services / hostgroups / servicegroups

        {table} -> {is_included_in_table}
        Hostgroups -> Hosts -> Services
        Servicegroups -> Services
        """

        preferred_tables = []
        for shortname in self._used_filters.keys():
            plugin = self._get_plugin_with_shortname(shortname)
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
        }.get(self._livestatus_table, [])  # TODO: Is the default correct/necessary?

    def get_search_url_params(self) -> HTTPVariables:
        exact_match = self.num_rows() == 1
        target_view = self._get_target_view(exact_match=exact_match)

        url_params: HTTPVariables = [("view_name", target_view), ("filled_in", "filter")]
        for plugin in self._used_search_plugins:
            match_info = plugin.get_matches(target_view, self._rows[0] if exact_match else None,
                                            self._livestatus_table, self._used_filters, self._rows)
            if not match_info:
                continue
            _text, url_filters = match_info
            url_params.extend(url_filters)

        return url_params

    def create_results(self) -> List[Result]:
        elements: List[Result] = []

        if not self._rows:
            return elements

        target_view = self._get_target_view()

        # Feed each row to the filters and let them add additional text/url infos
        for row in self._rows:
            text_tokens: List[Tuple[str, str]] = []
            url_params: HTTPVariables = []
            skip_site = False
            for name in self._used_filters:
                plugin = self._get_plugin_with_shortname(name)

                if plugin.is_group_match():
                    skip_site = True

                match_info = plugin.get_matches(target_view, row, self._livestatus_table,
                                                self._used_filters, [])
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
                Result(
                    text_tokens=text_tokens,
                    url=_build_url(url_tokens),
                    row=row,
                    display_text="",  # Is created later by self._generate_display_texts
                ))

        return self._generate_display_texts(elements)

    def _get_target_view(self, exact_match: bool = True) -> ViewName:
        if exact_match:
            if self._livestatus_table == "hosts":
                return "host"
            if self._livestatus_table == "services":
                return "allservices"
            if self._livestatus_table == "hostgroups":
                return "hostgroup"
            if self._livestatus_table == "servicegroups":
                return "servicegroup"
        else:
            if self._livestatus_table == "hosts":
                return "searchhost"
            if self._livestatus_table == "services":
                return "searchsvc"
            if self._livestatus_table == "hostgroups":
                return "hostgroups"
            if self._livestatus_table == "servicegroups":
                return "svcgroups"

        raise NotImplementedError()

    def _generate_display_texts(self, elements: List[Result]) -> List[Result]:
        """Creates the text displayed to the user

        Analyzes all display texts and ensures that we have unique ones"""
        for element in elements:
            if self._livestatus_table == "services":
                element.display_text = element.row["description"]
            else:
                element.display_text = element.text_tokens[0][1]

        if self._element_texts_unique(elements):
            return elements

        # Some (ugly) special handling when the results are not unique
        # Whenever this happens we try to find a fitting second value

        if self._livestatus_table in ["hostgroups", "servicegroups"]:
            # Discard redundant hostgroups
            new_elements: List[Result] = []
            used_groups: Set[str] = set()
            for element in elements:
                if element.display_text in used_groups:
                    continue
                new_elements.append(element)
                used_groups.add(element.display_text)
            return new_elements

        # Add additional info to the display text
        for element in elements:
            hostname = element.row.get("host_name", element.row.get("name"))
            if "&host_regex=" not in element.url:
                element.url += "&host_regex=%s" % hostname

            for shortname, text in element.text_tokens:
                if shortname in ["h", "al"] and text not in element.display_text:
                    element.display_text += " <b>%s</b>" % text
                    break
            else:
                element.display_text += " <b>%s</b>" % hostname

        return elements

    def _element_texts_unique(self, elements: List[Result]) -> bool:
        used_texts: Set[str] = set()
        for entry in elements:
            if entry.display_text in used_texts:
                return False
            used_texts.add(entry.display_text)
        return True


class LivestatusQuicksearch:
    def __init__(self, query: SearchQuery) -> None:
        self._query: SearchQuery = query

    def generate_results(self) -> Dict[str, List[Result]]:
        search_objects = self._determine_search_objects()
        self._conduct_search(search_objects)
        return self._evaluate_results(search_objects)

    def generate_search_url(self) -> str:
        search_objects = self._determine_search_objects()

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
            url_params.extend([
                ("view_name", "allservices"),
                ("filled_in", "filter"),
                ("service_regex", self._query),
            ])

        return _build_url(url_params)

    def _determine_search_objects(self) -> List[LivestatusSearchConductor]:
        """Construct search objects from the query

        Try to find search object expressions and construct objects or
        create the search objects in the configured search order
        """
        filter_names = {"%s" % x.name for x in match_plugin_registry.values()}
        filter_regex = "|".join(filter_names)

        # Goal: "((^| )(hg|h|sg|s|al|tg|ad):)"
        regex = "((^| )(%(filter_regex)s):)" % {"filter_regex": filter_regex}
        found_filters = []
        matches = re.finditer(regex, self._query)
        for match in matches:
            found_filters.append((match.group(1), match.start()))

        search_objects: List[LivestatusSearchConductor] = []
        if found_filters:
            filter_spec: Dict[str, List[str]] = {}
            current_string = self._query
            for filter_type, offset in found_filters[-1::-1]:
                filter_text = _to_regex(current_string[offset + len(filter_type):]).strip()
                filter_name = filter_type.strip().rstrip(":")
                filter_spec.setdefault(filter_name, []).append(filter_text)
                current_string = current_string[:offset]
            search_objects.append(LivestatusSearchConductor(filter_spec, FilterBehaviour.CONTINUE))
        else:
            # No explicit filters set.
            # Use configured quicksearch search order
            for (filter_name, filter_behaviour_str) in config.quicksearch_search_order:
                filter_behaviour = FilterBehaviour[filter_behaviour_str.upper()]
                search_objects.append(
                    LivestatusSearchConductor({filter_name: [_to_regex(self._query)]},
                                              filter_behaviour))

        return search_objects

    def _conduct_search(self, search_objects: List[LivestatusSearchConductor]) -> None:
        """Collect the raw data from livestatus"""
        total_rows = 0
        for idx, search_object in enumerate(search_objects):
            search_object.do_query()
            total_rows += search_object.num_rows()

            if total_rows > config.quicksearch_dropdown_limit:
                search_object.remove_rows_from_end(total_rows - config.quicksearch_dropdown_limit)
                raise TooManyRowsError(
                    _("More than %d results") % config.quicksearch_dropdown_limit)

            if search_object.row_limit_exceeded():
                raise TooManyRowsError(
                    _("More than %d results") % config.quicksearch_dropdown_limit)

            if (search_object.num_rows() > 0 and
                    search_object.filter_behaviour is not FilterBehaviour.CONTINUE):
                if search_object.filter_behaviour is FilterBehaviour.FINISHED_DISTINCT:
                    # Discard all data of previous filters and break
                    for i in range(idx - 1, -1, -1):
                        search_objects[i].remove_rows_from_end(config.quicksearch_dropdown_limit)
                break

    def _evaluate_results(
            self, search_objects: List[LivestatusSearchConductor]) -> Dict[str, List[Result]]:
        """Generates elements out of the raw data"""
        results_by_topic: Dict[str, List[Result]] = {}
        for search_object in search_objects:
            results = search_object.create_results()
            if results:
                results_by_topic[search_object.get_match_topic()] = results
        return results_by_topic


def _maybe_strip(param: Optional[str]) -> Optional[str]:
    if param is None:
        return None
    return param.strip()


class ResultRenderer:
    """HTML rendering the matched results"""
    def show(self, results_by_topic: Dict[str, List[Result]], query: SearchQuery) -> None:
        """Renders the elements

        Show search topic if at least two search objects provide elements
        """
        show_match_topics = len(results_by_topic) > 1

        for match_topic, results in sorted(results_by_topic.items(), key=lambda x: x[0]):
            if show_match_topics:
                html.div(match_topic, class_="topic")

            for result in sorted(results, key=lambda x: x.display_text):
                html.a(result.display_text, id="result_%s" % query, href=result.url, target="main")


#.
#   .--Search Plugins------------------------------------------------------.
#   |  ____                      _       ____  _             _             |
#   | / ___|  ___  __ _ _ __ ___| |__   |  _ \| |_   _  __ _(_)_ __  ___   |
#   | \___ \ / _ \/ _` | '__/ __| '_ \  | |_) | | | | |/ _` | | '_ \/ __|  |
#   |  ___) |  __/ (_| | | | (__| | | | |  __/| | |_| | (_| | | | | \__ \  |
#   | |____/ \___|\__,_|_|  \___|_| |_| |_|   |_|\__,_|\__, |_|_| |_|___/  |
#   |                                                  |___/               |
#   +----------------------------------------------------------------------+
#   | Realize the search mechanism to find objects via livestatus          |
#   '----------------------------------------------------------------------'


class ABCLivestatusMatchPlugin(metaclass=abc.ABCMeta):
    def __init__(self, supported_livestatus_tables: List[LivestatusTable],
                 preferred_livestatus_table: LivestatusTable, name: str):
        super().__init__()
        self._name = name
        self._supported_livestatus_tables = supported_livestatus_tables
        self._preferred_livestatus_table = preferred_livestatus_table

    @property
    def name(self) -> str:
        return self._name

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
    def get_match_topic(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_livestatus_filters(self, livestatus_table: LivestatusTable,
                               used_filters: UsedFilters) -> LivestatusFilterHeaders:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_matches(self, for_view: ViewName, row: Optional[Row], livestatus_table: LivestatusTable,
                    used_filters: UsedFilters, rows: Rows):
        raise NotImplementedError()

    def is_group_match(self) -> bool:
        return False

    def _create_textfilter_regex(self, used_filters: UsedFilters) -> str:
        patterns = used_filters[self.name]
        if len(patterns) > 1:
            return "(%s)" % "|".join(patterns)
        return patterns[0]


class MatchPluginRegistry(cmk.utils.plugin_registry.Registry[ABCLivestatusMatchPlugin]):
    def plugin_name(self, instance):
        return instance.name


match_plugin_registry = MatchPluginRegistry()


class GroupMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self, group_type: str, name: str):
        super(GroupMatchPlugin, self).__init__(
            ["%sgroups" % group_type, "%ss" % group_type, "services"],
            "%sgroups" % group_type,
            name,
        )
        self._group_type = group_type

    def is_group_match(self) -> bool:
        return True

    def get_match_topic(self) -> str:
        if self._group_type == "host":
            return _("Hostgroup")
        return _("Servicegroup")

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
        if livestatus_table == "%sgroups" % self._group_type:
            return ["name"]
        return ["%s_groups" % self._group_type]

    def get_livestatus_filters(self, livestatus_table: LivestatusTable,
                               used_filters: UsedFilters) -> LivestatusFilterHeaders:
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

    def get_matches(self, for_view: ViewName, row: Optional[Row], livestatus_table: LivestatusTable,
                    used_filters: UsedFilters, rows: Rows):
        supported_views = {
            # View name    url fieldname,                  key in row
            # Group domains (hostgroups, servicegroups)
            "hostgroup": ["hostgroup", "name"],
            "hostgroups": ["hostgroup_regex", "name"],
            "servicegroup": ["servicegroup", "name"],
            "svcgroups": ["servicegroup_regex", "name"],

            # Host/Service domain (hosts, services)
            "allservices": ["%sgroups" % self._group_type,
                            "%s_groups" % self._group_type],
            "searchsvc": [
                "%sgroups" % self._group_type, self._group_type == "service" and "groups" or
                "host_groups"
            ],
            "searchhost": [
                "%sgroups" % self._group_type, self._group_type == "service" and "groups" or
                "host_groups"
            ]
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return

        filter_name, row_fieldname = view_info
        if row:
            value = row.get(row_fieldname)
        else:
            value = used_filters.get(self.name)

        if isinstance(value, list):
            value = "|".join(value)

        return value, [(filter_name, value)]


match_plugin_registry.register(GroupMatchPlugin(
    group_type="service",
    name="sg",
))

match_plugin_registry.register(GroupMatchPlugin(
    group_type="host",
    name="hg",
))


class ServiceMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self):
        super(ServiceMatchPlugin, self).__init__(["services"], "services", "s")

    def get_match_topic(self) -> str:
        return _("Service Description")

    def get_livestatus_columns(self, livestatus_table: LivestatusTable) -> List[LivestatusColumn]:
        return ["service_description"]

    def get_livestatus_filters(self, livestatus_table: LivestatusTable,
                               used_filters: UsedFilters) -> LivestatusFilterHeaders:
        filter_lines = []
        for entry in used_filters.get(self.name, []):
            filter_lines.append("Filter: service_description ~~ %s" % entry)

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view: ViewName, row: Optional[Row], livestatus_table: LivestatusTable,
                    used_filters: UsedFilters, rows: Rows):
        supported_views = ["allservices", "searchsvc"]
        if for_view not in supported_views:
            return

        if row:
            field_value = row.get("description")
            search_key = "service"
        else:
            field_value = self._create_textfilter_regex(used_filters)
            search_key = "service_regex"

        return field_value, [(search_key, field_value)]


match_plugin_registry.register(ServiceMatchPlugin())


class HostMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self, livestatus_field, name):
        super(HostMatchPlugin, self).__init__(["hosts", "services"], "hosts", name)
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

    def get_livestatus_filters(self, livestatus_table: LivestatusTable,
                               used_filters: UsedFilters) -> LivestatusFilterHeaders:
        filter_lines = []
        for entry in used_filters.get(self.name, []):
            filter_lines.append("Filter: %s ~~ %s" %
                                (self._get_real_fieldname(livestatus_table), entry))

        if len(filter_lines) > 1:
            filter_lines.append("Or: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view: ViewName, row: Optional[Row], livestatus_table: LivestatusTable,
                    used_filters: UsedFilters, rows: Rows):
        supported_views = {
            # View name     Filter name
            # Exact matches (always uses hostname as filter)
            "host": {
                "name": "host",
                "address": "host",
                "alias": "host"
            },
            "allservices": {
                "name": "host_regex",
                "address": "host_regex",
                "alias": "host_regex"
            },
            # Multi matches
            "searchhost": {
                "name": "host_regex",
                "address": "host_address",
                "alias": "hostalias"
            },
            "searchsvc": {
                "name": "host_regex",
                "address": "host_address",
                "alias": "hostalias"
            }
        }

        view_info = supported_views.get(for_view)
        if not view_info:
            return

        filter_name = view_info.get(self._livestatus_field)

        if row:
            field_value = row.get(self._get_real_fieldname(livestatus_table))
            hostname = row.get("host_name", row.get("name"))
            url_info = [(filter_name, hostname)]
        else:
            field_value = self._create_textfilter_regex(used_filters)
            url_info = [(filter_name, field_value)]
            if self._livestatus_field == "address":
                url_info.append(("host_address_prefix", "yes"))

        return field_value, url_info


match_plugin_registry.register(HostMatchPlugin(
    livestatus_field="name",
    name="h",
))

match_plugin_registry.register(HostMatchPlugin(
    livestatus_field="alias",
    name="al",
))

match_plugin_registry.register(HostMatchPlugin(
    livestatus_field="address",
    name="ad",
))


class HosttagMatchPlugin(ABCLivestatusMatchPlugin):
    def __init__(self):
        super(HosttagMatchPlugin, self).__init__(["hosts", "services"], "hosts", "tg")

    def _get_hosttag_dict(self):
        lookup_dict = {}
        for tag_group in config.tags.tag_groups:
            for grouped_tag in tag_group.tags:
                lookup_dict[grouped_tag.id] = tag_group.id
        return lookup_dict

    def _get_auxtag_dict(self):
        lookup_dict = {}
        for tag_id in config.tags.aux_tag_list.get_tag_ids():
            lookup_dict[tag_id] = tag_id
        return lookup_dict

    def get_match_topic(self) -> str:
        return _("Hosttag")

    def get_livestatus_columns(self, livestatus_table):
        return ["tags"]

    def get_livestatus_filters(self, livestatus_table: LivestatusTable,
                               used_filters: UsedFilters) -> LivestatusFilterHeaders:
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
            filter_lines.append("Filter: tags = %s %s" %
                                (livestatus.lqencode(tag_key), livestatus.lqencode(tag_value)))

        if len(filter_lines) > 1:
            filter_lines.append("And: %d" % len(filter_lines))

        return "\n".join(filter_lines)

    def get_matches(self, for_view: ViewName, row: Optional[Row], livestatus_table: LivestatusTable,
                    used_filters: UsedFilters, rows: Rows):
        supported_views = {"searchhost": "host_regex", "host": "host"}

        filter_name = supported_views.get(for_view)
        if not filter_name:
            return

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
