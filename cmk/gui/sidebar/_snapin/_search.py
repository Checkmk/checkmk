#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import traceback

import livestatus

from cmk.ccc.exceptions import MKException, MKGeneralException
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.search import (
    ABCQuicksearchConductor,
    IncorrectLabelInputError,
    QuicksearchManager,
    TooManyRowsError,
)
from cmk.gui.type_defs import (
    SearchQuery,
    SearchResultsByTopic,
)

from ._base import PageHandlers, SidebarSnapin


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

        # I added MKGeneralException during a refactoring, but I did not check if it is needed.
        except (MKException, MKGeneralException) as e:
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
