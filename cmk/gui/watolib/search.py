#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass
from itertools import chain
from typing import Final

import redis
from redis import ConnectionError as RedisConnectionError

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.version import Edition, edition

from cmk.utils import paths
from cmk.utils.redis import get_redis_client, redis_enabled, redis_server_reachable
from cmk.utils.setup_search_index import (
    read_and_remove_update_requests,
    UpdateRequests,
    updates_requested,
)

from cmk.gui.background_job import BackgroundJob, BackgroundProcessInterface, InitialStatusArgs
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKAuthException
from cmk.gui.global_config import get_global_config
from cmk.gui.http import request
from cmk.gui.i18n import (
    _,
    get_current_language,
    get_languages,
    localize,
    translate_to_current_language,
)
from cmk.gui.logged_in import user
from cmk.gui.pages import get_page_handler
from cmk.gui.session import SuperUserContext
from cmk.gui.type_defs import SearchQuery, SearchResult, SearchResultsByTopic
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import file_name_and_query_vars_from_url, QueryVars
from cmk.gui.watolib.mode_permissions import mode_permissions_ensurance_registry
from cmk.gui.watolib.utils import may_edit_ruleset


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
MatchItemsByTopic = dict[str, MatchItems]


class ABCMatchItemGenerator(ABC):
    def __init__(self, name: str) -> None:
        self.name: Final[str] = name

    def __hash__(self) -> int:
        return hash(self.name)

    @abstractmethod
    def generate_match_items(self) -> MatchItems: ...

    @staticmethod
    @abstractmethod
    def is_affected_by_change(change_action_name: str) -> bool: ...

    @property
    @abstractmethod
    def is_localization_dependent(self) -> bool: ...


class MatchItemGeneratorRegistry(Registry[ABCMatchItemGenerator]):
    def plugin_name(self, instance: ABCMatchItemGenerator) -> str:
        return instance.name


match_item_generator_registry = MatchItemGeneratorRegistry()


