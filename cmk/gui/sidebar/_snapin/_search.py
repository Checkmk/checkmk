#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import abc
import itertools
import json
import traceback
from collections.abc import Iterable
from typing import cast, Final, get_args, Literal, override, TypeVar

import livestatus

from cmk.ccc.exceptions import MKException

from cmk.utils.redis import get_redis_client

from cmk.gui.config import active_config, Config
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.type_defs import (
    Icon,
    Provider,
    SearchQuery,
    SearchResult,
    SearchResultsByTopic,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.search import (
    ABCQuicksearchConductor,
    IncorrectLabelInputError,
    IndexNotFoundException,
    IndexSearcher,
    MonitoringSearchEngine,
    PermissionsHandler,
    QuicksearchManager,
    SetupSearchEngine,
    TooManyRowsError,
    UnifiedSearch,
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


class PageUnifiedSearch(AjaxPage):
    @override
    def handle_page(self, config: Config) -> None:
        super().handle_page(config)

    @override
    def page(self, config: Config) -> PageResult:
        query = request.get_str_input_mandatory("q")
        provider = self._parse_provider_query_param()

        setup_engine = SetupSearchEngine()
        monitoring_engine = MonitoringSearchEngine()
        unified_search_engine = UnifiedSearch(setup_engine, monitoring_engine)

        response = unified_search_engine.search(query, provider, config)

        return {
            "url": request.url,
            "query": query,
            "counts": response.counts.serialize(),
            "results": [result.serialize() for result in response.results],
        }

    def _parse_provider_query_param(self) -> Provider | None:
        if (provider := request.get_str_input("provider")) is None:
            return None

        return cast(Provider, provider) if provider in get_args(Provider) else None
