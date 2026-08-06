#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import override

import pytest
from fakeredis import FakeRedis
from pytest import MonkeyPatch
from pytest_mock import MockerFixture
from redis import Redis

import cmk.gui.search._engines._redis
from cmk.automations.results import GetConfigurationResult
from cmk.gui.config import Config
from cmk.gui.i18n import localize
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.search._engines._redis import (
    _SearchResultWithVisibilityCheck,
    IndexBuilder,
    IndexNotFoundException,
    IndexSearcher,
)
from cmk.gui.search.matchers import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.search.permissions import SearchPermissionsHandler, VisibilityCheck
from cmk.gui.session_context import _UserContext
from cmk.gui.type_defs import SearchResult
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato._omd_configuration import (
    ConfigDomainApache,
    ConfigDomainDiskspace,
    ConfigDomainRRDCached,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.livestatus_client.testing import MockLiveStatusConnection


class _FakePermissionsHandler:
    """Always-permit stand-in for the real, GUI-coupled `PermissionsHandler`."""

    def may_see_category(self, category: str) -> bool:
        return True

    def get_visibility_check(self, category: str) -> VisibilityCheck:
        return lambda _url: True


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

    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        yield self.match_item

    @staticmethod
    @override
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return True


class MatchItemGeneratorChangeDep(ABCMatchItemGenerator):
    match_item = MatchItem(
        title="change_dependent",
        topic="Change-dependent",
        url="",
        match_texts=["change_dependent"],
    )

    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        yield self.match_item

    @staticmethod
    @override
    def is_affected_by_change(change_action_name: str) -> bool:
        return "change_dependent" in change_action_name

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return False


@pytest.fixture(name="get_languages", scope="function", autouse=True)
def fixture_get_languages(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.search._engines._redis,
        "get_languages",
        lambda: [
            ("en", "English"),
            ("de", "German"),
        ],
    )


@pytest.fixture(name="match_item_generator_registry")
def fixture_match_item_generator_registry() -> MatchItemGeneratorRegistry:
    match_item_generator_registry = MatchItemGeneratorRegistry()
    match_item_generator_registry.register(
        MatchItemGeneratorLocDep("localization_dependent", provider="setup")
    )
    match_item_generator_registry.register(
        MatchItemGeneratorChangeDep("change_dependent", provider="setup")
    )
    return match_item_generator_registry


@pytest.fixture(name="clean_redis_client")
def fixture_clean_redis_client() -> "Redis":
    client = FakeRedis(decode_responses=True)
    client.flushall()
    return client


@pytest.fixture(name="index_builder")
def fixture_index_builder(
    match_item_generator_registry: MatchItemGeneratorRegistry,
    clean_redis_client: "Redis",
) -> IndexBuilder:
    return IndexBuilder(match_item_generator_registry, clean_redis_client)


@pytest.fixture(name="config")
def fixture_config() -> Config:
    return Config()


@pytest.fixture(name="permissions_handler")
def fixture_permissions_handler() -> SearchPermissionsHandler:
    return _FakePermissionsHandler()


@pytest.fixture(name="index_searcher")
def fixture_index_searcher(
    config: Config,
    clean_redis_client: "Redis",
    permissions_handler: SearchPermissionsHandler,
) -> IndexSearcher:
    return IndexSearcher(config, clean_redis_client, permissions_handler)


class TestIndexBuilder:
    @pytest.mark.usefixtures("with_admin_login")
    def test_update_only_not_built(
        self,
        clean_redis_client: "Redis",
        index_builder: IndexBuilder,
    ) -> None:
        index_builder.build_changed_sub_indices(["something"], UserPermissions({}, {}, {}, []))
        assert not index_builder.index_is_built(clean_redis_client)

    @pytest.mark.usefixtures("with_admin_login")
    def test_language_after_built(
        self,
        monkeypatch: MonkeyPatch,
        index_builder: IndexBuilder,
    ) -> None:
        current_lang = "en"

        def localize_with_memory(lang):
            """Needed to remember currently set language"""
            nonlocal current_lang
            current_lang = lang
            localize(lang)

        monkeypatch.setattr(
            cmk.gui.search._engines._redis,
            "localize",
            localize_with_memory,
        )
        monkeypatch.setattr(
            cmk.gui.search._engines._redis,
            "get_current_language",
            lambda: current_lang,
        )

        start_lang = "en"
        localize_with_memory(start_lang)
        index_builder.build_full_index(UserPermissions({}, {}, {}, []))
        assert current_lang == start_lang


class TestIndexBuilderAndSearcher:
    @pytest.mark.usefixtures("with_admin_login")
    def test_full_build_and_search(
        self,
        index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        index_builder.build_full_index(UserPermissions({}, {}, {}, []))
        assert self._evaluate_search_results_by_topic(index_searcher.search("**")) == [
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
        index_builder.build_changed_sub_indices(["something"], UserPermissions({}, {}, {}, []))
        assert not self._evaluate_search_results_by_topic(index_searcher.search("**"))

    @pytest.mark.usefixtures("with_admin_login")
    def test_update_and_search_with_update(
        self,
        index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        index_builder._mark_index_as_built()
        index_builder.build_changed_sub_indices(
            ["some_change_dependent_whatever"], UserPermissions({}, {}, {}, [])
        )
        assert self._evaluate_search_results_by_topic(index_searcher.search("**")) == [
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

        def empty_match_item_gen(user_permissions: UserPermissions):
            yield from ()

        index_builder.build_full_index(UserPermissions({}, {}, {}, []))

        monkeypatch.setattr(
            match_item_generator_registry["change_dependent"],
            "generate_match_items",
            empty_match_item_gen,
        )

        index_builder.build_changed_sub_indices(
            ["some_change_dependent_whatever"], UserPermissions({}, {}, {}, [])
        )
        assert self._evaluate_search_results_by_topic(index_searcher.search("**")) == [
            ("Localization-dependent", [SearchResult(title="localization_dependent", url="")]),
        ]

    @staticmethod
    def _evaluate_search_results_by_topic(
        results: Iterable[tuple[str, str, SearchResult]],
    ) -> list[tuple[str, list[SearchResult]]]:
        grouped: dict[str, list[SearchResult]] = {}
        for _category, topic, result in results:
            grouped.setdefault(topic, []).append(result)
        return list(grouped.items())


class TestIndexSearcher:
    @pytest.mark.usefixtures("with_admin_login", "inline_background_jobs", "allow_redis")
    def test_search_no_index(
        self,
        config: Config,
        clean_redis_client: "Redis",
        permissions_handler: SearchPermissionsHandler,
        mocker: MockerFixture,
    ) -> None:
        get_config = mocker.patch(
            "cmk.gui.wato.pages.global_settings.ABCConfigDomain.get_all_default_globals"
        )

        with pytest.raises(IndexNotFoundException):
            list(
                IndexSearcher(config, clean_redis_client, permissions_handler).search("change_dep")
            )
        get_config.assert_called()

    def test_sort_search_results(self) -> None:
        def fake_permissions_check(_url: str) -> bool:
            return True

        assert list(
            IndexSearcher._sort_search_results(
                {
                    "Hosts": [
                        _SearchResultWithVisibilityCheck(
                            SearchResult(title="host", url=""),
                            fake_permissions_check,
                        )
                    ],
                    "Setup": [
                        _SearchResultWithVisibilityCheck(
                            SearchResult(title="setup_menu_entry", url=""),
                            fake_permissions_check,
                        )
                    ],
                    "Global settings": [
                        _SearchResultWithVisibilityCheck(
                            SearchResult(title="global_setting", url=""),
                            fake_permissions_check,
                        )
                    ],
                    "Other topic": [
                        _SearchResultWithVisibilityCheck(
                            SearchResult(title="other_item", url=""),
                            fake_permissions_check,
                        )
                    ],
                    "Another topic": [
                        _SearchResultWithVisibilityCheck(
                            SearchResult(title="another_item", url=""),
                            fake_permissions_check,
                        )
                    ],
                }
            )
        ) == [
            (
                "Setup",
                [
                    _SearchResultWithVisibilityCheck(
                        SearchResult(title="setup_menu_entry", url=""),
                        fake_permissions_check,
                    )
                ],
            ),
            (
                "Hosts",
                [
                    _SearchResultWithVisibilityCheck(
                        SearchResult(title="host", url=""),
                        fake_permissions_check,
                    )
                ],
            ),
            (
                "Another topic",
                [
                    _SearchResultWithVisibilityCheck(
                        SearchResult(title="another_item", url=""),
                        fake_permissions_check,
                    )
                ],
            ),
            (
                "Other topic",
                [
                    _SearchResultWithVisibilityCheck(
                        SearchResult(title="other_item", url=""),
                        fake_permissions_check,
                    )
                ],
            ),
            (
                "Global settings",
                [
                    _SearchResultWithVisibilityCheck(
                        SearchResult(title="global_setting", url=""),
                        fake_permissions_check,
                    )
                ],
            ),
        ]


class TestRealisticSearch:
    @staticmethod
    @pytest.fixture()
    def suppress_get_configuration_automation_call(monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setattr(
            "cmk.gui.watolib.check_mk_automations.get_configuration",
            lambda *args, **kwargs: GetConfigurationResult({}),
        )

    @pytest.fixture()
    def real_index_builder(self, clean_redis_client: "Redis") -> IndexBuilder:
        from cmk.gui.search.matchers import match_item_generator_registry

        return IndexBuilder(match_item_generator_registry, clean_redis_client)

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
        real_index_builder: IndexBuilder,
        clean_redis_client: "Redis",
        index_searcher: IndexSearcher,
    ) -> None:
        real_index_builder.build_full_index(UserPermissions({}, {}, {}, []))
        assert IndexBuilder.index_is_built(clean_redis_client)
        assert len(list(index_searcher.search("Host"))) > 4

    def _livestatus_mock(
        self,
        live: MockLiveStatusConnection,
    ) -> MockLiveStatusConnection:
        live.add_table("eventconsolerules", [])
        return live

    @pytest.mark.usefixtures(
        "with_admin_login",
        "fake_omd_default_globals",
        "fake_diskspace_default_globals",
        "fake_apache_default_globals",
        "fake_rrdcached_default_globals",
        "suppress_get_configuration_automation_call",
        "mock_livestatus",
    )
    def test_index_is_built_as_super_user(
        self,
        real_index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        """
        We test that the index is always built as a super user.
        """
        with _UserContext(LoggedInNobody()):
            real_index_builder.build_full_index(UserPermissions({}, {}, {}, []))

        # if the search index did not internally use the super user while building, this item would
        # be missing, because the match item generator for the setup menu only yields entries which
        # the current user is allowed to see
        assert list(index_searcher.search("custom host attributes"))

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
        real_index_builder: IndexBuilder,
        index_searcher: IndexSearcher,
    ) -> None:
        """
        This test ensures that test_index_is_built_as_super_user makes sense, ie. that if we do not
        build as a super user, the entry "Custom host attributes" is not found.
        """

        @contextmanager
        def SuperUserContext() -> Iterator[None]:
            yield

        monkeypatch.setattr(
            cmk.gui.search._engines._redis,
            "SuperUserContext",
            SuperUserContext,
        )

        with _UserContext(LoggedInNobody()):
            real_index_builder.build_full_index(UserPermissions({}, {}, {}, []))

        assert not list(index_searcher.search("custom host attributes"))
