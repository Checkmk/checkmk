#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterator, Mapping
from typing import override

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.global_settings.pages import global_settings, site_specific_settings
from cmk.gui.i18n import _l
from cmk.gui.mkeventd.config_domain import ConfigDomainEventConsole
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    ConfigDomainName,
    ConfigVariableGroup,
    ConfigVariableHint,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.sites import site_management_registry, SitesConfigFile
from cmk.livestatus_client import UnixSocketInfo
from cmk.shared_typing import global_settings as shared
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import IconNames
from tests.testlib.gui.global_settings import (
    logged_in,
    patch_factory_defaults,
    registered,
    shown_variables,
)
from tests.testlib.gui.web_test_app import SetConfig, WebTestAppForCMK

REMOTE_SITE = SiteId("remote")
UNREPLICATED_SITE = SiteId("unreplicated")
TEST_DEFAULTS: Mapping[str, object] = {"test_var_a": 1, "test_var_b": 2}
EVENT_CONSOLE_VAR = "test_ec_var"
GUI_VAR = "test_gui_var"


@pytest.fixture(name="factory_defaults")
def fixture_factory_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_factory_defaults(monkeypatch, TEST_DEFAULTS)


@pytest.fixture(name="test_variables")
def fixture_test_variables(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, TEST_DEFAULTS)
    with registered(
        ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a", "test_var_b"
    ):
        yield


@pytest.fixture(name="variables_of_both_domains")
def fixture_variables_of_both_domains(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, {EVENT_CONSOLE_VAR: 1, GUI_VAR: 2})
    with (
        registered(
            ConfigVariableGroup(title=_l("Event Console group"), sort_index=1),
            EVENT_CONSOLE_VAR,
            primary_domain=ConfigDomainEventConsole,
        ),
        registered(ConfigVariableGroup(title=_l("GUI group"), sort_index=2), GUI_VAR),
    ):
        yield


@pytest.fixture(name="executables_variable")
def fixture_executables_variable(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, {"actions": 1})
    with registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "actions"):
        yield


@pytest.fixture(name="distributed_setup")
def fixture_distributed_setup(patch_omd_site: None) -> None:  # noqa: ARG001
    _add_remote_site(REMOTE_SITE, "Remote site", overrides={"test_var_a": 5})


def _add_remote_site(
    site_id: SiteId,
    alias: str,
    *,
    replicated: bool = True,
    overrides: Mapping[str, object] | None = None,
) -> None:
    socket: UnixSocketInfo = ("unix", {"path": "/elsewhere/run/live"})
    sites = site_management_registry["site_management"].load_sites()
    remote = sites[omd_site()].copy()
    remote["id"] = site_id
    remote["alias"] = alias
    remote["url_prefix"] = f"/{site_id}/"
    remote["socket"] = socket
    remote["replication"] = "slave" if replicated else None
    if overrides is not None:
        remote["globals"] = dict(overrides)
    sites[site_id] = remote
    SitesConfigFile().save(sites, pprint_value=False)


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_registered_group_with_a_visible_variable_becomes_a_topic(load_config: Config) -> None:
    with registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a"):
        topics = global_settings(load_config).topics
    assert [topic.headline for topic in topics] == ["Test group"]
    assert [variable.name for variable in topics[0].variables] == ["test_var_a"]


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_group_without_visible_variables_yields_no_topic(load_config: Config) -> None:
    with registered(ConfigVariableGroup(title=_l("Empty group"), sort_index=1)):
        topics = global_settings(load_config).topics
    assert topics == []


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_the_group_icon_and_description_become_the_topic_header(load_config: Config) -> None:
    group = ConfigVariableGroup(
        title=_l("Test group"),
        sort_index=1,
        icon=IconNames.sites,
        description=_l("Configures the test"),
    )
    with registered(group, "test_var_a"):
        topic = global_settings(load_config).topics[0]
    assert topic.icon == shared.IconNames.sites
    assert topic.subline == "Configures the test"


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_group_without_icon_and_description_gets_the_defaults(load_config: Config) -> None:
    with registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), "test_var_a"):
        topic = global_settings(load_config).topics[0]
    assert topic.icon == shared.IconNames.configuration
    assert topic.subline == ""


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_topics_follow_the_group_sort_index(load_config: Config) -> None:
    with (
        registered(ConfigVariableGroup(title=_l("Later"), sort_index=20), "test_var_a"),
        registered(ConfigVariableGroup(title=_l("Earlier"), sort_index=10), "test_var_b"),
    ):
        topics = global_settings(load_config).topics
    assert [topic.headline for topic in topics] == ["Earlier", "Later"]


@pytest.mark.usefixtures("executables_variable", "with_admin_login")
def test_an_administrator_sees_a_variable_that_adds_executables(load_config: Config) -> None:
    topics = global_settings(load_config).topics
    assert [variable.name for variable in topics[0].variables] == ["actions"]


