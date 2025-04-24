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

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.global_settings import (
    EditPiggybackHubGlobally,
    EditPiggybackHubSiteSpecific,
)
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


SITE_SPECIFIC_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/sites.mk")
GLOBAL_SETTINGS_REL_PATH = Path("etc/omd/global.mk")
SITE_CONF_REL_PATH = Path("etc/omd/site.conf")


class HubEnableActions(enum.Enum):
    """The piggyback-hub can be enabled by
    * navigating to its specific global setting page, checking the relevant checkbox and saving
    """

    SAVE = enum.auto()


class HubDisableActions(enum.Enum):
    """The piggyback-hub can be disabled by
    * navigating to its specific global setting page, unchecking the relevant checkbox and saving
    """

    SAVE = enum.auto()


def _enable_hub_globally(
    dashboard_page: Dashboard, enable_actions: HubEnableActions = HubEnableActions.SAVE
) -> None:
    logger.info("Enable the piggyback-hub globally")
    match enable_actions:
        case HubEnableActions.SAVE:
            settings_page = EditPiggybackHubGlobally(dashboard_page.page)
            settings_page.enable_hub()
            settings_page.save_button.click()
        case _:
            assert_never(enable_actions)


def _disable_hub_globally(
    dashboard_page: Dashboard, disable_action: HubDisableActions = HubDisableActions.SAVE
) -> None:
    logger.info("Disable the piggyback-hub globally")
    match disable_action:
        case HubDisableActions.SAVE:
            settings_page = EditPiggybackHubGlobally(dashboard_page.page)
            settings_page.disable_hub()
            settings_page.save_button.click()
        case _:
            assert_never(disable_action)


def _enable_hub_site_specific(
    dashboard_page: Dashboard,
    site_id: str,
    enable_action: HubEnableActions = HubEnableActions.SAVE,
) -> None:
    logger.info("Enable the piggyback-hub site-specific")
    match enable_action:
        case HubEnableActions.SAVE:
            site_specific_settings_page = EditPiggybackHubSiteSpecific(dashboard_page.page, site_id)
            site_specific_settings_page.enable_hub()
            site_specific_settings_page.save_button.click()
        case _:
            assert_never(enable_action)


def _disable_hub_site_specific(
    dashboard_page: Dashboard,
    site_id: str,
    disable_action: HubDisableActions = HubDisableActions.SAVE,
) -> None:
    logger.info("Disable the piggyback-hub site-specific")
    match disable_action:
        case HubDisableActions.SAVE:
            site_specific_settings_page = EditPiggybackHubSiteSpecific(dashboard_page.page, site_id)
            site_specific_settings_page.disable_hub()
            site_specific_settings_page.save_button.click()
        case _:
            assert_never(disable_action)


def _back_up_original_site_file_states(
    central_site: Site, remote_sites: list[Site]
) -> tuple[Sequence[Path], Mapping[Path, str]]:
    def replication_changes_rel_path(site_id: str) -> Path:
        return Path(f"var/check_mk/wato/replication_changes_{site_id}.mk")

    def replication_status_rel_path(site_id: str) -> Path:
        return Path(f"var/check_mk/wato/replication_status_{site_id}.mk")

    all_sites = [central_site] + remote_sites
    setting_files = (
        [GLOBAL_SETTINGS_REL_PATH, SITE_SPECIFIC_SETTINGS_REL_PATH, Path("etc/omd/site.conf")]
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
    """Backup all relevant settings, apply global and site-specific settings that need to be set up
    as precondition to the tests, then restore original settings after the test"""
    setting_files, backed_settings = _back_up_original_site_file_states(central_site, remote_sites)

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
        for path in setting_files:
            if path in backed_settings:
                central_site.write_text_file(path, backed_settings[path])
            elif central_site.file_exists(path):
                central_site.delete_file(path)


@pytest.mark.parametrize(
    ["enable_action"],
    [
        pytest.param(HubEnableActions.SAVE, id="save"),
    ],
)
@pytest.mark.parametrize(
    ["global_settings", "site_specific_settings"],
    [
        pytest.param(
            None,
            {"gui_e2e_central": {"site_piggyback_hub": False}},
            id="central site-specific disabled",
        ),
        pytest.param(
            {"site_piggyback_hub": False},
            None,
            id="globally disabled",
        ),
    ],
)
def test_disabled_on_central__enable_on_remote__error(
    test_site: Site,
    remote_site: Site,
    dashboard_page: Dashboard,
    global_settings: Mapping[str, object] | None,
    site_specific_settings: Mapping[str, Mapping[str, object]] | None,
    enable_action: HubEnableActions,
) -> None:
    """Test that enabling the piggyback-hub site-specific for a remote site fails if it is not enabled for the central site"""
    # given
    with _setup_settings(global_settings, site_specific_settings, test_site, [remote_site]):
        original_settings = test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)[
            "sites"
        ][remote_site.id]

        # when
        _enable_hub_site_specific(dashboard_page, remote_site.id, enable_action)

        # then
        dashboard_page.main_area.check_error(
            "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
        )

        assert (
            test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"][
                remote_site.id
            ]
            == original_settings
        ), (
            f"Piggyback-hub was enabled for remote site '{remote_site.id}' although it should remain disabled"
        )


