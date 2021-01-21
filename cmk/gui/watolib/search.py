#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from itertools import chain
from time import sleep
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    Final,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
)

import redis
from werkzeug.test import create_environ

from cmk.gui.background_job import BackgroundJobAlreadyRunning, BackgroundProcessInterface
from cmk.gui.config import UserContext, user
from cmk.gui.display_options import DisplayOptions
from cmk.gui.exceptions import MKAuthException
from cmk.gui.globals import RequestContext, g, request
from cmk.gui.gui_background_job import GUIBackgroundJob, job_registry
from cmk.gui.htmllib import html
from cmk.gui.http import Request
from cmk.gui.i18n import _, get_current_language, get_languages, localize
from cmk.gui.pages import get_page_handler
from cmk.gui.plugins.watolib.utils import (
    SampleConfigGenerator,
    sample_config_generator_registry,
)
from cmk.gui.type_defs import SearchQuery, SearchResult, SearchResultsByTopic
from cmk.gui.utils.urls import file_name_and_query_vars_from_url, QueryVars
from cmk.gui.watolib.utils import may_edit_ruleset
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.redis import get_redis_client
from cmk.utils.plugin_registry import Registry

if TYPE_CHECKING:
    from cmk.utils.redis import RedisDecoded

_NAME_DEFAULT_LANGUAGE = 'default'


class IndexNotFoundException(MKGeneralException):
    """Raised when trying to load a non-existing search index file or when the current language is
    missing in the search index"""


@dataclass
class MatchItem:
    title: str
    topic: str
    url: str
    match_texts: Iterable[str]

    def __post_init__(self) -> None:
        self.match_texts = [match_text.lower() for match_text in self.match_texts]


MatchItems = Iterable[MatchItem]
MatchItemsByTopic = Dict[str, MatchItems]


class ABCMatchItemGenerator(ABC):
    def __init__(self, name: str) -> None:
        self._name: Final[str] = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def generate_match_items(self) -> MatchItems:
        ...

    @staticmethod
    @abstractmethod
    def is_affected_by_change(change_action_name: str) -> bool:
        ...

    @property
    @abstractmethod
    def is_localization_dependent(self) -> bool:
        ...


class MatchItemGeneratorRegistry(Registry[ABCMatchItemGenerator]):
    def plugin_name(self, instance: ABCMatchItemGenerator) -> str:
        return instance.name


class IndexBuilder:
    _KEY_INDEX_BUILT = "si:index_built"
    PREFIX_LOCALIZATION_INDEPENDENT = "si:li"
    PREFIX_LOCALIZATION_DEPENDENT = "si:ld"

    def __init__(self, registry: MatchItemGeneratorRegistry) -> None:
        self._registry = registry
        self._all_languages = {
            name: name or _NAME_DEFAULT_LANGUAGE for language in get_languages()
            for name in [language[0]]
        }
        self._redis_client = get_redis_client()

    @staticmethod
    def add_to_prefix(prefix: str, to_add: Any) -> str:
        return f"{prefix}:{to_add}"

    @classmethod
    def key_categories(cls, prefix: str) -> str:
        return cls.add_to_prefix(prefix, "categories")

    @classmethod
    def key_match_texts(cls, prefix: str) -> str:
        return cls.add_to_prefix(prefix, "match_texts")

    def _build_index(
        self,
        names_and_generators: Iterable[ABCMatchItemGenerator],
    ) -> None:
        localization_dependent_generators = []

        with self._redis_client.pipeline() as pipeline:
            key_categories_li = self.key_categories(self.PREFIX_LOCALIZATION_INDEPENDENT)
            for match_item_generator in names_and_generators:
                if match_item_generator.is_localization_dependent:
                    localization_dependent_generators.append(match_item_generator)
                    continue
                pipeline.sadd(
                    key_categories_li,
                    match_item_generator.name,
                )
                self._add_match_items_to_redis(
                    match_item_generator,
                    pipeline,
                    self.PREFIX_LOCALIZATION_INDEPENDENT,
                )

            key_categories_ld = self.key_categories(self.PREFIX_LOCALIZATION_DEPENDENT)
            for language, language_name in self._all_languages.items():
                localize(language)
                prefix_ld = self.add_to_prefix(
                    self.PREFIX_LOCALIZATION_DEPENDENT,
                    language_name,
                )
                for match_item_generator in localization_dependent_generators:
                    pipeline.sadd(
                        key_categories_ld,
                        match_item_generator.name,
                    )
                    self._add_match_items_to_redis(
                        match_item_generator,
                        pipeline,
                        prefix_ld,
                    )

            pipeline.execute()

    @classmethod
    def _add_match_items_to_redis(
        cls,
        match_item_generator: ABCMatchItemGenerator,
        redis_pipeline: redis.client.Pipeline,
        redis_prefix: str,
    ) -> None:
        prefix = cls.add_to_prefix(redis_prefix, match_item_generator.name)
        key_match_texts = cls.key_match_texts(prefix)
        redis_pipeline.delete(key_match_texts)
        for idx, match_item in enumerate(match_item_generator.generate_match_items()):
            redis_pipeline.hset(
                key_match_texts,
                key=" ".join(match_item.match_texts),
                value=idx,
            )
            redis_pipeline.hset(  # type: ignore[call-arg]  # no idea why this is necessary...
                cls.add_to_prefix(prefix, idx),
                mapping={
                    "title": match_item.title,
                    "topic": match_item.topic,
                    "url": match_item.url,
                },
            )

    def _mark_index_as_built(self) -> None:
        self._redis_client.set(
            self._KEY_INDEX_BUILT,
            1,
        )

    def build_full_index(self) -> None:
        self._build_index(self._registry.values())
        self._mark_index_as_built()

    def build_changed_sub_indices(self, change_action_name: str) -> None:
        self._build_index(match_item_generator for match_item_generator in self._registry.values()
                          if match_item_generator.is_affected_by_change(change_action_name))

    @classmethod
    def index_is_built(cls, client: Optional['RedisDecoded'] = None) -> bool:
        return (client or get_redis_client()).exists(cls._KEY_INDEX_BUILT) == 1


