#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.type_defs import SearchResult
from cmk.gui.watolib import (
    hosts_and_folders,
    search,
)
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    IndexBuilder,
    IndexNotFoundException,
    IndexSearcher,
    MatchItem,
    MatchItems,
    MatchItemGeneratorRegistry,
    PermissionsHandler,
    URLChecker,
)


def test_match_item():
    assert MatchItem(
        "1",
        "2",
        "3",
        ["ABC", "Some text", "df"],
    ).match_texts == ["abc", "some text", "df"]


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


@pytest.fixture(name="get_languages", scope="function", autouse=True)
def fixture_get_languages(monkeypatch):
    monkeypatch.setattr(
        search,
        "get_languages",
        lambda: [[""], ["de"]],
    )


@pytest.fixture(name="match_item_generator_registry")
def fixture_match_item_generator_registry():
    match_item_generator_registry = MatchItemGeneratorRegistry()
    match_item_generator_registry.register(MatchItemGeneratorLocDep("localization_dependent"))
    match_item_generator_registry.register(MatchItemGeneratorChangeDep("change_dependent"))
    return match_item_generator_registry


@pytest.fixture(name="index_builder")
def fixture_index_builder(match_item_generator_registry):
    return IndexBuilder(match_item_generator_registry)


@pytest.fixture(name="index_searcher")
def fixture_index_searcher(index_builder):
    index_searcher = IndexSearcher()
    index_searcher._redis_client = index_builder._redis_client
    return index_searcher


class TestIndexBuilder:
    def test_update_only_not_built(self, with_admin_login, index_builder):
        index_builder.build_changed_sub_indices("something")
        assert not index_builder.index_is_built(index_builder._redis_client)


class TestIndexBuilderAndSearcher:
    def test_full_build_and_search(self, with_admin_login, index_builder, index_searcher):
        index_builder.build_full_index()
        assert list(index_searcher.search("**")) == [
            ("Change-dependent", [SearchResult(title="change_dependent", url="")]),
            ("Localization-dependent", [SearchResult(title="localization_dependent", url="")]),
        ]

    def test_update_and_search_no_update(
        self,
        with_admin_login,
        index_builder,
        index_searcher,
    ):
        index_builder._mark_index_as_built()
        index_builder.build_changed_sub_indices("something")
        assert not list(index_searcher.search("**"))

    def test_update_and_search_with_update(
        self,
        with_admin_login,
        index_builder,
        index_searcher,
    ):
        index_builder._mark_index_as_built()
        index_builder.build_changed_sub_indices("some_change_dependent_whatever")
        assert list(index_searcher.search("**")) == [
            ("Change-dependent", [SearchResult(title="change_dependent", url="")]),
        ]

    def test_update_with_empty_and_search(
        self,
        with_admin_login,
        match_item_generator_registry,
        index_builder,
        index_searcher,
    ):
        """
        Test if things can also be deleted from the index during an update
        """
        def empty_match_item_gen():
            yield from ()

        index_builder.build_full_index()
        match_item_generator_registry[
            "change_dependent"].generate_match_items = empty_match_item_gen
        index_builder.build_changed_sub_indices("some_change_dependent_whatever")
        assert list(index_searcher.search("**")) == [
            ("Localization-dependent", [SearchResult(title="localization_dependent", url="")]),
        ]


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
    def test_may_see_category(self, with_admin_login):
        permissions_handler = PermissionsHandler()
        for category in permissions_handler._category_permissions:
            assert permissions_handler.may_see_category(category)


class TestIndexSearcher:
    def test_search_no_index(self, with_admin_login):
        with pytest.raises(IndexNotFoundException):
            list(IndexSearcher().search("change_dep"))

    def test_sort_search_results(self):
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
