#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from copy import deepcopy
from pathlib import Path
import pytest
from cmk.gui.type_defs import SearchResult
from cmk.gui.watolib import (
    hosts_and_folders,
    search,
)
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    Index,
    IndexBuilder,
    IndexNotFoundException,
    IndexSearcher,
    IndexStore,
    MatchItem,
    MatchItems,
    MatchItemGeneratorRegistry,
    PermissionsHandler,
    URLChecker,
)
from cmk.utils.paths import tmp_dir


@pytest.fixture(scope="function", autouse=True)
def get_languages(monkeypatch):
    monkeypatch.setattr(
        search,
        "get_languages",
        lambda: [[""], ["de"]],
    )


def test_match_item():
    assert MatchItem(
        "1",
        "2",
        "3",
        ["ABC", "Some text", "df"],
    ).match_texts == ["abc", "some text", "df"]


class TestIndex:
    def test_update_localization_dependent(self):
        current_idx = Index(localization_independent={
            "topic 1": [MatchItem("1", "2", "3", ["4"])],
        },)
        current_idx_copy = deepcopy(current_idx)
        newer_idx = Index(localization_independent={"topic 3": []},)
        current_idx.update(newer_idx)
        assert (current_idx.localization_independent["topic 1"] ==
                current_idx_copy.localization_independent["topic 1"])
        assert (current_idx.localization_independent["topic 3"] ==
                newer_idx.localization_independent["topic 3"])

    def test_update_localization_independent(self):
        current_idx = Index(localization_dependent={
            "de": {
                "topic 2": [MatchItem("De", "2", "3", ["de"])]
            },
            "en": {
                "topic 2": [MatchItem("En", "2", "3", ["en"])]
            },
        },)
        current_idx_copy = deepcopy(current_idx)
        newer_idx = Index(localization_dependent={
            "de": {
                "topic 2": [MatchItem("De-Neu", "2", "3", ["de-neu"])]
            },
            "ro": {
                "topic 2": [MatchItem("Ro-Nou", "2", "3", ["ro-nou"])]
            },
        },)
        current_idx.update(newer_idx)
        assert current_idx.localization_dependent["en"] == current_idx_copy.localization_dependent[
            "en"]
        assert current_idx.localization_dependent["de"] == newer_idx.localization_dependent["de"]
        assert current_idx.localization_dependent["ro"] == newer_idx.localization_dependent["ro"]


class MatchItemGeneratorLocDep(ABCMatchItemGenerator):
    match_item = MatchItem(
        title="localization_dependent",
        topic="Localization-dependent",
        url="",
        match_texts=["localization_dependent"],
    )

    @property
    def name(self) -> str:
        return "localization_dependent"

    def generate_match_items(self) -> MatchItems:
        yield self.match_item

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True


class MatchItemGeneratorChangeDep(ABCMatchItemGenerator):
    match_item = MatchItem(
        title="change_dependent",
        topic="Change-dependent",
        url="",
        match_texts=["change_dependent"],
    )

    @property
    def name(self) -> str:
        return "change_dependent"

    def generate_match_items(self) -> MatchItems:
        yield self.match_item

    @staticmethod
    def is_affected_by_change(change_action_name: str) -> bool:
        return "change_dependent" in change_action_name

    @property
    def is_localization_dependent(self) -> bool:
        return False


@pytest.fixture(name="match_item_generator_registry")
def fixture_match_item_generator_registry():
    match_item_generator_registry = MatchItemGeneratorRegistry()
    match_item_generator_registry.register(MatchItemGeneratorLocDep("localization_dependent"))
    match_item_generator_registry.register(MatchItemGeneratorChangeDep("change_dependent"))
    return match_item_generator_registry


@pytest.fixture(name="index_builder")
def fixture_index_builder(match_item_generator_registry):
    return IndexBuilder(match_item_generator_registry)