class URLChecker:
    def __init__(self) -> None:
        from cmk.gui.wato.pages.hosts import ModeEditHost
        self._mode_edit_host = ModeEditHost

    @staticmethod
    def _set_query_vars(query_vars: QueryVars) -> None:
        for name, vals in query_vars.items():
            request.set_var(name, vals[0])

    @staticmethod
    def _set_current_folder(folder_name: str) -> None:
        # this attribute is set when calling cmk.gui.watolib.hosts_and_folders.Folder.all_folders
        # if it is not set now, then it will be set for sure upon the next call
        if not hasattr(g, "wato_folders"):
            return
        g.wato_current_folder = g.wato_folders[folder_name]

    def is_permitted(self, url: str) -> bool:
        file_name, query_vars = file_name_and_query_vars_from_url(url)
        self._set_query_vars(query_vars)

        is_host_url = "mode=edit_host" in url
        if is_host_url:
            self._set_current_folder(query_vars.get("folder", [""])[0])  # "" means root dir

        try:
            if is_host_url:
                self._try_host()
            else:
                self._try_page(file_name)
            return True
        except MKAuthException:
            return False

    @staticmethod
    def _try_page(file_name: str) -> None:
        page_handler = get_page_handler(file_name)
        if page_handler:
            page_handler()

    # TODO: Find a better solution here. We treat hosts separately because calling the page takes
    #  very long in this case and is not necessary (the initializer already throws an exception).
    def _try_host(self) -> None:
        self._mode_edit_host()


class PermissionsHandler:
    def __init__(self) -> None:
        self._category_permissions = {
            "global_settings": user.may("wato.global") or user.may("wato.seeall"),
            "folders": user.may("wato.hosts"),
            "hosts": user.may("wato.hosts"),
            "event_console": user.may("mkeventd.edit") or user.may("wato.seeall"),
            "event_console_settings": user.may("mkeventd.config") or user.may("wato.seeall")
        }
        self._url_checker = URLChecker()

    @staticmethod
    def _permissions_rule(url: str) -> bool:
        _, query_vars = file_name_and_query_vars_from_url(url)
        return may_edit_ruleset(query_vars['varname'][0])

    def _permissions_url(self, url: str) -> bool:
        return self._url_checker.is_permitted(url)

    def may_see_category(self, category: str) -> bool:
        return user.may("wato.use") and self._category_permissions.get(category, True)

    def permissions_for_items(self) -> Mapping[str, Callable[[str], bool]]:
        return {
            "rules": self._permissions_rule,
            "hosts": lambda url:
                     (any(user.may(perm) for perm in ("wato.all_folders", "wato.see_all_folders"))
                      or self._permissions_url(url)),
            "setup": self._permissions_url,
        }


