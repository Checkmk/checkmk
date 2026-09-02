#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import logging
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import assert_never

import pytest

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.setup.global_settings import (
    EditPiggybackHubGlobally,
    EditPiggybackHubSiteSpecific,
    GlobalSettings,
    SiteSpecificGlobalSettings,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site, SiteFactory
from tests.testlib.utils import is_cleanup_enabled

logger = logging.getLogger(__name__)


SITE_SPECIFIC_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/sites.mk")
GLOBAL_SETTINGS_REL_PATH = Path("etc/omd/global.mk")
SITE_CONF_REL_PATH = Path("etc/omd/site.conf")

EXPECTED_ERROR = (
    "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
)


@pytest.fixture(name="remote_site_wato_disabled", scope="module")
def fixture_remote_site_wato_disabled(test_site: Site, site_factory: SiteFactory) -> Iterator[Site]:
    """Return a second Checkmk site object for a distributed setup, shared across this module.

    WATO is disabled on the remote site (disable_remote_configuration=True).

    This overrides the function-scoped fixture of the same name from the top-level conftest.
    """
    with site_factory.connected_remote_site(
        "remote", test_site, "test_piggyback_hub_conf"
    ) as remote_site:
        yield remote_site


class HubEnableActions(enum.Enum):
    """The piggyback-hub can be enabled by
    * navigating to its specific global setting page, checking the relevant checkbox and saving
    * toggling its setting in the global settings page
    """

    SAVE = enum.auto()
    TOGGLE = enum.auto()


class HubDisableActions(enum.Enum):
    """The piggyback-hub can be disabled by
    * navigating to its specific global setting page, unchecking the relevant checkbox and saving
    * toggling its setting in the global settings page
    * resetting the global settings to factory settings
    """

    SAVE = enum.auto()
    TOGGLE = enum.auto()
    RESET = enum.auto()


HubAction = HubEnableActions | HubDisableActions


class TargetSite(enum.Enum):
    """The site a site-specific change is applied to."""

    CENTRAL = enum.auto()
    REMOTE = enum.auto()


def _enable_hub_globally(
    dashboard_page: MainDashboard, enable_actions: HubEnableActions = HubEnableActions.SAVE
) -> None:
    logger.info("Enable the piggyback-hub globally")
    match enable_actions:
        case HubEnableActions.SAVE:
            settings_page = EditPiggybackHubGlobally(dashboard_page.page)
            settings_page.enable_hub()
            settings_page.save_button.click()
        case HubEnableActions.TOGGLE:
            global_settings_page = GlobalSettings(dashboard_page.page)
            global_settings_page.toggle("Enable piggyback-hub")
        case _:
            assert_never(enable_actions)


def _disable_hub_globally(
    dashboard_page: MainDashboard,
    disable_action: HubDisableActions = HubDisableActions.SAVE,
    expect_success: bool = True,
) -> None:
    logger.info("Disable the piggyback-hub globally")
    match disable_action:
        case HubDisableActions.SAVE:
            settings_page = EditPiggybackHubGlobally(dashboard_page.page)
            settings_page.disable_hub()
            settings_page.save_button.click()
        case HubDisableActions.TOGGLE:
            global_settings_page = GlobalSettings(dashboard_page.page)
            global_settings_page.toggle("Enable piggyback-hub")
        case HubDisableActions.RESET:
            settings_page = EditPiggybackHubGlobally(dashboard_page.page)
            settings_page.to_factory_settings(expect_success=expect_success)
        case _:
            assert_never(disable_action)


def _enable_hub_site_specific(
    dashboard_page: MainDashboard,
    site_id: str,
    enable_action: HubEnableActions = HubEnableActions.SAVE,
) -> None:
    logger.info("Enable the piggyback-hub site-specific")
    match enable_action:
        case HubEnableActions.SAVE:
            site_specific_settings_page = EditPiggybackHubSiteSpecific(dashboard_page.page, site_id)
            site_specific_settings_page.enable_hub()
            site_specific_settings_page.save_button.click()
        case HubEnableActions.TOGGLE:
            site_specific_global_settings_page = SiteSpecificGlobalSettings(
                dashboard_page.page, site_id
            )
            site_specific_global_settings_page.toggle("Enable piggyback-hub")
        case _:
            assert_never(enable_action)


def _disable_hub_site_specific(
    dashboard_page: MainDashboard,
    site_id: str,
    disable_action: HubDisableActions = HubDisableActions.SAVE,
    expect_success: bool = True,
) -> None:
    logger.info("Disable the piggyback-hub site-specific")
    match disable_action:
        case HubDisableActions.SAVE:
            site_specific_settings_page = EditPiggybackHubSiteSpecific(dashboard_page.page, site_id)
            site_specific_settings_page.disable_hub()
            site_specific_settings_page.save_button.click()
        case HubDisableActions.TOGGLE:
            site_specific_global_settings_page = SiteSpecificGlobalSettings(
                dashboard_page.page, site_id
            )
            site_specific_global_settings_page.toggle("Enable piggyback-hub")
        case HubDisableActions.RESET:
            site_specific_settings_page = EditPiggybackHubSiteSpecific(dashboard_page.page, site_id)
            site_specific_settings_page.to_factory_settings(expect_success=expect_success)
        case _:
            assert_never(disable_action)


def _change_hub_globally(
    dashboard_page: MainDashboard, action: HubAction, expect_success: bool = True
) -> None:
    """Apply `action` to the piggyback-hub global setting."""
    match action:
        case HubEnableActions():
            _enable_hub_globally(dashboard_page, action)
        case HubDisableActions():
            _disable_hub_globally(dashboard_page, action, expect_success)
        case _:
            assert_never(action)


def _change_hub_site_specific(
    dashboard_page: MainDashboard, site_id: str, action: HubAction, expect_success: bool = True
) -> None:
    """Apply `action` to the piggyback-hub site-specific setting of `site_id`."""
    match action:
        case HubEnableActions():
            _enable_hub_site_specific(dashboard_page, site_id, action)
        case HubDisableActions():
            _disable_hub_site_specific(dashboard_page, site_id, action, expect_success)
        case _:
            assert_never(action)


def _back_up_original_site_file_states(
    central_site: Site, remote_sites: list[Site]
) -> tuple[Sequence[Path], Mapping[Path, str]]:
    def replication_changes_rel_path(site_id: str) -> Path:
        return Path(f"var/check_mk/wato/replication_changes_{site_id}.mk")

    def replication_status_rel_path(site_id: str) -> Path:
        return Path(f"var/check_mk/wato/replication_status_{site_id}.mk")

    all_sites = [central_site] + remote_sites
    setting_files = (
        [GLOBAL_SETTINGS_REL_PATH, SITE_SPECIFIC_SETTINGS_REL_PATH, SITE_CONF_REL_PATH]
        + [replication_changes_rel_path(site.id) for site in all_sites]
        + [replication_status_rel_path(site.id) for site in all_sites]
    )
    backed_settings = {
        setting_file: central_site.read_file(setting_file)
        for setting_file in setting_files
        if central_site.file_exists(setting_file)
    }
    return setting_files, backed_settings


@contextmanager
def _setup_settings(
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]] | None,
    central_site: Site,
    remote_sites: list[Site],
) -> Iterator[None]:
    """Backup all relevant site-specific settings.

    Apply global and site-specific settings that need to be set up as precondition to the tests,
    then restore original settings after the test.
    """
    setting_files, backed_settings = _back_up_original_site_file_states(central_site, remote_sites)
    list_of_files = ", ".join(map(str, setting_files))
    logger.info("Backup settings within: '%s'", list_of_files)
    if global_settings:
        central_site.update_global_settings(GLOBAL_SETTINGS_REL_PATH, dict(global_settings))
    if site_specific_settings:
        updated_settings = {
            site_id: {"globals": dict(settings)}
            for site_id, settings in site_specific_settings.items()
        }
        central_site.update_site_specific_settings(
            SITE_SPECIFIC_SETTINGS_REL_PATH, updated_settings
        )
    try:
        yield
    finally:
        if is_cleanup_enabled():
            logger.info("Restore settings within: '%s'", list_of_files)
            for path in setting_files:
                if path in backed_settings:
                    central_site.write_file(path, backed_settings[path])
                elif central_site.file_exists(path):
                    central_site.delete_file(path)