class TestIndexBuilder:
    def test_build_index(self, match_item_generator_registry, index_builder):
        assert index_builder._build_index(match_item_generator_registry.items()) == Index(
            localization_independent={"change_dependent": [MatchItemGeneratorChangeDep.match_item]},
            localization_dependent={
                "default": {
                    "localization_dependent": [MatchItemGeneratorLocDep.match_item]
                },
                "de": {
                    "localization_dependent": [MatchItemGeneratorLocDep.match_item]
                },
            },
        )

    def test_evaluate_match_item_generator(self):
        assert IndexBuilder._evaluate_match_item_generator(
            MatchItemGeneratorLocDep("localization_dependent")) == [
                MatchItemGeneratorLocDep.match_item
            ]

    def test_build_full_index(self, match_item_generator_registry, index_builder):
        assert index_builder.build_full_index() == index_builder._build_index(
            match_item_generator_registry.items())

    @pytest.mark.parametrize(
        "change_action_name, index",
        [
            (
                "something",
                Index(
                    localization_independent={},
                    localization_dependent={
                        "de": {},
                        "default": {},
                    },
                ),
            ),
            (
                "some_change_dependent_whatever",
                Index(
                    localization_independent={
                        "change_dependent": [MatchItemGeneratorChangeDep.match_item]
                    },
                    localization_dependent={
                        "de": {},
                        "default": {},
                    },
                ),
            ),
        ],
    )
    def test_build_changed_sub_indices(self, index_builder, change_action_name, index):
        assert index_builder.build_changed_sub_indices(change_action_name) == index


@pytest.fixture(name="index")
def fixture_index(index_builder):
    return index_builder.build_full_index()


@pytest.fixture(name="index_store", scope="function")
def fixture_index_store(tmp_path):
    path = Path(tmp_dir) / 'search_index_test.pkl'
    path.unlink(missing_ok=True)
    IndexStore._cached_index = None
    IndexStore._cached_mtime = 0.
    return IndexStore(path)


class TestIndexStore:
    def test_store_index(self, index, index_store):
        assert not index_store._path.is_file()
        index_store.store_index(index)
        assert index_store._path.is_file()

    def test_load_index(self, index, index_store):
        with pytest.raises(IndexNotFoundException):
            index_store.load_index(launch_rebuild_if_missing=False)
        index_store.store_index(index)
        loaded_index = index_store.load_index()
        assert loaded_index == index
        assert index_store.load_index() is loaded_index

    def test_is_cache_valid(self, index, index_store):
        assert not index_store._is_cache_valid(10)
        index_store.store_index(index)
        index_store.load_index()
        assert index_store._is_cache_valid(index_store._cached_mtime)


@pytest.fixture(name="created_host_url")
def fixture_created_host_url(with_admin_login):
    folder = Folder.root_folder()
    folder.create_hosts([("host", {}, [])])
    return "wato.py?folder=&host=host&mode=edit_host"


class TestURLChecker:
    def test_is_permitted_false(self, module_wide_request_context):
        assert not URLChecker().is_permitted("wato.py?folder=&mode=service_groups")

    def test_is_permitted_true(self, with_admin_login):
        assert URLChecker().is_permitted("wato.py?folder=&mode=service_groups")

    def test_is_permitted_host_true(self, created_host_url):
        assert URLChecker().is_permitted(created_host_url)

    def test_is_permitted_host_false(
        self,
        monkeypatch,
        module_wide_request_context,
        created_host_url,
    ):
        monkeypatch.setattr(
            hosts_and_folders.config.user,
            "may",
            lambda pname: False,
        )
        assert not URLChecker().is_permitted(created_host_url)


class TestPermissionHandler:
    def test_may_see_topic(self, with_admin_login):
        permissions_handler = PermissionsHandler()
        for topic in permissions_handler._topic_permissions:
            assert permissions_handler.may_see_topic(topic)


class TestIndexSearcher:
    def test_search(self, with_admin_login, index, index_store):
        index_store.store_index(index)
        assert list(IndexSearcher(index_store).search("change_dep")) == [
            ("Change-dependent", [SearchResult(title="change_dependent", url="")]),
        ]

    def test_sort_search_results(self, with_admin_login):
        assert list(
            IndexSearcher._sort_search_results({
                "Hosts": [SearchResult(title="host", url="")],
                "Setup": [SearchResult(title="setup_menu_entry", url="")],
                "Global settings": [SearchResult(title="global_setting", url="")],
                "Other topic": [SearchResult(title="other_item", url="")],
                "Another topic": [SearchResult(title="another_item", url="")],
            })) == [
                ('Setup', [SearchResult(title='setup_menu_entry', url='')]),
                ('Hosts', [SearchResult(title='host', url='')]),
                ('Another topic', [SearchResult(title='another_item', url='')]),
                ('Other topic', [SearchResult(title='other_item', url='')]),
                ('Global settings', [SearchResult(title='global_setting', url='')]),
            ]