class IndexBuilder:
    _KEY_INDEX_BUILT = "si:index_built"
    PREFIX_LOCALIZATION_INDEPENDENT = "si:li"
    PREFIX_LOCALIZATION_DEPENDENT = "si:ld"

    def __init__(
        self,
        registry: MatchItemGeneratorRegistry,
        redis_client: redis.Redis[str],
    ) -> None:
        self._registry = registry
        self._redis_client = redis_client

    @staticmethod
    def add_to_prefix(prefix: str, to_add: object) -> str:
        return f"{prefix}:{to_add}"

    @classmethod
    def key_categories(cls, prefix: str) -> str:
        return cls.add_to_prefix(prefix, "categories")

    @classmethod
    def key_match_texts(cls, prefix: str) -> str:
        return cls.add_to_prefix(prefix, "match_texts")

    def _build_index(
        self,
        match_item_generators: Iterable[ABCMatchItemGenerator],
    ) -> None:
        with SuperUserContext():
            self._do_build_index(match_item_generators)

    def _do_build_index(
        self,
        match_item_generators: Iterable[ABCMatchItemGenerator],
    ) -> None:
        current_language = get_current_language()

        with self._redis_client.pipeline() as pipeline:
            self._add_language_independent_item_generators_to_redis(
                iter(  # to make pylint happy
                    filter(
                        lambda match_item_gen: not match_item_gen.is_localization_dependent,
                        match_item_generators,
                    )
                ),
                pipeline,
            )
            self._add_language_dependent_item_generators_to_redis(
                list(
                    filter(
                        lambda match_item_gen: match_item_gen.is_localization_dependent,
                        match_item_generators,
                    )
                ),
                pipeline,
            )
            pipeline.execute()

        localize(current_language)

    @classmethod
    def _add_language_independent_item_generators_to_redis(
        cls,
        match_item_generators: Iterable[ABCMatchItemGenerator],
        redis_pipeline: redis.client.Pipeline,
    ) -> None:
        key_categories_li = cls.key_categories(cls.PREFIX_LOCALIZATION_INDEPENDENT)
        for match_item_generator in match_item_generators:
            cls._add_match_item_generator_to_redis(
                match_item_generator,
                redis_pipeline,
                key_categories_li,
                cls.PREFIX_LOCALIZATION_INDEPENDENT,
            )

    def _add_language_dependent_item_generators_to_redis(
        self,
        match_item_generators: Collection[ABCMatchItemGenerator],
        redis_pipeline: redis.client.Pipeline,
    ) -> None:
        key_categories_ld = self.key_categories(self.PREFIX_LOCALIZATION_DEPENDENT)
        for language_code, _language_name in get_languages():
            localize(language_code)
            for match_item_generator in match_item_generators:
                self._add_match_item_generator_to_redis(
                    match_item_generator,
                    redis_pipeline,
                    key_categories_ld,
                    self.add_to_prefix(
                        self.PREFIX_LOCALIZATION_DEPENDENT,
                        language_code,
                    ),
                )

    @classmethod
    def _add_match_item_generator_to_redis(
        cls,
        match_item_generator: ABCMatchItemGenerator,
        redis_pipeline: redis.client.Pipeline,
        category_key: str,
        prefix: str,
    ) -> None:
        redis_pipeline.sadd(
            category_key,
            match_item_generator.name,
        )
        cls._add_match_items_to_redis(
            match_item_generator,
            redis_pipeline,
            prefix,
        )

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
            redis_pipeline.hset(
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

    def build_changed_sub_indices(self, change_action_names: Collection[str]) -> None:
        self._build_index(
            {
                match_item_generator
                for change_action_name in change_action_names
                for match_item_generator in self._registry.values()
                if match_item_generator.is_affected_by_change(change_action_name)
            }
        )

    @classmethod
    def index_is_built(cls, client: redis.Redis[str]) -> bool:
        return client.exists(cls._KEY_INDEX_BUILT) == 1


def _set_query_vars(query_vars: QueryVars) -> None:
    for name, vals in query_vars.items():
        request.set_var(name, vals[0])


def _set_current_folder(folder_name: str) -> None:
    # this attribute is set when calling cmk.gui.watolib.hosts_and_folders.Folder.all_folders
    # if it is not set now, then it will be set for sure upon the next call
    if not hasattr(g, "wato_folders"):
        return
    g.wato_current_folder = g.wato_folders[folder_name]


def is_url_permitted(url: str) -> bool:
    file_name, query_vars = file_name_and_query_vars_from_url(url)
    _set_query_vars(query_vars)

    mode = modes[0] if (modes := query_vars.get("mode", [])) else None

    if mode == "edit_host":
        _set_current_folder(query_vars.get("folder", [""])[0])  # "" means root dir

    try:
        if mode:
            mode_permissions_ensurance_registry[mode]().ensure_permissions()
        else:
            _try_page(file_name)
        return True
    except MKAuthException:
        return False


def _try_page(file_name: str) -> None:
    page_handler = get_page_handler(file_name)
    if page_handler:
        with output_funnel.plugged():
            page_handler()
            output_funnel.drain()


class PermissionsHandler:
    def __init__(self) -> None:
        self._category_permissions = {
            "global_settings": user.may("wato.global") or user.may("wato.seeall"),
            "folders": user.may("wato.hosts"),
            "hosts": user.may("wato.hosts"),
            "event_console": user.may("mkeventd.edit") or user.may("wato.seeall"),
            "event_console_settings": user.may("mkeventd.config") or user.may("wato.seeall"),
            "logfile_pattern_analyzer": user.may("wato.pattern_editor") or user.may("wato.seeall"),
            "notification_parameter": user.may("wato.notifications") or user.may("wato.seeall"),
        }

    @staticmethod
    def _permissions_rule(url: str) -> bool:
        _, query_vars = file_name_and_query_vars_from_url(url)
        return may_edit_ruleset(query_vars["varname"][0])

    def may_see_category(self, category: str) -> bool:
        return user.may("wato.use") and self._category_permissions.get(category, True)

    @staticmethod
    def _permission_global_setting(url: str) -> bool:
        if edition(paths.omd_root) is not Edition.CSE:
            return True
        _, query_vars = file_name_and_query_vars_from_url(url)
        return get_global_config().global_settings.is_activated(query_vars["varname"][0])

    def permissions_for_items(self) -> Mapping[str, Callable[[str], bool]]:
        return {
            "global_settings": self._permission_global_setting,
            "rules": self._permissions_rule,
            "hosts": lambda url: (
                any(user.may(perm) for perm in ("wato.all_folders", "wato.see_all_folders"))
                or is_url_permitted(url)
            ),
            "setup": is_url_permitted,
        }


class IndexSearcher:
    def __init__(
        self,
        redis_client: redis.Redis[str],
        permissions_handler: PermissionsHandler,
    ) -> None:
        self._redis_client = redis_client
        if not redis_server_reachable(self._redis_client):
            raise RuntimeError("Redis server is not reachable")
        self._may_see_category = permissions_handler.may_see_category
        self._may_see_item_func = permissions_handler.permissions_for_items()
        self._user_id = user.ident

    def search(self, query: SearchQuery) -> SearchResultsByTopic:
        """
        Sorted search results restricted according to the permissions of the current user.

        The permissions check for the individual results is explicitly separated from the actual
        search in Redis. Searching in Redis and sorting the results by topic is fast. Checking the
        permissions can be quite slow, so we do this step at the very end in a generator function.
        This way, the code which displays the results can request as many results as it wants to
        render only, thus avoiding checking the permissions for all found results.
        """
        yield from self._filter_results_by_user_permissions(
            self._sort_search_results(self._search_redis(query))
        )

    def _search_redis(
        self, query: SearchQuery
    ) -> dict[str, list[_SearchResultWithPermissionsCheck]]:
        if not IndexBuilder.index_is_built(self._redis_client):
            self._launch_index_building_in_background_job()
            raise IndexNotFoundException

        query_preprocessed = f"*{query.lower().replace(' ', '*')}*"

        results_localization_independent = self._search_redis_categories(
            query=query_preprocessed,
            key_categories=IndexBuilder.key_categories(
                IndexBuilder.PREFIX_LOCALIZATION_INDEPENDENT
            ),
            key_prefix_match_items=IndexBuilder.PREFIX_LOCALIZATION_INDEPENDENT,
        )
        results_localization_dependent = self._search_redis_categories(
            query=query_preprocessed,
            key_categories=IndexBuilder.key_categories(IndexBuilder.PREFIX_LOCALIZATION_DEPENDENT),
            key_prefix_match_items=IndexBuilder.add_to_prefix(
                IndexBuilder.PREFIX_LOCALIZATION_DEPENDENT,
                get_current_language(),
            ),
        )

        return {
            topic: [
                *results_localization_independent[topic],
                *results_localization_dependent[topic],
            ]
            for topic in chain(results_localization_independent, results_localization_dependent)
        }

    def _launch_index_building_in_background_job(self) -> None:
        build_job = SearchIndexBackgroundJob()
        build_job.start(
            _index_building_in_background_job,
            # We deliberately do not provide an estimated duration here, since that involves I/O.
            # We need to be as fast as possible here, since this is done at the end of HTTP
            # requests.
            InitialStatusArgs(
                title=_("Search index"),
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )

    def _search_redis_categories(
        self,
        *,
        query: str,
        key_categories: str,
        key_prefix_match_items: str,
    ) -> defaultdict[str, list[_SearchResultWithPermissionsCheck]]:
        results = defaultdict(list)
        for category in self._redis_client.smembers(key_categories):
            if not self._may_see_category(category):
                continue

            prefix_category = IndexBuilder.add_to_prefix(
                key_prefix_match_items,
                category,
            )
            permissions_check = self._may_see_item_func.get(category, lambda _url: True)

            for _matched_text, idx_matched_item in self._redis_client.hscan_iter(
                IndexBuilder.key_match_texts(prefix_category),
                match=query,
            ):
                match_item_dict = self._redis_client.hgetall(
                    IndexBuilder.add_to_prefix(prefix_category, idx_matched_item)
                )

                # We translate the topics of our search results. For localization-dependent search
                # results, such as rulesets, they are already localized anyway. However, for
                # localization-independent results, such as hosts, they are not. For example,
                # "Hosts" in French is "Hôtes". Without this call to translate_to_current_language,
                # found hosts would be displayed under the topic "Hosts" instead of "Hôtes" in the
                # setup search.
                results[translate_to_current_language(match_item_dict["topic"])].append(
                    _SearchResultWithPermissionsCheck(
                        SearchResult(
                            match_item_dict["title"],
                            match_item_dict["url"],
                        ),
                        permissions_check,
                    )
                )
        return results

    @classmethod
    def _sort_search_results(
        cls,
        results: Mapping[str, Iterable[_SearchResultWithPermissionsCheck]],
    ) -> Iterator[tuple[str, Iterable[_SearchResultWithPermissionsCheck]]]:
        first_topics = cls._first_topics()
        last_topics = cls._last_topics()
        middle_topics = sorted(set(results.keys()) - set(first_topics) - set(last_topics))
        yield from (
            (
                topic,
                results[topic],
            )
            for topic in chain(
                first_topics,
                middle_topics,
                last_topics,
            )
            if topic in results
        )

    @staticmethod
    def _first_topics() -> Iterable[str]:
        # This is not a class attribute because it could mess up the localization if e.g.
        # string concatenation is used
        return (
            _("Setup"),
            _("Hosts"),
            _("VM, Cloud, Container"),
            _("Other integrations"),
            _("Service monitoring rules"),
            _("Service discovery rules"),
        )

    @staticmethod
    def _last_topics() -> Iterable[str]:
        # This is not a class attribute because it could mess up the localization if e.g.
        # string concatenation is used
        return (
            # _("Business Intelligence"),
            _("Event Console rule packs"),
            _("Event Console rules"),
            _("Event Console settings"),
            _("Notification parameter"),
            # _("Users"),
            _("Enforced services"),
            _("Global settings"),
            _("Miscellaneous"),
            _("Deprecated rulesets"),
            # _("Maintenance"),
        )

    @staticmethod
    def _filter_results_by_user_permissions(
        results_by_topic: Iterable[tuple[str, Iterable[_SearchResultWithPermissionsCheck]]],
    ) -> SearchResultsByTopic:
        yield from (
            (
                topic,
                (
                    result.result
                    for result in results
                    if result.permissions_check(result.result.url)
                ),
            )
            for topic, results in results_by_topic
        )


@dataclass(frozen=True)
class _SearchResultWithPermissionsCheck:
    result: SearchResult
    permissions_check: Callable[[str], bool]


def _index_building_in_background_job(job_interface: BackgroundProcessInterface) -> None:
    with job_interface.gui_context():
        _build_index(job_interface, get_redis_client())


def _build_index(job_interface: BackgroundProcessInterface, redis_client: redis.Redis[str]) -> None:
    job_interface.send_progress_update(_("Building of search index started"))
    IndexBuilder(match_item_generator_registry, redis_client).build_full_index()
    job_interface.send_result_message(_("Search index successfully built"))


def launch_requests_processing_background() -> None:
    if not updates_requested() or not redis_enabled():
        return
    job = SearchIndexBackgroundJob()
    job.start(
        _process_update_requests_background,
        # We deliberately do not provide an estimated duration here, since that involves I/O.
        # We need to be as fast as possible here, since this is done at the end of HTTP
        # requests.
        InitialStatusArgs(
            title=_("Search index"),
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )


def _process_update_requests_background(job_interface: BackgroundProcessInterface) -> None:
    with job_interface.gui_context():
        redis_client = get_redis_client()
        if not redis_server_reachable(redis_client):
            job_interface.send_progress_update(_("Redis is not reachable, terminating"))
            return

        try:
            while updates_requested():
                _process_update_requests(
                    read_and_remove_update_requests(),
                    job_interface,
                    redis_client,
                )
        except RedisConnectionError as e:
            # This can happen when Redis or the whole site is stopped while the background job is
            # running. Report an error in the background job result but don't create a crash report.
            job_interface.send_exception(_("An connection error occurred: %s") % e)


def _process_update_requests(
    requests: UpdateRequests,
    job_interface: BackgroundProcessInterface,
    redis_client: redis.Redis[str],
) -> None:
    if requests["rebuild"]:
        _build_index(job_interface, redis_client)
        return

    if not IndexBuilder.index_is_built(redis_client):
        job_interface.send_progress_update(_("Search index not found, re-building from scratch"))
        _build_index(job_interface, redis_client)
        return

    job_interface.send_progress_update(_("Updating of search index started"))
    IndexBuilder(match_item_generator_registry, redis_client).build_changed_sub_indices(
        requests["change_actions"]
    )
    job_interface.send_result_message(_("Search index successfully updated"))


class SearchIndexBackgroundJob(BackgroundJob):
    job_prefix = "search_index"

    @classmethod
    def gui_title(cls) -> str:
        return _("Search index")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)