def _wait_for_file_change(site: Site, file_path: Path, original_mtime: float) -> None:
    def _file_has_changed() -> bool:
        current_mtime = site.file_timestamp_ms(file_path)
        return current_mtime > original_mtime

    wait_until(_file_has_changed, timeout=10)


@pytest.mark.parametrize(
    ["action", "global_settings", "site_specific_settings", "expected_settings"],
    [
        pytest.param(
            HubEnableActions.SAVE,
            None,
            None,
            {"site_piggyback_hub": True},
            id="save-enable-from-unset",
        ),
        pytest.param(
            HubDisableActions.TOGGLE,
            {"site_piggyback_hub": True},
            {"gui_e2e_remote": {"site_piggyback_hub": False}},
            {"site_piggyback_hub": False},
            id="toggle-disable",
        ),
        pytest.param(
            HubDisableActions.RESET,
            {"site_piggyback_hub": True},
            {"gui_e2e_remote": {"site_piggyback_hub": False}},
            {},
            id="reset-to-default",
        ),
    ],
)
def test_change_hub_globally__no_error(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
    action: HubAction,
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]] | None,
    expected_settings: Mapping[str, object],
) -> None:
    """Test that each action persists the piggyback-hub global setting if the change is allowed"""
    # given
    with _setup_settings(
        global_settings, site_specific_settings, test_site, [remote_site_wato_disabled]
    ):
        original_mtime = test_site.file_timestamp_ms(GLOBAL_SETTINGS_REL_PATH)

        # when
        _change_hub_globally(dashboard_page, action)

        _wait_for_file_change(test_site, GLOBAL_SETTINGS_REL_PATH, original_mtime)

        # then
        assert test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH) == expected_settings, (
            "Piggyback-hub global setting was not successfully changed"
        )


