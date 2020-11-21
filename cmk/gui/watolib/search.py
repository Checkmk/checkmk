#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import chain
import pathlib
import pickle
from typing import (
    Callable,
    DefaultDict,
    Final,
    Iterable,
    Mapping,
    Sequence,
    Tuple,
)
from werkzeug.test import create_environ

from cmk.utils.paths import tmp_dir
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.plugin_registry import Registry
from cmk.gui.config import UserContext, user
from cmk.gui.background_job import BackgroundJobAlreadyRunning, BackgroundProcessInterface
from cmk.gui.exceptions import MKAuthException
from cmk.gui.globals import RequestContext
from cmk.gui.gui_background_job import GUIBackgroundJob, job_registry
from cmk.gui.htmllib import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.pages import get_page_handler
from cmk.gui.plugins.watolib.utils import (
    ConfigVariableRegistry,
    SampleConfigGenerator,
    config_variable_registry,
    sample_config_generator_registry,
)
from cmk.gui.type_defs import SearchQuery, SearchResult, SearchResultsByTopic
from cmk.gui.watolib.utils import may_edit_ruleset
from cmk.gui.utils.urls import file_name_and_query_vars_from_url, QueryVars


class IndexNotFoundException(MKGeneralException):
    """Raised when trying to load a non-existing search index file"""


@dataclass
class MatchItem:
    title: str
    topic: str
    url: str
    match_texts: Iterable[str]

    def __post_init__(self):
        self.match_texts = [match_text.lower() for match_text in self.match_texts]


MatchItems = Iterable[MatchItem]
Index = Mapping[str, Sequence[MatchItem]]


class ABCMatchItemGenerator(ABC):
    def __init__(self, name: str) -> None:
        self._name: Final[str] = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def generate_match_items(self) -> Iterable[MatchItem]:
        ...

    @abstractmethod
    def is_affected_by_change(self, change_action_name: str) -> bool:
        ...


class MatchItemGeneratorRegistry(Registry[ABCMatchItemGenerator]):
    def plugin_name(self, instance: ABCMatchItemGenerator) -> str:
        return instance.name


class IndexBuilder:
    def __init__(self, registry: MatchItemGeneratorRegistry):
        self._registry = registry

    @staticmethod
    def _build_index(names_and_generators: Iterable[Tuple[str, ABCMatchItemGenerator]]) -> Index:
        return {
            name: list(match_item_generator.generate_match_items())
            for name, match_item_generator in names_and_generators
        }

    def build_full_index(self) -> Index:
        return self._build_index(self._registry.items())

    def build_changed_sub_indices(self, change_action_name: str) -> Index:
        return self._build_index(
            ((name, match_item_generator)
             for name, match_item_generator in self._registry.items()
             if match_item_generator.is_affected_by_change(change_action_name)))


class IndexStore:
    _cached_index: Index = {}
    _cached_mtime = 0.

    def __init__(self, path: pathlib.Path) -> None:
        self._path = path
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def store_index(self, index: Index) -> None:
        with self._path.open(mode='wb') as index_file:
            pickle.dump(index, index_file)

    def load_index(self, launch_rebuild_if_missing: bool = True) -> Index:
        try:
            current_mtime = self._path.stat().st_mtime
            if self._is_cache_valid(current_mtime):
                return self._cached_index
            self.__class__._cached_index = self._load_index_from_file()
            self.__class__._cached_mtime = current_mtime
            return self._cached_index
        except FileNotFoundError:
            if launch_rebuild_if_missing:
                build_and_store_index_background()
            raise IndexNotFoundException

    def _is_cache_valid(self, current_mtime: float) -> bool:
        return bool(self._cached_index) and self._cached_mtime >= current_mtime

    def _load_index_from_file(self) -> Index:
        with self._path.open(mode="rb") as index_file:
            return pickle.load(index_file)

    def all_match_items(self) -> MatchItems:
        yield from (
            match_item for match_items in self.load_index().values() for match_item in match_items)


class URLChecker:
    def __init__(self):
        self._user_id = user.ident
        self._request = Request(create_environ())

    def _set_query_vars(self, query_vars: QueryVars) -> None:
        for name, vals in query_vars.items():
            self._request.set_var(name, vals[0])

    def is_permitted(self, url: str) -> bool:
        file_name, query_vars = file_name_and_query_vars_from_url(url)
        self._set_query_vars(query_vars)
        try:
            with RequestContext(html_obj=html(self._request), req=self._request):
                with UserContext(self._user_id):
                    page_handler = get_page_handler(file_name)
                    if page_handler:
                        page_handler()
            return True
        except MKAuthException:
            return False


class PermissionsHandler:
    def __init__(self):
        self._url_checker = URLChecker()

    @staticmethod
    def _permissions_rule(url: str) -> bool:
        _, query_vars = file_name_and_query_vars_from_url(url)
        return may_edit_ruleset(query_vars['varname'][0])

    def _permissions_host(self, url: str) -> bool:
        return self._url_checker.is_permitted(url)

    @staticmethod
    def permissions_for_topics() -> Mapping[str, bool]:
        return {
            "global_settings": user.may("wato.global"),
            "folders": user.may("wato.hosts"),
            "hosts": user.may("wato.hosts"),
        }

    def permissions_for_items(self) -> Mapping[str, Callable[[str], bool]]:
        return {
            "rules": self._permissions_rule,
            "hosts": self._permissions_host,
        }


