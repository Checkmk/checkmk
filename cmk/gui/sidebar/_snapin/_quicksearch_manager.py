#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import re
from collections.abc import Iterable

from cmk.ccc.exceptions import MKException
from cmk.gui.i18n import _
from cmk.gui.search.matchers import match_plugin_registry
from cmk.gui.search.quicksearch import (
    ABCLivestatusMatchPlugin,
    ABCQuicksearchConductor,
    BasicPluginQuicksearchConductor,
    FilterBehaviour,
    LivestatusQuicksearchConductor,
    sanitize_and_validate_regex,
    UrlBuilder,
    UsedFilters,
)
from cmk.gui.type_defs import SearchQuery, SearchResultsByTopic
from cmk.gui.utils.roles import UserPermissions
from cmk.web.utils.urls import HTTPVariable


class TooManyRowsError(MKException):
    pass


class SnapinQuicksearchManager:
    """Snapin-owned copy of the quicksearch orchestration layer."""

    def __init__(
        self,
        *,
        row_limit: int,
        search_order: Iterable[tuple[str, str]],
        build_url: UrlBuilder,
    ) -> None:
        self._row_limit = row_limit
        self._search_order = search_order
        self._build_url = build_url

    def generate_search_url(self, query: SearchQuery, user_permissions: UserPermissions) -> str:
        search_objects = self.determine_search_objects(query, user_permissions)

        # Hitting enter on the search field to open the search in the
        # page content area is currently only supported for livestatus
        # search plugins
        search_objects = [
            s for s in search_objects if isinstance(s, LivestatusQuicksearchConductor)
        ]

        with contextlib.suppress(TooManyRowsError):
            self.conduct_search(search_objects)

        # Generate a search page for the topmost search_object with results
        url_params: list[HTTPVariable] = []
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

        return self._build_url(url_params)

    def determine_search_objects(
        self, query: SearchQuery, user_permissions: UserPermissions
    ) -> list[ABCQuicksearchConductor]:
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
                    self._row_limit,
                )
            ]

        # No explicit filters specified by search expression. Execute the quicksearch plug-ins in
        # the order they are configured to let them answer the query.
        return [
            self._make_conductor(
                filter_name,
                {filter_name: [sanitize_and_validate_regex(query)]},
                FilterBehaviour[filter_behaviour_str.upper()],
                user_permissions,
            )
            for filter_name, filter_behaviour_str in self._search_order
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
            filter_query = current_string[offset + len(filter_type) :]
            filter_text = sanitize_and_validate_regex(filter_query).strip()
            filter_name = filter_type.strip().rstrip(":")
            used_filters.setdefault(filter_name, []).append(filter_text)
            current_string = current_string[:offset]
        return used_filters

    def _make_conductor(
        self,
        filter_name: str,
        used_filters: UsedFilters,
        filter_behaviour: FilterBehaviour,
        user_permissions: UserPermissions,
    ) -> ABCQuicksearchConductor:
        plugin = match_plugin_registry[filter_name]
        if isinstance(plugin, ABCLivestatusMatchPlugin):
            return LivestatusQuicksearchConductor(used_filters, filter_behaviour, self._row_limit)

        return BasicPluginQuicksearchConductor(
            used_filters, filter_behaviour, user_permissions, self._row_limit
        )

    def conduct_search(self, search_objects: list[ABCQuicksearchConductor]) -> None:
        """Collect the raw data from livestatus

        1. The single search objects execute the query.
        2. The number of results are counted and either limited or other filters are limited,
           depending on the configured filter behavior.
        """
        total_rows = 0

        for idx, search_object in enumerate(search_objects):
            search_object.do_query()
            total_rows += search_object.num_rows()

            if total_rows > self._row_limit:
                search_object.remove_rows_from_end(total_rows - self._row_limit)
                raise TooManyRowsError(
                    _("More than %(count)d results") % {"count": self._row_limit}
                )

            if search_object.row_limit_exceeded():
                raise TooManyRowsError(
                    _("More than %(count)d results") % {"count": self._row_limit}
                )

            if (
                search_object.num_rows() > 0
                and search_object.filter_behaviour is not FilterBehaviour.CONTINUE
            ):
                if search_object.filter_behaviour is FilterBehaviour.FINISHED_DISTINCT:
                    # Discard all data of previous filters and break
                    for i in range(idx - 1, -1, -1):
                        search_objects[i].remove_rows_from_end(self._row_limit)
                break

    def evaluate_results(
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
            for results in [search_object.create_results(self._build_url)]
            if results
        )
