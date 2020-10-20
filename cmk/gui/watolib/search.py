#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pathlib
import pickle
from typing import (
    Dict,
    Final,
    Iterable,
    List,
    Mapping,
    Sequence,
    Tuple,
)

from cmk.utils.paths import omd_root
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.plugin_registry import Registry
from cmk.gui.background_job import BackgroundJobAlreadyRunning, BackgroundProcessInterface
from cmk.gui.gui_background_job import GUIBackgroundJob, job_registry
from cmk.gui.i18n import _
from cmk.gui.type_defs import SearchQuery, SearchResult, SearchResultsByTopic
from cmk.gui.plugins.watolib.utils import SampleConfigGenerator, sample_config_generator_registry


class IndexNotFoundException(MKGeneralException):
    """Raised when trying to load a non-existing search index file"""


@dataclass
class MatchItem:
    title: str
    topic: str
    url: str
    permissions: None = None
    contact_group: None = None
    match_texts: Iterable[str] = field(default_factory=list)

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
    def __init__(self, path: pathlib.Path) -> None:
        self._path = path
        self._path.parent.mkdir(
            # TODO: permissions?
            # mode=
            parents=True,
            exist_ok=True,
        )

    def store_index(self, index: Index) -> None:
        with open(self._path, mode='wb') as index_file:
            pickle.dump(index, index_file)

    def load_index(self, launch_rebuild_if_missing: bool = True) -> Index:
        try:
            with open(self._path, mode='rb') as index_file:
                return pickle.load(index_file)
        except FileNotFoundError:
            if launch_rebuild_if_missing:
                build_and_store_index_background()
            raise IndexNotFoundException

    def all_match_items(self) -> MatchItems:
        yield from (
            match_item for match_items in self.load_index().values() for match_item in match_items)


class IndexSearcher:
    def __init__(self, index_store: IndexStore) -> None:
        self._index_store = index_store

    def search(self, query: SearchQuery) -> SearchResultsByTopic:
        query_lowercase = query.lower()
        results: Dict[str, List[SearchResult]] = {}
        for match_item in self._index_store.all_match_items():
            if any(query_lowercase in match_text for match_text in match_item.match_texts):
                results.setdefault(
                    match_item.topic,
                    [],
                ).append(SearchResult(
                    match_item.title,
                    match_item.url,
                ))
        return results


def get_index_store() -> IndexStore:
    return IndexStore(pathlib.Path(omd_root / pathlib.Path('tmp/check_mk/wato/search_index.pkl')))


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


match_item_generator_registry = MatchItemGeneratorRegistry()
