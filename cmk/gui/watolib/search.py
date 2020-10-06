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
    Sequence,
)

from cmk.utils.paths import omd_root
from cmk.utils.plugin_registry import Registry
from cmk.gui.type_defs import SearchQuery, SearchResult, SearchResultsByTopic


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
Index = Sequence[MatchItem]


class ABCMatchItemGenerator(ABC):
    def __init__(self, name: str) -> None:
        self._name: Final[str] = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def generate_match_items(self) -> Iterable[MatchItem]:
        ...


class MatchItemGeneratorRegistry(Registry[ABCMatchItemGenerator]):
    def plugin_name(self, instance: ABCMatchItemGenerator) -> str:
        return instance.name


class IndexBuilder:
    def __init__(self, registry: MatchItemGeneratorRegistry):
        self._registry = registry

    def build_index(self) -> Index:
        return [
            match_item for match_item_generator in self._registry.values()
            for match_item in match_item_generator.generate_match_items()
        ]


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

    def load_index(self) -> Index:
        with open(self._path, mode='rb') as index_file:
            return pickle.load(index_file)


class IndexSearcher:
    def __init__(self, index_store: IndexStore) -> None:
        self._index_store = index_store

    def search(self, query: SearchQuery) -> SearchResultsByTopic:
        query_lowercase = query.lower()
        results: Dict[str, List[SearchResult]] = {}
        for match_item in self._index_store.load_index():
            if any(query_lowercase in match_text for match_text in match_item.match_texts):
                results.setdefault(
                    match_item.topic,
                    [],
                ).append(SearchResult(
                    match_item.title,
                    match_item.url,
                ))
        return results


def get_index_store():
    return IndexStore(pathlib.Path(omd_root / pathlib.Path('tmp/check_mk/wato/search_index.pkl')))


match_item_generator_registry = MatchItemGeneratorRegistry()