@pytest.mark.parametrize(
    ["disable_action"],
    [
        pytest.param(HubDisableActions.SAVE, id="save"),
    ],
)
@pytest.mark.parametrize(
    ["global_settings", "site_specific_settings"],
    [
        pytest.param(
            {"site_piggyback_hub": True},
            {"gui_e2e_central": {"site_piggyback_hub": True}},
            id="globally enabled",
        ),
        pytest.param(
            None,
            {
                "gui_e2e_central": {"site_piggyback_hub": True},
                "gui_e2e_remote": {"site_piggyback_hub": True},
            },
            id="remote site-specific enabled",
        ),
    ],
)
def test_enabled_on_remote__disable_on_central__error(
    test_site: Site,
    remote_site: Site,
    dashboard_page: Dashboard,
    global_settings: dict[str, object] | None,
    site_specific_settings: dict[str, dict[str, object]],
    disable_action: HubDisableActions,
) -> None:
    """Test that disabling the piggyback-hub site-specific for the central site fails if it is enabled for a remote site"""
    # given
    with _setup_settings(global_settings, site_specific_settings, test_site, [remote_site]):
        original_settings = (
            test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"][
                remote_site.id
            ]["globals"]
            if "gui_e2e_remote" in site_specific_settings
            else {}
        )

        # when
        _disable_hub_site_specific(dashboard_page, test_site.id, disable_action)

        # then
        dashboard_page.main_area.check_error(
            "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
        )

        assert (
            test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"][
                remote_site.id
            ]["globals"]
            if "gui_e2e_remote" in site_specific_settings
            else {} == original_settings
        ), (
            f"Piggyback-hub was disabled for central site '{test_site.id}' although it should remain enabled"
        )


@pytest.mark.parametrize(
    ["disable_action"],
    [
        pytest.param(HubDisableActions.SAVE, id="save"),
    ],
)
def test_enabled_on_remote__disable_globally__error(
    test_site: Site,
    remote_site: Site,
    dashboard_page: Dashboard,
    disable_action: HubDisableActions,
) -> None:
    """Test that disabling the piggyback-hub globally fails if it is enabled for any remote sites"""
    # given
    with _setup_settings(
        {"site_piggyback_hub": True},
        {"gui_e2e_remote": {"site_piggyback_hub": True}},
        test_site,
        [remote_site],
    ):
        original_settings = test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH)

        # when
        _disable_hub_globally(dashboard_page, disable_action)

        # then
        dashboard_page.main_area.check_error(
            "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
        )
        assert test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH) == original_settings, (
            "Piggyback-hub was disabled globally although it should remain enabled"
        )


@pytest.mark.parametrize(
    ["enable_action"],
    [
        pytest.param(HubEnableActions.SAVE, id="save"),
    ],
)
def test_disabled_on_central__enable_globally__error(
    test_site: Site,
    remote_site: Site,
    dashboard_page: Dashboard,
    enable_action: HubEnableActions,
) -> None:
    """Test that enabling the piggyback-hub globally fails if it is disabled for the central site"""
    # given
    with _setup_settings(
        None,
        {"gui_e2e_central": {"site_piggyback_hub": False}},
        test_site,
        [remote_site],
    ):
        original_settings = test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH)

        # when
        _enable_hub_globally(dashboard_page, enable_action)

        # then
        dashboard_page.main_area.check_error(
            "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
        )
        assert test_site.read_global_settings(GLOBAL_SETTINGS_REL_PATH) == original_settings, (
            "Piggyback-hub was enabled globally although it should remain disabled"
        )
