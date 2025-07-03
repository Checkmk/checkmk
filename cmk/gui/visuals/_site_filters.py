#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from functools import partial

from cmk.ccc.site import SiteId

from cmk.gui import query_filters
from cmk.gui.config import active_config, Config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _l
from cmk.gui.type_defs import Choices, FilterHTTPVariables, Row
from cmk.gui.utils.autocompleter_config import AutocompleterConfig
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import AutocompleterRegistry, DualListChoice

from .filter import Filter, FilterRegistry


def register(
    filter_registry: FilterRegistry,
    autocompleter_registry: AutocompleterRegistry,
    site_choices: Callable[[], list[tuple[str, str]]],
    site_filter_heading_info: Callable[[FilterHTTPVariables], str | None],
) -> None:
    filter_registry.register(
        SiteFilter(
            title=_l("Site"),
            sort_index=500,
            query_filter=query_filters.Query(
                ident="siteopt",
                request_vars=["site"],
            ),
            description=_l("Optional selection of a site"),
            heading_info=site_filter_heading_info,
        )
    )

    filter_registry.register(
        SiteFilter(
            title=_l("Site (enforced)"),
            sort_index=501,
            query_filter=query_filters.Query(ident="site", request_vars=["site"]),
            description=_l("Selection of site is enforced, use this filter for joining"),
            is_show_more=True,
            heading_info=site_filter_heading_info,
        )
    )

    filter_registry.register(MultipleSitesFilter(site_choices, site_filter_heading_info))

    autocompleter_registry.register_autocompleter(
        "sites", partial(sites_autocompleter, sites_options=site_choices)
    )


class SiteFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        query_filter: query_filters.Query,
        description: None | str | LazyString = None,
        is_show_more: bool = False,
        heading_info: Callable[[FilterHTTPVariables], str | None],
    ) -> None:
        super().__init__(
            ident=query_filter.ident,
            title=title,
            sort_index=sort_index,
            info="host",
            htmlvars=query_filter.request_vars,
            link_columns=[],
            description=description,
            is_show_more=is_show_more,
        )
        self.query_filter = query_filter
        self._heading_info = heading_info

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.query_filter.request_vars[0], "")
        choices = [(current_value, current_value)] if current_value else []

        html.dropdown(
            self.query_filter.request_vars[0],
            choices,
            current_value,
            style="width: 250px;",
            class_=["ajax-vals"],
            data_autocompleter=json.dumps(
                AutocompleterConfig(
                    ident="sites",
                    strict=self.query_filter.ident == "site",
                ).config
            ),
        )

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return self._heading_info(value)

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {"site": row["site"]}


def default_site_filter_heading_info(value: FilterHTTPVariables) -> str | None:
    current_value = value.get("site")
    try:
        return active_config.sites[SiteId(current_value)]["alias"] if current_value else None
    except KeyError:
        return None


class MultipleSitesFilter(SiteFilter):
    def __init__(
        self,
        site_choices: Callable[[], list[tuple[str, str]]],
        heading_info: Callable[[FilterHTTPVariables], str | None],
    ) -> None:
        super().__init__(
            title=_l("Multiple sites"),
            sort_index=502,
            query_filter=query_filters.Query(ident="sites", request_vars=["sites"]),
            description=_l("Associative selection of multiple sites"),
            heading_info=heading_info,
        )
        self._site_choices = site_choices

    def get_request_sites(self, value: FilterHTTPVariables) -> list[str]:
        return [x for x in value.get(self.htmlvars[0], "").strip().split("|") if x]

    def display(self, value: FilterHTTPVariables) -> None:
        sites_vs = DualListChoice(choices=self._site_choices(), rows=4)
        sites_vs.render_input(self.htmlvars[0], self.get_request_sites(value))


def sites_autocompleter(
    config: Config, value: str, params: dict, sites_options: Callable[[], list[tuple[str, str]]]
) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """

    choices: Choices = [v for v in sites_options() if _matches_id_or_title(value, v)]

    # This part should not exists as the optional(not enforce) would better be not having the filter at all
    if not params.get("strict"):
        empty_choice: Choices = [("", "All Sites")]
        choices = empty_choice + choices
    return choices


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()