@pytest.mark.parametrize(
    ["target_site", "action", "global_settings", "site_specific_settings", "expected_settings"],
    [
        pytest.param(
            TargetSite.CENTRAL,
            HubEnableActions.SAVE,
            None,
            {"gui_e2e_central": {}},
            {"site_piggyback_hub": True},
            id="central-save-enable-from-unset",
        ),
        pytest.param(
            TargetSite.CENTRAL,
            HubDisableActions.TOGGLE,
            {"site_piggyback_hub": True},
            {
                "gui_e2e_central": {"site_piggyback_hub": True},
                "gui_e2e_remote": {"site_piggyback_hub": False},
            },
            {"site_piggyback_hub": False},
            id="central-toggle-disable",
        ),
        pytest.param(
            TargetSite.REMOTE,
            HubEnableActions.SAVE,
            {"site_piggyback_hub": True},
            {"gui_e2e_remote": {"site_piggyback_hub": False}},
            {"site_piggyback_hub": True},
            id="remote-save-enable",
        ),
        pytest.param(
            TargetSite.REMOTE,
            HubDisableActions.RESET,
            {"site_piggyback_hub": True},
            {
                "gui_e2e_central": {"site_piggyback_hub": True},
                "gui_e2e_remote": {"site_piggyback_hub": True},
            },
            {},
            id="remote-reset-to-default",
        ),
    ],
)
def test_change_hub_site_specific__no_error(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
    target_site: TargetSite,
    action: HubAction,
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]] | None,
    expected_settings: Mapping[str, object],
) -> None:
    """Test that each action persists the piggyback-hub site-specific setting if the change is allowed"""
    # given
    with _setup_settings(
        global_settings, site_specific_settings, test_site, [remote_site_wato_disabled]
    ):
        site_id = (
            test_site.id if target_site is TargetSite.CENTRAL else remote_site_wato_disabled.id
        )
        original_mtime = test_site.file_timestamp_ms(SITE_SPECIFIC_SETTINGS_REL_PATH)

        # when
        _change_hub_site_specific(dashboard_page, site_id, action)

        _wait_for_file_change(test_site, SITE_SPECIFIC_SETTINGS_REL_PATH, original_mtime)

        # then
        assert (
            test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"][
                site_id
            ]["globals"]
            == expected_settings
        ), f"Piggyback-hub site-specific setting was not successfully changed for site '{site_id}'"