class IndexSearcher:
    def __init__(self, index_store: IndexStore) -> None:
        self._index_store = index_store
        permissions_handler = PermissionsHandler()
        self._may_see_topic = permissions_handler.permissions_for_topics()
        self._may_see_item_func = permissions_handler.permissions_for_items()

    def search(self, query: SearchQuery) -> SearchResultsByTopic:
        query_lowercase = query.lower()
        results = DefaultDict(list)

        for topic, match_items in self._index_store.load_index().items():
            if not self._may_see_topic.get(topic, True):
                continue
            permissions_check = self._may_see_item_func.get(topic, lambda _: True)

            for match_item in match_items:
                if (any(query_lowercase in match_text for match_text in match_item.match_texts) and
                        permissions_check(match_item.url)):
                    results[match_item.topic].append(SearchResult(
                        match_item.title,
                        match_item.url,
                    ))

        yield from self._sort_search_results(results)

    def _sort_search_results(
        self,
        results: Mapping[str, Iterable[SearchResult]],
    ) -> SearchResultsByTopic:
        first_topics = self._first_topics()
        last_topics = self._last_topics()
        middle_topics = sorted(set(results.keys()) - set(first_topics) - set(last_topics))
        yield from ((
            topic,
            results[topic],
        ) for topic in chain(
            first_topics,
            middle_topics,
            last_topics,
        ) if topic in results)

    @staticmethod
    def _first_topics() -> Iterable[str]:
        # Note: this could just be a class attribute, however, due to the string concatenation,
        # this would mess up the localization
        return (
            _("Hosts"),
            _("Services") + " > " + _("Service monitoring rules"),
            _("Services") + " > " + _("Service discovery rules"),
        )

    @staticmethod
    def _last_topics() -> Iterable[str]:
        # Note: this could just be a class attribute, however, due to the string concatenation,
        # this would mess up the localization
        return (
            # _("Business Intelligence"),
            # _("Events"),
            # _("Users"),
            _("Services") + " > " + _("Enforced services"),
            _("Global settings"),
            # _("Maintenance"),
        )


def get_index_store() -> IndexStore:
    return IndexStore(pathlib.Path(tmp_dir / pathlib.Path('wato/search_index.pkl')))


def build_and_store_index() -> None:
    index_builder = IndexBuilder(match_item_generator_registry)
    index_store = get_index_store()
    index_store.store_index(index_builder.build_full_index())


def _build_and_store_index_background(job_interface: BackgroundProcessInterface) -> None:
    job_interface.send_progress_update(_("Building of search index started"))
    build_and_store_index()
    job_interface.send_result_message(_("Search index successfully built"))


def build_and_store_index_background() -> None:
    build_job = SearchIndexBackgroundJob()
    build_job.set_function(_build_and_store_index_background)
    try:
        build_job.start()
    except BackgroundJobAlreadyRunning:
        pass


def _update_and_store_index_background(
    change_action_name: str,
    job_interface: BackgroundProcessInterface,
) -> None:

    job_interface.send_progress_update(_("Updating of search index started"))

    index_builder = IndexBuilder(match_item_generator_registry)
    index_store = get_index_store()

    try:
        current_index = index_store.load_index(launch_rebuild_if_missing=False)
    except IndexNotFoundException:
        job_interface.send_progress_update(
            _("Search index file not found, re-building from scratch"))
        _build_and_store_index_background(job_interface)
        return

    index_store.store_index({
        **current_index,
        **index_builder.build_changed_sub_indices(change_action_name)
    })

    job_interface.send_result_message(_("Search index successfully updated"))


def update_and_store_index_background(change_action_name: str) -> None:
    update_job = SearchIndexBackgroundJob()
    update_job.set_function(_update_and_store_index_background, change_action_name)
    try:
        update_job.start()
    except BackgroundJobAlreadyRunning:
        pass


@job_registry.register
class SearchIndexBackgroundJob(GUIBackgroundJob):
    job_prefix = "search_index"

    @classmethod
    def gui_title(cls):
        return _("Search index")

    def __init__(self):
        last_job_status = GUIBackgroundJob(self.job_prefix).get_status()
        super().__init__(
            self.job_prefix,
            title=_("Search index"),
            stoppable=False,
            estimated_duration=last_job_status.get("duration"),
        )


@sample_config_generator_registry.register
class SampleConfigGeneratorSearchIndex(SampleConfigGenerator):
    """Initial building and storing of search index"""
    @classmethod
    def ident(cls) -> str:
        return "search_index"

    @classmethod
    def sort_index(cls) -> int:
        return 70

    def generate(self) -> None:
        build_and_store_index()


class MatchItemGeneratorGlobalSettings(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        conf_var_registry: ConfigVariableRegistry,
    ) -> None:
        super().__init__(name)
        self._config_variable_registry = conf_var_registry

    def generate_match_items(self) -> MatchItems:
        yield from (MatchItem(
            title=title,
            topic="Global settings",
            url="wato.py?mode=edit_configvar&varname=%s" % ident,
            match_texts=[title, config_var.ident()],
        ) for ident, config_var_type in self._config_variable_registry.items()
                    for config_var in [config_var_type()]
                    for title in [config_var.valuespec().title()]
                    if config_var.in_global_settings() and title)

    def is_affected_by_change(self, *_, **__) -> bool:
        return False


match_item_generator_registry = MatchItemGeneratorRegistry()

match_item_generator_registry.register(
    MatchItemGeneratorGlobalSettings(
        'global_settings',
        config_variable_registry,
    ))
