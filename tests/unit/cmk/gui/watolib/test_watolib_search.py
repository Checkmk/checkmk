#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
from typing import Iterator

import pytest
from pytest import MonkeyPatch

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.automations.results import GetConfigurationResult

from cmk.gui.logged_in import _UserContext, LoggedInNobody, user
from cmk.gui.plugins.wato.omd_configuration import (
    ConfigDomainApache,
    ConfigDomainDiskspace,
    ConfigDomainRRDCached,
)
from cmk.gui.type_defs import SearchResult
from cmk.gui.wato.pages.hosts import ModeEditHost
from cmk.gui.watolib import search
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    IndexBuilder,
    IndexNotFoundException,
    IndexSearcher,
    localize,
)
from cmk.gui.watolib.search import (
    match_item_generator_registry as real_match_item_generator_registry,
)
from cmk.gui.watolib.search import (
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
    PermissionsHandler,
    URLChecker,
)


@pytest.fixture(scope="function")
def fake_omd_default_globals(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        ConfigDomainOMD,
        "default_globals",
        lambda s: {
            "site_admin_mail": "",
            "site_apache_mode": "own",
            "site_apache_tcp_addr": "127.0.0.1",
            "site_apache_tcp_port": "5000",
            "site_autostart": False,
            "site_core": "cmc",
            "site_liveproxyd": True,
            "site_livestatus_tcp": None,
            "site_livestatus_tcp_only_from": "0.0.0.0 ::/0",
            "site_livestatus_tcp_port": "6557",
            "site_livestatus_tcp_tls": True,
            "site_mkeventd": ["SYSLOG"],
            "site_mkeventd_snmptrap": False,
            "site_mkeventd_syslog": True,
            "site_mkeventd_syslog_tcp": False,
            "site_multisite_authorisation": True,
            "site_multisite_cookie_auth": True,
            "site_nagios_theme": "classicui",
            "site_pnp4nagios": True,
            "site_tmpfs": True,
        },
    )


@pytest.fixture(scope="function")
def fake_diskspace_default_globals(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        ConfigDomainDiskspace,
        "default_globals",
        lambda s: {
            "diskspace_cleanup": {"cleanup_abandoned_host_files": 2592000},
        },
    )


@pytest.fixture(scope="function")
def fake_apache_default_globals(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        ConfigDomainApache,
        "default_globals",
        lambda s: {"apache_process_tuning": {"number_of_processes": 64}},
    )


@pytest.fixture(scope="function")
def fake_rrdcached_default_globals(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        ConfigDomainRRDCached,
        "default_globals",
        lambda s: {
            "rrdcached_tuning": {
                "TIMEOUT": 3600,
                "RANDOM_DELAY": 1800,
                "FLUSH_TIMEOUT": 7200,
                "WRITE_THREADS": 4,
            },
        },
    )


def test_match_item() -> None:
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
def fixture_get_languages(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        search,
        "get_languages",
        lambda: [[""], ["de"]],
    )


@pytest.fixture(name="match_item_generator_registry")
def fixture_match_item_generator_registry() -> MatchItemGeneratorRegistry:
    match_item_generator_registry = MatchItemGeneratorRegistry()
    match_item_generator_registry.register(MatchItemGeneratorLocDep("localization_dependent"))
    match_item_generator_registry.register(MatchItemGeneratorChangeDep("change_dependent"))
    return match_item_generator_registry