@pytest.mark.usefixtures("executables_variable")
def test_a_variable_the_user_may_not_read_is_left_out(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with logged_in(with_user[0], "wato.use", "wato.global"):
        assert global_settings(load_config).topics == []


@pytest.mark.usefixtures("test_variables", "with_admin_login")
def test_an_unset_variable_comes_from_the_factory_defaults(load_config: Config) -> None:
    variable = shown_variables(global_settings(load_config))["test_var_a"]

    assert variable.value == 1
    assert variable.origin is shared.GlobalSettingsOrigin.factory


@pytest.mark.usefixtures("test_variables", "with_admin_login")
def test_a_centrally_configured_variable_comes_from_the_global_settings(
    load_config: Config,
) -> None:
    ConfigDomainGUI().save({"test_var_a": 5})

    variable = shown_variables(global_settings(load_config))["test_var_a"]

    assert variable.value == 5
    assert variable.origin is shared.GlobalSettingsOrigin.global_


@pytest.mark.usefixtures("test_variables", "distributed_setup", "with_admin_login")
def test_the_global_page_shows_no_inherited_value(load_config: Config) -> None:
    assert shown_variables(global_settings(load_config))["test_var_a"].global_value is None


@pytest.mark.usefixtures("test_variables", "distributed_setup", "with_admin_login")
def test_the_global_page_links_the_site_that_overrides_a_variable(load_config: Config) -> None:
    variable = shown_variables(global_settings(load_config))["test_var_a"]

    assert variable.site_overrides == [
        shared.GlobalSettingsSiteOverride(
            site_id=REMOTE_SITE,
            title="Remote site",
            url="site_specific_settings.py?site=remote",
        )
    ]


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_an_administrator_reaches_the_page(load_config: Config) -> None:
    global_settings(load_config)


@pytest.mark.usefixtures("factory_defaults", "with_user_login")
def test_the_page_needs_the_global_settings_permission(load_config: Config) -> None:
    with pytest.raises(MKAuthException, match="Global settings"):
        global_settings(load_config)


@pytest.mark.usefixtures("factory_defaults")
def test_reading_all_modules_suffices_for_the_page(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with logged_in(with_user[0], "wato.use", "wato.seeall"):
        global_settings(load_config)


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_disabled_setup_refuses_the_page(load_config: Config) -> None:
    with pytest.raises(MKGeneralException):
        global_settings(dataclasses.replace(load_config, wato_enabled=False))


@pytest.mark.usefixtures(
    "factory_defaults", "patch_theme", "suppress_license_banner", "suppress_license_expiry_header"
)
def test_the_read_only_message_is_shown_on_the_page(
    logged_in_admin_wsgi_app: WebTestAppForCMK, set_config: SetConfig
) -> None:
    with set_config(
        wato_read_only={"enabled": True, "rw_users": [], "message": "Maintenance in progress"}
    ):
        response = logged_in_admin_wsgi_app.get("/NO_SITE/check_mk/global_settings.py", status=200)
    assert "Maintenance in progress" in response.text


@pytest.mark.usefixtures("test_variables", "distributed_setup", "with_admin_login")
def test_a_site_specific_value_is_shown_as_a_modification_of_the_inherited_one(
    load_config: Config,
) -> None:
    variable = shown_variables(site_specific_settings(load_config, REMOTE_SITE))["test_var_a"]

    assert variable.value == 5
    assert variable.origin is shared.GlobalSettingsOrigin.site
    assert variable.global_value == 1


@pytest.mark.usefixtures("test_variables", "distributed_setup", "with_admin_login")
def test_a_site_inherits_a_centrally_configured_value(load_config: Config) -> None:
    ConfigDomainGUI().save({"test_var_b": 7})

    variable = shown_variables(site_specific_settings(load_config, REMOTE_SITE))["test_var_b"]

    assert variable.value == 7
    assert variable.origin is shared.GlobalSettingsOrigin.global_
    assert variable.global_value == 7


@pytest.mark.usefixtures("test_variables", "distributed_setup", "with_admin_login")
def test_a_site_that_inherits_an_unconfigured_variable_comes_from_the_factory_defaults(
    load_config: Config,
) -> None:
    variable = shown_variables(site_specific_settings(load_config, REMOTE_SITE))["test_var_b"]

    assert variable.value == 2
    assert variable.origin is shared.GlobalSettingsOrigin.factory


@pytest.mark.usefixtures("patch_omd_site", "with_admin_login")
def test_an_unknown_site_is_refused(load_config: Config) -> None:
    with pytest.raises(MKUserError, match="This site does not exist"):
        site_specific_settings(load_config, SiteId("nowhere"))


@pytest.mark.usefixtures("patch_omd_site", "with_admin_login")
def test_a_non_distributed_setup_offers_no_site_specific_settings(load_config: Config) -> None:
    with pytest.raises(MKUserError, match="non-distributed setups"):
        site_specific_settings(load_config, omd_site())


@pytest.mark.usefixtures("distributed_setup", "with_admin_login")
def test_a_site_without_replication_offers_no_site_specific_settings(load_config: Config) -> None:
    _add_remote_site(UNREPLICATED_SITE, "Unreplicated site", replicated=False)

    with pytest.raises(MKUserError, match="not the central site nor a replication remote site"):
        site_specific_settings(load_config, UNREPLICATED_SITE)


@pytest.mark.usefixtures("factory_defaults", "distributed_setup")
def test_the_site_management_permission_suffices_for_the_site_page(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with logged_in(with_user[0], "wato.use", "wato.sites"):
        site_specific_settings(load_config, REMOTE_SITE)


@pytest.mark.usefixtures("factory_defaults", "distributed_setup", "with_user_login")
def test_the_site_page_refuses_a_user_without_the_site_management_permission(
    load_config: Config,
) -> None:
    with pytest.raises(MKAuthException, match="Site management"):
        site_specific_settings(load_config, REMOTE_SITE)


@pytest.mark.usefixtures("test_variables", "distributed_setup")
def test_a_site_manager_does_not_see_a_variable_they_may_not_read(
    load_config: Config, with_user: tuple[UserId, str]
) -> None:
    with logged_in(with_user[0], "wato.use", "wato.sites"):
        assert site_specific_settings(load_config, REMOTE_SITE).topics == []


@pytest.mark.usefixtures("factory_defaults", "distributed_setup", "with_admin_login")
def test_the_site_specific_breadcrumb_hangs_under_the_site_connection(load_config: Config) -> None:
    data = site_specific_settings(load_config, REMOTE_SITE)

    assert [item.title for item in data.breadcrumb][-3:] == [
        "Distributed monitoring",
        "Edit site connection remote",
        "Site-specific settings of Remote site",
    ]
    assert [item.link for item in data.breadcrumb][-3:-1] == [
        "wato.py?mode=sites",
        "wato.py?mode=edit_site&site=remote",
    ]


@pytest.mark.usefixtures("variables_of_both_domains", "with_admin_login")
def test_the_global_page_hides_event_console_variables(load_config: Config) -> None:
    assert set(shown_variables(global_settings(load_config))) == {GUI_VAR}


@pytest.mark.usefixtures("variables_of_both_domains", "distributed_setup", "with_admin_login")
def test_the_site_page_shows_event_console_variables_too(load_config: Config) -> None:
    assert set(shown_variables(site_specific_settings(load_config, REMOTE_SITE))) == {
        EVENT_CONSOLE_VAR,
        GUI_VAR,
    }


class _HintingDomain(ConfigDomainGUI):
    @classmethod
    @override
    def ident(cls) -> ConfigDomainName:
        return "test_hinting_domain"

    @classmethod
    @override
    def hint(cls) -> HTML:
        return HTML.without_escaping("<b>Restart</b> required")


@pytest.fixture(name="hinting_domain")
def fixture_hinting_domain() -> Iterator[None]:
    config_domain_registry.register(_HintingDomain())
    try:
        yield
    finally:
        config_domain_registry.unregister(_HintingDomain.ident())


@pytest.mark.usefixtures("factory_defaults", "hinting_domain", "with_admin_login")
def test_the_domain_hint_precedes_the_hints_of_the_variable(load_config: Config) -> None:
    with registered(
        ConfigVariableGroup(title=_l("Test group"), sort_index=1),
        "test_var_a",
        primary_domain=_HintingDomain,
        hints=lambda: [ConfigVariableHint(HTML.without_escaping("Take care"), variant="info")],
    ):
        variable = shown_variables(global_settings(load_config))["test_var_a"]

    assert variable.hints == [
        shared.GlobalSettingsHint(
            text="<b>Restart</b> required",
            variant=shared.GlobalSettingsHintVariant.warning,
            copyable=None,
        ),
        shared.GlobalSettingsHint(
            text="Take care", variant=shared.GlobalSettingsHintVariant.info, copyable=None
        ),
    ]


@pytest.mark.usefixtures("test_variables", "with_admin_login")
def test_a_variable_of_a_domain_without_a_hint_has_none(load_config: Config) -> None:
    assert shown_variables(global_settings(load_config))["test_var_a"].hints == []


@pytest.mark.usefixtures("factory_defaults", "with_admin_login")
def test_a_copyable_hint_keeps_its_value_out_of_the_text(load_config: Config) -> None:
    with registered(
        ConfigVariableGroup(title=_l("Test group"), sort_index=1),
        "test_var_a",
        hints=lambda: [
            ConfigVariableHint(HTML.without_escaping("Reachable at "), copyable="http://host/mcp")
        ],
    ):
        variable = shown_variables(global_settings(load_config))["test_var_a"]

    assert variable.hints == [
        shared.GlobalSettingsHint(
            text="Reachable at ",
            variant=shared.GlobalSettingsHintVariant.warning,
            copyable="http://host/mcp",
        )
    ]