@pytest.mark.parametrize(
    ["action", "global_settings", "site_specific_settings"],
    [
        pytest.param(
            HubDisableActions.SAVE,
            {"site_piggyback_hub": True},
            {"gui_e2e_remote": {"site_piggyback_hub": True}},
            id="save-disable-while-remote-enabled",
        ),
        pytest.param(
            HubEnableActions.TOGGLE,
            None,
            {"gui_e2e_central": {"site_piggyback_hub": False}},
            id="toggle-enable-while-central-disabled",
        ),
        pytest.param(
            HubDisableActions.RESET,
            {"site_piggyback_hub": True},
            {"gui_e2e_remote": {"site_piggyback_hub": True}},
            id="reset-while-remote-enabled",
        ),
    ],
)
def test_change_hub_globally__error(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
    action: HubAction,
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]],
) -> None:
    """Test that each action rejects a global change leaving the piggyback-hub enabled for a remote
    site while it is disabled for the central site"""
    # given
    with _setup_settings(
        global_settings, site_specific_settings, test_site, [remote_site_wato_disabled]
    ):
        original_settings = test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH)

        # when
        _change_hub_globally(dashboard_page, action, expect_success=False)

        # then
        dashboard_page.main_area.check_error(EXPECTED_ERROR)
        assert test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH) == original_settings, (
            "Piggyback-hub global setting was changed although it should remain unchanged"
        )


@pytest.mark.parametrize(
    ["target_site", "action", "global_settings", "site_specific_settings"],
    [
        pytest.param(
            TargetSite.REMOTE,
            HubEnableActions.SAVE,
            {"site_piggyback_hub": False},
            {"gui_e2e_remote": {"site_piggyback_hub": False}},
            id="remote-save-enable-while-central-disabled",
        ),
        pytest.param(
            TargetSite.CENTRAL,
            HubDisableActions.TOGGLE,
            {"site_piggyback_hub": True},
            {
                "gui_e2e_central": {"site_piggyback_hub": True},
                "gui_e2e_remote": {"site_piggyback_hub": True},
            },
            id="central-toggle-disable-while-remote-enabled",
        ),
        pytest.param(
            TargetSite.CENTRAL,
            HubDisableActions.RESET,
            {"site_piggyback_hub": False},
            {
                "gui_e2e_central": {"site_piggyback_hub": True},
                "gui_e2e_remote": {"site_piggyback_hub": True},
            },
            id="central-reset-while-remote-enabled",
        ),
    ],
)
def test_change_hub_site_specific__error(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
    target_site: TargetSite,
    action: HubAction,
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]],
) -> None:
    """Test that each action rejects a site-specific change leaving the piggyback-hub enabled for a
    remote site while it is disabled for the central site"""
    # given
    with _setup_settings(
        global_settings, site_specific_settings, test_site, [remote_site_wato_disabled]
    ):
        site_id = (
            test_site.id if target_site is TargetSite.CENTRAL else remote_site_wato_disabled.id
        )
        original_settings = test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)[
            "sites"
        ][site_id]["globals"]

        # when
        _change_hub_site_specific(dashboard_page, site_id, action, expect_success=False)

        # then
        dashboard_page.main_area.check_error(EXPECTED_ERROR)
        assert (
            test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"][
                site_id
            ]["globals"]
            == original_settings
        ), f"Piggyback-hub was changed for site '{site_id}' although it should remain unchanged"