@pytest.fixture(name="index_builder")
def fixture_index_builder(
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> IndexBuilder:
    return IndexBuilder(match_item_generator_registry)


@pytest.fixture(name="index_searcher")
def fixture_index_searcher(index_builder: IndexBuilder) -> IndexSearcher:
    index_searcher = IndexSearcher(PermissionsHandler(URLChecker[ModeEditHost](ModeEditHost)))
    index_searcher._redis_client = index_builder._redis_client
    return index_searcher


class TestIndexBuilder:
    @pytest.mark.usefixtures("with_admin_login")
    def test_update_only_not_built(
        self,
        index_builder: IndexBuilder,
    ) -> None:
        index_builder.build_changed_sub_indices("something")
        assert not index_builder.index_is_built(index_builder._redis_client)

    @pytest.mark.usefixtures("with_admin_login")
    def test_language_after_built(
        self,
        monkeypatch: MonkeyPatch,
        index_builder: IndexBuilder,
    ) -> None:

        current_lang = ""

        def localize_with_memory(lang):
            """Needed to remember currently set language"""
            nonlocal current_lang
            current_lang = lang
            localize(lang)

        monkeypatch.setattr(
            search,
            "localize",
            localize_with_memory,
        )
        monkeypatch.setattr(
            search,
            "get_current_language",
            lambda: current_lang,
        )

        start_lang = ""
        localize_with_memory(start_lang)
        index_builder.build_full_index()
        assert current_lang == start_lang


class TestIndexBuilderAndSearcher:
    @pytest.mark.usefixtures("with_admin_login")
    def test_full_build_and_search(
        self,
        index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        index_builder.build_full_index()
        assert list(index_searcher.search("**")) == [
            ("Change-dependent", [SearchResult(title="change_dependent", url="")]),
            ("Localization-dependent", [SearchResult(title="localization_dependent", url="")]),
        ]

    @pytest.mark.usefixtures("with_admin_login")
    def test_update_and_search_no_update(
        self,
        index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        index_builder._mark_index_as_built()
        index_builder.build_changed_sub_indices("something")
        assert not list(index_searcher.search("**"))

    @pytest.mark.usefixtures("with_admin_login")
    def test_update_and_search_with_update(
        self,
        index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        index_builder._mark_index_as_built()
        index_builder.build_changed_sub_indices("some_change_dependent_whatever")
        assert list(index_searcher.search("**")) == [
            ("Change-dependent", [SearchResult(title="change_dependent", url="")]),
        ]

    @pytest.mark.usefixtures("with_admin_login")
    def test_update_with_empty_and_search(
        self,
        monkeypatch: MonkeyPatch,
        match_item_generator_registry: MatchItemGeneratorRegistry,
        index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        """
        Test if things can also be deleted from the index during an update
        """

        def empty_match_item_gen():
            yield from ()

        index_builder.build_full_index()

        monkeypatch.setattr(
            match_item_generator_registry["change_dependent"],
            "generate_match_items",
            empty_match_item_gen,
        )

        index_builder.build_changed_sub_indices("some_change_dependent_whatever")
        assert list(index_searcher.search("**")) == [
            ("Localization-dependent", [SearchResult(title="localization_dependent", url="")]),
        ]


@pytest.fixture(name="created_host_url")
def fixture_created_host_url(with_admin_login) -> str:
    folder = Folder.root_folder()
    folder.create_hosts([("host", {}, [])])
    return "wato.py?folder=&host=host&mode=edit_host"


class TestURLChecker:
    @pytest.mark.usefixtures("request_context")
    def test_is_permitted_false(self) -> None:
        assert not URLChecker[ModeEditHost](ModeEditHost).is_permitted(
            "wato.py?folder=&mode=service_groups"
        )

    @pytest.mark.usefixtures("with_admin_login")
    def test_is_permitted_true(self) -> None:
        assert URLChecker[ModeEditHost](ModeEditHost).is_permitted(
            "wato.py?folder=&mode=service_groups"
        )

    def test_is_permitted_host_true(
        self,
        created_host_url: str,
    ) -> None:
        assert URLChecker[ModeEditHost](ModeEditHost).is_permitted(created_host_url)

    def test_is_permitted_host_false(
        self,
        monkeypatch: MonkeyPatch,
        request_context,
        created_host_url: str,
    ) -> None:
        monkeypatch.setattr(
            user,
            "may",
            lambda pname: False,
        )
        assert not URLChecker[ModeEditHost](ModeEditHost).is_permitted(created_host_url)


class TestPermissionHandler:
    @pytest.mark.usefixtures("with_admin_login")
    def test_may_see_category(self) -> None:
        permissions_handler = PermissionsHandler(URLChecker[ModeEditHost](ModeEditHost))
        for category in permissions_handler._category_permissions:
            assert permissions_handler.may_see_category(category)


class TestIndexSearcher:
    @pytest.mark.usefixtures("with_admin_login")
    def test_search_no_index(self) -> None:
        with pytest.raises(IndexNotFoundException):
            list(IndexSearcher(PermissionsHandler(URLChecker(ModeEditHost))).search("change_dep"))

    def test_sort_search_results(self) -> None:
        assert list(
            IndexSearcher._sort_search_results(
                {
                    "Hosts": [SearchResult(title="host", url="")],
                    "Setup": [SearchResult(title="setup_menu_entry", url="")],
                    "Global settings": [SearchResult(title="global_setting", url="")],
                    "Other topic": [SearchResult(title="other_item", url="")],
                    "Another topic": [SearchResult(title="another_item", url="")],
                }
            )
        ) == [
            ("Setup", [SearchResult(title="setup_menu_entry", url="")]),
            ("Hosts", [SearchResult(title="host", url="")]),
            ("Another topic", [SearchResult(title="another_item", url="")]),
            ("Other topic", [SearchResult(title="other_item", url="")]),
            ("Global settings", [SearchResult(title="global_setting", url="")]),
        ]


class TestRealisticSearch:
    @staticmethod
    @pytest.fixture()
    def suppress_get_configuration_automation_call(monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(
            "cmk.gui.watolib.check_mk_automations.get_configuration",
            lambda *args, **kwargs: GetConfigurationResult({}),
        )

    @pytest.mark.usefixtures(
        "with_admin_login",
        "fake_omd_default_globals",
        "fake_diskspace_default_globals",
        "fake_apache_default_globals",
        "fake_rrdcached_default_globals",
        "suppress_get_configuration_automation_call",
    )
    def test_real_search_without_exception(
        self,
        mock_livestatus: MockLiveStatusConnection,
    ) -> None:
        builder = IndexBuilder(real_match_item_generator_registry)

        with self._livestatus_mock(mock_livestatus):
            builder.build_full_index()

        assert builder.index_is_built(builder._redis_client)

        searcher = IndexSearcher(PermissionsHandler(URLChecker[ModeEditHost](ModeEditHost)))
        searcher._redis_client = builder._redis_client

        assert len(list(searcher.search("Host"))) > 4

    def _livestatus_mock(
        self,
        live: MockLiveStatusConnection,
    ) -> MockLiveStatusConnection:
        live.add_table("eventconsolerules", [])
        live.expect_query("GET eventconsolerules\nColumns: rule_id rule_hits\n")
        live.expect_query("GET eventconsolerules\nColumns: rule_id rule_hits\n")
        return live

    @pytest.mark.usefixtures(
        "with_admin_login",
        "fake_omd_default_globals",
        "fake_diskspace_default_globals",
        "fake_apache_default_globals",
        "fake_rrdcached_default_globals",
        "suppress_get_configuration_automation_call",
    )
    def test_index_is_built_as_super_user(
        self,
        mock_livestatus: MockLiveStatusConnection,
    ):
        """
        We test that the index is always built as a super user.
        """

        with _UserContext(LoggedInNobody()):
            builder = IndexBuilder(real_match_item_generator_registry)
            with self._livestatus_mock(mock_livestatus):
                builder.build_full_index()

        searcher = IndexSearcher(PermissionsHandler(URLChecker[ModeEditHost](ModeEditHost)))
        searcher._redis_client = builder._redis_client

        # if the search index did not internally use the super user while building, this item would
        # be missing, because the match item generator for the setup menu only yields entries which
        # the current user is allowed to see
        assert list(searcher.search("custom host attributes"))

    @pytest.mark.usefixtures(
        "with_admin_login",
        "fake_omd_default_globals",
        "fake_diskspace_default_globals",
        "fake_apache_default_globals",
        "fake_rrdcached_default_globals",
        "suppress_get_configuration_automation_call",
    )
    def test_dcd_not_found_if_not_super_user(
        self,
        monkeypatch: MonkeyPatch,
        mock_livestatus: MockLiveStatusConnection,
    ):
        """
        This test ensures that test_index_is_built_as_super_user makes sense, ie. that if we do not
        build as a super user, the entry "Custom host attributes" is not found.
        """

        @contextmanager
        def SuperUserContext() -> Iterator[None]:
            yield

        monkeypatch.setattr(
            search,
            "SuperUserContext",
            SuperUserContext,
        )

        with _UserContext(LoggedInNobody()):
            builder = IndexBuilder(real_match_item_generator_registry)
            with self._livestatus_mock(mock_livestatus):
                builder.build_full_index()

        searcher = IndexSearcher(PermissionsHandler(URLChecker[ModeEditHost](ModeEditHost)))
        searcher._redis_client = builder._redis_client
        assert not list(searcher.search("custom host attributes"))