class IndexSearcher:
    def __init__(self) -> None:
        permissions_handler = PermissionsHandler()
        self._may_see_category = permissions_handler.may_see_category
        self._may_see_item_func = permissions_handler.permissions_for_items()
        self._current_language = get_current_language() or _NAME_DEFAULT_LANGUAGE
        self._user_id = user.ident
        self._redis_client = get_redis_client()

    @contextmanager
    def _SearchContext(self) -> Iterator[None]:
        _request = Request(create_environ())
        with RequestContext(
                html_obj=html(_request),
                req=_request,
                display_options=DisplayOptions(),
        ), UserContext(self._user_id):
            yield

    def search(self, query: SearchQuery) -> SearchResultsByTopic:
        with self._SearchContext():
            results = self._search(query)
        yield from self._sort_search_results(results)

    def _search(self, query: SearchQuery) -> Mapping[str, Iterable[SearchResult]]:
        if not IndexBuilder.index_is_built(self._redis_client):
            build_index_background()
            raise IndexNotFoundException

        query_preprocessed = f"*{query.lower().replace(' ', '*')}*"
        results: DefaultDict[str, List[SearchResult]] = DefaultDict(list)

        self._search_redis(
            query_preprocessed,
            IndexBuilder.key_categories(IndexBuilder.PREFIX_LOCALIZATION_INDEPENDENT),
            IndexBuilder.PREFIX_LOCALIZATION_INDEPENDENT,
            results,
        )
        self._search_redis(
            query_preprocessed,
            IndexBuilder.key_categories(IndexBuilder.PREFIX_LOCALIZATION_DEPENDENT),
            IndexBuilder.add_to_prefix(
                IndexBuilder.PREFIX_LOCALIZATION_DEPENDENT,
                self._current_language,
            ),
            results,
        )

        return results

    def _search_redis(
        self,
        query: str,
        key_categories: str,
        key_prefix_match_items: str,
        results: DefaultDict[str, List[SearchResult]],
    ) -> None:
        for category in self._redis_client.smembers(key_categories):
            if not self._may_see_category(category):
                continue

            prefix_category = IndexBuilder.add_to_prefix(
                key_prefix_match_items,
                category,
            )
            permissions_check = self._may_see_item_func.get(category, lambda _: True)

            for _matched_text, idx_matched_item in self._redis_client.hscan_iter(
                    IndexBuilder.key_match_texts(prefix_category),
                    match=query,
            ):
                match_item_dict = self._redis_client.hgetall(
                    IndexBuilder.add_to_prefix(prefix_category, idx_matched_item))

                if not permissions_check(match_item_dict["url"]):
                    continue

                results[match_item_dict["topic"]].append(
                    SearchResult(
                        match_item_dict["title"],
                        match_item_dict["url"],
                    ))

    @classmethod
    def _sort_search_results(
        cls,
        results: Mapping[str, Iterable[SearchResult]],
    ) -> SearchResultsByTopic:
        first_topics = cls._first_topics()
        last_topics = cls._last_topics()
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
            _("Setup"),
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
            _("Event Console rule packages"),
            _("Event Console rules"),
            _("Event Console settings"),
            # _("Users"),
            _("Services") + " > " + _("Enforced services"),
            _("Global settings"),
            # _("Maintenance"),
        )


def build_index() -> None:
    IndexBuilder(match_item_generator_registry).build_full_index()


def _build_index_background(
    job_interface: BackgroundProcessInterface,
    n_attempts_redis_connection: int = 1,
) -> None:
    sleep_time = 5
    n_attempts = 0
    job_interface.send_progress_update(_("Building of search index started"))
    while True:
        try:
            n_attempts += 1
            build_index()
            break
        except redis.ConnectionError:
            job_interface.send_progress_update(
                _(f"Connection attempt {n_attempts} / {n_attempts_redis_connection} to Redis failed"
                 ))
            if n_attempts == n_attempts_redis_connection:
                job_interface.send_result_message(
                    _("Maximum number of allowed connection attempts reached, terminating"))
                raise
            job_interface.send_progress_update(_(f"Will wait for {sleep_time} seconds and retry"))
            sleep(sleep_time)
    job_interface.send_result_message(_("Search index successfully built"))


def build_index_background(n_attempts_redis_connection: int = 1) -> None:
    build_job = SearchIndexBackgroundJob()
    build_job.set_function(
        partial(
            _build_index_background,
            n_attempts_redis_connection=n_attempts_redis_connection,
        ))
    try:
        build_job.start()
    except BackgroundJobAlreadyRunning:
        pass


def _update_index_background(
    change_action_name: str,
    job_interface: BackgroundProcessInterface,
) -> None:
    job_interface.send_progress_update(_("Updating of search index started"))

    if not IndexBuilder.index_is_built():
        job_interface.send_progress_update(_("Search index not found, re-building from scratch"))
        _build_index_background(job_interface)
        return

    IndexBuilder(match_item_generator_registry).build_changed_sub_indices(change_action_name)
    job_interface.send_result_message(_("Search index successfully updated"))


def update_index_background(change_action_name: str) -> None:
    update_job = SearchIndexBackgroundJob()
    update_job.set_function(_update_index_background, change_action_name)
    try:
        update_job.start()
    except BackgroundJobAlreadyRunning:
        pass


@job_registry.register
class SearchIndexBackgroundJob(GUIBackgroundJob):
    job_prefix = "search_index"

    @classmethod
    def gui_title(cls) -> str:
        return _("Search index")

    def __init__(self) -> None:
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
        # it is possible that Redis is not yet up and running, therefore we explicitly allow
        # multiple connection attempts
        build_index_background(n_attempts_redis_connection=5)


match_item_generator_registry = MatchItemGeneratorRegistry()
